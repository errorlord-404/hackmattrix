import { lazy, Suspense } from 'react';
import { createBrowserRouter, createHashRouter, useRouteError } from 'react-router-dom';
import AppShell from '../components/layout/AppShell.jsx';

// Farm pages pull in maps, charts, photo tools, or large reference views.
// Load them only after the farmer chooses a route so the Electron assistant
// reaches its first useful screen quickly on low-powered devices.
const Dashboard = lazy(() => import('../pages/Dashboard.jsx'));
const AIAssistant = lazy(() => import('../pages/AIAssistant.jsx'));
const MyFields = lazy(() => import('../pages/MyFields.jsx'));
const FieldDetail = lazy(() => import('../pages/FieldDetail.jsx'));
const Irrigation = lazy(() => import('../pages/CorePages.jsx').then((module) => ({ default: module.Irrigation })));
const MarketPrices = lazy(() => import('../pages/CorePages.jsx').then((module) => ({ default: module.MarketPrices })));
const Reports = lazy(() => import('../pages/CorePages.jsx').then((module) => ({ default: module.Reports })));
const SoilHealth = lazy(() => import('../pages/CorePages.jsx').then((module) => ({ default: module.SoilHealth })));
const Weather = lazy(() => import('../pages/CorePages.jsx').then((module) => ({ default: module.Weather })));
const CropGuide = lazy(() => import('../pages/FieldTools.jsx').then((module) => ({ default: module.CropGuide })));
const FarmMap = lazy(() => import('../pages/FieldTools.jsx').then((module) => ({ default: module.FarmMap })));
const PestDisease = lazy(() => import('../pages/FieldTools.jsx').then((module) => ({ default: module.PestDisease })));
const GovtSchemes = lazy(() => import('../pages/GovtSchemes.jsx'));
const FarmFinance = lazy(() => import('../pages/FarmFinance.jsx'));
const MachineryRentals = lazy(() => import('../pages/MachineryRentals.jsx'));
const Marketplace = lazy(() => import('../pages/Marketplace.jsx'));
const VoiceAssistant = lazy(() => import('../pages/VoiceAssistant.jsx'));
const Settings = lazy(() => import('../pages/Settings.jsx'));
const DeviceOnboarding = lazy(() => import('../pages/DeviceOnboarding.jsx'));
const FieldTasks = lazy(() => import('../pages/FieldTasks.jsx'));

function RouteLoading() {
  return <div className="grid min-h-[40vh] place-items-center px-4 text-sm text-text-secondary" role="status">Loading KisanSathi…</div>;
}

function RouteRecovery() {
  const error = useRouteError();
  const failedModule = /dynamically imported module|import/i.test(String(error?.message || error || ''));
  return <main className="grid min-h-screen place-items-center bg-[radial-gradient(circle_at_top,#e9f5df,transparent_45%),#f7f6f0] px-5 text-center">
    <section className="w-full max-w-md rounded-2xl border border-primary/20 bg-white p-7 shadow-card">
      <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary">KisanSathi recovery</p>
      <h1 className="mt-3 text-2xl font-bold text-primary-dark">{failedModule ? 'An app update is ready' : 'This page needs a refresh'}</h1>
      <p className="mt-3 text-sm leading-6 text-text-secondary">{failedModule ? 'KisanSathi was updated while this window was open. Reload once to continue safely.' : 'Your farm records are unchanged. Reload the app to try this page again.'}</p>
      <button type="button" onClick={() => window.location.reload()} className="mt-6 rounded-lg bg-primary px-5 py-2.5 text-sm font-bold text-white transition hover:bg-primary-dark focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">Reload KisanSathi</button>
    </section>
  </main>;
}

const page = (Component) => <Suspense fallback={<RouteLoading />}><Component /></Suspense>;

const createAppRouter = window.location.protocol === 'file:' ? createHashRouter : createBrowserRouter;

export const router = createAppRouter([
  {
    // Main App Layout Shell wrapper route
    element: <AppShell />,
    errorElement: <RouteRecovery />,
    children: [
      { path: '/', element: page(window.kisanHarness ? AIAssistant : Dashboard) },
      { path: '/dashboard', element: page(Dashboard) },
      { path: '/fields', element: page(MyFields) },
      { path: '/fields/:fieldId', element: page(FieldDetail) },
      { path: '/map', element: page(FarmMap) },
      { path: '/crop-guide', element: page(CropGuide) },
      { path: '/soil', element: page(SoilHealth) },
      { path: '/weather', element: page(Weather) },
      { path: '/irrigation', element: page(Irrigation) },
      { path: '/tasks', element: page(FieldTasks) },
      { path: '/pest', element: page(PestDisease) },
      { path: '/market', element: page(MarketPrices) },
      { path: '/schemes', element: page(GovtSchemes) },
      { path: '/finance', element: page(FarmFinance) },
      { path: '/machinery', element: page(MachineryRentals) },
      { path: '/marketplace', element: page(Marketplace) },
      { path: '/ai', element: page(AIAssistant) },
      { path: '/voice', element: page(VoiceAssistant) },
      { path: '/reports', element: page(Reports) },
      { path: '/settings', element: page(Settings) },
      { path: '/device-setup', element: page(DeviceOnboarding) },
    ],
  },
]);
