import React, { createContext, useContext, useMemo, useReducer } from 'react'

export type Column = {
  name: string
  dtype: string
  nullable: boolean
  regex?: string
  distribution?: string
  // PII flags
  pii?: boolean
  piiSubtype?: 'email' | 'phone' | 'address' | 'national_id' | 'credit_card' | 'dob' | 'ip' | 'device'
  // Provider config
  provider?:
    | 'faker'
    | 'pattern'
    | 'sequence'
    | 'categorical'
    | 'expression'
    | 'geo'
    | 'checksum-valid'
    | 'reference'
    | 'empirical'
  providerConfig?: Record<string, unknown>
}

export type Table = {
  name: string
  columns: Column[]
  pk?: string[]
  uniques?: string[][]
  rowTarget?:
    | { type: 'absolute'; value: number }
    | { type: 'ratioTo'; table: string; ratio: number }
}

export type EntitySchema = {
  id: string
  name: string
  tables: Table[]
  updatedAt: string // ISO string
  relationships?: Relationship[]
  layout?: Record<string, { x: number; y: number }>
}

export type Relationship = {
  id: string
  sourceTable: string
  sourceColumn: string
  targetTable: string
  targetColumn: string
  cardinality: 'ONE_TO_ONE' | 'ONE_TO_MANY' | 'MANY_TO_MANY'
}

export type WizardState = {
  projectId?: string
  entities: EntitySchema[]
  selectedEntityId?: string
  activeTab?: 'entities' | 'diagram' | 'providers' | 'rules'
}

type Action =
  | { type: 'setProject'; projectId?: string }
  | { type: 'addEntity'; entity: Omit<EntitySchema, 'id' | 'updatedAt'> & Partial<Pick<EntitySchema, 'id' | 'updatedAt'>> }
  | { type: 'setSelectedEntity'; id?: string }
  | { type: 'setActiveTab'; tab: WizardState['activeTab'] }
  | { type: 'updateEntity'; id: string; patch: Partial<EntitySchema> }
  | { type: 'updateTable'; entityId: string; tableName: string; patch: Partial<Table> }
  | { type: 'updateColumn'; entityId: string; tableName: string; columnName: string; patch: Partial<Column> }
  | { type: 'togglePk'; entityId: string; tableName: string; columnName: string }
  | { type: 'upsertRelationship'; entityId: string; rel: Relationship }
  | { type: 'deleteRelationship'; entityId: string; relId: string }
  | { type: 'saveLayout'; entityId: string; layout: Record<string, { x: number; y: number }> }
  | {
      type: 'applyProviderSuggestions'
      entityId: string
      suggestions: Array<{
        table: string
        column: string
        provider?: Column['provider']
        providerConfig?: Record<string, unknown>
        pii?: boolean
        piiSubtype?: Column['piiSubtype']
      }>
    }

function reducer(state: WizardState, action: Action): WizardState {
  switch (action.type) {
    case 'setProject':
      return { ...state, projectId: action.projectId }
    case 'addEntity': {
      const id = action.entity.id ?? (typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : String(Date.now()))
      const updatedAt = action.entity.updatedAt ?? new Date().toISOString()
      const entity: EntitySchema = { id, updatedAt, name: action.entity.name, tables: action.entity.tables }
      return {
        ...state,
        entities: [entity, ...state.entities.filter((e) => e.id !== id)],
        selectedEntityId: id,
      }
    }
    case 'setSelectedEntity':
      return { ...state, selectedEntityId: action.id }
    case 'setActiveTab':
      return { ...state, activeTab: action.tab }
    case 'updateEntity': {
      const entities = state.entities.map((e) => (e.id === action.id ? { ...e, ...action.patch, updatedAt: new Date().toISOString() } : e))
      return { ...state, entities }
    }
    case 'updateTable': {
      const entities = state.entities.map((e) => {
        if (e.id !== action.entityId) return e
        const tables = e.tables.map((t) => (t.name === action.tableName ? { ...t, ...action.patch } : t))
        return { ...e, tables, updatedAt: new Date().toISOString() }
      })
      return { ...state, entities }
    }
    case 'updateColumn': {
      const entities = state.entities.map((e) => {
        if (e.id !== action.entityId) return e
        const tables = e.tables.map((t) => {
          if (t.name !== action.tableName) return t
          const cols = t.columns.map((c) => (c.name === action.columnName ? { ...c, ...action.patch } : c))
          return { ...t, columns: cols }
        })
        return { ...e, tables, updatedAt: new Date().toISOString() }
      })
      return { ...state, entities }
    }
    case 'togglePk': {
      const entities = state.entities.map((e) => {
        if (e.id !== action.entityId) return e
        const tables = e.tables.map((t) => {
          if (t.name !== action.tableName) return t
          const set = new Set(t.pk || [])
          if (set.has(action.columnName)) set.delete(action.columnName)
          else set.add(action.columnName)
          return { ...t, pk: Array.from(set) }
        })
        return { ...e, tables, updatedAt: new Date().toISOString() }
      })
      return { ...state, entities }
    }
    case 'upsertRelationship': {
      const entities = state.entities.map((e) => {
        if (e.id !== action.entityId) return e
        const rels = [...(e.relationships || [])]
        const idx = rels.findIndex((r) => r.id === action.rel.id)
        if (idx >= 0) rels[idx] = action.rel
        else rels.unshift(action.rel)
        return { ...e, relationships: rels, updatedAt: new Date().toISOString() }
      })
      return { ...state, entities }
    }
    case 'deleteRelationship': {
      const entities = state.entities.map((e) => {
        if (e.id !== action.entityId) return e
        const rels = (e.relationships || []).filter((r) => r.id !== action.relId)
        return { ...e, relationships: rels, updatedAt: new Date().toISOString() }
      })
      return { ...state, entities }
    }
    case 'saveLayout': {
      const entities = state.entities.map((e) => (e.id === action.entityId ? { ...e, layout: action.layout, updatedAt: new Date().toISOString() } : e))
      return { ...state, entities }
    }
    case 'applyProviderSuggestions': {
      const entities = state.entities.map((e) => {
        if (e.id !== action.entityId) return e
        const tables = e.tables.map((t) => {
          const suggestionsForTable = action.suggestions.filter((s) => s.table === t.name)
          if (suggestionsForTable.length === 0) return t
          const cols = t.columns.map((c) => {
            const s = suggestionsForTable.find((x) => x.column === c.name)
            if (!s) return c
            return {
              ...c,
              provider: s.provider ?? c.provider,
              providerConfig: s.providerConfig ?? c.providerConfig,
              pii: typeof s.pii === 'boolean' ? s.pii : c.pii,
              piiSubtype: s.piiSubtype ?? c.piiSubtype,
            }
          })
          return { ...t, columns: cols }
        })
        return { ...e, tables, updatedAt: new Date().toISOString() }
      })
      return { ...state, entities }
    }
    default:
      return state
  }
}

const WizardContext = createContext<{
  state: WizardState
  dispatch: React.Dispatch<Action>
} | null>(null)

export function WizardProvider({ children, initialProjectId }: { children: React.ReactNode; initialProjectId?: string }) {
  const [state, dispatch] = useReducer(reducer, {
    projectId: initialProjectId,
    entities: [],
    selectedEntityId: undefined,
    activeTab: 'entities',
  })

  const value = useMemo(() => ({ state, dispatch }), [state])
  return <WizardContext.Provider value={value}>{children}</WizardContext.Provider>
}

export function useWizard() {
  const ctx = useContext(WizardContext)
  if (!ctx) throw new Error('useWizard must be used within WizardProvider')
  return ctx
}

// Helpers to validate uniqueness
export function isEntityNameUnique(name: string, entities: EntitySchema[]) {
  return !entities.some((e) => e.name.trim().toLowerCase() === name.trim().toLowerCase())
}

// Mapping from backend canonical schema -> EntitySchema tables
type CanonicalColumn = { name: string; dtype: string; nullable: boolean }
type CanonicalTable = { name: string; columns?: CanonicalColumn[]; pk?: string[]; uniques?: string[][] }

export function tablesFromCanonicalSchema(schema: { tables: CanonicalTable[] }): Table[] {
  const tables = (schema?.tables ?? []).map((t) => ({
    name: String(t.name),
    columns: (t.columns ?? []).map((c) => ({ name: String(c.name), dtype: String(c.dtype), nullable: Boolean(c.nullable) })),
    pk: Array.isArray(t.pk) ? t.pk.map(String) : undefined,
    uniques: Array.isArray(t.uniques)
      ? t.uniques.map((u) => (Array.isArray(u) ? u.map(String) : [])).filter((u: string[]) => u.length > 0)
      : undefined,
  })) as Table[]
  return tables
}
