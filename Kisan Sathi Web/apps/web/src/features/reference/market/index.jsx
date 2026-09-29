import { referenceApi } from '../../../api/referenceApi.js';
import { ReferenceRoute } from '../ReferenceRoute.jsx';
export function MarketRoute() { return <ReferenceRoute title="Market prices" description="Sourced prices retain units, source, and freshness; they are not a sale or guarantee." loader={referenceApi.market} empty="No market observations are available." render={(data) => <pre data-testid="web-market-states">{JSON.stringify(data, null, 2)}</pre>} />; }
