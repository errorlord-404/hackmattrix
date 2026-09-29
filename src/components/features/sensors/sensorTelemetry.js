export const FRESH_FOR_MS = 60 * 60 * 1000;
export const AGING_FOR_MS = 6 * 60 * 60 * 1000;

export function freshnessFor(observedAt, now = Date.now()) {
  const timestamp = observedAt ? new Date(observedAt).getTime() : Number.NaN;
  if (!Number.isFinite(timestamp)) return { key: 'unknown', label: 'Unknown', detail: 'Timestamp unavailable' };
  const age = Math.max(0, now - timestamp);
  if (age <= FRESH_FOR_MS) return { key: 'fresh', label: 'Fresh', detail: 'Updated within the last hour' };
  if (age <= AGING_FOR_MS) return { key: 'aging', label: 'Aging', detail: 'Verify the device is still reporting' };
  return { key: 'stale', label: 'Stale', detail: 'Do not use this value as a live reading' };
}
