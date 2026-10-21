import Badge from './Badge.jsx'
import Button from './Button.jsx'
import Card from './Card.jsx'
import Skeleton from './Skeleton.jsx'
import { Field, ProfileSummary, Select, TagInput } from './ProfileControls.jsx'

export default function ProfileEditor({
  options,
  profile,
  profileId,
  profileForm,
  setField,
  validation,
  setValidation,
  busy,
  submitProfile,
  removeData,
  onFillExample,
  onCancel,
}) {
  return (
    <Card className="profile-panel" id="profile">
      <div className="section-title">
        <div>
          <p className="eyebrow">Step 1 · Your profile</p>
          <h2>Set your table.</h2>
        </div>
        <Button type="button" variant="quiet" onClick={onFillExample}>
          Fill example profile
        </Button>
        {profile && (
          <Badge
            tone={profile.requires_professional_review ? 'amber' : 'green'}
          >
            {Math.round(profile.completeness_score)}% complete
          </Badge>
        )}
      </div>
      {!options ? (
        <>
          <p className="muted">Loading profile options…</p>
          <Skeleton lines={5} />
        </>
      ) : (
        <form className="profile-form" onSubmit={submitProfile} noValidate>
          <div className="form-row">
            <Select
              label="Sex"
              value={profileForm.sex}
              options={options.sexes}
              onChange={(v) => setField('sex', v)}
            />
            <Field
              label="Age (13–100)"
              value={profileForm.age_years}
              type="number"
              min="13"
              max="100"
              error={validation.age_years}
              onChange={(v) => {
                setField('age_years', v)
                setValidation((current) => ({
                  ...current,
                  age_years: numberInRange(v, 13, 100)
                    ? ''
                    : 'Age must be between 13 and 100 years.',
                }))
              }}
            />
          </div>
          <div className="form-row">
            <Field
              label="Height"
              value={profileForm.height}
              type="number"
              min="1"
              error={validation.height}
              onChange={(v) => {
                setField('height', v)
                const cm =
                  Number(v) * (profileForm.height_unit === 'in' ? 2.54 : 1)
                setValidation((current) => ({
                  ...current,
                  height: numberInRange(cm, 100, 250)
                    ? ''
                    : 'Height must be between 100 and 250 cm after conversion.',
                }))
              }}
            />
            <Select
              label="Height unit"
              value={profileForm.height_unit}
              options={options.height_units}
              onChange={(v) => {
                setField('height_unit', v)
                const cm = Number(profileForm.height) * (v === 'in' ? 2.54 : 1)
                setValidation((current) => ({
                  ...current,
                  height: numberInRange(cm, 100, 250)
                    ? ''
                    : 'Height must be between 100 and 250 cm after conversion.',
                }))
              }}
            />
          </div>
          <div className="form-row">
            <Field
              label="Weight"
              value={profileForm.weight}
              type="number"
              min="1"
              error={validation.weight}
              onChange={(v) => {
                setField('weight', v)
                const kg =
                  Number(v) *
                  (profileForm.weight_unit === 'lb' ? 0.45359237 : 1)
                setValidation((current) => ({
                  ...current,
                  weight: numberInRange(kg, 25, 300)
                    ? ''
                    : 'Weight must be between 25 and 300 kg after conversion.',
                }))
              }}
            />
            <Select
              label="Weight unit"
              value={profileForm.weight_unit}
              options={options.weight_units}
              onChange={(v) => {
                setField('weight_unit', v)
                const kg =
                  Number(profileForm.weight) * (v === 'lb' ? 0.45359237 : 1)
                setValidation((current) => ({
                  ...current,
                  weight: numberInRange(kg, 25, 300)
                    ? ''
                    : 'Weight must be between 25 and 300 kg after conversion.',
                }))
              }}
            />
          </div>
          <Select
            label="Activity level"
            value={profileForm.activity_level}
            options={options.activity_levels}
            onChange={(v) => setField('activity_level', v)}
          />
          <Select
            label="Health goal"
            value={profileForm.health_goal}
            options={options.health_goals}
            onChange={(v) => setField('health_goal', v)}
          />
          <Select
            label="Diet type"
            value={profileForm.diet_type}
            options={options.diet_types}
            onChange={(v) => setField('diet_type', v)}
          />
          <TagInput
            label="Allergies"
            values={profileForm.allergies}
            onChange={(v) => setField('allergies', v)}
            options={options.canonical_allergens}
            hint="Unknown allergies are kept as strict exclusions."
          />
          <TagInput
            label="Food restrictions"
            values={profileForm.food_restrictions}
            onChange={(v) => setField('food_restrictions', v)}
          />
          <TagInput
            label="Dislikes"
            values={profileForm.dislikes}
            onChange={(v) => setField('dislikes', v)}
          />
          <TagInput
            label="Medical conditions"
            values={profileForm.medical_conditions}
            onChange={(v) => setField('medical_conditions', v)}
            maxTags={10}
          />
          <TagInput
            label="Cuisine preferences"
            values={profileForm.cuisine_preferences}
            onChange={(v) => setField('cuisine_preferences', v)}
            maxTags={10}
          />
          <div className="form-row">
            <Field
              label="Meals per day (2–6)"
              value={profileForm.meals_per_day}
              type="number"
              min="2"
              max="6"
              error={validation.meals_per_day}
              onChange={(v) => setField('meals_per_day', v)}
            />
            <Select
              label="Pregnant or breastfeeding?"
              value={profileForm.pregnant_or_breastfeeding}
              options={['', 'true', 'false']}
              labels={['Not specified', 'Yes', 'No']}
              onChange={(v) => setField('pregnant_or_breastfeeding', v)}
            />
          </div>
          <p className="muted">
            BMI is informational only. Health information is held for this
            browser session only.
          </p>
          <Button type="submit" disabled={busy}>
            {busy
              ? 'Saving profile…'
              : profileId
                ? 'Save profile changes'
                : 'Save profile'}
          </Button>
          {busy && (
            <Button type="button" variant="quiet" onClick={onCancel}>
              Cancel
            </Button>
          )}
        </form>
      )}
      {profile && (
        <ProfileSummary
          profile={profile}
          onDelete={removeData}
          onCancel={onCancel}
          busy={busy}
        />
      )}
      {profileId && !profile && (
        <>
          <Button variant="quiet" disabled={busy} onClick={removeData}>
            Delete my data
          </Button>
          {busy && (
            <Button variant="quiet" onClick={onCancel}>
              Cancel
            </Button>
          )}
        </>
      )}
    </Card>
  )
}
