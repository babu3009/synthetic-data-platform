import api from './api';

export interface ApiKey {
  id: string;
  project_id: string;
  name: string;
  scopes: string[];
  created_at: string;
  // plaintext_key only present on create response
  plaintext_key?: string;
}

export interface CreateApiKeyInput {
  name: string;
  scopes: string[];
}

export interface ListApiKeysOptions {
  page?: number;
  pageSize?: number;
  search?: string;
}

export async function listApiKeys(projectId: string, opts: ListApiKeysOptions = {}): Promise<ApiKey[]> {
  const { page = 1, pageSize = 10, search } = opts;
  const params = new URLSearchParams();
  params.set('skip', String((page - 1) * pageSize));
  params.set('limit', String(pageSize));
  if (search && search.trim()) params.set('q', search.trim());
  const res = await api.get(`/api/v1/projects/${projectId}/api-keys?${params.toString()}`);
  return res.data as ApiKey[];
}

export async function createApiKey(projectId: string, body: CreateApiKeyInput): Promise<ApiKey> {
  const res = await api.post(`/api/v1/projects/${projectId}/api-keys`, body);
  return res.data as ApiKey;
}

export async function revokeApiKey(projectId: string, keyId: string): Promise<ApiKey> {
  const res = await api.delete(`/api/v1/projects/${projectId}/api-keys/${keyId}`);
  return res.data as ApiKey;
}

export async function listApiKeyScopes(projectId: string): Promise<string[]> {
  const res = await api.get(`/api/v1/projects/${projectId}/api-keys/scopes`);
  return res.data as string[];
}
