import { Moon, Sun } from 'lucide-react'
import { useTheme } from '../hooks/useTheme.jsx'

export default function TopBar({ health }) {
  const { theme, toggleTheme } = useTheme()
  const status = health.status
  const label = {
    checking: 'Checking API',
    online: 'API connected',
    offline: 'API unavailable',
  }[status]
  return (
    <header className="topbar">
      <div className={`api-status api-status--${status}`} aria-live="polite">
        <span />
        {label}
      </div>
      <button
        type="button"
        className="theme-toggle"
        onClick={toggleTheme}
        aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
      >
        {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
        <span>{theme === 'dark' ? 'Light' : 'Dark'} mode</span>
      </button>
    </header>
  )
}
