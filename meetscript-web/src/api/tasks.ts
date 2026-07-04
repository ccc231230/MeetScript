import apiClient from './client';
import type { MeetingTask, TaskLog } from '../types';

export const tasksAPI = {
  get: (id: string) =>
    apiClient.get<MeetingTask>(`/tasks/${id}`),

  getLogs: (id: string) =>
    apiClient.get<TaskLog[]>(`/tasks/${id}/logs`),

  retry: (id: string) =>
    apiClient.post<MeetingTask>(`/tasks/${id}/retry`),
};
