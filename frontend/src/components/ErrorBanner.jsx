export default function ErrorBanner({ message, onClose }) {
  if (!message) return null
  return (
    <div className="error-banner" role="alert">
      <span className="error-banner-icon">!</span>
      <span className="error-banner-text">{message}</span>
      {onClose && (
        <button
          type="button"
          className="error-banner-close"
          aria-label="Dismiss error"
          onClick={onClose}
        >
          ×
        </button>
      )}
    </div>
  )
}
