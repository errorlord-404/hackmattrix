import { VoiceButton } from '../components/features/ai/VoiceButton.jsx';
import { ImageComposer } from '../components/features/ai/ImageComposer.jsx';
import { ConversationRoute } from '../features/conversation/index.jsx';
import { DashboardRoute } from '../features/core-farm/dashboard/index.jsx';
import { FieldsRoute } from '../features/core-farm/fields/index.jsx';
import { FieldDetailRoute } from '../features/core-farm/field-detail/index.jsx';
import { MapRoute } from '../features/core-farm/map/index.jsx';
import { CropGuideRoute } from '../features/core-farm/crop-guide/index.jsx';
import { SoilRoute } from '../features/core-farm/soil/index.jsx';
import { WeatherRoute } from '../features/core-farm/weather/index.jsx';
import { IrrigationRoute } from '../features/core-farm/irrigation/index.jsx';
import { TasksRoute } from '../features/core-farm/tasks/index.jsx';
import { PestRoute } from '../features/core-farm/pest/index.jsx';
import { MarketRoute } from '../features/reference/market/index.jsx';
import { SchemesRoute } from '../features/reference/schemes/index.jsx';
import { MachineryRoute } from '../features/reference/machinery/index.jsx';
import { MarketplaceRoute } from '../features/reference/marketplace/index.jsx';
import { AdvisorRoute } from '../features/advisor/index.jsx';
import { ReportsRoute } from '../features/reports/index.jsx';
import { SettingsRoute } from '../features/settings/index.jsx';
import { FinanceRoute } from '../features/finance/index.jsx';
import { DeviceSetupRoute } from '../features/core-farm/device-setup/index.jsx';

export const routes = Object.freeze([
  { id: 'dashboard', path: '/', label: 'Dashboard', protected: true },
  { id: 'fields', path: '/fields', label: 'Fields', protected: true },
  { id: 'field-detail', path: '/fields/:fieldId', label: 'Field detail', protected: true },
  { id: 'map', path: '/map', label: 'Map', protected: true },
  { id: 'crop-guide', path: '/crop-guide', label: 'Crop guide', protected: true },
  { id: 'soil', path: '/soil', label: 'Soil', protected: true },
  { id: 'weather', path: '/weather', label: 'Weather', protected: true },
  { id: 'irrigation', path: '/irrigation', label: 'Irrigation', protected: true },
  { id: 'tasks', path: '/tasks', label: 'Tasks', protected: true },
  { id: 'pest', path: '/pest', label: 'Pest guidance', protected: true },
  { id: 'market', path: '/market', label: 'Market', protected: true },
  { id: 'schemes', path: '/schemes', label: 'Schemes', protected: true },
  { id: 'machinery', path: '/machinery', label: 'Machinery', protected: true },
  { id: 'marketplace', path: '/marketplace', label: 'Marketplace', protected: true },
  { id: 'ai', path: '/ai', label: 'Advisor', protected: true },
  { id: 'advisor', path: '/advisor', label: 'Advisor status', protected: true },
  { id: 'voice', path: '/voice', label: 'Voice', protected: true },
  { id: 'screening', path: '/screening', label: 'Crop screening', protected: true },
  { id: 'reports', path: '/reports', label: 'Reports', protected: true },
  { id: 'settings', path: '/settings', label: 'Settings', protected: true },
  { id: 'finance', path: '/finance', label: 'Finance calculator', protected: true },
  { id: 'device-setup', path: '/device-setup', label: 'Device setup', protected: true },
]);

export const routeComponents = Object.freeze({ dashboard: DashboardRoute, fields: FieldsRoute, 'field-detail': FieldDetailRoute, map: MapRoute, 'crop-guide': CropGuideRoute, soil: SoilRoute, weather: WeatherRoute, irrigation: IrrigationRoute, tasks: TasksRoute, pest: PestRoute, market: MarketRoute, schemes: SchemesRoute, machinery: MachineryRoute, marketplace: MarketplaceRoute, ai: ConversationRoute, advisor: AdvisorRoute, voice: VoiceButton, screening: ImageComposer, reports: ReportsRoute, settings: SettingsRoute, finance: FinanceRoute, 'device-setup': DeviceSetupRoute });

export function routeFor(pathname = '/') {
  return routes.find((route) => route.path === pathname) || routes[0];
}
