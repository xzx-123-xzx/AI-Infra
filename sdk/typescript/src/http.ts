export class AIInfraError extends Error {
  constructor(public statusCode: number, message: string) {
    super(`[${statusCode}] ${message}`);
  }
}

export type ClientOptions = {
  adminToken?: string;
  apiKey?: string;
  timeoutMs?: number;
};

export class HttpClient {
  constructor(
    private baseUrl: string,
    private opts: ClientOptions = {},
  ) {}

  private headers(extra?: Record<string, string>): Record<string, string> {
    const h: Record<string, string> = { ...(extra || {}) };
    if (this.opts.adminToken) h.Authorization = `Bearer ${this.opts.adminToken}`;
    else if (this.opts.apiKey) h.Authorization = `Bearer ${this.opts.apiKey}`;
    return h;
  }

  async request<T>(method: string, path: string, init?: RequestInit): Promise<T> {
    const resp = await fetch(`${this.baseUrl}${path}`, {
      ...init,
      headers: { ...this.headers(init?.headers as Record<string, string>), ...init?.headers },
      signal: AbortSignal.timeout(this.opts.timeoutMs ?? 120000),
    });
    const text = await resp.text();
    if (!resp.ok) throw new AIInfraError(resp.status, text);
    return text ? JSON.parse(text) : (null as T);
  }

  get<T>(path: string) {
    return this.request<T>('GET', path);
  }

  post<T>(path: string, body?: unknown) {
    return this.request<T>('POST', path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  delete<T>(path: string) {
    return this.request<T>('DELETE', path, { method: 'DELETE' });
  }

  put<T>(path: string, body?: unknown) {
    return this.request<T>('PUT', path, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
    });
  }
}
