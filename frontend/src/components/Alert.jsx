import React, { useEffect, useState } from 'react'
import { AlertCircle, CheckCircle2, Info } from 'lucide-react'
import Button from './Button.jsx'

export default function Alert({ error, onRetry, tone = 'error' }) {
  if (!error) return null
  const Icon =
    tone === 'success' ? CheckCircle2 : tone === 'info' ? Info : AlertCircle
  return (
    <div
      className={`alert alert--${tone}`}
      role={tone === 'error' ? 'alert' : 'status'}
    >
      <Icon size={19} aria-hidden="true" />
      <div className="alert__content">
        <strong>{error.message || error}</strong>
        {error.retryAfter > 0 && <RetryCountdown seconds={error.retryAfter} />}
        {error.fieldErrors?.length > 0 && (
          <ul>
            {error.fieldErrors.map((item, index) => (
              <li key={`${item.field || item.loc?.join('.')}-${index}`}>
                {item.field || item.loc?.slice(1).join('.')}{' '}
                {item.message || item.msg}
              </li>
            ))}
          </ul>
        )}
      </div>
      {onRetry && (
        <Button variant="quiet" onClick={onRetry} aria-label="Retry request">
          Retry
        </Button>
      )}
    </div>
  )
}

function RetryCountdown({ seconds }) {
  const [remaining, setRemaining] = useState(seconds)
  useEffect(() => {
    setRemaining(seconds)
    const timer = window.setInterval(
      () => setRemaining((value) => Math.max(0, value - 1)),
      1000,
    )
    return () => window.clearInterval(timer)
  }, [seconds])
  return <span className="alert__countdown">Try again in {remaining}s</span>
}
