import apiClient from './client';
import type { LoginRequest, LoginResponse } from '../types';

export const authAPI = {
  login: (data: LoginRequest) =>
    apiClient.post<LoginResponse>('/auth/login', data),

  refresh: (refreshToken: string) =>
    apiClient.post<LoginResponse>('/auth/refresh', { refresh_token: refreshToken }),
};
