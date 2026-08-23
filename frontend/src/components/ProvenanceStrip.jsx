// Makes the data pipeline visible: satellite + soil + weather values that
// grounded the advisory, with their sources.
export default function ProvenanceStrip({ provenance, t }) {
  if (!provenance) return null
  const { satellite, soil, weather } = provenance
  const items = [
    {
      icon: '🛰️', label: t.satellite,
      value: satellite.ndvi_mean != null
        ? `NDVI ${satellite.ndvi_mean} (${satellite.ndvi_trend})`
        : '—',
      source: satellite.source,
    },
    {
      icon: '🧪', label: t.soil,
      value: soil.ph != null ? `pH ${soil.ph} · SOC ${soil.soc_g_per_kg} g/kg` : '—',
      source: soil.source,
    },
    {
      icon: '🌦️', label: t.weather,
      value: weather.rain_next_7d_mm != null
        ? `${weather.rain_next_7d_mm} mm rain / 7d · max ${weather.max_temp_c}°C`
        : '—',
      source: weather.source,
    },
  ]
  return (
    <div className="bg-white border border-stone-200 rounded-xl p-3">
      <p className="text-xs font-semibold text-stone-500 uppercase tracking-wide mb-2">
        {t.provenance}
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
        {items.map((item) => (
          <div key={item.label} className="flex items-start gap-2 text-sm">
            <span className="text-lg leading-none">{item.icon}</span>
            <div>
              <p className="font-medium">{item.label} ✓</p>
              <p className="text-stone-700">{item.value}</p>
              <p className="text-[10px] text-stone-400">{item.source}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
