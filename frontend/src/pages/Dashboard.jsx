import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Tooltip } from 'react-leaflet'
import { api } from '../api.js'

const CENTERS = { TS: [17.9, 79.5], OD: [20.5, 84.0] }

function StatCard({ label, value }) {
  return (
    <div className="bg-white border border-stone-200 rounded-xl p-4">
      <p className="text-3xl font-bold text-emerald-800">{value}</p>
      <p className="text-xs text-stone-500 mt-1">{label}</p>
    </div>
  )
}

function ListCard({ label, items, nameKey }) {
  return (
    <div className="bg-white border border-stone-200 rounded-xl p-4">
      <p className="text-xs text-stone-500 mb-2">{label}</p>
      {items.length === 0 && <p className="text-sm text-stone-400">—</p>}
      <ul className="space-y-1">
        {items.map((item, i) => (
          <li key={i} className="text-sm flex justify-between gap-2">
            <span className="truncate">{item[nameKey]}</span>
            <span className="text-stone-400">{item.count}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function Dashboard({ node, nodeId, t }) {
  const [stats, setStats] = useState(null)
  const [heatmap, setHeatmap] = useState([])
  const [alerts, setAlerts] = useState([])
  const [peers, setPeers] = useState([])
  const [models, setModels] = useState([])
  const [health, setHealth] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    setError(null)
    Promise.all([
      api.stats(node), api.heatmap(node), api.alerts(node),
      api.peers(node), api.models(node), api.health(node),
    ])
      .then(([s, h, a, p, m, hl]) => {
        if (cancelled) return
        setStats(s); setHeatmap(h); setAlerts(a.alerts)
        setPeers(p); setModels(m); setHealth(hl)
      })
      .catch((e) => !cancelled && setError(e.message))
    return () => { cancelled = true }
  }, [node])

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl p-4">
        Node unreachable: {error}
      </div>
    )
  }
  if (!stats) return <p className="text-stone-400 text-sm">Loading node data…</p>

  const peerAlerts = alerts.filter((a) => a.received_from_peer)
  const maxCount = Math.max(1, ...heatmap.map((p) => p.count))

  return (
    <div className="space-y-4">
      {/* Federated early-warning banner — the demo money-shot */}
      {peerAlerts.map((a) => (
        <div key={a.id} className="bg-orange-50 border-l-4 border-orange-500 rounded-xl p-4">
          <p className="font-semibold text-orange-800 text-sm">
            🔔 {t.fromPeer} {a.origin_state === 'TS' ? 'Telangana' : a.origin_state === 'OD' ? 'Odisha' : a.origin_state} (AgriNet federation)
          </p>
          <p className="text-sm text-stone-700 mt-1">{a.message}</p>
        </div>
      ))}

      <h2 className="text-lg font-bold">
        {stats.state_name} — {t.officerView}
      </h2>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard label={t.queriesToday} value={stats.queries_today} />
        <StatCard label={t.totalQueries} value={stats.total_queries} />
        <ListCard label={t.topCrops} items={stats.top_crops} nameKey="crop" />
        <ListCard label={t.topDiseases} items={stats.top_diseases} nameKey="disease" />
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        {/* Heatmap */}
        <div className="bg-white border border-stone-200 rounded-xl p-4">
          <p className="text-xs text-stone-500 mb-2">{t.queryHeatmap}</p>
          <MapContainer
            center={CENTERS[nodeId] || CENTERS.TS}
            zoom={7}
            className="h-72 w-full rounded-lg z-0"
            scrollWheelZoom={false}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {heatmap.map((p, i) => (
              <CircleMarker
                key={i}
                center={[p.lat, p.lon]}
                radius={6 + 14 * (p.count / maxCount)}
                pathOptions={{
                  color: 'transparent',
                  fillColor: p.count / maxCount > 0.6 ? '#dc2626' : p.count / maxCount > 0.3 ? '#f59e0b' : '#10b981',
                  fillOpacity: 0.55,
                }}
              >
                <Tooltip>{p.count} queries near {p.lat}, {p.lon}</Tooltip>
              </CircleMarker>
            ))}
          </MapContainer>
        </div>

        <div className="space-y-4">
          {/* Alert feed */}
          <div className="bg-white border border-stone-200 rounded-xl p-4">
            <p className="text-xs text-stone-500 mb-2">🚨 {t.alertFeed}</p>
            {alerts.length === 0 && <p className="text-sm text-stone-400">{t.noAlerts}</p>}
            <ul className="space-y-2">
              {alerts.map((a) => (
                <li
                  key={a.id}
                  className={`text-sm rounded-lg p-2.5 border ${
                    a.received_from_peer
                      ? 'bg-orange-50 border-orange-200'
                      : 'bg-red-50 border-red-200'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] font-bold text-white uppercase px-1.5 py-0.5 rounded ${
                      a.received_from_peer ? 'bg-orange-500' : 'bg-red-600'
                    }`}>
                      {a.received_from_peer ? `peer · ${a.origin_state}` : 'local'}
                    </span>
                    <span className="font-medium">{a.disease}</span>
                  </div>
                  <p className="text-xs text-stone-500 mt-1">
                    {a.district} · {a.report_count} reports / {a.window_days}d · severity {a.severity}
                  </p>
                </li>
              ))}
            </ul>
          </div>

          {/* Federation panel — makes the invisible layer visible */}
          <div className="bg-emerald-950 text-emerald-100 rounded-xl p-4">
            <p className="text-xs text-emerald-400 uppercase font-semibold mb-2">
              🌐 {t.federationPanel}
            </p>
            <p className="text-xs mb-2">
              {t.protocol}: AgriNet v{health?.protocol_version} · node {health?.state_id} · open schema (/v1)
            </p>
            <p className="text-xs text-emerald-400 mt-2 mb-1">{t.peerNodes}</p>
            <ul className="space-y-1">
              {peers.map((p) => (
                <li key={p.state_id} className="text-xs flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block" />
                  {p.name} · <code className="text-emerald-300">{p.base_url}</code>
                </li>
              ))}
            </ul>
            <p className="text-xs text-emerald-400 mt-3 mb-1">{t.modelRegistry}</p>
            <ul className="space-y-1">
              {models.map((m) => (
                <li key={m.name} className="text-xs">
                  📦 {m.name} <span className="text-emerald-500">v{m.version}</span> — {m.task}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
