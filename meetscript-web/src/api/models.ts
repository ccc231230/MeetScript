import apiClient from './client';
import type { ModelConfig, ModelConfigUpdate } from '../types';

export const modelsAPI = {
  list: () =>
    apiClient.get<ModelConfig[]>('/model-configs'),

  get: (id: string) =>
    apiClient.get<ModelConfig>(`/model-configs/${id}`),

  update: (id: string, data: ModelConfigUpdate) =>
    apiClient.put<ModelConfig>(`/model-configs/${id}`, data),
};
