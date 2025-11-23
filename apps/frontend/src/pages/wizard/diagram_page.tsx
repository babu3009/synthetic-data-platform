import { useState, useEffect } from 'react'
import { Alert, Button, Form, Spinner } from 'react-bootstrap'
import { useWizard, type EntitySchema } from '../../state/wizard'
import DiagramCanvas from '../../components/diagram/diagram_canvas'
import AddEntityModal from '../../components/entities/add_entity_modal'

export default function DiagramPage() {
  const { state, dispatch } = useWizard()
  const [showAdd, setShowAdd] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [selectedEntityId, setSelectedEntityId] = useState<string | undefined>(state.selectedEntityId)

  const projectId = state.projectId || 'default'
  
  // Get the latest entity from state (not a stale reference)
  const entity = state.entities.find((e) => e.id === selectedEntityId) || state.entities[0]

  // Sync local state with wizard state
  useEffect(() => {
    if (state.selectedEntityId !== selectedEntityId) {
      setSelectedEntityId(state.selectedEntityId)
    }
  }, [state.selectedEntityId])

  // Update wizard state when local selection changes
  const handleEntityChange = (entityId: string) => {
    setSelectedEntityId(entityId)
    dispatch({ type: 'setSelectedEntity', id: entityId })
  }

  const handleSave = async () => {
    if (!entity) return

    setSaving(true)
    setSaveSuccess(false)
    setSaveError(null)

    try {
      // Get the latest entity state (includes PK, FK relationships, layout)
      const latestEntity = state.entities.find((e) => e.id === entity.id)
      if (!latestEntity) {
        throw new Error('Entity not found in state')
      }

      // Save entity to localStorage with all data
      const key = `autosave:${projectId}:${latestEntity.id}`
      localStorage.setItem(key, JSON.stringify(latestEntity))

      dispatch({ type: 'clearDirty', savedAt: new Date().toISOString() })
      setSaveSuccess(true)
      
      // Hide success message after 3 seconds
      setTimeout(() => setSaveSuccess(false), 3000)
    } catch (e) {
      setSaveError(`Failed to save: ${e instanceof Error ? e.message : 'Unknown error'}`)
    } finally {
      setSaving(false)
    }
  }

  if (!entity) return <Alert variant="info">Select or create an entity to view its diagram.</Alert>

  return (
    <div>
      {saveSuccess && (
        <Alert variant="success" onClose={() => setSaveSuccess(false)} dismissible className="mb-2">
          <i className="bi bi-check-circle me-2"></i>Diagram saved successfully!
        </Alert>
      )}
      {saveError && (
        <Alert variant="danger" onClose={() => setSaveError(null)} dismissible className="mb-2">
          {saveError}
        </Alert>
      )}
      
      {/* Entity Selection Dropdown */}
      {state.entities.length > 1 && (
        <div className="mb-3">
          <Form.Label htmlFor="entity-select" className="fw-bold">Select Entity:</Form.Label>
          <Form.Select
            id="entity-select"
            value={selectedEntityId || ''}
            onChange={(e) => handleEntityChange(e.target.value)}
            className="w-auto"
          >
            {state.entities.map((ent) => (
              <option key={ent.id} value={ent.id}>
                {ent.name} {ent.version ? `(v${ent.version})` : ''}
              </option>
            ))}
          </Form.Select>
        </div>
      )}
      
      <div className="mb-2 d-flex justify-content-between align-items-center">
        <div>
          {state.isDirty && <span className="badge bg-warning text-dark">Unsaved changes</span>}
        </div>
        <div className="d-flex gap-2">
          <Button 
            variant="success" 
            onClick={handleSave} 
            disabled={saving}
          >
            {saving ? (
              <>
                <Spinner animation="border" size="sm" className="me-2" />
                Saving...
              </>
            ) : (
              <>
                <i className="bi bi-save me-2"></i>Save
              </>
            )}
          </Button>
          <Button onClick={() => setShowAdd(true)}>
            <i className="bi bi-plus-circle me-2"></i>New Entity
          </Button>
        </div>
      </div>
      <DiagramCanvas />
      <AddEntityModal
        show={showAdd}
        onHide={() => setShowAdd(false)}
        projectId={state.projectId || 'default'}
        existingNames={state.entities.map((e: EntitySchema) => e.name)}
        onCreated={(newEntity) => {
          dispatch({ type: 'addEntity', entity: newEntity })
          dispatch({ type: 'setSelectedEntity', id: newEntity.id })
          setShowAdd(false)
        }}
      />
    </div>
  )
}
