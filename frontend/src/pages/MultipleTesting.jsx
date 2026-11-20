import { useState } from 'react'
import { apiPost } from '../api/client.js'
import { fmtNum, fmtP, uniqueValues } from '../lib/format.js'
import StatCard from '../components/StatCard.jsx'
import Loading from '../components/Loading.jsx'
import ErrorBanner from '../components/ErrorBanner.jsx'
import { BarChartView, ChartCard, COLORS } from '../components/charts.jsx'

const METHOD_OPTIONS = [
  { id: 'bonferroni', label: 'Bonferroni' },
  { id: 'benjamini-hochberg', label: 'Benjamini–Hochberg' },
]

const METHOD_COLORS = {
  bonferroni: COLORS.indigo,
  'benjamini-hochberg': COLORS.amber,
}

const EXAMPLE =
  '0.0012, 0.021, 0.045, 0.12, 0.33, 0.0004, 0.61, 0.008'

function parseNumbers(text) {
  return text
    .split(/[\s,;]+/)
    .map((t) => t.trim())
    .filter(Boolean)
    .map((t) => Number(t))
    .filter((n) => Number.isFinite(n))
}

function parseNames(text) {
  return text
    .split(/[\n,;]+/)
    .map((t) => t.trim())
    .filter(Boolean)
}

export default function MultipleTesting() {
  const [pvaluesText, setPvaluesText] = useState(EXAMPLE)
  const [namesText, setNamesText] = useState('')
  const [methods, setMethods] = useState(['bonferroni', 'benjamini-hochberg'])
  const [alpha, setAlpha] = useState('0.05')

  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  function toggleMethod(id) {
    setMethods((prev) => (prev.includes(id) ? prev.filter((m) => m !== id) : [...prev, id]))
  }

  async function run() {
    const pvalues = parseNumbers(pvaluesText)
    if (!pvalues.length) {
      setError('Enter at least one valid p-value.')
      return
    }
    if (!methods.length) {
      setError('Select at least one correction method.')
      return
    }
    const names = parseNames(namesText)
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const res = await apiPost('/analysis/multiple-testing', {
        pvalues,
        metric_names: names.length ? names : undefined,
        methods,
        alpha: Number(alpha),
      })
      setResult(res)
    } catch (e) {
      setError(e.message || String(e))
    } finally {
      setLoading(false)
    }
  }

  const methodKeys = result ? Object.keys(result.by_method || {}) : []
  const chartData = result
    ? (result.pvalues || []).map((p, i) => {
        const row = { name: result.metric_names?.[i] || `metric_${i}`, original: p }
        for (const key of methodKeys) {
          row[key] = result.by_method[key].adjusted_pvalues?.[i]
        }
        return row
      })
    : []

  const totalRejected = result
    ? Object.fromEntries(
        methodKeys.map((key) => [
          key,
          (result.by_method[key].reject || []).filter(Boolean).length,
        ]),
      )
    : {}

  return (
    <div className="stack">
      <div className="card">
        <div className="card-header">
          <span className="card-title">Inputs</span>
        </div>

        <div className="grid grid-2">
          <label className="field">
            <span className="field-label">P-values (comma or newline separated)</span>
            <textarea
              className="input"
              rows={4}
              value={pvaluesText}
              onChange={(e) => setPvaluesText(e.target.value)}
              placeholder="0.012, 0.045, 0.31 …"
            />
          </label>
          <label className="field">
            <span className="field-label">Metric names (optional, one per line)</span>
            <textarea
              className="input"
              rows={4}
              value={namesText}
              onChange={(e) => setNamesText(e.target.value)}
              placeholder="signup_rate&#10;retention_7&#10;revenue …"
            />
          </label>
        </div>

        <div className="grid grid-2">
          <div className="field">
            <span className="field-label">Correction methods</span>
            <div className="checkbox-list">
              {METHOD_OPTIONS.map((opt) => (
                <label key={opt.id} className="checkbox-item">
                  <input
                    type="checkbox"
                    checked={methods.includes(opt.id)}
                    onChange={() => toggleMethod(opt.id)}
                  />
                  {opt.label}
                </label>
              ))}
            </div>
          </div>
          <label className="field">
            <span className="field-label">Alpha</span>
            <input
              className="input"
              type="number"
              step="0.01"
              value={alpha}
              onChange={(e) => setAlpha(e.target.value)}
            />
          </label>
        </div>

        <div className="btn-row">
          <button className="btn btn-primary" type="button" onClick={run} disabled={loading}>
            {loading ? 'Running…' : 'Run corrections'}
          </button>
          <button
            className="btn btn-secondary"
            type="button"
            onClick={() => {
              setPvaluesText(EXAMPLE)
              setNamesText('')
            }}
          >
            Load example
          </button>
        </div>

        <ErrorBanner message={error} onClose={() => setError('')} />
        {loading && <Loading label="Applying corrections…" />}
      </div>

      {result && (
        <>
          <div className="grid grid-4">
            <StatCard label="Tests" value={fmtNum(result.n_tests, 6)} hint="p-values corrected" />
            <StatCard label="Alpha" value={fmtNum(result.alpha, 4)} />
            {methodKeys.map((key) => (
              <StatCard
                key={key}
                label={`Rejected · ${key}`}
                value={fmtNum(totalRejected[key], 6)}
                tone="green"
                hint="metrics declared significant"
              />
            ))}
          </div>

          <div className="card">
            <div className="card-header">
              <span className="card-title">Adjusted p-values</span>
            </div>
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Metric</th>
                    <th>Original p</th>
                    {methodKeys.map((key) => (
                      <th key={`${key}-adj`}>{key} adj. p</th>
                    ))}
                    {methodKeys.map((key) => (
                      <th key={`${key}-rej`}>{key} reject</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(result.pvalues || []).map((p, i) => (
                    <tr key={i}>
                      <td>{result.metric_names?.[i] || `metric_${i}`}</td>
                      <td>{fmtP(p)}</td>
                      {methodKeys.map((key) => (
                        <td key={`${key}-adj`}>
                          {fmtNum(result.by_method[key].adjusted_pvalues?.[i], 5)}
                        </td>
                      ))}
                      {methodKeys.map((key) => (
                        <td key={`${key}-rej`}>
                          {result.by_method[key].reject?.[i] ? (
                            <span className="pill green">reject</span>
                          ) : (
                            <span className="pill slate">retain</span>
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="divider" />
            <p className="field-hint">
              "reject" means the metric stays significant after correction at alpha ={' '}
              {result.alpha}. Bonferroni controls the family-wise error rate; Benjamini–Hochberg
              controls the false-discovery rate.
            </p>
          </div>

          {chartData.length > 0 && (
            <ChartCard
              title="Adjusted p-values by method"
              note="Lower is more significant. The dashed line marks alpha."
              height={340}
            >
              <BarChartView
                data={chartData}
                xKey="name"
                rotateXTicks
                xLabel="Metric"
                yLabel="Adjusted p-value"
                valueFormatter={(v) => fmtNum(v, 5)}
                referenceLines={[
                  { y: result.alpha, label: `alpha = ${result.alpha}`, color: COLORS.red },
                ]}
                bars={[
                  { key: 'original', name: 'Original', color: COLORS.slate },
                  ...methodKeys.map((key) => ({
                    key,
                    name: key,
                    color: METHOD_COLORS[key] || COLORS.indigo,
                  })),
                ]}
              />
            </ChartCard>
          )}
        </>
      )}
    </div>
  )
}
