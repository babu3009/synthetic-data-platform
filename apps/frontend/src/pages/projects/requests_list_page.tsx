import { useEffect, useState, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Badge, Button, Modal, ProgressBar, Spinner, Table } from 'react-bootstrap'
import { listRequests, deleteRequest, startRequest, restartRequest, type Request } from '../../services/requests'

const statusVariant: Record<Request['status'], string> = {
  pending: 'secondary',
  running: 'primary',
  completed: 'success',
  failed: 'danger',
  cancelled: 'warning',
}

export default function RequestsListPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const pid = projectId!
  
  const [requests, setRequests] = useState<Request[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedError, setSelectedError] = useState<{ message: string; traceback: string } | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<{ id: string; alias?: string } | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [starting, setStarting] = useState<string | null>(null)
  const [restarting, setRestarting] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  
  // Fetch initial requests
  useEffect(() => {
    if (!pid) return
    
    const fetchRequests = async () => {
      try {
        setLoading(true)
        const data = await listRequests(pid, { page: 1, pageSize: 100 })
        setRequests(data)
        setError(null)
      } catch (e: unknown) {
        setError((e as Error).message || 'Failed to load requests')
      } finally {
        setLoading(false)
      }
    }
    
    fetchRequests()
  }, [pid])
  
  // Set up single WebSocket connection for all requests in this project
  useEffect(() => {
    if (!pid) return
    
    // Only connect if there are active requests
    const hasActiveRequests = requests.some(r => r.status === 'pending' || r.status === 'running')
    
    if (!hasActiveRequests) {
      // Clean up existing connection if no active requests
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
      return
    }
    
    // Don't reconnect if already connected
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      return
    }
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.hostname}:8000/api/v1/ws/projects/${pid}/requests`
    
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws
    
    ws.onopen = () => {
      console.log('WebSocket connected for project requests')
    }
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        if (data.type === 'status' && data.request) {
          const updatedRequest = data.request
          setRequests(prev => prev.map(r => 
            r.id === updatedRequest.id ? { 
              ...r, 
              alias: updatedRequest.alias || r.alias,
              status: updatedRequest.status,
              error_message: updatedRequest.error_message,
              started_at: updatedRequest.started_at || r.started_at,
              finished_at: updatedRequest.finished_at || r.finished_at,
            } : r
          ))
        } else if (data.type === 'heartbeat') {
          // Heartbeat received, connection is healthy
          console.debug('WebSocket heartbeat:', data.active_count, 'active requests')
        } else if (data.type === 'error') {
          console.error('WebSocket error:', data.message)
        }
      } catch (e) {
        console.error('WebSocket message parse error:', e)
      }
    }
    
    ws.onerror = (event) => {
      console.error('WebSocket connection error:', event)
    }
    
    ws.onclose = () => {
      console.log('WebSocket disconnected')
      wsRef.current = null
    }
    
    return () => {
      // Cleanup WebSocket connection on unmount
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [pid, requests.some(r => r.status === 'pending' || r.status === 'running')])
  
  const handleDelete = async () => {
    if (!deleteConfirm) return
    
    try {
      setDeleting(true)
      await deleteRequest(pid, deleteConfirm.id)
      // Remove from local state
      setRequests(prev => prev.filter(r => r.id !== deleteConfirm.id))
      setDeleteConfirm(null)
    } catch (e: unknown) {
      alert(`Failed to delete request: ${(e as Error).message}`)
    } finally {
      setDeleting(false)
    }
  }

  const handleStart = async (requestId: string) => {
    try {
      setStarting(requestId)
      await startRequest(pid, requestId)
      // Update status optimistically
      setRequests(prev => prev.map(r => 
        r.id === requestId ? { ...r, status: 'running' as const } : r
      ))
    } catch (e: unknown) {
      alert(`Failed to start request: ${(e as Error).message}`)
    } finally {
      setStarting(null)
    }
  }

  const handleRestart = async (requestId: string) => {
    try {
      setRestarting(requestId)
      const newRequest = await restartRequest(pid, requestId)
      // Add the new request to the list and start it immediately
      setRequests(prev => [newRequest, ...prev])
      // Auto-start the new request
      await startRequest(pid, newRequest.id)
      setRequests(prev => prev.map(r => 
        r.id === newRequest.id ? { ...r, status: 'running' as const } : r
      ))
    } catch (e: unknown) {
      alert(`Failed to restart request: ${(e as Error).message}`)
    } finally {
      setRestarting(null)
    }
  }
  
  const getQueuePosition = (req: Request) => {
    if (req.status !== 'pending') return null
    const pendingRequests = requests
      .filter(r => r.status === 'pending')
      .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
    return pendingRequests.findIndex(r => r.id === req.id) + 1
  }
  
  const getProgress = (req: Request) => {
    if (req.status === 'completed') return 100
    if (req.status === 'running') {
      // Calculate rough progress based on time elapsed (assuming average 5 min job)
      if (req.started_at) {
        const elapsed = Date.now() - new Date(req.started_at).getTime()
        const estimatedDuration = 5 * 60 * 1000 // 5 minutes
        const progress = Math.min(95, Math.floor((elapsed / estimatedDuration) * 100))
        return progress
      }
      return 10
    }
    if (req.status === 'failed') return 100
    return 0
  }
  
  const renderStatus = (req: Request) => {
    const queuePos = getQueuePosition(req)
    const progress = getProgress(req)
    
    if (req.status === 'pending' && queuePos) {
      return (
        <div className="d-flex align-items-center gap-2">
          <Badge bg={statusVariant[req.status]}>Waiting #{queuePos}</Badge>
        </div>
      )
    }
    
    if (req.status === 'running') {
      return (
        <div>
          <div className="d-flex align-items-center gap-2 mb-1">
            <Badge bg={statusVariant[req.status]}>Running</Badge>
            <span className="small text-muted">{progress}%</span>
          </div>
          <ProgressBar now={progress} style={{ height: '4px' }} animated />
        </div>
      )
    }
    
    if (req.status === 'failed') {
      return (
        <div className="d-flex align-items-center gap-2">
          <Badge bg={statusVariant[req.status]}>Failed</Badge>
          <Button 
            size="sm" 
            variant="outline-danger" 
            onClick={() => setSelectedError({
              message: req.error_message || 'No error message',
              traceback: req.error_traceback || 'No traceback available'
            })}
          >
            <i className="bi bi-flag"></i>
          </Button>
        </div>
      )
    }
    
    return <Badge bg={statusVariant[req.status]}>{req.status}</Badge>
  }
  
  if (loading) {
    return (
      <div className="container py-4">
        <h2 className="mb-3">Requests</h2>
        <div className="d-flex align-items-center gap-2">
          <Spinner animation="border" size="sm" />
          <span>Loading requests...</span>
        </div>
      </div>
    )
  }
  
  return (
    <div className="container py-4">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h2 className="mb-0">Requests</h2>
        <div className="d-flex align-items-center gap-2">
          <span className="small text-muted">
            {requests.filter(r => r.status === 'running').length} running
            {' • '}
            {requests.filter(r => r.status === 'pending').length} pending
          </span>
        </div>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}

      <Table hover className="align-middle">
        <thead>
          <tr>
            <th>Name / ID</th>
            <th>Type</th>
            <th style={{ width: '250px' }}>Status</th>
            <th>Created</th>
            <th>Duration</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {requests.length === 0 ? (
            <tr><td colSpan={6} className="text-muted text-center">No requests found.</td></tr>
          ) : requests.map(r => (
            <tr key={r.id}>
              <td>
                {r.alias && <div className="fw-bold text-primary">{r.alias}</div>}
                <code className="small text-muted">{r.id.substring(0, 8)}</code>
              </td>
              <td><span className="badge bg-light text-dark">{r.type}</span></td>
              <td>{renderStatus(r)}</td>
              <td><span className="small">{new Date(r.created_at).toLocaleString()}</span></td>
              <td>
                <span className="small text-muted">
                  {r.finished_at && r.started_at ? (
                    `${Math.round((new Date(r.finished_at).getTime() - new Date(r.started_at).getTime()) / 1000)}s`
                  ) : r.started_at ? (
                    `${Math.round((Date.now() - new Date(r.started_at).getTime()) / 1000)}s`
                  ) : '—'}
                </span>
              </td>
              <td className="text-end">
                <div className="d-flex gap-2 justify-content-end">
                  {r.status === 'pending' && (
                    <Button 
                      size="sm" 
                      variant="outline-success" 
                      onClick={() => handleStart(r.id)}
                      disabled={starting === r.id}
                      title="Start request execution"
                    >
                      {starting === r.id ? (
                        <>
                          <Spinner as="span" animation="border" size="sm" className="me-1" />
                          Starting...
                        </>
                      ) : (
                        <>
                          <i className="bi bi-play-fill"></i> Start
                        </>
                      )}
                    </Button>
                  )}
                  {(r.status === 'completed' || r.status === 'failed') && (
                    <Button 
                      size="sm" 
                      variant="outline-info" 
                      onClick={() => handleRestart(r.id)}
                      disabled={restarting === r.id}
                      title="Restart with new seed to generate new data"
                    >
                      {restarting === r.id ? (
                        <>
                          <Spinner as="span" animation="border" size="sm" className="me-1" />
                          Restarting...
                        </>
                      ) : (
                        <>
                          <i className="bi bi-arrow-clockwise"></i> Restart
                        </>
                      )}
                    </Button>
                  )}
                  <Link className="btn btn-sm btn-outline-primary" to={`/projects/${pid}/requests/${r.id}`}>
                    View
                  </Link>
                  <Button 
                    size="sm" 
                    variant="outline-danger" 
                    onClick={() => setDeleteConfirm({ id: r.id, alias: r.alias })}
                    disabled={r.status === 'running'}
                    title={r.status === 'running' ? 'Cannot delete running request' : 'Delete request'}
                  >
                    <i className="bi bi-trash"></i>
                  </Button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
      
      {/* Error Details Modal */}
      <Modal show={!!selectedError} onHide={() => setSelectedError(null)} size="lg">
        <Modal.Header closeButton>
          <Modal.Title>Error Details</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <div className="mb-3">
            <strong>Error Message:</strong>
            <div className="alert alert-danger mt-2">{selectedError?.message}</div>
          </div>
          <div>
            <strong>Stack Trace:</strong>
            <pre className="bg-light p-3 mt-2" style={{ fontSize: '0.85rem', maxHeight: '400px', overflow: 'auto' }}>
              {selectedError?.traceback}
            </pre>
          </div>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setSelectedError(null)}>
            Close
          </Button>
        </Modal.Footer>
      </Modal>
      
      {/* Delete Confirmation Modal */}
      <Modal show={!!deleteConfirm} onHide={() => setDeleteConfirm(null)}>
        <Modal.Header closeButton>
          <Modal.Title>Delete Request</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <p>Are you sure you want to delete this request?</p>
          {deleteConfirm?.alias && <p className="fw-bold text-primary">{deleteConfirm.alias}</p>}
          <p className="small text-muted">
            <code>{deleteConfirm?.id}</code>
          </p>
          <p className="text-danger small">This action cannot be undone. All associated artifacts will also be deleted.</p>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setDeleteConfirm(null)} disabled={deleting}>
            Cancel
          </Button>
          <Button variant="danger" onClick={handleDelete} disabled={deleting}>
            {deleting ? (
              <>
                <Spinner as="span" animation="border" size="sm" className="me-2" />
                Deleting...
              </>
            ) : (
              'Delete'
            )}
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  )
}
