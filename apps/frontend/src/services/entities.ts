import { EntitySchema } from '../state/wizard'

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
