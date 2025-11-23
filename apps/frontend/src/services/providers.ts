import api from './api'
import type { EntitySchema } from '../types/schema'

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
  confidence?: number // 0..1 confidence score (optional)
  reason?: string // optional rationale/explanation
}

export async function inferProviders(projectId: string, entity: EntitySchema, headers?: Record<string, string>) {
  // Build columns from entity schema
  const columns = entity.tables?.flatMap(table => 
    table.columns.map(col => ({
      table: table.name,
      column: col.name,
      dtype: col.dtype
    }))
  ) || []
  
  // Backend: try /api/v1 path with entity_id for filtering
  const res = await api.post(
    `/api/v1/projects/${projectId}/infer/providers`, 
    { 
      columns,
      entity_id: entity.id 
    }, 
    { headers }
  )
  return (res.data?.results || []).flatMap((r: any) => 
    r.suggestions?.map((s: any) => ({
      table: r.table,
      column: r.column,
      provider: s.provider,
      providerConfig: s.provider_config,
      pii: s.pii?.flagged,
      piiSubtype: s.pii?.subtype,
      confidence: s.score,
      reason: s.reasons?.join('; ')
    })) || []
  ) as ProviderSuggestion[]
}

// Optional non-scoped alias for public/trial mode
export async function inferProvidersAlias(entity: EntitySchema, headers?: Record<string, string>) {
  const res = await api.post(`/api/v1/infer/providers`, { entity }, { headers })
  return (res.data?.suggestions || []) as ProviderSuggestion[]
}

// Best-effort persistence of provider configs for an entity
export async function saveProviders(
  projectId: string,
  entityId: string,
  providers: ProviderSuggestion[]
) {
  try {
    // Save to localStorage (primary storage for now)
    const key = `providers:${projectId}:${entityId}`
    localStorage.setItem(key, JSON.stringify(providers))
    
    // Also save to database via entity update
    // Build schema from providers
    const entity = JSON.parse(localStorage.getItem(`autosave:${projectId}:${entityId}`) || '{}')
    if (entity && entity.tables) {
      // Apply providers to entity schema
      const tables = entity.tables.map((table: any) => ({
        ...table,
        columns: table.columns.map((col: any) => {
          const provider = providers.find(p => p.table === table.name && p.column === col.name)
          if (provider) {
            return {
              ...col,
              provider: provider.provider,
              providerConfig: provider.providerConfig,
              pii: provider.pii,
              piiSubtype: provider.piiSubtype
            }
          }
          return col
        })
      }))
      
      // Update entity in database
      const schema = {
        tables,
        relationships: entity.relationships,
        layout: entity.layout
      }
      
      try {
        await api.put(`/api/v1/projects/${projectId}/entities/${entityId}`, {
          name: entity.name,
          schema
        })
      } catch (apiError: any) {
        // If 404, try to create
        if (apiError?.response?.status === 404 && entity.name) {
          await api.post(`/api/v1/projects/${projectId}/entities`, {
            id: entityId,
            name: entity.name,
            schema
          })
        }
      }
    }
    
    return { success: true, message: 'Providers saved successfully' }
  } catch (e) {
    console.error('Failed to save providers:', e)
    throw e
  }
}

// Lightweight autosave of provider selections without hitting backend
export function autosaveProviders(projectId: string, entityId: string, providers: ProviderSuggestion[]) {
  try {
    const key = `providers:${projectId}:${entityId}`
    localStorage.setItem(key, JSON.stringify(providers))
  } catch (_) {
    // ignore
  }
}
