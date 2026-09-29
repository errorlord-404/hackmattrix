import { referenceApi } from '../../../api/referenceApi.js';
import { referenceMessages } from '../../../i18n/reference/messages.js';
import { ReferenceRoute } from '../ReferenceRoute.jsx';
export function MachineryRoute() { return <ReferenceRoute title="Machinery directory" description={referenceMessages.machinerySafety} loader={() => referenceApi.machinery()} empty="No directory records are available." render={(data) => <ul data-testid="web-machinery-discovery">{data.map((item) => <li key={item.id}>{item.title || item.provider_name}</li>)}</ul>} />; }
