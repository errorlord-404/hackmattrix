import { farmStateApi } from '../../../api/farmStateApi.js';
import { ResourceRoute } from '../ResourceRoute.jsx';
export function FieldDetailRoute({ fieldId }) { return <ResourceRoute title="Field detail" description="The server verifies ownership of this field ID." loader={() => farmStateApi.field(fieldId)} empty="Field not found." render={(data) => <pre data-testid="web-field-detail-scope">{JSON.stringify(data, null, 2)}</pre>} />; }
