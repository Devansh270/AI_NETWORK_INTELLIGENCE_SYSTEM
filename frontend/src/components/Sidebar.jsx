import { NavLink } from 'react-router-dom'

const navItems = [
  { label: 'Dashboard',  to: '/',          icon: '📊' },
  { label: 'Topology',   to: '/topology',  icon: '🔗' },
  { label: 'Alerts',     to: '/alerts',    icon: '🔔' },
  { label: 'Routing',    to: '/routing',   icon: '🔀' },
]

export default function Sidebar() {
  return (
    <aside className="w-56 h-screen bg-gray-900 flex flex-col py-6 px-4 gap-2 fixed left-0 top-0">
      <div className="text-white font-bold text-lg mb-6 px-2">AINIS</div>
      {navItems.map(item => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.to === '/'}
          className={({ isActive }) =>
            `flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors ${
              isActive
                ? 'bg-blue-600 text-white'
                : 'text-gray-400 hover:bg-gray-800 hover:text-white'
            }`
          }
        >
          <span>{item.icon}</span>
          {item.label}
        </NavLink>
      ))}
    </aside>
  )
}