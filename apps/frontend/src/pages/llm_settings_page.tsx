import React from 'react'
import { useParams } from 'react-router-dom'
import { Alert, Badge, Button, Card, Col, Collapse, Form, Row, Spinner, Table } from 'react-bootstrap'
import { useLlmProviders, useLlmModels } from '../hooks/use_llm_admin'
import { useInferProviders } from '../hooks/use_infer_providers'
import { useLlmSettings, useSaveLlmSettings } from '../hooks/use_llm_settings'
import type { EntitySchema } from '../types/schema'

// Simple role getter (OWNER, EDITOR, VIEWER)
function useRole() {
  return (localStorage.getItem('role') || 'OWNER') as 'OWNER' | 'EDITOR' | 'VIEWER'
}

const sampleEntity: EntitySchema = {
  id: 'sample',
  name: 'Sample',
  tables: [
    {
      name: 'users',
      columns: [
        { name: 'email', dtype: 'string', nullable: false, pii: true, piiSubtype: 'email' },
        { name: 'age', dtype: 'int', nullable: true },
        { name: 'country', dtype: 'string', nullable: true },
      ],
    },
  ],
}

export default function LlmSettingsPage() {
  const params = useParams()
  const projectId = params.projectId || new URLSearchParams(window.location.search).get('projectId') || ''
  const role = useRole()
  const canEdit = role === 'OWNER' || role === 'EDITOR'

  const settingsQ = useLlmSettings(projectId)
  const saveMut = useSaveLlmSettings(projectId)
  const providersQ = useLlmProviders(projectId)

  const [providerId, setProviderId] = React.useState<string | undefined>()
  const [modelId, setModelId] = React.useState<string | undefined>()
  const [showAdvanced, setShowAdvanced] = React.useState(false)
  const [testOpen, setTestOpen] = React.useState(false)

  const modelsQ = useLlmModels(projectId, providerId || '')
  const inferMut = useInferProviders(projectId)

  // Initialize selects when settings load
  React.useEffect(() => {
    if (settingsQ.data) {
      setProviderId(settingsQ.data.provider_id || undefined)
      setModelId(settingsQ.data.model_id || undefined)
    }
  }, [settingsQ.data])

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!settingsQ.data) return
    const payload = {
      ...settingsQ.data,
      provider_id: providerId || null,
      model_id: modelId || null,
    }
    saveMut.mutate(payload)
  }

  const runTest = () => {
    inferMut.mutate(sampleEntity)
    setTestOpen(true)
  }

  return (
    <div className="container mt-4">
      <h2 className="mb-3">LLM Settings</h2>
      {!projectId && <Alert variant="warning">Missing projectId context.</Alert>}
      {settingsQ.isLoading && <div className="d-flex align-items-center gap-2"><Spinner size="sm" /> <span>Loading settings…</span></div>}
      {settingsQ.isError && <Alert variant="danger">Failed to load settings.</Alert>}
      {settingsQ.data && (
        <Form onSubmit={onSubmit}>
          <Card className="mb-3">
            <Card.Header className="d-flex justify-content-between align-items-center">
              <span>General</span>
              <Form.Check
                type="switch"
                id="llm-enabled"
                label={settingsQ.data.enabled ? 'Enabled' : 'Disabled'}
                checked={settingsQ.data.enabled}
                disabled={!canEdit || saveMut.isPending}
                onChange={(e) => settingsQ.data && settingsQ.data.enabled !== e.target.checked && saveMut.mutate({ ...settingsQ.data, enabled: e.target.checked })}
              />
            </Card.Header>
            <Card.Body>
              <Row className="mb-3">
                <Col md={6}>
                  <Form.Label>Provider</Form.Label>
                  <Form.Select
                    value={providerId || ''}
                    onChange={(e) => setProviderId(e.target.value || undefined)}
                    disabled={!canEdit || saveMut.isPending}
                    aria-label="LLM provider select"
                  >
                    <option value="">-- Select provider --</option>
                    {providersQ.data?.filter((p) => p.is_enabled).map((p) => (
                      <option value={p.id} key={p.id}>{p.name} ({p.kind})</option>
                    ))}
                  </Form.Select>
                </Col>
                <Col md={6}>
                  <Form.Label>Model</Form.Label>
                  <Form.Select
                    value={modelId || ''}
                    onChange={(e) => setModelId(e.target.value || undefined)}
                    disabled={!canEdit || !providerId || modelsQ.isLoading}
                    aria-label="LLM model select"
                  >
                    <option value="">-- Select model --</option>
                    {modelsQ.data?.map((m) => (
                      <option value={m.id} key={m.id}>{m.display_name || m.name}{m.is_default ? ' (default)' : ''}</option>
                    ))}
                  </Form.Select>
                </Col>
              </Row>
              <Button
                variant="outline-secondary"
                size="sm"
                onClick={() => setShowAdvanced((s) => !s)}
                aria-expanded={showAdvanced}
              >
                {showAdvanced ? 'Hide Advanced' : 'Show Advanced'}
              </Button>
              <Collapse in={showAdvanced}>
                <div className="mt-3">
                  <Row className="g-3">
                    <Col md={4}>
                      <Form.Label>Temperature</Form.Label>
                      <Form.Control
                        type="number"
                        step="0.01"
                        min={0}
                        max={2}
                        value={settingsQ.data.temperature ?? ''}
                        disabled={!canEdit}
                        onChange={(e) => settingsQ.data && saveMut.mutate({ ...settingsQ.data, temperature: parseFloat(e.target.value) })}
                      />
                    </Col>
                    <Col md={4}>
                      <Form.Label>Top P</Form.Label>
                      <Form.Control
                        type="number"
                        step="0.01"
                        min={0}
                        max={1}
                        value={settingsQ.data.top_p ?? ''}
                        disabled={!canEdit}
                        onChange={(e) => settingsQ.data && saveMut.mutate({ ...settingsQ.data, top_p: parseFloat(e.target.value) })}
                      />
                    </Col>
                    <Col md={4}>
                      <Form.Label>Max Tokens</Form.Label>
                      <Form.Control
                        type="number"
                        min={16}
                        max={8192}
                        value={settingsQ.data.max_tokens ?? ''}
                        disabled={!canEdit}
                        onChange={(e) => settingsQ.data && saveMut.mutate({ ...settingsQ.data, max_tokens: parseInt(e.target.value) })}
                      />
                    </Col>
                  </Row>
                  <hr />
                  <Row className="g-3">
                    <Col md={6}>
                      <Form.Check
                        type="switch"
                        label="Block PII in prompts"
                        checked={!!settingsQ.data.guardrails?.block_pii}
                        disabled={!canEdit}
                        onChange={(e) => settingsQ.data && saveMut.mutate({ ...settingsQ.data, guardrails: { ...settingsQ.data.guardrails, block_pii: e.target.checked } })}
                      />
                    </Col>
                    <Col md={6}>
                      <Form.Check
                        type="switch"
                        label="Allow Tool Use"
                        checked={!!settingsQ.data.guardrails?.allow_tool_use}
                        disabled={!canEdit}
                        onChange={(e) => settingsQ.data && saveMut.mutate({ ...settingsQ.data, guardrails: { ...settingsQ.data.guardrails, allow_tool_use: e.target.checked } })}
                      />
                    </Col>
                  </Row>
                </div>
              </Collapse>
            </Card.Body>
          </Card>

          <div className="d-flex gap-2 mb-4">
            <Button type="submit" disabled={!canEdit || saveMut.isPending} variant="primary">Save Settings</Button>
            <Button type="button" variant="outline-primary" size="sm" onClick={runTest} disabled={inferMut.isPending}>Test Suggestion</Button>
          </div>

          <Collapse in={testOpen}>
            <div>
              <Card className="mb-4">
                <Card.Header className="d-flex justify-content-between align-items-center">
                  <span>Test Suggestions</span>
                  {inferMut.isPending && <Spinner size="sm" />}
                </Card.Header>
                <Card.Body>
                  {inferMut.isError && <Alert variant="danger">Failed to get suggestions.</Alert>}
                  {inferMut.data && inferMut.data.length === 0 && <div>No suggestions returned.</div>}
                  {inferMut.data && inferMut.data.length > 0 && (
                    <Table size="sm" bordered>
                      <thead>
                        <tr>
                          <th>Table</th>
                          <th>Column</th>
                          <th>Provider</th>
                          <th>PII?</th>
                        </tr>
                      </thead>
                      <tbody>
                        {inferMut.data.map((s, i) => (
                          <tr key={i}>
                            <td>{s.table}</td>
                            <td>{s.column}</td>
                            <td><Badge bg="secondary">{s.provider || '—'}</Badge></td>
                            <td>{s.pii ? <Badge bg="danger">Yes</Badge> : '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </Table>
                  )}
                </Card.Body>
              </Card>
            </div>
          </Collapse>
        </Form>
      )}
    </div>
  )
}
