import { Bot, Bug, CloudSun, Coins, Droplets, FileText, Landmark, LayoutDashboard, ListTodo, Map, PackageSearch, Sprout, Store, TestTube2, Wheat, Mic, Settings, Wrench } from 'lucide-react'

export const navigation = [
  ...(window.kisanHarness
    ? [{ label: 'Farm Assistant', key: 'ai', to: '/', icon: Bot }, { label: 'Dashboard', key: 'dashboard', to: '/dashboard', icon: LayoutDashboard }]
    : [{ label: 'Dashboard', key: 'dashboard', to: '/', icon: LayoutDashboard }]),
  { label: 'My Fields', key: 'fields', to: '/fields', icon: Wheat },
  { label: 'Farm Map', key: 'farmMap', to: '/map', icon: Map },
  { label: 'Soil Health', key: 'soil', to: '/soil', icon: TestTube2 },
  { label: 'Weather', key: 'weather', to: '/weather', icon: CloudSun },
  { label: 'Crop Guide', key: 'cropGuide', to: '/crop-guide', icon: Sprout },
  { label: 'Irrigation', key: 'irrigation', to: '/irrigation', icon: Droplets },
  { label: 'Field Actions', key: 'tasks', to: '/tasks', icon: ListTodo },
  { label: 'Pest & Disease', key: 'pest', to: '/pest', icon: Bug },
  { label: 'Market Prices', key: 'market', to: '/market', icon: Store },
  { label: 'Govt Schemes', key: 'schemes', to: '/schemes', icon: Landmark },
  { label: 'Farm Finance', key: 'finance', to: '/finance', icon: Coins },
  { label: 'Machinery Rentals', key: 'machinery', to: '/machinery', icon: Wrench },
  { label: 'Marketplace', to: '/marketplace', icon: PackageSearch },
  ...(!window.kisanHarness ? [{ label: 'AI Advisor', key: 'ai', to: '/ai', icon: Bot }] : []),
  { label: 'Reports', key: 'reports', to: '/reports', icon: FileText },
  { label: 'Voice Assistant', to: '/voice', icon: Mic },
  { label: 'Settings', to: '/settings', icon: Settings },
]

export const mobileNavigation = [
  { label: 'Home', key: 'home', to: '/', icon: window.kisanHarness ? Bot : LayoutDashboard },
  { label: 'Fields', key: 'fields', to: '/fields', icon: Wheat },
  { label: 'Voice', key: 'voice', to: '/voice', icon: Mic },
  { label: 'Market', key: 'marketShort', to: '/market', icon: Store },
  { label: 'Profile', key: 'profile', to: '/settings', icon: Settings },
]
