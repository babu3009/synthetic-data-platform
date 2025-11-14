import React from 'react'
import { useParams } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { validateRules, type Rule, type ValidationReport, type RuleResult } from '../../services/validation'
import { useToasts } from '../../hooks/use_toasts'

type DraftRule =
  | ({ type: 'uniqueness'; table: string; columns: string[] } & { id: string })
  | ({ type: 'implication'; table: string; when: string; then: string[] } & { id: string })
  | ({ type: 'distribution'; table: string; column: string; probs: Record<string, number> } & { id: string })
  | ({ type: 'temporal'; table: string; left: string; op: '<='|'<'|'>='|'>'|'=='|'!='; right: { column: string; offset_days: number } } & { id: string })

const emptyUniqueness = (): DraftRule => ({ id: crypto.randomUUID(), type: 'uniqueness', table: '', columns: [] })
const emptyImplication = (): DraftRule => ({ id: crypto.randomUUID(), type: 'implication', table: '', when: '', then: [] })
const emptyDistribution = (): DraftRule => ({ id: crypto.randomUUID(), type: 'distribution', table: '', column: '', probs: {} })
const emptyTemporal = (): DraftRule => ({ id: crypto.randomUUID(), type: 'temporal', table: '', left: '', op: '<=', right: { column: '', offset_days: 0 } })

const ruleFactories: Record<string, () => DraftRule> = {
  uniqueness: emptyUniqueness,
  implication: emptyImplication,
  distribution: emptyDistribution,
  temporal: emptyTemporal,
}

const ValidationRulesPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>()
  const { push } = useToasts()
  const [rules, setRules] = React.useState<DraftRule[]>([])
  const [sampleOnly, setSampleOnly] = React.useState(true)
  const [report, setReport] = React.useState<ValidationReport | null>(null)
  const storageKey = React.useMemo(() => projectId ? `validation_rules_${projectId}` : 'validation_rules_', [projectId])

  // Load saved rules on mount
  React.useEffect(() => {
    try {
      const raw = localStorage.getItem(storageKey)
      if (raw) {
        const saved = JSON.parse(raw) as { rules?: DraftRule[]; sampleOnly?: boolean }
        if (saved.rules) setRules(saved.rules)
        if (typeof saved.sampleOnly === 'boolean') setSampleOnly(saved.sampleOnly)
      }
    } catch {
      // ignore
    }
  }, [storageKey])

  // Persist rules & toggle
  React.useEffect(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify({ rules, sampleOnly }))
    } catch {
      // ignore
    }
  }, [storageKey, rules, sampleOnly])

  function addRule(kind: keyof typeof ruleFactories) {
    setRules(r => [...r, ruleFactories[kind]()])
  }

  function updateRule<T extends DraftRule>(id: string, patch: Partial<T>) {
    setRules(r => r.map(rule => rule.id === id ? ({ ...rule, ...patch } as DraftRule) : rule))
  }

  function removeRule(id: string) {
    setRules(r => r.filter(rule => rule.id !== id))
  }

  const runMut = useMutation({
    mutationFn: async () => {
      // Backend contract: POST /api/v1/validate body with { project_id, sample_only, rules }
  const body = { project_id: projectId, sample_only: sampleOnly, rules: rules.map(r => { const { id: _id, ...rest } = r; return rest }) }
      return validateRules(body)
    },
    onSuccess: (resp) => {
      setReport(resp.report || null)
      push('success', 'Validation completed')
    },
    onError: (e: unknown) => push('error', e instanceof Error ? e.message : 'Validation failed'),
  })

  function rowPassFail(r: unknown): 'pass' | 'fail' {
    const rr = r as { type?: string; stat?: { pass?: boolean }; violations?: number }
    if (rr?.type === 'distribution') {
      return rr?.stat?.pass ? 'pass' : 'fail'
    }
    if (typeof rr?.violations === 'number') return rr.violations > 0 ? 'fail' : 'pass'
    return 'pass'
  }

  function renderRuleEditor(rule: DraftRule) {
    switch (rule.type) {
      case 'uniqueness': {
        const u = rule as Extract<Rule, { type: 'uniqueness' }> & { id: string }
        return (
          <div>
            <div className="mb-2">
              <label className="form-label">Table</label>
              <input aria-label="Uniqueness table" placeholder="table_name" className="form-control form-control-sm" value={u.table} onChange={e => updateRule(u.id, { table: e.target.value })} />
            </div>
            <div className="mb-2">
              <label className="form-label">Columns (comma separated)</label>
              <input aria-label="Uniqueness columns" placeholder="col1,col2" className="form-control form-control-sm" value={u.columns.join(',')} onChange={e => updateRule(u.id, { columns: e.target.value.split(',').map(s => s.trim()).filter(Boolean) })} />
            </div>
          </div>
        )
      }
      case 'implication': {
        const imp = rule as Extract<Rule, { type: 'implication' }> & { id: string }
        return (
          <div>
            <div className="mb-2">
              <label className="form-label">Table</label>
              <input aria-label="Implication table" placeholder="table_name" className="form-control form-control-sm" value={imp.table} onChange={e => updateRule(imp.id, { table: e.target.value })} />
            </div>
            <div className="mb-2">
              <label className="form-label">When (expression)</label>
              <input aria-label="Implication when" placeholder="expression" className="form-control form-control-sm" value={imp.when} onChange={e => updateRule(imp.id, { when: e.target.value })} />
            </div>
            <div className="mb-2">
              <label className="form-label">Then columns (comma separated)</label>
              <input aria-label="Implication then" placeholder="colA,colB" className="form-control form-control-sm" value={imp.then.join(',')} onChange={e => updateRule(imp.id, { then: e.target.value.split(',').map(s => s.trim()).filter(Boolean) })} />
            </div>
          </div>
        )
      }
      case 'distribution': {
        const d = rule as Extract<Rule, { type: 'distribution' }> & { id: string }
        return (
          <div>
            <div className="mb-2">
              <label className="form-label">Table</label>
              <input aria-label="Distribution table" placeholder="table_name" className="form-control form-control-sm" value={d.table} onChange={e => updateRule(d.id, { table: e.target.value })} />
            </div>
            <div className="mb-2">
              <label className="form-label">Column</label>
              <input aria-label="Distribution column" placeholder="column" className="form-control form-control-sm" value={d.column} onChange={e => updateRule(d.id, { column: e.target.value })} />
            </div>
            <div className="mb-2">
              <label className="form-label">Probabilities (key=prob per line)</label>
              <textarea aria-label="Distribution probabilities" placeholder="A=0.5\nB=0.5" className="form-control form-control-sm" rows={3} value={Object.entries(d.probs).map(([k,v]) => `${k}=${v}`).join('\n')} onChange={e => {
                const entries = e.target.value.split('\n').map(line => line.trim()).filter(Boolean)
                const probs: Record<string, number> = {}
                for (const line of entries) {
                  const [k,v] = line.split('=')
                  const num = parseFloat(v)
                  if (!isNaN(num)) probs[k] = num
                }
                updateRule(d.id, { probs })
              }} />
            </div>
          </div>
        )
      }
      case 'temporal': {
        const t = rule as Extract<Rule, { type: 'temporal' }> & { id: string }
        return (
          <div>
            <div className="mb-2">
              <label className="form-label">Table</label>
              <input aria-label="Temporal table" placeholder="table_name" className="form-control form-control-sm" value={t.table} onChange={e => updateRule(t.id, { table: e.target.value })} />
            </div>
            <div className="mb-2">
              <label className="form-label">Left Column</label>
              <input aria-label="Temporal left" placeholder="left_col" className="form-control form-control-sm" value={t.left} onChange={e => updateRule(t.id, { left: e.target.value })} />
            </div>
            <div className="mb-2">
              <label className="form-label">Operator</label>
              <select aria-label="Temporal operator" className="form-select form-select-sm" value={t.op} onChange={e => updateRule(t.id, { op: e.target.value as '<=' | '<' | '>=' | '>' | '==' | '!=' })}>
                {['<=','<','>=','>','==','!='].map(o => <option key={o} value={o}>{o}</option>)}
              </select>
            </div>
            <div className="mb-2">
              <label className="form-label">Right Column</label>
              <input aria-label="Temporal right column" placeholder="right_col" className="form-control form-control-sm" value={t.right.column} onChange={e => updateRule(t.id, { right: { ...t.right, column: e.target.value } })} />
            </div>
            <div className="mb-2">
              <label className="form-label">Right Offset (days)</label>
              <input aria-label="Temporal offset" placeholder="0" type="number" className="form-control form-control-sm" value={t.right.offset_days} onChange={e => updateRule(t.id, { right: { ...t.right, offset_days: parseInt(e.target.value,10) || 0 } })} />
            </div>
          </div>
        )
      }
      default:
        return null
    }
  }

  function ReportTable({ data, label }: { data: RuleResult[]; label: string }) {
    const [openIdx, setOpenIdx] = React.useState<number | null>(null)
    return (
      <div className="mb-4">
        <h6 className="mb-2">{label}</h6>
        <table className="table table-sm table-bordered">
          <thead>
            <tr>
              <th>Type</th>
              <th>Table</th>
              <th>Checked</th>
              <th>Violations</th>
              <th>Rate</th>
              <th>Stats</th>
              <th>Samples</th>
            </tr>
          </thead>
          <tbody>
            {data.map((r,i) => {
              const verdict = rowPassFail(r)
              const rowClass = verdict === 'pass' ? 'table-success' : 'table-danger'
              return (
                <React.Fragment key={i}>
                  <tr className={rowClass}>
                    <td>{r.type}</td>
                    <td>{r.table}</td>
                    <td>{r.checked ?? '—'}</td>
                    <td>{r.violations ?? '—'}</td>
                    <td>{r.violation_rate != null ? (r.violation_rate * 100).toFixed(2) + '%' : '—'}</td>
                    <td>{r.stat ? `chi2=${r.stat.chi2 ?? '—'} df=${r.stat.df ?? '—'} pass=${r.stat.pass ? 'yes' : 'no'}` : '—'}</td>
                    <td>
                      {Array.isArray(r.samples) && r.samples.length > 0 ? (
                        <button className="btn btn-sm btn-outline-secondary" onClick={() => setOpenIdx(openIdx === i ? null : i)}>
                          {openIdx === i ? 'Hide' : 'View'} samples
                        </button>
                      ) : '—'}
                    </td>
                  </tr>
                  {openIdx === i && Array.isArray(r.samples) && r.samples.length > 0 && (
                    <tr className={rowClass}>
                      <td colSpan={7}>
                        <pre className="mb-0 small pre-wrap">{JSON.stringify(r.samples.slice(0,5), null, 2)}</pre>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              )
            })}
          </tbody>
        </table>
      </div>
    )
  }

  function renderReport() {
    if (!report) return null
    if (sampleOnly) {
      const data = (report.sample || []) as RuleResult[]
      if (data.length === 0) return <div className="alert alert-info">No results returned.</div>
      return <ReportTable data={data} label="Sample" />
    }
    const blocks: JSX.Element[] = []
    if (report.sample && report.sample.length > 0) blocks.push(<ReportTable key="sample" data={report.sample as RuleResult[]} label="Sample" />)
    if (report.final && report.final.length > 0) blocks.push(<ReportTable key="final" data={report.final as RuleResult[]} label="Final" />)
    if (blocks.length === 0) return <div className="alert alert-info">No results returned.</div>
    return <>{blocks}</>
  }

  return (
    <div className="container py-4">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h2 className="mb-0">Validation Rules</h2>
        <div className="d-flex gap-2">
          <select className="form-select form-select-sm" aria-label="Add Rule" onChange={e => { if (e.target.value) { addRule(e.target.value as keyof typeof ruleFactories); e.target.value = '' } }} defaultValue="">
            <option value="" disabled>Add Rule...</option>
            {Object.keys(ruleFactories).map(k => <option key={k} value={k}>{k}</option>)}
          </select>
          <div className="form-check form-check-inline">
            <input className="form-check-input" type="checkbox" id="sampleOnly" checked={sampleOnly} onChange={e => setSampleOnly(e.target.checked)} />
            <label className="form-check-label" htmlFor="sampleOnly">Sample Only</label>
          </div>
          <button className="btn btn-primary btn-sm" disabled={rules.length === 0 || runMut.isPending} onClick={() => runMut.mutate()}>{runMut.isPending ? 'Running…' : 'Run'}</button>
          <button className="btn btn-outline-secondary btn-sm" disabled={runMut.isPending || rules.length === 0} onClick={() => { setRules([]); setReport(null) }}>Clear</button>
        </div>
      </div>

      {rules.length === 0 && <div className="text-muted mb-3">No rules added. Use the dropdown to add one.</div>}

      <div className="row g-3 mb-4">
        {rules.map(rule => (
          <div className="col-md-6" key={rule.id}>
            <div className="card p-3 position-relative">
              <button type="button" className="btn-close position-absolute top-0 end-0 m-2" aria-label="Remove" onClick={() => removeRule(rule.id)}></button>
              <h6 className="fw-semibold text-uppercase mb-2">{rule.type}</h6>
              {renderRuleEditor(rule)}
            </div>
          </div>
        ))}
      </div>

      <h5 className="mb-2">Report</h5>
      {runMut.isPending && <div className="skeleton skeleton-line40 mb-3" />}
      {renderReport()}
    </div>
  )
}

export default ValidationRulesPage
