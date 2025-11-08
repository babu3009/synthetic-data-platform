import { useState, useEffect } from 'react'
import { Modal, Button, Form } from 'react-bootstrap'
import { useProjects } from '../hooks/use_projects'

type Props = {
  show: boolean
  onClose: () => void
  onSelect: (projectId: string) => void
}

export default function ProjectSelectorModal({ show, onClose, onSelect }: Props) {
  const { data, isLoading, isError } = useProjects()
  const [selected, setSelected] = useState<string>('')

  useEffect(() => {
    if (data && data.length > 0 && !selected) setSelected(data[0].id)
  }, [data, selected])

  return (
  <Modal show={show} onHide={onClose} backdrop="static" centered animation={false}>
      <Modal.Header closeButton>
        <Modal.Title>Select a project</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        {isLoading && <div>Loading projects…</div>}
        {isError && <div className="text-danger">Failed to load projects.</div>}
        {!isLoading && !isError && (
          <Form>
            <Form.Group>
              <Form.Label id="projectSelectLabel" htmlFor="projectSelect">Project</Form.Label>
              <Form.Select
                id="projectSelect"
                aria-label="Project select"
                aria-describedby="projectSelectLabel"
                title="Project select"
                value={selected}
                onChange={(e) => setSelected(e.currentTarget.value)}
              >
                {(data || []).map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </Form.Select>
            </Form.Group>
          </Form>
        )}
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button
          variant="primary"
          disabled={!selected}
          onClick={() => {
            if (selected) onSelect(selected)
          }}
        >
          Go
        </Button>
      </Modal.Footer>
    </Modal>
  )
}
