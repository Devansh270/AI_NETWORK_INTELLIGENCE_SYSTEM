import Sidebar from './Sidebar'
import Header from './Header'
import { Outlet, useLocation } from 'react-router-dom'

const PAGE_TITLES = {
  '/':         'Dashboard',
  '/topology': 'Network Topology',
  '/alerts':   'Alerts',
  '/routing':  'Routing Rules',
}

export default function Layout() {
  const location = useLocation()
  const title = PAGE_TITLES[location.pathname] ?? 'AINIS'
  return (
    <div className="flex bg-gray-950 min-h-screen">
      <Sidebar />
      <div className="flex-1 ml-56 flex flex-col">
        <Header title={title} />
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}