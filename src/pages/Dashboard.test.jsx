import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import Dashboard from './Dashboard.jsx';

vi.mock('../context/FarmDataContext.jsx', () => ({
  useFarmData: () => ({
    profile: { name: 'Ramesh' },
    fields: [{ id: 'field-1', name: 'North field', current_crop: 'Wheat', area_acres: 2 }],
    alerts: [], loading: false, error: null, refresh: vi.fn(),
  }),
}));

vi.mock('../hooks/useLanguage.jsx', () => ({ useLanguage: () => ({ language: 'en' }) }));
vi.mock('../api/referenceApi.js', () => ({ referenceApi: { marketSummary: vi.fn().mockResolvedValue([]) } }));
vi.mock('../api/farmStateApi.js', () => ({
  farmStateApi: {
    getDashboard: vi.fn().mockResolvedValue({ weather: null }),
    getSoilHealth: vi.fn().mockResolvedValue({
      status: 'within_screening_ranges', latest_test: null, recommendations: [], latest_observations: [
        { id: 'm', measurement: 'moisture', value: 40, unit: '%', source: 'soil-node', observed_at: new Date().toISOString() },
        { id: 't', measurement: 'temperature', value: 24, unit: '°C', source: 'soil-node', observed_at: new Date().toISOString() },
        { id: 'ph', measurement: 'ph', value: 6.5, unit: '', source: 'soil-node', observed_at: new Date().toISOString() },
        { id: 'ec', measurement: 'ec', value: 0.4, unit: 'mS/cm', source: 'soil-node', observed_at: new Date().toISOString() },
        { id: 'n', measurement: 'nitrogen', value: 42, unit: 'mg/kg', source: 'soil-node', observed_at: new Date().toISOString() },
        { id: 'p', measurement: 'phosphorus', value: 18, unit: 'mg/kg', source: 'soil-node', observed_at: new Date().toISOString() },
        { id: 'k', measurement: 'potassium', value: 111, unit: 'mg/kg', source: 'soil-node', observed_at: new Date().toISOString() },
      ],
    }),
    getIrrigationPlan: vi.fn().mockResolvedValue({
      status: 'not_required', target_moisture_percent: 35,
      recommendation: { what: 'Do not irrigate now', when: 'Review moisture before irrigating' },
    }),
  },
}));

describe('Dashboard', () => {
  it('surfaces all planned soil-node measurements rather than hiding NPK values', async () => {
    render(<MemoryRouter><Dashboard /></MemoryRouter>);
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Live soil telemetry' })).toBeTruthy());
    expect(screen.getByText('Moisture')).toBeTruthy();
    expect(screen.getByText('Soil temperature')).toBeTruthy();
    expect(screen.getByText('pH')).toBeTruthy();
    expect(screen.getByText('EC')).toBeTruthy();
    expect(screen.getByText('Nitrogen')).toBeTruthy();
    expect(screen.getByText('Phosphorus')).toBeTruthy();
    expect(screen.getByText('Potassium')).toBeTruthy();
    expect(screen.getByText(/Sensor values are screening inputs/i)).toBeTruthy();
  });

  it('describes moisture without leaking the aggregate soil-health status', async () => {
    render(<MemoryRouter><Dashboard /></MemoryRouter>);
    await waitFor(() => expect(screen.getByText('Moisture is at or above the irrigation target')).toBeTruthy());
    expect(screen.queryByText('within_screening_ranges')).toBeNull();
  });
});
