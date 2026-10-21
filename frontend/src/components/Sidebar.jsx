import {
  Activity,
  Apple,
  ChefHat,
  ClipboardList,
  Leaf,
  ScanSearch,
  ShieldCheck,
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-react'
import { NavLink } from 'react-router-dom'

const links = [
  { to: '/', label: 'Overview', icon: Activity },
  { to: '/food-recognition', label: 'Food recognition', icon: ScanSearch },
  { to: '/freshness-detector', label: 'Freshness', icon: Leaf },
  { to: '/hygiene-monitor', label: 'Hygiene monitor', icon: ShieldCheck },
  { to: '/kitchen-assistant', label: 'Kitchen assistant', icon: ChefHat },
  { to: '/meal-planner', label: 'Meal planner', icon: ClipboardList },
]

export default function Sidebar({ collapsed, onToggle }) {
  return (
    <aside
      className={`sidebar ${collapsed ? 'sidebar--collapsed' : ''}`}
      aria-label="Main navigation"
    >
      <div className="sidebar__brand">
        <span className="brand-mark">
          <Apple size={20} />
        </span>
        <span className="sidebar__wordmark">
          FoodVerse<span>AI</span>
        </span>
      </div>
      <nav>
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            title={collapsed ? label : undefined}
            aria-label={label}
            className={({ isActive }) =>
              `nav-link ${isActive ? 'nav-link--active' : ''}`
            }
          >
            <Icon size={19} aria-hidden="true" />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
      <button
        type="button"
        className="sidebar__collapse"
        onClick={onToggle}
        aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {collapsed ? <PanelLeftOpen size={19} /> : <PanelLeftClose size={19} />}
        <span>{collapsed ? 'Expand' : 'Collapse'}</span>
      </button>
    </aside>
  )
}
