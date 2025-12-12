import { apiClient } from './client';
import type {
  SettingsResponse,
  SettingsUpdateRequest,
  SettingsUpdateResponse,
  ConfigStatusResponse,
  ConnectionTestResult,
} from '@/types';

export async function getSettings(): Promise<SettingsResponse> {
  return apiClient.get<SettingsResponse>('/settings');
}

export async function updateSettings(
  settings: Record<string, string | number | null>
): Promise<SettingsUpdateResponse> {
  return apiClient.put<SettingsUpdateResponse, SettingsUpdateRequest>(
    '/settings',
    { settings }
  );
}

export async function getConfigStatus(): Promise<ConfigStatusResponse> {
  return apiClient.get<ConfigStatusResponse>('/settings/status');
}

export async function testConnections(): Promise<ConnectionTestResult> {
  return apiClient.post<ConnectionTestResult>('/settings/test-connection');
}

export async function deleteSetting(key: string): Promise<{ success: boolean }> {
  return apiClient.delete<{ success: boolean }>(`/settings/${key}`);
}

export async function restartBackend(): Promise<{ success: boolean; message: string }> {
  return apiClient.post<{ success: boolean; message: string }>('/settings/restart');
}
