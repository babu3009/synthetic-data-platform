import { useMemo, useState, useEffect } from 'react'
import { Alert, Button, Col, Form, Modal, Row, Table, OverlayTrigger, Tooltip, Popover } from 'react-bootstrap'
import { useWizard, type Column } from '../../state/wizard'
import { inferProviders, autosaveProviders, type ProviderSuggestion } from '../../services/providers'
import { autosaveEntity, updateEntity } from '../../services/entities'
import { useAutosave } from '../../hooks/use_autosave'
import ProviderConfigBuilder from '../../components/provider_config_builder'

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
  const [selectedEntityId, setSelectedEntityId] = useState<string | undefined>(state.selectedEntityId)
  const entity = state.entities.find((e) => e.id === selectedEntityId) || state.entities[0]
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
  const [autoSuggestedFor, setAutoSuggestedFor] = useState<string | null>(null)
  
  // Config builder state
  const [showConfigBuilder, setShowConfigBuilder] = useState(false)
  const [configBuilderContext, setConfigBuilderContext] = useState<{
    tableName: string
    column: Column
    provider: NonNullable<Column['provider']>
  } | null>(null)

  const projectId = state.projectId || 'default'

  // Sync local selectedEntityId with wizard state
  useEffect(() => {
    if (state.selectedEntityId && state.selectedEntityId !== selectedEntityId) {
      setSelectedEntityId(state.selectedEntityId)
    }
  }, [state.selectedEntityId, selectedEntityId])

  const tables = useMemo(() => entity?.tables || [], [entity])
  
  // Auto-suggest providers on first load if none are configured
  const hasConfiguredProviders = useMemo(() => {
    if (!entity) return true
    return entity.tables.some(t => 
      t.columns.some(c => c.provider || c.pii)
    )
  }, [entity])
  
  // Auto-trigger suggestion on first load for entities without providers
  useEffect(() => {
    if (!entity || hasConfiguredProviders || autoSuggestedFor === entity.id || loadingSuggest) return
    
    // Auto-trigger suggestion and auto-apply high confidence ones
    const autoSuggestAndApply = async () => {
      try {
        setAutoSuggestedFor(entity.id)
        setLoadingSuggest(true)
        
        const suggestions = (await inferProviders(projectId, entity)) as ProviderSuggestion[]
        
        // Auto-apply high confidence suggestions (>= 0.7)
        const highConfidence = suggestions.filter(s => (s.confidence ?? 0) >= 0.7)
        
        if (highConfidence.length > 0) {
          dispatch({ type: 'applyProviderSuggestions', entityId: entity.id, suggestions: highConfidence })
          
          // Calculate summary counts
          let providerCount = 0
          let piiCount = 0
          for (const s of highConfidence) {
            if (s.provider) providerCount++
            if (s.pii) piiCount++
          }
          
          setSummaryCounts({ providers: providerCount, pii: piiCount })
        }
        
        // Store remaining lower-confidence suggestions for manual review
        const remaining = suggestions.filter(s => (s.confidence ?? 0) < 0.7)
        const map: Record<string, ProviderSuggestion> = {}
        for (const s of remaining) {
          map[`${s.table}.${s.column}`] = s
        }
        setSuggestionsByKey(map)
        
      } catch (e) {
        // Silently fail auto-suggestion
        console.warn('Auto-suggestion failed:', e)
      } finally {
        setLoadingSuggest(false)
      }
    }
    
    // Delay slightly to avoid flash on page load
    const timer = setTimeout(autoSuggestAndApply, 500)
    
    return () => clearTimeout(timer)
  }, [entity?.id, hasConfiguredProviders, autoSuggestedFor, loadingSuggest])
  
  const groupedByTable = useMemo(() => {
    const groups: Record<string, Column[]> = {}
    if (!entity) return groups
    for (const t of entity.tables) {
      if (tableFilter !== '__all__' && t.name !== tableFilter) continue
      groups[t.name] = t.columns
    }
    return groups
  }, [entity, tableFilter])

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
    
    // Auto-open config builder for providers that require configuration
    if (provider && ['pattern', 'categorical', 'expression', 'reference'].includes(provider)) {
      setConfigBuilderContext({ tableName: table, column: col, provider })
      setShowConfigBuilder(true)
    }
  }
  
  function openConfigBuilder(table: string, col: Column) {
    if (!col.provider) return
    setConfigBuilderContext({ tableName: table, column: col, provider: col.provider })
    setShowConfigBuilder(true)
  }
  
  function handleConfigBuilderSave(config: Record<string, unknown>) {
    if (!configBuilderContext) return
    dispatch({
      type: 'updateColumn',
      entityId: entity.id,
      tableName: configBuilderContext.tableName,
      columnName: configBuilderContext.column.name,
      patch: { providerConfig: config }
    })
    setShowConfigBuilder(false)
    setConfigBuilderContext(null)
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
    if (!entity || !projectId) return
    setSaving(true)
    setError(null)
    try {
      // Save entity schema to database (includes all provider configurations)
      const updatedTables = entity.tables || []
      
      await updateEntity(projectId, entity.id, { 
        tables: updatedTables,
        relationships: entity.relationships,
        layout: entity.layout
      })
      
      // Update local state to mark as saved
      dispatch({ 
        type: 'updateEntity', 
        id: entity.id, 
        patch: { 
          tables: entity.tables,
          relationships: entity.relationships,
          layout: entity.layout
        } 
      })
      
      // Clear dirty flag
      dispatch({ type: 'clearDirty' })
      
      // Show success feedback
      const successMsg = document.createElement('div')
      successMsg.className = 'alert alert-success position-fixed top-0 start-50 translate-middle-x mt-3'
      successMsg.style.zIndex = '9999'
      successMsg.textContent = '✓ Provider and PII settings saved to database'
      document.body.appendChild(successMsg)
      setTimeout(() => successMsg.remove(), 2000)
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      const msg = e instanceof Error ? e.message : undefined
      setError(detail || msg || 'Failed to save provider settings')
      console.error('Failed to save providers:', e)
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
          <Form.Select 
            size="sm" 
            value={selectedEntityId || ''} 
            onChange={(e) => {
              const newId = e.target.value
              setSelectedEntityId(newId)
              dispatch({ type: 'setSelectedEntity', id: newId })
            }}
            style={{ width: 'auto', maxWidth: '300px' }}
            aria-label="Select entity"
          >
            {state.entities.map((e) => (
              <option key={e.id} value={e.id}>
                {e.name} {e.version ? `(v${e.version})` : ''}
              </option>
            ))}
          </Form.Select>
          <span className="badge bg-info text-dark">
            <i className="bi bi-funnel"></i> Entity-specific filtering
          </span>
          {!hasConfiguredProviders && autoSuggestedFor === entity?.id && (
            <Alert variant="info" className="mb-0 py-1 px-2 small d-inline-block">
              <i className="bi bi-magic"></i> Auto-suggesting best providers...
            </Alert>
          )}
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
          {Object.keys(groupedByTable).length === 0 ? (
            <tr>
              <td colSpan={6} className="text-center text-muted">
                No columns
              </td>
            </tr>
          ) : (
            Object.entries(groupedByTable).flatMap(([tableName, columns]) => [
              // Table header row
              <tr key={`header-${tableName}`} className="table-active">
                <td colSpan={6} className="fw-bold py-2 bg-light">
                  {tableName}
                </td>
              </tr>,
              // Column rows for this table
              // Column rows for this table
              ...columns.map((column, colIdx) => {
                const table = tableName
                const idx = visibleRows.findIndex(r => r.table === table && r.column.name === column.name)
                const cfgText = column.providerConfig ? JSON.stringify(column.providerConfig, null, 0) : ''
                const validation = validateConfig(column.provider, column.providerConfig)
                return (
                  <tr key={`${table}.${column.name}.${colIdx}`}>
                    <td className="ps-4">{column.name}</td>
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
                    <div className="d-flex gap-1 align-items-start">
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
                        className="flex-grow-1"
                      />
                      {column.provider && (
                        <Button
                          variant="outline-primary"
                          size="sm"
                          onClick={() => openConfigBuilder(table, column)}
                          title="Open guided config builder"
                          aria-label={`Configure ${column.provider} provider for ${table}.${column.name}`}
                        >
                          <i className="bi bi-gear-fill"></i>
                        </Button>
                      )}
                    </div>
                    {validation && <Form.Control.Feedback type="invalid" className="d-block">{validation}</Form.Control.Feedback>}
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
            ])
          )}
        </tbody>
      </Table>

      <SuggestionsDiffModal
        show={showDiff}
        onHide={() => setShowDiff(false)}
        diffs={diffs}
        onConfirm={handleApplyDiffs}
      />
      
      {configBuilderContext && (
        <ProviderConfigBuilder
          show={showConfigBuilder}
          onHide={() => {
            setShowConfigBuilder(false)
            setConfigBuilderContext(null)
          }}
          provider={configBuilderContext.provider}
          currentConfig={configBuilderContext.column.providerConfig}
          onSave={handleConfigBuilderSave}
          columnName={configBuilderContext.column.name}
          columnType={configBuilderContext.column.dtype}
        />
      )}
      </>
      )}
    </div>
  )
}
