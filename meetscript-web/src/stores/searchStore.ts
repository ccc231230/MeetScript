import { create } from 'zustand';
import type { SearchParams, SearchResult } from '../types';

interface SearchState {
  query: string;
  result: SearchResult | null;
  loading: boolean;
  isSearching: boolean;
  filters: Omit<SearchParams, 'q' | 'page' | 'page_size'>;
  setQuery: (q: string) => void;
  setResult: (r: SearchResult | null) => void;
  setLoading: (l: boolean) => void;
  setIsSearching: (s: boolean) => void;
  setFilters: (f: Partial<SearchState['filters']>) => void;
  reset: () => void;
}

export const useSearchStore = create<SearchState>((set) => ({
  query: '',
  result: null,
  loading: false,
  isSearching: false,
  filters: {},
  setQuery: (query) => set({ query }),
  setResult: (result) => set({ result }),
  setLoading: (loading) => set({ loading }),
  setIsSearching: (isSearching) => set({ isSearching }),
  setFilters: (f) => set((s) => ({ filters: { ...s.filters, ...f } })),
  reset: () => set({ query: '', result: null, isSearching: false, filters: {} }),
}));
