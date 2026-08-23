// Single place the frontend knows about backends. The node toggle switches
// every call between state nodes; Cloud Run URLs come from build-time env.
export const NODES = {
  TS: {
    label: 'Telangana node',
    url: import.meta.env.VITE_NODE_TS || 'http://localhost:8001',
  },
  OD: {
    label: 'Odisha node',
    url: import.meta.env.VITE_NODE_OD || 'http://localhost:8002',
  },
}

async function request(base, path, options = {}) {
  const res = await fetch(`${base}${path}`, options)
  if (!res.ok) {
    let detail = res.statusText
    try { detail = (await res.json()).detail || detail } catch { /* keep statusText */ }
    throw new Error(detail)
  }
  return res.json()
}

const json = (body) => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export const api = {
  getAdvisory: (node, payload) => request(node, '/api/advisory', json(payload)),
  ask: (node, payload) => request(node, '/api/ask', json(payload)),
  diagnose: (node, { image, crop, language, lat, lon }) => {
    const form = new FormData()
    form.append('image', image)
    if (crop) form.append('crop', crop)
    form.append('language', language)
    if (lat != null) form.append('lat', lat)
    if (lon != null) form.append('lon', lon)
    return request(node, '/api/diagnose', { method: 'POST', body: form })
  },
  stats: (node) => request(node, '/api/dashboard/stats'),
  heatmap: (node) => request(node, '/api/dashboard/heatmap'),
  alerts: (node) => request(node, '/v1/alerts'),
  peers: (node) => request(node, '/v1/peers'),
  models: (node) => request(node, '/v1/models'),
  health: (node) => request(node, '/v1/health'),
}
