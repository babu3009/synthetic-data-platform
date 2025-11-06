import { Button, Form, Offcanvas, OverlayTrigger, Tooltip } from 'react-bootstrap'
import { Relationship } from '../../state/wizard'

type Props = {
  show: boolean
  onHide: () => void
  relationship?: Relationship
  onChange: (rel: Relationship) => void
  onDelete: (id: string) => void
}

export default function EdgePanel({ show, onHide, relationship, onChange, onDelete }: Props) {
  if (!relationship) return null
  return (
    <Offcanvas show={show} onHide={onHide} placement="end">
      <Offcanvas.Header closeButton>
        <Offcanvas.Title>Relationship</Offcanvas.Title>
      </Offcanvas.Header>
      <Offcanvas.Body>
        <div className="mb-3">
          <Form.Label>Source</Form.Label>
          <div className="text-muted">
            {relationship.sourceTable}.{relationship.sourceColumn}
          </div>
        </div>
        <div className="mb-3">
          <Form.Label>Target</Form.Label>
          <div className="text-muted">
            {relationship.targetTable}.{relationship.targetColumn}
          </div>
        </div>
        <Form.Group controlId="cardinality" className="mb-3">
          <Form.Label>
            <span className="me-1">Cardinality</span>
            <OverlayTrigger placement="top" overlay={<Tooltip>ONE_TO_ONE, ONE_TO_MANY, or MANY_TO_MANY</Tooltip>}>
              <span role="img" aria-label="Cardinality help">❔</span>
            </OverlayTrigger>
          </Form.Label>
          <Form.Select
            value={relationship.cardinality}
            onChange={(e) => onChange({ ...relationship, cardinality: e.target.value as Relationship['cardinality'] })}
            aria-label="Relationship cardinality"
          >
            <option value="ONE_TO_ONE">ONE_TO_ONE</option>
            <option value="ONE_TO_MANY">ONE_TO_MANY</option>
            <option value="MANY_TO_MANY">MANY_TO_MANY</option>
          </Form.Select>
        </Form.Group>
        <div className="d-flex justify-content-between">
          <Button variant="outline-danger" onClick={() => onDelete(relationship.id)}>
            Delete
          </Button>
          <Button onClick={onHide}>Close</Button>
        </div>
      </Offcanvas.Body>
    </Offcanvas>
  )
}
