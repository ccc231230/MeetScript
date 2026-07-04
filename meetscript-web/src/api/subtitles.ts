import apiClient from './client';
import type { Subtitle } from '../types';

export const subtitlesAPI = {
  list: async (meetingId: string) => {
    const res = await apiClient.get<{ items: Subtitle[] }>(`/meetings/${meetingId}/subtitles`);
    return res.data.items;
  },
};
