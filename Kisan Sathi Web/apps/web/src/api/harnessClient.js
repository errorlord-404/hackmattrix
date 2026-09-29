import { requestJson, requestId } from './httpClient.js';

const EVENT_LIMIT = 512 * 1024;

function parseEvent(raw) {
  try {
    const value = JSON.parse(raw);
    if (!value || value.version !== '1.0' || !value.event_id || !value.session_id || !value.turn_id || !Number.isInteger(value.sequence) || !value.kind) return null;
    return value;
  } catch {
    return null;
  }
}

async function stream(path, { onEvent, after = 0, signal } = {}) {
  const response = await fetch(path, { method: 'GET', headers: { Accept: 'text/event-stream', 'X-Request-ID': requestId(), ...(after ? { 'Last-Event-ID': String(after) } : {}) }, credentials: 'include', signal });
  if (!response.ok) throw new Error(`Harness stream failed (${response.status})`);
  if (!response.body?.getReader) throw new Error('Streaming is not available in this browser.');
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let bytes = 0;
  while (true) {
    const next = await reader.read();
    if (next.done) break;
    bytes += next.value.byteLength;
    if (bytes > EVENT_LIMIT) throw new Error('Harness stream exceeded its safety limit.');
    buffer += decoder.decode(next.value, { stream: true });
    const lines = buffer.split(/\r?\n/);
    buffer = lines.pop() || '';
    for (const line of lines) {
      const value = line.startsWith('data:') ? line.slice(5).trim() : line.trim();
      if (!value) continue;
      const event = parseEvent(value);
      if (event) onEvent?.(event);
    }
  }
}

export const harnessClient = {
  start: (payload = {}) => requestJson('/harness/sessions', { method: 'POST', body: payload }),
  resume: (sessionId, after = 0, options = {}) => stream(`/harness/sessions/${encodeURIComponent(sessionId)}/events`, { ...options, after }),
  status: (sessionId) => requestJson(`/harness/sessions/${encodeURIComponent(sessionId)}`),
  sendText: (sessionId, payload) => requestJson(`/harness/sessions/${encodeURIComponent(sessionId)}/turns`, { method: 'POST', body: payload }),
  cancel: (sessionId, turnId) => requestJson(`/harness/sessions/${encodeURIComponent(sessionId)}/turns/${encodeURIComponent(turnId)}/cancel`, { method: 'POST' }),
  respond: (sessionId, requestIdValue, payload) => requestJson(`/harness/sessions/${encodeURIComponent(sessionId)}/approvals/${encodeURIComponent(requestIdValue)}`, { method: 'POST', body: payload }),
};
