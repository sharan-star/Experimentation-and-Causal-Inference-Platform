export default function ColumnSelect({
  label,
  value,
  options = [],
  onChange,
  hint,
  allowEmpty = false,
  placeholder = '— select —',
}) {
  return (
    <label className="field">
      {label && <span className="field-label">{label}</span>}
      <select
        className="input"
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value)}
      >
        {allowEmpty && <option value="">{placeholder}</option>}
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  )
}
