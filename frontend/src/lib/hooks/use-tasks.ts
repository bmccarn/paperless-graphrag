'use client';

import { useState, useEffect, useCallback } from 'react';
import { getTasks, getTask } from '@/lib/api';
import type { Task, TaskStatus } from '@/types';

export function useTasks(statusFilter?: TaskStatus, pollInterval: number = 5000) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchTasks = useCallback(async () => {
    try {
      const data = await getTasks(statusFilter);
      setTasks(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch tasks'));
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    fetchTasks();
    const interval = setInterval(fetchTasks, pollInterval);
    return () => clearInterval(interval);
  }, [fetchTasks, pollInterval]);

  return { tasks, isLoading, error, refetch: fetchTasks };
}

export function useTask(taskId: string | null, pollInterval: number = 2000) {
  const [task, setTask] = useState<Task | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchTask = useCallback(async () => {
    if (!taskId) return;
    try {
      setIsLoading(true);
      const data = await getTask(taskId);
      setTask(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch task'));
    } finally {
      setIsLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    if (!taskId) {
      setTask(null);
      return;
    }

    fetchTask();

    // Only poll if task is not completed
    if (task?.status === 'completed' || task?.status === 'failed') {
      return;
    }

    const interval = setInterval(fetchTask, pollInterval);
    return () => clearInterval(interval);
  }, [taskId, fetchTask, pollInterval, task?.status]);

  return { task, isLoading, error, refetch: fetchTask };
}
