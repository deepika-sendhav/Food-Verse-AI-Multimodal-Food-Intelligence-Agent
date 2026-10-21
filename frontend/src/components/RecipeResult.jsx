import {
  AlarmClock,
  ArrowDown,
  ArrowUp,
  Flame,
  CookingPot,
  Utensils,
  Timer,
} from 'lucide-react'
import Badge from './Badge.jsx'
import Button from './Button.jsx'
import Card from './Card.jsx'
import ResultList from './ResultList.jsx'

export default function RecipeResult({
  result,
  cookMode,
  setCookMode,
  cookStep,
  setCookStep,
  seconds,
  setSeconds,
  setTimerOn,
  wakeLockUnavailable,
}) {
  const orderedSteps = [...result.steps].sort(
    (left, right) => left.step_number - right.step_number,
  )
  const currentStep = orderedSteps[cookStep]
  const actionIcons = {
    prep: Utensils,
    chop: Utensils,
    heat: Flame,
    mix: ArrowDown,
    cook: CookingPot,
    rest: Timer,
    serve: Utensils,
    other: CookingPot,
  }
  const ActionIcon = currentStep
    ? actionIcons[currentStep.action_type] || CookingPot
    : CookingPot
  const startStepTimer = () => {
    setSeconds(Math.round((currentStep?.duration_minutes || 0) * 60))
    setTimerOn(true)
  }
  return (
    <div className="result-stack">
      <Card>
        <p className="eyebrow">
          Your kitchen idea · {result.input_type.replaceAll('_', ' ')}
        </p>
        <h2>{result.dish_name || result.interpreted_goal}</h2>
        <Badge tone={result.status === 'ok' ? 'green' : 'amber'}>
          {result.status}
        </Badge>
        {result.description && <p>{result.description}</p>}
        {result.clarifying_question && (
          <p className="notice" role="status">
            <strong>A little clarification:</strong>{' '}
            {result.clarifying_question}
          </p>
        )}
        <div className="metric-grid">
          <div className="metric">
            <span>Servings</span>
            <strong>{result.servings}</strong>
          </div>
          <div className="metric">
            <span>Total time</span>
            <strong>
              {result.total_time_minutes ?? 'Not available'}
              {result.total_time_minutes !== null ? ' min' : ''}
            </strong>
          </div>
          <div className="metric">
            <span>Difficulty</span>
            <strong>{result.difficulty || result.skill_level}</strong>
          </div>
        </div>
      </Card>
      {Boolean(result.ingredients.length) && (
        <Card>
          <h3>Ingredients</h3>
          <ul className="ingredient-list">
            {result.ingredients.map((item, index) => (
              <li key={`${item.name}-${index}`}>
                <span>
                  {item.quantity ?? ''} {item.unit ?? ''} {item.name}{' '}
                  {item.from_input && (
                    <Badge tone="green">From your input</Badge>
                  )}
                </span>
                {item.notes && <small>{item.notes}</small>}
                {item.dietary_conflict && (
                  <small className="field-error">
                    Dietary conflict flagged
                  </small>
                )}
              </li>
            ))}
          </ul>
        </Card>
      )}
      {Boolean(result.steps.length) && (
        <Card>
          <div className="section-title">
            <h3>Method</h3>
            <Button variant="quiet" onClick={() => setCookMode(!cookMode)}>
              {cookMode ? 'Exit cook mode' : 'Cook mode'}
            </Button>
          </div>
          {cookMode && currentStep ? (
            <div className="cook-mode">
              <p className="eyebrow">
                Step {cookStep + 1} of {orderedSteps.length} ·{' '}
                {currentStep.action_type}
              </p>
              <ActionIcon size={26} />
              <p className="cook-mode__instruction">
                {currentStep.instruction}
              </p>
              {currentStep.tip && <p className="muted">{currentStep.tip}</p>}
              {wakeLockUnavailable && (
                <p className="muted">
                  Screen wake lock is unavailable; your device may lock while
                  cooking.
                </p>
              )}
              <div className="cook-mode__controls">
                <Button
                  variant="quiet"
                  disabled={cookStep === 0}
                  onClick={() => {
                    setCookStep(cookStep - 1)
                    setTimerOn(false)
                  }}
                >
                  <ArrowUp size={15} /> Previous
                </Button>
                <span className="timer-readout">
                  {Math.floor(seconds / 60)}:
                  {String(seconds % 60).padStart(2, '0')}
                </span>
                <Button
                  variant="quiet"
                  disabled={!currentStep.duration_minutes}
                  onClick={startStepTimer}
                >
                  <AlarmClock size={15} /> Start timer
                </Button>
                <Button
                  disabled={cookStep === orderedSteps.length - 1}
                  onClick={() => {
                    setCookStep(cookStep + 1)
                    setTimerOn(false)
                    setSeconds(0)
                  }}
                >
                  Next <ArrowDown size={15} />
                </Button>
              </div>
            </div>
          ) : (
            <ol className="recipe-steps">
              {orderedSteps.map((step) => {
                const Icon = actionIcons[step.action_type] || CookingPot
                return (
                  <li key={step.step_number}>
                    <span className="step__number">
                      {String(step.step_number).padStart(2, '0')}
                    </span>
                    <div>
                      <strong>
                        <Icon size={15} aria-label={step.action_type} />{' '}
                        {step.instruction}
                      </strong>
                      {step.duration_minutes !== null && (
                        <p>
                          {step.duration_minutes} min · {step.action_type}
                          {step.heat_level ? ` · ${step.heat_level} heat` : ''}
                        </p>
                      )}
                      {step.tip && <p>{step.tip}</p>}
                    </div>
                  </li>
                )
              })}
            </ol>
          )}
        </Card>
      )}
      <Card>
        <h3>Kitchen notes</h3>
        <ResultList title="Allergens" items={result.allergens.contains} />
        <ResultList title="Safety notes" items={result.safety_notes} />
        <ResultList title="Warnings" items={result.warnings} />
        <ResultList title="Uncertainties" items={result.uncertainties} />
        <ResultList title="Disclaimers" items={result.disclaimers} />
        <ResultList title="Substitutions" items={result.substitutions} />
      </Card>
    </div>
  )
}
