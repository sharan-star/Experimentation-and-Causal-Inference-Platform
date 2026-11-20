import { useMemo, useRef, useState } from 'react'
import { apiPost } from '../api/client.js'
import {
  fmtNum,
  fmtP,
  fmtPct,
  fmtSigned,
  uniqueValues,
} from '../lib/format.js'
import DataSourcePanel from '../components/DataSourcePanel.jsx'
import ColumnSelect from '../components/ColumnSelect.jsx'
import StatCard from '../components/StatCard.jsx'
import ResultTable from '../components/ResultTable.jsx'
import ConclusionCallout from '../components/ConclusionCallout.jsx'
import Loading from '../components/Loading.jsx'
import ErrorBanner from '../components/ErrorBanner.jsx'
import { BarChartView, LineChartView, ChartCard, COLORS } from '../components/charts.jsx'

const METHODS = [
  { id: 'frequentist', label: 'Frequentist' },
  { id: 'bayesian', label: 'Bayesian' },
  { id: 'sequential', label: 'Sequential' },
]

const VARIANT_CANDIDATES = ['variant', 'version', 'segment', 'group', 'arm', 'treatment', 'test']
const METRIC_CANDIDATES = [
  'converted',
  'conversion',
  'visit',
  'retention_1',
  'click',
  'success',
  'y',
  'revenue',
]

function pickVariantColumn(columns) {
  return VARIANT_CANDIDATES.find((c) => columns.includes(c)) || columns[0] || ''
}

function pickMetricColumn(columns, variant) {
  const hit = METRIC_CANDIDATES.find((c) => columns.includes(c) && c !== variant)
  if (hit) return hit
  return columns.find((c) => c !== variant) || ''
}

function pickLabels(values) {
  const strs = values.map((v) => String(v))
  const control =
    strs.find((v) => /no e-?mail|control|gate_30|^a$|^0$|false/i.test(v)) ?? strs[0] ?? ''
  const treatment =
    strs.find(
      (v) => v !== control && /mens e-?mail|treatment|gate_40|^b$|^1$|true/i.test(v),
    ) ?? strs.find((v) => v !== control) ?? strs[1] ?? ''
  return { control, treatment }
}

export default function ABAnalysis() {
  const [data, setData] = useState(null)
  const [variantColumn, setVariantColumn] = useState('')
  const [metricColumn, setMetricColumn] = useState('')
  const [controlLabel, setControlLabel] = useState('')
  const [treatmentLabel, setTreatmentLabel] = useState('')
  const [metricType, setMetricType] = useState('proportion')
  const [method, setMethod] = useState('frequentist')
  const [alpha, setAlpha] = useState('0.05')
  const [nLooks, setNLooks] = useState('5')
  const [spending, setSpending] = useState('obrien-fleming')
  const [draws, setDraws] = useState('3000')
  const [seed, setSeed] = useState('42')

  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const columns = data?.columns || []
  const labelValues = useMemo(
    () => uniqueValues(data?.preview, variantColumn),
    [data, variantColumn],
  )

  function suggestType(col, preview) {
    if (!col) return 'proportion'
    const values = new Set()
    for (const row of preview || []) {
      const v = row?.[col]
      if (v === null || v === undefined) continue
      values.add(Number(v))
      if (values.size > 3) return 'continuous'
    }
    if (values.size === 0) return 'proportion'
    return [...values].every((v) => v === 0 || v === 1) ? 'proportion' : 'continuous'
  }

  function handleDataLoaded(payload) {
    setResult(null)
    setError('')
    const cols = payload.columns || []
    const variant = pickVariantColumn(cols)
    const metric = pickMetricColumn(cols, variant)
    const labels = pickLabels(uniqueValues(payload.preview, variant))
    setData(payload)
    setVariantColumn(variant)
    setMetricColumn(metric)
    setControlLabel(labels.control)
    setTreatmentLabel(labels.treatment)
    setMetricType(suggestType(metric, payload.preview))
  }

  function handleVariantChange(col) {
    setVariantColumn(col)
    const labels = pickLabels(uniqueValues(data?.preview, col))
    setControlLabel(labels.control)
    setTreatmentLabel(labels.treatment)
  }

  function handleMetricChange(col) {
    setMetricColumn(col)
    setMetricType(suggestType(col, data?.preview))
  }

  function buildRequest() {
    const metric_type = metricType === 'proportion' ? 'proportion' : 'continuous'
    const common = {
      metric_type,
      data: data.dataSource,
      variant_column: variantColumn,
      metric_column: metricColumn,
      control_label: controlLabel,
      treatment_label: treatmentLabel,
    }
    if (method === 'frequentist') return { path: '/analysis/frequentist', body: { ...common, alpha: Number(alpha) } }
    if (method === 'bayesian')
      return { path: '/analysis/bayesian', body: { ...common, draws: Number(draws), seed: Number(seed) } }
    return {
      path: '/analysis/sequential',
      body: { ...common, n_looks: Number(nLooks), spending, alpha: Number(alpha) },
    }
  }

  async function run() {
    if (!data) {
      setError('Load a data source first.')
      return
    }
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const { path, body } = buildRequest()
      const res = await apiPost(path, body)
      setResult(res)
    } catch (e) {
      setError(e.message || String(e))
    } finally {
      setLoading(false)
    }
  }

  // ------------------------------------------------------------------ render
  const canRun = Boolean(data && variantColumn && metricColumn && controlLabel && treatmentLabel)

  return (
    <div className="stack">
      <DataSourcePanel
        allowedSources={['simulate', 'dataset', 'upload']}
        simulateKinds={['binary', 'continuous']}
        onLoaded={handleDataLoaded}
        title="Experiment data"
      />

      {data && (
        <div className="card">
          <div className="card-header">
            <span className="card-title">Columns &amp; method</span>
          </div>
          <div className="grid grid-3">
            <ColumnSelect
              label="Variant / group column"
              value={variantColumn}
              options={columns}
              onChange={handleVariantChange}
            />
            <ColumnSelect
              label="Metric column"
              value={metricColumn}
              options={columns}
              onChange={handleMetricChange}
            />
            <label className="field">
              <span className="field-label">Metric type</span>
              <select
                className="input"
                value={metricType}
                onChange={(e) => setMetricType(e.target.value)}
              >
                <option value="proportion">Proportion / binary (conversion)</option>
                <option value="continuous">Continuous (mean)</option>
              </select>
            </label>
            <ColumnSelect
              label="Control label"
              value={controlLabel}
              options={labelValues.map(String)}
              onChange={setControlLabel}
            />
            <ColumnSelect
              label="Treatment label"
              value={treatmentLabel}
              options={labelValues.map(String)}
              onChange={setTreatmentLabel}
            />
            <label className="field">
              <span className="field-label">Method</span>
              <select className="input" value={method} onChange={(e) => setMethod(e.target.value)}>
                {METHODS.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="grid grid-3">
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
            {method === 'sequential' && (
              <>
                <label className="field">
                  <span className="field-label">Interim looks</span>
                  <input
                    className="input"
                    type="number"
                    step="1"
                    value={nLooks}
                    onChange={(e) => setNLooks(e.target.value)}
                  />
                </label>
                <label className="field">
                  <span className="field-label">Alpha-spending</span>
                  <select
                    className="input"
                    value={spending}
                    onChange={(e) => setSpending(e.target.value)}
                  >
                    <option value="obrien-fleming">O'Brien-Fleming</option>
                    <option value="pocock">Pocock</option>
                  </select>
                </label>
              </>
            )}
            {method === 'bayesian' && (
              <>
                <label className="field">
                  <span className="field-label">Posterior draws</span>
                  <input
                    className="input"
                    type="number"
                    step="500"
                    value={draws}
                    onChange={(e) => setDraws(e.target.value)}
                  />
                </label>
                <label className="field">
                  <span className="field-label">Seed</span>
                  <input
                    className="input"
                    type="number"
                    step="1"
                    value={seed}
                    onChange={(e) => setSeed(e.target.value)}
                  />
                </label>
              </>
            )}
          </div>

          <div className="btn-row">
            <button className="btn btn-primary" type="button" onClick={run} disabled={!canRun || loading}>
              {loading ? 'Running…' : `Run ${method} analysis`}
            </button>
          </div>

          <ErrorBanner message={error} onClose={() => setError('')} />
          {loading && <Loading label="Running analysis…" />}
        </div>
      )}

      {result && <ABResult method={method} payload={result} metricType={metricType} />}
    </div>
  )
}

function freqTone(res) {
  return res?.significant ? 'green' : 'amber'
}

function bayesTone(res) {
  if (res?.decision === 'ship_treatment') return 'green'
  if (res?.decision === 'keep_control') return 'red'
  return 'amber'
}

function seqTone(res) {
  return res?.final_decision === 'reject_null' ? 'green' : 'amber'
}

function ABResult({ method, payload, metricType }) {
  if (method === 'frequentist') return <FrequentistResult payload={payload} metricType={metricType} />
  if (method === 'bayesian') return <BayesianResult payload={payload} metricType={metricType} />
  return <SequentialResult payload={payload} />
}

function FrequentistResult({ payload, metricType }) {
  const res = payload.result || {}
  const dist = payload.distribution || {}
  const isBinary = res.test === 'two_proportion_ztest'

  const rows = [
    { label: 'Test', value: res.test },
    { label: 'Control N', value: fmtNum(res.n_control, 8) },
    { label: 'Treatment N', value: fmtNum(res.n_treatment, 8) },
    isBinary
      ? { label: 'Control rate', value: fmtPct(res.rate_control, 3) }
      : { label: 'Control mean', value: fmtNum(res.mean_control, 6) },
    isBinary
      ? { label: 'Treatment rate', value: fmtPct(res.rate_treatment, 3) }
      : { label: 'Treatment mean', value: fmtNum(res.mean_treatment, 6) },
    { label: 'Absolute lift', value: fmtSigned(res.absolute_lift, 5) },
    { label: 'Relative lift', value: res.relative_lift != null ? fmtPct(res.relative_lift, 2) : '—' },
    {
      label: '95% confidence interval',
      value: `[${fmtNum(res.ci_lower, 5)}, ${fmtNum(res.ci_upper, 5)}]`,
    },
    { label: 'p-value', value: fmtP(res.p_value) },
    isBinary
      ? { label: "Cohen's h", value: fmtNum(res.cohens_h, 4) }
      : { label: "Cohen's d", value: fmtNum(res.cohens_d, 4) },
    { label: 'Statistic', value: fmtNum(res.z_stat ?? res.t_stat, 4) },
    { label: 'Significant', value: res.significant ? `Yes (p < ${res.alpha})` : 'No' },
  ]

  return (
    <div className="stack">
      <ConclusionCallout conclusion={payload.conclusion} tone={freqTone(res)} />
      <div className="grid grid-4">
        <StatCard label="p-value" value={fmtP(res.p_value)} hint={`alpha = ${res.alpha}`} tone={res.significant ? 'green' : 'amber'} />
        <StatCard label="Absolute lift" value={fmtSigned(res.absolute_lift, 4)} hint="treatment − control" />
        <StatCard
          label="Relative lift"
          value={res.relative_lift != null ? fmtPct(res.relative_lift, 2) : '—'}
          hint="vs. control"
        />
        <StatCard label="Significant" value={res.significant ? 'Yes' : 'No'} tone={res.significant ? 'green' : 'slate'} />
      </div>

      <div className="grid grid-2" style={{ alignItems: 'start' }}>
        <div className="card mb-0">
          <div className="card-header">
            <span className="card-title">Key numbers</span>
          </div>
          <ResultTable rows={rows} />
        </div>
        {dist.type === 'histogram' ? (
          <ChartCard title="Distribution of the metric by arm" note="Overlaid histogram of the two arms." height={320}>
            <BarChartView
              data={(dist.bin_centers || []).map((center, i) => ({
                center: Number(center).toFixed(2),
                control: dist.control?.[i],
                treatment: dist.treatment?.[i],
              }))}
              xKey="center"
              xInterval={4}
              xLabel="Metric value"
              yLabel="Count"
              valueFormatter={(v) => fmtNum(v, 6)}
              bars={[
                { key: 'control', name: 'Control', color: COLORS.control },
                { key: 'treatment', name: 'Treatment', color: COLORS.treatment },
              ]}
            />
          </ChartCard>
        ) : (
          <ChartCard title="Success rate by arm" note="Binary metric comparison." height={320}>
            <BarChartView
              data={(dist.categories || []).map((cat, i) => ({
                name: cat,
                rate: dist.success_rate?.[i],
                counts: dist.counts?.[i],
              }))}
              xKey="name"
              yLabel="Success rate"
              valueFormatter={(v) => fmtPct(v, 3)}
              hideLegend
              bars={[{ key: 'rate', name: 'Success rate', color: COLORS.indigo }]}
            />
          </ChartCard>
        )}
      </div>
    </div>
  )
}

function BayesianResult({ payload }) {
  const res = payload.result || {}
  const hist = res.posterior_histogram || {}
  const edges = hist.edges || []
  const chartData = (hist.counts || []).map((count, i) => ({
    center: ((edges[i] + edges[i + 1]) / 2).toFixed(4),
    count,
  }))

  const rows = [
    { label: 'Method', value: res.method },
    { label: 'Engine', value: res.engine },
    { label: 'P(B beats A)', value: fmtPct(res.prob_treatment_better, 2) },
    { label: 'P(A beats B)', value: fmtPct(res.prob_control_better, 2) },
    { label: 'Posterior mean difference', value: fmtSigned(res.posterior_mean_diff, 6) },
    { label: 'Posterior std. dev.', value: fmtNum(res.posterior_std_diff, 6) },
    {
      label: '95% credible interval',
      value: `[${fmtNum(res.credible_interval?.[0], 6)}, ${fmtNum(res.credible_interval?.[1], 6)}]`,
    },
    { label: 'Credible level', value: fmtPct(res.credible_level, 0) },
    { label: 'Decision', value: res.decision },
    { label: 'Expected loss if shipping B', value: fmtNum(res.expected_loss_if_ship_treatment, 6) },
    { label: 'Relative lift (posterior mean)', value: fmtPct(res.relative_lift_posterior_mean, 2) },
  ]

  return (
    <div className="stack">
      <ConclusionCallout conclusion={payload.conclusion} tone={bayesTone(res)} />
      <div className="grid grid-4">
        <StatCard label="P(B beats A)" value={fmtPct(res.prob_treatment_better, 1)} tone={bayesTone(res)} hint="posterior probability" />
        <StatCard label="Posterior mean diff." value={fmtSigned(res.posterior_mean_diff, 5)} hint="treatment − control" />
        <StatCard
          label="95% credible interval"
          value={`[${fmtNum(res.credible_interval?.[0], 3)}, ${fmtNum(res.credible_interval?.[1], 3)}]`}
        />
        <StatCard label="Decision" value={String(res.decision || '—').replace(/_/g, ' ')} tone={bayesTone(res)} />
      </div>

      <div className="grid grid-2" style={{ alignItems: 'start' }}>
        <div className="card mb-0">
          <div className="card-header">
            <span className="card-title">Key numbers</span>
          </div>
          <ResultTable rows={rows} />
        </div>
        <ChartCard
          title="Posterior distribution of the difference"
          note="Histogram of posterior draws of (treatment − control)."
          height={320}
        >
          <BarChartView
            data={chartData}
            xKey="center"
            xInterval={4}
            xLabel="Difference"
            yLabel="Draws"
            valueFormatter={(v) => fmtNum(v, 6)}
            hideLegend
            bars={[{ key: 'count', name: 'Posterior draws', color: COLORS.violet }]}
          />
        </ChartCard>
      </div>
    </div>
  )
}

function SequentialResult({ payload }) {
  const res = payload.result || {}
  const looks = res.looks || []
  const chartData = looks.map((l) => ({
    n: l.n_per_arm,
    naive: l.naive_p_value,
    valid: l.always_valid_p_value,
    boundary: l.nominal_p_boundary,
  }))

  const last = looks[looks.length - 1]

  const rows = [
    { label: 'Spending function', value: res.spending },
    { label: 'Alpha', value: fmtNum(res.alpha, 4) },
    { label: 'Number of looks', value: fmtNum(looks.length, 6) },
    { label: 'Final decision', value: res.final_decision },
    ...looks.map((l) => ({
      label: `Look ${l.look} · n/arm ${fmtNum(l.n_per_arm, 8)}`,
      value: `naive p=${fmtP(l.naive_p_value)} · always-valid p=${fmtP(l.always_valid_p_value)} · boundary p<${fmtNum(
        l.nominal_p_boundary,
        4,
      )}`,
    })),
  ]

  return (
    <div className="stack">
      <ConclusionCallout conclusion={payload.conclusion} tone={seqTone(res)} />
      <div className="grid grid-4">
        <StatCard
          label="Final decision"
          value={res.final_decision === 'reject_null' ? 'Reject null' : 'Keep running'}
          tone={seqTone(res)}
        />
        <StatCard label="Looks" value={fmtNum(looks.length, 6)} hint={`spending: ${res.spending}`} />
        <StatCard
          label="Final naive p-value"
          value={fmtP(last?.naive_p_value)}
          hint={last ? `at ${fmtNum(last.n_per_arm, 8)} users/arm` : undefined}
        />
        <StatCard
          label="Final always-valid p"
          value={fmtP(last?.always_valid_p_value)}
          hint={`boundary p < ${fmtNum(last?.nominal_p_boundary, 4)}`}
        />
      </div>

      <div className="grid grid-2" style={{ alignItems: 'start' }}>
        <div className="card mb-0">
          <div className="card-header">
            <span className="card-title">Look-by-look results</span>
          </div>
          <ResultTable rows={rows} />
        </div>
        <ChartCard
          title="p-values vs. sample size (peek-safe)"
          note="Naive p-value, always-valid p-value and the alpha-spending boundary at each look."
          height={320}
        >
          <LineChartView
            data={chartData}
            xKey="n"
            xLabel="Users per arm"
            yLabel="p-value"
            xTickFormatter={(v) => fmtNum(v, 6)}
            valueFormatter={(v) => fmtP(v)}
            referenceLines={[{ y: res.alpha, label: `alpha = ${res.alpha}`, color: COLORS.slate }]}
            lines={[
              { key: 'naive', name: 'Naive p-value', color: COLORS.amber, strokeWidth: 2, dot: true },
              { key: 'valid', name: 'Always-valid p-value', color: COLORS.indigo, strokeWidth: 2.5, dot: true },
              { key: 'boundary', name: 'Nominal p boundary', color: COLORS.red, dash: '6 4', strokeWidth: 2 },
            ]}
          />
        </ChartCard>
      </div>
    </div>
  )
}
