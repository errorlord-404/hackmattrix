import { farmStateApi } from '../../../api/farmStateApi.js';
import { ResourceRoute } from '../ResourceRoute.jsx';
export function FieldsRoute() { return <ResourceRoute title="My fields" description="Fields are returned only for the authenticated farmer." loader={farmStateApi.fields} empty="No fields are recorded yet." render={(data) => <ul data-testid="web-fields-states">{data.map((field) => <li key={field.id}>{field.name}</li>)}</ul>} />; }
