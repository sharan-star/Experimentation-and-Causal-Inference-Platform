import { useEffect, useState } from 'react'
import { health } from '../api/client.js'

export default function Header({ title, subtitle, onToggleNav }) {
  const [status, setStatus] = useState('checking')

  useEffect(() => {
    let cancelled = false
    health()
      .then(() => {
        if (!cancelled) setStatus('online')
      })
      .catch(() => {
        if (!cancelled) setStatus('offline')
      })
    return () => {
      cancelled = true
    }
  }, [])

  const label =
    status === 'online'
      ? 'Backend online'
      : status === 'offline'
        ? 'Backend offline'
        : 'Checking backend…'

  return (
    <header className="header">
      <button
        type="button"
        className="header-menu"
        aria-label="Toggle navigation"
        onClick={onToggleNav}
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#334155" strokeWidth="2">
          <path d="M4 7h16M4 12h16M4 17h16" strokeLinecap="round" />
        </svg>
      </button>
      <div className="header-titles">
        <span className="header-title">{title}</span>
        {subtitle && <span className="header-subtitle">{subtitle}</span>}
      </div>
      <div className="header-spacer" />
      <span className="status-pill" title="FastAPI backend health check (/api/health)">
        <span className={`status-dot ${status}`} />
        {label}
      </span>
    </header>
  )
}
