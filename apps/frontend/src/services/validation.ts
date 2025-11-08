import api from './api'

export type Rule =
  | { type: 'implication'; table: string; when: string; then: string[] }
  | { type: 'uniqueness'; table: string; columns: string[] }
  | { type: 'distribution'; table: string; column: string; probs: Record<string, number> }
  | { type: 'temporal'; table: string; left: string; op: '<='|'<'|'>='|'>'|'=='|'!='; right: { column: string; offset_days: number } }

export type RuleResult = {
  type: string
  table: string
  checked?: number
  violations?: number
  violation_rate?: number
  samples?: unknown[]
  stat?: { n: number; chi2: number; df: number; critical: number; pass: boolean }
  observed?: Record<string, number>
}

export type ValidationReport = { sample: RuleResult[]; final: RuleResult[] }

// Accept unknown payload; caller is responsible for supplying a shape the backend understands.
export async function validateRules(body: unknown) {
  const res = await api.post('/api/v1/validate', body)
  return res.data as { rules?: Rule[]; report?: ValidationReport }
}
