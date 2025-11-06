import { useEffect, useState } from 'react'
import { Modal, Button, Form } from 'react-bootstrap'
import { Column } from '../../state/wizard'

type Props = {
  show: boolean
  column?: Column
  onSave: (patch: Column) => void
  onHide: () => void
}

export default function ColumnEditorModal({ show, column, onSave, onHide }: Props) {
  const [state, setState] = useState<Column | null>(null)
  useEffect(() => {
    setState(column ? { ...column } : null)
  }, [column])

  if (!state) return null
  return (
    <Modal show={show} onHide={onHide} backdrop="static">
      <Modal.Header closeButton>
        <Modal.Title>Edit Column: {state.name}</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <Form.Group className="mb-2">
          <Form.Label>Data type</Form.Label>
          <Form.Select value={state.dtype} onChange={(e) => setState({ ...state, dtype: e.target.value })}>
            <option value="uuid">uuid</option>
            <option value="text">text</option>
            <option value="varchar">varchar</option>
            <option value="int">int</option>
            <option value="bigint">bigint</option>
            <option value="numeric">numeric</option>
            <option value="timestamp">timestamp</option>
            <option value="date">date</option>
            <option value="bool">bool</option>
          </Form.Select>
        </Form.Group>
        <Form.Group className="mb-2">
          <Form.Check
            type="switch"
            label="Nullable"
            checked={!!state.nullable}
            onChange={(e) => setState({ ...state, nullable: e.target.checked })}
          />
        </Form.Group>
        <Form.Group className="mb-2">
          <Form.Check type="switch" label="PII" checked={!!state.pii} onChange={(e) => setState({ ...state, pii: e.target.checked })} />
        </Form.Group>
        <Form.Group className="mb-2">
          <Form.Label>Regex</Form.Label>
          <Form.Control value={state.regex || ''} onChange={(e) => setState({ ...state, regex: e.target.value })} />
        </Form.Group>
        <Form.Group className="mb-2">
          <Form.Label>Distribution</Form.Label>
          <Form.Control placeholder="e.g., normal(mu=0,sigma=1) or categorical(a:0.7,b:0.3)" value={state.distribution || ''} onChange={(e) => setState({ ...state, distribution: e.target.value })} />
        </Form.Group>
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={onHide}>
          Cancel
        </Button>
        <Button onClick={() => onSave(state)}>Save</Button>
      </Modal.Footer>
    </Modal>
  )
}
