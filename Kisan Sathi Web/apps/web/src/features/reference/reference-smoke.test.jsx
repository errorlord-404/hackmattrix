import { describe, expect, it } from 'vitest';
import { referenceSafety } from '../../api/referenceApi.js';
import { referenceMessages } from '../../i18n/reference/messages.js';
describe('reference safety smoke', () => { it('renders external text as inert bounded data', () => { expect(referenceSafety('<script>bad</script> Market')).toBe('bad Market'); expect(referenceMessages.schemeSafety).toContain('no submission'); }); });
