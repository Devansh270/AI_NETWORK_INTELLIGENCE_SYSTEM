import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import DashboardPage from './pages/Dashboard'
import TopologyPage from './pages/Topology'
import AlertsPage from './pages/Alerts'
import RoutingPage from './pages/Routing'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<DashboardPage />} />
          <Route path="topology" element={<TopologyPage />} />
          <Route path="alerts" element={<AlertsPage />} />
          <Route path="routing" element={<RoutingPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
)