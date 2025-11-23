import api from './api'

export type RequestType = 'relational' | 'flat' | 'timeseries'

export type RequestParams = {
  progress?: number
  schema?: unknown
  outputs?: unknown
  [key: string]: unknown
}

export type Request = {
  id: string
  project_id: string
  type: RequestType
  alias?: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  error_message?: string
  error_traceback?: string
  seed?: number
  params_json?: RequestParams
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

export async function startRequest(projectId: string, requestId: string) {
  // Use longer timeout since the job runs synchronously and can take time
  const res = await api.post(
    `/api/v1/projects/${projectId}/requests/${requestId}:start`,
    {},
    { timeout: 60000 } // 60 second timeout for job execution
  )
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

export interface ListRequestsOptions {
  page?: number
  pageSize?: number
  search?: string
}

export async function listRequests(projectId: string, opts: ListRequestsOptions = {}) {
  const { page = 1, pageSize = 10, search } = opts
  const params = new URLSearchParams()
  params.set('skip', String((page - 1) * pageSize))
  params.set('limit', String(pageSize))
  if (search && search.trim()) params.set('q', search.trim())
  const res = await api.get(`/api/v1/projects/${projectId}/requests?${params.toString()}`)
  return res.data as Request[]
}

export async function signArtifact(requestId: string, artifactId: string) {
  // Backend returns { url: string, expires_at?: string }
  const res = await api.get(`/api/v1/requests/${requestId}/artifacts/${artifactId}:sign`)
  return res.data as { url: string; expires_at?: string }
}

export async function deleteRequest(projectId: string, requestId: string) {
  await api.delete(`/api/v1/projects/${projectId}/requests/${requestId}`)
}

export async function restartRequest(projectId: string, requestId: string) {
  const res = await api.post(`/api/v1/projects/${projectId}/requests/${requestId}:restart`)
  return res.data as Request
}
