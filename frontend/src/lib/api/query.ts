import { apiClient } from './client';
import type { QueryRequest, QueryResponse } from '@/types';

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
}

export async function submitQueryStream(
  request: QueryRequest,
  onEvent: (event: StreamEvent) => void,
): Promise<QueryResponse> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || '';
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

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Parse SSE events
    const lines = buffer.split('\n');
    buffer = lines.pop() || ''; // Keep incomplete line in buffer

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const event: StreamEvent = JSON.parse(line.slice(6));
          onEvent(event);

          if (event.type === 'complete' && event.response) {
            finalResponse = {
              query: event.query || request.query,
              method: event.method || request.method,
              response: event.response,
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
    }
  }

  if (!finalResponse) {
    throw new Error('No response received');
  }

  return finalResponse;
}
