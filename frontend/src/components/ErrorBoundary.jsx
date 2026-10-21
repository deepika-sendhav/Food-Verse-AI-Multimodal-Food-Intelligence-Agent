import React from 'react'
import { AlertTriangle } from 'lucide-react'

export default class ErrorBoundary extends React.Component {
  state = { hasError: false }
  static getDerivedStateFromError() {
    return { hasError: true }
  }
  render() {
    if (this.state.hasError)
      return (
        <div className="error-boundary" role="alert">
          <AlertTriangle />
          <h2>That view could not be displayed.</h2>
          <p>Refresh the page to try again.</p>
        </div>
      )
    return this.props.children
  }
}
