import { HttpClient } from './http.js';

export class RagClient {
  private http: HttpClient;

  constructor(baseUrl = 'http://localhost:8081', opts: { adminToken?: string } = {}) {
    this.http = new HttpClient(baseUrl, { adminToken: opts.adminToken });
  }

  health() {
    return this.http.get('/health');
  }

  createKnowledgeBase(name: string, tenantId = 'default', description?: string) {
    return this.http.post('/knowledge-bases', { name, tenant_id: tenantId, description });
  }

  listKnowledgeBases(tenantId?: string) {
    const q = tenantId ? `?tenant_id=${encodeURIComponent(tenantId)}` : '';
    return this.http.get(`/knowledge-bases${q}`);
  }

  uploadDocument(kbId: number, file: Blob, filename: string, asyncIngest = true) {
    const form = new FormData();
    form.append('file', file, filename);
    const q = asyncIngest ? '?async_ingest=true' : '?async_ingest=false';
    return this.http.request('POST', `/knowledge-bases/${kbId}/documents${q}`, { method: 'POST', body: form });
  }

  getDocument(kbId: number, docId: number) {
    return this.http.get(`/knowledge-bases/${kbId}/documents/${docId}`);
  }

  chat(kbId: number, query: string, extra: Record<string, unknown> = {}) {
    return this.http.post(`/knowledge-bases/${kbId}/chat`, { query, ...extra });
  }

  createSyncSource(kbId: number, body: Record<string, unknown>) {
    return this.http.post(`/knowledge-bases/${kbId}/sync-sources`, body);
  }

  runSync(kbId: number, sourceId: number) {
    return this.http.post(`/knowledge-bases/${kbId}/sync-sources/${sourceId}/run`);
  }
}
