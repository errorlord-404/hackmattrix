import { farmStateApi } from '../../../api/farmStateApi.js';
import { ResourceRoute } from '../ResourceRoute.jsx';
export function TasksRoute() { return <ResourceRoute title="Field tasks" description="Tasks are claim-scoped and do not purchase or control equipment." loader={farmStateApi.tasks} empty="No field tasks are recorded." render={(data) => <ul data-testid="web-task-approval">{data.map((task) => <li key={task.id}>{task.title}</li>)}</ul>} />; }
