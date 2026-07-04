import apiClient from './client';
import type { SearchResult, SearchParams, Meeting } from '../types';
import type { PaginatedResponse } from '../types';

export const searchAPI = {
  searchSubtitles: async (params: SearchParams): Promise<{ data: SearchResult }> => {
    const res = await apiClient.get<SearchResult>('/search/subtitles', { params });
    // Backend returns { subtitles, meetings, total, ... }, frontend expects { items, ... }
    return {
      ...res,
      data: {
        items: res.data?.subtitles ?? [],
        total: res.data?.total ?? 0,
        page: res.data?.page ?? 1,
        page_size: res.data?.page_size ?? 50,
        pages: Math.ceil((res.data?.total ?? 0) / (res.data?.page_size ?? 50)),
      },
    };
  },

  searchMeetings: (keyword: string) =>
    apiClient.get<PaginatedResponse<Meeting>>('/search/meetings', { params: { q: keyword } }),
};
