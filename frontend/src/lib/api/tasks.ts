import { apiClient } from './client';
import type { Task, TaskStatus } from '@/types';

export async function getTasks(status?: TaskStatus): Promise<Task[]> {
  const endpoint = status ? `/tasks?status=${status}` : '/tasks';
  return apiClient.get<Task[]>(endpoint);
}

export async function getTask(taskId: string): Promise<Task> {
  return apiClient.get<Task>(`/tasks/${taskId}`);
}

export async function cleanupTasks(maxAgeHours: number = 24): Promise<{ removed: number }> {
  return apiClient.post<{ removed: number }>(`/tasks/cleanup?max_age_hours=${maxAgeHours}`);
}
