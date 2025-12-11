import { apiClient } from './client';
import type { SyncRequest, SyncResponse, StatsResponse } from '@/types';

export async function triggerSync(full: boolean = false): Promise<SyncResponse> {
  return apiClient.post<SyncResponse, SyncRequest>('/sync', { full });
}

export async function getStats(): Promise<StatsResponse> {
  return apiClient.get<StatsResponse>('/documents/stats');
}
