import type {
  ConfigPayload,
  DiffResponse,
  PydanticErrorEntry,
  RootSchema,
} from './types';

const API_BASE = '/api';

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: PydanticErrorEntry[] | string,
  ) {
    super(`API ${status}: ${typeof detail === 'string' ? detail : JSON.stringify(detail)}`);
  }
}

async function _fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(url, init);
  if (!resp.ok) {
    let detail: PydanticErrorEntry[] | string;
    try {
      const body = await resp.json();
      detail = body.detail ?? body;
    } catch {
      detail = await resp.text();
    }
    throw new ApiError(resp.status, detail);
  }
  return (await resp.json()) as T;
}

export async function getConfig(): Promise<ConfigPayload> {
  return _fetchJson<ConfigPayload>(`${API_BASE}/config`);
}

export async function getSchema(): Promise<RootSchema> {
  return _fetchJson<RootSchema>(`${API_BASE}/schema`);
}

export async function putConfig(payload: ConfigPayload): Promise<DiffResponse> {
  return _fetchJson<DiffResponse>(`${API_BASE}/config`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function postDiff(payload: ConfigPayload): Promise<DiffResponse> {
  return _fetchJson<DiffResponse>(`${API_BASE}/diff`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

// configarr endpoints — Phase 26 (D-03)
export async function getConfigarrConfig(): Promise<Record<string, unknown>> {
  return _fetchJson<Record<string, unknown>>(`${API_BASE}/configarr/config`);
}
export async function getConfigarrSchema(): Promise<RootSchema> {
  return _fetchJson<RootSchema>(`${API_BASE}/configarr/schema`);
}
export async function putConfigarrConfig(payload: Record<string, unknown>): Promise<DiffResponse> {
  return _fetchJson<DiffResponse>(`${API_BASE}/configarr/config`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}
export async function postConfigarrDiff(payload: Record<string, unknown>): Promise<DiffResponse> {
  return _fetchJson<DiffResponse>(`${API_BASE}/configarr/diff`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}
