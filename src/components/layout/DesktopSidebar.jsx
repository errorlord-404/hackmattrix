import { NavLink } from 'react-router-dom';
import { Leaf, MessageCircle } from 'lucide-react';
import { navigation } from '../../data/navigation.js';
import { useLanguage } from '../../hooks/useLanguage.jsx';

export default function DesktopSidebar({ collapsed }) {
  const { t } = useLanguage();

  return (
    // Main sidebar container: Adjusts width and padding based on 'collapsed' state
    <aside
      className={`fixed inset-y-0 left-0 hidden flex-col overflow-y-auto border-r border-[#d9e9db] bg-[#f6fbf6] py-6 transition-all lg:flex ${
        collapsed ? 'w-20 px-3' : 'w-64 px-4'
      }`}
    >
      {/* Brand Header: Centers the icon when collapsed, shows text when expanded */}
      <div
        className={`flex items-center gap-2 text-xl font-bold text-primary-dark ${
          collapsed ? 'justify-center' : 'px-3'
        }`}
      >
        <span className="grid size-9 place-items-center rounded-xl bg-primary text-white">
          <Leaf size={20} />
        </span>
        {!collapsed && 'KisanSathi'}
      </div>

      {/* Navigation Menu */}
      <nav className="mt-9 space-y-1">
        {navigation
          // Exclude specific routes (e.g., '/voice') from the sidebar
          .filter(({ to }) => to !== '/voice')
          .map(({ label, key, to, icon: Icon }) => (
            <NavLink
              title={key ? t(key) : label}
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center rounded-lg py-2.5 text-sm font-medium transition ${
                  collapsed ? 'justify-center px-2' : 'gap-3 px-3'
                } ${
                  isActive
                    ? 'bg-[#dceedd] text-primary-dark' // Active link styling
                    : 'text-text-secondary hover:bg-[#eaf5eb] hover:text-primary-dark' // Default/Hover styling
                }`
              }
            >
              <Icon size={18} />
              {/* Only show the label text if the sidebar is fully expanded */}
              {!collapsed && (key ? t(key) : label)}
            </NavLink>
          ))}
      </nav>

      {/* Help Banner: Pushed to the bottom ('mt-auto'), only visible when expanded */}
      {!collapsed && (
        <div className="mt-auto rounded-xl bg-primary-dark p-4 text-white">
          <p className="text-sm font-semibold">Need Help?</p>
          <p className="mt-1 text-xs text-green-100">
            Talk to KisanSathi anytime.
          </p>
          <NavLink
            to="/ai"
            className="mt-3 flex w-fit items-center gap-1.5 rounded-lg bg-white px-3 py-2 text-xs font-semibold text-primary"
          >
            <MessageCircle size={14} /> Chat Now
          </NavLink>
        </div>
      )}
    </aside>
  );
}