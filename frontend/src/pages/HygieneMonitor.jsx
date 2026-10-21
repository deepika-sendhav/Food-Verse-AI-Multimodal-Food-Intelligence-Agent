import { useEffect, useRef, useState } from 'react'
import { analyzeHygiene } from '../api/hygiene.js'
import Alert from '../components/Alert.jsx'
import Button from '../components/Button.jsx'
import Card from '../components/Card.jsx'
import Dropzone from '../components/Dropzone.jsx'
import EmptyState from '../components/EmptyState.jsx'
import HygieneResult from '../components/HygieneResult.jsx'
import Skeleton from '../components/Skeleton.jsx'
import { validateUpload, VIDEO_TYPES } from '../utils/validation.js'

const mediaTypes =
  'image/jpeg,image/png,image/webp,video/mp4,video/quicktime,video/x-msvideo,video/webm'

export default function HygieneMonitor() {
  const [file, setFile] = useState(null)
  const [contextRules, setContextRules] = useState('')
  const [interval, setInterval] = useState('10')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [fileError, setFileError] = useState('')
  const [progress, setProgress] = useState(0)
  const abortRef = useRef(null)
  useEffect(() => () => abortRef.current?.abort(), [])
  const setUpload = (next) => {
    const message = validateUpload(next, { video: true })
    setFileError(message)
    setFile(message ? null : next)
    setResult(null)
  }
  useEffect(() => {
    if (!busy) {
      setProgress(0)
      return undefined
    }
    const timer = window.setInterval(
      () => setProgress((value) => Math.min(92, value + 3)),
      2000,
    )
    return () => window.clearInterval(timer)
  }, [busy])
  const run = async () => {
    const validation = validateUpload(file, { video: true })
    if (validation) {
      setFileError(validation)
      return
    }
    const selectedVideo = VIDEO_TYPES.includes(file.type)
    if (contextRules.length > 500) {
      setFileError('Context rules must be 500 characters or fewer.')
      return
    }
    const form = new FormData()
    if (file) form.append('file', file)
    if (contextRules.trim()) form.append('context_rules', contextRules.trim())
    form.append('interval_seconds', interval)
    abortRef.current = new AbortController()
    setBusy(true)
    setError(null)
    setProgress(3)
    try {
      setResult(await analyzeHygiene(form, { signal: abortRef.current.signal }))
      setProgress(100)
    } catch (reason) {
      if (!reason.cancelled) setError(reason)
    } finally {
      abortRef.current = null
      setBusy(false)
      setFile(selectedVideo ? null : file)
    }
  }
  return (
    <div className="page-wrap">
      <div className="page-heading">
        <p className="eyebrow">Observe safer kitchen routines</p>
        <h1>Hygiene monitor</h1>
        <p>
          Review visible food-handling practices in an image or a short kitchen
          video. Results depend on what the media shows.
        </p>
      </div>
      <div className="workspace-grid">
        <Card className="input-panel">
          <h2>Add kitchen media</h2>
          <Dropzone
            file={file}
            onFile={setUpload}
            accept={mediaTypes}
            label="Choose image or video"
          />
          <p className="muted">
            Images: JPG, PNG or WEBP up to 10 MB. Videos: MP4, MOV, AVI or WEBM
            up to 50 MB.
          </p>
          {fileError && (
            <p className="field-error" role="alert">
              {fileError}
            </p>
          )}
          <label className="field">
            <span>
              Context rules <small>optional · up to 500 characters</small>
            </span>
            <textarea
              maxLength="500"
              value={contextRules}
              onChange={(event) => setContextRules(event.target.value)}
              placeholder="Add useful context for this review"
              rows="3"
            />
          </label>
          <label className="field">
            <span>
              Video frame interval <strong>{interval}s</strong>
            </span>
            <input
              type="range"
              min="1"
              max="30"
              value={interval}
              onChange={(event) => setInterval(event.target.value)}
              aria-label="Video frame interval in seconds"
            />
          </label>
          <Button onClick={run} disabled={!file || busy}>
            {busy ? 'Reviewing kitchen…' : 'Analyze hygiene'}
          </Button>
          {busy && (
            <Button variant="quiet" onClick={() => abortRef.current?.abort()}>
              Cancel analysis
            </Button>
          )}
          <p className="muted">
            Video analysis can take about a minute. The selected media preview
            is cleared after the request.
          </p>
        </Card>
        <div className="results-panel" aria-live="polite">
          <Alert error={error} onRetry={error && file ? run : undefined} />
          {busy && (
            <Card>
              <p>Reviewing visible evidence… {progress}%</p>
              <Skeleton lines={4} />
              <div className="progress-track">
                <span style={{ width: `${progress}%` }} />
              </div>
            </Card>
          )}
          {result ? (
            <HygieneResult result={result} />
          ) : (
            <Card className="result-placeholder">
              <EmptyState title="A clearer view of kitchen practice" />
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
