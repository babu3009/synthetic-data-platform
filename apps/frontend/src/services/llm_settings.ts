import api from './api'

export interface ProjectLlmSettings {
  enabled: boolean
  provider_id?: string | null
  model_id?: string | null
  temperature?: number | null
  top_p?: number | null
  max_tokens?: number | null
  guardrails?: {
    block_pii?: boolean
    allow_tool_use?: boolean
  }
  updated_at?: string
}

export async function getProjectLlmSettings(projectId: string): Promise<ProjectLlmSettings> {
  const res = await api.get(`/api/v1/projects/${projectId}/llm-settings`)
  // Provide sensible defaults if empty
  return {
    enabled: false,
    temperature: 0.7,
    top_p: 1,
    max_tokens: 256,
    guardrails: { block_pii: true, allow_tool_use: false },
    ...(res.data || {}),
  }
}

export async function updateProjectLlmSettings(projectId: string, settings: ProjectLlmSettings): Promise<ProjectLlmSettings> {
  const res = await api.put(`/api/v1/projects/${projectId}/llm-settings`, settings)
  return res.data as ProjectLlmSettings
}
