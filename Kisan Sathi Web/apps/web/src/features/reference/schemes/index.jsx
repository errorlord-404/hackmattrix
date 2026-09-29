import { referenceApi } from '../../../api/referenceApi.js';
import { referenceMessages } from '../../../i18n/reference/messages.js';
import { ReferenceRoute } from '../ReferenceRoute.jsx';
export function SchemesRoute() { return <ReferenceRoute title="Government schemes" description={referenceMessages.schemeSafety} loader={referenceApi.schemes} empty="No matching schemes are available." render={(data) => <ul data-testid="web-schemes-safety">{data.map((item) => <li key={item.id}>{item.title || item.name || item.scheme_name}</li>)}</ul>} />; }
