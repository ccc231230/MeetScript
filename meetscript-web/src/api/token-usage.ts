import apiClient from './client';
import type { TokenUsage, TokenUsageStats, PaginatedResponse } from '../types';

export const tokenUsageAPI = {
  list: (params?: { page?: number; page_size?: number; days?: number }) =>
    apiClient.get<PaginatedResponse<TokenUsage>>('/token-usage', { params }),

  stats: (days?: number) =>
    apiClient.get<TokenUsageStats>('/token-usage/stats', { params: { days } }),
};
