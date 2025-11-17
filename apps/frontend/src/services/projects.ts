import api from './api'

// Align with backend schema (webhook_run_status_url).
// Deprecated front-end name webhook_url is removed; migrate any callers.
export type Project = {
  id: string
  name: string
  description?: string | null
  owner?: string
  tags?: string[]
  webhook_run_status_url?: string | null
  artifact_ttl_days?: number | null
  created_at?: string
  updated_at?: string
  entity_count?: number
}

export async function listProjects(): Promise<Project[]> {
  const res = await api.get('/api/v1/projects/')
  return res.data
}

export async function createProject(input: { 
  name: string
  description?: string | null
  tags?: string[]
  webhook_run_status_url?: string | null
  artifact_ttl_days?: number | null
}): Promise<Project> {
  const res = await api.post('/api/v1/projects/', input)
  return res.data
}

export async function getProject(id: string): Promise<Project> {
  const res = await api.get(`/api/v1/projects/${encodeURIComponent(id)}`)
  return res.data
}

export async function updateProject(id: string, input: { 
  name?: string
  description?: string | null
  tags?: string[]
  webhook_run_status_url?: string | null
  artifact_ttl_days?: number | null
}): Promise<Project> {
  const res = await api.put(`/api/v1/projects/${encodeURIComponent(id)}`, input)
  return res.data
}

export async function deleteProject(id: string): Promise<void> {
  await api.delete(`/api/v1/projects/${encodeURIComponent(id)}`)
}

// Register or update the run-status webhook for a project
export async function registerRunStatusWebhook(projectId: string, url: string): Promise<Project> {
  const res = await api.post('/api/v1/webhooks/run-status', { project_id: projectId, url })
  return res.data
}

// Check if project name exists for current user
export async function checkProjectNameExists(name: string): Promise<boolean> {
  try {
    const names = await searchProjectNames(name)
    return names.some(n => n.toLowerCase() === name.toLowerCase())
  } catch {
    return false
  }
}

// Search project names (for validation/autocomplete)
export async function searchProjectNames(query: string = ''): Promise<string[]> {
  const res = await api.get('/api/v1/projects/search/', { params: { q: query } })
  return res.data
}
