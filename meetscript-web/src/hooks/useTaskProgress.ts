import { useRef, useCallback } from 'react';
import type { TaskProgressEvent } from '../types';

export function useTaskProgress(taskId: string | null) {
  const eventsRef = useRef<TaskProgressEvent[]>([]);

  const appendEvent = useCallback((event: TaskProgressEvent) => {
    eventsRef.current.push(event);
  }, []);

  const clearEvents = useCallback(() => {
    eventsRef.current = [];
  }, []);

  return { events: eventsRef, appendEvent, clearEvents };
}
