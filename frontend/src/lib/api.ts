import { API_BASE_URL } from './constants';
import { ContentBlock } from './types';

export type SSEEvent =
  | { type: 'text_delta'; content: string }
  | { type: 'text_done' }
  | { type: 'table'; data: any }
  | { type: 'chart'; data: any }
  | { type: 'pdf_link'; data: any }
  | { type: 'sources'; data: any }
  | { type: 'done' };

export async function streamChat(
  skillId: string,
  message: string,
  sessionId: string,
  onEvent: (event: SSEEvent) => void,
  onError: (error: Error) => void,
  signal?: AbortSignal,
): Promise<void> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        skill_id: skillId,
        message,
        session_id: sessionId,
      }),
      signal,
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No response body');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith('data: ')) continue;

        const jsonStr = trimmed.slice(6);
        if (jsonStr === '[DONE]') {
          onEvent({ type: 'done' });
          return;
        }

        try {
          const event = JSON.parse(jsonStr) as SSEEvent;
          onEvent(event);
        } catch {
          // skip malformed JSON
        }
      }
    }

    // Stream ended without explicit done
    onEvent({ type: 'done' });
  } catch (err: any) {
    if (err.name !== 'AbortError') {
      onError(err);
    }
  }
}

export function getReportUrl(reportId: string): string {
  return `${API_BASE_URL}/api/reports/${reportId}`;
}
