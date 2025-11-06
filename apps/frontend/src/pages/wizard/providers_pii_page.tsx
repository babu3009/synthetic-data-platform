import { useMemo, useState } from 'react'
import { Alert, Button, Col, Form, Modal, Row, Table } from 'react-bootstrap'
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
  }>
  onConfirm: () => void
}) {
  return (
    <Modal show={show} onHide={onHide} size="lg">
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
                <th>Before</th>
                <th>After</th>
              </tr>
            </thead>
            <tbody>
              {diffs.map((d, i) => (
                <tr key={i}>
                  <td>{d.table}</td>
                  <td>{d.column}</td>
                  <td>
                    <code>{JSON.stringify(d.before)}</code>
                  </td>
                  <td>
                    <code>{JSON.stringify(d.after)}</code>
                  </td>
                </tr>
              ))}
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
    Array<{ table: string; column: string; before: Partial<Column>; after: Partial<Column> }>
  >([])
  const [showDiff, setShowDiff] = useState(false)

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
      const diffs: Array<{ table: string; column: string; before: Partial<Column>; after: Partial<Column> }> = []
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
        if (JSON.stringify(before) !== JSON.stringify(after)) diffs.push({ table: s.table, column: s.column, before, after })
      }
      setDiffs(diffs)
      setShowDiff(true)
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      const msg = e instanceof Error ? e.message : undefined
      setError(detail || msg || 'Failed to infer providers')
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
          <Form.Select size="sm" value={tableFilter} onChange={(e) => setTableFilter(e.target.value)}>
            <option value="__all__">All tables</option>
            {tables.map((t) => (
              <option key={t.name} value={t.name}>
                {t.name}
              </option>
            ))}
          </Form.Select>
          <Button variant="secondary" size="sm" onClick={handleSuggest} disabled={loadingSuggest}>
            {loadingSuggest ? 'Suggesting…' : 'Auto-suggest providers'}
          </Button>
          <Button size="sm" onClick={handleSave} disabled={saving}>
            {saving ? 'Saving…' : 'Save'}
          </Button>
        </div>
      </div>

      <Table bordered hover size="sm">
        <thead>
          <tr>
            <th>Table</th>
            <th>Column</th>
            <th>Type</th>
            <th>Provider</th>
            <th>Config (JSON)</th>
            <th>PII</th>
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
                      value={column.provider || ''}
                      onChange={(e) => handleProviderChange(table, column, (e.target.value || undefined) as Column['provider'])}
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
                      value={cfgText}
                      onChange={(e) => handleConfigChange(table, column, e.target.value)}
                      placeholder={column.provider === 'pattern' ? '{"mask":"AA-9999"}' : column.provider === 'categorical' ? '{"categories":[{"value":"A","weight":0.5}]}' : '{}'}
                      isInvalid={!!validation}
                    />
                    {validation && <Form.Control.Feedback type="invalid">{validation}</Form.Control.Feedback>}
                  </td>
                  <td>
                    <Row className="g-1">
                      <Col xs="auto" className="d-flex align-items-center">
                        <Form.Check
                          type="switch"
                          checked={!!column.pii}
                          onChange={(e) => handlePiiToggle(table, column, e.target.checked)}
                          label="PII"
                        />
                      </Col>
                      <Col>
                        <Form.Select
                          disabled={!column.pii}
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
