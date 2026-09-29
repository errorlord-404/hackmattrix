import { CheckCircle2, CircleAlert, LoaderCircle, RefreshCw, Volume2 } from 'lucide-react';
import { useAIConversation } from '../../../context/AIConversationContext.jsx';

const labels = {
  codex: 'Codex app-server',
  plugin: 'KisanSathi tools',
  backend: 'Farm data service',
  sarvam: 'Sarvam voice',
};

function StatusIcon({ status }) {
  if (status === 'available' || status === 'ok' || status === 'configured' || status === 'ready') return <CheckCircle2 size={16} className="text-emerald-600" />;
  if (status === 'starting' || status === 'unknown' || status === 'checking') return <LoaderCircle size={16} className="animate-spin text-amber-600" />;
  return <CircleAlert size={16} className="text-red-600" />;
}

function statusText(name, value) {
  if (name === 'codex') return value?.running ? 'Connected' : value?.lastError || 'Not started';
  if (name === 'plugin') return value?.status === 'available' ? 'Discovered locally' : 'Plugin files are missing';
  if (name === 'backend') return value?.status === 'ok' ? 'Reachable' : value?.message || 'Unavailable';
  if (name === 'sarvam') return value?.status === 'configured' ? 'Configured' : value?.message || 'Not configured';
  return 'Unknown';
}

function statusValue(name, value) {
  if (name === 'codex') return value?.running ? 'ready' : 'unavailable';
  return value?.status || 'unknown';
}

export default function HarnessStatusCard() {
  const { harnessDetails, harnessStatus, refreshHarnessStatus, autoPlay, setAutoPlay } = useAIConversation();
  const details = harnessDetails || {};
  const rows = ['codex', 'plugin', 'backend', 'sarvam'];

  return (
    <section className="mt-6 overflow-hidden rounded-card border border-border bg-white shadow-card" aria-labelledby="harness-status-title">
      <div className="flex items-start justify-between gap-4 border-b border-border bg-emerald-50/60 p-5">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary">Advisor connection</p>
          <h2 id="harness-status-title" className="mt-1 text-lg font-bold text-text-primary">KisanSathi Codex harness</h2>
          <p className="mt-1 max-w-xl text-xs leading-5 text-text-secondary">The manual farm screens stay available while Codex uses approved local tools to read and update farm records.</p>
        </div>
        <button type="button" onClick={refreshHarnessStatus} className="inline-flex shrink-0 items-center gap-2 rounded-lg border border-emerald-200 bg-white px-3 py-2 text-xs font-semibold text-primary-dark hover:bg-emerald-50" aria-label="Refresh advisor connection status">
          <RefreshCw size={14} /> Refresh
        </button>
      </div>
      <div className="grid gap-2 p-4 sm:grid-cols-2">
        {rows.map((name) => {
          const value = details[name] || (name === 'codex' ? { status: harnessStatus } : null);
          const state = statusValue(name, value);
          return <div key={name} className="flex min-h-16 items-center gap-3 rounded-xl border border-border bg-surface-muted/40 px-3 py-2.5">
            <StatusIcon status={state} />
            <div className="min-w-0"><p className="text-xs font-bold text-text-primary">{labels[name]}</p><p className="truncate text-[11px] text-text-secondary">{statusText(name, value)}</p></div>
          </div>;
        })}
      </div>
      <label className="flex items-center gap-3 border-t border-border p-4 text-sm">
        <span className="grid size-9 place-items-center rounded-lg bg-primary-50 text-primary"><Volume2 size={17} /></span>
        <span className="flex-1"><span className="block font-semibold text-text-primary">Speak answers automatically</span><span className="block text-xs text-text-secondary">Sarvam will read each localized Codex answer aloud.</span></span>
        <input type="checkbox" checked={autoPlay} onChange={(event) => setAutoPlay(event.target.checked)} className="size-5 accent-primary" />
      </label>
      {details.codex?.threadId && <p className="border-t border-border px-4 py-3 text-[11px] text-text-muted">Session is resumable if the desktop companion restarts.</p>}
    </section>
  );
}
