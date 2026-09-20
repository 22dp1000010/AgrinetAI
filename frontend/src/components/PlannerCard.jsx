// Seasonal rotation plan rendered as a season-by-season timeline.
export default function PlannerCard({ plan, t }) {
  return (
    <div className="space-y-3">
      <ol className="relative border-s-2 border-emerald-200 ms-2 space-y-3">
        {plan.rotation.map((step, i) => (
          <li key={i} className="ms-4">
            <span className="absolute -start-[9px] mt-1.5 w-4 h-4 rounded-full bg-emerald-600 border-2 border-white" />
            <p className="text-xs font-semibold text-emerald-700 uppercase">{step.season}</p>
            <p className="font-semibold text-sm">{step.crop}</p>
            <p className="text-sm text-stone-600">{step.why}</p>
          </li>
        ))}
      </ol>

      {plan.regenerative_plan?.length > 0 && (
        <div className="bg-lime-50 border border-lime-200 rounded-xl p-3">
          <p className="text-xs font-semibold text-lime-700 uppercase mb-1">♻️ {t.regenerativePlan}</p>
          <ul className="list-disc list-inside space-y-1">
            {plan.regenerative_plan.map((r, i) => (
              <li key={i} className="text-sm text-stone-700">{r}</li>
            ))}
          </ul>
        </div>
      )}

      {plan.soil_note && (
        <div className="bg-stone-50 border border-stone-200 rounded-xl p-3">
          <p className="text-xs font-semibold text-stone-500 uppercase mb-1">🧪 {t.soilNote}</p>
          <p className="text-sm text-stone-700">{plan.soil_note}</p>
        </div>
      )}

      {plan.citations?.length > 0 && (
        <p className="text-xs text-stone-400">
          📄 {[...new Set(plan.citations.map((c) => c.source))].join(' · ')}
        </p>
      )}
      {plan.confidence_note && (
        <p className="text-xs text-stone-400 italic">{plan.confidence_note}</p>
      )}
    </div>
  )
}
