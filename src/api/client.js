const DEFAULT_TIMEOUT_MS = 12000;

const desktopBackendUrl = window.kisanHarness?.backendUrl;
// Electron supplies this value from its main process. The browser fallback is
// deliberately the same demo API so a Vite-only session does not point at a
// different, usually inactive, port.
export const FARM_STATE_API_URL = (desktopBackendUrl || import.meta.env.VITE_FARM_STATE_API_URL || 'http://127.0.0.1:8001').replace(/\/$/, '');
export const REFERENCE_API_URL = (desktopBackendUrl || import.meta.env.VITE_REFERENCE_API_URL || 'http://127.0.0.1:8001').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(message, { status = 0, code = 'request_failed', details = null, requestId = null, retryable = true } = {}) {
    super(message);
    this.name = 'ApiError'; this.status = status; this.code = code; this.details = details; this.requestId = requestId; this.retryable = retryable;
  }
}

export function getFarmerId() {
  if (window.kisanHarness) return window.kisanHarness.farmerId || 'demo';
  return localStorage.getItem('kisansathi-farmer-id') || import.meta.env.VITE_DEMO_FARMER_ID || 'demo';
}

export async function apiRequest(baseUrl, path, options = {}) {
  const { method = 'GET', body, headers = {}, farmerScoped = false, timeoutMs = DEFAULT_TIMEOUT_MS } = options;
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  const requestId = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`;
  const requestHeaders = { Accept: 'application/json', 'X-Request-ID': requestId, ...headers };
  if (farmerScoped) requestHeaders['X-Farmer-ID'] = getFarmerId();
  const formBody = body instanceof FormData || body instanceof Blob;
  if (body != null && !formBody) requestHeaders['Content-Type'] = 'application/json';
  try {
    const response = await fetch(`${baseUrl}${path}`, {
      method, headers: requestHeaders, body: body == null ? undefined : formBody ? body : JSON.stringify(body), signal: controller.signal,
    });
    const contentType = response.headers.get('content-type') || '';
    const payload = contentType.includes('application/json') ? await response.json() : await response.text();
    if (!response.ok) {
      const detail = payload?.detail ?? payload;
      throw new ApiError(typeof detail === 'string' ? detail : detail?.message || `Request failed (${response.status})`, {
        status: response.status, code: detail?.code || 'request_failed', details: detail,
        requestId: response.headers.get('X-Request-ID') || requestId,
        retryable: detail?.retryable ?? response.status >= 500,
      });
    }
    return payload;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(controller.signal.aborted ? 'The request timed out.' : 'The backend service is unavailable.', {
      code: controller.signal.aborted ? 'request_aborted' : 'service_unavailable', details: error?.message,
      retryable: true,
    });
  } finally { window.clearTimeout(timer); }
}

export function queryString(values) {
  const query = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => { if (value !== undefined && value !== null && value !== '') query.set(key, value); });
  const result = query.toString(); return result ? `?${result}` : '';
}

