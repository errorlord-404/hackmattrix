import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import MachineryRentals from './MachineryRentals.jsx';

const mocks = vi.hoisted(() => ({
  listMachineryRentals: vi.fn(),
  nearbyMachineryRentals: vi.fn(),
}));

mocks.listMachineryRentals.mockResolvedValue([{
  id: 'rental-1', name: 'Tractor — Wardha CHC', category: 'tractor', provider_name: 'Wardha CHC',
  location: 'Wardha, Maharashtra', state: 'Maharashtra', source: 'Government of India FARMS CHC public feed',
  source_url: 'https://agrimachinery.nic.in/Index/farmsapp', fetched_at: new Date().toISOString(),
  hourly_rate: 800, availability_status: 'published',
}]);
mocks.nearbyMachineryRentals.mockResolvedValue([]);

vi.mock('../context/FarmDataContext.jsx', () => ({ useFarmData: () => ({
  profile: { location: 'Pune, Maharashtra', latitude: 18.52, longitude: 73.86 },
  fields: [{ id: 'field-1', name: 'Lower Field', centroid_lat: 18.52, centroid_lon: 73.86 }],
}) }));
vi.mock('../hooks/useLanguage.jsx', () => ({ useLanguage: () => ({ language: 'en' }) }));
vi.mock('../api/referenceApi.js', () => ({ referenceApi: mocks }));

describe('MachineryRentals', () => {
  it('switches from an empty local radius to the live all-India directory', async () => {
    render(<MachineryRentals />);
    await waitFor(() => expect(screen.getByText('No machinery records in this search')).toBeTruthy());
    fireEvent.click(screen.getByRole('button', { name: 'All India' }));
    await waitFor(() => expect(screen.getByText('Tractor — Wardha CHC')).toBeTruthy());
    expect(mocks.listMachineryRentals).toHaveBeenCalledWith({ category: undefined });
    expect(screen.getByText('Nationwide view')).toBeTruthy();
  });
});
