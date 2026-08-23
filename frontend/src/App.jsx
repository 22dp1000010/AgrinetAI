import { useState } from 'react'
import Farmer from './pages/Farmer.jsx'
import Dashboard from './pages/Dashboard.jsx'
import { NODES } from './api.js'
import { STRINGS } from './i18n.js'

const LANGS = [
  { code: 'en', label: 'English' },
  { code: 'te', label: 'తెలుగు' },
  { code: 'hi', label: 'हिंदी' },
]

export default function App() {
  const [view, setView] = useState('farmer')
  const [nodeId, setNodeId] = useState('TS')
  const [language, setLanguage] = useState('en')
  const t = STRINGS[language]
  const node = NODES[nodeId].url

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-emerald-900 text-white shadow">
        <div className="max-w-5xl mx-auto px-4 py-3 flex flex-wrap items-center gap-3">
          <div className="mr-auto">
            <h1 className="text-xl font-bold tracking-tight">🌾 {t.appTitle}</h1>
            <p className="text-emerald-200 text-xs">{t.tagline}</p>
          </div>

          <nav className="flex rounded-lg overflow-hidden border border-emerald-700 text-sm">
            <button
              onClick={() => setView('farmer')}
              className={`px-3 py-1.5 ${view === 'farmer' ? 'bg-emerald-600' : 'bg-emerald-800 hover:bg-emerald-700'}`}
            >
              {t.farmerView}
            </button>
            <button
              onClick={() => setView('officer')}
              className={`px-3 py-1.5 ${view === 'officer' ? 'bg-emerald-600' : 'bg-emerald-800 hover:bg-emerald-700'}`}
            >
              {t.officerView}
            </button>
          </nav>

          <select
            value={nodeId}
            onChange={(e) => setNodeId(e.target.value)}
            className="bg-emerald-800 border border-emerald-700 rounded-lg px-2 py-1.5 text-sm"
            title="State node"
          >
            {Object.entries(NODES).map(([id, n]) => (
              <option key={id} value={id}>{n.label}</option>
            ))}
          </select>

          <div className="flex rounded-lg overflow-hidden border border-emerald-700 text-sm">
            {LANGS.map((l) => (
              <button
                key={l.code}
                onClick={() => setLanguage(l.code)}
                className={`px-2.5 py-1.5 ${language === l.code ? 'bg-emerald-600' : 'bg-emerald-800 hover:bg-emerald-700'}`}
              >
                {l.label}
              </button>
            ))}
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-5xl w-full mx-auto px-4 py-5">
        {view === 'farmer'
          ? <Farmer node={node} language={language} t={t} />
          : <Dashboard node={node} nodeId={nodeId} t={t} />}
      </main>

      <footer className="text-center text-xs text-stone-400 pb-4">
        AgriNet — open federation protocol v1.0 · a digital public good prototype
      </footer>
    </div>
  )
}
