import { create } from 'zustand';

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  userId: string | null;
  role: string | null;
  setAuth: (access: string, refresh: string, userId: string, role: string) => void;
  logout: () => void;
  isAuthenticated: () => boolean;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  accessToken: localStorage.getItem('access_token'),
  refreshToken: localStorage.getItem('refresh_token'),
  userId: localStorage.getItem('user_id'),
  role: localStorage.getItem('user_role'),
  setAuth: (access, refresh, userId, role) => {
    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);
    localStorage.setItem('user_id', userId);
    localStorage.setItem('user_role', role);
    set({ accessToken: access, refreshToken: refresh, userId, role });
  },
  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_id');
    localStorage.removeItem('user_role');
    set({ accessToken: null, refreshToken: null, userId: null, role: null });
  },
  isAuthenticated: () => !!get().accessToken,
}));
