import { useEffect, useMemo, useState } from 'react';
import { Search, Tractor, Wrench } from 'lucide-react';
import { referenceApi } from '../api/referenceApi.js';
import { useFarmData } from '../context/FarmDataContext.jsx';
import { EmptyState, ErrorState, LoadingState, SourceStamp } from '../components/feedback/ApiState.jsx';
import LocationSearchControl from '../components/location/LocationSearchControl.jsx';
import { useLanguage } from '../hooks/useLanguage.jsx';
import { parseDisplayLocation, selectedLocation, hasCoordinates } from '../lib/location.js';
import NearbyServicesMap from '../components/maps/NearbyServicesMap.jsx';

const RADIUS_OPTIONS = [25, 50, 100, 250];

export default function MachineryRentals() {
  const { profile, fields = [] } = useFarmData();
  const { language } = useLanguage();
  const [items, setItems] = useState([]);
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [fieldId, setFieldId] = useState(fields[0]?.id || '');
  const [radius, setRadius] = useState(50);
  const [scope, setScope] = useState('nearby');
  const [searchOrigin, setSearchOrigin] = useState(null);
  const [mode, setMode] = useState('list');
  const [selectedId, setSelectedId] = useState(null);
  const [reloadToken, setReloadToken] = useState(0);
  const selectedField = fields.find((field) => field.id === fieldId) || fields[0];
  const farmLocation = useMemo(() => selectedLocation(profile, selectedField), [profile, selectedField]);
  const activeLocation = searchOrigin || farmLocation;
  const fallbackAdmin = parseDisplayLocation(profile?.location);
  const isHindi = language === 'hi';
  const isMarathi = language === 'mr';

  useEffect(() => {
    let active = true;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    setError(null);
    const request = scope === 'all'
      ? referenceApi.listMachineryRentals({ category: category || undefined })
      : hasCoordinates(activeLocation)
        ? referenceApi.nearbyMachineryRentals({
          lat: activeLocation.latitude,
          lon: activeLocation.longitude,
          radius_km: radius,
          category: category || undefined,
        })
        : referenceApi.listMachineryRentals({
          district: activeLocation.district || fallbackAdmin.district,
          state: activeLocation.state || fallbackAdmin.state,
          category: category || undefined,
        });
    request.then((result) => {
      if (active) setItems(Array.isArray(result) ? result : []);
    }).catch((reason) => { if (active) setError(reason); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [activeLocation, category, fallbackAdmin.district, fallbackAdmin.state, radius, reloadToken, scope]);

  const categories = useMemo(() => [...new Set(items.map((item) => item.category).filter(Boolean))].sort(), [items]);
  const visible = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return items;
    return items.filter((item) => [item.name, item.category, item.provider_name, item.location, item.state, item.district]
      .join(' ').toLowerCase().includes(normalized));
  }, [items, query]);
  const title = isMarathi ? 'शेती यंत्रसामग्री भाडे' : isHindi ? 'कृषि मशीनरी किराया' : 'Machinery & tractor rentals';
  const locationLabel = scope === 'all' ? 'All India directory' : activeLocation.label || 'Selected farm';

  const chooseField = (nextFieldId) => {
    setFieldId(nextFieldId);
    setSearchOrigin(null);
    setScope('nearby');
  };

  const chooseSearchLocation = (nextLocation) => {
    setSearchOrigin(nextLocation);
    if (nextLocation) setScope('nearby');
  };

  return <main className="mx-auto max-w-[1440px] px-4 py-5 sm:px-6 lg:px-8 lg:py-7">
    <header>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-primary">India-wide provider directory</p>
          <h1 className="mt-2 text-2xl font-bold">{title}</h1>
          <p className="mt-1 max-w-3xl text-sm text-text-secondary">Search official FARMS custom-hiring records by any Indian location, compare distance and disclosed rates, and contact providers directly. This screen never creates a booking.</p>
        </div>
        <div className="rounded-xl border border-primary/15 bg-primary-50 px-4 py-3 text-right text-xs text-text-secondary">
          <p className="font-bold text-primary">{scope === 'all' ? 'Nationwide view' : 'Location view'}</p>
          <p className="mt-1">{visible.length} matching records</p>
        </div>
      </div>
    </header>

    <div className="mt-5 flex flex-wrap items-center gap-2">
      <span className="text-xs text-text-secondary">Search near</span>
      {fields.length > 0 && <select aria-label="Farm field" value={selectedField?.id || ''} onChange={(event) => chooseField(event.target.value)} className="rounded-lg border border-border bg-white px-3 py-2 text-sm">
        {fields.map((field) => <option value={field.id} key={field.id}>{field.name}</option>)}
      </select>}
      <button type="button" onClick={() => { setScope('nearby'); setSearchOrigin(null); }} className={`rounded-lg px-3 py-2 text-xs font-bold ${scope === 'nearby' ? 'bg-primary text-white' : 'border border-border bg-white text-text-secondary'}`}>Near a location</button>
      <button type="button" onClick={() => { setScope('all'); setSearchOrigin(null); }} className={`rounded-lg px-3 py-2 text-xs font-bold ${scope === 'all' ? 'bg-primary text-white' : 'border border-border bg-white text-text-secondary'}`}>All India</button>
      <select aria-label="Search radius" value={radius} onChange={(event) => setRadius(Number(event.target.value))} disabled={scope === 'all'} className="rounded-lg border border-border bg-white px-3 py-2 text-sm disabled:opacity-50">
        {RADIUS_OPTIONS.map((value) => <option value={value} key={value}>{value} km</option>)}
      </select>
      <div className="ml-auto inline-flex rounded-lg bg-surface-muted p-1">
        <button type="button" onClick={() => setMode('list')} className={`rounded-md px-3 py-1.5 text-xs font-semibold ${mode === 'list' ? 'bg-primary text-white' : 'text-text-secondary'}`}>List</button>
        <button type="button" onClick={() => setMode('map')} className={`rounded-md px-3 py-1.5 text-xs font-semibold ${mode === 'map' ? 'bg-primary text-white' : 'text-text-secondary'}`}>Map</button>
      </div>
    </div>

    <div className="mt-4"><LocationSearchControl key={selectedField?.id || 'profile'} fallbackLocation={farmLocation} value={searchOrigin} onChange={chooseSearchLocation} /></div>
    <p className="mt-2 text-xs text-text-secondary">{locationLabel}{scope !== 'all' && hasCoordinates(activeLocation) ? ` · ${Number(activeLocation.latitude).toFixed(4)}, ${Number(activeLocation.longitude).toFixed(4)} · within ${radius} km` : ''}</p>

    <div className="mt-5 flex flex-wrap gap-3">
      <label className="flex min-w-60 flex-1 items-center gap-2 rounded-xl border border-border bg-white px-3 py-2 shadow-card">
        <Search size={16} className="text-text-muted" /><span className="sr-only">Filter machinery</span><input value={query} onChange={(event) => setQuery(event.target.value)} className="min-w-0 flex-1 text-sm outline-none" placeholder="Filter tractors, implements, providers…" />
      </label>
      <select aria-label="Machinery category" value={category} onChange={(event) => setCategory(event.target.value)} className="rounded-xl border border-border bg-white px-3 py-2 text-sm">
        <option value="">All categories</option>{categories.map((item) => <option value={item} key={item}>{item}</option>)}
      </select>
    </div>

    {loading && <div className="mt-6"><LoadingState label="Searching the live machinery directory…" /></div>}
    {!loading && error && <div className="mt-6"><ErrorState error={error} onRetry={() => setReloadToken((value) => value + 1)} /></div>}
    {!loading && !error && !items.length && <div className="mt-6"><EmptyState title="No machinery records in this search" detail={scope === 'all' ? 'The live directory returned no records. Refresh the source or try again later.' : 'Try a wider radius, another Indian location, or switch to All India.'} /></div>}
    {!loading && !error && items.length > 0 && <>
      {mode === 'map' && <div className="mt-6"><NearbyServicesMap location={scope === 'all' ? { latitude: 20.5937, longitude: 78.9629, label: 'India' } : activeLocation} items={visible} selectedId={selectedId} onSelect={(item) => setSelectedId(item.id)} radiusKm={radius} /></div>}
      {mode === 'list' && (visible.length ? <section className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">{visible.map((item) => <article className={`overflow-hidden rounded-card border bg-white shadow-card ${selectedId === item.id ? 'border-primary ring-2 ring-primary/10' : 'border-border'}`} key={item.id} onClick={() => setSelectedId(item.id)}>
        {item.image_url ? <img src={item.image_url} alt="" className="h-36 w-full object-cover" /> : <div className="grid h-36 place-items-center bg-primary-50 text-primary"><Tractor size={42} /></div>}
        <div className="p-5"><div className="flex items-start justify-between gap-3"><div><span className="text-xs font-semibold uppercase tracking-wide text-primary">{item.category}</span><h2 className="mt-1 font-bold">{item.name}</h2></div><Wrench size={18} className="shrink-0 text-primary" /></div>
          <p className="mt-3 text-sm text-text-secondary">{item.description || item.provider_name}</p>
          <div className="mt-4 grid grid-cols-2 gap-2 text-xs"><span className="rounded-lg bg-surface-muted p-2">Hourly: <b>{item.hourly_rate == null ? '—' : `₹${item.hourly_rate}`}</b></span><span className="rounded-lg bg-surface-muted p-2">Daily: <b>{item.daily_rate == null ? '—' : `₹${item.daily_rate}`}</b></span></div>
          <p className="mt-3 text-xs text-text-secondary">{[item.location, item.district, item.state].filter(Boolean).join(', ') || 'Location not published'}{item.distance_km == null ? '' : ` · ${item.distance_km} km`}</p><p className="mt-1 text-xs font-semibold text-emerald-700">{item.availability_status}</p>
          {item.contact_phone && <a href={`tel:${item.contact_phone}`} className="mt-4 inline-block rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-white">Contact provider</a>}<SourceStamp source={item.source} fetchedAt={item.fetched_at || item.observed_at} />
        </div>
      </article>)}</section> : <div className="mt-6"><EmptyState title="No matching listings" detail="Try another category or search term." /></div>)}
    </>}
  </main>;
}
