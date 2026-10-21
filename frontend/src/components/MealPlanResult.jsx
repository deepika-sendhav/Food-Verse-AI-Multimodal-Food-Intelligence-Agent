import Badge from './Badge.jsx'
import Button from './Button.jsx'
import Card from './Card.jsx'
import ResultList from './ResultList.jsx'
import { formatLabel } from '../utils/format.js'

export function PlanResult({
  result,
  selectedDay,
  setSelectedDay,
  onAcknowledge,
  busy,
}) {
  const activeDay = result.days[selectedDay]
  const macros = [
    ['Protein', result.targets.protein_g, 'var(--macro-protein)'],
    ['Carbs', result.targets.carbs_g, 'var(--macro-carbs)'],
    ['Fat', result.targets.fats_g, 'var(--macro-fat)'],
  ]
  const total = macros.reduce((sum, [, value]) => sum + (value || 0), 0) || 1
  const segments = macros
    .map(
      ([label, value, color], index) =>
        `${color} ${macros.slice(0, index).reduce((acc, item) => acc + ((item[1] || 0) / total) * 100, 0)}% ${macros.slice(0, index + 1).reduce((acc, item) => acc + ((item[1] || 0) / total) * 100, 0)}%`,
    )
    .join(', ')
  const review = result.status === 'professional_review_required'
  return (
    <div className="result-stack">
      <Card>
        <p className="eyebrow">Meal plan</p>
        <h2>
          {review ? 'A note before you continue' : formatLabel(result.status)}
        </h2>
        <Badge
          tone={
            result.alert_level === 'critical'
              ? 'red'
              : result.alert_level === 'warning' || review
                ? 'amber'
                : 'green'
          }
        >
          {result.alert_level}
        </Badge>
        {review && (
          <div className="safety-disclaimer">
            <strong>Professional review is recommended</strong>
            <p>
              This plan needs review by a qualified professional before you rely
              on personalized recommendations.
            </p>
            <ResultList
              title="Safety flags"
              items={result.safety_flags.map(
                (flag) =>
                  `${formatLabel(flag.severity)} · ${flag.code}: ${flag.message}`,
              )}
            />
            <Button variant="quiet" disabled={busy} onClick={onAcknowledge}>
              Show general healthy eating outline
            </Button>
          </div>
        )}
        <div className="metric-grid">
          <div className="metric">
            <span>Daily calories target</span>
            <strong>{result.targets.calories ?? 'Not available'}</strong>
          </div>
          <div className="metric">
            <span>Hydration target</span>
            <strong>
              {result.targets.hydration_ml == null
                ? 'Not available'
                : `${result.targets.hydration_ml} ml`}
            </strong>
          </div>
          <div className="metric">
            <span>Plan type</span>
            <strong>{formatLabel(result.plan_type)}</strong>
          </div>
        </div>
        {macros.some(([, value]) => value != null) && (
          <div className="macro-chart-wrap">
            <div
              className="macro-donut"
              role="img"
              aria-label="Macronutrient target distribution"
              style={{ background: `conic-gradient(${segments})` }}
            >
              <span>Targets</span>
            </div>
            <div className="macro-legend">
              {macros.map(([label, value, color]) => (
                <span key={label}>
                  <i style={{ background: color }} />
                  {label}: {value == null ? 'Not available' : `${value} g`}
                </span>
              ))}
            </div>
          </div>
        )}
        <ResultList title="Target notes" items={result.targets.notes} />
        {result.status === 'partial' && (
          <ResultList
            title="Days not generated"
            items={result.failed_days.map(
              (day) => `Day ${day.day_number}: ${day.reason}`,
            )}
          />
        )}
        {result.general_outline.length > 0 && (
          <div className="outline-panel">
            <h3>General healthy eating outline</h3>
            <ul>
              {result.general_outline.map((item, index) => (
                <li key={`${item}-${index}`}>{item}</li>
              ))}
            </ul>
          </div>
        )}
        <ResultList title="Warnings" items={result.warnings} />
      </Card>
      {result.days.length > 0 && (
        <Card>
          <div className="day-tabs" role="tablist" aria-label="Meal plan days">
            {result.days.map((day, index) => (
              <button
                type="button"
                role="tab"
                aria-selected={selectedDay === index}
                className={
                  selectedDay === index ? 'day-tab day-tab--active' : 'day-tab'
                }
                key={day.day_number}
                onClick={() => setSelectedDay(index)}
              >
                Day {day.day_number}
              </button>
            ))}
          </div>
          {activeDay && (
            <>
              <div className="section-title">
                <h3>Day {activeDay.day_number}</h3>
                <span>
                  {Math.round(activeDay.daily_totals.calories_kcal)} kcal
                </span>
              </div>
              <div className="meal-list">
                {activeDay.meals.map((meal, index) => (
                  <article
                    className="meal-card"
                    key={`${meal.meal_slot}-${index}`}
                  >
                    <div className="meal-item">
                      <div>
                        <Badge>{meal.meal_slot}</Badge>
                        <h3>{meal.dish_name || 'Meal unavailable'}</h3>
                        <p>{meal.description || meal.unavailable_reason}</p>
                      </div>
                      {meal.prep_time_minutes != null && (
                        <Badge tone="neutral">
                          {meal.prep_time_minutes} min
                        </Badge>
                      )}
                    </div>
                    {meal.status === 'available' &&
                      meal.estimated_nutrition && (
                        <div className="metric-grid">
                          <div className="metric">
                            <span>Calories</span>
                            <strong>
                              {meal.estimated_nutrition.calories_kcal} kcal
                            </strong>
                          </div>
                          <div className="metric">
                            <span>Protein</span>
                            <strong>
                              {meal.estimated_nutrition.protein_g} g
                            </strong>
                          </div>
                          <div className="metric">
                            <span>Carbs</span>
                            <strong>
                              {meal.estimated_nutrition.carbs_g} g
                            </strong>
                          </div>
                        </div>
                      )}
                    {meal.ingredients?.length > 0 && (
                      <p className="muted">
                        Ingredients:{' '}
                        {meal.ingredients
                          .map((ingredient) => ingredient.name)
                          .join(', ')}
                      </p>
                    )}
                    {meal.alternatives?.length > 0 && (
                      <details>
                        <summary>
                          Alternatives ({meal.alternatives.length})
                        </summary>
                        {meal.alternatives.map((alternative) => (
                          <p key={alternative.dish_name}>
                            <strong>{alternative.dish_name}</strong> —{' '}
                            {alternative.description} ·{' '}
                            {alternative.estimated_nutrition.calories_kcal} kcal
                          </p>
                        ))}
                      </details>
                    )}
                    {meal.nutrition_notes?.length > 0 && (
                      <ResultList
                        title="Nutrition notes"
                        items={meal.nutrition_notes}
                      />
                    )}
                  </article>
                ))}
              </div>
              <h3>Daily totals vs targets</h3>
              <div className="metric-grid">
                <div className="metric">
                  <span>Calories</span>
                  <strong>
                    {activeDay.daily_totals.calories_kcal} /{' '}
                    {result.targets.calories ?? '—'} kcal
                  </strong>
                </div>
                <div className="metric">
                  <span>Protein</span>
                  <strong>
                    {activeDay.daily_totals.protein_g} /{' '}
                    {result.targets.protein_g ?? '—'} g
                  </strong>
                </div>
                <div className="metric">
                  <span>Carbohydrates</span>
                  <strong>
                    {activeDay.daily_totals.carbs_g} /{' '}
                    {result.targets.carbs_g ?? '—'} g
                  </strong>
                </div>
                <div className="metric">
                  <span>Fat</span>
                  <strong>
                    {activeDay.daily_totals.fats_g} /{' '}
                    {result.targets.fats_g ?? '—'} g
                  </strong>
                </div>
                <div className="metric">
                  <span>Fiber</span>
                  <strong>
                    {activeDay.daily_totals.fiber_g} /{' '}
                    {result.targets.fiber_g ?? '—'} g
                  </strong>
                </div>
              </div>
            </>
          )}
        </Card>
      )}
      {result.weekly_report && (
        <Card>
          <h3>Weekly report</h3>
          <div className="metric-grid">
            <div className="metric">
              <span>Average daily calories</span>
              <strong>
                {result.weekly_report.average_daily_calories ?? 'Not available'}
              </strong>
            </div>
            <div className="metric">
              <span>Variety score</span>
              <strong>
                {Math.round(result.weekly_report.variety_score * 100)}%
              </strong>
            </div>
            <div className="metric">
              <span>Days within 10% target</span>
              <strong>
                {result.weekly_report.days_within_10_percent_of_target}/7
              </strong>
            </div>
          </div>
          <ResultList
            title="Highlights"
            items={result.weekly_report.highlights}
          />
          <ResultList
            title="Areas to consider"
            items={result.weekly_report.concern_areas}
          />
        </Card>
      )}
      <Card>
        <ResultList
          title="Adaptive suggestions"
          items={result.adaptive_suggestions}
        />
        <ResultList title="Disclaimers" items={result.disclaimers} />
      </Card>
    </div>
  )
}
