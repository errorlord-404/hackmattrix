import { farmStateApi } from '../../../api/farmStateApi.js';
import { ResourceRoute } from '../ResourceRoute.jsx';
export function MapRoute() { return <ResourceRoute title="Farm map" description="Boundaries come from the authenticated API; browser coordinates never authorize records." loader={farmStateApi.map} empty="No field boundaries are recorded." render={(data) => <pre data-testid="web-map-states">{JSON.stringify(data, null, 2)}</pre>} />; }
