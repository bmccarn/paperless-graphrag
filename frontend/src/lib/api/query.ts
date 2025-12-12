import { apiClient } from './client';
import type { QueryRequest, QueryResponse, SourceDocumentRef } from '@/types';

export async function submitQuery(request: QueryRequest): Promise<QueryResponse> {
  return apiClient.post<QueryResponse, QueryRequest>('/query', request);
}

export interface StreamEvent {
  type: 'status' | 'thinking' | 'complete' | 'error';
  message?: string;
  detail?: string;
  response?: string;
  query?: string;
  method?: string;
  source_documents?: SourceDocumentRef[];
}

export async function submitQueryStream(
  request: QueryRequest,
  onEvent: (event: StreamEvent) => void,
): Promise<QueryResponse> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || '/api';
  const response = await fetch(`${baseUrl}/query/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Query failed' }));
    throw new Error(error.detail || 'Query failed');
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('No response body');
  }

  const decoder = new TextDecoder();
  let buffer = '';
  let finalResponse: QueryResponse | null = null;

  // Helper to process a single SSE line
  const processLine = (line: string) => {
    if (line.startsWith('data: ')) {
      try {
        const event: StreamEvent = JSON.parse(line.slice(6));
        onEvent(event);

        if (event.type === 'complete') {
          // Check for response existence (not just truthiness) to handle empty strings
          finalResponse = {
            query: event.query || request.query,
            method: event.method || request.method,
            response: event.response ?? '',
            source_documents: event.source_documents,
          };
        } else if (event.type === 'error') {
          throw new Error(event.message || 'Query failed');
        }
      } catch (e) {
        if (e instanceof SyntaxError) {
          console.warn('Failed to parse SSE event:', line);
        } else {
          throw e;
        }
      }
    }
  };

  while (true) {
    const { done, value } = await reader.read();

    if (value) {
      buffer += decoder.decode(value, { stream: !done });
    }

    // Parse SSE events
    const lines = buffer.split('\n');
    buffer = lines.pop() || ''; // Keep incomplete line in buffer

    for (const line of lines) {
      processLine(line);
    }

    if (done) {
      // Process any remaining content in buffer after stream ends
      if (buffer.trim()) {
        processLine(buffer);
      }
      break;
    }
  }

  if (!finalResponse) {
    throw new Error('No response received');
  }

  return finalResponse;
}
