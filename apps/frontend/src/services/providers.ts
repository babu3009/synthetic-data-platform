import api from './api'
import type { EntitySchema } from '../state/wizard'

export type ProviderSuggestion = {
  table: string
  column: string
  provider?:
    | 'faker'
    | 'pattern'
    | 'sequence'
    | 'categorical'
    | 'expression'
    | 'geo'
    | 'checksum-valid'
    | 'reference'
    | 'empirical'
  providerConfig?: Record<string, unknown>
  pii?: boolean
  piiSubtype?: 'email' | 'phone' | 'address' | 'national_id' | 'credit_card' | 'dob' | 'ip' | 'device'
}

export async function inferProviders(projectId: string, entity: EntitySchema, headers?: Record<string, string>) {
  // Backend: try /api/v1 path; if it fails, propagate error
  const res = await api.post(`/api/v1/projects/${projectId}/infer/providers`, { entity }, { headers })
  return (res.data?.suggestions || []) as ProviderSuggestion[]
}

// Best-effort persistence of provider configs for an entity
export async function saveProviders(
  projectId: string,
  entityId: string,
  providers: ProviderSuggestion[],
  headers?: Record<string, string>
) {
  try {
    const res = await api.put(`/api/v1/projects/${projectId}/entities/${entityId}/providers`, { providers }, { headers })
    return res.data
  } catch (e) {
    // Fallback to localStorage to avoid data loss
    try {
      const key = `providers:${projectId}:${entityId}`
      localStorage.setItem(key, JSON.stringify(providers))
    } catch (_) {
      // ignore
    }
    throw e
  }
}
