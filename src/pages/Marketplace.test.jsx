import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import Marketplace from './Marketplace.jsx';

const mocks = vi.hoisted(() => ({ searchMarketplace: vi.fn(), marketplaceStatus: vi.fn(), listSeeds: vi.fn(), listFertilizers: vi.fn() }));

mocks.searchMarketplace.mockResolvedValue([{
  id: 'listing-1', listing_type: 'logistics', title: 'Wardha cold transport', provider_name: 'Demo FPO',
  description: 'Refrigerated transport for produce.', location: 'Wardha', district: 'Wardha', state: 'Maharashtra',
  price_amount: 800, price_currency: 'INR', price_unit: 'per trip', source: 'Approved directory',
  source_url: 'https://directory.example', listing_url: 'https://directory.example/listing-1', fetched_at: new Date().toISOString(),
}]);
mocks.marketplaceStatus.mockResolvedValue({ configured: true, source_count: 1, listing_types: ['logistics'], message: 'Configured.' });
mocks.listSeeds.mockResolvedValue([{ id: 'seed-1', crop: 'Paddy', variety: 'Certified local reference', duration_days: '120 days', yield_potential: 'Verify locally', disease_resistance: 'Review label', recommended_zone: 'Verify local zone' }]);
mocks.listFertilizers.mockResolvedValue([]);

vi.mock('../context/FarmDataContext.jsx', () => ({ useFarmData: () => ({ profile: { location: 'Wardha, Maharashtra' } }) }));
vi.mock('../api/referenceApi.js', () => ({ referenceApi: { searchMarketplace: mocks.searchMarketplace, marketplaceStatus: mocks.marketplaceStatus, listSeeds: mocks.listSeeds, listFertilizers: mocks.listFertilizers } }));

describe('Marketplace', () => {
  it('renders source-attributed directory records without presenting a transaction action', async () => {
    render(<MemoryRouter><Marketplace /></MemoryRouter>);
    await waitFor(() => expect(screen.getByText('Wardha cold transport')).toBeTruthy());
    expect(screen.getByText('Demo FPO')).toBeTruthy();
    expect(screen.getByText('Source listing')).toBeTruthy();
    expect(screen.queryByText(/book now|buy now/i)).toBeNull();
    expect(mocks.searchMarketplace).toHaveBeenCalledWith(expect.objectContaining({ district: 'Wardha', state: 'Maharashtra' }));
  });

  it('fills the seeds tab with the shared reference catalog and labels it safely', async () => {
    render(<MemoryRouter><Marketplace /></MemoryRouter>);
    await waitFor(() => expect(screen.getByText('Wardha cold transport')).toBeTruthy());
    fireEvent.click(screen.getAllByRole('button', { name: 'Seeds' })[0]);
    await waitFor(() => expect(screen.getByText('Certified local reference')).toBeTruthy());
    expect(screen.getByText(/not a live supplier offer/i)).toBeTruthy();
  });
});
