import { useEffect, useMemo, useState, useRef } from 'react'
import { Alert, Badge, Button, Spinner, Table, Form, Row, Col } from 'react-bootstrap'
import { useParams } from 'react-router-dom'
import { signArtifact, type Artifact, type Request } from '../services/requests'

const WS_MAX_RETRIES = 10
const WS_RETRY_DELAY = 2000 // 2 seconds

export default function RequestDetailPage() {
  const { projectId, requestId } = useParams<{ projectId: string; requestId: string }>()
  const [req, setReq] = useState<Request | null>(null)
  const [arts, setArts] = useState<Artifact[]>([])
  const [error, setError] = useState<string | null>(null)
  const [wsError, setWsError] = useState<string | null>(null)
  const [fmt, setFmt] = useState<'all' | Artifact['format']>('all')
  const [fromDate, setFromDate] = useState<string>('')
  const [toDate, setToDate] = useState<string>('')
  
  const wsRef = useRef<WebSocket | null>(null)
  const retryCountRef = useRef(0)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const statusColor = useMemo(() => {
    switch (req?.status) {
      case 'completed': return 'success'
      case 'failed': return 'danger'
      case 'running': return 'primary'
      default: return 'secondary'
    }
  }, [req?.status])

  useEffect(() => {
    if (!requestId) return

    // Listen for logout event to cleanup WebSocket
    const handleWsCleanup = () => {
      if (wsRef.current) {
        wsRef.current.close(1000, 'User logged out')
        wsRef.current = null
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
        reconnectTimeoutRef.current = null
      }
    }

    window.addEventListener('ws:cleanup', handleWsCleanup)

    const connectWebSocket = () => {
      // Close existing connection if any
      if (wsRef.current) {
        wsRef.current.close()
      }

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${window.location.hostname}:8000/api/v1/ws/requests/${requestId}`
      
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('WebSocket connected')
        retryCountRef.current = 0 // Reset retry count on successful connection
        setWsError(null)
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          switch (data.type) {
            case 'status':
              setReq({
                id: data.request_id,
                project_id: projectId || '',
                type: req?.type || 'relational',
                alias: data.alias || req?.alias,
                status: data.status,
                created_at: data.created_at,
                started_at: data.started_at,
                finished_at: data.finished_at,
              } as Request)
              break
            
            case 'artifacts':
              setArts(data.artifacts.map((a: any) => ({
                id: a.id,
                request_id: requestId || '',
                format: a.format,
                size_bytes: a.size_bytes,
                storage_uri: a.storage_uri,
                created_at: a.created_at,
              })))
              break
            
            case 'complete':
              // Connection will close after this
              break
            
            case 'error':
              setError(data.message)
              break
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e)
        }
      }

      ws.onerror = (event) => {
        console.error('WebSocket error:', event)
      }

      ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason)
        wsRef.current = null

        // Only retry if not a normal closure and haven't exceeded max retries
        if (event.code !== 1000 && retryCountRef.current < WS_MAX_RETRIES) {
          retryCountRef.current++
          console.log(`Reconnecting... Attempt ${retryCountRef.current}/${WS_MAX_RETRIES}`)
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connectWebSocket()
          }, WS_RETRY_DELAY)
        } else if (retryCountRef.current >= WS_MAX_RETRIES) {
          setWsError('Connection lost. Please refresh the page to reconnect.')
        }
      }
    }

    connectWebSocket()

    return () => {
      // Cleanup on unmount
      window.removeEventListener('ws:cleanup', handleWsCleanup)
      
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounted')
      }
    }
  }, [requestId, projectId])

  return (
    <div className="container py-3">
      <h3>Request Detail</h3>
      {error && <Alert variant="danger">{error}</Alert>}
      {wsError && (
        <Alert variant="warning">
          {wsError}
          {retryCountRef.current >= WS_MAX_RETRIES && (
            <Button size="sm" variant="link" onClick={() => window.location.reload()}>
              Refresh Now
            </Button>
          )}
        </Alert>
      )}
      {!req && !error && (
        <div className="d-flex align-items-center gap-2"><Spinner animation="border" size="sm" /><span>Connecting…</span></div>
      )}
      {req && (
        <div className="mb-3">
          {req.alias && (
            <div className="mb-2">
              <h4 className="text-primary">{req.alias}</h4>
            </div>
          )}
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
