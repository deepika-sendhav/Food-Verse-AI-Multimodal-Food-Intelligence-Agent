import Alert from './Alert.jsx'
import Badge from './Badge.jsx'
import Card from './Card.jsx'
import Gauge from './Gauge.jsx'
import ResultList from './ResultList.jsx'

export default function HygieneResult({ result }) {
  return (
    <div className="result-stack">
      <Card className={`result-hero status-band status-band--${result.status}`}>
        <div>
          <p className="eyebrow">Hygiene review</p>
          <h2>{result.summary}</h2>
          <Badge
            tone={
              result.status === 'good'
                ? 'green'
                : result.status === 'action_required'
                  ? 'red'
                  : 'amber'
            }
          >
            {result.status}
          </Badge>
          <p>
            {result.frames_analyzed} frames analyzed ·{' '}
            {result.frames_skipped.length} skipped ·{' '}
            {result.frames_failed.length} failed
          </p>
        </div>
        {result.overall_score !== null ? (
          <Gauge
            value={Math.round(result.overall_score)}
            label="Overall score"
          />
        ) : (
          <div className="score-explanation">
            <strong>Insufficient evidence</strong>
            <p>A score could not be calculated from the selected frames.</p>
          </div>
        )}
      </Card>
      {result.frames_failed.length > 0 && (
        <Alert
          tone="info"
          error={{
            message: `Some frames could not be analyzed (${result.frames_failed.length}). Results may be partial.`,
          }}
        />
      )}
      <Card>
        <h3>Evidence & observations</h3>
        <div className="metric-grid">
          <div className="metric">
            <span>Overall evidence coverage</span>
            <strong>{Math.round(result.evidence_coverage * 100)}%</strong>
          </div>
          {Object.entries(result.category_evidence_coverage).map(
            ([key, value]) => (
              <div className="metric" key={key}>
                <span>{key.replaceAll('_', ' ')} evidence</span>
                <strong>{Math.round(value * 100)}%</strong>
              </div>
            ),
          )}
        </div>
        {result.violations.length ? (
          <div className="violation-list">
            {result.violations.map((item, index) => (
              <article className="violation" key={`${item.indicator}-${index}`}>
                <div className="violation__heading">
                  <strong>{item.indicator.replaceAll('_', ' ')}</strong>
                  <div className="chip-list">
                    <Badge tone={item.severity === 'High' ? 'red' : 'amber'}>
                      {item.severity}
                    </Badge>
                    <Badge tone={item.status === 'confirmed' ? 'red' : 'amber'}>
                      {item.status}
                    </Badge>
                  </div>
                </div>
                <p>{item.suggested_action}</p>
                {item.timestamps_seconds.length > 0 && (
                  <p className="muted">
                    At{' '}
                    {item.timestamps_seconds
                      .map((time) => `${time.toFixed(1)}s`)
                      .join(', ')}
                  </p>
                )}
                {item.evidence.map((evidence, evidenceIndex) => (
                  <p className="muted" key={`${evidence}-${evidenceIndex}`}>
                    {evidence}
                  </p>
                ))}
                <ResultList title="Coaching notes" items={item.notes} />
              </article>
            ))}
          </div>
        ) : (
          <p>No violations were flagged in the analyzed frames.</p>
        )}
        <h3>Category scores</h3>
        <div className="metric-grid">
          {Object.entries(result.category_scores).map(([key, value]) => (
            <div className="metric" key={key}>
              <span>{key.replaceAll('_', ' ')}</span>
              <strong>
                {value === null
                  ? 'Not enough evidence'
                  : `${Math.round(value)} / 100`}
              </strong>
            </div>
          ))}
        </div>
        <ResultList
          title="Alerts"
          items={result.alerts.map(
            (alert) => `${alert.title}: ${alert.message}`,
          )}
        />
        <ResultList
          title="Skipped frames"
          items={result.frames_skipped.map(
            (frame) =>
              `${frame.timestamp_seconds.toFixed(1)}s — ${frame.reason}`,
          )}
        />
        <ResultList
          title="Failed frames"
          items={result.frames_failed.map(
            (frame) =>
              `${frame.timestamp_seconds.toFixed(1)}s — ${frame.reason}`,
          )}
        />
        <ResultList title="Disclaimers" items={result.disclaimers} />
      </Card>
    </div>
  )
}
