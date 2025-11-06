import { useMemo, useState } from 'react'
import { Button, Table, Alert } from 'react-bootstrap'
import { useWizard, isEntityNameUnique, EntitySchema } from '../../state/wizard'
import AddEntityModal from '../../components/entities/add_entity_modal'

export default function EntitiesPage() {
  const { state, dispatch } = useWizard()
  const [show, setShow] = useState(false)
  const [error, setError] = useState<string | null>(null)

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

  return (
    <div>
      {error && (
        <Alert variant="danger" onClose={() => setError(null)} dismissible>
          {error}
        </Alert>
      )}
      {!hasUniqueNames && <Alert variant="warning">Duplicate entity names detected. Please rename to ensure uniqueness.</Alert>}

      <div className="d-flex justify-content-between align-items-center mb-3">
        <div>
          <h5 className="mb-0">Entities</h5>
          <small className="text-muted">Project: {projectId}</small>
        </div>
        <Button onClick={() => setShow(true)}>Add Entity</Button>
      </div>

      <Table striped bordered hover size="sm">
        <thead>
          <tr>
            <th>Name</th>
            <th>Tables</th>
            <th>Updated</th>
          </tr>
        </thead>
        <tbody>
          {entities.length === 0 ? (
            <tr>
              <td colSpan={3} className="text-center text-muted">
                No entities yet. Click "Add Entity" to get started.
              </td>
            </tr>
          ) : (
            entities.map((e: EntitySchema) => (
              <tr key={e.id} role="button" onClick={() => dispatch({ type: 'setSelectedEntity', id: e.id })}>
                <td>{e.name}</td>
                <td>{e.tables?.length ?? 0}</td>
                <td>{new Date(e.updatedAt).toLocaleString()}</td>
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
    </div>
  )
}
