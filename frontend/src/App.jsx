import { useState } from 'react'
import Sidebar from './components/Sidebar.jsx'
import Header from './components/Header.jsx'
import PowerCalculator from './pages/PowerCalculator.jsx'
import ABAnalysis from './pages/ABAnalysis.jsx'
import MultipleTesting from './pages/MultipleTesting.jsx'
import CausalInference from './pages/CausalInference.jsx'

const PAGES = {
  power: {
    id: 'power',
    title: 'Power Calculator',
    subtitle: 'Size your experiment before you run it',
    Component: PowerCalculator,
  },
  ab: {
    id: 'ab',
    title: 'A/B Analysis',
    subtitle: 'Frequentist, Bayesian and sequential readouts',
    Component: ABAnalysis,
  },
  multiple: {
    id: 'multiple',
    title: 'Multiple Testing',
    subtitle: 'Control the false-discovery rate across many metrics',
    Component: MultipleTesting,
  },
  causal: {
    id: 'causal',
    title: 'Causal Inference',
    subtitle: 'Estimate cause and effect when you cannot randomise',
    Component: CausalInference,
  },
}

export default function App() {
  const [activeId, setActiveId] = useState('power')
  const [navOpen, setNavOpen] = useState(false)

  const page = PAGES[activeId]
  const PageComponent = page.Component

  return (
    <div className="app-shell">
      <Sidebar
        activeId={activeId}
        open={navOpen}
        onNavigate={(id) => {
          setActiveId(id)
          setNavOpen(false)
        }}
      />
      {navOpen && <div className="scrim" onClick={() => setNavOpen(false)} />}
      <div className="app-main">
        <Header
          title={page.title}
          subtitle={page.subtitle}
          onToggleNav={() => setNavOpen((o) => !o)}
        />
        <main className="content">
          <PageComponent />
        </main>
      </div>
    </div>
  )
}
