import { useState } from 'react'
import { Alert, Button, Spinner } from 'react-bootstrap'
import { useWizard, type EntitySchema } from '../../state/wizard'
import DiagramCanvas from '../../components/diagram/diagram_canvas'
import AddEntityModal from '../../components/entities/add_entity_modal'

export default function DiagramPage() {
  const { state, dispatch } = useWizard()
  const [showAdd, setShowAdd] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  const projectId = state.projectId || 'default'
  
  // Get the latest entity from state (not a stale reference)
  const entity = state.entities.find((e) => e.id === state.selectedEntityId) || state.entities[0]

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
