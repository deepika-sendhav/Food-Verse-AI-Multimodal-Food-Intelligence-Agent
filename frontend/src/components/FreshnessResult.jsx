import Alert from './Alert.jsx'
import Badge from './Badge.jsx'
import Card from './Card.jsx'
import Gauge from './Gauge.jsx'
import ResultList from './ResultList.jsx'

export default function FreshnessResult({
  result,
  features,
  onLoadFeatures,
  featureError,
  onRetryFeatures,
  featuresBusy,
  onCancelFeatures,
}) {
  const confidence = Math.min(90, result.confidence)
  return (
    <div className="result-stack">
      <Card
        className={`result-hero freshness-verdict freshness-verdict--${result.color} freshness-verdict--${result.alert_level}`}
      >
        <div>
          <p className="eyebrow">Freshness assessment</p>
          <h2>{result.item_name || 'Your ingredient'}</h2>
          <Badge
            tone={
              result.alert_level === 'critical'
                ? 'red'
                : result.alert_level === 'warning'
                  ? 'amber'
                  : 'green'
            }
          >
            {result.alert_level} · {result.freshness_level}
          </Badge>
          <p>{result.safety_status}</p>
        </div>
        <Gauge value={confidence} label="Confidence · capped at 90" />
      </Card>
      <Card>
        <h3>What we observed</h3>
        <ResultList title="Detected signs" items={result.detected_signs} />
        <h3>Assessment</h3>
        <p>{result.reasoning}</p>
        <h3>Recommendation</h3>
        <p>{result.recommendation}</p>
        <ResultList title="Safety warnings" items={result.safety_warnings} />
        <div className="safety-disclaimer">
          <strong>Safety disclaimer</strong>
          <p>{result.safety_disclaimer}</p>
        </div>
        <ResultList title="Uncertainties" items={result.uncertainties} />
        <details
          className="measured-features"
          onToggle={(event) => {
            if (event.currentTarget.open) onLoadFeatures()
          }}
        >
          <summary>Measured features</summary>
          <Alert error={featureError} onRetry={onRetryFeatures} />
          {featuresBusy && (
            <p role="status">
              Measuring visible image features…
              <button type="button" onClick={onCancelFeatures}>
                Cancel
              </button>
            </p>
          )}
          {features ? (
            <FeatureValues value={features} />
          ) : (
            <p className="muted">
              Open this panel to request the image measurements.
            </p>
          )}
        </details>
      </Card>
    </div>
  )
}

function FeatureValues({ value }) {
  return (
    <div className="feature-grid">
      {Object.entries(value).map(([name, item]) => (
        <FeatureValue key={name} label={name} value={item} />
      ))}
    </div>
  )
}

function FeatureValue({ label, value }) {
  if (Array.isArray(value)) {
    return (
      <section className="feature-group">
        <h4>{label.replaceAll('_', ' ')}</h4>
        {value.map((item, index) => (
          <FeatureValue
            key={`${label}-${index}`}
            label={`item ${index + 1}`}
            value={item}
          />
        ))}
      </section>
    )
  }
  if (value && typeof value === 'object') {
    return (
      <section className="feature-group">
        <h4>{label.replaceAll('_', ' ')}</h4>
        {Object.entries(value).map(([name, item]) => (
          <FeatureValue key={name} label={name} value={item} />
        ))}
      </section>
    )
  }
  const rendered =
    typeof value === 'number'
      ? value.toFixed(3)
      : typeof value === 'boolean'
        ? value
          ? 'Yes'
          : 'No'
        : String(value)
  return (
    <div className="metric">
      <span>{label.replaceAll('_', ' ')}</span>
      <strong>{rendered}</strong>
    </div>
  )
}
