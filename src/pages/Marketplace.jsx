import { useCallback, useEffect, useMemo, useState } from 'react';
import { ExternalLink, PackageSearch, Search, Truck, Wrench } from 'lucide-react';
import { referenceApi } from '../api/referenceApi.js';
import { useFarmData } from '../context/FarmDataContext.jsx';
import { EmptyState, ErrorState, LoadingState, SourceStamp } from '../components/feedback/ApiState.jsx';
import LocationSearchControl from '../components/location/LocationSearchControl.jsx';
import { parseDisplayLocation, selectedLocation, hasCoordinates } from '../lib/location.js';
import NearbyServicesMap from '../components/maps/NearbyServicesMap.jsx';
import { FertilizerReferenceCatalog, MarketplaceCoverage, SeedReferenceCatalog } from '../components/marketplace/ReferenceCatalog.jsx';

const TYPES = [
  ['all', 'Everything'], ['machinery', 'Machinery'], ['seed', 'Seeds'], ['fertilizer', 'Fertilizers'],
  ['logistics', 'Logistics'], ['buyer', 'Buyers'], ['exporter', 'Exporters'],
];
const RADIUS_OPTIONS = [25, 50, 100, 250];

export default function Marketplace() {
  const { profile, fields = [] } = useFarmData();
  const [fieldId, setFieldId] = useState(fields[0]?.id || '');
  const selectedField = fields.find((field) => field.id === fieldId) || fields[0];
  const farmLocation = useMemo(() => selectedLocation(profile, selectedField), [profile, selectedField]);
  const fallbackAdmin = parseDisplayLocation(profile?.location);
  const [scope, setScope] = useState('nearby');
  const [searchOrigin, setSearchOrigin] = useState(null);
  const activeLocation = searchOrigin || farmLocation;
  const [listingType, setListingType] = useState('all');
  const [query, setQuery] = useState('');
  const [items, setItems] = useState([]);
  const [directoryStatus, setDirectoryStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [catalogItems, setCatalogItems] = useState([]);
  const [catalogLoading, setCatalogLoading] = useState(false);
  const [catalogError, setCatalogError] = useState(null);
  const [catalogRetry, setCatalogRetry] = useState(0);
  const [radius, setRadius] = useState(25);
  const [mode, setMode] = useState('list');
  const [selectedId, setSelectedId] = useState(null);
  const isReferenceType = listingType === 'seed' || listingType === 'fertilizer';

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const search = scope === 'all'
        ? referenceApi.searchMarketplace({ listing_type: listingType === 'all' ? undefined : listingType, query: query || undefined, limit: 100 })
        : hasCoordinates(activeLocation)
          ? referenceApi.nearbyMarketplace({ lat: activeLocation.latitude, lon: activeLocation.longitude, radius_km: radius, listing_type: listingType === 'all' ? undefined : listingType })
          : referenceApi.searchMarketplace({ listing_type: listingType === 'all' ? undefined : listingType, district: activeLocation.district || fallbackAdmin.district, state: activeLocation.state || fallbackAdmin.state, query: query || undefined });
      const [nextItems, nextStatus] = await Promise.all([search, referenceApi.marketplaceStatus()]);
      const filtered = query ? nextItems.filter((item) => [item.title, item.category, item.provider_name, item.description, item.location].join(' ').toLowerCase().includes(query.toLowerCase())) : nextItems;
      setItems(filtered);
      setDirectoryStatus(nextStatus);
    } catch (reason) {
      setError(reason);
    } finally {
      setLoading(false);
    }
  }, [activeLocation, fallbackAdmin.district, fallbackAdmin.state, listingType, query, radius, scope]);

  useEffect(() => {
    const timer = window.setTimeout(load, 250);
    return () => window.clearTimeout(timer);
  }, [load]);

  useEffect(() => {
    if (!isReferenceType) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setCatalogItems([]);
      setCatalogError(null);
      return undefined;
    }
    let active = true;
    setCatalogLoading(true);
    setCatalogError(null);
    const request = listingType === 'seed' ? referenceApi.listSeeds() : referenceApi.listFertilizers();
    request.then((result) => {
      if (active) setCatalogItems(Array.isArray(result) ? result : []);
    }).catch((reason) => {
      if (active) setCatalogError(reason);
    }).finally(() => {
      if (active) setCatalogLoading(false);
    });
    return () => { active = false; };
  }, [catalogRetry, isReferenceType, listingType]);

  const categories = useMemo(() => [...new Set(items.map((item) => item.category).filter(Boolean))], [items]);
  const chooseField = (nextFieldId) => {
    setFieldId(nextFieldId);
    setSearchOrigin(null);
    setScope('nearby');
  };
  const chooseType = (nextType) => {
    setListingType(nextType);
    setSelectedId(null);
  };
  const showLoading = loading || (isReferenceType && catalogLoading);

  return <main className="mx-auto max-w-[1440px] px-4 py-5 sm:px-6 lg:px-8 lg:py-7">
    <header className="rounded-2xl border border-primary/15 bg-primary-50 px-5 py-5"><div className="flex items-start gap-3"><span className="rounded-xl bg-primary p-3 text-white"><PackageSearch size={24} /></span><div><h1 className="text-2xl font-bold">Farm marketplace directory</h1><p className="mt-1 max-w-3xl text-sm text-text-secondary">Source-attributed discovery for machinery, crop inputs, logistics, buyers and exporters. Contact a provider directly; KisanSathi does not book, buy, sell, or guarantee a listing.</p></div></div></header>
    <div className="mt-6 flex flex-wrap gap-2">{TYPES.map(([value, label]) => <button type="button" key={value} onClick={() => chooseType(value)} className={`rounded-full px-3 py-2 text-xs font-bold ${listingType === value ? 'bg-primary text-white' : 'border border-border bg-white text-text-secondary'}`}>{label}</button>)}</div>
    <div className="mt-4 flex flex-wrap items-center gap-2"><span className="text-xs text-text-secondary">Search near</span>{fields.length > 0 && <select aria-label="Farm field" value={selectedField?.id || ''} onChange={(event) => chooseField(event.target.value)} className="rounded-lg border border-border bg-white px-3 py-2 text-sm">{fields.map((field) => <option value={field.id} key={field.id}>{field.name}</option>)}</select>}<button type="button" onClick={() => { setScope('nearby'); setSearchOrigin(null); }} className={`rounded-lg px-3 py-2 text-xs font-bold ${scope === 'nearby' ? 'bg-primary text-white' : 'border border-border bg-white text-text-secondary'}`}>Near a location</button><button type="button" onClick={() => { setScope('all'); setSearchOrigin(null); }} className={`rounded-lg px-3 py-2 text-xs font-bold ${scope === 'all' ? 'bg-primary text-white' : 'border border-border bg-white text-text-secondary'}`}>All India</button><select aria-label="Search radius" value={radius} onChange={(event) => setRadius(Number(event.target.value))} disabled={scope === 'all'} className="rounded-lg border border-border bg-white px-3 py-2 text-sm disabled:opacity-50">{RADIUS_OPTIONS.map((value) => <option value={value} key={value}>{value} km</option>)}</select><div className="ml-auto inline-flex rounded-lg bg-surface-muted p-1"><button type="button" onClick={() => setMode('list')} className={`rounded-md px-3 py-1.5 text-xs font-semibold ${mode === 'list' ? 'bg-primary text-white' : 'text-text-secondary'}`}>List</button><button type="button" onClick={() => setMode('map')} className={`rounded-md px-3 py-1.5 text-xs font-semibold ${mode === 'map' ? 'bg-primary text-white' : 'text-text-secondary'}`}>Map</button></div></div>
    <div className="mt-4"><LocationSearchControl key={selectedField?.id || 'profile'} fallbackLocation={farmLocation} value={searchOrigin} onChange={(nextLocation) => { setSearchOrigin(nextLocation); if (nextLocation) setScope('nearby'); }} /></div>
    <p className="mt-2 text-xs text-text-secondary">{scope === 'all' ? 'All India directory' : activeLocation.label} · {scope === 'all' || !hasCoordinates(activeLocation) ? 'location fallback' : `${Number(activeLocation.latitude).toFixed(4)}, ${Number(activeLocation.longitude).toFixed(4)}`}</p>
    <label className="mt-4 flex max-w-2xl items-center gap-2 rounded-xl border border-border bg-white px-3 py-2 shadow-card"><Search size={17} className="text-text-muted" /><span className="sr-only">Search listings</span><input value={query} onChange={(event) => setQuery(event.target.value)} className="min-w-0 flex-1 text-sm outline-none" placeholder="Search provider, service, crop input, buyer, or location" /></label>
    <MarketplaceCoverage activeType={listingType} directoryStatus={directoryStatus} />
    {showLoading && <div className="mt-5"><LoadingState label={isReferenceType ? 'Loading the shared reference catalog…' : 'Searching approved public directories…'} /></div>}
    {!showLoading && error && <div className="mt-5"><ErrorState error={error} onRetry={load} /></div>}
    {!showLoading && !error && catalogError && isReferenceType && <div className="mt-5"><ErrorState error={catalogError} onRetry={() => setCatalogRetry((value) => value + 1)} /></div>}
    {!showLoading && !error && !catalogError && listingType === 'seed' && <SeedReferenceCatalog items={catalogItems} query={query} />}
    {!showLoading && !error && !catalogError && listingType === 'fertilizer' && <FertilizerReferenceCatalog items={catalogItems} query={query} />}
    {!showLoading && !error && !isReferenceType && !items.length && <div className="mt-5"><EmptyState title="No verified listings for this category" detail={listingType === 'logistics' || listingType === 'buyer' ? 'No approved public directory source is configured for this category yet. The empty state is intentional so the app never invents provider contacts or prices.' : directoryStatus?.message || 'No approved listing matched this location. Clear filters, widen the radius, or switch to All India.'} /></div>}
    {!showLoading && !error && !isReferenceType && items.length > 0 && <><p className="mt-5 text-xs text-text-secondary">{items.length} listings · {categories.length ? `categories: ${categories.join(', ')}` : 'uncategorised'}</p>{mode === 'map' && <div className="mt-4"><NearbyServicesMap location={scope === 'all' ? { latitude: 20.5937, longitude: 78.9629, label: 'India' } : activeLocation} items={items} selectedId={selectedId} onSelect={(item) => setSelectedId(item.id)} radiusKm={radius} /></div>}{mode === 'list' && <section className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">{items.map((item) => <article key={item.id} onClick={() => setSelectedId(item.id)} className={`rounded-card border bg-white p-5 shadow-card ${selectedId === item.id ? 'border-primary ring-2 ring-primary/10' : 'border-border'}`}><div className="flex items-start justify-between gap-3"><span className="rounded-lg bg-primary-50 p-2 text-primary">{item.listing_type === 'logistics' ? <Truck size={18} /> : <Wrench size={18} />}</span><span className="rounded-full bg-surface-muted px-2 py-1 text-[10px] font-bold uppercase text-text-secondary">{item.listing_type}</span></div><h2 className="mt-4 font-bold">{item.title}</h2><p className="mt-1 text-xs font-semibold text-primary">{item.provider_name || 'Public directory listing'}</p><p className="mt-3 min-h-10 text-sm text-text-secondary">{item.description || 'No description was published by the source.'}</p>{item.price_amount != null && <p className="mt-4 text-lg font-bold">{item.price_currency || 'INR'} {Number(item.price_amount).toLocaleString()}<span className="ml-1 text-xs font-medium text-text-secondary">{item.price_unit || ''}</span></p>}<p className="mt-4 text-xs text-text-secondary">{[item.location, item.district, item.state].filter(Boolean).join(', ') || 'Location not published'}{item.distance_km == null ? '' : ` · ${item.distance_km} km`}</p><div className="mt-4 flex flex-wrap gap-2">{item.contact_phone && <a href={`tel:${item.contact_phone}`} className="rounded-lg bg-primary px-3 py-2 text-xs font-bold text-white">Call provider</a>}{item.listing_url && <a href={item.listing_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 rounded-lg border border-border px-3 py-2 text-xs font-bold text-primary">Source listing <ExternalLink size={13} /></a>}</div><SourceStamp source={item.source} fetchedAt={item.fetched_at} /></article>)}</section>}</>}
  </main>;
}
