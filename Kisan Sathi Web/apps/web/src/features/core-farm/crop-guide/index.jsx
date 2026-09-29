import { farmStateApi } from '../../../api/farmStateApi.js';
import { ResourceRoute } from '../ResourceRoute.jsx';
export function CropGuideRoute({ fieldId }) { return <ResourceRoute title="Crop guide" description="Guidance is tied to the selected field cycle and recorded sources." loader={() => farmStateApi.cropTimeline(fieldId)} empty="No recorded crop cycle is available." render={(data) => <pre data-testid="web-crop-guide-states">{JSON.stringify(data, null, 2)}</pre>} />; }
