import { describe, expect, it } from 'vitest';
import { UNKNOWN_CROP, cropRoutingState } from './cropRouting.js';

describe('cropRoutingState', () => {
  it('requires explicit farmer confirmation before routing', () => {
    expect(cropRoutingState('tomato', false).status).toBe('needs_confirmation');
  });

  it('does not route when the farmer does not know the crop', () => {
    expect(cropRoutingState(UNKNOWN_CROP, true).status).toBe('unknown_crop');
  });

  it('permits a confirmed crop to continue to a future specialist', () => {
    expect(cropRoutingState('rice', true).status).toBe('ready');
  });
});
