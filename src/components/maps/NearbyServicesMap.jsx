import { useEffect, useMemo, useState } from 'react';
import { Circle, MapContainer, Marker, Popup, TileLayer, useMap } from 'react-leaflet';
import L from 'leaflet';

function Recenter({ location, items }) {
  const map = useMap();
  const points = useMemo(() => [location, ...items].filter((item) => Number.isFinite(Number(item?.latitude)) && Number.isFinite(Number(item?.longitude))).map((item) => [Number(item.latitude), Number(item.longitude)]), [items, location]);
  useEffect(() => {
    if (points.length > 1) {
      const bounds = L.latLngBounds(points);
      map.fitBounds(bounds, { padding: [24, 24], maxZoom: 14 });
    } else if (points[0]) map.setView(points[0], 13);
  }, [map, points]);
  return null;
}

export default function NearbyServicesMap({ location, items, selectedId, onSelect, radiusKm = 25 }) {
  const [tileError, setTileError] = useState(false);
  const center = [Number(location?.latitude) || 20.5937, Number(location?.longitude) || 78.9629];
  return <div className="relative z-0 h-[360px] overflow-hidden rounded-card border border-border shadow-card">
    <MapContainer center={center} zoom={12} scrollWheelZoom className="h-full w-full" aria-label="Nearby services map">
      <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" eventHandlers={{ tileerror: () => setTileError(true) }} />
      <Recenter location={location} items={items} />
      {location?.latitude != null && location?.longitude != null && <Circle center={center} radius={radiusKm * 1000} pathOptions={{ color: '#2e7d32', fillColor: '#8fbd64', fillOpacity: 0.08 }} />}
      {location?.latitude != null && location?.longitude != null && <Marker position={center}><Popup><b>{location.label || 'Selected farm'}</b><br />Search origin</Popup></Marker>}
      {items.map((item) => item.latitude != null && item.longitude != null && <Marker key={item.id} position={[item.latitude, item.longitude]} eventHandlers={{ click: () => onSelect?.(item) }} opacity={selectedId === item.id ? 1 : 0.82}><Popup><b>{item.title || item.name}</b><br />{item.provider_name || 'Provider'}<br />{item.distance_km == null ? 'Distance unavailable' : `${item.distance_km} km away`}</Popup></Marker>)}
    </MapContainer>
    {tileError && <span role="status" className="absolute left-3 top-3 z-[500] rounded-lg bg-amber-100 px-3 py-2 text-xs text-amber-900">Map tiles unavailable. Use List View for the same provider records.</span>}
    <span className="pointer-events-none absolute bottom-3 left-3 z-[500] rounded-lg bg-black/60 px-3 py-2 text-xs text-white">Nearby providers · source-attributed</span>
  </div>;
}
