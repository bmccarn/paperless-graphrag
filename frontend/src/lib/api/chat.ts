import { apiClient } from './client';

// Types for chat API
export interface ChatSessionResponse {
  id: string;
  name: string;
  createdAt: string;
  updatedAt: string;
  messages?: ChatMessageResponse[];
}

export interface ChatMessageResponse {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  method?: string;
  sourceDocuments?: Array<{
    paperless_id: number;
    title: string;
    view_url: string;
  }>;
  timestamp: string;
}

export interface ChatStatusResponse {
  enabled: boolean;
  message: string;
}

export interface CreateSessionRequest {
  name: string;
  id?: string;
}

export interface AddMessageRequest {
  id?: string;
  role: 'user' | 'assistant';
  content: string;
  method?: string;
  sourceDocuments?: Array<{
    paperless_id: number;
    title: string;
    view_url: string;
  }>;
  timestamp?: string;
}

/**
 * Check if persistent chat history is enabled
 */
export async function getChatStatus(): Promise<ChatStatusResponse> {
  return apiClient.get<ChatStatusResponse>('/chat/status');
}

/**
 * Test the database connection
 */
export async function testChatConnection(): Promise<{ success: boolean; message: string }> {
  return apiClient.post<{ success: boolean; message: string }>('/chat/test-connection');
}

/**
 * List all chat sessions
 */
export async function getSessions(): Promise<ChatSessionResponse[]> {
  return apiClient.get<ChatSessionResponse[]>('/chat/sessions');
}

/**
 * Create a new chat session
 */
export async function createSession(name: string, id?: string): Promise<ChatSessionResponse> {
  return apiClient.post<ChatSessionResponse, CreateSessionRequest>('/chat/sessions', { name, id });
}

/**
 * Get a single chat session with all messages
 */
export async function getSession(sessionId: string): Promise<ChatSessionResponse> {
  return apiClient.get<ChatSessionResponse>(`/chat/sessions/${sessionId}`);
}

/**
 * Delete a chat session
 */
export async function deleteSession(sessionId: string): Promise<{ success: boolean }> {
  return apiClient.delete<{ success: boolean }>(`/chat/sessions/${sessionId}`);
}

/**
 * Rename a chat session
 */
export async function renameSession(sessionId: string, name: string): Promise<ChatSessionResponse> {
  return apiClient.put<ChatSessionResponse>(`/chat/sessions/${sessionId}`, { name });
}

/**
 * Add a message to a chat session
 */
export async function addMessage(
  sessionId: string,
  message: AddMessageRequest
): Promise<ChatMessageResponse> {
  return apiClient.post<ChatMessageResponse, AddMessageRequest>(
    `/chat/sessions/${sessionId}/messages`,
    message
  );
}

/**
 * Get recent messages from a session (for conversation context)
 */
export async function getRecentMessages(
  sessionId: string,
  limit: number = 6
): Promise<ChatMessageResponse[]> {
  return apiClient.get<ChatMessageResponse[]>(
    `/chat/sessions/${sessionId}/messages/recent?limit=${limit}`
  );
}

/**
 * Generate a meaningful chat title from a user message using AI
 */
export async function generateChatTitle(message: string): Promise<string> {
  const response = await apiClient.post<{ title: string }, { message: string }>(
    '/chat/generate-title',
    { message }
  );
  return response.title;
}
