import { farmStateApi } from '../../../api/farmStateApi.js';
import { ResourceRoute } from '../ResourceRoute.jsx';
export function DashboardRoute() { return <ResourceRoute title="Farm dashboard" description="Claim-scoped overview with independent source states." loader={farmStateApi.dashboard} empty="No dashboard observations are recorded." render={(data) => <pre data-testid="web-dashboard-states">{JSON.stringify(data, null, 2)}</pre>} />; }
