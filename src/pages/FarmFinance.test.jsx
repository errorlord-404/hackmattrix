import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import FarmFinance from './FarmFinance.jsx';

const mocks = vi.hoisted(() => ({
  listLedgerEntries: vi.fn(),
  getLedgerSummary: vi.fn(),
  createLedgerEntry: vi.fn(),
  updateLedgerEntryStatus: vi.fn(),
}));

vi.mock('../context/FarmDataContext.jsx', () => ({
  useFarmData: () => ({
    fields: [{ id: 'field-1', name: 'North field', current_crop: 'tomato' }],
    profile: { farmer_id: 'farmer-1', location: 'Pune, Maharashtra' },
  }),
}));
vi.mock('../api/farmStateApi.js', () => ({ farmStateApi: mocks }));
vi.mock('../api/referenceApi.js', () => ({ referenceApi: { compareMandis: vi.fn() } }));
vi.mock('../hooks/useLanguage.jsx', () => ({ useLanguage: () => ({ language: 'en' }) }));

describe('FarmFinance', () => {
  it('loads persisted records and saves a farmer-confirmed INR expense to the API', async () => {
    mocks.listLedgerEntries.mockResolvedValue([{ id: 'ledger-1', entry_type: 'expense', category: 'Seed', title: 'Tomato seed', amount_inr: 820, occurred_at: '2026-09-07', crop_name: 'tomato' }]);
    mocks.getLedgerSummary.mockResolvedValue({ income_inr: 0, expense_inr: 820, balance_inr: -820, active_entry_count: 1 });
    mocks.createLedgerEntry.mockResolvedValue({ id: 'ledger-2' });
    render(<FarmFinance />);
    await waitFor(() => expect(screen.getByText('Tomato seed')).toBeTruthy());
    fireEvent.click(screen.getByRole('button', { name: 'Add transaction' }));
    fireEvent.change(screen.getByPlaceholderText('Description'), { target: { value: 'Field labour' } });
    fireEvent.change(screen.getByPlaceholderText('Amount (₹)'), { target: { value: '500' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save ledger record' }));
    await waitFor(() => expect(mocks.createLedgerEntry).toHaveBeenCalledWith(expect.objectContaining({
      entry_type: 'expense', title: 'Field labour', amount_inr: 500, source: 'farmer_confirmed:manual_ui',
    })));
  });
});
