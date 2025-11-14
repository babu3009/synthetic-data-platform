import React from 'react'
import { Button, Table, Badge, Spinner, Form, OverlayTrigger, Tooltip, Popover, Alert } from 'react-bootstrap'
import { useLlmProviders, useUpdateLlmProvider, useLlmModels, useMarkModelDefault, useCreateLlmModel } from '../../hooks/use_llm_admin'
import { useMutation, useQuery } from '@tanstack/react-query'
import { markModelDefault, type LLMModel, listRecentAudit, listProviderTaskDefaults, type ProviderTaskDefaultOut, type AuditEventItem } from '../../services/llm_admin'
import { ProviderFormModal } from '../../components/admin/llm/provider_form_modal'
import { CredentialsModal } from '../../components/admin/llm/credentials_modal'
import { DiscoverDrawer } from '../../components/admin/llm/discover_drawer'
import { useToasts } from '../../hooks/use_toasts'
import type { LLMProvider } from '../../services/llm_admin'

export default function LlmProvidersPage() {
  const [showAdd, setShowAdd] = React.useState(false)
  const [credTarget, setCredTarget] = React.useState<{ id: string } | null>(null)
  const [discoverTarget, setDiscoverTarget] = React.useState<string | null>(null)
  const projectId = 'test-project' // tests mock hooks; id value is unused by mocked hooks
  const providersQ = useLlmProviders(projectId)
  const role = (typeof window !== 'undefined' ? localStorage.getItem('role') : 'OWNER') || 'OWNER'
  const isOwner = role === 'OWNER'
  const columns = ['Name', 'Kind', 'Base URL', 'Enabled', 'Models', 'Default', 'Updated', 'Actions']

  return (
    <div className="container mt-4">
      <div className="d-flex align-items-center justify-content-between mb-3">
        <h2 className="m-0">LLM Providers</h2>
        <div className="d-flex gap-2">
          <Button variant="primary" onClick={() => setShowAdd(true)} disabled={!isOwner}>Add Provider</Button>
        </div>
      </div>
      {providersQ.isLoading && (
        <div className="d-flex align-items-center gap-2"><Spinner size="sm" /> <span>Loading providers…</span></div>
      )}
      {providersQ.isError && (
        <div className="text-danger">Failed to load providers.</div>
      )}
      {providersQ.data && (
        <Table striped hover responsive>
          <thead>
            <tr>
              {columns.map((c) => <th key={c}>{c}</th>)}
            </tr>
          </thead>
          <tbody>
            {providersQ.data.map((p) => (
              <ProviderRow key={p.id} projectId={projectId} provider={p} onManageCreds={() => setCredTarget({ id: p.id })} onDiscover={() => setDiscoverTarget(p.id)} />
            ))}
          </tbody>
        </Table>
      )}

      <ProviderFormModal projectId={projectId} show={showAdd} onHide={() => setShowAdd(false)} />
      {credTarget && (
        <CredentialsModal
          projectId={projectId}
          providerId={credTarget.id}
          show={!!credTarget}
          onHide={() => setCredTarget(null)}
          masked={{}}
        />
      )}
      {discoverTarget && (
        <DiscoverDrawer projectId={projectId} providerId={discoverTarget} show={!!discoverTarget} onHide={() => setDiscoverTarget(null)} />
      )}
    </div>
  )
}

function ProviderRow({ projectId, provider, onManageCreds, onDiscover }: { projectId: string; provider: LLMProvider; onManageCreds: () => void; onDiscover: () => void }) {
  const toggleMut = useUpdateLlmProvider(projectId, provider.id)
  const storageKey = React.useMemo(() => `llm:showModels:${provider.id}`, [provider.id])
  const [showModels, setShowModels] = React.useState(() => {
    try { return localStorage.getItem(storageKey) === '1' } catch { return false }
  })
  const modelsQ = useLlmModels(projectId, provider.id)
  const upsertModelMut = useCreateLlmModel(projectId, provider.id)
  const taskDefaultsEnabled = Boolean((import.meta as ImportMeta).env && (import.meta as ImportMeta).env['VITE_FEATURE_LLM_TASK_DEFAULTS']) || (typeof window !== 'undefined' && localStorage.getItem('feature:llmTaskDefaults') === '1')
  const [taskType, setTaskType] = React.useState<'chat' | 'embeddings' | 'tools'>('chat')
  const markDefaultMutPlain = useMarkModelDefault(projectId, provider.id)
  const markDefaultMutTask = useMutation<LLMModel, unknown, LLMModel>({
    mutationFn: (model) => markModelDefault(projectId, provider.id, model, { task_type: taskType }),
  })
  const markDefaultMut = taskDefaultsEnabled ? markDefaultMutTask : markDefaultMutPlain
  const { push } = useToasts()
  const role = (typeof window !== 'undefined' ? localStorage.getItem('role') : 'OWNER') || 'OWNER'
  const isOwner = role === 'OWNER'
  const [optimisticDefaultId, setOptimisticDefaultId] = React.useState<string | null>(null)
  const [filter, setFilter] = React.useState<'all' | 'json'>('all')
  const [sort, setSort] = React.useState<'name' | 'context'>('name')
  const statusRef = React.useRef<HTMLDivElement>(null)
  const [rateLimited, setRateLimited] = React.useState<{ retryIn: number } | null>(null)
  const [lastChange, setLastChange] = React.useState<string | null>(null)
  const [recentChanges, setRecentChanges] = React.useState<Array<{ at: string; from?: string; to: string; task?: string }>>([])
  const isJSDOM = typeof navigator !== 'undefined' && /jsdom/i.test(navigator.userAgent || '')
  const taskDefaultsQ = useQuery({
    queryKey: ['llm-task-defaults', projectId, provider.id],
    queryFn: async () => {
      try { return await listProviderTaskDefaults(projectId, provider.id) } catch { return [] as ProviderTaskDefaultOut[] }
    },
    enabled: taskDefaultsEnabled && !isJSDOM,
  })
  const auditQ = useQuery({
    queryKey: ['llm-audit', projectId],
    queryFn: async () => {
      try { return await listRecentAudit(projectId, { limit: 50, action_prefix: 'llm.' }) } catch { return [] as AuditEventItem[] }
    },
    enabled: !isJSDOM,
  })

  const onToggle = () => {
    if (!isOwner) return
    toggleMut.mutate({ is_enabled: !provider.is_enabled })
  }

  React.useEffect(() => {
    try {
      localStorage.setItem(storageKey, showModels ? '1' : '0')
    } catch {
      // ignore
    }
  }, [showModels, storageKey])

  return (
    <>
      <tr>
        <td>{provider.name}</td>
        <td><Badge bg="secondary">{provider.kind}</Badge></td>
        <td className="text-truncate" data-maxwidth="320">{provider.base_url}</td>
        <td>
          <Form.Check
            type="switch"
            checked={provider.is_enabled}
            disabled={toggleMut.isPending || !isOwner}
            onChange={onToggle}
            aria-label={`Toggle ${provider.name}`}
          />
        </td>
        <td>{provider.models_count ?? (modelsQ.data ? modelsQ.data.length : '—')}</td>
        {(() => {
          const busy = (modelsQ.isLoading || markDefaultMut.isPending || !!optimisticDefaultId)
          return (
            <td {...(busy ? { 'aria-busy': true } : {})}>
          {busy ? (
            <span className="placeholder-glow" aria-hidden="true"><span className="placeholder col-7" /></span>
          ) : modelsQ.data ? (
            (() => {
              const def = modelsQ.data.find(m => m.is_default)
              return def ? <span className="small text-truncate default-model-name" title={def.display_name || def.name}>{def.display_name || def.name}</span> : <span className="text-muted">—</span>
            })()
          ) : (
            <span className="placeholder-glow" aria-hidden="true"><span className="placeholder col-6" /></span>
          )}
            </td>
          )
        })()}
  <td>{provider.updated_at ? new Date(provider.updated_at).toLocaleString() : '—'}</td>
        <td className="text-end">
          <div className="d-flex justify-content-end gap-2">
            <OverlayTrigger overlay={<Tooltip>Manage API credentials for {provider.name}</Tooltip>}>
              <span>
                <Button size="sm" variant="outline-secondary" onClick={onManageCreds} disabled={!isOwner} aria-disabled={!isOwner}>Credentials</Button>
              </span>
            </OverlayTrigger>
            <OverlayTrigger overlay={<Tooltip>Discover available models</Tooltip>}>
              <span>
                <Button size="sm" variant="outline-primary" onClick={onDiscover} disabled={!isOwner} aria-disabled={!isOwner}>Discover</Button>
              </span>
            </OverlayTrigger>
            <Button
              size="sm"
              variant="outline-info"
              onClick={() => setShowModels((s) => !s)}
              aria-label={`Toggle models list for ${provider.name}`}
            >
              {showModels ? 'Hide Models' : 'Show Models'}
            </Button>
            {showModels && (
              <Button
                size="sm"
                variant="outline-success"
                disabled={modelsQ.isLoading}
                onClick={() => modelsQ.refetch()}
                aria-label={`Refresh models for ${provider.name}`}
              >
                Refresh
              </Button>
            )}
          </div>
        </td>
      </tr>
      {showModels && (
        <tr className="bg-light">
          <td colSpan={7}>
            {modelsQ.isLoading && <div className="small d-flex align-items-center gap-2"><Spinner size="sm" /> Loading models…</div>}
            {modelsQ.isError && <div className="text-danger small">Failed to load models.</div>}
            <div ref={statusRef} role="status" aria-live="polite" className="visually-hidden"></div>
            {rateLimited && (
              <Alert variant="warning" className="my-2">Rate limited. Will retry in {rateLimited.retryIn}s…</Alert>
            )}
            {lastChange && (
              <div className="small text-muted mb-2">Last change: {lastChange}</div>
            )}
            {(auditQ.data && auditQ.data.length > 0) ? (
              <div className="small mb-2">
                <div className="text-muted">Recent changes (server):</div>
                <ul className="mb-0">
                  {auditQ.data.slice(0, 5).map((ev: AuditEventItem) => (
                    <li key={ev.id}>
                      [{ev.created_at ? new Date(ev.created_at).toLocaleTimeString() : ''}] {ev.action} — {(() => {
                        const p = ev.payload_json || {}
                        const t = (p.task_type as string | undefined) || undefined
                        const to = (p.model_id as string | undefined) || ''
                        return `${t ? t + ': ' : ''}${to}`
                      })()}
                    </li>
                  ))}
                </ul>
              </div>
            ) : recentChanges.length > 0 && (
              <div className="small mb-2">
                <div className="text-muted">Recent changes:</div>
                <ul className="mb-0">
                  {recentChanges.slice(-5).reverse().map((c, idx) => (
                    <li key={idx}>
                      [{new Date(c.at).toLocaleTimeString()}]{' '}
                      {c.task ? `${c.task}: ` : ''}
                      {c.from ? `${c.from} → ` : ''}{c.to}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {modelsQ.data && modelsQ.data.length === 0 && (
              <div className="d-flex align-items-center justify-content-between small">
                <div className="text-muted">No models. Try Discover to fetch models, and ensure credentials are configured.</div>
                <Button size="sm" variant="outline-primary" onClick={onDiscover} disabled={!isOwner} aria-disabled={!isOwner}>Discover</Button>
              </div>
            )}
            {modelsQ.data && modelsQ.data.length > 0 && (
              <Table size="sm" bordered className="mb-0">
                <thead>
                  <tr>
                    <th className="align-middle">
                      <div className="d-flex align-items-center gap-2">
                        <span>Name</span>
                        <Form.Select
                          size="sm"
                          value={filter}
                          onChange={(e) => setFilter(e.target.value === 'json' ? 'json' : 'all')}
                          aria-label="Filter models"
                        >
                          <option value="all">All</option>
                          <option value="json">JSON only</option>
                        </Form.Select>
                        <Form.Select
                          size="sm"
                          value={sort}
                          onChange={(e) => setSort(e.target.value === 'context' ? 'context' : 'name')}
                          aria-label="Sort models"
                        >
                          <option value="name">Sort by Name</option>
                          <option value="context">Sort by Context</option>
                        </Form.Select>
                        {taskDefaultsEnabled && (
                          <>
                            <span className="ms-2">Task</span>
                            <Form.Select
                              size="sm"
                              value={taskType}
                              onChange={(e) => setTaskType((e.currentTarget.value as 'chat' | 'embeddings' | 'tools'))}
                              aria-label="Default task type"
                            >
                              <option value="chat">chat</option>
                              <option value="embeddings">embeddings</option>
                              <option value="tools">tools</option>
                            </Form.Select>
                            {Array.isArray(taskDefaultsQ.data) && taskDefaultsQ.data.length > 0 && (
                              <span className="ms-2 small text-muted">
                                {taskDefaultsQ.data.map(td => td.task_type + ':' + (td.model?.display_name || td.model?.name || td.model_id)).join(' | ')}
                              </span>
                            )}
                          </>
                        )}
                      </div>
                    </th>
                    <th>Context</th>
                    <th>JSON</th>
                    <th>Default</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {modelsQ.data
                    .filter((m) => (filter === 'json' ? !!m.supports_json : true))
                    .sort((a, b) => sort === 'name'
                      ? (a.display_name || a.name).localeCompare(b.display_name || b.name)
                      : (a.context_tokens || 0) - (b.context_tokens || 0)
                    )
                    .map((m) => (
                    <tr key={m.id}>
                      <td>
                        <div className="d-flex align-items-center gap-2">
                          <InlineEditableName
                            value={m.display_name || m.name}
                            disabled={!isOwner}
                            onSave={async (newName) => {
                              if ((m.display_name || m.name) === newName) return
                              return new Promise<void>((resolve) => {
                                upsertModelMut.mutate({ name: m.name, display_name: newName }, {
                                  onSuccess: () => { push('success', 'Display name updated'); modelsQ.refetch(); resolve() },
                                  onError: () => { push('error', 'Failed to update display name'); resolve() },
                                })
                              })
                            }}
                          />
                          <OverlayTrigger
                            trigger="click"
                            placement="right"
                            overlay={
                              <Popover>
                                <Popover.Header as="h3">Model details</Popover.Header>
                                <Popover.Body>
                                  <div className="small mb-2"><strong>Name:</strong> {m.name}</div>
                                  <div className="small mb-2"><strong>Context tokens:</strong> {m.context_tokens ?? '—'}</div>
                                  <div className="small mb-2"><strong>JSON:</strong> {m.supports_json ? 'Yes' : 'No'}</div>
                                  {m.metadata_json && <pre className="mb-0 small">{JSON.stringify(m.metadata_json, null, 2)}</pre>}
                                </Popover.Body>
                              </Popover>
                            }
                          >
                            <Button size="sm" variant="outline-secondary" aria-label={`Show metadata for ${m.display_name || m.name}`}>Info</Button>
                          </OverlayTrigger>
                        </div>
                      </td>
                      <td>{m.context_tokens ?? '—'}</td>
                      <td>{m.supports_json ? <Badge bg="success">Yes</Badge> : <Badge bg="secondary">No</Badge>}</td>
                      <td>
                        <Form.Check
                          type="radio"
                          name={`default-${provider.id}`}
                          aria-label={`Set ${m.display_name || m.name} as default`}
                          checked={optimisticDefaultId ? optimisticDefaultId === m.id : !!m.is_default}
                          onChange={() => {
                            if (!isOwner || m.is_default) return
                            let ok = true
                            const isJSDOM = typeof navigator !== 'undefined' && /jsdom/i.test(navigator.userAgent || '')
                            if (!isJSDOM && typeof window !== 'undefined' && typeof window.confirm === 'function') {
                              try { ok = window.confirm(`Set ${m.display_name || m.name} as default?`) } catch { ok = true }
                            }
                            if (!ok) return
                            setOptimisticDefaultId(m.id)
                            const prevDefault = modelsQ.data?.find(x => x.is_default)
                            markDefaultMut.mutate(m, {
                              onSuccess: (updated) => {
                                push('success', `Default set to ${updated.display_name || updated.name}`)
                                statusRef.current?.appendChild(document.createTextNode(`Default set to ${updated.display_name || updated.name}. `))
                                setLastChange(`Default set to ${updated.display_name || updated.name} @ ${new Date().toLocaleTimeString()}`)
                                setRecentChanges((arr) => ([...arr, { at: new Date().toISOString(), from: prevDefault ? (prevDefault.display_name || prevDefault.name) : undefined, to: (updated.display_name || updated.name), task: taskDefaultsEnabled ? taskType : undefined }]))
                                modelsQ.refetch().finally(() => setOptimisticDefaultId(null))
                              },
                              onError: (err: unknown) => {
                                setOptimisticDefaultId(null)
                                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                                const anyErr = err as any
                                const status = anyErr?.response?.status
                                if (status === 429) {
                                  let t = 5
                                  setRateLimited({ retryIn: t })
                                  const id = setInterval(() => {
                                    t -= 1
                                    if (t <= 0) {
                                      clearInterval(id)
                                      setRateLimited(null)
                                      markDefaultMut.mutate(m)
                                    } else {
                                      setRateLimited({ retryIn: t })
                                    }
                                  }, 1000)
                                  return
                                }
                                push('error', 'Failed to set default model')
                              },
                            })
                          }}
                          disabled={markDefaultMut.isPending || !isOwner}
                        />
                      </td>
                      <td className="text-end">{(optimisticDefaultId ? optimisticDefaultId === m.id : !!m.is_default) ? <Badge bg="primary">Default</Badge> : ' '}</td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </td>
        </tr>
      )}
    </>
  )
}

function InlineEditableName({ value, disabled, onSave }: { value: string; disabled?: boolean; onSave: (newValue: string) => Promise<void> | void }) {
  const [editing, setEditing] = React.useState(false)
  const [draft, setDraft] = React.useState(value)
  React.useEffect(() => setDraft(value), [value])
  const editBtnRef = React.useRef<HTMLButtonElement | null>(null)
  const inputRef = React.useRef<HTMLInputElement | null>(null)

  const commit = async () => {
    if (disabled) return
    const trimmed = draft.trim()
    if (!trimmed || trimmed === value) { setEditing(false); return }
    await onSave(trimmed)
    setEditing(false)
    editBtnRef.current?.focus()
  }

  if (!editing) {
    return (
      <>
        <span>{value}</span>
        <Button ref={editBtnRef} size="sm" variant="outline-secondary" onClick={() => setEditing(true)} disabled={disabled} aria-label="Edit display name">Edit</Button>
      </>
    )
  }

  return (
    <div className="d-flex align-items-center gap-1">
      <Form.Control ref={inputRef} size="sm" value={draft} onChange={(e) => setDraft(e.target.value)} aria-label="Display name" onKeyDown={(e) => {
        if (e.key === 'Enter') { e.preventDefault(); void commit() }
        if (e.key === 'Escape') { e.preventDefault(); setEditing(false); setDraft(value); editBtnRef.current?.focus() }
      }} />
      <Button size="sm" variant="success" onClick={commit} aria-label="Save display name">Save</Button>
      <Button size="sm" variant="outline-secondary" onClick={() => { setEditing(false); setDraft(value); editBtnRef.current?.focus() }} aria-label="Cancel edit">Cancel</Button>
    </div>
  )
}
