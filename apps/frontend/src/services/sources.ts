import api from './api'

export type SourceResponse = {
  id: string
  type?: string
  created_at?: string
}

function formDataWithFile(file: File, extra?: Record<string, string>) {
  const fd = new FormData()
  fd.append('file', file)
  if (extra) {
    for (const [k, v] of Object.entries(extra)) fd.append(k, v)
  }
  return fd
}

export async function uploadDDLSource(projectId: string, file: File, dialect?: string, headers?: Record<string, string>) {
  const fd = formDataWithFile(file, dialect ? { dialect } : undefined)
  const res = await api.post(`/api/v1/projects/${projectId}/sources`, fd, {
    headers: { 'Content-Type': 'multipart/form-data', ...(headers || {}) },
  })
  return res.data as SourceResponse
}

export async function uploadJSONSource(projectId: string, file: File, headers?: Record<string, string>) {
  const fd = formDataWithFile(file)
  const res = await api.post(`/api/v1/projects/${projectId}/sources`, fd, {
    headers: { 'Content-Type': 'multipart/form-data', ...(headers || {}) },
  })
  return res.data as SourceResponse
}

export async function getSourceSchema(projectId: string, sourceId: string, headers?: Record<string, string>) {
  // Try primary endpoint
  try {
    const res = await api.get(`/api/v1/projects/${projectId}/sources/${sourceId}`, { headers })
    if (res.data && res.data.tables) return res.data
  } catch (_) {
    // fallthrough to /tables
  }
  const res2 = await api.get(`/api/v1/projects/${projectId}/sources/${sourceId}/tables`, { headers })
  return res2.data
}

// List sources for a project. Backend currently omits explicit list endpoint in legacy router; if unavailable this will
// return an empty array. Once /api/v1/projects/:projectId/sources is implemented to list existing sources, this method
// will surface real data.
export type SourceListItem = {
  id: string
  kind: string
  created_at?: string
  tables_count?: number
}

export async function listSources(projectId: string): Promise<SourceListItem[]> {
  try {
    const res = await api.get(`/api/v1/projects/${projectId}/sources`)
    // Expect shape: [{ id, kind, created_at, tables_count? }]
    if (Array.isArray(res.data)) return res.data as SourceListItem[]
    return []
  } catch (e) {
    // Gracefully degrade until endpoint exists
    return []
  }
}

export async function getSourceDag(projectId: string, sourceId: string) {
  const res = await api.get(`/api/v1/projects/${projectId}/sources/${sourceId}/dag`)
  return res.data as { nodes: string[]; edges: [string, string][] }
}
