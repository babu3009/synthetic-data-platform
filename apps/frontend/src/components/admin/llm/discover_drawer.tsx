import React from 'react'
import { Offcanvas, Button, Table, Badge, Spinner } from 'react-bootstrap'
import { useDiscoverModels, useMarkModelDefault } from '../../../hooks/use_llm_admin'
import type { LLMModel } from '../../../services/llm_admin'

interface Props {
  projectId: string
  providerId: string
  show: boolean
  onHide: () => void
}

export function DiscoverDrawer({ projectId, providerId, show, onHide }: Props) {
  const discoverMut = useDiscoverModels(projectId, providerId)
  const markDefaultMut = useMarkModelDefault(projectId, providerId)
  const [models, setModels] = React.useState<LLMModel[]>([])

  React.useEffect(() => {
    if (show && providerId) {
      discoverMut.mutate(undefined, {
        onSuccess: (resp) => setModels(resp.models),
      })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [show, providerId])

  const markDefault = (m: LLMModel) => {
    markDefaultMut.mutate(m, {
      onSuccess: (updated) => {
        setModels((prev) => prev.map((x) => ({ ...x, is_default: x.id === updated.id })))
      },
    })
  }

  return (
    <Offcanvas show={show} onHide={onHide} placement="end" backdrop="static">
      <Offcanvas.Header closeButton>
        <Offcanvas.Title>Discover Models</Offcanvas.Title>
      </Offcanvas.Header>
      <Offcanvas.Body>
        {discoverMut.isPending && (
          <div className="d-flex align-items-center gap-2">
            <Spinner size="sm" /> <span>Fetching models...</span>
          </div>
        )}
        {discoverMut.isError && (
          <div className="text-danger small mb-2">Error discovering models</div>
        )}
        {!discoverMut.isPending && models.length === 0 && (
          <div className="text-muted">No models discovered.</div>
        )}
        {models.length > 0 && (
          <Table striped size="sm" hover>
            <thead>
              <tr>
                <th>Name</th>
                <th>Context</th>
                <th>JSON</th>
                <th>Default</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {models.map((m) => (
                <tr key={m.id}>
                  <td>{m.display_name || m.name}</td>
                  <td>{m.context_tokens || '—'}</td>
                  <td>{m.supports_json ? <Badge bg="success">Yes</Badge> : <Badge bg="secondary">No</Badge>}</td>
                  <td>{m.is_default ? <Badge bg="primary">Default</Badge> : '—'}</td>
                  <td className="text-end">
                    {!m.is_default && (
                      <Button
                        size="sm"
                        variant="outline-primary"
                        disabled={markDefaultMut.isPending}
                        onClick={() => markDefault(m)}
                      >
                        {markDefaultMut.isPending ? '...' : 'Make Default'}
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
        {discoverMut.data && (
          <div className="mt-3 small text-muted">
            Added: {discoverMut.data.added_count} • Updated: {discoverMut.data.updated_count} • Unchanged: {discoverMut.data.unchanged_count}
          </div>
        )}
      </Offcanvas.Body>
    </Offcanvas>
  )
}
