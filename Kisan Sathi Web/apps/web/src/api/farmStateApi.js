import { requestJson } from './httpClient.js';

const get = (path) => requestJson(path);
const write = (path, body, options = {}) => requestJson(path, { method: options.method || 'POST', body, headers: options.idempotencyKey ? { 'Idempotency-Key': options.idempotencyKey } : {} });

export const farmStateApi = Object.freeze({
  dashboard: () => get('/v1/dashboard'),
  fields: () => get('/v1/fields'),
  field: (fieldId) => get(`/v1/fields/${encodeURIComponent(fieldId)}`),
  map: () => get('/v1/fields/map'),
  cropOptions: (fieldId) => get(`/v1/fields/${encodeURIComponent(fieldId)}/crop-options`),
  cropTimeline: (fieldId) => get(`/v1/fields/${encodeURIComponent(fieldId)}/timeline`),
  soil: (fieldId) => get(`/v1/fields/${encodeURIComponent(fieldId)}/soil-health`),
  observations: (fieldId) => get(`/v1/fields/${encodeURIComponent(fieldId)}/observations/latest`),
  weather: ({ lat, lon } = {}) => get(`/v1/weather?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`),
  irrigation: (fieldId) => get(`/v1/fields/${encodeURIComponent(fieldId)}/irrigation-plan`),
  recordIrrigation: (body, idempotencyKey) => write('/v1/irrigation-events', body, { idempotencyKey }),
  tasks: () => get('/v1/tasks'),
});
