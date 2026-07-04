import apiClient from './client';
import type { ExportRequest } from '../types';

export const exportsAPI = {
  export: (data: ExportRequest) =>
    apiClient.post('/export', data, { responseType: 'blob' }),
};
