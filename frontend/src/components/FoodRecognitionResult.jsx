import Badge from './Badge.jsx'
import Card from './Card.jsx'
import Gauge from './Gauge.jsx'
import ResultList from './ResultList.jsx'
import { displayValue } from '../utils/format.js'

export default function FoodResult({ result }) {
  const nutrition = result.nutrition
  const measures = [
    ['Calories', nutrition.calories_kcal, ' kcal', 800],
    ['Protein', nutrition.protein_g, ' g', 60],
    ['Carbohydrates', nutrition.carbs_g, ' g', 100],
    ['Fats', nutrition.fats_g, ' g', 70],
    ['Fiber', nutrition.fiber_g, ' g', 30],
    ['Sugar', nutrition.sugar_g, ' g', 50],
  ]
  return (
    <div className="result-stack">
      <Card className="result-hero">
        <div>
          <p className="eyebrow">Food analysis</p>
          <h2>{result.dish_name || 'Dish identified'}</h2>
          <div className="chip-list">
            {result.detected_items?.map((item) => (
              <Badge key={item} tone="green">
                {item}
              </Badge>
            ))}
          </div>
          <p>{result.description}</p>
        </div>
        {result.health_score !== null ? (
          <Gauge
            value={result.health_score}
            label={result.health_label || 'Health score'}
          />
        ) : (
          <div className="score-explanation">
            <strong>Health score unavailable</strong>
            <p>The response did not include a score for this dish.</p>
          </div>
        )}
      </Card>
      <Card>
        <h3>Nutrition estimate</h3>
        <p className="muted">
          {nutrition.serving_description}
          {nutrition.serving_size_is_assumed ? ' · serving size assumed' : ''}
        </p>
        <div className="nutrition-table">
          {measures.map(([label, value, unit, max]) => (
            <div className="nutrition-row" key={label}>
              <span>{label}</span>
              <div className="nutrition-bar">
                <span
                  style={{
                    width:
                      value == null
                        ? '0%'
                        : `${Math.min(100, (value / max) * 100)}%`,
                  }}
                />
              </div>
              <strong>{displayValue(value, unit)}</strong>
            </div>
          ))}
        </div>
        <p className="source-note">Source: {nutrition.source}</p>
        <ResultList
          title="Nutrition uncertainties"
          items={nutrition.uncertainties}
        />
      </Card>
      <Card>
        <h3>Insights & context</h3>
        <p>{result.reasoning}</p>
        <ResultList title="Insights" items={result.insights} />
        <ResultList
          title="Consider these alternatives"
          items={result.alternatives}
        />
        <ResultList title="Uncertainties" items={result.uncertainties} />
        <p className="disclaimer">
          Nutrition values are estimates and may vary with ingredients and
          serving size.
        </p>
      </Card>
    </div>
  )
}
