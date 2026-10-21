import { createContext, useContext, useEffect, useMemo, useState } from 'react'

const ThemeContext = createContext(null)

function preferredTheme() {
  const saved = localStorage.getItem('foodverse-theme')
  return (
    saved ||
    (window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark'
      : 'light')
  )
}

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(preferredTheme)
  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem('foodverse-theme', theme)
  }, [theme])
  const value = useMemo(
    () => ({
      theme,
      toggleTheme: () =>
        setTheme((current) => (current === 'dark' ? 'light' : 'dark')),
    }),
    [theme],
  )
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) throw new Error('useTheme must be used inside ThemeProvider')
  return context
}
