import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import DeviceOnboarding from './DeviceOnboarding.jsx';

const mocks = vi.hoisted(() => ({ latest: vi.fn(), history: vi.fn(), devices: vi.fn() }));
mocks.latest.mockResolvedValue([{ id: 'm1', measurement: 'moisture', value: 31, unit: '%', observed_at: new Date().toISOString(), source: 'soil-node-a17f' }]);
mocks.history.mockResolvedValue([{ id: 'm0', measurement: 'moisture', value: 28, unit: '%', observed_at: new Date(Date.now() - 3600000).toISOString(), source: 'soil-node-a17f' }, { id: 'm1', measurement: 'moisture', value: 31, unit: '%', observed_at: new Date().toISOString(), source: 'soil-node-a17f' }]);
mocks.devices.mockResolvedValue([{ device_id: 'soil-node-a17f', field_id: 'field-1', status: 'fresh', last_received_at: new Date().toISOString(), firmware_version: '0.1.0', rejection_reason: null }]);
vi.mock('../context/FarmDataContext.jsx', () => ({ useFarmData: () => ({ loading: false, fields: [{ id: 'field-1', name: 'North field', current_crop: 'Wheat' }] }) }));
vi.mock('../api/farmStateApi.js', () => ({ farmStateApi: { getLatestObservations: mocks.latest, getObservationHistory: mocks.history, listDeviceHealth: mocks.devices } }));

describe('DeviceOnboarding', () => {
  it('shows an unknown state until a field is assigned, then renders sourced history', async () => {
    render(<MemoryRouter><DeviceOnboarding /></MemoryRouter>);
    expect(screen.getByText('Assign a field to check its latest reading.')).toBeTruthy();
    const select = screen.getByLabelText('Field');
    select.value = 'field-1'; select.dispatchEvent(new Event('change', { bubbles: true }));
    await waitFor(() => expect(screen.getByLabelText('Moisture history chart')).toBeTruthy());
    expect(mocks.history).toHaveBeenCalledWith('field-1');
    expect(screen.getByText('Gateway fresh: soil-node-a17f')).toBeTruthy();
  });
});
