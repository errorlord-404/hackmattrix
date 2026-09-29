import { useCallback, useEffect, useState } from 'react';
import { ArrowRight, CalendarDays, CloudSun, Droplets, Leaf, MapPin, RefreshCw, TrendingUp, TriangleAlert } from 'lucide-react';
import { Link } from 'react-router-dom';
import { farmStateApi } from '../api/farmStateApi.js';
import { referenceApi } from '../api/referenceApi.js';
import { useFarmData } from '../context/FarmDataContext.jsx';
import { EmptyState, ErrorState, LoadingState, SourceStamp } from '../components/feedback/ApiState.jsx';
import SensorTelemetryPanel from '../components/features/sensors/SensorTelemetryPanel.jsx';
import TomatoDemoControls from '../components/features/sensors/TomatoDemoControls.jsx';
import { useLanguage } from '../hooks/useLanguage.jsx';

const Card = ({ children, className = '' }) => <section className={`rounded-card border border-border bg-surface shadow-card ${className}`}>{children}</section>;
const Go = ({ to, children }) => <Link to={to} className="inline-flex items-center gap-1 rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-white transition hover:bg-primary-dark">{children}<ArrowRight size={13} /></Link>;

function Metric({ icon: Icon, label, value, note, tone = 'text-primary bg-primary-50' }) {
  return <Card className="p-4"><div className="flex justify-between gap-3"><div><p className="text-xs font-medium text-text-secondary">{label}</p><p className="mt-2 text-2xl font-bold text-text-primary">{value}</p><p className="mt-1 min-h-4 text-xs text-text-secondary">{note}</p></div><span className={`h-fit rounded-xl p-3 ${tone}`}><Icon size={22} /></span></div></Card>;
}

function soilValue(soil, key) {
  return soil?.latest_observations?.find((item) => item.measurement === key)?.value ?? soil?.latest_test?.[key === 'moisture' ? 'moisture_percent' : key];
}

function moistureNote(moisture, plan) {
  if (moisture == null) return 'No current moisture observation';
  if (plan?.status === 'not_required') return 'Moisture is at or above the irrigation target';
  if (plan?.status === 'recommended') return 'Moisture is below the irrigation target';
  if (plan?.status === 'defer_for_rain') return 'Moisture is below target; rain is expected';
  if (plan?.status === 'reassess_after_recent_irrigation') return 'Recheck moisture after recent irrigation';
  return 'Latest recorded moisture reading';
}

export default function Dashboard() {
  const { language } = useLanguage();
  const hi = language === 'hi';
  const { profile, fields, alerts, loading: farmLoading, error: farmError, refresh } = useFarmData();
  const [dashboard, setDashboard] = useState(null);
  const [soil, setSoil] = useState(null);
  const [plan, setPlan] = useState(null);
  const [market, setMarket] = useState([]);
  const [tomatoDemo, setTomatoDemo] = useState(null);
  const [tomatoScenario, setTomatoScenario] = useState('balanced');
  const [tomatoBusy, setTomatoBusy] = useState(false);
  const [sensorError, setSensorError] = useState(null);
  const [contentError, setContentError] = useState(null);
  const [loadingContent, setLoadingContent] = useState(false);
  const field = fields[0];

  const load = useCallback(async () => {
    if (!field) return;
    setLoadingContent(true);
    setSensorError(null);
    setContentError(null);
    const [nextDashboard, nextSoil, nextPlan, nextMarket, nextTomatoDemo] = await Promise.allSettled([
      farmStateApi.getDashboard(),
      farmStateApi.getSoilHealth(field.id),
      farmStateApi.getIrrigationPlan(field.id),
      field.current_crop ? referenceApi.marketSummary({ crop: field.current_crop }) : Promise.resolve([]),
      farmStateApi.getTomatoDemo ? farmStateApi.getTomatoDemo(field.id) : Promise.resolve(null),
    ]);
    if (nextDashboard.status === 'fulfilled') setDashboard(nextDashboard.value);
    if (nextSoil.status === 'fulfilled') setSoil(nextSoil.value); else setSensorError(nextSoil.reason);
    if (nextPlan.status === 'fulfilled') setPlan(nextPlan.value);
    if (nextMarket.status === 'fulfilled') setMarket(nextMarket.value); else setContentError(nextMarket.reason);
    if (nextTomatoDemo.status === 'fulfilled' && nextTomatoDemo.value) {
      setTomatoDemo(nextTomatoDemo.value);
      if (nextTomatoDemo.value.scenario) setTomatoScenario(nextTomatoDemo.value.scenario);
    }
    if (nextDashboard.status === 'rejected' && nextPlan.status === 'rejected' && nextMarket.status === 'rejected') setContentError(nextDashboard.reason);
    setLoadingContent(false);
  }, [field]);

  useEffect(() => {
    if (!field || !tomatoDemo?.running) return undefined;
    const interval = window.setInterval(async () => {
      try {
        const next = await farmStateApi.tickTomatoDemo(field.id);
        setTomatoDemo(next);
        await load();
      } catch (error) {
        setSensorError(error);
      }
    }, 15_000);
    return () => window.clearInterval(interval);
  }, [field, tomatoDemo?.running, load]);

  const runTomatoDemoAction = async (action) => {
    if (!field) return;
    setTomatoBusy(true);
    try {
      const next = await action(field.id);
      setTomatoDemo(next);
      if (next.scenario) setTomatoScenario(next.scenario);
      await load();
    } catch (error) {
      setSensorError(error);
    } finally {
      setTomatoBusy(false);
    }
  };

  // Poll the displayed field at a calm interval; a stale state is shown rather than pretending it is live.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
    const interval = window.setInterval(load, 60_000);
    return () => window.clearInterval(interval);
  }, [load]);

  if (farmLoading) return <div className="px-4 pt-5 lg:px-8"><LoadingState /></div>;
  if (farmError) return <div className="px-4 pt-5 lg:px-8"><ErrorState error={farmError} onRetry={refresh} /></div>;
  if (!profile || !fields.length) return <div className="mx-auto max-w-3xl px-4 py-10"><EmptyState title="Set up your local farm profile" detail="Open Settings to save your farmer profile, location, and then add a field. Dashboard values will appear from the backend after those records exist." action={<Link to="/settings" className="mt-4 inline-block rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-white">Open Settings</Link>} /></div>;

  const weather = dashboard?.weather;
  const moisture = soilValue(soil, 'moisture');
  const latestPrice = market[0];
  const soilTest = soil?.latest_test;
  return <main className="mx-auto max-w-[1440px] px-4 py-5 sm:px-6 lg:px-8 lg:py-7">
    <header className="rounded-2xl border border-primary/15 bg-[radial-gradient(circle_at_top_right,_rgba(132,204,22,0.25),_transparent_42%),linear-gradient(135deg,#f7fff8,#eff9ef)] px-5 py-5 shadow-card sm:px-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div><p className="text-xs font-bold uppercase tracking-[0.16em] text-primary">KisanSathi · field command centre</p><h1 className="mt-2 text-2xl font-bold text-text-primary sm:text-3xl">{hi ? `नमस्ते ${profile.name}` : `Hello ${profile.name}`} <span aria-hidden="true">🌾</span></h1><p className="mt-1 flex items-center gap-1 text-sm text-text-secondary"><MapPin size={14} />{field.name} · {field.current_crop || 'Crop not recorded'} · {field.area_acres} acres</p></div>
        <button onClick={load} disabled={loadingContent} className="inline-flex items-center gap-2 rounded-lg border border-primary/25 bg-white px-3 py-2 text-xs font-bold text-primary transition hover:bg-primary-50 disabled:opacity-60"><RefreshCw size={14} className={loadingContent ? 'animate-spin' : ''} />{loadingContent ? 'Refreshing…' : 'Refresh field data'}</button>
      </div>
    </header>

    {contentError ? <div className="mt-5"><ErrorState error={contentError} onRetry={load} /></div> : null}

    <section aria-label="Farm overview" className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <Metric icon={CloudSun} label="Weather" value={weather?.current?.temperature_c == null ? '—' : `${weather.current.temperature_c}°C`} note={weather?.provider || 'Weather unavailable'} tone="text-amber-700 bg-amber-50" />
      <Metric icon={Droplets} label="Soil moisture" value={moisture == null ? 'Unknown' : `${moisture}%`} note={moistureNote(moisture, plan)} tone="text-sky-700 bg-sky-50" />
      <Metric icon={CalendarDays} label="Irrigation advice" value={plan?.recommendation?.what || 'Unknown'} note={plan?.recommendation?.when || 'No plan available'} tone="text-violet-700 bg-violet-50" />
      <Metric icon={TrendingUp} label="Market price" value={latestPrice ? `₹${latestPrice.price_per_quintal}` : '—'} note={latestPrice?.mandi_name || 'No dated reference'} tone="text-emerald-700 bg-emerald-50" />
    </section>

    <div className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,1.65fr)_minmax(290px,0.85fr)]">
      <div className="space-y-4"><TomatoDemoControls status={tomatoDemo} scenario={tomatoScenario} onScenarioChange={setTomatoScenario} busy={tomatoBusy} onStart={() => runTomatoDemoAction((id) => farmStateApi.startTomatoDemo(id, { scenario: tomatoScenario, seed: 42 }))} onIrrigate={() => runTomatoDemoAction(farmStateApi.irrigateTomatoDemo)} onStop={() => runTomatoDemoAction(farmStateApi.stopTomatoDemo)} onForecastFixture={(scenario) => runTomatoDemoAction((id) => farmStateApi.setTomatoDemoWeatherFixture(id, scenario))} /><SensorTelemetryPanel observations={soil?.latest_observations || []} fieldName={field.name} loading={loadingContent && !soil} error={sensorError} onRetry={load} /></div>
      <aside className="space-y-5">
        <Card className="p-5"><div className="flex items-start justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-[0.12em] text-text-secondary">Farm attention</p><h2 className="mt-2 text-lg font-bold text-primary-dark">{alerts.length ? `${alerts.length} item${alerts.length === 1 ? '' : 's'} need review` : 'No open local alerts'}</h2></div><TriangleAlert className={alerts.length ? 'text-amber-600' : 'text-primary'} /></div>{alerts.length ? <div className="mt-4 space-y-2">{alerts.slice(0, 3).map((alert) => <div className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900" key={alert.id}><p className="font-semibold">{alert.title}</p><p className="mt-1 text-xs">{alert.message}</p></div>)}</div> : <p className="mt-4 text-sm text-text-secondary">Continue checking crop images and verified field readings.</p>}<div className="mt-5"><Go to="/ai">Ask advisor</Go></div></Card>
        <Card className="p-5"><div className="flex items-start justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-[0.12em] text-text-secondary">Active field</p><h2 className="mt-2 text-lg font-bold">{field.name}</h2><p className="mt-1 text-sm text-text-secondary">{field.current_crop || 'Crop not recorded'} · {field.area_acres} acres</p></div><Leaf className="text-primary" /></div><div className="mt-4 grid grid-cols-2 gap-2 text-xs"><div className="rounded-lg bg-surface-muted p-3"><p className="text-text-secondary">Latest pH</p><b className="mt-1 block text-base">{soilValue(soil, 'ph') ?? '—'}</b></div><div className="rounded-lg bg-surface-muted p-3"><p className="text-text-secondary">Soil test</p><b className="mt-1 block text-base">{soilTest?.observed_at ? new Date(soilTest.observed_at).toLocaleDateString() : 'Not recorded'}</b></div></div><div className="mt-4"><Go to={`/fields/${field.id}`}>View field</Go></div></Card>
      </aside>
    </div>

    <section className="mt-5 grid gap-5 lg:grid-cols-3">
      <Card className="p-5"><h2 className="font-bold">Soil health baseline</h2>{soilTest ? <div className="mt-4 grid grid-cols-2 gap-2">{[['pH', soilValue(soil, 'ph')], ['N', soilValue(soil, 'nitrogen')], ['P', soilValue(soil, 'phosphorus')], ['K', soilValue(soil, 'potassium')]].map(([label, value]) => <div className="rounded-lg bg-surface-muted p-3" key={label}><p className="text-[10px] text-text-secondary">{label}</p><b className="mt-1 block text-lg text-primary-dark">{value ?? '—'}</b></div>)}</div> : <p className="mt-4 text-sm text-text-secondary">No verified soil test recorded. Sensor readings are displayed separately as current observations.</p>}<div className="mt-5"><Go to="/soil">Open soil health</Go></div></Card>
      <Card className="p-5"><h2 className="font-bold">Weather forecast</h2>{weather?.daily?.length ? <div className="mt-4 grid grid-cols-5">{weather.daily.slice(0, 5).map((day) => <div className="text-center" key={day.observed_at}><p className="text-[10px] text-text-secondary">{new Date(day.observed_at).toLocaleDateString(undefined, { weekday: 'short' })}</p><p className="my-2 text-xl" aria-hidden="true">{day.precipitation_probability > 50 ? '🌧️' : '☀️'}</p><b className="text-xs">{day.temperature_max_c ?? '—'}°</b></div>)}</div> : <p className="mt-4 text-sm text-text-secondary">No cached forecast.</p>}<SourceStamp source={weather?.provider} fetchedAt={weather?.fetched_at} warning={!weather ? 'Weather remains unknown until a location-based request succeeds.' : undefined} /><div className="mt-5"><Go to="/weather">Open weather</Go></div></Card>
      <Card className="p-5"><h2 className="font-bold">Market snapshot</h2>{latestPrice ? <><p className="mt-5 text-3xl font-bold text-primary-dark">₹{latestPrice.price_per_quintal}</p><p className="mt-1 text-xs text-text-secondary">{latestPrice.mandi_name}</p><SourceStamp source={latestPrice.source} fetchedAt={latestPrice.fetched_at} /></> : <p className="mt-5 text-sm text-text-secondary">No dated mandi reference is available for this crop.</p>}<div className="mt-5"><Go to="/market">View prices</Go></div></Card>
    </section>
  </main>;
}
