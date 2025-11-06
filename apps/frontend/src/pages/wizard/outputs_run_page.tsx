import { useMemo, useState } from 'react'
import { Alert, Button, Col, Form, Row, Table } from 'react-bootstrap'
import { useNavigate } from 'react-router-dom'
import { useWizard } from '../../state/wizard'
import type { EntitySchema } from '../../state/wizard'
import { createRequest, estimateRequest, startRequest } from '../../services/requests'

type Format = 'csv' | 'xlsx' | 'parquet' | 'jsonl'
type Destination = 'download' | 'object-store' | 'db-writeback' | 'kafka'

export default function OutputsRunPage() {
  const { state } = useWizard()
  const navigate = useNavigate()
  const entity: EntitySchema | undefined = state.entities.find((e) => e.id === state.selectedEntityId) || state.entities[0]

  const [formats, setFormats] = useState<Record<Format, boolean>>({ csv: true, xlsx: true, parquet: false, jsonl: false })
  const [destination, setDestination] = useState<Destination>('download')
  const [schedule, setSchedule] = useState<string>('') // ISO datetime-local string
  const [estimating, setEstimating] = useState(false)
  const [estimate, setEstimate] = useState<{ rows?: number; size_bytes?: number; seconds?: number } | null>(null)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const projectId = state.projectId

  const type = useMemo(() => {
    if (!entity) return 'relational'
    return (entity.tables?.length || 0) > 1 ? 'relational' : 'flat'
  }, [entity]) as 'relational' | 'flat'

  function formatsArray() {
    return (Object.keys(formats) as Format[]).filter((f) => formats[f])
  }

  async function onEstimate() {
    setError(null)
    setEstimate(null)
    if (!projectId) { setError('No project selected.'); return }
    if (!entity) { setError('No entity selected.'); return }
    try {
      setEstimating(true)
      // Create a draft request just for estimation
      const payload = {
        type,
        params_json: {
          entity,
          outputs: { formats: formatsArray(), destination },
          schedule: schedule || undefined,
        },
      }
      const req = await createRequest(projectId, payload)
      const est = await estimateRequest(projectId, req.id)
      setEstimate(est)
    } catch (e: unknown) {
      setError((e as Error)?.message || 'Failed to estimate')
    } finally {
      setEstimating(false)
    }
  }

  async function onCreateRequest() {
    setError(null)
    if (!projectId) { setError('No project selected.'); return }
    if (!entity) { setError('No entity selected.'); return }
    try {
      setCreating(true)
      const payload = {
        type,
        params_json: {
          entity,
          outputs: { formats: formatsArray(), destination },
          schedule: schedule || undefined,
        },
      }
      const req = await createRequest(projectId, payload)
      // Immediately start the request
      await startRequest(req.id)
      // Navigate to request detail page
      navigate(`/projects/${projectId}/requests/${req.id}`)
    } catch (e: unknown) {
      setError((e as Error)?.message || 'Failed to create request')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div>
      {!entity && <Alert variant="info">Select or create an entity first.</Alert>}
      {!projectId && <Alert variant="warning">No project selected. Open the Wizard with a projectId query parameter.</Alert>}
      {error && <Alert variant="danger">{error}</Alert>}

      <Row className="mb-3">
        <Col md={6}>
          <Form.Group controlId="formats">
            <Form.Label>Output formats</Form.Label>
            <div className="d-flex flex-wrap gap-3">
              {(['csv','xlsx','parquet','jsonl'] as Format[]).map((f) => (
                <Form.Check key={f} type="checkbox" id={`fmt-${f}`} label={f.toUpperCase()} checked={formats[f]} onChange={(e) => setFormats((prev) => ({ ...prev, [f]: e.target.checked }))} />
              ))}
            </div>
          </Form.Group>
        </Col>
        <Col md={6}>
          <Form.Group controlId="destination">
            <Form.Label>Destination</Form.Label>
            <Form.Select value={destination} onChange={(e) => setDestination(e.target.value as Destination)}>
              <option value="download">Download</option>
              <option value="object-store">Object Store</option>
              <option value="db-writeback">DB Write-back</option>
              <option value="kafka">Kafka</option>
            </Form.Select>
            <Form.Text muted>
              Destination controls where artifacts are stored after generation. Download keeps files locally.
            </Form.Text>
          </Form.Group>
        </Col>
      </Row>

      <Row className="mb-3">
        <Col md={6}>
          <Form.Group controlId="schedule">
            <Form.Label>Optional schedule</Form.Label>
            <Form.Control type="datetime-local" value={schedule} onChange={(e) => setSchedule(e.target.value)} />
            <Form.Text muted>Leave empty to run immediately.</Form.Text>
          </Form.Group>
        </Col>
      </Row>

      <div className="d-flex gap-2 mb-3">
        <Button variant="secondary" onClick={onEstimate} disabled={estimating || !projectId || !entity}>{estimating ? 'Estimating…' : 'Estimate'}</Button>
        <Button variant="primary" onClick={onCreateRequest} disabled={creating || !projectId || !entity}>{creating ? 'Creating…' : 'Create Request'}</Button>
      </div>

      {estimate && (
        <div className="mt-3">
          <h6>Estimate</h6>
          <Table bordered size="sm">
            <tbody>
              <tr><td>Rows</td><td>{estimate.rows ?? '-'}</td></tr>
              <tr><td>Size (bytes)</td><td>{estimate.size_bytes ?? '-'}</td></tr>
              <tr><td>Time (s)</td><td>{estimate.seconds ?? '-'}</td></tr>
            </tbody>
          </Table>
        </div>
      )}
    </div>
  )
}
