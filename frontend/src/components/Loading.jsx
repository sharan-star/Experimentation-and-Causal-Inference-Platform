export default function Loading({ label = 'Working…' }) {
  return (
    <div className="loading">
      <span className="spinner" />
      <span>{label}</span>
    </div>
  )
}
