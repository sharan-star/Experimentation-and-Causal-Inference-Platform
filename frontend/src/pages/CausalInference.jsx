import { useEffect, useState } from 'react'
import { apiPost } from '../api/client.js'
import { fmtNum, fmtP, fmtPct, fmtSigned, uniqueValues } from '../lib/format.js'
import DataSourcePanel from '../components/DataSourcePanel.jsx'
import ColumnSelect from '../components/ColumnSelect.jsx'
import StatCard from '../components/StatCard.jsx'
import ResultTable from '../components/ResultTable.jsx'
import ConclusionCallout from '../components/ConclusionCallout.jsx'
import Loading from '../components/Loading.jsx'
import ErrorBanner from '../components/ErrorBanner.jsx'
import { BarChartView, LineChartView, ChartCard, COLORS } from '../components/charts.jsx'

const METHOD_CONFIG = {
  propensity: {
    label: 'Propensity Score Matching',
    defaultDataset: 'lalonde',
    defaults: {
      treatment_column: 'treat',
      outcome_column: 're78',
      covariates: ['age', 'education', 'black', 'hispanic', 'married', 'nodegree', 're74', 're75'],
      caliper: 0.1,
    },
  },
  did: {
    label: 'Difference-in-Differences',
    defaultDataset: 'card_krueger',
    defaults: {
      outcome_column: 'fte_employment',
      treated_column: 'treated',
      post_column: 'post',
    },
  },
  synthetic: {
    label: 'Synthetic Control',
    defaultDataset: 'prop99',
    defaults: {
      unit_column: 'state',
      time_column: 'year',
      outcome_column: 'cigsales',
      treated_unit: 'California',
      treatment_time: 1989,
    },
  },
  uplift: {
    label: 'Uplift (CATE)',
    defaultDataset: 'hillstrom',
    defaults: {
      treatment_column: 'segment',
      outcome_column: 'visit',
      features: ['recency', 'history', 'mens', 'womens', 'newbie'],
      learner: 'causal_forest',
      n_estimators: 200,
      seed: 42,
    },
  },
}

const METHODS = Object.entries(METHOD_CONFIG).map(([id, cfg]) => ({ id, label: cfg.label }))

function signTone(x) {
  if (x === null || x === undefined || Number.isNaN(x)) return 'amber'
  if (x > 0) return 'green'
  if (x < 0) return 'red'
  return 'amber'
}

function MultiColumnSelect({ label, columns, selected, onChange }) {
  const toggle = (col) => {
    const set = new Set(selected || [])
    if (set.has(col)) set.delete(col)
    else set.add(col)
    onChange(Array.from(set))
  }
  return (
    <div className="field">
      <span className="field-label">{label}</span>
      <div className="checkbox-list">
        {columns.map((col) => (
          <label key={col} className="checkbox-item">
            <input
              type="checkbox"
              checked={(selected || []).includes(col)}
              onChange={() => toggle(col)}
            />
            {col}
          </label>
        ))}
      </div>
    </div>
  )
}

export default function CausalInference() {
  const [method, setMethod] = useState('propensity')
  const [data, setData] = useState(null)
  const [form, setForm] = useState({ ...METHOD_CONFIG.propensity.defaults })
  const [alpha, setAlpha] = useState('0.05')

  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    setData(null)
    setResult(null)
    setError('')
    setAlpha('0.05')
    setForm({ ...METHOD_CONFIG[method].defaults })
  }, [method])

  function handleDataLoaded(payload) {
    setResult(null)
    setError('')
    setData(payload)
    const cols = payload.columns || []
    const cfg = METHOD_CONFIG[method]
    const next = { ...cfg.defaults }
    if (next.covariates) next.covariates = next.covariates.filter((c) => cols.includes(c))
    if (next.features) next.features = next.features.filter((c) => cols.includes(c))
    if ('treated_unit' in next) {
      const units = uniqueValues(payload.preview, next.unit_column).map(String)
      if (units.length && !units.includes(String(next.treated_unit))) {
        next.treated_unit = units[0]
      }
    }
    setForm(next)
  }

  const setField = (key, value) => setForm((prev) => ({ ...prev, [key]: value }))

  function buildBody() {
    const base = { data: data.dataSource, alpha: Number(alpha) }
    if (method === 'propensity') {
      return {
        path: '/causal/propensity',
        body: {
          ...base,
          treatment_column: form.treatment_column,
          outcome_column: form.outcome_column,
          covariates: form.covariates || [],
          caliper: Number(form.caliper),
          use_dowhy: false,
        },
      }
    }
    if (method === 'did') {
      return {
        path: '/causal/did',
        body: {
          ...base,
          outcome_column: form.outcome_column,
          treated_column: form.treated_column,
          post_column: form.post_column,
        },
      }
    }
    if (method === 'synthetic') {
      return {
        path: '/causal/synthetic-control',
        body: {
          ...base,
          unit_column: form.unit_column,
          time_column: form.time_column,
          outcome_column: form.outcome_column,
          treated_unit: form.treated_unit,
          treatment_time: Number(form.treatment_time),
        },
      }
    }
    return {
      path: '/causal/uplift',
      body: {
        ...base,
        treatment_column: form.treatment_column,
        outcome_column: form.outcome_column,
        features: form.features || [],
        learner: form.learner,
        n_estimators: Number(form.n_estimators),
        seed: Number(form.seed),
      },
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
      const { path, body } = buildBody()
      const res = await apiPost(path, body)
      setResult(res)
    } catch (e) {
      setError(e.message || String(e))
    } finally {
      setLoading(false)
    }
  }

  const columns = data?.columns || []
  const unitValues = uniqueValues(data?.preview, form.unit_column).map(String)

  return (
    <div className="stack">
      <div className="card">
        <div className="card-header">
          <span className="card-title">Causal method</span>
        </div>
        <div className="tabs">
          {METHODS.map((m) => (
            <button
              key={m.id}
              type="button"
              className={`tab${method === m.id ? ' active' : ''}`}
              onClick={() => setMethod(m.id)}
            >
              {m.label}
            </button>
          ))}
        </div>
        <p className="field-hint" style={{ marginTop: 12 }}>
          {method === 'propensity' &&
            'Estimate the treatment effect by matching treated and control units with similar propensity scores, reporting covariate balance before and after matching.'}
          {method === 'did' &&
            'Compare the change over time in a treated group against a control group (two-group, two-period difference-in-differences).'}
          {method === 'synthetic' &&
            'Build a weighted combination of untreated "donor" units that tracks the treated unit in the pre-period, then read the post-period gap as the effect.'}
          {method === 'uplift' &&
            'Estimate heterogeneous treatment effects (CATE) and evaluate targeting with a Qini curve and AUUC.'}
        </p>
      </div>

      <DataSourcePanel
        key={method}
        title="Data source"
        allowedSources={['dataset', 'upload', 'simulate']}
        simulateKinds={['observational']}
        defaultDataset={METHOD_CONFIG[method].defaultDataset}
        onLoaded={handleDataLoaded}
      />

      {data && (
        <div className="card">
          <div className="card-header">
            <span className="card-title">Column mapping</span>
          </div>

          {method === 'propensity' && (
            <>
              <div className="grid grid-3">
                <ColumnSelect
                  label="Treatment column"
                  value={form.treatment_column}
                  options={columns}
                  onChange={(v) => setField('treatment_column', v)}
                />
                <ColumnSelect
                  label="Outcome column"
                  value={form.outcome_column}
                  options={columns}
                  onChange={(v) => setField('outcome_column', v)}
                />
                <label className="field">
                  <span className="field-label">Caliper</span>
                  <input
                    className="input"
                    type="number"
                    step="0.01"
                    value={form.caliper}
                    onChange={(e) => setField('caliper', e.target.value)}
                  />
                </label>
              </div>
              <MultiColumnSelect
                label="Covariates (confounders to balance)"
                columns={columns}
                selected={form.covariates}
                onChange={(v) => setField('covariates', v)}
              />
            </>
          )}

          {method === 'did' && (
            <div className="grid grid-3">
              <ColumnSelect
                label="Outcome column"
                value={form.outcome_column}
                options={columns}
                onChange={(v) => setField('outcome_column', v)}
              />
              <ColumnSelect
                label="Treated group column (0/1)"
                value={form.treated_column}
                options={columns}
                onChange={(v) => setField('treated_column', v)}
              />
              <ColumnSelect
                label="Post-period column (0/1)"
                value={form.post_column}
                options={columns}
                onChange={(v) => setField('post_column', v)}
              />
            </div>
          )}

          {method === 'synthetic' && (
            <div className="grid grid-3">
              <ColumnSelect
                label="Unit column"
                value={form.unit_column}
                options={columns}
                onChange={(v) => setField('unit_column', v)}
              />
              <ColumnSelect
                label="Time column"
                value={form.time_column}
                options={columns}
                onChange={(v) => setField('time_column', v)}
              />
              <ColumnSelect
                label="Outcome column"
                value={form.outcome_column}
                options={columns}
                onChange={(v) => setField('outcome_column', v)}
              />
              <label className="field">
                <span className="field-label">Treated unit</span>
                <select
                  className="input"
                  value={form.treated_unit}
                  onChange={(e) => setField('treated_unit', e.target.value)}
                >
                  {unitValues.length === 0 && <option value={form.treated_unit}>{form.treated_unit}</option>}
                  {unitValues.map((u) => (
                    <option key={u} value={u}>
                      {u}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span className="field-label">Treatment time</span>
                <input
                  className="input"
                  type="number"
                  step="1"
                  value={form.treatment_time}
                  onChange={(e) => setField('treatment_time', e.target.value)}
                />
              </label>
            </div>
          )}

          {method === 'uplift' && (
            <>
              <div className="grid grid-3">
                <ColumnSelect
                  label="Treatment column"
                  value={form.treatment_column}
                  options={columns}
                  onChange={(v) => setField('treatment_column', v)}
                />
                <ColumnSelect
                  label="Outcome column"
                  value={form.outcome_column}
                  options={columns}
                  onChange={(v) => setField('outcome_column', v)}
                />
                <label className="field">
                  <span className="field-label">Learner</span>
                  <select
                    className="input"
                    value={form.learner}
                    onChange={(e) => setField('learner', e.target.value)}
                  >
                    <option value="causal_forest">Causal forest (DML)</option>
                    <option value="t_learner">T-learner</option>
                  </select>
                </label>
                <label className="field">
                  <span className="field-label">Trees / estimators</span>
                  <input
                    className="input"
                    type="number"
                    step="50"
                    value={form.n_estimators}
                    onChange={(e) => setField('n_estimators', e.target.value)}
                  />
                </label>
                <label className="field">
                  <span className="field-label">Seed</span>
                  <input
                    className="input"
                    type="number"
                    step="1"
                    value={form.seed}
                    onChange={(e) => setField('seed', e.target.value)}
                  />
                </label>
              </div>
              <MultiColumnSelect
                label="Features (covariates used for the CATE model)"
                columns={columns}
                selected={form.features}
                onChange={(v) => setField('features', v)}
              />
            </>
          )}

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
          </div>

          <div className="btn-row">
            <button className="btn btn-primary" type="button" onClick={run} disabled={loading}>
              {loading ? 'Estimating…' : 'Estimate causal effect'}
            </button>
          </div>

          <ErrorBanner message={error} onClose={() => setError('')} />
          {loading && <Loading label="Estimating causal effect…" />}
        </div>
      )}

      {result && <CausalResult method={method} payload={result} />}
    </div>
  )
}

function CausalResult({ method, payload }) {
  if (method === 'propensity') return <PropensityResult payload={payload} />
  if (method === 'did') return <DidResult payload={payload} />
  if (method === 'synthetic') return <SyntheticResult payload={payload} />
  return <UpliftResult payload={payload} />
}

function PropensityResult({ payload }) {
  const res = payload.result || {}
  const smdBefore = res.balance_smd_before || {}
  const smdAfter = res.balance_smd_after || {}
  const covariates = Object.keys(smdBefore)
  const chartData = covariates.map((c) => ({
    cov: c,
    before: smdBefore[c],
    after: smdAfter[c],
  }))
  const tone = !res.balanced ? 'amber' : signTone(res.effect)

  const rows = [
    { label: 'Method', value: res.method },
    { label: 'Estimated effect (ATT)', value: fmtSigned(res.effect, 6) },
    { label: '95% CI', value: `[${fmtNum(res.ci?.[0], 6)}, ${fmtNum(res.ci?.[1], 6)}]` },
    { label: 'Naive (unadjusted) estimate', value: fmtSigned(res.naive_estimate, 6) },
    { label: 'Confounding bias', value: fmtSigned(res.confounding_bias, 6) },
    { label: 'Matched pairs', value: fmtNum(res.n_matched_pairs, 8) },
    { label: 'Max SMD before', value: fmtNum(res.max_smd_before, 4) },
    { label: 'Max SMD after', value: fmtNum(res.max_smd_after, 4) },
    { label: 'Balanced (max SMD < 0.1)', value: res.balanced ? 'Yes' : 'No' },
  ]

  return (
    <div className="stack">
      <ConclusionCallout conclusion={payload.conclusion} tone={tone} />
      <div className="grid grid-4">
        <StatCard label="Estimated effect (ATT)" value={fmtSigned(res.effect, 4)} tone={tone} hint="adjusted for confounding" />
        <StatCard label="Naive estimate" value={fmtSigned(res.naive_estimate, 4)} hint="raw group difference" />
        <StatCard label="Confounding bias" value={fmtSigned(res.confounding_bias, 4)} />
        <StatCard
          label="Max SMD after"
          value={fmtNum(res.max_smd_after, 4)}
          tone={res.balanced ? 'green' : 'amber'}
          hint={res.balanced ? 'balanced' : 'still imbalanced'}
        />
      </div>

      <div className="grid grid-2" style={{ alignItems: 'start' }}>
        <div className="card mb-0">
          <div className="card-header">
            <span className="card-title">Key numbers</span>
          </div>
          <ResultTable rows={rows} />
        </div>
        <ChartCard
          title="Covariate balance (standardised mean difference)"
          note="SMD before vs. after matching. Values below 0.1 are considered well balanced."
          height={320}
        >
          <BarChartView
            data={chartData}
            xKey="cov"
            rotateXTicks
            xLabel="Covariate"
            yLabel="|SMD|"
            valueFormatter={(v) => fmtNum(v, 4)}
            referenceLines={[{ y: 0.1, label: '0.1 (balanced)', color: COLORS.red }]}
            bars={[
              { key: 'before', name: 'Before matching', color: COLORS.control },
              { key: 'after', name: 'After matching', color: COLORS.indigo },
            ]}
          />
        </ChartCard>
      </div>
    </div>
  )
}

function DidResult({ payload }) {
  const res = payload.result || {}
  const cm = res.cell_means || {}
  const chartData = [
    { group: 'Control', pre: cm.control_pre, post: cm.control_post },
    { group: 'Treated', pre: cm.treated_pre, post: cm.treated_post },
  ]
  const tone = signTone(res.att)

  const rows = [
    { label: 'Method', value: res.method },
    { label: 'ATT (interaction)', value: fmtSigned(res.att, 6) },
    { label: '95% CI', value: `[${fmtNum(res.ci?.[0], 6)}, ${fmtNum(res.ci?.[1], 6)}]` },
    { label: 'p-value', value: fmtP(res.p_value) },
    { label: 'Naive estimate', value: fmtSigned(res.naive_estimate, 6) },
    { label: 'Observations', value: fmtNum(res.n_obs, 8) },
    { label: 'R²', value: fmtNum(res.r_squared, 4) },
  ]

  return (
    <div className="stack">
      <ConclusionCallout conclusion={payload.conclusion} tone={tone} />
      <div className="grid grid-4">
        <StatCard label="ATT" value={fmtSigned(res.att, 4)} tone={tone} hint="average treatment effect on treated" />
        <StatCard label="p-value" value={fmtP(res.p_value)} hint={`alpha = ${res.alpha}`} />
        <StatCard label="Naive estimate" value={fmtSigned(res.naive_estimate, 4)} hint="unadjusted DiD-in-means" />
        <StatCard label="Observations" value={fmtNum(res.n_obs, 8)} />
      </div>

      <div className="grid grid-2" style={{ alignItems: 'start' }}>
        <div className="card mb-0">
          <div className="card-header">
            <span className="card-title">Key numbers</span>
          </div>
          <ResultTable rows={rows} />
        </div>
        <ChartCard
          title="Cell means: pre vs. post"
          note="The difference in the change between groups is the difference-in-differences estimate."
          height={320}
        >
          <BarChartView
            data={chartData}
            xKey="group"
            xLabel="Group"
            yLabel="Mean outcome"
            valueFormatter={(v) => fmtNum(v, 6)}
            bars={[
              { key: 'pre', name: 'Pre period', color: COLORS.control },
              { key: 'post', name: 'Post period', color: COLORS.indigo },
            ]}
          />
        </ChartCard>
      </div>
    </div>
  )
}

function SyntheticResult({ payload }) {
  const res = payload.result || {}
  const time = res.time || []
  const chartData = time.map((t, i) => ({
    time: t,
    treated: res.treated?.[i],
    synthetic: res.synthetic?.[i],
  }))
  const tone = signTone(res.effect)

  const topWeights = (res.weights || []).slice(0, 8).map((w) => ({
    label: `Weight · ${w.unit}`,
    value: fmtNum(w.weight, 4),
  }))

  const rows = [
    { label: 'Method', value: res.method },
    { label: 'Treated unit', value: res.treated_unit },
    { label: 'Treatment time', value: fmtNum(res.treatment_time, 8) },
    { label: 'Estimated effect (ATT)', value: fmtSigned(res.effect, 6) },
    { label: 'Pre-period RMSE', value: fmtNum(res.pre_period_rmse, 6) },
    { label: 'Placebo p-value', value: fmtP(res.p_value) },
    { label: 'Donor units', value: fmtNum(res.n_donors, 8) },
    ...topWeights,
  ]

  return (
    <div className="stack">
      <ConclusionCallout conclusion={payload.conclusion} tone={tone} />
      <div className="grid grid-4">
        <StatCard label="Estimated effect (ATT)" value={fmtSigned(res.effect, 4)} tone={tone} hint="post-period average gap" />
        <StatCard label="Pre-period RMSE" value={fmtNum(res.pre_period_rmse, 4)} hint="lower = better pre-fit" />
        <StatCard label="Placebo p-value" value={fmtP(res.p_value)} hint={`alpha = ${res.alpha}`} />
        <StatCard label="Donor units" value={fmtNum(res.n_donors, 8)} />
      </div>

      <div className="grid grid-2" style={{ alignItems: 'start' }}>
        <div className="card mb-0">
          <div className="card-header">
            <span className="card-title">Key numbers & donor weights</span>
          </div>
          <ResultTable rows={rows} />
        </div>
        <ChartCard
          title="Treated vs. synthetic over time"
          note={`Actual treated unit vs. its synthetic counterfactual (treatment begins at ${res.treatment_time}).`}
          height={320}
        >
          <LineChartView
            data={chartData}
            xKey="time"
            xLabel="Time"
            yLabel="Outcome"
            valueFormatter={(v) => fmtNum(v, 6)}
            lines={[
              { key: 'treated', name: 'Treated', color: COLORS.indigo, strokeWidth: 2.5 },
              { key: 'synthetic', name: 'Synthetic', color: COLORS.amber, strokeWidth: 2, dash: '6 4' },
            ]}
          />
        </ChartCard>
      </div>
    </div>
  )
}

function UpliftResult({ payload }) {
  const res = payload.result || {}
  const qini = res.qini || {}
  const chartData = (qini.fraction || []).map((f, i) => ({
    fraction: f,
    qini: qini.qini?.[i],
    random: qini.random_baseline?.[i],
  }))
  const importance = Object.entries(res.feature_importance || {}).map(([feature, value]) => ({
    feature,
    importance: value,
  }))
  importance.sort((a, b) => b.importance - a.importance)
  const tone = signTone(res.ate)

  const rows = [
    { label: 'Method', value: res.method },
    { label: 'Engine', value: res.engine },
    { label: 'ATE', value: fmtSigned(res.ate, 6) },
    { label: 'Mean CATE', value: fmtSigned(res.cate_mean, 6) },
    { label: 'CATE std. dev.', value: fmtNum(res.cate_std, 6) },
    { label: 'Share with positive CATE', value: fmtPct(res.cate_positive_share, 1) },
    { label: 'AUUC', value: fmtNum(res.auuc, 6) },
    { label: 'Qini @ 10%', value: fmtNum(res.qini_at_10pct, 6) },
    { label: 'Qini @ 30%', value: fmtNum(res.qini_at_30pct, 6) },
  ]

  return (
    <div className="stack">
      <ConclusionCallout conclusion={payload.conclusion} tone={tone} />
      <div className="grid grid-4">
        <StatCard label="ATE" value={fmtSigned(res.ate, 4)} tone={tone} hint="average treatment effect" />
        <StatCard label="Mean CATE" value={fmtSigned(res.cate_mean, 4)} />
        <StatCard label="Positive CATE share" value={fmtPct(res.cate_positive_share, 1)} hint="users likely to benefit" />
        <StatCard label="AUUC" value={fmtNum(res.auuc, 4)} hint="area under the uplift curve" />
      </div>

      <div className="grid grid-2" style={{ alignItems: 'start' }}>
        <div className="card mb-0">
          <div className="card-header">
            <span className="card-title">Key numbers</span>
          </div>
          <ResultTable rows={rows} />
        </div>
        <ChartCard
          title="Qini curve"
          note="Cumulative uplift when targeting users in order of predicted effect, vs. random targeting."
          height={320}
        >
          <LineChartView
            data={chartData}
            xKey="fraction"
            xLabel="Fraction of population targeted"
            yLabel="Cumulative uplift"
            xTickFormatter={(v) => fmtNum(v, 2)}
            valueFormatter={(v) => fmtNum(v, 6)}
            lines={[
              { key: 'qini', name: 'Qini (model)', color: COLORS.indigo, strokeWidth: 2.5, area: true },
              { key: 'random', name: 'Random baseline', color: COLORS.slate, strokeWidth: 2, dash: '6 4' },
            ]}
          />
        </ChartCard>
      </div>

      {importance.length > 0 && (
        <ChartCard
          title="Feature importance"
          note="Which covariates drive the heterogeneity of the treatment effect."
          height={320}
        >
          <BarChartView
            data={importance}
            xKey="feature"
            rotateXTicks
            xLabel="Feature"
            yLabel="Importance"
            valueFormatter={(v) => fmtNum(v, 4)}
            hideLegend
            bars={[{ key: 'importance', name: 'Importance', color: COLORS.teal }]}
          />
        </ChartCard>
      )}
    </div>
  )
}
