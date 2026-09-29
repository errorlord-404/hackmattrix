const DEFAULT_TIMEOUT_MS = 12_000;
const CHAT_TIMEOUT_MS = 45_000;
const MAX_STREAM_BYTES = 512 * 1024;
const MAX_STREAM_EVENTS = 120;
const SESSION_STORAGE_KEY = 'kisan-sathi-web-session-id';
let memorySessionId = null;

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(message, { status = 0, code = 'request_failed', retryable = true, details = null } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.retryable = retryable;
    this.details = details;
  }
}

function requestUrl(path) {
  return `${API_BASE_URL}${path}`;
}

function requestId() {
  return `web-${globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`}`;
}

function csrfToken() {
  const match = globalThis.document?.cookie?.match(/(?:^|; )kisansathi_csrf=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

function newId(prefix) {
  const uuid = globalThis.crypto?.randomUUID?.();
  return uuid ? `${prefix}-${uuid}` : `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function getSessionId() {
  try {
    const existing = globalThis.sessionStorage?.getItem(SESSION_STORAGE_KEY);
    if (existing) return existing;
    if (memorySessionId) return memorySessionId;
    const created = memorySessionId || newId('session');
    memorySessionId = created;
    globalThis.sessionStorage?.setItem(SESSION_STORAGE_KEY, created);
    return created;
  } catch {
    return memorySessionId || (memorySessionId = newId('session'));
  }
}

export function createTurnId() {
  return newId('turn');
}

export async function requestJson(path, options = {}) {
  const { method = 'GET', body, headers = {}, timeoutMs = DEFAULT_TIMEOUT_MS } = options;
  const controller = new AbortController();
  const timer = globalThis.setTimeout(() => controller.abort(), timeoutMs);
  const requestHeaders = { Accept: 'application/json', 'X-Request-ID': requestId(), ...headers };
  if (body != null) requestHeaders['Content-Type'] = 'application/json';
  if (method !== 'GET' && method !== 'HEAD') {
    const csrf = csrfToken();
    if (csrf) requestHeaders['X-CSRF-Token'] = csrf;
  }

  try {
    const response = await fetch(requestUrl(path), {
      method,
      headers: requestHeaders,
      credentials: 'include',
      body: body == null ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });
    const contentType = response.headers.get('content-type') || '';
    const payload = contentType.includes('application/json') ? await response.json() : await response.text();
    if (!response.ok) {
      const detail = payload?.detail ?? payload;
      const message = typeof detail === 'string' ? detail : detail?.message || `Request failed (${response.status})`;
      throw new ApiError(message, {
        status: response.status,
        code: detail?.code || 'request_failed',
        retryable: detail?.retryable ?? response.status >= 500,
        details: detail,
      });
    }
    return payload;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(controller.signal.aborted ? 'The request timed out.' : 'The standalone API could not be reached.', {
      code: controller.signal.aborted ? 'request_timeout' : 'network_error',
      details: error?.message,
    });
  } finally {
    globalThis.clearTimeout(timer);
  }
}

function parsePayload(raw) {
  const text = raw.trim();
  if (!text || text === '[DONE]') return { done: text === '[DONE]', value: null };
  try {
    return { done: false, value: JSON.parse(text) };
  } catch {
    return null;
  }
}

/** Read standalone NDJSON; accept `data:` lines for SSE-compatible proxies. */
export async function readNdjsonStream(response, onEvent, { maxBytes = MAX_STREAM_BYTES, maxEvents = MAX_STREAM_EVENTS } = {}) {
  if (!response.ok) throw new ApiError(`Chat stream failed (${response.status})`, { status: response.status });
  if (!response.body?.getReader) throw new ApiError('Streaming is not available in this browser.', { code: 'stream_unsupported', retryable: false });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let pendingSseLines = [];
  let bytesRead = 0;
  let eventCount = 0;
  let done = false;

  const emit = (raw) => {
    const parsed = parsePayload(raw);
    if (!parsed) throw new ApiError('The chat stream contained invalid JSON.', { code: 'invalid_stream', retryable: false });
    if (parsed.done) { done = true; return; }
    eventCount += 1;
    if (eventCount > maxEvents) throw new ApiError('The chat stream contained too many events.', { code: 'stream_too_many_events', retryable: false });
    onEvent(parsed.value);
  };

  const flushSse = () => {
    if (!pendingSseLines.length) return;
    const combined = pendingSseLines.join('\n');
    pendingSseLines = [];
    emit(combined);
  };

  const consume = (chunk) => {
    buffer += decoder.decode(chunk, { stream: true });
    bytesRead += chunk.byteLength;
    if (bytesRead > maxBytes) throw new ApiError('The chat stream exceeded its safety limit.', { code: 'stream_too_large', retryable: false });

    const lines = buffer.split(/\r?\n/);
    buffer = lines.pop() || '';
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) { flushSse(); continue; }
      if (trimmed.startsWith(':')) continue;
      if (trimmed.startsWith('data:')) {
        const data = trimmed.slice(5).trimStart();
        if (data === '[DONE]') { pendingSseLines = []; emit(data); continue; }
        if (parsePayload(data)) emit(data);
        else pendingSseLines.push(data);
        continue;
      }
      if (pendingSseLines.length) flushSse();
      emit(trimmed);
    }
  };

  while (!done) {
    const { done: streamDone, value } = await reader.read();
    if (streamDone) break;
    consume(value);
  }
  if (!done) {
    buffer += decoder.decode();
    if (buffer.trim()) {
      if (buffer.trim().startsWith('data:')) pendingSseLines.push(buffer.trim().slice(5).trimStart());
      else emit(buffer.trim());
    }
    flushSse();
  }
  return { bytesRead, eventCount };
}

export async function streamChat({ messages, sessionId = getSessionId(), turnId = createTurnId(), toolNames = null, onEvent }) {
  const controller = new AbortController();
  const timer = globalThis.setTimeout(() => controller.abort(), CHAT_TIMEOUT_MS);
  const body = { messages, session_id: sessionId, turn_id: turnId };
  if (toolNames?.length) body.tool_names = toolNames;

  try {
    const response = await fetch(requestUrl('/chat/stream'), {
      method: 'POST',
      headers: {
        Accept: 'application/x-ndjson, text/event-stream',
        'Content-Type': 'application/json',
        'X-Session-ID': sessionId,
        'X-Request-ID': requestId(),
        ...(csrfToken() ? { 'X-CSRF-Token': csrfToken() } : {}),
      },
      credentials: 'include',
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    return await readNdjsonStream(response, onEvent, { maxBytes: MAX_STREAM_BYTES, maxEvents: MAX_STREAM_EVENTS });
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(controller.signal.aborted ? 'The chat stream timed out.' : 'The chat stream was interrupted.', {
      code: controller.signal.aborted ? 'stream_timeout' : 'stream_network_error',
    });
  } finally {
    globalThis.clearTimeout(timer);
  }
}

export const api = {
  healthz: () => requestJson('/healthz'),
  readyz: () => requestJson('/readyz'),
  tools: () => requestJson('/tools'),
  visionCapabilities: () => requestJson('/v1/vision/capabilities'),
  cropDiseasePrototype: () => requestJson('/v1/crop-disease/prototype'),
  streamChat,
};

export const apiLimits = { DEFAULT_TIMEOUT_MS, CHAT_TIMEOUT_MS, MAX_STREAM_BYTES, MAX_STREAM_EVENTS };
