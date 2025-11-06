import { useEffect, useMemo, useState } from 'react'
import { Alert, Button, Col, Form, Row, Table, ToggleButton, ToggleButtonGroup, OverlayTrigger, Tooltip } from 'react-bootstrap'
import YAML from 'js-yaml'
import { useWizard } from '../../state/wizard'
import type { Rule, ValidationReport } from '../../services/validation'
import type { EntitySchema, Table as EntityTable, Column as EntityColumn } from '../../state/wizard'
import { validateRules } from '../../services/validation'

function prettyJSON(obj: unknown) {
  try {
    return JSON.stringify(obj, null, 2)
  } catch {
    return ''
  }
}

function safeParseJSON(text: string): unknown | Error {
  try {
    return JSON.parse(text)
  } catch (e) {
    return e as Error
  }
}

function safeParseYAML(text: string): unknown | Error {
  try {
    return YAML.load(text)
  } catch (e) {
    return e as Error
  }
}

function toNormalizedRules(obj: unknown): Rule[] | string {
  if (!obj || typeof obj !== 'object') return 'YAML/JSON must define an array under `rules`.'
  const rules = (obj as { rules?: unknown }).rules
  if (!Array.isArray(rules)) return 'Missing `rules` array.'
  // Light structural check
  const normalized: Rule[] = []
  for (const r of rules) {
    if (!r || typeof r !== 'object') return 'Each rule must be an object.'
    if (r.type === 'implication') {
      if (!r.table || !r.when || !Array.isArray(r.then)) return 'Implication rule requires table, when, then[]'
      normalized.push({ type: 'implication', table: String(r.table), when: String(r.when), then: r.then.map(String) })
    } else if (r.type === 'uniqueness') {
      if (!r.table || !Array.isArray(r.columns)) return 'Uniqueness rule requires table and columns[]'
      normalized.push({ type: 'uniqueness', table: String(r.table), columns: r.columns.map(String) })
    } else if (r.type === 'distribution') {
      if (!r.table || !r.column || typeof r.probs !== 'object') return 'Distribution rule requires table, column, and probs{ }'
      const probsRec: Record<string, number> = {}
      for (const [k, v] of Object.entries(r.probs as Record<string, unknown>)) probsRec[String(k)] = Number(v)
      normalized.push({ type: 'distribution', table: String(r.table), column: String(r.column), probs: probsRec })
    } else if (r.type === 'temporal') {
      if (!r.table || !r.left || !r.op || !r.right?.column) return 'Temporal rule requires table, left, op, right{column, offset_days}'
      normalized.push({ type: 'temporal', table: String(r.table), left: String(r.left), op: r.op, right: { column: String(r.right.column), offset_days: Number(r.right.offset_days ?? 0) } })
    } else {
      return `Unknown rule type: ${String((r as { type?: unknown }).type)}`
    }
  }
  return normalized
}

export default function RulesPage() {
  const { state } = useWizard()
  const entity: EntitySchema | undefined = state.entities.find((e) => e.id === state.selectedEntityId) || state.entities[0]

  const [source, setSource] = useState<'yaml' | 'json'>('yaml')
  const [yamlText, setYamlText] = useState<string>(() => {
    // Initial scaffold
    return `rules:\n  - type: uniqueness\n    table: ${entity?.tables?.[0]?.name || 'table'}\n    columns: [${entity?.tables?.[0]?.columns?.[0]?.name || 'id'}]\n`
  })
  const [jsonText, setJsonText] = useState<string>('')
  const [lintMessages, setLintMessages] = useState<string[]>([])
  const [parseError, setParseError] = useState<string | null>(null)
  const [report, setReport] = useState<ValidationReport | null>(null)
  const [sending, setSending] = useState(false)

  // Mirror other pane
  useEffect(() => {
    if (source === 'yaml') {
      const parsed = safeParseYAML(yamlText)
      if (parsed instanceof Error) {
        setParseError(parsed.message)
        return
      }
      setParseError(null)
      setJsonText(prettyJSON(parsed))
    } else {
      const parsed = safeParseJSON(jsonText)
      if (parsed instanceof Error) {
        setParseError(parsed.message)
        return
      }
      setParseError(null)
      try { setYamlText(YAML.dump(parsed as object)); } catch (_e) { /* ignore */ }
    }
  }, [source, yamlText, jsonText])

  const rules: Rule[] | null = useMemo(() => {
    const raw = source === 'yaml' ? safeParseYAML(yamlText) : safeParseJSON(jsonText)
    if (raw instanceof Error) return null
    const normalized = toNormalizedRules(raw)
    if (typeof normalized === 'string') return null
    return normalized
  }, [source, yamlText, jsonText])

  // Inline lints based on entity schema
  useEffect(() => {
  const msgs: string[] = []
    if (!rules || !entity) { setLintMessages(msgs); return }
  const tableMap = new Map<string, EntityTable>(entity.tables.map((t: EntityTable) => [t.name, t]))
  function hasColumn(table: string, col: string) { return (tableMap.get(table)?.columns || []).some((c: EntityColumn) => c.name === col) }
  function dtypeOf(table: string, col: string) { return (tableMap.get(table)?.columns || []).find((c: EntityColumn) => c.name === col)?.dtype }

    for (const r of rules) {
      if (r.type === 'uniqueness') {
        if (!tableMap.has(r.table)) msgs.push(`uniqueness: table '${r.table}' does not exist`)
        for (const c of r.columns) if (!hasColumn(r.table, c)) msgs.push(`uniqueness: column '${r.table}.${c}' not found`)
      } else if (r.type === 'distribution') {
        if (!hasColumn(r.table, r.column)) msgs.push(`distribution: column '${r.table}.${r.column}' not found`)
        // If the column has categorical provider with categories, ensure keys match
        const col = (tableMap.get(r.table)?.columns || []).find((cc: EntityColumn) => cc.name === r.column)
        const cats = (col?.provider === 'categorical' ? (col.providerConfig as { categories?: Array<{ value: string }> })?.categories : undefined)
        if (cats && cats.length > 0) {
          const catValues = new Set(cats.map((x) => x.value))
          for (const k of Object.keys(r.probs)) if (!catValues.has(k)) msgs.push(`distribution: key '${k}' not in categorical values for ${r.table}.${r.column}`)
        }
      } else if (r.type === 'temporal') {
        const leftParts = r.left.split('.')
        if (leftParts.length !== 2) msgs.push(`temporal: left must be 'table.column' got '${r.left}'`)
        const lt = leftParts[0]; const lc = leftParts[1]
        if (!hasColumn(lt, lc)) msgs.push(`temporal: column '${r.left}' not found`)
        const rightCol = `${r.table}.${r.right.column}`
        if (!hasColumn(r.table, r.right.column)) msgs.push(`temporal: right column '${rightCol}' not found`)
        const ld = dtypeOf(lt, lc); const rd = dtypeOf(r.table, r.right.column)
        const isDate = (d?: string) => d === 'date' || d === 'timestamp'
        if (ld && !isDate(ld)) msgs.push(`temporal: left '${r.left}' is not a date/timestamp column`)
        if (rd && !isDate(rd)) msgs.push(`temporal: right '${rightCol}' is not a date/timestamp column`)
      }
    }
    setLintMessages(msgs)
  }, [rules, entity])

  async function onDryRunValidate() {
    setSending(true)
    setReport(null)
    try {
      const payload: { rules: Rule[] | null } = { rules }
      const res = await validateRules(payload)
      setReport(res.report || null)
    } catch (e) {
      // Shallow error surface
      setReport({ sample: [], final: [] })
    } finally {
      setSending(false)
    }
  }

  return (
    <div>
      {!entity && <Alert variant="info">Select or create an entity first.</Alert>}

      <div className="d-flex justify-content-between align-items-center mb-2">
        <div className="d-flex align-items-center gap-2">
          <strong>Edit source:</strong>
          <ToggleButtonGroup type="radio" name="source" value={source} onChange={(val: 'yaml'|'json') => setSource(val)} aria-label="Select rules edit source">
            <ToggleButton id="src-yaml" value={'yaml'} size="sm" variant={source==='yaml'?'primary':'outline-primary'} aria-label="Edit YAML">YAML</ToggleButton>
            <ToggleButton id="src-json" value={'json'} size="sm" variant={source==='json'?'primary':'outline-primary'} aria-label="Edit JSON">JSON</ToggleButton>
          </ToggleButtonGroup>
        </div>
        <div className="d-flex align-items-center gap-2">
          <OverlayTrigger placement="left" overlay={<Tooltip>Run a server-side check without saving rules</Tooltip>}>
            <Button onClick={onDryRunValidate} disabled={sending || !rules || parseError!==null} aria-label="Dry-run validate rules"> {sending ? 'Validating…' : 'Dry-run validate'} </Button>
          </OverlayTrigger>
        </div>
      </div>

      {parseError && <Alert variant="danger">Parse error: {parseError}</Alert>}
      {lintMessages.length > 0 && (
        <Alert variant="warning">
          <ul className="mb-0">
            {lintMessages.map((m, i) => (
              <li key={i}>{m}</li>
            ))}
          </ul>
        </Alert>
      )}

      <Row>
        <Col md={6}>
          <Form.Group controlId="rulesYaml">
            <Form.Label>YAML</Form.Label>
            <Form.Control as="textarea" rows={18} value={yamlText} onChange={(e) => setYamlText(e.target.value)} disabled={source!=='yaml'} aria-label="Rules YAML editor" />
          </Form.Group>
        </Col>
        <Col md={6}>
          <Form.Group controlId="rulesJson">
            <Form.Label>JSON</Form.Label>
            <Form.Control as="textarea" rows={18} value={jsonText} onChange={(e) => setJsonText(e.target.value)} disabled={source!=='json'} aria-label="Rules JSON editor" />
            <Form.Text muted>Switch edit source to modify this pane.</Form.Text>
          </Form.Group>
        </Col>
      </Row>

      {report && (
        <div className="mt-3">
          <h6>Validation report</h6>
          <Row>
            <Col md={6}>
              <strong>Sample</strong>
              <ReportTable results={report.sample} />
            </Col>
            <Col md={6}>
              <strong>Final</strong>
              <ReportTable results={report.final} />
            </Col>
          </Row>
        </div>
      )}
    </div>
  )
}

function ReportTable({ results }: { results: NonNullable<ValidationReport['sample']> }) {
  const rows = results || []
  type BaseRow = { type?: string; table?: string; checked?: number; violations?: number; violation_rate?: number; stat?: { pass?: boolean } }
  const passCount = rows.filter((r) => (r as BaseRow).stat ? Boolean((r as BaseRow).stat?.pass) : (((r as BaseRow).violations ?? 0) === 0)).length
  const failCount = rows.length - passCount
  return (
    <div>
      <div className="mb-2">Pass: <strong>{passCount}</strong> · Fail: <strong>{failCount}</strong></div>
      <Table bordered size="sm">
        <thead>
          <tr>
            <th>Type</th>
            <th>Table</th>
            <th>Checked</th>
            <th>Violations</th>
            <th>Rate</th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={5} className="text-muted text-center">No results</td>
            </tr>
          ) : (
            rows.slice(0, 10).map((r, i) => (
              <tr key={i}>
                <td>{r.type}</td>
                <td>{r.table}</td>
                <td>{r.checked ?? '-'}</td>
                <td>{r.violations ?? '-'}</td>
                <td>{r.violation_rate?.toFixed?.(3) ?? '-'}</td>
              </tr>
            ))
          )}
        </tbody>
      </Table>
    </div>
  )
}
