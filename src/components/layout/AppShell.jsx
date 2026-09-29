import { Outlet } from 'react-router-dom'
import { useState } from 'react'
import DesktopSidebar from './DesktopSidebar.jsx'
import Header from './Header.jsx'
import MobileBottomNav from './MobileBottomNav.jsx'
import MobileTopHeader from './MobileTopHeader.jsx'
import MobileDrawer from './MobileDrawer.jsx'

export default function AppShell() {
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [desktopCollapsed, setDesktopCollapsed] = useState(false)
  return (
    <div className="min-h-svh bg-background">
      <DesktopSidebar collapsed={desktopCollapsed} />
      <div className={desktopCollapsed ? 'lg:pl-20' : 'lg:pl-64'}>
        <Header onMenuClick={() => setDesktopCollapsed(value => !value)} />
        <MobileTopHeader onMenuClick={() => setDrawerOpen(true)} />
        <main className="pb-24 lg:pb-8"><Outlet /></main>
      </div>
      <MobileBottomNav />
      <MobileDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </div>
  )
}
