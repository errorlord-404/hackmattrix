import { act, cleanup, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { FarmDataProvider, useFarmData } from './FarmDataContext.jsx';

const api = vi.hoisted(() => ({
  getProfile: vi.fn(),
  listFields: vi.fn(),
  listMapFields: vi.fn(),
  getWeatherAlerts: vi.fn(),
  listAlerts: vi.fn(),
  updateProfile: vi.fn(),
  createField: vi.fn(),
  updateField: vi.fn(),
  updateAlert: vi.fn(),
}));

vi.mock('../api/farmStateApi.js', () => ({ farmStateApi: api }));

function AlertCount() {
  const { alerts } = useFarmData();
  return <span data-testid="alert-count">{alerts.length}</span>;
}

describe('FarmDataProvider forecast alert refresh', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    api.getProfile.mockResolvedValue({ name: 'Asha' });
    api.listFields.mockResolvedValue([{ id: 'field-1', name: 'North field' }]);
    api.listMapFields.mockResolvedValue([]);
    api.getWeatherAlerts.mockResolvedValue([]);
    api.listAlerts.mockResolvedValue([{ id: 'forecast-1', title: 'Rain likely in forecast window' }]);
    window.kisanHarness = { notifications: { showAlert: vi.fn().mockResolvedValue({ shown: true }) } };
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
    vi.clearAllMocks();
    Reflect.deleteProperty(window, 'kisanHarness');
  });

  it('checks every field at startup and again every 15 minutes while Electron is open', async () => {
    render(<FarmDataProvider><AlertCount /></FarmDataProvider>);

    await act(async () => { await Promise.resolve(); });
    expect(api.getWeatherAlerts).toHaveBeenCalledWith('field-1');
    expect(screen.getByTestId('alert-count').textContent).toBe('1');

    await act(async () => { await vi.advanceTimersByTimeAsync(15 * 60 * 1000); });
    expect(api.getWeatherAlerts).toHaveBeenCalledTimes(2);
    expect(api.listAlerts).toHaveBeenCalledWith('open');
  });

  it('shows a native alert only for newly discovered open alerts while Electron remains open', async () => {
    render(<FarmDataProvider><AlertCount /></FarmDataProvider>);

    await act(async () => { await Promise.resolve(); });
    expect(window.kisanHarness.notifications.showAlert).not.toHaveBeenCalled();
    api.listAlerts.mockResolvedValue([
      { id: 'forecast-1', title: 'Rain likely in forecast window' },
      { id: 'forecast-2', title: 'Strong wind risk', message: 'Review your field tasks before the forecast window.' },
    ]);

    await act(async () => { await vi.advanceTimersByTimeAsync(15 * 60 * 1000); });

    expect(window.kisanHarness.notifications.showAlert).toHaveBeenCalledWith({
      title: 'Strong wind risk', message: 'Review your field tasks before the forecast window.',
    });
  });

  it('does not show a native alert when the profile has disabled notifications', async () => {
    api.getProfile.mockResolvedValue({ name: 'Asha', notification_preferences: { enabled: false } });
    render(<FarmDataProvider><AlertCount /></FarmDataProvider>);

    await act(async () => { await Promise.resolve(); });
    api.listAlerts.mockResolvedValue([
      { id: 'forecast-1', title: 'Rain likely in forecast window' },
      { id: 'forecast-2', title: 'Strong wind risk', message: 'Review your field tasks before the forecast window.' },
    ]);

    await act(async () => { await vi.advanceTimersByTimeAsync(15 * 60 * 1000); });

    expect(window.kisanHarness.notifications.showAlert).not.toHaveBeenCalled();
  });
});
