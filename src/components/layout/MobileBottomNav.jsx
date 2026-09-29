import { NavLink } from 'react-router-dom';
import { Mic } from 'lucide-react';
import { mobileNavigation } from '../../data/navigation.js';
import { useLanguage } from '../../hooks/useLanguage.jsx';

export default function MobileBottomNav() {
  const { t } = useLanguage();

  return (
    // Main bottom nav container: Fixed to bottom, hidden on large screens (lg:hidden)
    // Uses safe-area-inset-bottom to accommodate mobile gestures/home indicators
    <nav className="fixed inset-x-0 bottom-0 z-20 flex h-[70px] items-center justify-around border-t border-border bg-white px-2 pb-[env(safe-area-inset-bottom)] lg:hidden">
      {mobileNavigation.map(({ label, key, to, icon: Icon }, index) => (
        <NavLink
          key={to}
          to={to}
          aria-label={t(key) || label}
          className={({ isActive }) =>
            `flex min-w-12 flex-col items-center gap-1 text-[10px] font-medium ${
              isActive ? 'text-primary' : 'text-text-muted'
            }`
          }
        >
          {/* 
            Special styling for the center item (index 2): 
            Creates a prominent, elevated floating action button (FAB) effect using negative margin (-mt-8) 
          */}
          {index === 2 ? (
            <span className="-mt-8 grid size-14 place-items-center rounded-full border-4 border-background bg-primary text-white shadow-lg">
              <Mic size={23} />
            </span>
          ) : (
            // Standard icon for all other navigation items
            <Icon size={19} />
          )}
          
          {/* Translated label */}
          <span>{t(key) || label}</span>
        </NavLink>
      ))}
    </nav>
  );
}