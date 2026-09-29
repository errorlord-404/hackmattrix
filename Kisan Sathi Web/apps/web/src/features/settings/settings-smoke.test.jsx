import { describe, expect, it } from 'vitest';
import { calculateFinance } from '../finance/index.jsx';
describe('settings and finance boundary smoke', () => { it('calculates without creating ledger state', () => { expect(calculateFinance({ quantity: 2, unitPrice: 10, costs: 3 })).toEqual({ gross: 20, net: 17 }); }); });
