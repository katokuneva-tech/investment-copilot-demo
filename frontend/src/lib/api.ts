import { API_BASE_URL } from './constants';
import { ContentBlock, KBDocument } from './types';

function authHeaders(): Record<string, string> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('copilot_token') : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export type SSEEvent =
  | { type: 'text_delta'; content: string }
  | { type: 'text_done' }
  | { type: 'status'; content: string }
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
  attachmentIds?: string[],
  history?: Array<{role: string; content: string}>,
): Promise<void> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({
        skill_id: skillId,
        message,
        session_id: sessionId,
        attachment_ids: attachmentIds || [],
        history: history || [],
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
  } catch (err: unknown) {
    if (err instanceof Error && err.name !== 'AbortError') {
      onError(err);
    } else if (!(err instanceof Error)) {
      onError(new Error(String(err)));
    }
  }
}

export async function fetchDocuments(): Promise<KBDocument[]> {
  const res = await fetch(`${API_BASE_URL}/api/documents`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Failed to fetch documents');
  const data = await res.json();
  return data.documents;
}

export async function uploadDocument(file: File): Promise<KBDocument> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE_URL}/api/documents/upload`, {
    method: 'POST',
    headers: authHeaders(),
    body: formData,
  });
  if (!res.ok) throw new Error('Failed to upload document');
  const data = await res.json();
  return data.document;
}

export async function deleteDocument(docId: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/documents/${docId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error('Failed to delete document');
}

export async function toggleDocument(docId: string): Promise<KBDocument> {
  const res = await fetch(`${API_BASE_URL}/api/documents/${docId}/toggle`, {
    method: 'PATCH',
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error('Failed to toggle document');
  const data = await res.json();
  return data.document;
}

export async function uploadChatFile(file: File, sessionId: string): Promise<KBDocument> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('session_id', sessionId);
  const res = await fetch(`${API_BASE_URL}/api/documents/session-upload`, {
    method: 'POST',
    headers: authHeaders(),
    body: formData,
  });
  if (!res.ok) throw new Error('Failed to upload chat file');
  const data = await res.json();
  return data.document;
}

export async function fetchDocumentContent(docId: string): Promise<{ document: KBDocument; content: string }> {
  const res = await fetch(`${API_BASE_URL}/api/documents/${docId}/content`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Failed to fetch document content');
  return res.json();
}

export async function exportBlocks(blocks: ContentBlock[], title: string): Promise<string> {
  const res = await fetch(`${API_BASE_URL}/api/export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({
      blocks: blocks.map(b => ({ type: b.type, data: b.data })),
      title,
      format: 'pdf',
    }),
  });
  if (!res.ok) throw new Error('Export failed');
  const data = await res.json();
  return data.url;
}

export function getReportUrl(reportId: string): string {
  return `${API_BASE_URL}/api/reports/${reportId}`;
}
