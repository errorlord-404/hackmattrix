import { Leaf, Menu } from 'lucide-react';
import { useLanguage } from '../../hooks/useLanguage.jsx';
import AlertMenu from './AlertMenu.jsx';

export default function MobileTopHeader({ onMenuClick }) {
  // Extract language state to conditionally handle accessibility labels
  const { language } = useLanguage();
  const hi = language === 'hi';

  return (
    // Main header container: Visible only on mobile/tablet screens (lg:hidden)
    <header className="flex h-16 items-center justify-between border-b border-border bg-white px-5 lg:hidden">
      
      {/* Left side: Hamburger menu button to trigger the mobile drawer */}
      <button
        onClick={onMenuClick}
        aria-label={hi ? 'मेनू खोलें' : 'Open menu'}
      >
        <Menu size={21} />
      </button>

      {/* Center: App branding and logo */}
      <span className="flex items-center gap-1.5 text-lg font-bold text-primary-dark">
        <Leaf size={21} className="text-primary" />
        KisanSathi
      </span>

      {/* Right side: Notification bell icon */}
      <AlertMenu mobile />
      
    </header>
  );
}
