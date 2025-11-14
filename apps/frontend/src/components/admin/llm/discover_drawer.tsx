import React from 'react'
import { Offcanvas, Button, Table, Badge, Spinner, Alert } from 'react-bootstrap'
import { useDiscoverModels, useMarkModelDefault, useLlmModels } from '../../../hooks/use_llm_admin'
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
  const [badges, setBadges] = React.useState<Record<string, 'New' | 'Updated' | undefined>>({})
  const [rateLimited, setRateLimited] = React.useState<{ retryIn: number } | null>(null)
  const baselineQ = useLlmModels(projectId, providerId)

  React.useEffect(() => {
    if (show && providerId) {
      // capture baseline for badges
      const baseline = new Map<string, LLMModel>((baselineQ.data || []).map((m) => [m.id, m]))
      discoverMut.mutate(undefined, {
        onSuccess: (resp) => {
          setModels(resp.models)
          const next: Record<string, 'New' | 'Updated' | undefined> = {}
          for (const m of resp.models) {
            const prev = baseline.get(m.id)
            if (!prev) next[m.id] = 'New'
            else if (
              prev.display_name !== m.display_name ||
              prev.context_tokens !== m.context_tokens ||
              !!prev.supports_json !== !!m.supports_json ||
              JSON.stringify(prev.metadata_json || {}) !== JSON.stringify(m.metadata_json || {})
            ) next[m.id] = 'Updated'
          }
          setBadges(next)
        },
        onError: (err: unknown) => {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const anyErr = err as any
          const status = anyErr?.response?.status
          if (status === 429) {
            // Simple backoff retry once after 5s
            let t = 5
            setRateLimited({ retryIn: t })
            const id = setInterval(() => {
              t -= 1
              if (t <= 0) {
                clearInterval(id)
                setRateLimited(null)
                discoverMut.mutate(undefined, { onSuccess: (resp) => setModels(resp.models) })
              } else {
                setRateLimited({ retryIn: t })
              }
            }, 1000)
          }
        },
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
      <Offcanvas.Body aria-busy={discoverMut.isPending}>
        <div role="status" aria-live="polite" className="visually-hidden"></div>
        {discoverMut.isPending && (
          <>
            <div className="d-flex align-items-center gap-2 mb-2">
              <Spinner size="sm" /> <span>Discovering models...</span>
            </div>
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
                {Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i}>
                    <td><span className="placeholder col-8" /></td>
                    <td><span className="placeholder col-4" /></td>
                    <td><span className="placeholder col-2" /></td>
                    <td><span className="placeholder col-3" /></td>
                    <td className="text-end"><span className="placeholder col-4" /></td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </>
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
                  <td>
                    <span>{m.display_name || m.name}</span>
                    {badges[m.id] && (
                      <Badge bg={badges[m.id] === 'New' ? 'success' : 'warning'} className="ms-2">{badges[m.id]}</Badge>
                    )}
                  </td>
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
        {rateLimited && (
          <Alert variant="warning" className="mt-2">Rate limited. Will retry in {rateLimited.retryIn}s…</Alert>
        )}
        {discoverMut.data && (
          <div className="mt-3 small text-muted">
            Added: {discoverMut.data.added_count} • Updated: {discoverMut.data.updated_count} • Unchanged: {discoverMut.data.unchanged_count}
            <div className="mt-2">
              <Button size="sm" variant="outline-primary" onClick={() => discoverMut.mutate(undefined, { onSuccess: (resp) => setModels(resp.models) })} disabled={discoverMut.isPending}>
                {discoverMut.isPending ? 'Discovering…' : 'Run Discover Again'}
              </Button>
            </div>
          </div>
        )}
      </Offcanvas.Body>
    </Offcanvas>
  )
}
