import { HttpClient } from './http.js';

export class AgentClient {
  private http: HttpClient;

  constructor(baseUrl = 'http://localhost:8083', opts: { adminToken?: string } = {}) {
    this.http = new HttpClient(baseUrl, { adminToken: opts.adminToken });
  }

  health() {
    return this.http.get('/health');
  }

  listTools() {
    return this.http.get('/agents/tools');
  }

  run(query: string, opts: { kbId?: number; tools?: string[]; maxSteps?: number } = {}) {
    return this.http.post('/agents/run', {
      query,
      kb_id: opts.kbId,
      tools: opts.tools,
      max_steps: opts.maxSteps,
    });
  }
}
