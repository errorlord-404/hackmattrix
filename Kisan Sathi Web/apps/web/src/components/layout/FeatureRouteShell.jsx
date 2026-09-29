export function FeatureRouteShell({ eyebrow = 'Farm workspace', title, description, children }) {
  return <main className="feature-route" data-testid="standalone-feature-route"><p className="eyebrow">{eyebrow}</p><h1>{title}</h1>{description && <p>{description}</p>}{children}</main>;
}
