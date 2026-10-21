import React from 'react'
import ReactDOM from 'react-dom/client'
import '@fontsource-variable/fraunces'
import '@fontsource/inter'
import './styles/global.css'
import App from './App.jsx'
import { ThemeProvider } from './hooks/useTheme.jsx'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ThemeProvider>
      <App />
    </ThemeProvider>
  </React.StrictMode>,
)
