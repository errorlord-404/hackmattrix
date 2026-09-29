import { FeatureRouteShell } from '../../components/layout/FeatureRouteShell.jsx';
import { ResourceState } from '../../components/feedback/ResourceState.jsx';
import { useReference } from '../../hooks/reference/useReference.js';
import { referenceSafety } from '../../api/referenceApi.js';

export function ReferenceRoute({ title, description, loader, empty, render }) {
  const resource = useReference(loader);
  return <FeatureRouteShell eyebrow="Reference workspace" title={title} description={description}><ResourceState resource={resource} empty={empty}>{(data) => render(Array.isArray(data) ? data.map((item) => ({ ...item, title: referenceSafety(item.title || item.name || item.scheme_name) })) : data)}</ResourceState></FeatureRouteShell>;
}
