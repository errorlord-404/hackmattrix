import { useEffect, useState } from 'react';

export function useResource(loader, dependencies = []) {
  const [state, setState] = useState({ status: 'loading', data: null, error: null });
  useEffect(() => {
    let active = true;
    setState((current) => ({ ...current, status: 'loading', error: null }));
    Promise.resolve().then(loader).then((data) => { if (active) setState({ status: Array.isArray(data) && data.length === 0 ? 'empty' : 'success', data, error: null }); }).catch((error) => { if (active) setState({ status: error?.retryable ? 'unavailable' : 'error', data: null, error }); });
    return () => { active = false; };
  // The caller supplies a stable dependency list for the selected backend ID.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencies);
  return state;
}
