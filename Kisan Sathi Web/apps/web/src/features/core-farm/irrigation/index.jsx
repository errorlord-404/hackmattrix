import { farmStateApi } from '../../../api/farmStateApi.js';
import { ResourceRoute } from '../ResourceRoute.jsx';
import { coreFarmMessages } from '../../../i18n/core-farm/messages.js';
export function IrrigationRoute({ fieldId }) { return <ResourceRoute title="Irrigation" description={coreFarmMessages.irrigationSafety} loader={() => farmStateApi.irrigation(fieldId)} empty="No irrigation plan is recorded." render={(data) => <pre data-testid="web-irrigation-safety">{JSON.stringify(data, null, 2)}</pre>} />; }
