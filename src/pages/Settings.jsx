import { useEffect, useState } from 'react';
import { Bell, Database, Download, Globe, KeyRound, RefreshCw, Save, SlidersHorizontal, UserRound, Volume2, XCircle } from 'lucide-react';
import { useLanguage } from '../hooks/useLanguage.jsx';
import { useFarmData } from '../context/FarmDataContext.jsx';
import HarnessStatusCard from '../components/features/ai/HarnessStatusCard.jsx';
import { farmStateApi } from '../api/farmStateApi.js';
import { referenceApi } from '../api/referenceApi.js';
import { FARM_STATE_API_URL, getFarmerId } from '../api/client.js';

export default function Settings() {
  const { language, setLanguage, t } = useLanguage();
  const { profile, saveProfile } = useFarmData();
  const [saving, setSaving] = useState(false); const [message, setMessage] = useState('');
  const [storage, setStorage] = useState({ loading: true, farmState: null, health: null, diagnostics: null, error: '' });
  const [storageRefreshToken, setStorageRefreshToken] = useState(0);
  const [exportMessage, setExportMessage] = useState('');
  const [demoLoading, setDemoLoading] = useState(false);
  const [form, setForm] = useState({ name: '', phone: '', location: '', latitude: '', longitude: '', notifications: true });
  const [sarvam, setSarvam] = useState({ loading: true, error: '', configured: false });
  const [sarvamSaving, setSarvamSaving] = useState(false);
  const [sarvamTesting, setSarvamTesting] = useState(false);
  const [sarvamMessage, setSarvamMessage] = useState('');
  const [sarvamForm, setSarvamForm] = useState({ api_key: '', stt_model: 'saaras:v3', stt_language_code: 'unknown', tts_model: 'bulbul:v3', tts_speaker: 'shubh', tts_pace: 1, translate_model: 'mayura:v1' });
  // Populate the editable form when the local profile arrives.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { if (profile) setForm({ name: profile.name || '', phone: profile.phone || '', location: profile.location || '', latitude: profile.latitude ?? '', longitude: profile.longitude ?? '', notifications: profile.notification_preferences?.enabled ?? true }); }, [profile]);
  useEffect(() => {
    let active = true;
    Promise.all([farmStateApi.getStorageStatus(), referenceApi.getBackendHealth(), farmStateApi.getDiagnostics()])
      .then(([farmState, health, diagnostics]) => { if (active) setStorage({ loading: false, farmState, health, diagnostics, error: '' }); })
      .catch((error) => { if (active) setStorage({ loading: false, farmState: null, health: null, diagnostics: null, error: error.message }); });
    return () => { active = false; };
  }, [storageRefreshToken]);
  useEffect(() => {
    let active = true;
    farmStateApi.getSarvamRuntimeConfig()
      .then((config) => { if (active) { setSarvam({ ...config, loading: false, error: '' }); setSarvamForm((current) => ({ ...current, ...config, api_key: '' })); } })
      .catch((error) => { if (active) setSarvam({ loading: false, error: error.message, configured: false }); });
    return () => { active = false; };
  }, []);
  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }));
  const updateSarvam = (key, value) => setSarvamForm((current) => ({ ...current, [key]: value }));
  const submit = async (event) => { event.preventDefault(); setSaving(true); setMessage(''); try { await saveProfile({ name: form.name, phone: form.phone || null, location: form.location || null, preferred_language: language, latitude: form.latitude === '' ? null : Number(form.latitude), longitude: form.longitude === '' ? null : Number(form.longitude), notification_preferences: { enabled: form.notifications, channels: ['in_app'] } }); setMessage('Profile saved locally.'); } catch (error) { setMessage(error.message); } finally { setSaving(false); } };
  const saveSarvam = async (event) => { event.preventDefault(); setSarvamSaving(true); setSarvamMessage(''); try { const body = { ...sarvamForm, api_key: sarvamForm.api_key || undefined, tts_pace: Number(sarvamForm.tts_pace) }; const config = await farmStateApi.updateSarvamRuntimeConfig(body); setSarvam({ ...config, loading: false, error: '' }); setSarvamForm((current) => ({ ...current, ...config, api_key: '' })); setSarvamMessage(config.configured ? 'Sarvam is configured for this backend session.' : 'Voice settings saved. Add a key to enable Sarvam.'); } catch (error) { setSarvamMessage(error.message); } finally { setSarvamSaving(false); } };
  const testSarvamVoice = async () => {
    setSarvamTesting(true); setSarvamMessage('');
    try {
      if (!sarvam.configured) throw new Error('Apply a Sarvam API key before testing voice.');
      const voiceTest = {
        hi: { language_code: 'hi-IN', text: 'किसानसाथी वॉइस टेस्ट। आपकी आवाज़ सेवा कनेक्ट हो गई है।' },
        mr: { language_code: 'mr-IN', text: 'किसानसाथी आवाज चाचणी. तुमची आवाज सेवा जोडली गेली आहे.' },
        en: { language_code: 'en-IN', text: 'KisanSathi voice test. Your speech service is connected.' },
      }[language] || { language_code: 'en-IN', text: 'KisanSathi voice test. Your speech service is connected.' };
      const result = await farmStateApi.synthesizeSpeech(voiceTest);
      if (result.status !== 'completed' || !result.audio_base64) throw new Error(result.message || 'Sarvam did not return playable audio.');
      const audio = new Audio(`data:${result.audio_mime_type || 'audio/wav'};base64,${result.audio_base64}`);
      await audio.play();
      setSarvamMessage('Voice connection succeeded. You should hear the KisanSathi test message.');
    } catch (error) { setSarvamMessage(`Voice test failed: ${error.message}`); } finally { setSarvamTesting(false); }
  };
  const clearSarvamKey = async () => {
    if (!window.confirm('Clear the active Sarvam key? Voice, translation, and speech will stop until you add it again.')) return;
    setSarvamSaving(true); setSarvamMessage('');
    try {
      const config = await farmStateApi.updateSarvamRuntimeConfig({ clear_api_key: true });
      setSarvam({ ...config, loading: false, error: '' });
      setSarvamForm((current) => ({ ...current, ...config, api_key: '' }));
      setSarvamMessage('The active Sarvam key was cleared from this backend session.');
    } catch (error) { setSarvamMessage(error.message); } finally { setSarvamSaving(false); }
  };
  const exportFarmData = async () => { setExportMessage('Preparing export…'); try { const payload = await farmStateApi.exportSnapshot(); const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' }); const url = URL.createObjectURL(blob); const anchor = document.createElement('a'); anchor.href = url; anchor.download = `kisansathi-farm-export-${new Date().toISOString().slice(0, 10)}.json`; anchor.click(); URL.revokeObjectURL(url); setExportMessage('Farm snapshot downloaded.'); } catch (error) { setExportMessage(error.message); } };
  const loadDemoData = async () => { if (!window.confirm('Load or repair the local demo farmer fixture?')) return; setDemoLoading(true); setExportMessage('Loading demo data…'); try { await farmStateApi.loadDemoData(); setExportMessage('Demo farmer data is ready.'); setStorageRefreshToken((value) => value + 1); } catch (error) { setExportMessage(error.message); } finally { setDemoLoading(false); } };

  return (
    <div className="mx-auto max-w-3xl px-4 py-5 sm:px-6 lg:px-8 lg:py-7">
      {/* Page Header */}
      <h1 className="text-2xl font-bold">{t('settings')}</h1>
      <p className="mt-1 text-sm text-text-secondary">
        {t('settingsPage.description')}
      </p>

      {/* Settings Card Container */}
      <form id="profile" onSubmit={submit} className="mt-6 overflow-hidden rounded-card border border-border bg-white shadow-card">
        {/* User Profile Section */}
        <div className="flex items-center gap-3 border-b border-border p-5">
          <span className="grid size-10 place-items-center rounded-xl bg-primary-50 text-primary">
            <UserRound size={20} />
          </span>
          <div className="grid flex-1 gap-3 sm:grid-cols-2">
            <input required value={form.name} onChange={(event) => update('name', event.target.value)} placeholder="Farmer name" className="rounded-lg border border-border px-3 py-2 text-sm" />
            <input value={form.phone} onChange={(event) => update('phone', event.target.value)} placeholder="Phone (optional)" className="rounded-lg border border-border px-3 py-2 text-sm" />
            <input value={form.location} onChange={(event) => update('location', event.target.value)} placeholder="Village, district, state" className="rounded-lg border border-border px-3 py-2 text-sm sm:col-span-2" />
            <input type="number" step="any" min="-90" max="90" value={form.latitude} onChange={(event) => update('latitude', event.target.value)} placeholder="Latitude" className="rounded-lg border border-border px-3 py-2 text-sm" />
            <input type="number" step="any" min="-180" max="180" value={form.longitude} onChange={(event) => update('longitude', event.target.value)} placeholder="Longitude" className="rounded-lg border border-border px-3 py-2 text-sm" />
          </div>
        </div>

        {/* Language Preferences Section */}
        <div className="flex items-center gap-3 border-b border-border p-5">
          <span className="grid size-10 place-items-center rounded-xl bg-primary-50 text-primary">
            <Globe size={20} />
          </span>
          <div className="flex-1">
            <p className="font-bold">{t('language')}</p>
            <p className="text-xs text-text-secondary">
              {t('settingsPage.languageDescription')}
            </p>
          </div>
          <select
            value={language}
            onChange={(event) => setLanguage(event.target.value)}
            className="rounded-lg border border-border bg-white px-3 py-2 text-sm"
          >
            <option value="en">English</option>
            <option value="hi">हिंदी</option>
            <option value="mr">मराठी</option>
          </select>
        </div>

        {/* Notifications Button Option */}
        <label className="flex w-full items-center gap-3 p-5 text-left">
          <span className="grid size-10 place-items-center rounded-xl bg-primary-50 text-primary">
            <Bell size={20} />
          </span>
          <span className="flex-1">
            <span className="block font-bold">
              {t('settingsPage.notifications')}
            </span>
            <span className="block text-xs text-text-secondary">
              {t('settingsPage.notificationsDescription')}
            </span>
            <span className="mt-1 block text-xs text-text-muted">When enabled, new alerts appear in KisanSathi and as a desktop notification while this app is open. SMS and closed-app alerts are not configured.</span>
          </span>
          <input type="checkbox" checked={form.notifications} onChange={(event) => update('notifications', event.target.checked)} className="size-5 accent-primary" />
        </label>
        <div className="border-t border-border p-5"><button disabled={saving || !form.name.trim()} className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"><Save size={16} /> {saving ? 'Saving…' : 'Save profile'}</button></div>

      </form>

      {/* Footer Saved Status Note */}
      <p className="mt-4 text-xs text-text-muted">
        {message || 'Profile data is stored in the selected farmer SQLite store.'}
      </p>

      <section aria-label="Data connection status" className="mt-5 rounded-card border border-border bg-white p-5 shadow-card">
        <div className="flex items-start gap-3">
          <span className="grid size-10 place-items-center rounded-xl bg-primary-50 text-primary"><Database size={20} /></span>
          <div className="min-w-0 flex-1"><h2 className="font-bold">Data connection</h2><p className="text-xs text-text-secondary">Checks the exact farmer database selected by this app.</p></div>
          <button type="button" onClick={() => setStorageRefreshToken((value) => value + 1)} className="inline-flex items-center gap-1 rounded-lg border border-border px-3 py-2 text-xs font-semibold" aria-label="Refresh data connection"><RefreshCw size={14} /> Refresh</button>
        </div>
        <p className="mt-3 text-xs text-text-muted">Active API: <b>{FARM_STATE_API_URL}</b> · farmer: <b>{getFarmerId()}</b></p>
        {storage.loading ? <p className="mt-3 text-sm text-text-secondary">Checking backend connection…</p> : storage.error ? <p role="alert" className="mt-3 text-sm text-red-700">Cannot reach the backend: {storage.error}</p> : (
          <div className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
            <p className="rounded-lg bg-primary-50 px-3 py-2 text-primary-900">Farm data: connected ({storage.farmState.farm_state_store.replaceAll('_', ' ')})</p>
            <p className={`rounded-lg px-3 py-2 ${storage.health.reference_database === 'available' ? 'bg-primary-50 text-primary-900' : 'bg-amber-50 text-amber-900'}`}>Reference data: {storage.health.reference_database}</p>
          </div>
        )}
        {storage.diagnostics && <div className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
          <p className="rounded-lg border border-border px-3 py-2">Fields: <b>{storage.diagnostics.farmer_state.fields}</b> · open tasks: <b>{storage.diagnostics.farmer_state.open_tasks}</b> · open alerts: <b>{storage.diagnostics.farmer_state.open_alerts}</b></p>
          <p className="rounded-lg border border-border px-3 py-2">Reference catalog: <b>{storage.diagnostics.components.reference_database.counts.schemes}</b> schemes · <b>{storage.diagnostics.components.reference_database.counts.machinery}</b> machinery · <b>{storage.diagnostics.components.reference_database.counts.marketplace}</b> listings</p>
        </div>}
        {storage.diagnostics?.degraded_components?.length > 0 && <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-900">Degraded components: {storage.diagnostics.degraded_components.join(', ')}. Local farmer records remain usable; verify reference data before acting.</p>}
        <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-border pt-4"><button type="button" onClick={loadDemoData} disabled={demoLoading} className="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">{demoLoading ? 'Loading…' : 'Load demo data'}</button><button type="button" onClick={exportFarmData} className="inline-flex items-center gap-2 rounded-lg border border-primary/30 bg-primary-50 px-3 py-2 text-xs font-semibold text-primary-dark"><Download size={14} /> Export farm snapshot</button><span className="text-xs text-text-muted">Demo loading is local-only; export includes farmer-owned records and audit history.</span>{exportMessage && <span className="text-xs text-primary">{exportMessage}</span>}</div>
      </section>

      <section id="voice" aria-label="Sarvam voice configuration" className="mt-5 overflow-hidden rounded-card border border-border bg-white shadow-card">
        <div className="flex items-start gap-3 border-b border-border bg-primary-50/60 p-5">
          <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-primary text-white"><KeyRound size={20} /></span>
          <div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><h2 className="font-bold">Sarvam voice & language</h2><span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${sarvam.configured ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-900'}`}>{sarvam.configured ? 'Configured' : 'Key required'}</span></div><p className="mt-1 text-xs text-text-secondary">Set the active desktop-session key and defaults for transcription, speech, and translation.</p></div>
        </div>
        {sarvam.loading ? <p className="p-5 text-sm text-text-secondary">Reading voice configuration…</p> : sarvam.error ? <p role="alert" className="p-5 text-sm text-red-700">Cannot read Sarvam configuration: {sarvam.error}</p> : (
          <form onSubmit={saveSarvam} className="p-5">
            <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950">Your key is sent only to this local backend and retained in active process memory. It is never shown again, saved in farmer data, or written to this project. Restarting the backend clears a key entered here; use the deployment environment only when you need it available after restarts.</div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <label className="sm:col-span-2"><span className="mb-1 block text-xs font-semibold text-text-secondary">Sarvam API key</span><input type="password" autoComplete="off" value={sarvamForm.api_key} onChange={(event) => updateSarvam('api_key', event.target.value)} placeholder={sarvam.configured ? 'Leave blank to keep the active key' : 'Paste a Sarvam API key'} className="w-full rounded-lg border border-border px-3 py-2 text-sm" /></label>
              <label><span className="mb-1 block text-xs font-semibold text-text-secondary">Speech-to-text model</span><input value={sarvamForm.stt_model} onChange={(event) => updateSarvam('stt_model', event.target.value)} className="w-full rounded-lg border border-border px-3 py-2 text-sm" /></label>
              <label><span className="mb-1 block text-xs font-semibold text-text-secondary">Default STT language</span><input value={sarvamForm.stt_language_code} onChange={(event) => updateSarvam('stt_language_code', event.target.value)} placeholder="unknown, hi-IN, en-IN" className="w-full rounded-lg border border-border px-3 py-2 text-sm" /></label>
              <label><span className="mb-1 block text-xs font-semibold text-text-secondary">Text-to-speech model</span><input value={sarvamForm.tts_model} onChange={(event) => updateSarvam('tts_model', event.target.value)} className="w-full rounded-lg border border-border px-3 py-2 text-sm" /></label>
              <label><span className="mb-1 block text-xs font-semibold text-text-secondary">Voice</span><input value={sarvamForm.tts_speaker} onChange={(event) => updateSarvam('tts_speaker', event.target.value)} className="w-full rounded-lg border border-border px-3 py-2 text-sm" /></label>
              <label><span className="mb-1 block text-xs font-semibold text-text-secondary">Speech pace</span><input type="number" min="0.5" max="2" step="0.1" value={sarvamForm.tts_pace} onChange={(event) => updateSarvam('tts_pace', event.target.value)} className="w-full rounded-lg border border-border px-3 py-2 text-sm" /></label>
              <label><span className="mb-1 block text-xs font-semibold text-text-secondary">Translation model</span><input value={sarvamForm.translate_model} onChange={(event) => updateSarvam('translate_model', event.target.value)} className="w-full rounded-lg border border-border px-3 py-2 text-sm" /></label>
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-3"><button disabled={sarvamSaving} className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"><SlidersHorizontal size={16} /> {sarvamSaving ? 'Applying…' : 'Apply voice settings'}</button><button type="button" onClick={testSarvamVoice} disabled={!sarvam.configured || sarvamSaving || sarvamTesting} className="inline-flex items-center gap-2 rounded-lg border border-primary/30 bg-primary-50 px-4 py-2 text-sm font-semibold text-primary-dark disabled:opacity-50"><Volume2 size={16} /> {sarvamTesting ? 'Testing voice…' : 'Test voice'}</button>{sarvam.configured && <button type="button" onClick={clearSarvamKey} disabled={sarvamSaving || sarvamTesting} className="inline-flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm font-semibold text-red-700 disabled:opacity-50"><XCircle size={16} /> Clear session key</button>}<span role={sarvamMessage ? 'status' : undefined} className="text-xs text-text-muted">{sarvamMessage || `Storage: ${sarvam.api_key_storage}.`}</span></div>
          </form>
        )}
      </section>

      <HarnessStatusCard />

    </div>
  );
}
