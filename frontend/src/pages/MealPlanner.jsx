import { useEffect, useMemo, useRef, useState } from 'react'
import {
  createProfile,
  deleteProfile,
  getProfileOptions,
  updateProfile,
} from '../api/profile.js'
import { generateMealPlan as requestMealPlan } from '../api/mealPlanner.js'
import Alert from '../components/Alert.jsx'
import Button from '../components/Button.jsx'
import Card from '../components/Card.jsx'
import EmptyState from '../components/EmptyState.jsx'
import { PlanResult } from '../components/MealPlanResult.jsx'
import ProfileEditor from '../components/ProfileEditor.jsx'
import { Field, Select, TagInput } from '../components/ProfileControls.jsx'
import Skeleton from '../components/Skeleton.jsx'
import { numberInRange } from '../utils/validation.js'

const initialProfile = {
  age_years: '30',
  sex: 'prefer_not_to_say',
  height: '165',
  height_unit: 'cm',
  weight: '65',
  weight_unit: 'kg',
  activity_level: 'moderate',
  health_goal: 'eat_healthier',
  diet_type: 'omnivore',
  allergies: [],
  food_restrictions: [],
  dislikes: [],
  medical_conditions: [],
  pregnant_or_breastfeeding: '',
  meals_per_day: '3',
  cuisine_preferences: [],
}

export default function MealPlanner() {
  const [options, setOptions] = useState(null)
  const [profileForm, setProfileForm] = useState(initialProfile)
  const [profileId, setProfileId] = useState(
    () => sessionStorage.getItem('foodverse-profile-id') || '',
  )
  const [profile, setProfile] = useState(null)
  const [planType, setPlanType] = useState('daily')
  const [days, setDays] = useState('7')
  const [budget, setBudget] = useState('')
  const [cookTime, setCookTime] = useState('')
  const [history, setHistory] = useState([])
  const [plan, setPlan] = useState(null)
  const [selectedDay, setSelectedDay] = useState(0)
  const [error, setError] = useState(null)
  const [validation, setValidation] = useState({})
  const [planValidation, setPlanValidation] = useState('')
  const [busy, setBusy] = useState(false)
  const [filedMissing, setFiledMissing] = useState(false)
  const abortRef = useRef(null)
  const [retryAction, setRetryAction] = useState(null)

  const optionsAbortRef = useRef(null)
  const loadOptions = (signal) =>
    getProfileOptions({ signal })
      .then(setOptions)
      .catch((reason) => {
        if (!reason.cancelled) setError(reason)
      })
  useEffect(() => {
    optionsAbortRef.current = new AbortController()
    loadOptions(optionsAbortRef.current.signal)
    return () => {
      optionsAbortRef.current?.abort()
      abortRef.current?.abort()
    }
  }, [])

  const setField = (name, value) =>
    setProfileForm((form) => ({ ...form, [name]: value }))
  const heightCm =
    Number(profileForm.height) * (profileForm.height_unit === 'in' ? 2.54 : 1)
  const weightKg =
    Number(profileForm.weight) *
    (profileForm.weight_unit === 'lb' ? 0.45359237 : 1)
  const profileValidation = useMemo(
    () => ({
      age_years: numberInRange(profileForm.age_years, 13, 100)
        ? ''
        : 'Age must be between 13 and 100 years.',
      height: numberInRange(heightCm, 100, 250)
        ? ''
        : 'Height must be between 100 and 250 cm after conversion.',
      weight: numberInRange(weightKg, 25, 300)
        ? ''
        : 'Weight must be between 25 and 300 kg after conversion.',
      meals_per_day: numberInRange(profileForm.meals_per_day, 2, 6)
        ? ''
        : 'Choose between 2 and 6 meals per day.',
    }),
    [profileForm, heightCm, weightKg],
  )

  const validateProfileForm = () => {
    setValidation(profileValidation)
    return Object.values(profileValidation).every((message) => !message)
  }
  const makeProfileInput = () => ({
    ...profileForm,
    age_years: Number(profileForm.age_years),
    height: Number(profileForm.height),
    weight: Number(profileForm.weight),
    meals_per_day: Number(profileForm.meals_per_day),
    pregnant_or_breastfeeding:
      profileForm.pregnant_or_breastfeeding === ''
        ? null
        : profileForm.pregnant_or_breastfeeding === 'true',
  })
  const submitProfile = async (event) => {
    event.preventDefault()
    if (!validateProfileForm()) return
    setError(null)
    setBusy(true)
    setFiledMissing(false)
    abortRef.current = new AbortController()
    setRetryAction(() => () => submitProfile({ preventDefault() {} }))
    try {
      const input = makeProfileInput()
      const saved = profileId
        ? await updateProfile(profileId, input, {
            signal: abortRef.current.signal,
          })
        : await createProfile(input, { signal: abortRef.current.signal })
      setProfile(saved)
      setProfileId(saved.profile_id)
      sessionStorage.setItem('foodverse-profile-id', saved.profile_id)
    } catch (reason) {
      if (!reason.cancelled) {
        setError(reason)
        if (reason.status === 404) {
          setFiledMissing(true)
          setProfileId('')
          setProfile(null)
          setPlan(null)
          setProfileForm(initialProfile)
          setHistory([])
          sessionStorage.removeItem('foodverse-profile-id')
        }
      }
    } finally {
      abortRef.current = null
      setBusy(false)
    }
  }

  const requestPlan = async (acknowledgeReview = false) => {
    if (!numberInRange(days, 1, 7)) {
      setPlanValidation('Plan length must be between 1 and 7 days.')
      return
    }
    if (cookTime && !numberInRange(cookTime, 5, 120)) {
      setPlanValidation(
        'Maximum cooking time must be between 5 and 120 minutes.',
      )
      return
    }
    if (history.length > 14) {
      setPlanValidation('Recent history can include up to 14 meals.')
      return
    }
    setPlanValidation('')
    const input = {
      profile_id: profileId,
      plan_type: planType,
      days: Number(days),
      acknowledge_review: acknowledgeReview,
    }
    if (budget) input.budget_level = budget
    if (cookTime) input.cooking_time_minutes_max = Number(cookTime)
    if (history.length) input.recent_history = history
    setError(null)
    setBusy(true)
    abortRef.current = new AbortController()
    setRetryAction(() => () => requestPlan(acknowledgeReview))
    try {
      setPlan(
        await requestMealPlan(input, {
          signal: abortRef.current.signal,
          timeout: planType === 'weekly' ? 180_000 : 30_000,
        }),
      )
      setSelectedDay(0)
      setFiledMissing(false)
    } catch (reason) {
      if (reason.cancelled) return
      setError(reason)
      if (reason.status === 404) {
        setFiledMissing(true)
        setProfileId('')
        setProfile(null)
        setPlan(null)
        setRetryAction(null)
        sessionStorage.removeItem('foodverse-profile-id')
      }
    } finally {
      abortRef.current = null
      setBusy(false)
    }
  }
  const submitPlan = (event) => {
    event.preventDefault()
    requestPlan(false)
  }

  const removeData = async () => {
    setError(null)
    setBusy(true)
    setRetryAction(() => removeData)
    abortRef.current = new AbortController()
    try {
      if (profileId)
        await deleteProfile(profileId, { signal: abortRef.current.signal })
      sessionStorage.removeItem('foodverse-profile-id')
      setProfileId('')
      setProfile(null)
      setPlan(null)
      setProfileForm(initialProfile)
      setHistory([])
      setFiledMissing(false)
    } catch (reason) {
      if (reason.cancelled) return
      if (reason.status === 404) {
        sessionStorage.removeItem('foodverse-profile-id')
        setProfileId('')
        setProfile(null)
        setPlan(null)
        setProfileForm(initialProfile)
        setHistory([])
      } else setError(reason)
    } finally {
      abortRef.current = null
      setBusy(false)
    }
  }

  return (
    <div className="page-wrap">
      <div className="page-heading">
        <p className="eyebrow">Personalized, with care</p>
        <h1>Meal planner</h1>
        <p>
          Create a food profile, then ask for a daily or weekly plan shaped by
          your preferences.
        </p>
      </div>
      <Alert
        error={error}
        onRetry={
          filedMissing
            ? undefined
            : retryAction || (error ? loadOptions : undefined)
        }
      />
      {filedMissing && (
        <Alert
          tone="info"
          error={{
            message:
              'This profile is no longer available. Profiles are kept in backend memory and expire; recreate your profile below to continue.',
          }}
        />
      )}
      <div className="planner-grid">
        <ProfileEditor
          options={options}
          profile={profile}
          profileId={profileId}
          profileForm={profileForm}
          setField={setField}
          validation={validation}
          setValidation={setValidation}
          busy={busy}
          submitProfile={submitProfile}
          removeData={removeData}
          onFillExample={() =>
            setProfileForm({
              ...initialProfile,
              age_years: '34',
              sex: 'female',
              height: '168',
              weight: '70',
              activity_level: 'light',
              health_goal: 'maintain',
              diet_type: 'vegetarian',
              cuisine_preferences: ['Mediterranean'],
            })
          }
          onCancel={() => abortRef.current?.abort()}
        />
        <div className="planner-results" aria-live="polite">
          <Card>
            <p className="eyebrow">Step 2 · Planning preferences</p>
            <h2>What sounds good?</h2>
            <form className="profile-form" onSubmit={submitPlan}>
              <Select
                label="Plan type"
                value={planType}
                options={['daily', 'weekly']}
                onChange={setPlanType}
              />
              <Field
                label="Days (1–7)"
                type="number"
                min="1"
                max="7"
                value={days}
                onChange={setDays}
              />
              <Select
                label="Budget"
                value={budget}
                options={['', 'low', 'medium', 'high']}
                labels={['No preference', 'Low', 'Medium', 'High']}
                onChange={setBudget}
              />
              <Field
                label="Maximum cooking time (minutes)"
                type="number"
                min="5"
                max="120"
                value={cookTime}
                onChange={setCookTime}
              />{' '}
              <TagInput
                label="Recent history"
                hint="Meals from recent days, if useful."
                values={history}
                onChange={setHistory}
                maxTags={14}
              />
              <Button type="submit" disabled={!profileId || busy}>
                {busy ? 'Planning your meals…' : 'Generate meal plan'}
              </Button>
              {busy && planType === 'weekly' && (
                <p className="muted" role="status">
                  Weekly plans request each day separately and may take a few
                  minutes.
                </p>
              )}
              {busy && (
                <Button
                  type="button"
                  variant="quiet"
                  onClick={() => abortRef.current?.abort()}
                >
                  Cancel
                </Button>
              )}
              {planValidation && (
                <p className="field-error" role="alert">
                  {planValidation}
                </p>
              )}
              {!profileId && (
                <p className="muted">
                  Save a profile first to generate a personalized plan.
                </p>
              )}
            </form>
          </Card>
          {plan ? (
            <PlanResult
              result={plan}
              selectedDay={selectedDay}
              setSelectedDay={setSelectedDay}
              onAcknowledge={() => requestPlan(true)}
              busy={busy}
            />
          ) : (
            <Card className="result-placeholder">
              <EmptyState title="A week of possibility" />
            </Card>
          )}
        </div>
      </div>
      {busy && (
        <Card>
          <p>Working on your food plan…</p>
          <Skeleton lines={4} />
        </Card>
      )}
      <p className="disclaimer">
        Meal suggestions are estimates, not medical advice. Follow any
        professional guidance relevant to your health.
      </p>
    </div>
  )
}
