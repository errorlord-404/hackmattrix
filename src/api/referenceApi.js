import { apiRequest, queryString, REFERENCE_API_URL } from './client.js';

const request = (path, options = {}) => apiRequest(REFERENCE_API_URL, path, options);
const CACHE_PREFIX = 'kisansathi:reference-cache:v1:';

function annotate(payload, meta) {
  if (!payload || typeof payload !== 'object') return payload;
  try { Object.defineProperty(payload, '__cacheMeta', { value: meta, enumerable: false, configurable: true }); } catch { /* optional metadata */ }
  return payload;
}

function readCache(key) {
  try {
    const raw = globalThis.localStorage?.getItem(`${CACHE_PREFIX}${key}`);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed?.version === 1 && parsed.savedAt && parsed.payload != null ? parsed : null;
  } catch { return null; }
}

async function cachedRequest(path, options = {}) {
  const key = options.cacheKey || path;
  try {
    const payload = await request(path, options);
    const savedAt = Date.now();
    try {
      const encoded = JSON.stringify({ version: 1, savedAt, payload });
      if (encoded.length <= 1024 * 1024) globalThis.localStorage?.setItem(`${CACHE_PREFIX}${key}`, encoded);
    } catch { /* storage is optional */ }
    return annotate(payload, { mode: 'live', savedAt });
  } catch (error) {
    const cached = readCache(key);
    if (!cached) throw error;
    return annotate(cached.payload, { mode: 'stale_cache', savedAt: cached.savedAt, ageMs: Math.max(0, Date.now() - cached.savedAt), errorCode: error.code });
  }
}

export function getReferenceCacheMeta(value) { return value?.__cacheMeta || null; }
export const referenceApi = {
  getBackendHealth: () => request('/health'),
  listCrops: () => cachedRequest('/crops'), marketSummary: (filters) => cachedRequest(`/market-prices/summary${queryString(filters)}`),
  marketHistory: (filters) => cachedRequest(`/market-prices/history${queryString(filters)}`), marketTrend: (filters) => cachedRequest(`/market-prices/trend${queryString(filters)}`),
  compareMandis: (crop, assumptions) => request(`/market-prices/compare/${encodeURIComponent(crop)}${queryString(assumptions)}`),
  compareSaleRoutes: (body) => request('/market-prices/compare-routes', { method: 'POST', body }),
  compareMspWithMarket: (crop) => request(`/msp/compare-market${queryString({ crop })}`),
  listSchemes: () => cachedRequest('/gov-schemes'),
  listSchemesByState: (state) => cachedRequest(`/gov-schemes/by-state/${encodeURIComponent(state)}`),
  listSeeds: () => cachedRequest('/seeds'),
  listFertilizers: () => cachedRequest('/fertilizer'),
  listMachineryRentals: (filters) => cachedRequest(`/machinery-rentals${queryString(filters)}`),
  nearbyMachineryRentals: (filters) => cachedRequest(`/machinery-rentals/nearby${queryString(filters)}`),
  marketplaceStatus: () => cachedRequest('/marketplace/status'),
  searchMarketplace: (filters) => cachedRequest(`/marketplace/listings${queryString(filters)}`),
  nearbyMarketplace: (filters) => cachedRequest(`/marketplace/nearby${queryString(filters)}`),
};
