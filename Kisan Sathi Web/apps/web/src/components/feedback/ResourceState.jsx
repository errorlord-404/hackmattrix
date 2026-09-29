export function ResourceState({ resource, empty = 'No records are available.', children }) {
  if (resource.status === 'loading') return <div role="status">Loading current farm data…</div>;
  if (resource.status === 'empty') return <div role="status">{empty}</div>;
  if (resource.status === 'unavailable') return <div role="alert">This provider is unavailable. No new farm value was inferred.</div>;
  if (resource.status === 'error') return <div role="alert">This farm record could not be loaded. Nothing was changed.</div>;
  return children(resource.data);
}
