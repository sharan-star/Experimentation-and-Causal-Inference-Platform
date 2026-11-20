// Small presentation helpers shared across pages.

export function isNil(x) {
  return x === null || x === undefined || (typeof x === 'number' && Number.isNaN(x))
}

/** Format a number with a fixed number of significant digits. */
export function fmtNum(x, digits = 4) {
  if (isNil(x)) return '—'
  const n = Number(x)
  if (!Number.isFinite(n)) return '—'
  if (n === 0) return '0'
  const abs = Math.abs(n)
  if (abs >= 1e6 || abs < 1e-4) return n.toExponential(digits)
  return Number(n.toPrecision(digits)).toLocaleString(undefined, {
    maximumFractionDigits: 6,
  })
}

/** Format a fraction as a percentage, e.g. 0.123 -> "12.3%". */
export function fmtPct(x, digits = 1) {
  if (isNil(x)) return '—'
  const n = Number(x)
  if (!Number.isFinite(n)) return '—'
  return `${(n * 100).toFixed(digits)}%`
}

/** Format a p-value compactly (scientific when very small). */
export function fmtP(x) {
  if (isNil(x)) return '—'
  const n = Number(x)
  if (!Number.isFinite(n)) return '—'
  if (n === 0) return '< 1e-300'
  if (n < 1e-4) return n.toExponential(2)
  return n.toFixed(4)
}

/** Format a value with an explicit leading sign. */
export function fmtSigned(x, digits = 4) {
  if (isNil(x)) return '—'
  const n = Number(x)
  if (!Number.isFinite(n)) return '—'
  const sign = n > 0 ? '+' : ''
  return `${sign}${fmtNum(n, digits)}`
}

/** Truncate a long label for chart axes. */
export function shortLabel(label, max = 14) {
  const s = String(label ?? '')
  return s.length > max ? `${s.slice(0, max - 1)}…` : s
}

/** Distinct non-null values of a column across an array of records. */
export function uniqueValues(rows, column) {
  const seen = []
  const set = new Set()
  for (const row of rows || []) {
    const value = row?.[column]
    if (value === null || value === undefined) continue
    const key = String(value)
    if (!set.has(key)) {
      set.add(key)
      seen.push(value)
    }
  }
  return seen
}

/** Parse user input into a number, or null when blank/invalid. */
export function toNumber(value) {
  if (value === '' || value === null || value === undefined) return null
  const n = Number(value)
  return Number.isFinite(n) ? n : null
}
