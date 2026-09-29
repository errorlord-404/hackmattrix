import { describe, expect, it } from 'vitest';
import { coreFarmMessages } from '../../i18n/core-farm/messages.js';

describe('core farm safety contracts', () => {
  it('keeps provider and irrigation states truthful', () => {
    expect(coreFarmMessages.unavailable).toContain('No value was invented');
    expect(coreFarmMessages.irrigationSafety).toContain('never controls physical equipment');
  });
});
