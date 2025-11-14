import { useEffect, useMemo, useState } from 'react'
import { Alert, Badge, Button, Spinner, Table, Form, Row, Col } from 'react-bootstrap'
import { useParams } from 'react-router-dom'
import { getRequest, listArtifacts, signArtifact, type Artifact, type Request } from '../services/requests'

export default function RequestDetailPage() {
  const { projectId, requestId } = useParams<{ projectId: string; requestId: string }>()
  const [req, setReq] = useState<Request | null>(null)
  const [arts, setArts] = useState<Artifact[]>([])
  const [error, setError] = useState<string | null>(null)
  const [fmt, setFmt] = useState<'all' | Artifact['format']>('all')
  const [fromDate, setFromDate] = useState<string>('')
  const [toDate, setToDate] = useState<string>('')

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
      <Form className="mb-2" role="search" aria-label="Filter artifacts">
        <Row className="g-2 align-items-end">
          <Col xs="auto">
            <Form.Label className="small mb-1">Format</Form.Label>
            <Form.Select value={fmt} onChange={(e) => setFmt((e.currentTarget.value as 'all' | Artifact['format']))} size="sm" aria-label="Filter by format">
              <option value="all">All</option>
              <option value="csv">CSV</option>
              <option value="parquet">Parquet</option>
              <option value="xlsx">XLSX</option>
              <option value="jsonl">JSONL</option>
            </Form.Select>
          </Col>
          <Col xs="auto">
            <Form.Label className="small mb-1">From</Form.Label>
            <Form.Control type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} size="sm" aria-label="From date" />
          </Col>
          <Col xs="auto">
            <Form.Label className="small mb-1">To</Form.Label>
            <Form.Control type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} size="sm" aria-label="To date" />
          </Col>
          <Col xs="auto">
            <Button size="sm" variant="outline-secondary" onClick={() => { setFmt('all'); setFromDate(''); setToDate('') }}>Reset</Button>
          </Col>
        </Row>
      </Form>
      {(fmt !== 'all' || fromDate || toDate) && (
        <div className="mb-2 small d-flex align-items-center gap-2">
          <span className="text-muted">Active filters:</span>
          {fmt !== 'all' && <Badge bg="secondary" title="Format">Format: {fmt.toUpperCase()}</Badge>}
          {fromDate && <Badge bg="secondary" title="From date">From: {fromDate}</Badge>}
          {toDate && <Badge bg="secondary" title="To date">To: {toDate}</Badge>}
          <Button size="sm" variant="link" onClick={() => { setFmt('all'); setFromDate(''); setToDate('') }} aria-label="Clear all filters">Clear</Button>
        </div>
      )}
      <Table bordered size="sm">
        <thead>
          <tr>
            <th>Format</th>
            <th>Size</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {(() => {
            const filtered = arts
              .filter((a) => (fmt === 'all' ? true : a.format === fmt))
              .filter((a) => {
                if (!fromDate && !toDate) return true
                const d = new Date(a.created_at)
                const startOk = fromDate ? d >= new Date(fromDate) : true
                const endOk = toDate ? d <= new Date(toDate + 'T23:59:59') : true
                return startOk && endOk
              })
            if (filtered.length === 0) {
              return (<tr><td colSpan={4} className="text-muted text-center">No artifacts yet</td></tr>)
            }
            return filtered.map((a) => (
            <tr key={a.id}>
              <td>{a.format.toUpperCase()}</td>
              <td>{a.size_bytes}</td>
              <td>{new Date(a.created_at).toLocaleString()}</td>
              <td>
                <Button size="sm" variant="outline-primary" onClick={async () => {
                  try {
                    const resp = await signArtifact(a.request_id, a.id)
                    const url = resp.url || a.storage_uri
                    window.open(url, '_blank', 'noopener,noreferrer')
                  } catch (e) {
                    // fallback to storage_uri if signing fails
                    window.open(a.storage_uri, '_blank', 'noopener,noreferrer')
                  }
                }}>Get Signed URL</Button>
              </td>
            </tr>
            ))
          })()}
        </tbody>
      </Table>
    </div>
  )
}
