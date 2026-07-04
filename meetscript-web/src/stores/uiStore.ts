import { create } from 'zustand';

type ThemeMode = 'light' | 'dark';
type Language = 'zh-CN' | 'en-US' | 'ja-JP';

interface UIState {
  collapsed: boolean;
  themeMode: ThemeMode;
  language: Language;
  toggleCollapsed: () => void;
  setThemeMode: (mode: ThemeMode) => void;
  setLanguage: (lang: Language) => void;
}

export const useUIStore = create<UIState>((set) => ({
  collapsed: false,
  themeMode: (localStorage.getItem('theme_mode') as ThemeMode) || 'light',
  language: (localStorage.getItem('i18nextLng') as Language) || 'zh-CN',
  toggleCollapsed: () => set((s) => ({ collapsed: !s.collapsed })),
  setThemeMode: (mode) => {
    localStorage.setItem('theme_mode', mode);
    set({ themeMode: mode });
  },
  setLanguage: (lang) => set({ language: lang }),
}));
