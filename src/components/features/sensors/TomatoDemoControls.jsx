import { Play, RefreshCw, Sprout, Square, Waves } from 'lucide-react';

const SCENARIOS = [
  ['balanced', 'Balanced tomato soil'],
  ['water-stress', 'Water stress'],
  ['nitrogen-low', 'Low nitrogen'],
  ['salinity-risk', 'Salinity risk'],
  ['alkaline-soil', 'Alkaline soil'],
];

export default function TomatoDemoControls({ status, scenario, onScenarioChange, onStart, onIrrigate, onStop, onForecastFixture, busy = false }) {
  if (!status?.enabled) return null;
  const running = status.running === true;
  const selectedScenario = scenario || status.scenario || 'balanced';
  return <section className="rounded-card border border-violet-200 bg-violet-50/60 p-4" aria-label="Tomato demo simulator">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div className="flex items-start gap-3">
        <span className="rounded-lg bg-violet-600 p-2 text-white"><Sprout size={17} /></span>
        <div>
          <h2 className="font-bold text-violet-950">Tomato prototype simulator</h2>
          <p className="mt-1 text-xs leading-5 text-violet-900/75">Demo-only soil values change every 15 seconds. No pump or hardware is controlled.</p>
        </div>
      </div>
      <span className={`rounded-full px-2.5 py-1 text-[11px] font-bold ${running ? 'bg-emerald-100 text-emerald-800' : 'bg-white text-violet-800'}`}>{running ? 'Running' : 'Stopped'}</span>
    </div>
    <div className="mt-4 flex flex-wrap items-end gap-2">
      <label className="text-xs font-semibold text-violet-950">Scenario<select value={selectedScenario} onChange={(event) => onScenarioChange(event.target.value)} className="mt-1 block rounded-lg border border-violet-200 bg-white px-3 py-2 text-xs" disabled={busy}><option value="balanced">Balanced tomato soil</option>{SCENARIOS.slice(1).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
      <button type="button" onClick={onStart} disabled={busy} className="inline-flex items-center gap-1.5 rounded-lg bg-violet-700 px-3 py-2 text-xs font-bold text-white disabled:opacity-50"><Play size={13} />{running ? 'Restart scenario' : 'Start simulation'}</button>
      {running && <><button type="button" onClick={onIrrigate} disabled={busy} className="inline-flex items-center gap-1.5 rounded-lg border border-sky-300 bg-white px-3 py-2 text-xs font-bold text-sky-800 disabled:opacity-50"><Waves size={13} />Simulate irrigation</button><button type="button" onClick={onStop} disabled={busy} className="inline-flex items-center gap-1.5 rounded-lg border border-violet-300 bg-white px-3 py-2 text-xs font-bold text-violet-900 disabled:opacity-50"><Square size={12} />Stop</button></>}
      {running && <span className="inline-flex items-center gap-1 text-[11px] text-violet-900/75"><RefreshCw size={12} />Tick {status.tick_count} · simulated source</span>}
    </div>
    {onForecastFixture && <div className="mt-3 rounded-lg border border-violet-200 bg-white/70 p-3"><p className="text-xs font-bold text-violet-950">Demo forecast fixture</p><p className="mt-1 text-[11px] leading-4 text-violet-900/75">Explicitly simulated weather for repeatable irrigation narration; it never claims to be a live forecast.</p><div className="mt-2 flex flex-wrap gap-2"><button type="button" disabled={busy} onClick={() => onForecastFixture('ordinary-rain')} className="rounded-md border border-violet-200 bg-white px-2.5 py-1.5 text-[11px] font-bold text-violet-900 disabled:opacity-50">Ordinary rain</button><button type="button" disabled={busy} onClick={() => onForecastFixture('heavy-rain')} className="rounded-md bg-violet-700 px-2.5 py-1.5 text-[11px] font-bold text-white disabled:opacity-50">Heavy rain · 30 mm / 48h</button><button type="button" disabled={busy} onClick={() => onForecastFixture('clear')} className="rounded-md border border-violet-200 bg-white px-2.5 py-1.5 text-[11px] font-bold text-violet-900 disabled:opacity-50">Use live weather</button></div>{status.forecast_fixture && <p className="mt-2 text-[11px] font-semibold text-violet-900">Active fixture: {status.forecast_fixture}</p>}</div>}
  </section>;
}
