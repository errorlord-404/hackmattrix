import { X, Leaf } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { navigation } from '../../data/navigation.js';
import { useLanguage } from '../../hooks/useLanguage.jsx';

export default function MobileDrawer({ open, onClose }) {
  const { t, language, setLanguage } = useLanguage();

  return (
    // Main container: Fixed overlay for mobile screens, toggles pointer events based on state
    <div
      className={`fixed inset-0 z-50 lg:hidden ${open ? '' : 'pointer-events-none'}`}
      aria-hidden={!open}
    >
      {/* Backdrop: Semi-transparent overlay with smooth fade transition */}
      <button
        onClick={onClose}
        className={`absolute inset-0 left-0 bg-black/35 transition-opacity ${
          open ? 'opacity-100' : 'opacity-0'
        }`}
        aria-label="Close menu"
      />

      {/* Drawer Panel: Slides in from the left */}
      <aside
        className={`absolute inset-y-0 left-0 flex w-[82%] max-w-[320px] flex-col overflow-y-auto bg-[#f6fbf6] p-5 shadow-2xl transition-transform ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Drawer Header: Brand logo and close button */}
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-2 text-lg font-bold text-primary-dark">
            <span className="grid size-9 place-items-center rounded-xl bg-primary text-white">
              <Leaf size={19} />
            </span>
            KisanSathi
          </span>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-text-secondary"
            aria-label="Close menu"
          >
            <X size={20} />
          </button>
        </div>

        {/* Language Selection Dropdown */}
        <select
          aria-label="Language"
          value={language}
          onChange={(event) => setLanguage(event.target.value)}
          className="mt-5 rounded-lg border border-[#d9e9db] bg-white px-3 py-2 text-sm font-semibold text-primary"
        >
          <option value="en">English</option>
          <option value="hi">हिंदी</option>
          <option value="mr">मराठी</option>
        </select>

        {/* Navigation Links: Automatically closes drawer on click */}
        <nav className="mt-5 space-y-1">
          {navigation.map(({ label, key, to, icon: Icon }) => (
            <NavLink
              key={to}
              onClick={onClose}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-3 text-sm font-medium ${
                  isActive
                    ? 'bg-[#dceedd] text-primary-dark' // Active state styling
                    : 'text-text-secondary hover:bg-[#eaf5eb]' // Default & hover styling
                }`
              }
            >
              <Icon size={18} />
              {key ? t(key) : label}
            </NavLink>
          ))}
        </nav>
      </aside>
    </div>
  );
}
