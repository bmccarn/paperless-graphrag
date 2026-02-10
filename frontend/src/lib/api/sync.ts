import { apiClient } from './client';
import type { SyncRequest, SyncResponse, StatsResponse } from '@/types';

export async function triggerSync(full: boolean = false, reindex: boolean = false): Promise<SyncResponse> {
  return apiClient.post<SyncResponse, SyncRequest>('/sync', { full, reindex });
}

export async function getStats(): Promise<StatsResponse> {
  return apiClient.get<StatsResponse>('/documents/stats');
}
