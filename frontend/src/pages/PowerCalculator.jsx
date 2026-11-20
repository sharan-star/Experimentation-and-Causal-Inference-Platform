import { useState } from 'react'
import { apiPost } from '../api/client.js'
import { fmtNum, fmtPct } from '../lib/format.js'
import StatCard from '../components/StatCard.jsx'
import ResultTable from '../components/ResultTable.jsx'
import Loading from '../components/Loading.jsx'
import ErrorBanner from '../components/ErrorBanner.jsx'
import { ChartCard, LineChartView, COLORS } from '../components/charts.jsx'

const LIFT_GRID = Array.from({ length: 30 }, (_, i) => (i + 1) / 100) // 1%..30%
const D_GRID = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0]

export default function PowerCalculator() {
  const [metricType, setMetricType] = useState('proportion')
  const [pControl, setPControl] = useState('0.10')
  const [relativeLift, setRelativeLift] = useState('10') // percent
  const [cohensD, setCohensD] = useState('0.2')
  const [alpha, setAlpha] = useState('0.05')
  const [power, setPower] = useState('0.80')
  const [ratio, setRatio] = useState('1.0')

  const [result, setResult] = useState(null)
  const [whatIf, setWhatIf] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const base = () => ({
    alpha: Number(alpha),
    power: Number(power),
    ratio: Number(ratio),
  })

  function sampleSizeRequest() {
    if (metricType === 'proportion') {
      return {
        metric_type: 'proportion',
        p_control: Number(pControl),
        relative_lift: Number(relativeLift) / 100,
        ...base(),
      }
    }
    return {
      metric_type: 'continuous',
      cohens_d: Number(cohensD),
      ...base(),
    }
  }

  async function computeWhatIf() {
    if (metricType === 'proportion') {
      const results = await Promise.all(
        LIFT_GRID.map((lift) =>
          apiPost('/power/sample-size', {
            metric_type: 'proportion',
            p_control: Number(pControl),
            relative_lift: lift,
            ...base(),
          }),
        ),
      )
      return LIFT_GRID.map((lift, i) => ({
        x: Number((lift * 100).toFixed(1)),
        n_per_arm: results[i]?.n_control,
        n_total: results[i]?.n_total,
      }))
    }
    const results = await Promise.all(
      D_GRID.map((d) =>
        apiPost('/power/sample-size', {
          metric_type: 'continuous',
          cohens_d: d,
          ...base(),
        }),
      ),
    )
    return D_GRID.map((d, i) => ({
      x: d,
      n_per_arm: results[i]?.n_control,
      n_total: results[i]?.n_total,
    }))
  }

  async function run() {
    setLoading(true)
    setError('')
    setResult(null)
    setWhatIf(null)
    try {
      const [res, series] = await Promise.all([
        apiPost('/power/sample-size', sampleSizeRequest()),
        computeWhatIf(),
      ])
      setResult(res)
      setWhatIf(series)
    } catch (e) {
      setError(e.message || String(e))
    } finally {
      setLoading(false)
    }
  }

  const effectLabel = metricType === 'proportion' ? "Cohen's h" : "Cohen's d"
  const effectValue =
    metricType === 'proportion' ? result?.cohens_h : result?.cohens_d
  const xKey = 'x'

  const rows = result
    ? [
        { label: 'Test', value: result.method },
        metricType === 'proportion'
          ? { label: 'Control rate (p₁)', value: fmtPct(result.p_control, 2) }
          : null,
        metricType === 'proportion'
          ? { label: 'Treatment rate (p₂)', value: fmtPct(result.p_treatment, 2) }
          : null,
        metricType === 'proportion'
          ? { label: 'Absolute lift', value: fmtNum(result.absolute_lift, 4) }
          : null,
        metricType === 'proportion'
          ? { label: 'Relative lift', value: fmtPct(result.relative_lift, 2) }
          : null,
        { label: effectLabel, value: fmtNum(effectValue, 4) },
        { label: 'Alpha (significance level)', value: fmtNum(result.alpha, 4) },
        { label: 'Target power (1 − β)', value: fmtNum(result.power, 4) },
        { label: 'Allocation ratio', value: fmtNum(ratio, 4) },
        { label: 'Required per control arm', value: fmtNum(result.n_control, 8) },
        { label: 'Required per treatment arm', value: fmtNum(result.n_treatment, 8) },
        { label: 'Total required sample', value: fmtNum(result.n_total, 8) },
      ].filter(Boolean)
    : []

  return (
    <div className="stack">
      <div className="card">
        <div className="card-header">
          <span className="card-title">Design inputs</span>
        </div>

        <div className="tabs" style={{ marginBottom: 18 }}>
          <button
            type="button"
            className={`tab${metricType === 'proportion' ? ' active' : ''}`}
            onClick={() => setMetricType('proportion')}
          >
            Proportion (conversion)
          </button>
          <button
            type="button"
            className={`tab${metricType === 'continuous' ? ' active' : ''}`}
            onClick={() => setMetricType('continuous')}
          >
            Continuous (mean)
          </button>
        </div>

        <div className="grid grid-3">
          {metricType === 'proportion' ? (
            <>
              <label className="field">
                <span className="field-label">Baseline rate (control)</span>
                <input
                  className="input"
                  type="number"
                  step="0.01"
                  value={pControl}
                  onChange={(e) => setPControl(e.target.value)}
                />
                <span className="field-hint">e.g. 0.10 for a 10% conversion rate</span>
              </label>
              <label className="field">
                <span className="field-label">Relative lift to detect (%)</span>
                <input
                  className="input"
                  type="number"
                  step="1"
                  value={relativeLift}
                  onChange={(e) => setRelativeLift(e.target.value)}
                />
                <span className="field-hint">e.g. 10 for a +10% relative improvement</span>
              </label>
            </>
          ) : (
            <label className="field">
              <span className="field-label">Cohen's d (effect size)</span>
              <input
                className="input"
                type="number"
                step="0.05"
                value={cohensD}
                onChange={(e) => setCohensD(e.target.value)}
              />
              <span className="field-hint">0.2 = small, 0.5 = medium, 0.8 = large</span>
            </label>
          )}
          <label className="field">
            <span className="field-label">Alpha (type-I error)</span>
            <input
              className="input"
              type="number"
              step="0.01"
              value={alpha}
              onChange={(e) => setAlpha(e.target.value)}
            />
          </label>
          <label className="field">
            <span className="field-label">Target power (1 − β)</span>
            <input
              className="input"
              type="number"
              step="0.05"
              value={power}
              onChange={(e) => setPower(e.target.value)}
            />
          </label>
          <label className="field">
            <span className="field-label">Allocation ratio</span>
            <input
              className="input"
              type="number"
              step="0.1"
              value={ratio}
              onChange={(e) => setRatio(e.target.value)}
            />
            <span className="field-hint">treatment / control (1.0 = balanced)</span>
          </label>
        </div>

        <div className="btn-row" style={{ marginTop: 6 }}>
          <button type="button" className="btn btn-primary" onClick={run} disabled={loading}>
            {loading ? 'Calculating…' : 'Calculate sample size'}
          </button>
        </div>

        <ErrorBanner message={error} onClose={() => setError('')} />
        {loading && <Loading label="Computing sample size and what-if curve…" />}
      </div>

      {result && (
        <>
          <div className="grid grid-4">
            <StatCard
              label="Per control arm"
              value={fmtNum(result.n_control, 8)}
              hint="users in the control group"
            />
            <StatCard
              label="Per treatment arm"
              value={fmtNum(result.n_treatment, 8)}
              hint={Number(ratio) === 1 ? 'balanced with control' : `ratio ${ratio}`}
            />
            <StatCard
              label="Total sample size"
              value={fmtNum(result.n_total, 8)}
              tone="green"
              hint="across both arms"
            />
            <StatCard
              label={effectLabel}
              value={fmtNum(effectValue, 4)}
              hint="standardised effect size"
            />
          </div>

          <div className="grid grid-2" style={{ alignItems: 'start' }}>
            <div className="card mb-0">
              <div className="card-header">
                <span className="card-title">Full result</span>
              </div>
              <ResultTable rows={rows} />
            </div>

            {whatIf && whatIf.length > 0 && (
              <ChartCard
                title="What-if: required sample size vs. effect"
                note={
                  metricType === 'proportion'
                    ? `Required sample size as the relative lift varies from 1% to 30% (baseline ${fmtPct(Number(pControl), 2)}, power ${power}).`
                    : `Required sample size as Cohen's d varies (power ${power}).`
                }
                height={320}
              >
                <LineChartView
                  data={whatIf}
                  xKey={xKey}
                  xLabel={metricType === 'proportion' ? 'Relative lift (%)' : "Cohen's d"}
                  yLabel="Sample size"
                  xTickFormatter={(v) => (metricType === 'proportion' ? `${v}%` : v)}
                  lines={[
                    {
                      key: 'n_total',
                      name: 'Total',
                      color: COLORS.indigo,
                      area: true,
                      strokeWidth: 2.5,
                    },
                    { key: 'n_per_arm', name: 'Per arm', color: COLORS.amber, strokeWidth: 2 },
                  ]}
                />
              </ChartCard>
            )}
          </div>
        </>
      )}
    </div>
  )
}
