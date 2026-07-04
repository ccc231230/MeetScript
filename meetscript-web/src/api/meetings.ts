import apiClient from './client';
import type {
  Meeting,
  MeetingCreate,
  MeetingListParams,
  PaginatedResponse,
  SignUrlResponse,
  UploadCompleteRequest,
} from '../types';

export const meetingsAPI = {
  list: (params?: MeetingListParams) =>
    apiClient.get<PaginatedResponse<Meeting>>('/meetings', { params }),

  get: (id: string) =>
    apiClient.get<Meeting>(`/meetings/${id}`),

  create: (data: MeetingCreate) =>
    apiClient.post<Meeting>('/meetings', data),

  update: (id: string, data: Partial<MeetingCreate>) =>
    apiClient.put<Meeting>(`/meetings/${id}`, data),

  delete: (id: string) =>
    apiClient.delete(`/meetings/${id}`),

  getSignUrl: (fileName: string, contentType: string, fileSize: number) =>
    apiClient.post<SignUrlResponse>('/meetings/upload/sign-url', {
      file_name: fileName,
      content_type: contentType,
      file_size: fileSize,
    }),

  uploadFile: (file: File, onProgress?: (pct: number) => void) => {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post<SignUrlResponse>('/meetings/upload/file', formData, {
      timeout: 5 * 60 * 1000, // 5 minutes for large video files
      // NOTE: Do NOT set Content-Type here. Axios auto-detects FormData
      // and sets "multipart/form-data; boundary=----WebKitFormBoundaryXXX".
      // Manually setting "multipart/form-data" without boundary breaks parsing.
      onUploadProgress: (e) => {
        if (onProgress && e.total) {
          onProgress(Math.round((e.loaded / e.total) * 70));
        }
      },
    });
  },

  notifyUploadComplete: (data: UploadCompleteRequest) =>
    apiClient.post<Meeting>('/meetings/upload/complete', data),

  triggerProcess: (id: string) =>
    apiClient.post(`/meetings/${id}/process`),
};
