import { referenceApi } from '../../api/referenceApi.js';
import { ResourceRoute } from '../core-farm/ResourceRoute.jsx';
export function AlertsRoute() { return <ResourceRoute title="Alerts" description="Acknowledgement is a bounded server write; alert content is rendered as data." loader={referenceApi.alerts} empty="No alerts are recorded." render={(data) => <pre>{JSON.stringify(data, null, 2)}</pre>} />; }
