import { useState } from 'react'
import { Alert, Button } from 'react-bootstrap'
import { useWizard, type EntitySchema } from '../../state/wizard'
import DiagramCanvas from '../../components/diagram/diagram_canvas'
import AddEntityModal from '../../components/entities/add_entity_modal'

export default function DiagramPage() {
  const { state, dispatch } = useWizard()
  const entity = state.entities.find((e) => e.id === state.selectedEntityId) || state.entities[0]
  const [showAdd, setShowAdd] = useState(false)

  if (!entity) return <Alert variant="info">Select or create an entity to view its diagram.</Alert>

  return (
    <div>
      <div className="mb-2 d-flex justify-content-end">
        <Button onClick={() => setShowAdd(true)}>+ New Entity</Button>
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
