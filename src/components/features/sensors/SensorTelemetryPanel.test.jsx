import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import SensorTelemetryPanel from './SensorTelemetryPanel.jsx';
import { freshnessFor } from './sensorTelemetry.js';
import i18n from '../../../i18n/index.js';

const now = Date.now();
const observations = [
  { id: 'moisture', measurement: 'moisture', value: 31.4, unit: '%', source: 'soil-node-a17f', observed_at: new Date(now - 15 * 60 * 1000).toISOString() },
  { id: 'ph', measurement: 'ph', value: 6.8, unit: '', source: 'soil-node-a17f', observed_at: new Date(now - 8 * 60 * 60 * 1000).toISOString() },
];

function renderPanel(props = {}) {
  return render(<MemoryRouter><SensorTelemetryPanel fieldName="North field" observations={observations} {...props} /></MemoryRouter>);
}

describe('SensorTelemetryPanel', () => {
  it('shows measurements with distinct current and stale states', () => {
    renderPanel();
    expect(screen.getByRole('heading', { name: 'Live soil telemetry' })).toBeTruthy();
    expect(screen.getByText('31.4')).toBeTruthy();
    expect(screen.getByText('6.8')).toBeTruthy();
    expect(screen.getAllByText('Fresh').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Stale').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Source: soil-node-a17f')).toHaveLength(2);
  });

  it('does not present missing readings as healthy data', () => {
    renderPanel({ observations: [] });
    expect(screen.getByText('No sensor data yet')).toBeTruthy();
    expect(screen.getByText(/recommendations should treat soil measurements as unknown/i)).toBeTruthy();
  });

  it('classifies unavailable timestamps as unknown and old readings as stale', () => {
    expect(freshnessFor()).toMatchObject({ key: 'unknown' });
    expect(freshnessFor(new Date(now - 7 * 60 * 60 * 1000).toISOString(), now)).toMatchObject({ key: 'stale' });
  });

  it('keeps the telemetry labels understandable in Hindi', async () => {
    await i18n.changeLanguage('hi');
    renderPanel();
    expect(screen.getAllByRole('heading', { name: 'लाइव मिट्टी टेलीमेट्री' }).length).toBeGreaterThan(0);
    expect(screen.getAllByText('पीएच').length).toBeGreaterThan(0);
    await i18n.changeLanguage('en');
  });
});
