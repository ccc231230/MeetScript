import apiClient from './client';
import type { ExportRequest } from '../types';

export const exportsAPI = {
  export: (data: ExportRequest) =>
    apiClient.post('/exports', null, {
      params: {
        meeting_id: data.meeting_id,
        format: data.format,
        lang: data.lang || 'zh',
      },
      responseType: 'blob',
    }),
};
