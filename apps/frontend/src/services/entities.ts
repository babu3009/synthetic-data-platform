import api from './api'
import type { EntitySchema, EntitySchemaCreate, EntitySchemaUpdate } from '../types/schema'

// Backend response type (snake_case)
interface EntityResponse {
  id: string
  project_id: string
  name: string
  description: string | null
  version: number
  schema: any
  rules_config: string | null
  rules_format: string | null
  created_at: string
  updated_at: string
}

// Transform backend response to frontend EntitySchema
function transformEntityResponse(data: EntityResponse): EntitySchema {
  return {
    id: data.id,
    name: data.name,
    description: data.description || undefined,
    version: data.version,
    tables: data.schema.tables || [],
    relationships: data.schema.relationships,
    layout: data.schema.layout,
    updatedAt: data.updated_at,
    rulesConfig: data.rules_config || undefined,
    rulesFormat: (data.rules_format as 'yaml' | 'json') || undefined,
  }
}

export async function autosaveEntity(projectId: string | undefined, entity: EntitySchema) {
  // Save to localStorage first (immediate, never fails)
  try {
    const key = `autosave:${projectId || 'default'}:${entity.id}`
    localStorage.setItem(key, JSON.stringify(entity))
  } catch (e) {
    // noop
  }
  
  // Then save to backend database (best effort)
  if (projectId) {
    try {
      const schema = {
        tables: entity.tables || [],
        relationships: entity.relationships,
        layout: entity.layout
      }
      await api.put(`/api/v1/projects/${projectId}/entities/${entity.id}`, {
        name: entity.name,
        description: entity.description,
        schema
      })
    } catch (error: any) {
      // If entity doesn't exist, create it
      if (error?.response?.status === 404) {
        try {
          const response = await api.post(`/api/v1/projects/${projectId}/entities`, {
            id: entity.id,
            name: entity.name,
            description: entity.description,
            schema: {
              tables: entity.tables || [],
              relationships: entity.relationships,
              layout: entity.layout
            }
          })
          
          // If backend created with different ID, update localStorage to match
          const createdId = response.data?.id
          if (createdId && createdId !== entity.id) {
            const oldKey = `autosave:${projectId}:${entity.id}`
            const newKey = `autosave:${projectId}:${createdId}`
            const data = localStorage.getItem(oldKey)
            if (data) {
              const entityData = JSON.parse(data)
              entityData.id = createdId
              localStorage.setItem(newKey, JSON.stringify(entityData))
              localStorage.removeItem(oldKey)
            }
          }
        } catch (e) {
          console.warn('Backend entity creation failed:', e)
        }
      } else {
        console.warn('Backend entity save failed:', error)
      }
    }
  }
}

export async function listEntities(projectId: string) {
  const res = await api.get(`/api/v1/projects/${projectId}/entities`)
  return (res.data as EntityResponse[]).map(transformEntityResponse)
}

export async function getEntity(projectId: string, entityId: string) {
  const res = await api.get(`/api/v1/projects/${projectId}/entities/${entityId}`)
  return transformEntityResponse(res.data as EntityResponse)
}

export async function createEntity(projectId: string, payload: EntitySchemaCreate) {
  const res = await api.post(`/api/v1/projects/${projectId}/entities`, payload)
  return transformEntityResponse(res.data as EntityResponse)
}

export async function updateEntity(projectId: string, entityId: string, patch: EntitySchemaUpdate) {
  const res = await api.put(`/api/v1/projects/${projectId}/entities/${entityId}`, patch)
  return transformEntityResponse(res.data as EntityResponse)
}

export async function deleteEntity(projectId: string, entityId: string) {
  await api.delete(`/api/v1/projects/${projectId}/entities/${entityId}`)
  return { id: entityId }
}
