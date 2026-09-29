import { API_BASE_URL, requestJson } from './httpClient.js';

export async function fetchVisionDescriptor(signal) {
  return requestJson('/v1/vision/descriptor', { signal });
}

export async function requestServerVision(imageBlob, { crop, signal } = {}) {
  const headers = { 'Content-Type': imageBlob.type || 'application/octet-stream' };
  if (crop) headers['X-Crop-Name'] = crop;
  const response = await fetch(`${API_BASE_URL}/v1/vision/fallback`, { method: 'POST', headers, body: imageBlob, credentials: 'include', signal });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload?.detail?.message || 'server vision fallback failed');
  return payload;
}

export async function finalizeVisionCandidate({ uploadId, contentSha256, releaseId, preprocessingVersion, descriptorSignature, descriptorExpiresAt, candidate, fieldId, crop, idempotencyKey, signal }) {
  return requestJson('/v1/vision/finalize', {
    method: 'POST',
    signal,
    headers: {
      ...(fieldId ? { 'X-Field-ID': fieldId } : {}),
      ...(crop ? { 'X-Crop-Name': crop } : {}),
      ...(idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {}),
    },
    body: {
      upload_id: uploadId,
      content_sha256: contentSha256,
      release_id: releaseId,
      preprocessing_version: preprocessingVersion,
      descriptor_signature: descriptorSignature,
      descriptor_expires_at: descriptorExpiresAt,
      candidate: candidate || {},
    },
  });
}

export function screenInWorker(worker, request, { timeoutMs = 8000 } = {}) {
  return new Promise((resolve) => {
    const timer = globalThis.setTimeout(() => {
      worker.postMessage({ type: 'cancel' });
      resolve({ status: 'fallback', reason: 'browser_timeout', target: 'server' });
    }, timeoutMs);
    worker.onmessage = ({ data }) => {
      if (data?.type !== 'candidate' && data?.type !== 'fallback') return;
      globalThis.clearTimeout(timer);
      resolve(data.type === 'candidate' ? { status: 'candidate', ...data } : { status: 'fallback', target: 'server', ...data });
    };
    worker.onerror = () => {
      globalThis.clearTimeout(timer);
      resolve({ status: 'fallback', reason: 'worker_crash', target: 'server' });
    };
    worker.postMessage({ type: 'screen', ...request });
  });
}
