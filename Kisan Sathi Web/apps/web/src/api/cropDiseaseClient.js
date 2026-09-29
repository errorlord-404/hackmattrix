import { API_BASE_URL, csrfToken, requestId } from './httpClient.js';

export async function fetchCropDiseasePrototype(signal) {
  const response = await fetch(`${API_BASE_URL}/v1/crop-disease/prototype`, {
    credentials: 'include',
    headers: { Accept: 'application/json', 'X-Request-ID': requestId() },
    signal,
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload?.detail?.message || 'prototype model profile unavailable');
  return payload;
}

export async function predictCropDisease(imageBlob, { crop, signal } = {}) {
  const headers = {
    Accept: 'application/json',
    'Content-Type': imageBlob.type || 'application/octet-stream',
    'X-Request-ID': requestId(),
    ...(crop ? { 'X-Crop-Name': crop } : {}),
  };
  const csrf = csrfToken();
  if (csrf) headers['X-CSRF-Token'] = csrf;
  const response = await fetch(`${API_BASE_URL}/v1/crop-disease/predict?crop=${encodeURIComponent(crop || '')}`, {
    method: 'POST', credentials: 'include', headers, body: imageBlob, signal,
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload?.detail?.message || 'crop screening failed');
  return payload;
}
