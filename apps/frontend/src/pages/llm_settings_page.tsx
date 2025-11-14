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
  // Local shadow state for advanced numeric params so inputs are properly controlled for test updates
  const [advParams, setAdvParams] = React.useState<{ temperature: number | '' ; top_p: number | '' ; max_tokens: number | '' }>({
    temperature: settingsQ.data?.temperature ?? '',
    top_p: settingsQ.data?.top_p ?? '',
    max_tokens: settingsQ.data?.max_tokens ?? '',
  })
  // Local shadow state for guardrails switches for incremental updates
  const [guardrails, setGuardrails] = React.useState<{ block_pii: boolean ; allow_tool_use: boolean }>({
    block_pii: !!settingsQ.data?.guardrails?.block_pii,
    allow_tool_use: !!settingsQ.data?.guardrails?.allow_tool_use,
  })

  const modelsQ = useLlmModels(projectId, providerId || '')
  const effectiveModelId = React.useMemo(() => {
    return modelId || modelsQ.data?.find((m) => m.is_default)?.id
  }, [modelId, modelsQ.data])
  const inferMut = useInferProviders(projectId, {
    taskType: 'chat',
    taskDefaults: effectiveModelId ? { chat: effectiveModelId } : undefined,
  })

  // Primitive snapshots to drive initialization without depending on object identity
  const depProviderId = settingsQ.data?.provider_id || undefined
  const depModelId = settingsQ.data?.model_id || undefined
  const depTemp: number | '' = settingsQ.data?.temperature ?? ''
  const depTopP: number | '' = settingsQ.data?.top_p ?? ''
  const depMaxTokens: number | '' = settingsQ.data?.max_tokens ?? ''
  const depBlockPii = !!settingsQ.data?.guardrails?.block_pii
  const depAllowToolUse = !!settingsQ.data?.guardrails?.allow_tool_use

  // Initialize selects when settings load; avoid infinite loops when data object identity changes by
  // depending only on primitive fields and updating state only when values differ.
  React.useEffect(() => {
    const nextProvider = depProviderId
    const nextModel = depModelId
    const nextAdv: { temperature: number | ''; top_p: number | ''; max_tokens: number | '' } = {
      temperature: depTemp,
      top_p: depTopP,
      max_tokens: depMaxTokens,
    }
    const nextGuard = {
      block_pii: depBlockPii,
      allow_tool_use: depAllowToolUse,
    }
    setProviderId((prev) => (prev !== nextProvider ? nextProvider : prev))
    setModelId((prev) => (prev !== nextModel ? nextModel : prev))
    setAdvParams((prev) => {
      if (
        prev.temperature !== nextAdv.temperature ||
        prev.top_p !== nextAdv.top_p ||
        prev.max_tokens !== nextAdv.max_tokens
      ) {
        return nextAdv
      }
      return prev
    })
    setGuardrails((prev) => (
      prev.block_pii !== nextGuard.block_pii || prev.allow_tool_use !== nextGuard.allow_tool_use ? nextGuard : prev
    ))
  }, [
    depProviderId,
    depModelId,
    depTemp,
    depTopP,
    depMaxTokens,
    depBlockPii,
    depAllowToolUse,
  ])

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
                  <div className="mt-2">
                    <Button
                      size="sm"
                      variant="outline-secondary"
                      disabled={!canEdit || !providerId || modelsQ.isLoading || !modelsQ.data?.some((m) => m.is_default)}
                      onClick={() => {
                        const def = modelsQ.data?.find((m) => m.is_default)
                        if (!def || !settingsQ.data) return
                        setModelId(def.id)
                        // Save immediately to apply shortcut
                        saveMut.mutate({ ...settingsQ.data, provider_id: providerId || null, model_id: def.id })
                      }}
                    >
                      Use provider default
                    </Button>
                  </div>
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
                      <Form.Label htmlFor="llm-temperature">Temperature</Form.Label>
                      <Form.Control
                        id="llm-temperature"
                        aria-label="Temperature"
                        type="number"
                        step="0.01"
                        min={0}
                        max={2}
                        value={advParams.temperature}
                        disabled={!canEdit}
                        onChange={(e) => {
                          if (!settingsQ.data) return
                          const val = parseFloat(e.target.value)
                          setAdvParams(p => {
                            const next = { ...p, temperature: val }
                            saveMut.mutate({ ...settingsQ.data, temperature: next.temperature as number, top_p: next.top_p as number, max_tokens: next.max_tokens as number })
                            return next
                          })
                        }}
                      />
                    </Col>
                    <Col md={4}>
                      <Form.Label htmlFor="llm-top-p">Top P</Form.Label>
                      <Form.Control
                        id="llm-top-p"
                        aria-label="Top P"
                        type="number"
                        step="0.01"
                        min={0}
                        max={1}
                        value={advParams.top_p}
                        disabled={!canEdit}
                        onChange={(e) => {
                          if (!settingsQ.data) return
                          const val = parseFloat(e.target.value)
                          setAdvParams(p => {
                            const next = { ...p, top_p: val }
                            saveMut.mutate({ ...settingsQ.data, temperature: next.temperature as number, top_p: next.top_p as number, max_tokens: next.max_tokens as number })
                            return next
                          })
                        }}
                      />
                    </Col>
                    <Col md={4}>
                      <Form.Label htmlFor="llm-max-tokens">Max Tokens</Form.Label>
                      <Form.Control
                        id="llm-max-tokens"
                        aria-label="Max Tokens"
                        type="number"
                        min={16}
                        max={8192}
                        value={advParams.max_tokens}
                        disabled={!canEdit}
                        onChange={(e) => {
                          if (!settingsQ.data) return
                          const val = parseInt(e.target.value)
                          setAdvParams(p => {
                            const next = { ...p, max_tokens: val }
                            saveMut.mutate({ ...settingsQ.data, temperature: next.temperature as number, top_p: next.top_p as number, max_tokens: next.max_tokens as number })
                            return next
                          })
                        }}
                      />
                    </Col>
                  </Row>
                  <hr />
                  <Row className="g-3">
                    <Col md={6}>
                      <Form.Check
                        type="switch"
                        id="guardrails-block-pii"
                        label="Block PII in prompts"
                        checked={guardrails.block_pii}
                        disabled={!canEdit}
                        onChange={(e) => {
                          if (!settingsQ.data) return
                          setGuardrails(g => {
                            const next = { ...g, block_pii: e.target.checked }
                            saveMut.mutate({ ...settingsQ.data, guardrails: { block_pii: next.block_pii, allow_tool_use: next.allow_tool_use } })
                            return next
                          })
                        }}
                      />
                    </Col>
                    <Col md={6}>
                      <Form.Check
                        type="switch"
                        id="guardrails-allow-tool-use"
                        label="Allow Tool Use"
                        checked={guardrails.allow_tool_use}
                        disabled={!canEdit}
                        onChange={(e) => {
                          if (!settingsQ.data) return
                          setGuardrails(g => {
                            const next = { ...g, allow_tool_use: e.target.checked }
                            saveMut.mutate({ ...settingsQ.data, guardrails: { block_pii: next.block_pii, allow_tool_use: next.allow_tool_use } })
                            return next
                          })
                        }}
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
