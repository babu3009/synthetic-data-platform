import { useEffect, useMemo, useState, useRef } from 'react'
import { Alert, Badge, Button, Spinner, Table, Form, Row, Col, ProgressBar, Modal } from 'react-bootstrap'
import { useParams } from 'react-router-dom'
import { signArtifact, getRequest, startRequest, listArtifacts, type Artifact, type Request } from '../services/requests'

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
  const [starting, setStarting] = useState(false)
  const [showErrorModal, setShowErrorModal] = useState(false)
  const [progress, setProgress] = useState(0)
  const [refreshing, setRefreshing] = useState(false)
  
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

  const progressPercent = useMemo(() => {
    // Use WebSocket progress if available (real-time), otherwise fall back to params_json
    if (progress > 0) return progress
    if (!req?.params_json) return 0
    const paramProgress = req.params_json.progress
    if (typeof paramProgress === 'number') return Math.min(100, Math.max(0, paramProgress))
    return 0
  }, [progress, req?.params_json])

  const handleStart = async () => {
    if (!projectId || !requestId) {
      setError('Missing project ID or request ID')
      return
    }
    setStarting(true)
    try {
      await startRequest(projectId, requestId)
      // Refresh the request data
      const updated = await getRequest(projectId, requestId)
      setReq(updated)
    } catch (e: unknown) {
      const err = e as Error
      // Handle validation errors from API
      if (err.message && typeof err.message === 'object') {
        setError(JSON.stringify(err.message, null, 2))
      } else {
        setError(err.message || 'Failed to start request')
      }
    } finally {
      setStarting(false)
    }
  }

  // Function to fetch artifacts
  const fetchArtifacts = async () => {
    if (!requestId) return
    try {
      const artifacts = await listArtifacts(requestId)
      setArts(artifacts)
    } catch (e: unknown) {
      console.error('Failed to fetch artifacts:', e)
    }
  }

  // Function to refresh all data
  const handleRefresh = async () => {
    if (!projectId || !requestId) return
    
    setRefreshing(true)
    setError(null)
    
    try {
      // Fetch request data
      const data = await getRequest(projectId, requestId)
      setReq(data)
      
      // Extract and set progress
      if (data.params_json && typeof data.params_json.progress === 'number') {
        setProgress(data.params_json.progress)
      }
      
      // Fetch artifacts
      await fetchArtifacts()
      
      console.log('Data refreshed successfully')
    } catch (e: unknown) {
      setError((e as Error).message || 'Failed to refresh data')
    } finally {
      setRefreshing(false)
    }
  }

  useEffect(() => {
    if (!requestId || !projectId) return

    // Fetch initial request data and artifacts
    const fetchInitialData = async () => {
      try {
        const data = await getRequest(projectId, requestId)
        setReq(data)
        
        // Initialize progress from params_json if available
        if (data.params_json && typeof data.params_json.progress === 'number') {
          setProgress(data.params_json.progress)
        }
        
        // If request is completed or failed, fetch artifacts immediately
        if (data.status === 'completed' || data.status === 'failed') {
          await fetchArtifacts()
        }
      } catch (e: unknown) {
        setError((e as Error).message || 'Failed to load request')
      }
    }

    fetchInitialData()

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
          console.log('WebSocket message received:', data.type, data.status)
          
          switch (data.type) {
            case 'status':
              // Update progress first
              if (typeof data.progress === 'number') {
                setProgress(Math.min(100, Math.max(0, data.progress)))
              }
              
              // Update request state
              setReq(prev => {
                const updated = {
                  ...prev!,
                  id: data.request_id || prev?.id || requestId!,
                  project_id: projectId!,
                  type: prev?.type || 'relational',
                  alias: data.alias || prev?.alias,
                  status: data.status,
                  error_message: data.error_message,
                  created_at: data.created_at || prev?.created_at || '',
                  started_at: data.started_at || prev?.started_at,
                  finished_at: data.finished_at || prev?.finished_at,
                  params_json: prev?.params_json || {},
                }
                
                // Update progress in params_json
                if (typeof data.progress === 'number' && updated.params_json) {
                  updated.params_json = {
                    ...updated.params_json,
                    progress: data.progress
                  }
                }
                
                return updated
              })
              
              // If completed or failed, fetch artifacts immediately
              if (data.status === 'completed' || data.status === 'failed') {
                console.log('Job finished, fetching artifacts...')
                
                if (data.status === 'completed') {
                  setProgress(100)
                }
                
                // Fetch artifacts immediately
                fetchArtifacts()
                
                // After a short delay, fetch full request to ensure we have all data
                setTimeout(() => {
                  getRequest(projectId!, requestId!).then(fullReq => {
                    console.log('Full request data fetched:', fullReq.status)
                    setReq(fullReq)
                    
                    // Update progress from full request
                    if (fullReq.params_json && typeof fullReq.params_json.progress === 'number') {
                      setProgress(fullReq.params_json.progress)
                    }
                    
                    // Fetch artifacts again to ensure we have them
                    fetchArtifacts()
                  }).catch(err => {
                    console.error('Failed to fetch full request data:', err)
                  })
                }, 1000) // Wait 1 second before fetching full data
              }
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
            
            case 'progress':
              // Handle dedicated progress messages
              if (typeof data.percent === 'number') {
                setProgress(Math.min(100, Math.max(0, data.percent)))
              }
              break
            
            case 'complete':
              console.log('Received complete message')
              setProgress(100)
              
              // Fetch artifacts and full data
              fetchArtifacts()
              
              // Fetch full request after short delay
              setTimeout(() => {
                if (projectId && requestId) {
                  getRequest(projectId, requestId).then(fullReq => {
                    console.log('Full request data after complete:', fullReq.status)
                    setReq(fullReq)
                    if (fullReq.params_json && typeof fullReq.params_json.progress === 'number') {
                      setProgress(fullReq.params_json.progress)
                    }
                    fetchArtifacts()
                  }).catch(err => {
                    console.error('Failed to fetch full request data:', err)
                  })
                }
              }, 1000)
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
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h3 className="mb-0">Request Detail</h3>
        <Button
          variant="outline-primary"
          size="sm"
          onClick={handleRefresh}
          disabled={refreshing}
        >
          {refreshing ? (
            <><Spinner animation="border" size="sm" className="me-1" />Refreshing...</>
          ) : (
            <><i className="bi bi-arrow-clockwise me-1"></i>Refresh</>
          )}
        </Button>
      </div>
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
          <div className="d-flex align-items-center gap-2 mb-2">
            <div><strong>Status:</strong> <Badge bg={statusColor}>{req.status}</Badge></div>
            {req.status === 'pending' && (
              <Button
                size="sm"
                variant="success"
                onClick={handleStart}
                disabled={starting}
              >
                {starting ? (
                  <><Spinner animation="border" size="sm" className="me-1" />Starting...</>
                ) : (
                  'Start'
                )}
              </Button>
            )}
            {req.status === 'failed' && req.error_message && (
              <Button
                size="sm"
                variant="outline-danger"
                onClick={() => setShowErrorModal(true)}
                title="View error details"
              >
                <i className="bi bi-exclamation-triangle-fill"></i> View Error
              </Button>
            )}
          </div>
          {req.created_at && <div><strong>Created:</strong> {new Date(req.created_at).toLocaleString()}</div>}
          {req.started_at && <div><strong>Started:</strong> {new Date(req.started_at).toLocaleString()}</div>}
          {req.finished_at && <div><strong>Finished:</strong> {new Date(req.finished_at).toLocaleString()}</div>}
          {(req.status === 'running' || req.status === 'completed' || (progressPercent > 0)) && (
            <div className="mt-3">
              <div className="d-flex justify-content-between align-items-center mb-1">
                <strong>Progress:</strong>
                <span className="badge bg-secondary">{progressPercent}%</span>
              </div>
              <ProgressBar 
                now={progressPercent} 
                variant={req.status === 'completed' ? 'success' : 'primary'}
                striped={req.status === 'running'}
                animated={req.status === 'running'}
                label={req.status === 'running' ? `${progressPercent}%` : ''}
              />
            </div>
          )}
          {req.status === 'failed' && req.error_message && (
            <Alert variant="danger" className="mt-2">
              <strong>Error:</strong> {req.error_message.substring(0, 200)}{req.error_message.length > 200 ? '...' : ''}
              {req.error_message.length > 200 && (
                <Button size="sm" variant="link" className="p-0 ms-2" onClick={() => setShowErrorModal(true)}>
                  View full error
                </Button>
              )}
            </Alert>
          )}
          {req.status === 'running' && (
            <Alert variant="info" className="mt-2">
              <Spinner animation="border" size="sm" className="me-2" />
              Request is currently running...
            </Alert>
          )}
          {req.status === 'pending' && (
            <Alert variant="secondary" className="mt-2">
              Request is waiting to start. Click the "Start" button above to begin processing.
            </Alert>
          )}
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

      {/* Error Details Modal */}
      <Modal show={showErrorModal} onHide={() => setShowErrorModal(false)} size="lg">
        <Modal.Header closeButton>
          <Modal.Title>
            <i className="bi bi-exclamation-triangle-fill text-danger me-2"></i>
            Error Details
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <div className="mb-3">
            <strong>Request ID:</strong>
            <div className="font-monospace small text-muted">{req?.id}</div>
          </div>
          <div className="mb-3">
            <strong>Status:</strong>
            <div><Badge bg="danger">Failed</Badge></div>
          </div>
          <div>
            <strong>Error Message:</strong>
            <pre className="alert alert-danger mt-2 text-wrap">
              {req?.error_message || 'No error message available'}
            </pre>
          </div>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowErrorModal(false)}>
            Close
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  )
}
