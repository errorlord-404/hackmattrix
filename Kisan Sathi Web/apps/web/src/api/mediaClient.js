import { API_BASE_URL, csrfToken, requestId } from './httpClient.js';

export const MEDIA_LIMITS = Object.freeze({ imageBytes: 10 * 1024 * 1024, audioBytes: 10 * 1024 * 1024 });

export class MediaClientError extends Error {
  constructor(message, { status = 0, code = 'media_request_failed', retryable = true, details = null } = {}) {
    super(message);
    this.name = 'MediaClientError';
    this.status = status;
    this.code = code;
    this.retryable = retryable;
    this.details = details;
  }
}

export function validateImageFile(file) {
  if (!file || !['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) return { ok: false, code: 'image_type_invalid', message: 'Choose a JPEG, PNG, or WebP image.' };
  if (file.size > MEDIA_LIMITS.imageBytes) return { ok: false, code: 'image_too_large', message: 'That image exceeds the 10 MB limit.' };
  return { ok: true };
}

function parsePayload(response, payload) {
  if (response.ok) return payload;
  const detail = payload?.detail ?? payload;
  throw new MediaClientError(detail?.message || `Media request failed (${response.status})`, { status: response.status, code: detail?.code || 'media_request_failed', retryable: detail?.retryable ?? response.status >= 500, details: detail });
}

export async function uploadMedia(kind, blob, { fieldId, crop, language = 'en-IN', idempotencyKey, signal } = {}) {
  if (!blob) throw new MediaClientError('Media content is required.', { code: 'media_empty', retryable: false });
  const isImage = kind === 'image';
  const limit = isImage ? MEDIA_LIMITS.imageBytes : MEDIA_LIMITS.audioBytes;
  if (blob.size > limit) throw new MediaClientError('Media exceeds the configured upload limit.', { code: 'media_too_large', status: 413, retryable: false });
  const headers = { Accept: 'application/json', 'Content-Type': blob.type || (isImage ? 'application/octet-stream' : 'audio/webm'), 'X-Request-ID': requestId() };
  if (idempotencyKey) headers['Idempotency-Key'] = idempotencyKey;
  if (fieldId) headers['X-Field-ID'] = fieldId;
  if (crop) headers['X-Crop-Name'] = crop;
  if (!isImage) headers['Accept-Language'] = language;
  const csrf = csrfToken();
  if (csrf) headers['X-CSRF-Token'] = csrf;
  const response = await fetch(`${API_BASE_URL}/v1/media/${kind}`, { method: 'POST', headers, body: blob, credentials: 'include', signal });
  const contentType = response.headers.get('content-type') || '';
  const payload = contentType.includes('application/json') ? await response.json() : await response.text();
  return parsePayload(response, payload);
}
