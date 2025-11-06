import api from './api'

export type RequestType = 'relational' | 'flat' | 'timeseries'

export type Request = {
  id: string
  project_id: string
  type: RequestType
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  seed?: number
  params_json?: unknown
  created_at: string
  started_at?: string
  finished_at?: string
}

export type Artifact = {
  id: string
  request_id: string
  format: 'csv' | 'xlsx' | 'parquet' | 'jsonl'
  storage_uri: string
  size_bytes: number
  created_at: string
}

export async function createRequest(projectId: string, payload: Partial<Request>) {
  const res = await api.post(`/api/v1/projects/${projectId}/requests/`, payload)
  return res.data as Request
}

export async function startRequest(requestId: string) {
  const res = await api.post(`/api/v1/requests/${requestId}:start`)
  return res.data as Request
}

export async function getRequest(projectId: string, requestId: string) {
  const res = await api.get(`/api/v1/projects/${projectId}/requests/${requestId}`)
  return res.data as Request
}

export async function listArtifacts(requestId: string) {
  const res = await api.get(`/api/v1/requests/${requestId}/artifacts`)
  return res.data as Artifact[]
}

export async function estimateRequest(projectId: string, requestId: string) {
  // Backend contract: POST ...:estimate returns { rows: number, size_bytes: number, seconds: number }
  const res = await api.post(`/api/v1/projects/${projectId}/requests/${requestId}:estimate`)
  return res.data as { rows?: number; size_bytes?: number; seconds?: number }
}
