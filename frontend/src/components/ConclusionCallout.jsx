// Plain-English conclusion box.
// tone: 'green' (win/success), 'amber' (inconclusive), 'red' (negative / none).
const TONE_LABEL = {
  green: 'Looks good',
  amber: 'Inconclusive',
  red: 'No effect / negative',
}

export default function ConclusionCallout({ conclusion, tone = 'amber' }) {
  if (!conclusion) return null
  const { headline, details, recommendation } = conclusion

  return (
    <div className={`callout ${tone}`} role="status">
      <div className="callout-head">
        <span className="callout-badge">{TONE_LABEL[tone] || 'Result'}</span>
        <span>{headline}</span>
      </div>
      {details && <p className="callout-details">{details}</p>}
      {recommendation && (
        <p className="callout-rec">
          <strong>What to do: </strong>
          {recommendation}
        </p>
      )}
    </div>
  )
}
