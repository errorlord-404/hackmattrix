import { requestJson } from './httpClient.js';

const get = (path) => requestJson(path);
const post = (path, body, idempotencyKey) => requestJson(path, { method: 'POST', body, headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {} });

export const referenceApi = Object.freeze({
  market: (crop) => get(crop ? `/market-prices/by-crop/${encodeURIComponent(crop)}` : '/market-prices/summary'),
  marketHistory: (crop) => get(`/market-prices/history?crop=${encodeURIComponent(crop)}`),
  schemes: (state) => get(state ? `/gov-schemes/by-state/${encodeURIComponent(state)}` : '/gov-schemes'),
  eligibility: (body) => post('/gov-schemes/check-eligibility', body),
  machinery: (filters = {}) => get(`/machinery-rentals?${new URLSearchParams(filters).toString()}`),
  marketplace: (filters = {}) => get(`/marketplace/listings?${new URLSearchParams(filters).toString()}`),
  reports: () => get('/v1/reports'),
  createReport: (body, idempotencyKey) => post('/v1/reports', body, idempotencyKey),
  profile: () => get('/v1/profile'),
  updateProfile: (body, idempotencyKey) => requestJson('/v1/profile', { method: 'PUT', body, headers: { 'Idempotency-Key': idempotencyKey } }),
  alerts: () => get('/v1/alerts'),
});

export function referenceSafety(text) {
  return String(text || '').replace(/<[^>]*>/g, '').slice(0, 2000);
}
