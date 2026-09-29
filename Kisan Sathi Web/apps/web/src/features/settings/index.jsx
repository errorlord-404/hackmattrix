import { referenceApi } from '../../api/referenceApi.js';
import { ResourceRoute } from '../core-farm/ResourceRoute.jsx';
export function SettingsRoute() { return <ResourceRoute title="Settings" description="Profile and language preferences remain claim-scoped; provider credentials never enter browser storage." loader={referenceApi.profile} empty="No profile is available." render={(data) => <pre data-testid="web-settings-safety">{JSON.stringify(data, null, 2)}</pre>} />; }
