export default function ResultTable({ title, rows }) {
  const items = (rows || []).filter(Boolean)
  if (!items.length) return null
  return (
    <div className="result-table-wrap">
      {title && <h3 className="card-subtitle">{title}</h3>}
      <table className="result-table">
        <tbody>
          {items.map((row, i) => (
            <tr key={`${row.label}-${i}`}>
              <td className="rt-label">{row.label}</td>
              <td className="rt-value">{row.value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
