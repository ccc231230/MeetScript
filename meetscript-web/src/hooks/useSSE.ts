import { useEffect, useRef } from 'react';

export interface TaskProgressEvent {
  task_id: string;
  meeting_id: string;
  task_type: string;
  status: string;
  progress: number;
  current_step: string;
  message: string;
  timestamp: string;
  error_detail?: string;
}

/**
 * Subscribe to a single task's progress via SSE.
 */
export function useSSE(taskId: string | null, onMessage: (data: TaskProgressEvent) => void) {
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  useEffect(() => {
    if (!taskId) return;

    const eventSource = new EventSource(`/api/v1/tasks/${taskId}/stream`);
    let closed = false;

    eventSource.onmessage = (event) => {
      if (closed) return;
      try {
        const data = JSON.parse(event.data) as TaskProgressEvent;
        onMessageRef.current(data);
        if (['completed', 'failed', 'dlq'].includes(data.status)) {
          closed = true;
          eventSource.close();
        }
      } catch {
        // ignore parse errors
      }
    };

    return () => {
      closed = true;
      eventSource.close();
    };
  }, [taskId]);
}

/**
 * Subscribe to ALL task progress events for a meeting via SSE.
 * Optionally also subscribe to a specific task within that meeting.
 */
export function useMeetingSSE(
  meetingId: string | null,
  taskId: string | null,
  onMessage: (data: TaskProgressEvent) => void,
) {
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  useEffect(() => {
    if (!meetingId) return;

    let url = `/api/v1/meetings/${meetingId}/stream`;
    if (taskId) {
      url += `?task_id=${taskId}`;
    }

    const eventSource = new EventSource(url);
    let closed = false;

    eventSource.onmessage = (event) => {
      if (closed) return;
      try {
        const data = JSON.parse(event.data) as TaskProgressEvent;
        onMessageRef.current(data);
      } catch {
        // ignore parse errors
      }
    };

    return () => {
      closed = true;
      eventSource.close();
    };
  }, [meetingId, taskId]);
}
