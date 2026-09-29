export function LoadingState({ label = 'Loading live farm data…' }) { return <div className="rounded-card border border-border bg-white p-6 text-sm text-text-secondary shadow-card">{label}</div>; }
export function ErrorState({ error, onRetry }) { return <div className="rounded-card border border-red-200 bg-red-50 p-5 text-sm text-red-800"><p className="font-bold">{error?.status === 404 ? 'Requested data was not found' : error?.status >= 500 || error?.code === 'service_unavailable' ? 'Farm service is unavailable' : 'Live data is unavailable'}</p><p className="mt-1">{error?.message || 'The backend could not be reached.'}</p>{(error?.code || error?.requestId) && <p className="mt-2 text-[11px] text-red-700">Code: {error.code || 'unknown'}{error.requestId ? ` · Request ${error.requestId}` : ''}{error.retryable ? ' · retryable' : ''}</p>}{onRetry && <button onClick={onRetry} className="mt-3 rounded-lg bg-red-700 px-3 py-2 text-xs font-semibold text-white">Retry</button>}</div>; }
export function EmptyState({ title, detail, action }) { return <div className="rounded-card border border-dashed border-border bg-white p-8 text-center"><p className="font-bold">{title}</p><p className="mt-2 text-sm text-text-secondary">{detail}</p>{action}</div>; }

export function StaleDataNotice({ meta }) {
  if (meta?.mode !== 'stale_cache') return null;
  const ageHours = Math.max(1, Math.round((meta.ageMs || 0) / 3600000));
  return <div role="status" className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">Showing last-known reference data cached about {ageHours} hour{ageHours === 1 ? '' : 's'} ago. The backend or provider is unavailable; verify before acting.</div>;
}
export function SourceStamp({ source, fetchedAt, warning }) { return <p className={`mt-2 text-[11px] ${warning ? 'text-amber-700' : 'text-text-muted'}`}>{warning || `Source: ${source || 'local farm state'}${fetchedAt ? ` · ${new Date(fetchedAt).toLocaleString()}` : ''}`}</p>; }

