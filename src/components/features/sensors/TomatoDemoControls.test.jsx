import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import TomatoDemoControls from './TomatoDemoControls.jsx';

describe('TomatoDemoControls', () => {
  it('stays hidden when the backend has not enabled demo mode', () => {
    const { container } = render(<TomatoDemoControls status={{ enabled: false }} />);
    expect(container.firstChild).toBeNull();
  });

  it('starts scenarios and exposes simulated irrigation without implying hardware control', () => {
    const onStart = vi.fn();
    const onIrrigate = vi.fn();
    render(<TomatoDemoControls status={{ enabled: true, running: true, scenario: 'water-stress', tick_count: 2 }} scenario="water-stress" onScenarioChange={vi.fn()} onStart={onStart} onIrrigate={onIrrigate} onStop={vi.fn()} />);
    expect(screen.getByText('Demo-only soil values change every 15 seconds. No pump or hardware is controlled.')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: /restart scenario/i }));
    fireEvent.click(screen.getByRole('button', { name: /simulate irrigation/i }));
    expect(onStart).toHaveBeenCalledTimes(1);
    expect(onIrrigate).toHaveBeenCalledTimes(1);
  });

  it('exposes visibly labelled forecast fixtures for a repeatable rain demo', () => {
    const onForecastFixture = vi.fn();
    render(<TomatoDemoControls status={{ enabled: true, running: true, scenario: 'water-stress', tick_count: 2 }} scenario="water-stress" onScenarioChange={vi.fn()} onStart={vi.fn()} onIrrigate={vi.fn()} onStop={vi.fn()} onForecastFixture={onForecastFixture} />);
    expect(screen.getByText(/explicitly simulated weather/i)).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: /heavy rain/i }));
    expect(onForecastFixture).toHaveBeenCalledWith('heavy-rain');
  });
});
