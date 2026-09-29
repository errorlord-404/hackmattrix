import { FeatureRouteShell } from '../../../components/layout/FeatureRouteShell.jsx';

export function DeviceSetupRoute() {
  return (
    <FeatureRouteShell
      title="Device onboarding"
      description="Connect field observations without granting hardware control."
    >
      <section className="degraded-box" aria-label="Device onboarding status">
        <strong>Device setup is ready for claim-scoped telemetry.</strong>
        <span>Hardware actions remain disabled; pairing and observations are reviewed by the service.</span>
      </section>
    </FeatureRouteShell>
  );
}

export default DeviceSetupRoute;
