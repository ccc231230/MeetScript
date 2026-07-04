import apiClient from './client';
import type { MeetingTask, TaskLog } from '../types';

export const tasksAPI = {
  list: (params?: { status?: string; page?: number; page_size?: number }) =>
    apiClient.get<{ items: MeetingTask[]; total: number }>('/tasks', { params }),

  get: (id: string) =>
    apiClient.get<MeetingTask>(`/tasks/${id}`),

  getLogs: (id: string) =>
    apiClient.get<TaskLog[]>(`/tasks/${id}/logs`),

  retry: (id: string) =>
    apiClient.post<MeetingTask>(`/tasks/${id}/retry`),
};
