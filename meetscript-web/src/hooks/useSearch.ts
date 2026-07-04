import { useState, useCallback, useRef } from 'react';

export function useSearch(debounceMs = 300) {
  const [query, setQuery] = useState('');
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  const debouncedSetQuery = useCallback(
    (value: string) => {
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => setQuery(value), debounceMs);
    },
    [debounceMs],
  );

  return { query, setQuery: debouncedSetQuery };
}
