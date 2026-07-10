const STORAGE_KEY = 'aiinfra_console_settings'

const defaults = {
  adminToken: 'change-me-admin-token',
  gatewayBase: '/api/gateway',
  ragBase: '/api/rag',
}

export function loadSettings() {
  try {
    return { ...defaults, ...JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}') }
  } catch {
    return { ...defaults }
  }
}

export function saveSettings(settings) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
}

function authHeaders(settings) {
  return {
    Authorization: `Bearer ${settings.adminToken}`,
  }
}

async function request(base, path, settings, options = {}) {
  const resp = await fetch(`${base}${path}`, {
    ...options,
    headers: {
      ...authHeaders(settings),
      ...(options.headers || {}),
    },
  })
  const text = await resp.text()
  let data = null
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = text
  }
  if (!resp.ok) {
    throw new Error(typeof data === 'object' ? data.detail || JSON.stringify(data) : text)
  }
  return data
}

export const api = {
  gatewayHealth: (s) => request(s.gatewayBase, '/health', s),
  ragHealth: (s) => request(s.ragBase, '/health', s),
  listModels: (s) => request(s.gatewayBase, '/admin/models', s),
  listKeys: (s) => request(s.gatewayBase, '/admin/keys', s),
  createKey: (s, body) =>
    request(s.gatewayBase, '/admin/keys', s, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  listKbs: (s) => request(s.ragBase, '/knowledge-bases', s),
  createKb: (s, body) =>
    request(s.ragBase, '/knowledge-bases', s, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  deleteKb: (s, id) => request(s.ragBase, `/knowledge-bases/${id}`, s, { method: 'DELETE' }),
  getKb: (s, id) => request(s.ragBase, `/knowledge-bases/${id}`, s),
  listDocs: (s, kbId) => request(s.ragBase, `/knowledge-bases/${kbId}/documents`, s),
  uploadDoc: async (s, kbId, file) => {
    const form = new FormData()
    form.append('file', file)
    const resp = await fetch(`${s.ragBase}/knowledge-bases/${kbId}/documents`, {
      method: 'POST',
      headers: authHeaders(s),
      body: form,
    })
    const data = await resp.json()
    if (!resp.ok) throw new Error(data.detail || JSON.stringify(data))
    return data
  },
  deleteDoc: (s, kbId, docId) =>
    request(s.ragBase, `/knowledge-bases/${kbId}/documents/${docId}`, s, { method: 'DELETE' }),
  chat: (s, kbId, query) =>
    request(s.ragBase, `/knowledge-bases/${kbId}/chat`, s, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    }),
  retrieve: (s, kbId, query) =>
    request(s.ragBase, `/knowledge-bases/${kbId}/retrieve`, s, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    }),
}
