import { create } from 'zustand';
import type { Meeting } from '../types';

interface MeetingState {
  meetings: Meeting[];
  currentMeeting: Meeting | null;
  loading: boolean;
  error: string | null;
  setMeetings: (meetings: Meeting[]) => void;
  setCurrentMeeting: (meeting: Meeting | null) => void;
  addMeeting: (meeting: Meeting) => void;
  removeMeeting: (id: string) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useMeetingStore = create<MeetingState>((set) => ({
  meetings: [],
  currentMeeting: null,
  loading: false,
  error: null,
  setMeetings: (meetings) => set({ meetings, error: null }),
  setCurrentMeeting: (meeting) => set({ currentMeeting: meeting }),
  addMeeting: (meeting) =>
    set((s) => ({ meetings: [meeting, ...s.meetings] })),
  removeMeeting: (id) =>
    set((s) => ({
      meetings: s.meetings.filter((m) => m.id !== id),
      currentMeeting: s.currentMeeting?.id === id ? null : s.currentMeeting,
    })),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
}));
