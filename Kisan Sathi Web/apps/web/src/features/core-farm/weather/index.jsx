import { farmStateApi } from '../../../api/farmStateApi.js';
import { ResourceRoute } from '../ResourceRoute.jsx';
export function WeatherRoute({ lat, lon }) { return <ResourceRoute title="Weather" description="Forecasts show provider and freshness state; an outage is not a forecast." loader={() => lat == null || lon == null ? Promise.reject({ retryable: false }) : farmStateApi.weather({ lat, lon })} empty="No weather observation is available." render={(data) => <pre data-testid="web-weather-states">{JSON.stringify(data, null, 2)}</pre>} />; }
