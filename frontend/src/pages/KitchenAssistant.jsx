import { useEffect, useRef, useState } from 'react'
import { Mic, MicOff } from 'lucide-react'
import { generateRecipe } from '../api/kitchenAssistant.js'
import Alert from '../components/Alert.jsx'
import Button from '../components/Button.jsx'
import Card from '../components/Card.jsx'
import Dropzone from '../components/Dropzone.jsx'
import EmptyState from '../components/EmptyState.jsx'
import RecipeResult from '../components/RecipeResult.jsx'
import Skeleton from '../components/Skeleton.jsx'
import { IMAGE_LIMIT_BYTES, validateUpload } from '../utils/validation.js'

export default function KitchenAssistant() {
  const [file, setFile] = useState(null)
  const [text, setText] = useState('')
  const [servings, setServings] = useState('2')
  const [skill, setSkill] = useState('beginner')
  const [diet, setDiet] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [fileError, setFileError] = useState('')
  const [listening, setListening] = useState(false)
  const [cookStep, setCookStep] = useState(0)
  const [cookMode, setCookMode] = useState(false)
  const [seconds, setSeconds] = useState(0)
  const [timerOn, setTimerOn] = useState(false)
  const [wakeLockUnavailable, setWakeLockUnavailable] = useState(false)
  const abortRef = useRef(null)
  const recognitionRef = useRef(null)
  const wakeLockRef = useRef(null)
  useEffect(() => () => abortRef.current?.abort(), [])
  const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition
  const setUpload = (next) => {
    const message = validateUpload(next)
    setFileError(message)
    setFile(message ? null : next)
    setResult(null)
  }
  useEffect(() => {
    if (!timerOn || seconds <= 0) return undefined
    const timer = window.setInterval(
      () => setSeconds((value) => Math.max(0, value - 1)),
      1000,
    )
    return () => window.clearInterval(timer)
  }, [timerOn, seconds])
  useEffect(() => {
    let active = true
    if (cookMode && 'wakeLock' in navigator) {
      navigator.wakeLock
        .request('screen')
        .then((lock) => {
          if (active) wakeLockRef.current = lock
          else lock.release()
        })
        .catch(() => {
          if (active) setWakeLockUnavailable(true)
        })
    }
    if (!cookMode) {
      wakeLockRef.current?.release()
      wakeLockRef.current = null
      setWakeLockUnavailable(false)
    }
    return () => {
      active = false
      wakeLockRef.current?.release()
    }
  }, [cookMode])
  useEffect(() => () => recognitionRef.current?.stop(), [])
  const toggleDictation = () => {
    if (!SpeechRecognition) return
    if (listening) {
      recognitionRef.current?.stop()
      setListening(false)
      return
    }
    const recognition = new SpeechRecognition()
    recognition.lang = navigator.language || 'en-US'
    recognition.interimResults = true
    const baseText = text.trim()
    recognition.onresult = (event) =>
      setText(
        `${baseText}${baseText ? ' ' : ''}${Array.from(event.results)
          .map((entry) => entry[0].transcript)
          .join(' ')}`.slice(0, 1000),
      )
    recognition.onend = () => setListening(false)
    recognitionRef.current = recognition
    recognition.start()
    setListening(true)
  }
  const run = async () => {
    if (text.length > 1000 || diet.length > 200) {
      setFileError(
        'Text input must be 1,000 characters or fewer and dietary preferences 200 characters or fewer.',
      )
      return
    }
    if (
      !Number.isInteger(Number(servings)) ||
      Number(servings) < 1 ||
      Number(servings) > 12
    ) {
      setFileError('Servings must be between 1 and 12.')
      return
    }
    if (file && validateUpload(file)) {
      setFileError(validateUpload(file))
      return
    }
    if (!file && !text.trim()) {
      setFileError(
        'Add ingredients in text or choose an image before generating a recipe.',
      )
      return
    }
    const form = new FormData()
    if (text.trim()) form.append('text_input', text.trim())
    if (file) form.append('file', file)
    form.append('servings', servings)
    form.append('skill_level', skill)
    if (diet.trim()) form.append('dietary_preferences', diet.trim())
    abortRef.current = new AbortController()
    setBusy(true)
    setError(null)
    try {
      setResult(await generateRecipe(form, { signal: abortRef.current.signal }))
      setCookStep(0)
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
        <p className="eyebrow">Make something of what you have</p>
        <h1>Kitchen assistant</h1>
        <p>
          Share ingredients as words, a photo, or a little of both to get a
          recipe idea.
        </p>
      </div>
      <div className="workspace-grid">
        <Card className="input-panel">
          <h2>What’s in your kitchen?</h2>
          <label className="field">
            <span>
              Ingredients or cooking goal{' '}
              <small>optional · up to 1,000 characters</small>
            </span>
            <textarea
              maxLength="1000"
              value={text}
              onChange={(event) => setText(event.target.value)}
              rows="4"
              placeholder={
                result?.clarifying_question
                  ? 'Answer the question here, then generate again'
                  : 'e.g. Chickpeas, spinach and lemon'
              }
            />
          </label>
          <Button
            type="button"
            variant="quiet"
            onClick={() =>
              setText(
                'I have cooked lentils, spinach, lemon, garlic, and brown rice. Suggest a simple beginner-friendly dinner.',
              )
            }
          >
            Use sample text
          </Button>
          {SpeechRecognition && (
            <Button
              type="button"
              variant="quiet"
              onClick={toggleDictation}
              aria-pressed={listening}
            >
              {listening ? <MicOff size={16} /> : <Mic size={16} />}
              {listening ? 'Stop dictation' : 'Dictate ingredients'}
            </Button>
          )}
          <Dropzone file={file} onFile={setUpload} />
          <p className="muted">
            JPG, PNG or WEBP · up to {IMAGE_LIMIT_BYTES / 1024 / 1024} MB
          </p>
          {fileError && (
            <p className="field-error" role="alert">
              {fileError}
            </p>
          )}
          <div className="form-row">
            <label className="field">
              <span>Servings</span>
              <input
                type="number"
                min="1"
                max="12"
                value={servings}
                onChange={(event) => setServings(event.target.value)}
              />
            </label>
            <label className="field">
              <span>Skill level</span>
              <select
                value={skill}
                onChange={(event) => setSkill(event.target.value)}
              >
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </select>
            </label>
          </div>
          <label className="field">
            <span>
              Dietary preferences <small>optional · up to 200 characters</small>
            </span>
            <input
              maxLength="200"
              value={diet}
              onChange={(event) => setDiet(event.target.value)}
              placeholder="e.g. vegetarian, no nuts"
            />
          </label>
          <Button onClick={run} disabled={busy}>
            {busy
              ? 'Creating an idea…'
              : result?.status === 'needs_clarification'
                ? 'Answer & try again'
                : 'Generate recipe'}
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
              <p>Thinking through your ingredients…</p>
              <Skeleton lines={4} />
              <div className="progress-track">
                <span className="progress-track__indeterminate" />
              </div>
            </Card>
          )}
          {result ? (
            <RecipeResult
              result={result}
              cookMode={cookMode}
              setCookMode={setCookMode}
              cookStep={cookStep}
              setCookStep={setCookStep}
              seconds={seconds}
              setSeconds={setSeconds}
              setTimerOn={setTimerOn}
              wakeLockUnavailable={wakeLockUnavailable}
            />
          ) : (
            <Card className="result-placeholder">
              <EmptyState title="A recipe is taking shape" />
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
