import { useEffect, useRef, useState } from 'react'
import { analyzeFood } from '../api/foodRecognition.js'
import Alert from '../components/Alert.jsx'
import Button from '../components/Button.jsx'
import Card from '../components/Card.jsx'
import Dropzone from '../components/Dropzone.jsx'
import EmptyState from '../components/EmptyState.jsx'
import FoodResult from '../components/FoodRecognitionResult.jsx'
import Skeleton from '../components/Skeleton.jsx'
import { IMAGE_LIMIT_BYTES, validateUpload } from '../utils/validation.js'

export default function FoodRecognition() {
  const [file, setFile] = useState(null)
  const [serving, setServing] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [fileError, setFileError] = useState('')
  const abortRef = useRef(null)
  useEffect(() => () => abortRef.current?.abort(), [])
  const selectFile = (next) => {
    const message = validateUpload(next)
    setFileError(message)
    setFile(message ? null : next)
    setResult(null)
  }
  const run = async () => {
    if (validateUpload(file)) {
      setFileError(validateUpload(file))
      return
    }
    if (
      serving &&
      (Number(serving) < 1 ||
        Number(serving) > 5000 ||
        !Number.isFinite(Number(serving)))
    ) {
      setFileError('Serving size must be between 1 and 5,000 grams.')
      return
    }
    setFileError('')
    const form = new FormData()
    if (file) form.append('file', file)
    if (serving) form.append('serving_size_g', serving)
    abortRef.current = new AbortController()
    setBusy(true)
    setError(null)
    try {
      setResult(await analyzeFood(form, { signal: abortRef.current.signal }))
    } catch (reason) {
      if (!reason.cancelled) setError(reason)
    } finally {
      abortRef.current = null
      setBusy(false)
    }
  }
  return (
    <div className="page-wrap">
      <div className="page-heading">
        <p className="eyebrow">See what’s on your plate</p>
        <h1>Food recognition</h1>
        <p>
          Get a thoughtful breakdown of a dish, its visible ingredients and
          estimated nutrition.
        </p>
      </div>
      <div className="workspace-grid">
        <Card className="input-panel">
          <h2>Start with a photo</h2>
          <p>Use a clear overhead image for the most useful read.</p>
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
            <span>
              Serving size{' '}
              <small>Optional · grams. Leave empty to use the default.</small>
            </span>
            <input
              type="number"
              min="1"
              max="5000"
              step="any"
              value={serving}
              onChange={(event) => setServing(event.target.value)}
              placeholder="Leave empty for default"
            />
          </label>
          <Button onClick={run} disabled={!file || busy}>
            {busy ? 'Reading your plate…' : 'Analyze food'}
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
              <p>Reading your plate…</p>
              <Skeleton lines={4} />
              <div className="progress-track">
                <span className="progress-track__indeterminate" />
              </div>
            </Card>
          )}
          {result ? (
            <FoodResult result={result} />
          ) : (
            <Card className="result-placeholder">
              <EmptyState title="Your plate, decoded" />
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
