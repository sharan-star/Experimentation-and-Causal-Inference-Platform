import { useCallback, useEffect, useRef, useState } from 'react'
import { apiUploadCsv, getDataset, listDatasets, simulateDataset } from '../api/client.js'
import { fmtNum } from '../lib/format.js'
import Loading from './Loading.jsx'
import ErrorBanner from './ErrorBanner.jsx'

const DEFAULT_SIMULATE = {
  kind: 'binary',
  n_a: 5000,
  n_b: 5000,
  p_a: 0.1,
  relative_lift: 0.1,
  mean_a: 10,
  std: 5,
  seed: 42,
}

const KIND_LABELS = {
  binary: 'Binary (conversion)',
  continuous: 'Continuous',
  observational: 'Observational (confounded)',
  sequential: 'Sequential stream',
  multimetric: 'Multi-metric',
}

const SOURCE_LABELS = {
  simulate: 'Simulate',
  dataset: 'Load dataset',
  upload: 'Upload CSV',
}

function formatCell(value) {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'number') return fmtNum(value, 6)
  return String(value)
}

function NumericField({ label, value, onChange, step = 'any', hint }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      <input
        className="input"
        type="number"
        step={step}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  )
}

function PreviewTable({ columns, preview }) {
  if (!columns?.length || !preview?.length) return null
  return (
    <div className="table-scroll" style={{ marginTop: 14 }}>
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {preview.slice(0, 10).map((row, i) => (
            <tr key={i}>
              {columns.map((c) => (
                <td key={c}>{formatCell(row[c])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/**
 * Reusable data-source picker. Loads a preview and reports a normalized
 * payload via {@link onLoaded}:
 *   { dataSource, columns, dtypes, n_rows, preview, sourceType }
 * where `dataSource` is exactly what the analysis endpoints expect.
 */
export default function DataSourcePanel({
  allowedSources = ['simulate', 'dataset', 'upload'],
  simulateKinds = ['binary', 'continuous'],
  defaultDataset = '',
  defaultSimulate = null,
  onLoaded,
  showPreview = true,
  title = 'Data source',
}) {
  const [sourceType, setSourceType] = useState(allowedSources[0])
  const [datasets, setDatasets] = useState([])
  const [datasetName, setDatasetName] = useState(defaultDataset)
  const [sim, setSim] = useState({ ...DEFAULT_SIMULATE, ...(defaultSimulate || {}) })
  const [fileName, setFileName] = useState('')
  const [info, setInfo] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const onLoadedRef = useRef(onLoaded)
  useEffect(() => {
    onLoadedRef.current = onLoaded
  }, [onLoaded])

  const emit = useCallback((payload) => {
    onLoadedRef.current?.(payload)
  }, [])

  // Fetch the dataset catalogue once when the "load dataset" tab is available.
  useEffect(() => {
    if (!allowedSources.includes('dataset')) return undefined
    let cancelled = false
    listDatasets()
      .then((data) => {
        if (!cancelled) setDatasets(data?.datasets || [])
      })
      .catch(() => {
        /* catalogue is optional; the select just stays empty */
      })
    return () => {
      cancelled = true
    }
  }, [allowedSources])

  const loadDataset = useCallback(
    async (name) => {
      if (!name) return
      setLoading(true)
      setError('')
      try {
        const data = await getDataset(name)
        const next = {
          columns: data.columns,
          dtypes: data.dtypes,
          n_rows: data.n_rows,
          preview: data.preview,
        }
        setInfo(next)
        emit({ dataSource: { source: 'dataset', name }, ...next, sourceType: 'dataset' })
      } catch (e) {
        setInfo(null)
        setError(e.message || String(e))
      } finally {
        setLoading(false)
      }
    },
    [emit],
  )

  const loadSimulate = useCallback(
    async (spec) => {
      const payload = spec || sim
      setLoading(true)
      setError('')
      try {
        const data = await simulateDataset(payload)
        const next = {
          columns: data.columns,
          dtypes: data.dtypes,
          n_rows: data.n_rows,
          preview: data.preview,
        }
        setInfo(next)
        emit({ dataSource: { source: 'simulate', simulate: payload }, ...next, sourceType: 'simulate' })
      } catch (e) {
        setInfo(null)
        setError(e.message || String(e))
      } finally {
        setLoading(false)
      }
    },
    [emit, sim],
  )

  const loadUpload = useCallback(
    async (file) => {
      setLoading(true)
      setError('')
      try {
        const data = await apiUploadCsv(file)
        setFileName(data.filename || file.name)
        const next = {
          columns: data.columns,
          dtypes: data.dtypes,
          n_rows: data.n_rows,
          preview: data.preview,
        }
        setInfo(next)
        emit({ dataSource: { source: 'upload', upload_id: data.upload_id }, ...next, sourceType: 'upload' })
      } catch (e) {
        setInfo(null)
        setError(e.message || String(e))
      } finally {
        setLoading(false)
      }
    },
    [emit],
  )

  // Auto-load when the source tab or the selected dataset changes.
  useEffect(() => {
    if (sourceType === 'dataset') loadDataset(datasetName)
    else if (sourceType === 'simulate') loadSimulate(sim)
    else if (sourceType === 'upload') {
      setInfo(null)
      setFileName('')
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sourceType, datasetName])

  const updateSim = (key, value) =>
    setSim((prev) => ({ ...prev, [key]: key === 'kind' ? value : Number(value) }))

  const showTabs = allowedSources.length > 1
  const kind = sim.kind

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">{title}</span>
        {info && (
          <span className="meta-line">
            <span>
              <strong>{fmtNum(info.n_rows, 6)}</strong> rows
            </span>
            <span>
              <strong>{info.columns?.length || 0}</strong> columns
            </span>
          </span>
        )}
      </div>

      {showTabs && (
        <div className="tabs" style={{ marginBottom: 18 }}>
          {allowedSources.map((src) => (
            <button
              key={src}
              type="button"
              className={`tab${sourceType === src ? ' active' : ''}`}
              onClick={() => setSourceType(src)}
            >
              {SOURCE_LABELS[src] || src}
            </button>
          ))}
        </div>
      )}

      {sourceType === 'simulate' && (
        <>
          <div className="grid grid-3">
            <label className="field">
              <span className="field-label">Data generating process</span>
              <select
                className="input"
                value={kind}
                onChange={(e) => updateSim('kind', e.target.value)}
              >
                {simulateKinds.map((k) => (
                  <option key={k} value={k}>
                    {KIND_LABELS[k] || k}
                  </option>
                ))}
              </select>
            </label>
            {(kind === 'binary' || kind === 'continuous' || kind === 'sequential') && (
              <NumericField
                label={kind === 'observational' ? 'N' : 'N (arm A / control)'}
                value={sim.n_a}
                onChange={(v) => updateSim('n_a', v)}
                step="1"
              />
            )}
            {kind === 'observational' && (
              <NumericField label="N" value={sim.n_a} onChange={(v) => updateSim('n_a', v)} step="1" />
            )}
            {(kind === 'binary' || kind === 'continuous') && (
              <NumericField
                label="N (arm B / treatment)"
                value={sim.n_b}
                onChange={(v) => updateSim('n_b', v)}
                step="1"
              />
            )}
          </div>

          <div className="grid grid-3">
            {(kind === 'binary' || kind === 'sequential') && (
              <NumericField
                label="Baseline rate p (control)"
                value={sim.p_a}
                onChange={(v) => updateSim('p_a', v)}
                hint="e.g. 0.10 for 10% conversion"
              />
            )}
            {kind === 'continuous' && (
              <NumericField
                label="Control mean"
                value={sim.mean_a}
                onChange={(v) => updateSim('mean_a', v)}
              />
            )}
            {kind !== 'observational' && (
              <NumericField
                label="Relative lift"
                value={sim.relative_lift}
                onChange={(v) => updateSim('relative_lift', v)}
                hint="e.g. 0.10 for +10%"
              />
            )}
            {kind === 'continuous' && (
              <NumericField label="Std. deviation" value={sim.std} onChange={(v) => updateSim('std', v)} />
            )}
            <NumericField label="Seed" value={sim.seed} onChange={(v) => updateSim('seed', v)} step="1" />
          </div>

          <div className="btn-row" style={{ marginTop: 4 }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => loadSimulate(sim)}
              disabled={loading}
            >
              Preview simulated data
            </button>
          </div>
        </>
      )}

      {sourceType === 'dataset' && (
        <>
          <label className="field">
            <span className="field-label">Bundled dataset</span>
            <select
              className="input"
              value={datasetName}
              onChange={(e) => setDatasetName(e.target.value)}
            >
              <option value="">— select a dataset —</option>
              {datasets.map((d) => (
                <option key={d.name} value={d.name}>
                  {d.name} — {d.analysis}
                </option>
              ))}
            </select>
          </label>
          {datasets.find((d) => d.name === datasetName)?.description && (
            <p className="field-hint" style={{ marginTop: -6 }}>
              {datasets.find((d) => d.name === datasetName).description}
            </p>
          )}
        </>
      )}

      {sourceType === 'upload' && (
        <label className="field">
          <span className="field-label">CSV file</span>
          <input
            className="input"
            type="file"
            accept=".csv,text/csv"
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) loadUpload(file)
            }}
          />
          {fileName && <span className="field-hint">Loaded: {fileName}</span>}
        </label>
      )}

      <ErrorBanner message={error} onClose={() => setError('')} />
      {loading && <Loading label="Loading data…" />}

      {showPreview && !loading && info && (
        <PreviewTable columns={info.columns} preview={info.preview} />
      )}
    </div>
  )
}
