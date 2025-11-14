import React from 'react'
import { useMutation } from '@tanstack/react-query'
import { flatPreview } from '../services/flat'
import { useToasts } from '../hooks/use_toasts'

const exampleSchema = {
  columns: [
    { name: 'id', provider: { type: 'sequence', start: 1 } },
    { name: 'email', provider: { type: 'faker', method: 'email' } },
    { name: 'age', provider: { type: 'distribution', probs: { '18-29': 0.3, '30-44': 0.4, '45-64': 0.2, '65+': 0.1 } } }
  ]
}

const FlatPreviewPage: React.FC = () => {
  const { push } = useToasts()
  const [jsonText, setJsonText] = React.useState(JSON.stringify(exampleSchema, null, 2))
  const [n, setN] = React.useState(10)
  const [rows, setRows] = React.useState<Array<Record<string, unknown>>>([])
  
  const exampleText = React.useMemo(() => JSON.stringify(exampleSchema, null, 2), [])
  
  // Parse JSON and validate schema eagerly to drive UX state (button disable + helper text)
  const { parsed: parsedSchema, parseError } = React.useMemo(() => {
    try {
      return { parsed: JSON.parse(jsonText) as unknown, parseError: null as string | null }
    } catch (e) {
      return { parsed: null as unknown, parseError: 'Invalid JSON' as string | null }
    }
  }, [jsonText])

  // Lightweight client-side schema validation for quick feedback
  function validateSchema(raw: unknown): string | null {
    if (!raw || typeof raw !== 'object') return 'Schema must be a JSON object with a columns array.'
    const obj = raw as { columns?: unknown }
    if (!Array.isArray(obj.columns)) return 'Schema must include a "columns" array.'
    for (const [idx, col] of obj.columns.entries()) {
      if (!col || typeof col !== 'object') return `Column at index ${idx} must be an object.`
      const c = col as { name?: unknown; provider?: unknown }
      if (typeof c.name !== 'string' || c.name.length === 0) return `Column at index ${idx} missing valid name.`
      if (!c.provider || typeof c.provider !== 'object') return `Column "${c.name}" missing provider object.`
      const p = c.provider as { type?: unknown }
      if (typeof p.type !== 'string' || p.type.length === 0) return `Column "${c.name}" provider.type is required.`
    }
    return null
  }

  const schemaError = React.useMemo(() => {
    if (parseError) return parseError
    return validateSchema(parsedSchema)
  }, [parseError, parsedSchema])

  const columnCount = React.useMemo(() => {
    if (schemaError) return null as number | null
    if (!parsedSchema || typeof parsedSchema !== 'object') return null
    const cols = (parsedSchema as { columns?: unknown }).columns
    return Array.isArray(cols) ? cols.length : null
  }, [schemaError, parsedSchema])

  const resetToExample = React.useCallback(() => {
    setJsonText(exampleText)
    push('info', 'Schema reset to example')
  }, [exampleText, push])

  const copyExampleToClipboard = React.useCallback(async () => {
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(exampleText)
      } else {
        // Fallback for environments without clipboard API
        const ta = document.createElement('textarea')
        ta.value = exampleText
        ta.style.position = 'fixed'
        ta.style.opacity = '0'
        document.body.appendChild(ta)
        ta.select()
        document.execCommand('copy')
        document.body.removeChild(ta)
      }
      push('success', 'Example schema copied to clipboard')
    } catch {
      push('error', 'Failed to copy example schema')
    }
  }, [exampleText, push])

  const runMut = useMutation({
    mutationFn: async () => {
      try {
        const schema = parsedSchema
        const err = validateSchema(schema)
        if (err) throw new Error(err)
        const resp = await flatPreview({ schema, n })
        return resp
      } catch (e) {
        throw new Error(e instanceof Error ? e.message : 'Invalid JSON')
      }
    },
    onSuccess: (resp) => {
      setRows(resp.rows || [])
      push('success', `Preview generated (${resp.rows?.length ?? 0} rows)`) 
    },
    onError: (e: unknown) => {
      // Try to extract backend error message shape { detail } or { message }
      let msg = 'Preview failed'
      if (e instanceof Error && e.message) {
        msg = e.message
      } else if (typeof e === 'object' && e) {
        const resp = (e as Record<string, unknown>).response as Record<string, unknown> | undefined
        const data = resp?.data as Record<string, unknown> | undefined
        const detail = (data?.detail as string | undefined) || (data?.message as string | undefined)
        msg = detail || msg
      }
      push('error', msg)
    },
  })

  const headers = React.useMemo(() => {
    const set = new Set<string>()
    for (const r of rows) Object.keys(r || {}).forEach(k => set.add(k))
    return Array.from(set)
  }, [rows])

  return (
    <div className="container py-4">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h2 className="mb-0">Flat Preview</h2>
        <div className="d-flex align-items-center gap-2">
          <label className="form-label mb-0">Rows</label>
          <input aria-label="Rows to generate" type="number" min={1} max={200} className="form-control form-control-sm w-180" value={n} onChange={e => {
            const val = Math.max(1, Math.min(200, parseInt(e.target.value, 10) || 1))
            setN(val)
          }} />
          <button className="btn btn-primary" disabled={runMut.isPending || !!schemaError} onClick={() => runMut.mutate()}>{runMut.isPending ? 'Previewing…' : 'Preview'}</button>
          {!schemaError && typeof columnCount === 'number' && (
            <span className="badge bg-secondary" aria-label="Column count">Columns: {columnCount}</span>
          )}
        </div>
      </div>

      <div className="row g-3">
        <div className="col-md-6">
          <label className="form-label">Schema JSON</label>
          <textarea className="form-control" rows={20} value={jsonText} onChange={e => setJsonText(e.target.value)} aria-label="Schema JSON" />
          <div className="form-text">Provide a flat schema with provider configs. Example prefilled.</div>
          {schemaError && <div role="alert" className="text-danger small mt-1">{schemaError}</div>}
          <div className="mt-2 d-flex gap-2">
            <button type="button" className="btn btn-outline-secondary btn-sm" onClick={resetToExample} aria-label="Reset to example schema">Reset to example</button>
            <button type="button" className="btn btn-outline-secondary btn-sm" onClick={copyExampleToClipboard} aria-label="Copy example schema">Copy example</button>
          </div>
          <details className="mt-2">
            <summary>Schema tips</summary>
            <ul className="small mb-0">
              <li>Root must be an object with a <code>columns</code> array.</li>
              <li>Each column: <code>{'{ name: string, provider: { type: string, ... } }'}</code>.</li>
              <li>Common providers: <code>sequence</code>, <code>faker</code> (method), <code>distribution</code> (probs).</li>
              <li>Example:
                <pre className="mb-0 small pre-wrap">{JSON.stringify(exampleSchema, null, 2)}</pre>
              </li>
            </ul>
          </details>
        </div>
        <div className="col-md-6">
          <label className="form-label">Preview</label>
          {rows.length === 0 ? (
            <div className="text-muted">No rows yet. Click Preview to generate.</div>
          ) : (
            <div className="table-responsive border rounded">
              <table className="table table-sm table-striped mb-0">
                <thead>
                  <tr>
                    {headers.map(h => <th key={h}>{h}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r, i) => (
                    <tr key={i}>
                      {headers.map(h => <td key={h}>{String((r as Record<string, unknown>)[h] ?? '')}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default FlatPreviewPage
