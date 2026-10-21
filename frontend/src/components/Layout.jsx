import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar.jsx'
import TopBar from './TopBar.jsx'
import ErrorBoundary from './ErrorBoundary.jsx'
import useApiHealth from '../hooks/useApiHealth.js'

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false)
  const health = useApiHealth()
  return (
    <div className={`app-shell ${collapsed ? 'app-shell--collapsed' : ''}`}>
      <Sidebar
        collapsed={collapsed}
        onToggle={() => setCollapsed((value) => !value)}
      />
      <div className="app-main">
        <TopBar health={health} />
        {health.demo && (
          <div
            className="demo-banner"
            role="status"
            aria-label="Demo mode: sample data only"
          >
            Demo mode: sample data only. No real analysis was performed.
          </div>
        )}
        <main id="main-content">
          <ErrorBoundary>
            <Outlet context={health} />
          </ErrorBoundary>
        </main>
      </div>
    </div>
  )
}
