import apiClient from './client';
import type { ApiKey, ApiKeyCreate, ApiKeyCreateResponse } from '../types';

export const apiKeysAPI = {
  list: () =>
    apiClient.get<ApiKey[]>('/api-keys'),

  create: (data: ApiKeyCreate) =>
    apiClient.post<ApiKeyCreateResponse>('/api-keys', data),

  delete: (id: string) =>
    apiClient.delete(`/api-keys/${id}`),
};
