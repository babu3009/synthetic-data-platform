import { useMemo, useState } from 'react'
import { Alert, Button, Col, Form, Modal, Row, Table, OverlayTrigger, Tooltip, Popover } from 'react-bootstrap'
import { useWizard, type Column } from '../../state/wizard'
import { inferProviders, saveProviders, autosaveProviders, type ProviderSuggestion } from '../../services/providers'
import { autosaveEntity } from '../../services/entities'
import { useAutosave } from '../../hooks/use_autosave'

function validateConfig(provider: Column['provider'], cfg: Column['providerConfig']): string | null {
  if (!provider) return null
  if (!cfg) cfg = {}
  switch (provider) {
    case 'pattern': {
      const mask = (cfg as { mask?: string } | undefined)?.mask
      if (!mask || typeof mask !== 'string' || mask.trim().length === 0) return 'Pattern mask is required.'
      return null
    }
    case 'categorical': {
      const cats = (cfg as { categories?: Array<{ value: unknown; weight?: number }> } | undefined)?.categories
      if (!Array.isArray(cats) || cats.length === 0) return 'At least one category is required.'
      const total = cats.reduce((s: number, c: { weight?: number }) => s + (typeof c.weight === 'number' ? c.weight : 0), 0)
      if (Math.abs(total - 1) > 1e-6) return 'Categorical weights must sum to 1.'
      return null
    }
    default:
      return null
  }
}

function SuggestionsDiffModal({
  show,
  onHide,
  diffs,
  onConfirm,
}: {
  show: boolean
  onHide: () => void
  diffs: Array<{
    table: string
    column: string
    before: Partial<Column>
    after: Partial<Column>
    confidence?: number
    reason?: string
    manualOverride?: boolean
  }>
  onConfirm: () => void
}) {
  return (
  <Modal show={show} onHide={onHide} size="lg" animation={false}>
      <Modal.Header closeButton>
        <Modal.Title>Apply provider suggestions</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        {diffs.length === 0 ? (
          <Alert variant="info">No changes suggested.</Alert>
        ) : (
          <Table bordered size="sm">
            <thead>
              <tr>
                <th>Table</th>
                <th>Column</th>
                <th>Change</th>
                <th>Confidence</th>
              </tr>
            </thead>
            <tbody>
              {diffs.map((d, i) => {
                const changes: Array<JSX.Element> = []
                if (d.before.provider !== d.after.provider) {
                  changes.push(
                    <div key="prov">
                      <strong>provider:</strong> <code>{String(d.before.provider ?? '(none)')}</code> →{' '}
                      <code>{String(d.after.provider ?? '(none)')}</code>
                    </div>
                  )
                }
                if (JSON.stringify(d.before.providerConfig ?? null) !== JSON.stringify(d.after.providerConfig ?? null)) {
                  changes.push(
                    <div key="cfg">
                      <strong>config:</strong> <code>{JSON.stringify(d.before.providerConfig ?? {})}</code> →{' '}
                      <code>{JSON.stringify(d.after.providerConfig ?? {})}</code>
                    </div>
                  )
                }
                if (d.before.pii !== d.after.pii) {
                  changes.push(
                    <div key="pii">
                      <strong>pii:</strong> <code>{String(d.before.pii ?? false)}</code> →{' '}
                      <code>{String(d.after.pii ?? false)}</code>
                    </div>
                  )
                }
                if (d.before.piiSubtype !== d.after.piiSubtype) {
                  changes.push(
                    <div key="piisub">
                      <strong>piiSubtype:</strong> <code>{String(d.before.piiSubtype ?? '(none)')}</code> →{' '}
                      <code>{String(d.after.piiSubtype ?? '(none)')}</code>
                    </div>
                  )
                }
                return (
                  <tr key={i}>
                    <td>{d.table}</td>
                    <td>
                      {d.column}
                      {d.manualOverride && (
                        <span className="ms-2 badge bg-warning text-dark" title="This will overwrite a manual selection">
                          overwrites manual
                        </span>
                      )}
                    </td>
                    <td>{changes.length > 0 ? changes : <span className="text-muted">(no field changes)</span>}</td>
                    <td>
                      {typeof d.confidence === 'number' ? (
                        <OverlayTrigger placement="left" overlay={<Tooltip>{d.reason || 'suggestion'}</Tooltip>}>
                          <span className="badge bg-info text-dark">{Math.round(d.confidence * 100)}%</span>
                        </OverlayTrigger>
                      ) : (
                        <span className="text-muted">n/a</span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </Table>
        )}
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={onHide}>
          Cancel
        </Button>
        <Button onClick={onConfirm} disabled={diffs.length === 0}>
          Apply
        </Button>
      </Modal.Footer>
    </Modal>
  )
}

export default function ProvidersPiiPage() {
  const { state, dispatch } = useWizard()
  const entity = state.entities.find((e) => e.id === state.selectedEntityId) || state.entities[0]
  const [tableFilter, setTableFilter] = useState<string>('__all__')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [loadingSuggest, setLoadingSuggest] = useState(false)
  const [diffs, setDiffs] = useState<
    Array<{ table: string; column: string; before: Partial<Column>; after: Partial<Column>; confidence?: number; reason?: string; manualOverride?: boolean }>
  >([])
  const [showDiff, setShowDiff] = useState(false)
  const [lastChangesCount, setLastChangesCount] = useState<number | null>(null)
  const [suggestionsByKey, setSuggestionsByKey] = useState<Record<string, ProviderSuggestion>>({})
  const [summaryCounts, setSummaryCounts] = useState<{ providers: number; pii: number } | null>(null)

  const projectId = state.projectId || 'default'

  const tables = useMemo(() => entity?.tables || [], [entity])
  const visibleRows = useMemo(() => {
    const rows: Array<{ table: string; column: Column }> = []
    if (!entity) return rows
    for (const t of entity.tables) {
      if (tableFilter !== '__all__' && t.name !== tableFilter) continue
      for (const c of t.columns) rows.push({ table: t.name, column: c })
    }
    return rows
  }, [entity, tableFilter])


  const providerOptions: Column['provider'][] = [
    'faker',
    'pattern',
    'sequence',
    'categorical',
    'expression',
    'geo',
    'checksum-valid',
    'reference',
    'empirical',
  ]

  const piiOptions: NonNullable<Column['piiSubtype']>[] = [
    'email',
    'phone',
    'address',
    'national_id',
    'credit_card',
    'dob',
    'ip',
    'device',
  ]

  function handleProviderChange(table: string, col: Column, provider: Column['provider']) {
    dispatch({ type: 'updateColumn', entityId: entity.id, tableName: table, columnName: col.name, patch: { provider } })
  }

  function handleConfigChange(table: string, col: Column, value: string) {
    try {
      const parsed = value.trim() ? JSON.parse(value) : undefined
      dispatch({ type: 'updateColumn', entityId: entity.id, tableName: table, columnName: col.name, patch: { providerConfig: parsed } })
      setError(null)
    } catch (e: unknown) {
      setError('Config must be valid JSON')
    }
  }

  function handlePiiToggle(table: string, col: Column, checked: boolean) {
    dispatch({ type: 'updateColumn', entityId: entity.id, tableName: table, columnName: col.name, patch: { pii: checked } })
  }

  function handlePiiSubtype(table: string, col: Column, subtype?: Column['piiSubtype']) {
    dispatch({ type: 'updateColumn', entityId: entity.id, tableName: table, columnName: col.name, patch: { piiSubtype: subtype } })
  }

  async function handleSuggest() {
    if (!entity) return
    setLoadingSuggest(true)
    setError(null)
    try {
      const suggestions = (await inferProviders(projectId, entity)) as ProviderSuggestion[]
      const diffs: Array<{ table: string; column: string; before: Partial<Column>; after: Partial<Column>; confidence?: number; reason?: string; manualOverride?: boolean }> = []
      const map: Record<string, ProviderSuggestion> = {}
      let providerChanges = 0
      let piiUpdates = 0
      for (const s of suggestions) {
        const t = entity.tables.find((tt) => tt.name === s.table)
        const c = t?.columns.find((cc) => cc.name === s.column)
        if (!t || !c) continue
        const before: Partial<Column> = {
          provider: c.provider,
          providerConfig: c.providerConfig,
          pii: c.pii,
          piiSubtype: c.piiSubtype,
        }
        const after: Partial<Column> = {
          provider: s.provider ?? c.provider,
          providerConfig: s.providerConfig ?? c.providerConfig,
          pii: typeof s.pii === 'boolean' ? s.pii : c.pii,
          piiSubtype: s.piiSubtype ?? c.piiSubtype,
        }
        const changed = JSON.stringify(before) !== JSON.stringify(after)
        if (changed) {
          const manualOverride = Boolean(
            (c.provider && s.provider && s.provider !== c.provider) ||
              (c.providerConfig && JSON.stringify(c.providerConfig) !== JSON.stringify(s.providerConfig ?? c.providerConfig)) ||
              (typeof s.pii === 'boolean' && s.pii !== c.pii) ||
              (s.piiSubtype && s.piiSubtype !== c.piiSubtype)
          )
          diffs.push({ table: s.table, column: s.column, before, after, confidence: s.confidence, reason: s.reason, manualOverride })
          const key = `${s.table}.${s.column}`
          map[key] = s
          if ((before.provider !== after.provider) || (JSON.stringify(before.providerConfig ?? null) !== JSON.stringify(after.providerConfig ?? null))) providerChanges++
          if ((before.pii !== after.pii) || (before.piiSubtype !== after.piiSubtype)) piiUpdates++
        }
      }
      setDiffs(diffs)
      setLastChangesCount(diffs.length)
      setShowDiff(true)
      setSuggestionsByKey(map)
      setSummaryCounts({ providers: providerChanges, pii: piiUpdates })
    } catch (e: unknown) {
      const res = (e as { response?: { status?: number; data?: { detail?: string } } })?.response
      const status = res?.status
      if (status === 429) {
        setError('Rate limit exceeded for provider inference. Please wait a few seconds and try again.')
      } else {
        const detail = res?.data?.detail
        const msg = e instanceof Error ? e.message : undefined
        setError(detail || msg || 'Failed to infer providers')
      }
    } finally {
      setLoadingSuggest(false)
    }
  }

  async function handleApplyDiffs() {
    setShowDiff(false)
    if (diffs.length === 0 || !entity) return
    const suggestions: ProviderSuggestion[] = diffs.map((d) => ({
      table: d.table,
      column: d.column,
      provider: d.after.provider,
      providerConfig: d.after.providerConfig,
      pii: d.after.pii,
      piiSubtype: d.after.piiSubtype,
    }))
    dispatch({ type: 'applyProviderSuggestions', entityId: entity.id, suggestions })
  }

  // Apply a single row suggestion
  function applySuggestion(tableName: string, col: Column) {
    const key = `${tableName}.${col.name}`
    const s = suggestionsByKey[key]
    if (!s) return
    const patch: Partial<Column> = {
      provider: (s.provider ?? col.provider) as Column['provider'],
      providerConfig: s.providerConfig ?? col.providerConfig,
      pii: typeof s.pii === 'boolean' ? s.pii : col.pii,
      piiSubtype: (s.piiSubtype ?? col.piiSubtype) as Column['piiSubtype'],
    }
    dispatch({ type: 'updateColumn', entityId: entity.id, tableName, columnName: col.name, patch })
    // Remove this suggestion and recompute summary
    const newMap = { ...suggestionsByKey }
    delete newMap[key]
    setSuggestionsByKey(newMap)
    // recompute counts vs current entity snapshot
    setSummaryCounts(prev => {
      if (!prev) return prev
      // naive decrement: we don't know whether this was a provider change, pii update, or both; recompute from remaining diffs
      let providers = 0
      let pii = 0
      for (const [k, sug] of Object.entries(newMap)) {
        const [tName, cName] = k.split('.')
        const t = entity.tables.find(tt => tt.name === tName)
        const c = t?.columns.find(cc => cc.name === cName)
        if (!t || !c) continue
        const before = { provider: c.provider, providerConfig: c.providerConfig, pii: c.pii, piiSubtype: c.piiSubtype }
        const after = {
          provider: sug.provider ?? c.provider,
          providerConfig: sug.providerConfig ?? c.providerConfig,
          pii: typeof sug.pii === 'boolean' ? sug.pii : c.pii,
          piiSubtype: sug.piiSubtype ?? c.piiSubtype,
        }
        if ((before.provider !== after.provider) || (JSON.stringify(before.providerConfig ?? null) !== JSON.stringify(after.providerConfig ?? null))) providers++
        if ((before.pii !== after.pii) || (before.piiSubtype !== after.piiSubtype)) pii++
      }
      return { providers, pii }
    })
  }

  async function handleSave() {
    if (!entity) return
    setSaving(true)
    setError(null)
    try {
      // Persist entity snapshot (autosave) and try backend providers save
      await autosaveEntity(projectId, entity)
      // Build providers snapshot
      const providers: ProviderSuggestion[] = []
      for (const t of entity.tables) {
        for (const c of t.columns) {
          providers.push({
            table: t.name,
            column: c.name,
            provider: c.provider,
            providerConfig: c.providerConfig,
            pii: c.pii,
            piiSubtype: c.piiSubtype,
          })
        }
      }
      await saveProviders(projectId, entity.id, providers)
      // Clear dirty on successful explicit save
      dispatch({ type: 'clearDirty' })
    } catch (e: unknown) {
      // Show non-blocking error; localStorage fallback already attempted in service
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      const msg = e instanceof Error ? e.message : undefined
      setError(detail || msg || 'Saved locally; backend save not available')
    } finally {
      setSaving(false)
    }
  }

  // Debounced autosave (800ms) for providers changes
  useAutosave([entity, projectId], async () => {
    if (!entity) return
    await autosaveEntity(projectId, entity)
    // Save a lightweight providers-only snapshot too
    const providers: ProviderSuggestion[] = []
    for (const t of entity.tables) {
      for (const c of t.columns) {
        providers.push({
          table: t.name,
          column: c.name,
          provider: c.provider,
          providerConfig: c.providerConfig,
          pii: c.pii,
          piiSubtype: c.piiSubtype,
        })
      }
    }
    autosaveProviders(projectId, entity.id, providers)
  }, 800, () => dispatch({ type: 'clearDirty' }))

  return (
    <div>
      {!entity && <Alert variant="info">Select or create an entity to configure providers and PII.</Alert>}
      {entity && (
      <>
      {error && (
        <Alert variant="danger" onClose={() => setError(null)} dismissible>
          {error}
        </Alert>
      )}

      <div className="d-flex justify-content-between align-items-center mb-2">
        <div className="d-flex align-items-center gap-2">
          <strong>Entity:</strong>
          <span>{entity.name}</span>
        </div>
        <div className="d-flex align-items-center gap-2">
          <Form.Select size="sm" value={tableFilter} onChange={(e) => setTableFilter(e.target.value)} aria-label="Filter by table">
            <option value="__all__">All tables</option>
            {tables.map((t) => (
              <option key={t.name} value={t.name}>
                {t.name}
              </option>
            ))}
          </Form.Select>
          <Button variant="secondary" size="sm" onClick={handleSuggest} disabled={loadingSuggest} aria-label="Auto-suggest providers from column metadata">
            {loadingSuggest ? 'Suggesting…' : 'Auto-suggest providers'}
            {lastChangesCount != null && !loadingSuggest && (
              <span className="ms-2 badge bg-light text-dark">{lastChangesCount} changes</span>
            )}
          </Button>
          <Button size="sm" onClick={handleSave} disabled={saving} aria-label="Save provider and PII settings">
            {saving ? 'Saving…' : 'Save'}
          </Button>
        </div>
      </div>

      {summaryCounts && (summaryCounts.providers > 0 || summaryCounts.pii > 0) && (
        <Alert variant="info" className="py-2">
          <strong>Suggestions summary:</strong>
          <span className="ms-2">{summaryCounts.providers} provider change{summaryCounts.providers === 1 ? '' : 's'}</span>
          <span className="ms-3">{summaryCounts.pii} PII update{summaryCounts.pii === 1 ? '' : 's'}</span>
        </Alert>
      )}

      <Table bordered hover size="sm">
        <thead>
          <tr>
            <th>Table</th>
            <th>Column</th>
            <th>Type</th>
            <th>
              <div className="d-flex align-items-center gap-1">
                <span>Provider</span>
                <OverlayTrigger placement="top" overlay={<Tooltip>Select a generator for this column</Tooltip>}>
                  <span role="img" aria-label="Provider help">❔</span>
                </OverlayTrigger>
              </div>
            </th>
            <th>
              <div className="d-flex align-items-center gap-1">
                <span>Config (JSON)</span>
                <OverlayTrigger placement="top" overlay={<Tooltip>Provider-specific configuration</Tooltip>}>
                  <span role="img" aria-label="Config help">❔</span>
                </OverlayTrigger>
              </div>
            </th>
            <th>
              <div className="d-flex align-items-center gap-1">
                <span>PII</span>
                <OverlayTrigger placement="top" overlay={<Tooltip>Mark and subtype personally identifiable info</Tooltip>}>
                  <span role="img" aria-label="PII help">❔</span>
                </OverlayTrigger>
              </div>
            </th>
            <th>Suggestion</th>
          </tr>
        </thead>
        <tbody>
          {visibleRows.length === 0 ? (
            <tr>
              <td colSpan={6} className="text-center text-muted">
                No columns
              </td>
            </tr>
          ) : (
            visibleRows.map(({ table, column }, idx) => {
              const cfgText = column.providerConfig ? JSON.stringify(column.providerConfig, null, 0) : ''
              const validation = validateConfig(column.provider, column.providerConfig)
              return (
                <tr key={`${table}.${column.name}.${idx}`}>
                  <td>{table}</td>
                  <td>{column.name}</td>
                  <td>{column.dtype}</td>
                  <td>
                    <Form.Select
                      aria-label={`Provider for ${table}.${column.name}`}
                      value={column.provider || ''}
                      onChange={(e) => handleProviderChange(table, column, (e.target.value || undefined) as Column['provider'])}
                      onKeyDown={(e) => {
                        if (e.altKey && (e.key === 'ArrowDown' || e.key === 'ArrowUp')) {
                          e.preventDefault()
                          const dir = e.key === 'ArrowDown' ? 1 : -1
                          const nextIndex = idx + dir
                          const selector = `[data-row-index="${nextIndex}"][data-col-role="provider"]`
                          const el = document.querySelector<HTMLSelectElement>(selector)
                          el?.focus()
                        }
                      }}
                      data-row-index={idx}
                      data-col-role="provider"
                    >
                      <option value="">(none)</option>
                      {providerOptions.map((p) => (
                        <option key={p} value={p}>
                          {p}
                        </option>
                      ))}
                    </Form.Select>
                  </td>
                  <td>
                    <Form.Control
                      as="textarea"
                      rows={1}
                      aria-label={`Provider config for ${table}.${column.name}`}
                      value={cfgText}
                      onChange={(e) => handleConfigChange(table, column, e.target.value)}
                      placeholder={column.provider === 'pattern' ? '{"mask":"AA-9999"}' : column.provider === 'categorical' ? '{"categories":[{"value":"A","weight":0.5}]}' : '{}'}
                      isInvalid={!!validation}
                      onKeyDown={(e) => {
                        if (e.altKey && (e.key === 'ArrowDown' || e.key === 'ArrowUp')) {
                          e.preventDefault()
                          const dir = e.key === 'ArrowDown' ? 1 : -1
                          const nextIndex = idx + dir
                          const selector = `[data-row-index="${nextIndex}"][data-col-role="config"]`
                          const el = document.querySelector<HTMLTextAreaElement>(selector)
                          el?.focus()
                        }
                      }}
                      data-row-index={idx}
                      data-col-role="config"
                    />
                    {validation && <Form.Control.Feedback type="invalid">{validation}</Form.Control.Feedback>}
                  </td>
                  <td>
                    <Row className="g-1">
                      <Col xs="auto" className="d-flex align-items-center">
                        <Form.Check
                          type="switch"
                          aria-label={`PII switch for ${table}.${column.name}`}
                          checked={!!column.pii}
                          onChange={(e) => handlePiiToggle(table, column, e.target.checked)}
                          label="PII"
                        />
                      </Col>
                      <Col>
                        <Form.Select
                          disabled={!column.pii}
                          aria-label={`PII subtype for ${table}.${column.name}`}
                          value={column.piiSubtype || ''}
                          onChange={(e) =>
                            handlePiiSubtype(
                              table,
                              column,
                              (e.target.value || undefined) as NonNullable<Column['piiSubtype']> | undefined
                            )
                          }
                        >
                          <option value="">(none)</option>
                          {piiOptions.map((p) => (
                            <option key={p} value={p}>
                              {p}
                            </option>
                          ))}
                        </Form.Select>
                      </Col>
                    </Row>
                  </td>
                  <td>
                    {(() => {
                      const key = `${table}.${column.name}`
                      const s = suggestionsByKey[key]
                      if (!s) return <span className="text-muted">—</span>
                      const pop = (
                        <Popover id={`why-${idx}`}>
                          <Popover.Header as="h3">Why this suggestion?</Popover.Header>
                          <Popover.Body>
                            <div className="small">{s.reason || 'No additional context.'}</div>
                          </Popover.Body>
                        </Popover>
                      )
                      return (
                        <div className="d-flex align-items-center gap-2">
                          <span className="badge bg-info text-dark" title="Confidence">{typeof s.confidence === 'number' ? `${Math.round(s.confidence * 100)}%` : 'n/a'}</span>
                          <OverlayTrigger trigger={["hover", "focus"]} placement="left" overlay={pop}>
                            <Button variant="outline-secondary" size="sm" aria-label="Why this suggestion?">Why?</Button>
                          </OverlayTrigger>
                          {(() => {
                            const before = { provider: column.provider, providerConfig: column.providerConfig, pii: column.pii, piiSubtype: column.piiSubtype }
                            const after = {
                              provider: s.provider ?? column.provider,
                              providerConfig: s.providerConfig ?? column.providerConfig,
                              pii: typeof s.pii === 'boolean' ? s.pii : column.pii,
                              piiSubtype: s.piiSubtype ?? column.piiSubtype,
                            }
                            const changedProvider = Boolean(before.provider && s.provider && s.provider !== before.provider)
                            const changedConfig = Boolean(before.providerConfig && JSON.stringify(before.providerConfig) !== JSON.stringify(after.providerConfig))
                            const changedPii = typeof s.pii === 'boolean' && s.pii !== before.pii
                            const changedSubtype = Boolean(s.piiSubtype && s.piiSubtype !== before.piiSubtype)
                            const overwritesManual = changedProvider || changedConfig || changedPii || changedSubtype
                            if (!overwritesManual) return null

                            const details: string[] = []
                            if (changedProvider) details.push(`provider: ${String(before.provider)} → ${String(after.provider)}`)
                            if (changedConfig) details.push('config: will be updated')
                            if (changedPii) details.push(`PII: ${String(before.pii)} → ${String(after.pii)}`)
                            if (changedSubtype) details.push(`PII subtype: ${String(before.piiSubtype ?? 'none')} → ${String(after.piiSubtype ?? 'none')}`)

                            const pop = (
                              <Popover id={`overwrite-${idx}`}>
                                <Popover.Header as="h3">Overwrites manual values</Popover.Header>
                                <Popover.Body>
                                  <ul className="mb-0 ps-3">
                                    {details.map((d, i) => (
                                      <li key={i} className="small">{d}</li>
                                    ))}
                                  </ul>
                                </Popover.Body>
                              </Popover>
                            )

                            return (
                              <OverlayTrigger trigger={["hover", "focus"]} placement="top" overlay={pop}>
                                <span className="badge bg-warning text-dark" role="button" tabIndex={0} aria-label="Overwrites manual value (show details)">Overwrites manual</span>
                              </OverlayTrigger>
                            )
                          })()}
                          <Button variant="success" size="sm" onClick={() => applySuggestion(table, column)} aria-label={`Apply suggestion for ${table}.${column.name}`}>
                            Apply
                          </Button>
                        </div>
                      )
                    })()}
                  </td>
                </tr>
              )
            })
          )}
        </tbody>
      </Table>

      <SuggestionsDiffModal
        show={showDiff}
        onHide={() => setShowDiff(false)}
        diffs={diffs}
        onConfirm={handleApplyDiffs}
      />
      </>
      )}
    </div>
  )
}
