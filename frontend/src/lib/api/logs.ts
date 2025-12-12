import { apiClient } from './client';

export interface LogFileInfo {
  name: string;
  path: string;
  size_bytes: number;
  exists: boolean;
}

export interface LogFilesResponse {
  files: LogFileInfo[];
}

export interface LogContentResponse {
  content: string;
  total_lines: number;
  returned_lines: number;
}

export async function getLogFiles(): Promise<LogFilesResponse> {
  return apiClient.get<LogFilesResponse>('/logs/files');
}

export async function getIndexingLog(tail: number = 500): Promise<LogContentResponse> {
  return apiClient.get<LogContentResponse>(`/logs/indexing?tail=${tail}`);
}

export interface LogFileContentResponse extends LogContentResponse {
  filename: string;
}

export async function getLogFile(filename: string, tail: number = 500): Promise<LogFileContentResponse> {
  return apiClient.get<LogFileContentResponse>(`/logs/file/${encodeURIComponent(filename)}?tail=${tail}`);
}

export async function clearIndexingLog(): Promise<{ message: string; cleared: boolean }> {
  return apiClient.delete<{ message: string; cleared: boolean }>('/logs/indexing');
}

export function getIndexingLogStreamUrl(): string {
  // Return the SSE endpoint URL
  return '/logs/indexing/stream?tail=100';
}
