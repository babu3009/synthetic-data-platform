import api from './api'

// ---- Types ----
export interface LLMProvider {
  id: string
  kind: 'openai' | 'anthropic' | 'ollama' | 'lmstudio'
  name: string
  base_url: string
  is_enabled: boolean
  created_at?: string
  updated_at?: string
  models_count?: number // derived client-side
}

export interface LLMModel {
  id: string
  provider_id: string
  name: string
  display_name?: string
  context_tokens?: number
  supports_json?: boolean
  is_default?: boolean
  metadata_json?: Record<string, unknown>
  created_at?: string
  updated_at?: string
}

export interface DiscoverModelsResponse {
  models: LLMModel[]
  added_count: number
  updated_count: number
  unchanged_count: number
}

export interface CreateProviderInput {
  kind: LLMProvider['kind']
  name: string
  base_url: string
  is_enabled?: boolean
}

export interface UpdateProviderInput {
  name?: string
  base_url?: string
  is_enabled?: boolean
}

export interface UpsertCredentialsInput {
  api_key?: string | null
  org_id?: string | null
  extra?: Record<string, unknown>
}

export interface CreateModelInput {
  name: string
  display_name?: string
  context_tokens?: number
  supports_json?: boolean
  is_default?: boolean
  metadata_json?: Record<string, unknown>
}

// Helper to append project_id query param consistently
function withProject(projectId: string) {
  return (path: string) => `${path}?project_id=${encodeURIComponent(projectId)}`
}

// ---- Provider CRUD ----
export async function listProviders(projectId: string): Promise<LLMProvider[]> {
  const res = await api.get(withProject(projectId)(`/api/v1/admin/llm/providers`))
  const providers: LLMProvider[] = res.data || []
  return providers
}

export async function createProvider(projectId: string, input: CreateProviderInput): Promise<LLMProvider> {
  const res = await api.post(withProject(projectId)(`/api/v1/admin/llm/providers`), input)
  return res.data as LLMProvider
}

export async function updateProvider(projectId: string, providerId: string, input: UpdateProviderInput): Promise<LLMProvider> {
  const res = await api.patch(withProject(projectId)(`/api/v1/admin/llm/providers/${providerId}`), input)
  return res.data as LLMProvider
}

// ---- Credentials ----
export async function upsertCredentials(projectId: string, providerId: string, input: UpsertCredentialsInput) {
  const res = await api.post(withProject(projectId)(`/api/v1/admin/llm/providers/${providerId}/credentials`), input)
  return res.data
}

// ---- Models ----
export async function listModels(projectId: string, providerId: string): Promise<LLMModel[]> {
  const res = await api.get(withProject(projectId)(`/api/v1/admin/llm/providers/${providerId}/models`))
  return res.data || []
}

export async function createModel(projectId: string, providerId: string, input: CreateModelInput): Promise<LLMModel> {
  const res = await api.post(withProject(projectId)(`/api/v1/admin/llm/providers/${providerId}/models`), input)
  return res.data as LLMModel
}

// ---- Probe ----
export interface ProbeResult { ok: boolean; message: string }
export async function probeProvider(projectId: string, providerId: string): Promise<ProbeResult> {
  const res = await api.post(withProject(projectId)(`/api/v1/admin/llm/providers/${providerId}:probe`))
  return res.data as ProbeResult
}

// ---- Discover ----
export async function discoverModels(projectId: string, providerId: string): Promise<DiscoverModelsResponse> {
  const res = await api.post(withProject(projectId)(`/api/v1/admin/llm/providers/${providerId}:discover-models`))
  return res.data as DiscoverModelsResponse
}

// Utility to mark one model default (client-side follow-up create/upsert) -- backend may upsert
export async function markModelDefault(projectId: string, providerId: string, model: LLMModel): Promise<LLMModel> {
  // Re-send create with is_default true (server should update existing or ignore if unchanged)
  return createModel(projectId, providerId, { ...model, is_default: true })
}
