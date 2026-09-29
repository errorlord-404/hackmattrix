import { describe, expect, it } from 'vitest';
import { referenceApi } from '../../api/referenceApi.js';
describe('report smoke', () => { it('uses a server-owned reports route', () => { expect(referenceApi.reports.toString()).toContain('/v1/reports'); }); });
