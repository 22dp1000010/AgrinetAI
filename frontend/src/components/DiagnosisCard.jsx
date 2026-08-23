const CONFIDENCE_BADGE = {
  high: 'bg-emerald-600',
  medium: 'bg-amber-500',
  low: 'bg-red-600',
}

export default function DiagnosisCard({ result, t }) {
  return (
    <div className="border border-stone-200 rounded-xl p-3 bg-white space-y-2">
      <div className="flex items-center gap-2">
        <span className={`text-[10px] font-bold uppercase text-white px-1.5 py-0.5 rounded ${CONFIDENCE_BADGE[result.confidence]}`}>
          {result.confidence}
        </span>
        <h3 className="font-semibold">{result.disease}</h3>
      </div>

      {result.symptoms_observed?.length > 0 && (
        <ul className="text-sm text-stone-600 list-disc list-inside">
          {result.symptoms_observed.map((s, i) => <li key={i}>{s}</li>)}
        </ul>
      )}

      {result.treatment_steps?.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-stone-500 uppercase">{t.treatment}</p>
          <ol className="text-sm text-stone-700 list-decimal list-inside space-y-0.5 mt-1">
            {result.treatment_steps.map((s, i) => <li key={i}>{s}</li>)}
          </ol>
        </div>
      )}

      {result.organic_options?.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-lime-700 uppercase">♻️ {t.organic}</p>
          <ul className="text-sm text-stone-700 list-disc list-inside mt-1">
            {result.organic_options.map((s, i) => <li key={i}>{s}</li>)}
          </ul>
        </div>
      )}

      {result.safety_note && (
        <p className="text-xs bg-amber-50 border border-amber-200 rounded-lg p-2 text-amber-800">
          ⚠️ {result.safety_note}
        </p>
      )}

      {result.citations?.length > 0 && (
        <p className="text-xs text-stone-400">
          📄 {result.citations.map((c) => c.source).join(' · ')}
        </p>
      )}

      <p className="text-[11px] text-stone-400 italic">{t.outbreakNotice}</p>
    </div>
  )
}
