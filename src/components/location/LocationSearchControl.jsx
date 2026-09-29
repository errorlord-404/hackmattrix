import { useState } from 'react';
import { Crosshair, LoaderCircle, MapPin, Search, X } from 'lucide-react';

const INDIA_SEARCH_URL = 'https://nominatim.openstreetmap.org/search';

function coordinate(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function addressPart(address = {}) {
  return address.county || address.state_district || address.city_district || address.city
    || address.town || address.village || address.municipality || null;
}

function toLocation(result) {
  return {
    latitude: coordinate(result.lat),
    longitude: coordinate(result.lon),
    district: addressPart(result.address),
    state: result.address?.state || null,
    label: result.display_name || result.name || 'Selected location',
    source: 'OpenStreetMap Nominatim',
  };
}

export default function LocationSearchControl({ fallbackLocation, value, onChange }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [locating, setLocating] = useState(false);
  const [error, setError] = useState('');

  const search = async (event) => {
    event?.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;
    setSearching(true);
    setError('');
    try {
      const params = new URLSearchParams({
        format: 'jsonv2',
        addressdetails: '1',
        countrycodes: 'in',
        limit: '5',
        q: trimmed,
      });
      const response = await fetch(`${INDIA_SEARCH_URL}?${params}`, {
        headers: { Accept: 'application/json' },
      });
      if (!response.ok) throw new Error('Location search is temporarily unavailable.');
      const nextResults = await response.json();
      setResults(Array.isArray(nextResults) ? nextResults : []);
      if (!nextResults?.length) setError('No Indian location matched. Try a village, district, state, or landmark.');
    } catch (reason) {
      setResults([]);
      setError(reason.message || 'Location search is temporarily unavailable.');
    } finally {
      setSearching(false);
    }
  };

  const useCurrentLocation = () => {
    if (!navigator.geolocation) {
      setError('GPS is unavailable. Search for a location instead.');
      return;
    }
    setLocating(true);
    setError('');
    navigator.geolocation.getCurrentPosition(
      (position) => {
        onChange?.({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          label: 'Current location',
          source: 'device GPS',
        });
        setLocating(false);
      },
      () => {
        setError('GPS permission was unavailable. Search for a location instead.');
        setLocating(false);
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 300000 },
    );
  };

  const resetToFarm = () => {
    setQuery('');
    setResults([]);
    setError('');
    onChange?.(null);
  };

  return <section className="rounded-2xl border border-primary/15 bg-primary-50/60 p-4" aria-label="Search providers by Indian location">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <p className="flex items-center gap-2 text-sm font-bold text-text-primary"><MapPin size={17} className="text-primary" />Search anywhere in India</p>
        <p className="mt-1 max-w-2xl text-xs leading-5 text-text-secondary">Search a village, district, state, landmark, or PIN code. Results are ranked from the selected location and remain discovery-only.</p>
      </div>
      <div className="flex flex-wrap gap-2">
        <button type="button" onClick={resetToFarm} className="rounded-lg border border-primary/20 bg-white px-3 py-2 text-xs font-semibold text-primary">Use selected farm</button>
        <button type="button" onClick={useCurrentLocation} disabled={locating} className="inline-flex items-center gap-1.5 rounded-lg border border-primary/20 bg-white px-3 py-2 text-xs font-semibold text-primary disabled:opacity-60">
          {locating ? <LoaderCircle size={14} className="animate-spin" /> : <Crosshair size={14} />}{locating ? 'Locating…' : 'Use GPS'}
        </button>
      </div>
    </div>
    <form onSubmit={search} className="mt-3 flex gap-2" role="search">
      <label className="relative min-w-0 flex-1">
        <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
        <span className="sr-only">Search Indian location</span>
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="e.g. Wardha, Maharashtra or 442001" className="w-full rounded-lg border border-border bg-white py-2.5 pl-9 pr-3 text-sm outline-none ring-primary/20 focus:ring-2" />
      </label>
      <button type="submit" disabled={searching || !query.trim()} className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">
        {searching ? <LoaderCircle size={14} className="animate-spin" /> : <Search size={14} />}{searching ? 'Searching…' : 'Search'}
      </button>
    </form>
    {results.length > 0 && <div className="mt-2 overflow-hidden rounded-lg border border-border bg-white shadow-card">
      {results.map((result) => <button type="button" key={`${result.place_id}-${result.lat}`} onClick={() => { onChange?.(toLocation(result)); setQuery(result.display_name || result.name || ''); setResults([]); }} className="block w-full border-b border-border px-3 py-2.5 text-left text-xs leading-5 last:border-b-0 hover:bg-primary-50">
        <span className="font-semibold text-text-primary">{result.name || 'Selected place'}</span><span className="block text-text-secondary">{result.display_name}</span>
      </button>)}
      <p className="px-3 py-2 text-[10px] text-text-muted">Search results © OpenStreetMap contributors</p>
    </div>}
    {error && <p className="mt-2 flex items-start gap-1.5 rounded-lg bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-900"><X size={14} className="mt-0.5 shrink-0" />{error}</p>}
    <p className="mt-3 text-xs text-text-secondary">Search origin: <b className="text-text-primary">{value?.label || fallbackLocation?.label || 'Selected farm'}</b>{value?.source && <span> · {value.source}</span>}{value?.latitude != null && value?.longitude != null && <span> · {Number(value.latitude).toFixed(4)}, {Number(value.longitude).toFixed(4)}</span>}</p>
  </section>;
}
