import { referenceApi } from '../../../api/referenceApi.js';
import { ReferenceRoute } from '../ReferenceRoute.jsx';
export function MarketplaceRoute() { return <ReferenceRoute title="Marketplace directory" description="Directory information is informational and never guarantees stock, price, contact, or transaction." loader={() => referenceApi.marketplace()} empty="No marketplace records are available." render={(data) => <pre data-testid="web-marketplace-safety">{JSON.stringify(data, null, 2)}</pre>} />; }
