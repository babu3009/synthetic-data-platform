import { Alert, Card } from 'react-bootstrap'
import { useWizard } from '../../state/wizard'

export default function DiagramPage() {
  const { state } = useWizard()
  const entity = state.entities.find((e) => e.id === state.selectedEntityId)
  if (!entity) return <Alert variant="info">Select or create an entity to view its diagram.</Alert>

  // Placeholder: Just render tables overview for now
  return (
    <div>
      <h5 className="mb-3">{entity.name}</h5>
      <div className="d-flex flex-wrap gap-3">
        {entity.tables.map((t) => (
          <Card key={t.name}>
            <Card.Header>
              <strong>{t.name}</strong>
            </Card.Header>
            <Card.Body>
              <ul className="mb-0">
                {t.columns.map((c) => (
                  <li key={c.name}>
                    {c.name} <small className="text-muted">({c.dtype}{c.nullable ? ', nullable' : ''})</small>
                  </li>
                ))}
              </ul>
            </Card.Body>
          </Card>
        ))}
      </div>
    </div>
  )
}
