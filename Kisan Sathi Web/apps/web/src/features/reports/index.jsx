import { referenceApi } from '../../api/referenceApi.js';
import { ResourceRoute } from '../core-farm/ResourceRoute.jsx';
export function ReportsRoute() { return <ResourceRoute title="Farm reports" description="Reports are authoritative persisted records and writes require server policy, approval, and idempotency." loader={referenceApi.reports} empty="No reports are recorded." render={(data) => <pre data-testid="web-reports-approval">{JSON.stringify(data, null, 2)}</pre>} />; }
