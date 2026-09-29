import { useEffect, useMemo, useState } from 'react';
import { CornerDownLeft, RotateCcw } from 'lucide-react';
import L from 'leaflet';
import { MapContainer, Marker, Polygon, Polyline, TileLayer, useMap, useMapEvents } from 'react-leaflet';
import { boundaryAreaAcres, boundaryError } from './fieldBoundary.js';

function Recenter({ center }) {
  const map = useMap();
  useEffect(() => { if (center) map.setView(center, Math.max(map.getZoom(), 16)); }, [center, map]);
  return null;
}

function AddCorner({ onAdd }) {
  useMapEvents({ click: (event) => onAdd([event.latlng.lat, event.latlng.lng]) });
  return null;
}

export default function FieldBoundaryEditor({ latitude, longitude, points, onChange }) {
  const [initialCenter] = useState(() => [Number(latitude) || 20.5937, Number(longitude) || 78.9629]);
  const center = useMemo(() => Number.isFinite(Number(latitude)) && Number.isFinite(Number(longitude)) && latitude !== '' && longitude !== ''
    ? [Number(latitude), Number(longitude)] : null, [latitude, longitude]);
  const cornerIcon = useMemo(() => L.divIcon({ className: 'kisansathi-map-pin', html: '<span aria-hidden="true"></span>', iconSize: [34, 42], iconAnchor: [17, 42] }), []);
  const issue = points.length ? boundaryError(points) : null;
  const area = boundaryAreaAcres(points);
  const moveCorner = (index, next) => onChange(points.map((point, pointIndex) => pointIndex === index ? next : point));

  return <section className="mt-4 rounded-xl border border-primary/20 bg-primary-50/60 p-3" aria-label="Draw field boundary">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div><h3 className="text-sm font-bold text-primary-dark">Trace your field</h3><p className="mt-1 text-xs leading-5 text-text-secondary">Tap each corner in order, then drag a corner to adjust it. This is your drawing, not a land survey.</p></div>
      <div className="flex gap-2"><button type="button" disabled={!points.length} onClick={() => onChange(points.slice(0, -1))} className="inline-flex items-center gap-1 rounded-lg border border-primary/20 bg-white px-2.5 py-1.5 text-xs font-semibold text-primary disabled:opacity-40"><CornerDownLeft size={13} />Undo</button><button type="button" disabled={!points.length} onClick={() => onChange([])} className="inline-flex items-center gap-1 rounded-lg border border-primary/20 bg-white px-2.5 py-1.5 text-xs font-semibold text-primary disabled:opacity-40"><RotateCcw size={13} />Clear</button></div>
    </div>
    <div className="relative z-0 mt-3 overflow-hidden rounded-xl border border-border bg-[#d9ead3]">
      <MapContainer center={initialCenter} zoom={center ? 16 : 5} scrollWheelZoom className="h-64 w-full sm:h-80" aria-label="Tap field corners on map">
        <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        <Recenter center={center} /><AddCorner onAdd={(point) => { if (points.length < 100) onChange([...points, point]); }} />
        {points.length > 2 ? <Polygon positions={points} pathOptions={{ color: '#166534', weight: 3, fillColor: '#4ade80', fillOpacity: 0.23 }} /> : points.length > 1 ? <Polyline positions={points} pathOptions={{ color: '#166534', weight: 3 }} /> : null}
        {points.map((point, index) => <Marker key={index} position={point} draggable icon={cornerIcon} eventHandlers={{ dragend: (event) => { const next = event.target.getLatLng(); moveCorner(index, [next.lat, next.lng]); } }} />)}
      </MapContainer>
      <span className="pointer-events-none absolute bottom-3 left-3 z-[500] rounded-lg bg-white/90 px-3 py-2 text-[11px] font-semibold text-primary-dark shadow-card">{points.length} corners · tap map to add</span>
    </div>
    <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs"><span className={issue ? 'text-amber-800' : 'text-primary-dark'}>{issue || 'Boundary ready for review. Verify its position before saving.'}</span>{points.length >= 3 && <strong className="rounded-full bg-white px-3 py-1 text-primary-dark">Map estimate: {area.toFixed(2)} acres</strong>}</div>
  </section>;
}
