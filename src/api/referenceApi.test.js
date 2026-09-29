import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getReferenceCacheMeta, referenceApi } from './referenceApi.js';

function response(payload) {
  return { ok: true, headers: { get: (name) => name === 'content-type' ? 'application/json' : 'request-test' }, json: async () => payload, text: async () => JSON.stringify(payload) };
}

describe('reference cache', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('serves a marked last-known response when the reference backend becomes unavailable', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(response([{ id: 'scheme-1', name: 'Demo scheme' }]))
      .mockRejectedValueOnce(new Error('offline'));
    const first = await referenceApi.listSchemes();
    expect(getReferenceCacheMeta(first).mode).toBe('live');
    const second = await referenceApi.listSchemes();
    expect(second).toEqual(first);
    expect(getReferenceCacheMeta(second).mode).toBe('stale_cache');
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
