import { useState } from 'react';
import { ArrowRight, Droplets, Map, Plus, Sprout, X } from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';
import { farmImages } from '../data/images.js';
import { useLanguage } from '../hooks/useLanguage.jsx';
import { useFarmData } from '../context/FarmDataContext.jsx';
import { EmptyState, ErrorState, LoadingState } from '../components/feedback/ApiState.jsx';
import LocationPicker from '../components/fields/LocationPicker.jsx';
import FieldBoundaryEditor from '../components/fields/FieldBoundaryEditor.jsx';
import { boundaryAreaAcres, boundaryError, editableBoundaryPoints, farmerDrawnBoundary } from '../components/fields/fieldBoundary.js';

const cropImages = [farmImages.wheat, farmImages.potato, farmImages.mustard];

function approximateBoundary(latitude, longitude) {
  const lat = Number(latitude); const lon = Number(longitude); const delta = 0.001;
  return { type: 'Feature', properties: { quality: 'approximate_point_buffer' }, geometry: { type: 'Polygon', coordinates: [[[lon - delta, lat - delta], [lon + delta, lat - delta], [lon + delta, lat + delta], [lon - delta, lat + delta], [lon - delta, lat - delta]]] } };
}

function AddFieldDialog({ onClose, onCreate, onUpdate, profile, field = null, agentGuided = false }) {
  const [form, setForm] = useState({ name: field?.name || '', area_acres: field?.area_acres || '', current_crop: field?.current_crop || '', latitude: field?.centroid_lat ?? profile?.latitude ?? '', longitude: field?.centroid_lon ?? profile?.longitude ?? '' });
  const [boundaryMode, setBoundaryMode] = useState('drawn');
  const [corners, setCorners] = useState(() => field?.boundary_geojson?.properties?.quality === 'approximate_point_buffer' ? [] : editableBoundaryPoints(field?.boundary_geojson));
  const [error, setError] = useState(''); const [saving, setSaving] = useState(false);
  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }));
  const submit = async (event) => {
    event.preventDefault(); setError('');
    if (form.latitude === '' || form.longitude === '') { setError('Choose the field location first.'); return; }
    if (boundaryMode === 'drawn' && boundaryError(corners)) { setError(boundaryError(corners)); return; }
    setSaving(true);
    try {
      const body = { name: form.name, area_acres: Number(form.area_acres), current_crop: form.current_crop || null, boundary_geojson: boundaryMode === 'drawn' ? farmerDrawnBoundary(corners) : approximateBoundary(form.latitude, form.longitude) };
      if (field) await onUpdate(field.id, body); else await onCreate(body);
      onClose();
    } catch (err) { setError(err.message); } finally { setSaving(false); }
  };
  const areaDifference = corners.length >= 3 && Number(form.area_acres) > 0
    ? Math.abs(boundaryAreaAcres(corners) - Number(form.area_acres)) / Number(form.area_acres) : 0;
  return <div className="fixed inset-0 z-50 overflow-y-auto bg-black/35 p-4"><div className="grid min-h-full place-items-center"><form onSubmit={submit} className="w-full max-w-2xl rounded-2xl border border-border bg-white p-6 shadow-xl"><div className="flex items-start justify-between"><div><h2 className="text-lg font-bold">{field ? `Review ${field.name} boundary` : 'Add field'}</h2><p className="mt-1 text-xs text-text-secondary">{field ? 'Trace the actual corners to replace the saved approximate or unclassified boundary.' : 'Find your field, then trace its corners. You can choose an approximate pin if the map is unclear.'}</p></div><button type="button" onClick={onClose} aria-label="Close"><X size={20} /></button></div><div className="mt-5 grid gap-3 sm:grid-cols-2"><input required value={form.name} onChange={(event) => update('name', event.target.value)} placeholder="Field name" aria-label="Field name" className="rounded-lg border border-border px-3 py-2 text-sm" /><input required type="number" min="0.01" step="any" value={form.area_acres} onChange={(event) => update('area_acres', event.target.value)} placeholder="Area in acres" aria-label="Area in acres" className="rounded-lg border border-border px-3 py-2 text-sm" /><input value={form.current_crop} onChange={(event) => update('current_crop', event.target.value)} placeholder="Current crop (optional)" aria-label="Current crop" className="rounded-lg border border-border px-3 py-2 text-sm sm:col-span-2" /></div><LocationPicker latitude={form.latitude} longitude={form.longitude} fallbackLocation={profile} agentGuided={agentGuided} onChange={(location) => setForm((current) => ({ ...current, latitude: location.latitude, longitude: location.longitude }))} />
    <fieldset className="mt-4"><legend className="text-sm font-bold text-text-primary">How should we mark the field?</legend><div className="mt-2 grid gap-2 sm:grid-cols-2"><label className={`cursor-pointer rounded-xl border p-3 text-xs ${boundaryMode === 'drawn' ? 'border-primary bg-primary-50 text-primary-dark' : 'border-border'}`}><input type="radio" name="boundary-mode" checked={boundaryMode === 'drawn'} onChange={() => setBoundaryMode('drawn')} className="mr-2 accent-primary" />Draw my boundary<span className="mt-1 block text-text-secondary">Trace and adjust corners on a map.</span></label><label className={`cursor-pointer rounded-xl border p-3 text-xs ${boundaryMode === 'approximate' ? 'border-primary bg-primary-50 text-primary-dark' : 'border-border'}`}><input type="radio" name="boundary-mode" checked={boundaryMode === 'approximate'} onChange={() => setBoundaryMode('approximate')} className="mr-2 accent-primary" />Use approximate pin<span className="mt-1 block text-text-secondary">A rough square only; not your actual boundary.</span></label></div></fieldset>
    {boundaryMode === 'drawn' ? <FieldBoundaryEditor latitude={form.latitude} longitude={form.longitude} points={corners} onChange={setCorners} /> : <p className="mt-3 rounded-lg bg-amber-50 p-3 text-xs text-amber-900">We will save a rough map buffer around the pin, clearly marked as approximate. It is not suitable for area or legal measurements.</p>}
    {boundaryMode === 'drawn' && areaDifference > 0.25 && <p className="mt-3 rounded-lg bg-amber-50 p-3 text-xs text-amber-900">The drawn map estimate differs from the acreage you entered by more than 25%. Please check both before saving.</p>}
    {error && <p role="alert" className="mt-3 rounded-lg bg-red-50 p-3 text-xs text-red-800">{error}</p>}<button disabled={saving || (boundaryMode === 'drawn' && Boolean(boundaryError(corners)))} className="mt-5 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{saving ? 'Saving…' : field ? 'Save boundary changes' : 'Save this field'}</button></form></div></div>;
}

export default function MyFields() {
  const { language } = useLanguage(); const hi = language === 'hi'; const { profile, fields, mapFields, loading, error, refresh, createField, updateField } = useFarmData(); const [showAdd, setShowAdd] = useState(false); const [reviewField, setReviewField] = useState(null); const [searchParams, setSearchParams] = useSearchParams(); const displayFields = fields.map((field) => ({ ...field, ...(mapFields.find((mappedField) => mappedField.id === field.id) || {}) }));
  const addRequested = searchParams.get('add') === '1';
  const guidedRequested = searchParams.get('guided') === '1';
  const requestedReviewField = searchParams.get('review') === '1' && !loading
    ? fields.find((field) => field.boundary_geojson?.properties?.quality !== 'farmer_drawn_unverified') || fields[0] : null;
  const closeDialog = () => {
    setShowAdd(false); setReviewField(null);
    const next = new URLSearchParams(searchParams);
    next.delete('add'); next.delete('guided'); next.delete('review');
    setSearchParams(next, { replace: true });
  };
  const label = hi ? { title: 'मेरी फसलें', subtitle: 'अपने हर खेत की स्थिति और प्रगति देखें।', add: 'खेत जोड़ें', moisture: 'मिट्टी की नमी', details: 'खेत का विवरण देखें', mapTitle: 'अपने सभी खेत फार्म मैप पर देखें', mapText: 'एक ही जगह पर खेत की सीमा और स्वास्थ्य स्थिति देखें।', mapAction: 'फार्म मैप खोलें' } : { title: 'My Fields', subtitle: 'Track the health and progress of every field.', add: 'Add field', moisture: 'Soil moisture', details: 'View field details', mapTitle: 'See all fields on your farm map', mapText: 'View field boundaries and health status in one place.', mapAction: 'Open Farm Map' };
  return <div className="mx-auto max-w-[1440px] px-4 py-5 sm:px-6 lg:px-8 lg:py-7">
    {(showAdd || addRequested) && <AddFieldDialog profile={profile} onClose={closeDialog} onCreate={createField} agentGuided={guidedRequested} />}
    {!(showAdd || addRequested) && (reviewField || requestedReviewField) && <AddFieldDialog field={reviewField || requestedReviewField} profile={profile} onClose={closeDialog} onUpdate={updateField} />}
    <header className="flex items-start justify-between"><div><h1 className="text-2xl font-bold">{label.title}</h1><p className="mt-1 text-sm text-text-secondary">{label.subtitle}</p></div><div className="flex gap-2"><Link to="/device-setup" className="rounded-lg border border-primary/25 bg-white px-3 py-2 text-xs font-semibold text-primary">Connect soil node</Link><button onClick={() => setShowAdd(true)} className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-white"><Plus size={15} />{label.add}</button></div></header>
    <div className="mt-6">{loading ? <LoadingState /> : error ? <ErrorState error={error} onRetry={refresh} /> : displayFields.length === 0 ? <EmptyState title="No fields yet" detail="Create your first field to unlock crop timelines, observations, alerts, and irrigation planning." action={<button onClick={() => setShowAdd(true)} className="mt-4 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-white">{label.add}</button>} /> : <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{displayFields.map((field, index) => <article className="overflow-hidden rounded-card border border-border bg-white shadow-card" key={field.id}><img className="h-32 w-full object-cover" src={cropImages[index % cropImages.length]} alt="Field crop" /><div className="p-5"><div className="flex items-start justify-between"><div><div className="flex items-center gap-2"><span className="rounded-lg bg-primary-50 p-1.5 text-primary"><Sprout size={15} /></span><h2 className="font-bold">{field.name}</h2></div><p className="mt-2 text-xs text-text-secondary">{field.current_crop || 'Crop not recorded'} · {field.area_acres} acres</p></div><span className="rounded-full bg-primary-50 px-2 py-1 text-[10px] font-bold text-primary">{field.status}</span></div><p className="mt-4 text-sm font-semibold text-primary-dark">{field.current_crop || 'No active crop cycle'}</p><div className="mt-2 flex items-center justify-between text-xs text-text-secondary"><span className="flex items-center gap-1"><Droplets size={14} className="text-info" />{label.moisture}</span><b>{field.latest_moisture_percent == null ? '—' : `${field.latest_moisture_percent}%`}</b></div><div className="mt-2 h-2 rounded-full bg-surface-muted"><div className="h-full rounded-full bg-primary" style={{ width: `${Math.min(field.latest_moisture_percent || 0, 100)}%` }} /></div><Link to={`/fields/${field.id}`} className="mt-5 flex items-center justify-between border-t border-border pt-4 text-xs font-semibold text-primary">{label.details}<ArrowRight size={15} /></Link></div></article>)}</div>}</div>
    <section className="mt-6 rounded-card border border-border bg-primary-50 p-5"><div className="flex items-start gap-3"><span className="rounded-lg bg-white p-2 text-primary"><Map size={21} /></span><div><h2 className="font-bold text-primary-dark">{label.mapTitle}</h2><p className="mt-1 text-sm text-text-secondary">{label.mapText}</p><Link className="mt-3 inline-flex items-center gap-1 text-sm font-bold text-primary" to="/map">{label.mapAction}<ArrowRight size={15} /></Link></div></div></section>
  </div>;
}
