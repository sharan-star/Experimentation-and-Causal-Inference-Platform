import {
  ResponsiveContainer,
  BarChart,
  Bar,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from 'recharts'
import { fmtNum } from '../lib/format.js'

export const COLORS = {
  control: '#94a3b8',
  treatment: '#4f46e5',
  indigo: '#4f46e5',
  indigoLight: '#818cf8',
  amber: '#d97706',
  green: '#059669',
  red: '#dc2626',
  slate: '#64748b',
  teal: '#0d9488',
  violet: '#7c3aed',
}

const AXIS_TICK = { fontSize: 11, fill: '#64748b' }
const GRID_STROKE = '#e2e8f0'

export function ChartCard({ title, note, height = 300, children }) {
  return (
    <div className="chart-card">
      {title && <div className="chart-title">{title}</div>}
      {note && <div className="chart-note">{note}</div>}
      <div style={{ width: '100%', height }}>
        <ResponsiveContainer width="100%" height="100%">
          {children}
        </ResponsiveContainer>
      </div>
    </div>
  )
}

function defaultFormatter(value) {
  return fmtNum(value, 4)
}

/**
 * Grouped / simple bar chart.
 * bars: [{ key, name, color, radius }]
 */
export function BarChartView({
  data,
  xKey = 'name',
  bars,
  xLabel,
  yLabel,
  valueFormatter = defaultFormatter,
  hideLegend = false,
  xTickFormatter,
  rotateXTicks = false,
  xInterval = 0,
  referenceLines = [],
}) {
  return (
    <BarChart data={data} margin={{ top: 8, right: 16, left: 4, bottom: rotateXTicks ? 40 : 8 }}>
      <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} vertical={false} />
      <XAxis
        dataKey={xKey}
        tick={AXIS_TICK}
        interval={xInterval}
        angle={rotateXTicks ? -35 : 0}
        textAnchor={rotateXTicks ? 'end' : 'middle'}
        height={rotateXTicks ? 60 : 30}
        label={xLabel ? { value: xLabel, position: 'insideBottom', offset: -2, fontSize: 11, fill: '#64748b' } : undefined}
        tickFormatter={xTickFormatter}
      />
      <YAxis tick={AXIS_TICK} label={yLabel ? { value: yLabel, angle: -90, position: 'insideLeft', fontSize: 11, fill: '#64748b' } : undefined} />
      <Tooltip formatter={(v) => valueFormatter(v)} />
      {!hideLegend && <Legend wrapperStyle={{ fontSize: 12 }} />}
      {referenceLines.map((rl, i) => (
        <ReferenceLine
          key={i}
          y={rl.y}
          stroke={rl.color || COLORS.red}
          strokeDasharray="5 4"
          label={{ value: rl.label, fontSize: 11, fill: rl.color || COLORS.red, position: 'insideTopRight' }}
        />
      ))}
      {bars.map((bar) => (
        <Bar
          key={bar.key}
          dataKey={bar.key}
          name={bar.name || bar.key}
          fill={bar.color || COLORS.indigo}
          radius={bar.radius ?? [4, 4, 0, 0]}
        />
      ))}
    </BarChart>
  )
}

/**
 * Line / area chart.
 * lines: [{ key, name, color, dash, area, strokeWidth, dot }]
 */
export function LineChartView({
  data,
  xKey = 'x',
  lines,
  xLabel,
  yLabel,
  valueFormatter = defaultFormatter,
  referenceLines = [],
  xTickFormatter,
}) {
  return (
    <ComposedChart data={data} margin={{ top: 8, right: 16, left: 4, bottom: 8 }}>
      <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} />
      <XAxis
        dataKey={xKey}
        tick={AXIS_TICK}
        tickFormatter={xTickFormatter}
        label={xLabel ? { value: xLabel, position: 'insideBottom', offset: -4, fontSize: 11, fill: '#64748b' } : undefined}
      />
      <YAxis tick={AXIS_TICK} label={yLabel ? { value: yLabel, angle: -90, position: 'insideLeft', fontSize: 11, fill: '#64748b' } : undefined} />
      <Tooltip formatter={(v) => valueFormatter(v)} />
      <Legend wrapperStyle={{ fontSize: 12 }} />
      {referenceLines.map((rl, i) => (
        <ReferenceLine
          key={i}
          y={rl.y}
          stroke={rl.color || COLORS.red}
          strokeDasharray="5 4"
          label={{ value: rl.label, fontSize: 11, fill: rl.color || COLORS.red, position: 'insideTopRight' }}
        />
      ))}
      {lines.map((line) =>
        line.area ? (
          <Area
            key={line.key}
            type="monotone"
            dataKey={line.key}
            name={line.name || line.key}
            stroke={line.color || COLORS.indigo}
            fill={line.color || COLORS.indigo}
            fillOpacity={0.15}
            strokeWidth={line.strokeWidth || 2}
            dot={false}
          />
        ) : (
          <Line
            key={line.key}
            type="monotone"
            dataKey={line.key}
            name={line.name || line.key}
            stroke={line.color || COLORS.indigo}
            strokeWidth={line.strokeWidth || 2}
            strokeDasharray={line.dash}
            dot={line.dot ?? false}
            connectNulls
          />
        ),
      )}
    </ComposedChart>
  )
}
