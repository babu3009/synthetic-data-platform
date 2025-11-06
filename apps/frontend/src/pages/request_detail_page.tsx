import { useEffect, useMemo, useState } from 'react'
import { Alert, Badge, Button, Spinner, Table } from 'react-bootstrap'
import { useParams } from 'react-router-dom'
import { getRequest, listArtifacts, type Artifact, type Request } from '../services/requests'

export default function RequestDetailPage() {
  const { projectId, requestId } = useParams<{ projectId: string; requestId: string }>()
  const [req, setReq] = useState<Request | null>(null)
  const [arts, setArts] = useState<Artifact[]>([])
  const [error, setError] = useState<string | null>(null)

  const statusColor = useMemo(() => {
    switch (req?.status) {
      case 'completed': return 'success'
      case 'failed': return 'danger'
      case 'running': return 'primary'
      default: return 'secondary'
    }
  }, [req?.status])

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined
    async function tick() {
      try {
        if (!projectId || !requestId) return
        const r = await getRequest(projectId, requestId)
        setReq(r)
        if (r.status === 'completed' || r.status === 'failed' || r.status === 'cancelled') {
          const a = await listArtifacts(r.id)
          setArts(a)
          return // stop polling
        }
      } catch (e: unknown) {
        setError((e as Error)?.message || 'Failed to fetch request')
      }
      timer = setTimeout(tick, 2000)
    }
    tick()
    return () => { if (timer) clearTimeout(timer) }
  }, [projectId, requestId])

  return (
    <div className="container py-3">
      <h3>Request Detail</h3>
      {error && <Alert variant="danger">{error}</Alert>}
      {!req && !error && (
        <div className="d-flex align-items-center gap-2"><Spinner animation="border" size="sm" /><span>Loading…</span></div>
      )}
      {req && (
        <div className="mb-3">
          <div><strong>ID:</strong> {req.id}</div>
          <div><strong>Type:</strong> {req.type}</div>
          <div><strong>Status:</strong> <Badge bg={statusColor}>{req.status}</Badge></div>
        </div>
      )}

      <h5>Artifacts</h5>
      <Table bordered size="sm">
        <thead>
          <tr>
            <th>Format</th>
            <th>Size</th>
            <th>URI</th>
          </tr>
        </thead>
        <tbody>
          {arts.length === 0 ? (
            <tr><td colSpan={3} className="text-muted text-center">No artifacts yet</td></tr>
          ) : arts.map((a) => (
            <tr key={a.id}>
              <td>{a.format.toUpperCase()}</td>
              <td>{a.size_bytes}</td>
              <td>
                <a href={a.storage_uri} target="_blank" rel="noreferrer">
                  <Button size="sm" variant="outline-primary">Open</Button>
                </a>
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </div>
  )
}
