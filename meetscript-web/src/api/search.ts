import apiClient from './client';
import type { SearchResult, SearchParams, Meeting } from '../types';
import type { PaginatedResponse } from '../types';

export const searchAPI = {
  searchSubtitles: (params: SearchParams) =>
    apiClient.get<SearchResult>('/search/subtitles', { params }),

  searchMeetings: (keyword: string) =>
    apiClient.get<PaginatedResponse<Meeting>>('/search/meetings', { params: { q: keyword } }),
};
