import { MapPin, Menu } from 'lucide-react';
import { useLanguage } from '../../hooks/useLanguage.jsx';
import { useFarmData } from '../../context/FarmDataContext.jsx';
import AlertMenu from './AlertMenu.jsx';

export default function Header({ onMenuClick }) {
  // Extract language context and setup a quick boolean for Hindi checks
  const { language, setLanguage, t } = useLanguage();
  const { profile } = useFarmData();
  const hi = language === 'hi';
  const name = profile?.name || (hi ? 'स्थानीय प्रोफ़ाइल सेट करें' : 'Set up local profile');
  const location = profile?.location || (hi ? 'स्थान उपलब्ध नहीं' : 'Location unavailable');
  const initials = profile?.name ? profile.name.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase() : 'KS';

  return (
    // Main header container: Hidden on small screens, visible on desktop (lg:flex)
    <header className="hidden h-[68px] items-center justify-between border-b border-border bg-white px-8 lg:flex">
      
      {/* Left side: Sidebar Toggle Button */}
      <button
        onClick={onMenuClick}
        aria-label={hi ? 'साइडबार खोलें या बंद करें' : 'Toggle sidebar'}
        className="rounded-lg p-1 hover:bg-surface-muted"
      >
        <Menu size={20} />
      </button>

      {/* Right side: Actions, Settings, and User Profile */}
      <div className="ml-auto flex items-center gap-6 text-sm text-text-secondary">
        
        {/* Language Selector Dropdown */}
        <select
          aria-label={t('language')}
          value={language}
          onChange={(event) => setLanguage(event.target.value)}
          className="rounded-lg border border-border bg-white px-2 py-1.5 text-xs font-semibold text-primary"
        >
          <option value="en">EN</option>
          <option value="hi">हिंदी</option>
          <option value="mr">मराठी</option>
        </select>

        {/* Farmer Location Indicator */}
        <span className="flex items-center gap-1.5">
          <MapPin size={16} className="text-primary" />
          {location}
        </span>

        {/* Notification Bell */}
        <AlertMenu />

        {/* User Avatar (Initials) */}
        <div className="flex size-9 items-center justify-center rounded-full bg-amber-100 text-xs font-bold text-amber-800">
          {initials}
        </div>
        
        {/* User Name */}
        <span className="-ml-4 font-medium text-text-primary">
          {name}
        </span>
        
      </div>
    </header>
  );
}
