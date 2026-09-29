const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

export class HttpClientError extends Error {
  constructor(message, { status = 0, code = 'request_failed', retryable = true, details = null } = {}) {
    super(message);
    this.name = 'HttpClientError';
    this.status = status;
    this.code = code;
    this.retryable = retryable;
    this.details = details;
  }
}

function requestId() {
  return `web-${globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`}`;
}

function csrfToken() {
  const match = globalThis.document?.cookie?.match(/(?:^|; )kisansathi_csrf=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export async function requestJson(path, { method = 'GET', body, headers = {}, timeoutMs = 12000, signal } = {}) {
  const controller = new AbortController();
  const timer = globalThis.setTimeout(() => controller.abort(), timeoutMs);
  const merged = { Accept: 'application/json', 'X-Request-ID': requestId(), ...headers };
  if (body !== undefined) merged['Content-Type'] = 'application/json';
  if (method !== 'GET' && method !== 'HEAD') {
    const csrf = csrfToken();
    if (csrf) merged['X-CSRF-Token'] = csrf;
  }
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, { method, headers: merged, body: body === undefined ? undefined : JSON.stringify(body), credentials: 'include', signal: signal || controller.signal });
    const type = response.headers.get('content-type') || '';
    const payload = type.includes('application/json') ? await response.json() : await response.text();
    if (!response.ok) {
      const detail = payload?.detail ?? payload;
      const message = typeof detail === 'string' ? detail : detail?.message || `Request failed (${response.status})`;
      throw new HttpClientError(message, { status: response.status, code: detail?.code || 'request_failed', retryable: detail?.retryable ?? response.status >= 500, details: detail });
    }
    return payload;
  } catch (error) {
    if (error instanceof HttpClientError) throw error;
    throw new HttpClientError(controller.signal.aborted ? 'The request timed out.' : 'The standalone API could not be reached.', { code: controller.signal.aborted ? 'request_timeout' : 'network_error', details: error?.message });
  } finally {
    globalThis.clearTimeout(timer);
  }
}

export { API_BASE_URL, csrfToken, requestId };
