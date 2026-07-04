import apiClient from './client';
import type { Translation, TranslationRequest } from '../types';

export const translationAPI = {
  list: async (meetingId: string, lang?: string) => {
    const res = await apiClient.get<{ items: Translation[] }>(`/meetings/${meetingId}/translations`, { params: { lang } });
    return res.data.items;
  },

  request: (data: TranslationRequest) =>
    apiClient.post('/translations', data),

  update: (id: string, translatedText: string) =>
    apiClient.put<Translation>(`/translations/${id}`, { translated_text: translatedText }),
};
