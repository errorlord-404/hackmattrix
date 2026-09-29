import { afterEach, describe, expect, it, vi } from 'vitest';
import { loadSession } from '../../api/authClient.js';

afterEach(() => vi.restoreAllMocks());

describe('server-owned auth gate contract', () => {
  it('loads only actor-safe session status with credentials', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: true, status: 200, headers: new Headers({ 'content-type': 'application/json' }), json: async () => ({ authenticated: true, actor: { roles: ['farmer'] } }) });
    const result = await loadSession();
    expect(result.authenticated).toBe(true);
    expect(fetchMock.mock.calls[0][1].credentials).toBe('include');
    expect(JSON.stringify(result)).not.toContain('farmer_id');
  });
});
