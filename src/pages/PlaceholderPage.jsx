import { ArrowLeft, Construction } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function PlaceholderPage({ title }) {
  return (
    <div className="mx-auto flex min-h-[65svh] max-w-xl flex-col items-center justify-center px-6 text-center">
      {/* Icon Container: Renders a construction icon inside a styled rounded box */}
      <div className="grid size-16 place-items-center rounded-2xl bg-primary-50 text-primary">
        <Construction size={30} />
      </div>

      {/* Dynamic Page Title */}
      <h1 className="mt-5 text-2xl font-bold">{title}</h1>

      {/* Informational Message */}
      <p className="mt-2 text-sm leading-6 text-text-secondary">
        This feature is next in the KisanSathi build. The dashboard is ready to
        explore.
      </p>

      {/* Navigation Link back to the main dashboard */}
      <Link
        to="/"
        className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-primary"
      >
        <ArrowLeft size={16} />
        Back to dashboard
      </Link>
    </div>
  );
}