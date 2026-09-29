import { AlertTriangle, CheckCircle2, Clock3, Droplets, FlaskConical, Gauge, Thermometer, WifiOff } from 'lucide-react';
import { Link } from 'react-router-dom';
import { freshnessFor } from './sensorTelemetry.js';
import { useLanguage } from '../../../hooks/useLanguage.jsx';

const METRICS = {
  moisture: { label: 'Moisture', labelHi: 'नमी', icon: Droplets, tone: 'text-sky-700 bg-sky-50', defaultUnit: '%' },
  temperature: { label: 'Soil temperature', labelHi: 'मिट्टी का तापमान', icon: Thermometer, tone: 'text-orange-700 bg-orange-50', defaultUnit: '°C' },
  ph: { label: 'pH', labelHi: 'पीएच', icon: FlaskConical, tone: 'text-violet-700 bg-violet-50', defaultUnit: '' },
  ec: { label: 'EC', labelHi: 'ईसी', icon: Gauge, tone: 'text-emerald-700 bg-emerald-50', defaultUnit: 'mS/cm' },
  nitrogen: { label: 'Nitrogen', labelHi: 'नाइट्रोजन', icon: FlaskConical, tone: 'text-lime-800 bg-lime-50', defaultUnit: 'mg/kg' },
  phosphorus: { label: 'Phosphorus', labelHi: 'फॉस्फोरस', icon: FlaskConical, tone: 'text-amber-800 bg-amber-50', defaultUnit: 'mg/kg' },
  potassium: { label: 'Potassium', labelHi: 'पोटैशियम', icon: FlaskConical, tone: 'text-rose-700 bg-rose-50', defaultUnit: 'mg/kg' },
};

const COPY = {
  en: { title: 'Live soil telemetry', latest: 'latest field observations', noReadings: 'No readings', measurements: 'measurements available', last: 'Last observation:', water: 'Water conditions', chemistry: 'Soil chemistry', noData: 'No sensor data yet', unknown: 'Connect a soil node and take the first verified reading. Until then, recommendations should treat soil measurements as unknown.', loading: 'Loading the latest sensor readings…', unavailable: 'Sensor readings are unavailable', retry: 'Retry readings', open: 'Open soil health →', source: 'Source:', warning: 'Sensor values are screening inputs. Confirm unusual nutrient readings with a soil test before changing fertilizer.' },
  hi: { title: 'लाइव मिट्टी टेलीमेट्री', latest: 'खेत की नवीनतम रीडिंग', noReadings: 'कोई रीडिंग नहीं', measurements: 'माप उपलब्ध हैं', last: 'अंतिम रीडिंग:', water: 'जल स्थिति', chemistry: 'मिट्टी रसायन', noData: 'अभी कोई सेंसर डेटा नहीं', unknown: 'मिट्टी नोड जोड़ें और पहली सत्यापित रीडिंग लें। तब तक सलाह मिट्टी के माप को अज्ञात मानेगी।', loading: 'नवीनतम सेंसर रीडिंग लोड हो रही हैं…', unavailable: 'सेंसर रीडिंग उपलब्ध नहीं हैं', retry: 'रीडिंग फिर से लें', open: 'मिट्टी स्वास्थ्य खोलें →', source: 'स्रोत:', warning: 'सेंसर मान केवल स्क्रीनिंग इनपुट हैं। उर्वरक बदलने से पहले असामान्य पोषक रीडिंग को मिट्टी जांच से पुष्टि करें।' },
};

function latestObservation(observations) {
  return observations.reduce((latest, item) => {
    if (!latest) return item;
    return new Date(item.observed_at).getTime() > new Date(latest.observed_at).getTime() ? item : latest;
  }, null);
}

function StatusBadge({ status, hi }) {
  const styles = {
    fresh: 'border-emerald-200 bg-emerald-50 text-emerald-800',
    aging: 'border-amber-200 bg-amber-50 text-amber-800',
    stale: 'border-rose-200 bg-rose-50 text-rose-800',
    unknown: 'border-slate-200 bg-slate-50 text-slate-700',
  };
  const labels = hi ? { fresh: 'ताज़ा', aging: 'पुराना हो रहा है', stale: 'पुराना', unknown: 'अज्ञात' } : {};
  return <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[11px] font-bold ${styles[status.key]}`}><span className={`h-1.5 w-1.5 rounded-full ${status.key === 'fresh' ? 'bg-emerald-500' : status.key === 'aging' ? 'bg-amber-500' : status.key === 'stale' ? 'bg-rose-500' : 'bg-slate-400'}`} />{labels[status.key] || status.label}</span>;
}

function Measurement({ observation, hi, copy }) {
  const meta = METRICS[observation.measurement] || { label: observation.measurement, icon: Gauge, tone: 'text-slate-700 bg-slate-100', defaultUnit: observation.unit };
  const Icon = meta.icon;
  const status = freshnessFor(observation.observed_at);
  const unit = observation.unit || meta.defaultUnit;
  return <article className="rounded-xl border border-border bg-white p-3 shadow-sm">
    <div className="flex items-start justify-between gap-2">
      <span className={`rounded-lg p-2 ${meta.tone}`}><Icon size={16} /></span>
      <StatusBadge status={status} hi={hi} />
    </div>
    <p className="mt-3 text-xs font-medium text-text-secondary">{hi ? meta.labelHi || meta.label : meta.label}</p>
    <p className="mt-1 text-xl font-bold text-text-primary">{Number(observation.value).toLocaleString(undefined, { maximumFractionDigits: 2 })}<span className="ml-1 text-xs font-medium text-text-secondary">{unit}</span></p>
    <p className="mt-2 truncate text-[10px] text-text-muted" title={observation.source}>{copy.source} {observation.source || 'local sensor'}</p>
    <p className="mt-1 text-[10px] text-text-muted">{observation.observed_at ? new Date(observation.observed_at).toLocaleString() : 'Time unavailable'}</p>
  </article>;
}

export default function SensorTelemetryPanel({ observations = [], fieldName, loading = false, error, onRetry, compact = false }) {
  const { language } = useLanguage();
  const hi = language === 'hi';
  const copy = COPY[hi ? 'hi' : 'en'];
  const latest = latestObservation(observations);
  const status = freshnessFor(latest?.observed_at);
  const simulated = observations.some((item) => String(item.source || '').startsWith('simulation:'));
  const shown = compact ? observations.filter((item) => ['moisture', 'temperature', 'ph', 'ec'].includes(item.measurement)) : observations;
  const chemistry = shown.filter((item) => ['ph', 'ec', 'nitrogen', 'phosphorus', 'potassium'].includes(item.measurement));
  const water = shown.filter((item) => ['moisture', 'temperature'].includes(item.measurement));
  return <section className="overflow-hidden rounded-card border border-border bg-surface shadow-card" aria-labelledby="live-soil-telemetry">
    <div className="border-b border-border bg-[radial-gradient(circle_at_top_right,_rgba(34,197,94,0.15),_transparent_45%),linear-gradient(135deg,#f8fffa,#ffffff)] px-5 py-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2"><span className="rounded-lg bg-primary p-2 text-white"><Droplets size={17} /></span><div><h2 id="live-soil-telemetry" className="font-bold text-text-primary">{copy.title}</h2><p className="text-xs text-text-secondary">{fieldName ? `${fieldName} · ${copy.latest}` : copy.latest}</p>{simulated && <span className="mt-1 inline-flex rounded-full bg-violet-100 px-2 py-0.5 text-[10px] font-bold text-violet-800">Simulated demo data</span>}</div></div>
        </div>
        {latest ? <div className="text-right"><StatusBadge status={status} hi={hi} /><p className="mt-1 text-[10px] text-text-muted">{status.detail}</p></div> : <StatusBadge status={{ key: 'unknown', label: copy.noReadings }} hi={hi} />}
      </div>
    </div>

    {loading ? <div className="p-5 text-sm text-text-secondary">{copy.loading}</div> : error ? <div className="m-5 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900"><div className="flex gap-2"><WifiOff size={18} className="mt-0.5 shrink-0" /><div><p className="font-bold">{copy.unavailable}</p><p className="mt-1 text-xs">{error.message || copy.latest}</p>{onRetry && <button onClick={onRetry} className="mt-3 rounded-lg bg-rose-700 px-3 py-2 text-xs font-semibold text-white">{copy.retry}</button>}</div></div></div> : !observations.length ? <div className="p-5"><div className="rounded-xl border border-dashed border-border bg-surface-muted p-5 text-center"><Clock3 className="mx-auto text-text-muted" size={24} /><p className="mt-3 font-bold">{copy.noData}</p><p className="mx-auto mt-1 max-w-md text-sm text-text-secondary">{copy.unknown}</p></div></div> : <div className="p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-lg bg-surface-muted px-3 py-2 text-xs text-text-secondary"><span className="inline-flex items-center gap-1.5"><CheckCircle2 size={14} className="text-primary" />{observations.length} {copy.measurements}</span><span>{copy.last} {latest?.observed_at ? new Date(latest.observed_at).toLocaleString() : 'unknown'}</span></div>
      {water.length ? <section><h3 className="mb-2 text-xs font-bold uppercase tracking-[0.12em] text-text-secondary">{copy.water}</h3><div className={`grid gap-3 ${compact ? 'grid-cols-2' : 'grid-cols-2 lg:grid-cols-3'}`}>{water.map((item) => <Measurement key={item.id || item.measurement} observation={item} hi={hi} copy={copy} />)}</div></section> : null}
      {chemistry.length ? <section className={water.length ? 'mt-5' : ''}><h3 className="mb-2 text-xs font-bold uppercase tracking-[0.12em] text-text-secondary">{copy.chemistry}</h3><div className={`grid gap-3 ${compact ? 'grid-cols-2' : 'grid-cols-2 md:grid-cols-3 lg:grid-cols-5'}`}>{chemistry.map((item) => <Measurement key={item.id || item.measurement} observation={item} hi={hi} copy={copy} />)}</div></section> : null}
      <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4"><p className="flex max-w-xl gap-2 text-xs text-amber-800"><AlertTriangle size={15} className="mt-0.5 shrink-0" />{copy.warning}</p><Link to="/soil" className="text-xs font-bold text-primary hover:underline">{copy.open}</Link></div>
    </div>}
  </section>;
}
