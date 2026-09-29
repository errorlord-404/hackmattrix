import { afterEach, describe, expect, it, vi } from 'vitest';
import { getFarmerId } from './client.js';

describe('farmer identity selection', () => {
  afterEach(() => { vi.unstubAllGlobals(); localStorage.clear(); });

  it('uses the launcher-bound farmer in the desktop even if browser storage differs', () => {
    localStorage.setItem('kisansathi-farmer-id', 'someone-else');
    vi.stubGlobal('kisanHarness', { farmerId: 'bound-farmer' });
    expect(getFarmerId()).toBe('bound-farmer');
  });

  it('uses the Electron main-process backend for both farm and reference requests', async () => {
    vi.stubGlobal('kisanHarness', { farmerId: 'bound-farmer', backendUrl: 'http://127.0.0.1:8000/' });
    vi.resetModules();
    const { FARM_STATE_API_URL, REFERENCE_API_URL } = await import('./client.js');
    expect(FARM_STATE_API_URL).toBe('http://127.0.0.1:8000');
    expect(REFERENCE_API_URL).toBe('http://127.0.0.1:8000');
  });
});
