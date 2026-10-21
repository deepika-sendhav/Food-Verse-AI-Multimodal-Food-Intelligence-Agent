import { useEffect, useState, useRef } from 'react'
import { analyzeFreshness, extractFreshnessFeatures } from '../api/freshness.js'
import Alert from '../components/Alert.jsx'
import Button from '../components/Button.jsx'
import Card from '../components/Card.jsx'
import Dropzone from '../components/Dropzone.jsx'
import EmptyState from '../components/EmptyState.jsx'
import FreshnessResult from '../components/FreshnessResult.jsx'
import Skeleton from '../components/Skeleton.jsx'
import { IMAGE_LIMIT_BYTES, validateUpload } from '../utils/validation.js'

export default function FreshnessDetector() {
  const [file, setFile] = useState(null)
  const [storageTime, setStorageTime] = useState('')
  const [storageType, setStorageType] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [features, setFeatures] = useState(null)
  const [featureError, setFeatureError] = useState(null)
  const [featuresBusy, setFeaturesBusy] = useState(false)
  const [fileError, setFileError] = useState('')
  const abortRef = useRef(null)
  const featureAbortRef = useRef(null)
  useEffect(
    () => () => {
      abortRef.current?.abort()
      featureAbortRef.current?.abort()
    },
    [],
  )
  const selectFile = (next) => {
    const message = validateUpload(next)
    setFileError(message)
    setFile(message ? null : next)
    setResult(null)
    setFeatures(null)
    featureAbortRef.current?.abort()
  }
  const run = async () => {
    const validation = validateUpload(file)
    if (validation) {
      setFileError(validation)
      return
    }
    const form = new FormData()
    if (file) form.append('file', file)
    if (storageTime) form.append('storage_time', storageTime)
    if (storageType) form.append('storage_type', storageType)
    abortRef.current = new AbortController()
    setBusy(true)
    setError(null)
    try {
      setResult(
        await analyzeFreshness(form, { signal: abortRef.current.signal }),
      )
    } catch (reason) {
      if (!reason.cancelled) setError(reason)
    } finally {
      abortRef.current = null
      setBusy(false)
    }
  }
  const loadFeatures = async () => {
    if (features || !file) return
    const form = new FormData()
    form.append('file', file)
    featureAbortRef.current = new AbortController()
    try {
      setFeatureError(null)
      setFeaturesBusy(true)
      setFeatures(
        await extractFreshnessFeatures(form, {
          signal: featureAbortRef.current.signal,
        }),
      )
    } catch (reason) {
      if (!reason.cancelled) setFeatureError(reason)
    } finally {
      featureAbortRef.current = null
      setFeaturesBusy(false)
    }
  }
  return (
    <div className="page-wrap">
      <div className="page-heading">
        <p className="eyebrow">A closer look at your produce</p>
        <h1>Freshness detector</h1>
        <p>
          Explore visual freshness signals alongside the way an item has been
          stored.
        </p>
      </div>
      <div className="workspace-grid">
        <Card className="input-panel">
          <h2>Inspect an ingredient</h2>
          <Dropzone file={file} onFile={selectFile} />
          <p className="muted">
            JPG, PNG or WEBP · up to {IMAGE_LIMIT_BYTES / 1024 / 1024} MB
          </p>
          {fileError && (
            <p className="field-error" role="alert">
              {fileError}
            </p>
          )}
          <label className="field">
            <span>How long has it been stored?</span>
            <input
              maxLength="100"
              value={storageTime}
              onChange={(event) => setStorageTime(event.target.value)}
              placeholder="e.g. 3 days"
            />
          </label>
          <label className="field">
            <span>Where was it stored?</span>
            <select
              value={storageType}
              onChange={(event) => setStorageType(event.target.value)}
            >
              <option value="">Not specified</option>
              <option value="refrigerator">Refrigerator</option>
              <option value="freezer">Freezer</option>
              <option value="room_temperature">Room temperature</option>
              <option value="other">Other</option>
            </select>
          </label>
          <Button onClick={run} disabled={!file || busy}>
            {busy ? 'Checking signs…' : 'Assess freshness'}
          </Button>
          {busy && (
            <Button variant="quiet" onClick={() => abortRef.current?.abort()}>
              Cancel
            </Button>
          )}
        </Card>
        <div className="results-panel" aria-live="polite">
          <Alert error={error} onRetry={run} />
          {busy && (
            <Card>
              <p>Looking for visible signs…</p>
              <Skeleton lines={4} />
            </Card>
          )}
          {result ? (
            <FreshnessResult
              result={result}
              features={features}
              onLoadFeatures={loadFeatures}
              featureError={featureError}
              onRetryFeatures={loadFeatures}
              featuresBusy={featuresBusy}
              onCancelFeatures={() => featureAbortRef.current?.abort()}
            />
          ) : (
            <Card className="result-placeholder">
              <EmptyState title="A fresh perspective" />
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
