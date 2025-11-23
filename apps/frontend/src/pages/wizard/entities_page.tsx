import { useMemo, useState } from 'react'
import { Button, Table, Alert, ButtonGroup, Spinner } from 'react-bootstrap'
import { useWizard, isEntityNameUnique, EntitySchema } from '../../state/wizard'
import AddEntityModal from '../../components/entities/add_entity_modal'
import EditEntityModal from '../../components/entities/edit_entity_modal'
import { deleteEntity } from '../../services/entities'

export default function EntitiesPage() {
  const { state, dispatch } = useWizard()
  const [show, setShow] = useState(false)
  const [editingEntity, setEditingEntity] = useState<EntitySchema | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)

  const entities = state.entities
  const projectId = state.projectId || 'default'

  const hasUniqueNames = useMemo(() => {
    const names = new Set<string>()
    for (const e of entities) {
      const key = e.name.trim().toLowerCase()
      if (names.has(key)) return false
      names.add(key)
    }
    return true
  }, [entities])

  const onCreated = (entity: EntitySchema) => {
    if (!isEntityNameUnique(entity.name, entities)) {
      setError('Entity name must be unique within the project.')
      return
    }
    dispatch({ type: 'addEntity', entity })
    dispatch({ type: 'setActiveTab', tab: 'diagram' })
    setShow(false)
  }

  const onUpdated = (entity: EntitySchema) => {
    dispatch({ type: 'updateEntity', id: entity.id, patch: { name: entity.name, description: entity.description, tables: entity.tables } })
    setEditingEntity(null)
  }

  const handleDelete = async (id: string, name: string) => {
    if (window.confirm(`Are you sure you want to delete entity "${name}"?`)) {
      try {
        // Delete from backend if projectId exists
        if (state.projectId) {
          await deleteEntity(state.projectId, id)
        }
        
        // Delete from localStorage
        const key = `autosave:${projectId}:${id}`
        localStorage.removeItem(key)
        
        // Update wizard state
        dispatch({ type: 'deleteEntity', id })
      } catch (err) {
        console.error('Failed to delete entity:', err)
        setError(`Failed to delete entity: ${err instanceof Error ? err.message : 'Unknown error'}`)
      }
    }
  }

  const handleView = (id: string) => {
    dispatch({ type: 'setSelectedEntity', id })
    dispatch({ type: 'setActiveTab', tab: 'diagram' })
  }

  const handleSave = async () => {
    if (!hasUniqueNames) {
      setError('Cannot save: duplicate entity names detected.')
      return
    }

    setSaving(true)
    setSaveSuccess(false)
    setError(null)

    try {
      // Save entities to localStorage
      const prefix = `autosave:${projectId}:`
      
      // Clear old entities for this project
      const keysToRemove: string[] = []
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i)
        if (key?.startsWith(prefix)) {
          keysToRemove.push(key)
        }
      }
      keysToRemove.forEach(k => localStorage.removeItem(k))

      // Save each entity
      entities.forEach((entity) => {
        const key = `${prefix}${entity.id}`
        localStorage.setItem(key, JSON.stringify(entity))
      })

      dispatch({ type: 'clearDirty', savedAt: new Date().toISOString() })
      setSaveSuccess(true)
      
      // Hide success message after 3 seconds
      setTimeout(() => setSaveSuccess(false), 3000)
    } catch (e) {
      setError(`Failed to save entities: ${e instanceof Error ? e.message : 'Unknown error'}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      {error && (
        <Alert variant="danger" onClose={() => setError(null)} dismissible>
          {error}
        </Alert>
      )}
      {saveSuccess && (
        <Alert variant="success" onClose={() => setSaveSuccess(false)} dismissible>
          <i className="bi bi-check-circle me-2"></i>Entities saved successfully!
        </Alert>
      )}
      {!hasUniqueNames && <Alert variant="warning">Duplicate entity names detected. Please rename to ensure uniqueness.</Alert>}

      <div className="d-flex justify-content-between align-items-center mb-3">
        <div>
          <h5 className="mb-0 d-inline me-3">Entities</h5>
          {state.isDirty && <span className="badge bg-warning text-dark">Unsaved changes</span>}
        </div>
        <div className="d-flex gap-2">
          <Button 
            variant="success" 
            onClick={handleSave} 
            disabled={saving || entities.length === 0 || !hasUniqueNames}
          >
            {saving ? (
              <>
                <Spinner animation="border" size="sm" className="me-2" />
                Saving...
              </>
            ) : (
              <>
                <i className="bi bi-save me-2"></i>Save Entities
              </>
            )}
          </Button>
          <Button onClick={() => setShow(true)}>
            <i className="bi bi-plus-circle me-2"></i>Add Entity
          </Button>
        </div>
      </div>

      <Table striped bordered hover size="sm">
        <thead>
          <tr>
            <th>Name</th>
            <th>Description</th>
            <th>Version</th>
            <th>Tables</th>
            <th>Updated</th>
            <th style={{ width: '150px' }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {entities.length === 0 ? (
            <tr>
              <td colSpan={6} className="text-center text-muted">
                No entities yet. Click "Add Entity" to get started.
              </td>
            </tr>
          ) : (
            entities.map((e: EntitySchema) => (
              <tr key={e.id}>
                <td role="button" onClick={() => handleView(e.id)}>{e.name}</td>
                <td role="button" onClick={() => handleView(e.id)}>
                  <small className="text-muted">{e.description || '-'}</small>
                </td>
                <td role="button" onClick={() => handleView(e.id)}>
                  <span className="badge bg-secondary">v{e.version || 1}</span>
                </td>
                <td role="button" onClick={() => handleView(e.id)}>{e.tables?.length ?? 0}</td>
                <td role="button" onClick={() => handleView(e.id)}>{new Date(e.updatedAt).toLocaleString()}</td>
                <td>
                  <ButtonGroup size="sm">
                    <Button variant="outline-primary" onClick={() => handleView(e.id)} title="View">
                      <i className="bi bi-eye"></i>
                    </Button>
                    <Button variant="outline-secondary" onClick={() => setEditingEntity(e)} title="Edit">
                      <i className="bi bi-pencil"></i>
                    </Button>
                    <Button variant="outline-danger" onClick={() => handleDelete(e.id, e.name)} title="Delete">
                      <i className="bi bi-trash"></i>
                    </Button>
                  </ButtonGroup>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </Table>

      <AddEntityModal
        show={show}
        onHide={() => setShow(false)}
        projectId={projectId}
        existingNames={entities.map((e: EntitySchema) => e.name)}
        onCreated={onCreated}
      />

      {editingEntity && (
        <EditEntityModal
          show={true}
          onHide={() => setEditingEntity(null)}
          entity={editingEntity}
          existingNames={entities.filter(e => e.id !== editingEntity.id).map((e: EntitySchema) => e.name)}
          onUpdated={onUpdated}
        />
      )}
    </div>
  )
}
