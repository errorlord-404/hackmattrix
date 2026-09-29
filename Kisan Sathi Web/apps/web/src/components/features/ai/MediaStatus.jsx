export function MediaStatus({ result, error, onRetry }) {
  if (error) return <div className="degraded-box" role="alert"><strong>Media is unavailable.</strong><span>{error.message || 'No media result was generated.'}</span>{onRetry && <button type="button" onClick={onRetry}>Try again</button>}</div>;
  if (!result) return null;
  const unavailable = result.status === 'unavailable';
  return <div className="degraded-box" role="status"><strong>{unavailable ? 'Provider unavailable.' : 'Review required.'}</strong><span>{result.message || 'No diagnosis was generated.'}</span></div>;
}
