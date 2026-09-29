import { afterEach, describe, expect, it, vi } from 'vitest';
import { farmStateApi } from './farmStateApi.js';

afterEach(() => {
  localStorage.clear();
  vi.unstubAllGlobals();
});

describe('farmer-scoped API contract', () => {
  it('sends the selected farmer identity when checking storage status', async () => {
    localStorage.setItem('kisansathi-farmer-id', 'farmer_a');
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      farmer_id: 'farmer_a', farm_state: 'available', farm_state_store: 'server_local_sqlite', reference_database: 'available',
    }), { status: 200, headers: { 'content-type': 'application/json' } }));
    vi.stubGlobal('fetch', fetchMock);

    await expect(farmStateApi.getStorageStatus()).resolves.toMatchObject({ farmer_id: 'farmer_a' });
    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8001/v1/storage-status',
      expect.objectContaining({ headers: expect.objectContaining({ 'X-Farmer-ID': 'farmer_a' }) }),
    );
  });
});
