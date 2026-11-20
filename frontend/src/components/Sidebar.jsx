const NAV_ITEMS = [
  {
    id: 'power',
    label: 'Power Calculator',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M4 19h16" strokeLinecap="round" />
        <rect x="5" y="11" width="3" height="8" rx="1" fill="currentColor" stroke="none" />
        <rect x="10.5" y="7" width="3" height="12" rx="1" fill="currentColor" stroke="none" />
        <rect x="16" y="4" width="3" height="15" rx="1" fill="currentColor" stroke="none" />
      </svg>
    ),
  },
  {
    id: 'ab',
    label: 'A/B Analysis',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <circle cx="8" cy="12" r="4.5" />
        <circle cx="16" cy="12" r="4.5" />
      </svg>
    ),
  },
  {
    id: 'multiple',
    label: 'Multiple Testing',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <circle cx="12" cy="12" r="8" />
        <circle cx="12" cy="12" r="4" />
        <circle cx="12" cy="12" r="1.2" fill="currentColor" stroke="none" />
      </svg>
    ),
  },
  {
    id: 'causal',
    label: 'Causal Inference',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <circle cx="6" cy="6" r="2.4" />
        <circle cx="18" cy="6" r="2.4" />
        <circle cx="12" cy="18" r="2.4" />
        <path d="M7.8 7.6 10.7 16M16.2 7.6 13.3 16M8.4 6h7.2" strokeLinecap="round" />
      </svg>
    ),
  },
]

export default function Sidebar({ activeId, onNavigate, open }) {
  return (
    <aside className={`sidebar${open ? ' open' : ''}`}>
      <div className="sidebar-brand">
        <div className="brand-mark">EC</div>
        <div className="brand-text">
          <span className="brand-title">Experimentation</span>
          <span className="brand-sub">Causal Inference Platform</span>
        </div>
      </div>
      <nav className="sidebar-nav">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`nav-item${activeId === item.id ? ' active' : ''}`}
            onClick={() => onNavigate(item.id)}
          >
            {item.icon}
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
      <div className="sidebar-footer">
        Design &amp; analyse experiments · estimate cause and effect
      </div>
    </aside>
  )
}
