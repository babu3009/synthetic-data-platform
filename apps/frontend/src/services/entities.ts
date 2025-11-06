import api from './api'
import type { EntitySchema, EntitySchemaCreate, EntitySchemaUpdate } from '../types/schema'

export async function autosaveEntity(projectId: string | undefined, entity: EntitySchema) {
  // Backend endpoint not finalized yet; persist to localStorage as a safe fallback.
  try {
    const key = `autosave:${projectId || 'default'}:${entity.id}`
    localStorage.setItem(key, JSON.stringify(entity))
  } catch (e) {
    // noop
  }
  // If/when backend exists, uncomment and adapt:
  // try {
  //   await api.put(`/api/v1/projects/${projectId}/entities/${entity.id}`, entity)
  // } catch (e) { /* ignore for autosave */ }
}

export async function listEntities(projectId: string) {
  const res = await api.get(`/api/v1/projects/${projectId}/entities`)
  return res.data as EntitySchema[]
}

export async function getEntity(projectId: string, entityId: string) {
  const res = await api.get(`/api/v1/projects/${projectId}/entities/${entityId}`)
  return res.data as EntitySchema
}

export async function createEntity(projectId: string, payload: EntitySchemaCreate) {
  const res = await api.post(`/api/v1/projects/${projectId}/entities`, payload)
  return res.data as EntitySchema
}

export async function updateEntity(projectId: string, entityId: string, patch: EntitySchemaUpdate) {
  const res = await api.put(`/api/v1/projects/${projectId}/entities/${entityId}`, patch)
  return res.data as EntitySchema
}

export async function deleteEntity(projectId: string, entityId: string) {
  await api.delete(`/api/v1/projects/${projectId}/entities/${entityId}`)
  return { id: entityId }
}
