import { useState } from 'react'

const URGENCY_STYLES = {
  high: 'border-l-red-500 bg-red-50',
  medium: 'border-l-amber-500 bg-amber-50',
  low: 'border-l-emerald-500 bg-emerald-50',
}

const URGENCY_BADGE = {
  high: 'bg-red-600 text-white',
  medium: 'bg-amber-500 text-white',
  low: 'bg-emerald-600 text-white',
}

function CitationList({ citations, t }) {
  const [open, setOpen] = useState(false)
  if (!citations?.length) return null
  return (
    <div className="mt-2">
      <button
        onClick={() => setOpen(!open)}
        className="text-xs text-emerald-700 underline underline-offset-2"
      >
        {t.whyThisAdvice} {open ? '▲' : '▼'}
      </button>
      {open && (
        <ul className="mt-1 space-y-0.5">
          {citations.map((c, i) => (
            <li key={i} className="text-xs text-stone-500">
              📄 {c.source}{c.excerpt_ref ? ` · ${c.excerpt_ref}` : ''}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default function AdvisoryCard({ advisory, t }) {
  return (
    <div className="space-y-3">
      {advisory.advisory.map((item, i) => (
        <div
          key={i}
          className={`border border-stone-200 border-l-4 rounded-xl p-3 ${URGENCY_STYLES[item.urgency]}`}
        >
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${URGENCY_BADGE[item.urgency]}`}>
              {item.urgency}
            </span>
            <h3 className="font-semibold text-sm">{item.title}</h3>
          </div>
          <p className="text-sm text-stone-700">{item.detail}</p>
        </div>
      ))}

      {advisory.irrigation_guidance && (
        <div className="bg-sky-50 border border-sky-200 rounded-xl p-3">
          <p className="text-xs font-semibold text-sky-700 uppercase mb-1">💧 {t.irrigation}</p>
          <p className="text-sm text-stone-700">{advisory.irrigation_guidance}</p>
        </div>
      )}

      {advisory.regenerative_recommendations?.length > 0 && (
        <div className="bg-lime-50 border border-lime-200 rounded-xl p-3">
          <p className="text-xs font-semibold text-lime-700 uppercase mb-1">♻️ {t.regenerative}</p>
          <ul className="list-disc list-inside space-y-1">
            {advisory.regenerative_recommendations.map((r, i) => (
              <li key={i} className="text-sm text-stone-700">{r}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="px-1">
        <CitationList citations={advisory.citations} t={t} />
        {advisory.confidence_note && (
          <p className="text-xs text-stone-400 mt-2 italic">{advisory.confidence_note}</p>
        )}
      </div>
    </div>
  )
}
