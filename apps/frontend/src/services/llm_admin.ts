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

export interface ProviderTaskDefaultOut {
  task_type: 'chat' | 'embeddings' | 'tools'
  model_id: string
  model?: LLMModel | null
}

export interface AuditEventItem {
  id: string
  actor: string
  project_id?: string | null
  action: string
  payload_json?: Record<string, unknown>
  created_at?: string | null
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

// Mark one model as default using explicit backend endpoint
export async function markModelDefault(
  projectId: string,
  providerId: string,
  model: LLMModel,
  opts?: { task_type?: 'chat' | 'embeddings' | 'tools' }
): Promise<LLMModel> {
  const base = `/api/v1/admin/llm/providers/${providerId}/models/${model.id}:mark-default`
  const path = withProject(projectId)(opts?.task_type ? `${base}&task_type=${encodeURIComponent(opts.task_type)}` : base)
  const res = await api.patch(path)
  return res.data as LLMModel
}

// ---- Task defaults (read) ----
export async function listProviderTaskDefaults(projectId: string, providerId: string): Promise<ProviderTaskDefaultOut[]> {
  const res = await api.get(withProject(projectId)(`/api/v1/admin/llm/providers/${providerId}/task-defaults`))
  return (res.data as ProviderTaskDefaultOut[]) || []
}

// ---- Audit (recent) ----
export async function listRecentAudit(projectId: string, opts?: { limit?: number; action_prefix?: string }): Promise<AuditEventItem[]> {
  const qp = new URLSearchParams({ project_id: projectId })
  if (opts?.limit) qp.set('limit', String(opts.limit))
  if (opts?.action_prefix) qp.set('action_prefix', opts.action_prefix)
  const res = await api.get(`/api/v1/admin/llm/audit/recent?${qp.toString()}`)
  return (res.data as AuditEventItem[]) || []
}
