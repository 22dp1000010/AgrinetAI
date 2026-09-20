import { useState } from 'react'

// Farmer-facing outbreak warnings: red for the farmer's own district,
// amber for regional/federated early warnings from other states.
export default function WarningBanner({ warnings, t }) {
  if (!warnings?.length) return null
  return (
    <div className="space-y-2">
      {warnings.map((w, i) => <Warning key={i} w={w} t={t} />)}
    </div>
  )
}

function Warning({ w, t }) {
  const [open, setOpen] = useState(false)
  const own = w.scope === 'your_district'
  return (
    <div
      className={`border-l-4 rounded-xl p-3 ${
        own ? 'bg-red-50 border-red-500' : 'bg-amber-50 border-amber-500'
      }`}
    >
      <p className={`text-sm font-semibold ${own ? 'text-red-800' : 'text-amber-800'}`}>
        {own ? '🚨' : '⚠️'} {own ? t.outbreakYourDistrict : t.outbreakRegional}
        {w.from_peer && (
          <span className="font-normal"> · {t.viaFederation} {w.origin_state}</span>
        )}
      </p>
      <p className="text-sm text-stone-700 mt-1">
        {w.message || `${w.disease}${w.district ? ` — ${w.district}` : ''}`}
      </p>
      {w.prevention && (
        <div className="mt-2">
          <button
            onClick={() => setOpen(!open)}
            className={`text-xs underline underline-offset-2 ${own ? 'text-red-700' : 'text-amber-700'}`}
          >
            🛡️ {t.preventionTip} {open ? '▲' : '▼'}
          </button>
          {open && (
            <div className="mt-1 bg-white/70 rounded-lg p-2">
              <p className="text-xs text-stone-700">{w.prevention.text}</p>
              <p className="text-[10px] text-stone-400 mt-1">📄 {w.prevention.source}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
