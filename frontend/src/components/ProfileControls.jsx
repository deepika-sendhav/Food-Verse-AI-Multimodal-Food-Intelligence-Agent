import { useState } from 'react'
import Alert from './Alert.jsx'
import Button from './Button.jsx'
import ResultList from './ResultList.jsx'
import { formatLabel } from '../utils/format.js'

export function Field({ label, value, onChange, hint, error, ...inputProps }) {
  return (
    <label className="field">
      <span>
        {label}
        {hint && <small>{hint}</small>}
      </span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-invalid={Boolean(error)}
        {...inputProps}
      />
      {error && <small className="field-error">{error}</small>}
    </label>
  )
}

export function Select({ label, value, options = [], labels, onChange }) {
  return (
    <label className="field">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option, index) => (
          <option key={option} value={option}>
            {labels?.[index] ?? formatLabel(option) ?? 'Not specified'}
          </option>
        ))}
      </select>
    </label>
  )
}

export function TagInput({
  label,
  values,
  onChange,
  hint,
  options = [],
  maxTags = 20,
}) {
  const [draft, setDraft] = useState('')
  const add = (value) => {
    const token = value.trim()
    if (token && !values.includes(token) && values.length < maxTags)
      onChange([...values, token])
    setDraft('')
  }
  return (
    <div className="field">
      <span>
        {label}
        {hint && <small>{hint}</small>}
      </span>
      {options.length > 0 && (
        <select
          aria-label={`Add ${label.toLowerCase()}`}
          value=""
          onChange={(event) => add(event.target.value)}
        >
          <option value="">Choose a common allergen…</option>
          {options
            .filter((item) => !values.includes(item))
            .map((item) => (
              <option key={item} value={item}>
                {formatLabel(item)}
              </option>
            ))}
        </select>
      )}
      <input
        value={draft}
        maxLength={label === 'Medical conditions' ? 500 : 50}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ',') {
            event.preventDefault()
            add(draft)
          }
        }}
        placeholder="Type and press Enter"
        aria-label={`${label} entry`}
      />
      <div className="chip-list">
        {values.map((value) => (
          <button
            className="tag-chip"
            type="button"
            key={value}
            onClick={() => onChange(values.filter((item) => item !== value))}
            aria-label={`Remove ${value}`}
          >
            {value} ×
          </button>
        ))}
      </div>
    </div>
  )
}

export function ProfileSummary({ profile, onDelete, onCancel, busy }) {
  return (
    <section className="profile-summary">
      <h3>Normalized profile</h3>
      <div className="metric-grid">
        <div className="metric">
          <span>Age</span>
          <strong>{profile.age_years}</strong>
        </div>
        <div className="metric">
          <span>Height</span>
          <strong>{profile.height_cm} cm</strong>
        </div>
        <div className="metric">
          <span>Weight</span>
          <strong>{profile.weight_kg} kg</strong>
        </div>
        <div className="metric">
          <span>BMI · informational only</span>
          <strong>{profile.bmi}</strong>
        </div>
      </div>
      <ResultList
        title="Excluded foods"
        items={profile.excluded_foods.map(
          (food) =>
            `${food.name} · ${food.reason}${food.strict ? ' · strict' : ''}`,
        )}
      />
      <ResultList
        title="Unrecognized allergies"
        items={profile.unrecognized_allergies}
      />
      <ResultList title="Warnings" items={profile.warnings} />
      {profile.safety_flags.map((flag) => (
        <Alert
          key={flag.code}
          tone={flag.severity === 'info' ? 'info' : 'error'}
          error={{ message: `${formatLabel(flag.severity)}: ${flag.message}` }}
        />
      ))}
      <Button variant="quiet" disabled={busy} onClick={onDelete}>
        Delete my data
      </Button>
      {busy && (
        <Button variant="quiet" onClick={onCancel}>
          Cancel
        </Button>
      )}
    </section>
  )
}
