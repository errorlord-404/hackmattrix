import { describe, expect, it, vi } from 'vitest';
import { uploadMedia, validateImageFile } from '../../../api/mediaClient.js';

describe('media browser contracts', () => {
  it('rejects unsupported or oversized images before network use', () => {
    expect(validateImageFile({ type: 'application/pdf', size: 10 })).toMatchObject({ ok: false, code: 'image_type_invalid' });
    expect(validateImageFile({ type: 'image/png', size: 11 * 1024 * 1024 })).toMatchObject({ ok: false, code: 'image_too_large' });
  });

  it('sends media with server session credentials and no browser identity selector', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: true, status: 200, headers: new Headers({ 'content-type': 'application/json' }), json: async () => ({ status: 'inconclusive', diagnosis: null }) });
    const result = await uploadMedia('image', new Blob(['png'], { type: 'image/png' }), { fieldId: 'field-1', crop: 'rice', idempotencyKey: 'image-test-1' });
    expect(result.status).toBe('inconclusive');
    const [, options] = fetchMock.mock.calls[0];
    expect(options.credentials).toBe('include');
    expect(options.headers['X-Field-ID']).toBe('field-1');
    expect(JSON.stringify(options.headers)).not.toContain('farmer');
  });
});
