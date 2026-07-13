const STORAGE_KEY = 'aiinfra_console_settings'

const defaults = {
  adminToken: 'change-me-admin-token',
  gatewayBase: '/api/gateway',
  ragBase: '/api/rag',
  mlopsBase: '/api/mlops',
  agentBase: '/api/agent',
  tenantFilter: '',
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

function qs(params) {
  const entries = Object.entries(params).filter(([, v]) => v !== '' && v != null)
  if (!entries.length) return ''
  return '?' + new URLSearchParams(Object.fromEntries(entries)).toString()
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
  listKeys: (s) => request(s.gatewayBase, `/admin/keys${qs({ tenant_id: s.tenantFilter })}`, s),
  createKey: (s, body) =>
    request(s.gatewayBase, '/admin/keys', s, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  listTenants: (s) => request(s.gatewayBase, '/admin/tenants', s),
  createTenant: (s, body) =>
    request(s.gatewayBase, '/admin/tenants', s, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  tenantUsage: (s, tenantId) => request(s.gatewayBase, `/admin/tenants/${tenantId}/usage`, s),
  updateQuota: (s, tenantId, body) =>
    request(s.gatewayBase, `/admin/tenants/${tenantId}/quota`, s, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  listKbs: (s) => request(s.ragBase, `/knowledge-bases${qs({ tenant_id: s.tenantFilter })}`, s),
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
    const resp = await fetch(`${s.ragBase}/knowledge-bases/${kbId}/documents?async_ingest=true`, {
      method: 'POST',
      headers: authHeaders(s),
      body: form,
    })
    const data = await resp.json()
    if (!resp.ok) throw new Error(data.detail || JSON.stringify(data))
    return data
  },
  getDoc: (s, kbId, docId) => request(s.ragBase, `/knowledge-bases/${kbId}/documents/${docId}`, s),
  listSyncSources: (s, kbId) => request(s.ragBase, `/knowledge-bases/${kbId}/sync-sources`, s),
  createSyncSource: (s, kbId, body) =>
    request(s.ragBase, `/knowledge-bases/${kbId}/sync-sources`, s, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  runSync: (s, kbId, sourceId) =>
    request(s.ragBase, `/knowledge-bases/${kbId}/sync-sources/${sourceId}/run`, s, { method: 'POST' }),
  deleteDoc: (s, kbId, docId) =>
    request(s.ragBase, `/knowledge-bases/${kbId}/documents/${docId}`, s, { method: 'DELETE' }),
  chat: (s, kbId, body) =>
    request(s.ragBase, `/knowledge-bases/${kbId}/chat`, s, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(typeof body === 'string' ? { query: body } : body),
    }),
  retrieve: (s, kbId, query) =>
    request(s.ragBase, `/knowledge-bases/${kbId}/retrieve`, s, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    }),
  listPrompts: (s) => request(s.ragBase, `/prompts${qs({ tenant_id: s.tenantFilter })}`, s),
  createPrompt: (s, body) =>
    request(s.ragBase, '/prompts', s, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  getPrompt: (s, id) => request(s.ragBase, `/prompts/${id}`, s),
  addPromptVersion: (s, id, body) =>
    request(s.ragBase, `/prompts/${id}/versions`, s, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  configureAb: (s, id, variants) =>
    request(s.ragBase, `/prompts/${id}/ab`, s, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ variants }),
    }),
  deletePrompt: (s, id) => request(s.ragBase, `/prompts/${id}`, s, { method: 'DELETE' }),
  federatedChat: (s, body) =>
    request(s.ragBase, '/federated/chat', s, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  listEvalDatasets: (s) => request(s.ragBase, `/eval/datasets${qs({ tenant_id: s.tenantFilter })}`, s),
  createEvalDataset: (s, body) =>
    request(s.ragBase, '/eval/datasets', s, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  createEvalRun: (s, body) =>
    request(s.ragBase, '/eval/runs', s, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  listEvalRuns: (s) => request(s.ragBase, '/eval/runs', s),
  compareEvalRuns: (s, a, b) => request(s.ragBase, `/eval/runs/compare?run_a=${a}&run_b=${b}`, s),
  listMlopsJobs: (s) => request(s.mlopsBase, `/jobs${qs({ tenant_id: s.tenantFilter })}`, s),
  createMlopsJob: (s, body) =>
    request(s.mlopsBase, '/jobs', s, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  submitMlopsJob: (s, id) => request(s.mlopsBase, `/jobs/${id}/submit`, s, { method: 'POST' }),
  listRegistry: (s) => request(s.mlopsBase, `/registry${qs({ tenant_id: s.tenantFilter })}`, s),
  listWorkflows: (s) => request(s.agentBase, `/workflows${qs({ tenant_id: s.tenantFilter })}`, s),
  createWorkflow: (s, body) =>
    request(s.agentBase, '/workflows', s, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  runWorkflow: (s, id, query) =>
    request(s.agentBase, `/workflows/${id}/run`, s, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    }),
}
