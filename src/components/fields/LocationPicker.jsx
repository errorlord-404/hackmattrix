import { useEffect, useMemo, useState } from 'react';
import { Crosshair, LoaderCircle, MapPin, Search, X } from 'lucide-react';
import L from 'leaflet';
import { MapContainer, Marker, Popup, TileLayer, useMap, useMapEvents } from 'react-leaflet';

const INDIA_CENTER = [20.5937, 78.9629];

function coordinate(value) {
  if (value === '' || value == null) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function RecenterMap({ point }) {
  const map = useMap();
  useEffect(() => { if (point) map.setView(point, Math.max(map.getZoom(), 15), { animate: true }); }, [map, point]);
  return null;
}

function MapClickHandler({ onChange }) {
  useMapEvents({ click: (event) => onChange({ latitude: event.latlng.lat, longitude: event.latlng.lng }) });
  return null;
}

export default function LocationPicker({ latitude, longitude, fallbackLocation, onChange, agentGuided = false }) {
  const [point, setPoint] = useState(() => ({ latitude: coordinate(latitude), longitude: coordinate(longitude) }));
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [locating, setLocating] = useState(false);
  const [error, setError] = useState('');

  const selectedPoint = useMemo(() => {
    const nextLatitude = coordinate(latitude) ?? point.latitude;
    const nextLongitude = coordinate(longitude) ?? point.longitude;
    return nextLatitude != null && nextLongitude != null ? [nextLatitude, nextLongitude] : null;
  }, [latitude, longitude, point.latitude, point.longitude]);

  const initialCenter = useMemo(() => {
    if (selectedPoint) return selectedPoint;
    const fallbackLatitude = coordinate(fallbackLocation?.latitude);
    const fallbackLongitude = coordinate(fallbackLocation?.longitude);
    return fallbackLatitude != null && fallbackLongitude != null ? [fallbackLatitude, fallbackLongitude] : INDIA_CENTER;
  }, [fallbackLocation?.latitude, fallbackLocation?.longitude, selectedPoint]);

  const pinIcon = useMemo(() => L.divIcon({
    className: 'kisansathi-map-pin',
    html: '<span aria-hidden="true"></span>',
    iconSize: [34, 42],
    iconAnchor: [17, 42],
  }), []);

  const updatePoint = (nextPoint) => {
    setPoint(nextPoint);
    onChange?.(nextPoint);
    setError('');
  };

  const searchLocation = async (event) => {
    event?.preventDefault();
    const trimmedQuery = query.trim();
    if (!trimmedQuery) return;
    setSearching(true);
    setError('');
    try {
      const response = await fetch(`https://nominatim.openstreetmap.org/search?format=jsonv2&limit=5&addressdetails=1&q=${encodeURIComponent(trimmedQuery)}`, { headers: { Accept: 'application/json' } });
      if (!response.ok) throw new Error('Location search is temporarily unavailable.');
      const nextResults = await response.json();
      setResults(nextResults);
      if (!nextResults.length) setError('No matching location found. Try a village, district, or landmark.');
    } catch (searchError) {
      setResults([]);
      setError(searchError.message || 'Location search is temporarily unavailable.');
    } finally {
      setSearching(false);
    }
  };

  const useCurrentLocation = () => {
    if (!navigator.geolocation) {
      setError('This browser does not provide GPS location. Search or tap the map instead.');
      return;
    }
    setLocating(true);
    setError('');
    navigator.geolocation.getCurrentPosition(
      (position) => {
        updatePoint({ latitude: position.coords.latitude, longitude: position.coords.longitude });
        setLocating(false);
      },
      () => {
        setError('GPS permission was unavailable. Search or tap the map to choose a location.');
        setLocating(false);
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 300000 },
    );
  };

  const chooseResult = (result) => {
    updatePoint({ latitude: Number(result.lat), longitude: Number(result.lon) });
    setQuery(result.display_name);
    setResults([]);
  };

  return <div className="mt-5 rounded-xl border border-border bg-surface-muted p-3">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <p className="flex items-center gap-2 text-sm font-bold text-text-primary"><MapPin size={17} className="text-primary" /> Choose field location</p>
        <p className="mt-1 max-w-lg text-xs leading-5 text-text-secondary">{agentGuided ? 'Step 1: tap “Use my location” and approve GPS, or search/tap the map. Then place the pin on your farm before tracing its corners.' : 'Search for your farm, use GPS, or tap and drag the pin. You can trace the field boundary in the next step.'}</p>
      </div>
      <button type="button" onClick={useCurrentLocation} disabled={locating} className="inline-flex items-center gap-1.5 rounded-lg border border-primary/20 bg-white px-3 py-2 text-xs font-semibold text-primary disabled:opacity-60">
        {locating ? <LoaderCircle size={14} className="animate-spin" /> : <Crosshair size={14} />}{locating ? 'Locating…' : 'Use my location'}
      </button>
    </div>
    <div role="search" className="mt-3 flex gap-2">
      <div className="relative min-w-0 flex-1"><Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" /><input value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') searchLocation(event); }} placeholder="Search village, district, or landmark" aria-label="Search location" className="w-full rounded-lg border border-border bg-white py-2.5 pl-9 pr-3 text-sm outline-none ring-primary/20 focus:ring-2" /></div>
      <button type="button" onClick={() => searchLocation()} disabled={searching || !query.trim()} className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">{searching ? <LoaderCircle size={14} className="animate-spin" /> : <Search size={14} />}{searching ? 'Searching…' : 'Search'}</button>
    </div>
    {results.length > 0 && <div className="mt-2 overflow-hidden rounded-lg border border-border bg-white shadow-card">{results.map((result) => <button type="button" key={`${result.place_id}-${result.lat}`} onClick={() => chooseResult(result)} className="block w-full border-b border-border px-3 py-2.5 text-left text-xs leading-5 last:border-b-0 hover:bg-primary-50"><span className="font-semibold text-text-primary">{result.name || 'Selected place'}</span><span className="block text-text-secondary">{result.display_name}</span></button>)}<p className="px-3 py-2 text-[10px] text-text-muted">Search results © OpenStreetMap contributors</p></div>}
    {error && <p className="mt-2 flex items-start gap-1.5 rounded-lg bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-900"><X size={14} className="mt-0.5 shrink-0" />{error}</p>}
    <div className="relative z-0 mt-3 overflow-hidden rounded-xl border border-border bg-[#d9ead3]">
      <MapContainer center={initialCenter} zoom={selectedPoint ? 15 : 5} scrollWheelZoom className="h-64 w-full sm:h-72" aria-label="Choose field location on map">
        <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        <MapClickHandler onChange={updatePoint} />
        <RecenterMap point={selectedPoint} />
        {selectedPoint && <Marker position={selectedPoint} draggable icon={pinIcon} eventHandlers={{ dragend: (event) => { const next = event.target.getLatLng(); updatePoint({ latitude: next.lat, longitude: next.lng }); } }}><Popup>Drag this pin to your field</Popup></Marker>}
      </MapContainer>
      <div className="pointer-events-none absolute bottom-3 left-3 z-[500] rounded-lg bg-white/90 px-3 py-2 text-[11px] font-medium text-text-secondary shadow-card">Tap map to place · drag pin to adjust</div>
    </div>
    <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs">
      <span className="text-text-secondary">{selectedPoint ? 'Location selected' : 'Location required before creating the field'}</span>
      {selectedPoint && <span className="rounded-full bg-primary-50 px-2.5 py-1 font-semibold text-primary">{selectedPoint[0].toFixed(5)}, {selectedPoint[1].toFixed(5)}</span>}
    </div>
  </div>;
}
