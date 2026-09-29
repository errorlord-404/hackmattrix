import { farmStateApi } from '../../../api/farmStateApi.js';
import { ResourceRoute } from '../ResourceRoute.jsx';
export function SoilRoute({ fieldId }) { return <ResourceRoute title="Soil health" description="Measurements retain their recorded time and provenance." loader={() => farmStateApi.soil(fieldId)} empty="No soil test is recorded for this field." render={(data) => <pre data-testid="web-soil-states">{JSON.stringify(data, null, 2)}</pre>} />; }
