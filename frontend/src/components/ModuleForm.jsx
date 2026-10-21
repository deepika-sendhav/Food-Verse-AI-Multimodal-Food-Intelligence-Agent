import { useState } from 'react'
import Button from './Button.jsx'
import Alert from './Alert.jsx'

export default function ModuleForm({
  eyebrow,
  title,
  description,
  children,
  onSubmit,
  submitLabel = 'Analyze',
  loadingLabel = 'Working…',
  error,
  onRetry,
}) {
  const [busy, setBusy] = useState(false)
  const [lastData, setLastData] = useState(null)
  const handleSubmit = async (event) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    setLastData(data)
    setBusy(true)
    try {
      await onSubmit(data)
    } finally {
      setBusy(false)
    }
  }
  return (
    <div className="page-wrap">
      <div className="page-heading">
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      <Alert
        error={error}
        onRetry={error && lastData ? () => onRetry?.(lastData) : undefined}
      />
      <form className="module-form card" onSubmit={handleSubmit}>
        {children}
        <Button type="submit" disabled={busy}>
          {busy ? loadingLabel : submitLabel}
        </Button>
      </form>
    </div>
  )
}
