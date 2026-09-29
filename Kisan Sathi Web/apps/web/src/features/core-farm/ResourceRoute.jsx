import { FeatureRouteShell } from '../../components/layout/FeatureRouteShell.jsx';
import { ResourceState } from '../../components/feedback/ResourceState.jsx';
import { useResource } from '../../hooks/core-farm/useResource.js';

export function ResourceRoute({ title, description, loader, empty, render }) {
  const resource = useResource(loader);
  return <FeatureRouteShell title={title} description={description}><ResourceState resource={resource} empty={empty}>{render}</ResourceState></FeatureRouteShell>;
}
