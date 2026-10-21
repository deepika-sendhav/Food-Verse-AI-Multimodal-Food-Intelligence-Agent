export default function Gauge({ value, label = 'Score' }) {
  const safeValue = Number.isFinite(value)
    ? Math.min(100, Math.max(0, value))
    : 0
  return (
    <div
      className="gauge"
      role="img"
      aria-label={`${label}: ${value ?? 'not available'} out of 100`}
    >
      <svg viewBox="0 0 120 70" aria-hidden="true">
        <path className="gauge__track" d="M 12 62 A 48 48 0 0 1 108 62" />
        <path
          className="gauge__value"
          d="M 12 62 A 48 48 0 0 1 108 62"
          pathLength="100"
          style={{ strokeDasharray: `${safeValue} 100` }}
        />
      </svg>
      <strong>
        {value ?? '—'}
        <small>/100</small>
      </strong>
      <span>{label}</span>
    </div>
  )
}
