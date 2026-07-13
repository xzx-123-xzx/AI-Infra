import { HttpClient } from './http.js';

export class GatewayClient {
  private http: HttpClient;

  constructor(baseUrl = 'http://localhost:8080', opts: { adminToken?: string; apiKey?: string } = {}) {
    this.http = new HttpClient(baseUrl, opts);
  }

  health() {
    return this.http.get('/health');
  }

  listModels() {
    return this.http.get<{ data: { id: string; provider: string }[] }>('/admin/models');
  }

  listApiKeys(tenantId?: string) {
    const q = tenantId ? `?tenant_id=${encodeURIComponent(tenantId)}` : '';
    return this.http.get(`/admin/keys${q}`);
  }

  createApiKey(name: string, tenantId = 'default', rateLimitRpm?: number) {
    return this.http.post('/admin/keys', { name, tenant_id: tenantId, rate_limit_rpm: rateLimitRpm });
  }

  chatCompletions(model: string, messages: { role: string; content: string }[], extra: Record<string, unknown> = {}) {
    return this.http.post('/v1/chat/completions', { model, messages, stream: false, ...extra });
  }

  listTenants() {
    return this.http.get('/admin/tenants');
  }

  tenantUsage(tenantId: string) {
    return this.http.get(`/admin/tenants/${tenantId}/usage`);
  }
}
