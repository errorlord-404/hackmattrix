import { FeatureRouteShell } from '../../components/layout/FeatureRouteShell.jsx';

export function calculateFinance({ quantity = 0, unitPrice = 0, costs = 0 } = {}) { return { gross: Number(quantity) * Number(unitPrice), net: Number(quantity) * Number(unitPrice) - Number(costs) }; }
export function FinanceRoute() { return <FeatureRouteShell title="Finance calculator" description="This is a stateless calculation only. No ledger, payment, loan, or financial commitment is persisted."><div data-testid="web-finance-boundary">Enter explicit assumptions to calculate a local estimate.</div></FeatureRouteShell>; }
