import React, { createContext, useContext, useMemo, useReducer } from 'react'

export type Column = {
  name: string
  dtype: string
  nullable: boolean
}

export type Table = {
  name: string
  columns: Column[]
  pk?: string[]
  uniques?: string[][]
}

export type EntitySchema = {
  id: string
  name: string
  tables: Table[]
  updatedAt: string // ISO string
}

export type WizardState = {
  projectId?: string
  entities: EntitySchema[]
  selectedEntityId?: string
  activeTab?: 'entities' | 'diagram'
}

type Action =
  | { type: 'setProject'; projectId?: string }
  | { type: 'addEntity'; entity: Omit<EntitySchema, 'id' | 'updatedAt'> & Partial<Pick<EntitySchema, 'id' | 'updatedAt'>> }
  | { type: 'setSelectedEntity'; id?: string }
  | { type: 'setActiveTab'; tab: WizardState['activeTab'] }

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
export function tablesFromCanonicalSchema(schema: { tables: any[] }): Table[] {
  const tables = (schema?.tables ?? []).map((t: any) => ({
    name: String(t.name),
    columns: (t.columns ?? []).map((c: any) => ({ name: String(c.name), dtype: String(c.dtype), nullable: Boolean(c.nullable) })),
    pk: Array.isArray(t.pk) ? t.pk.map(String) : undefined,
    uniques: Array.isArray(t.uniques) ? t.uniques.map((u: any) => (Array.isArray(u) ? u.map(String) : [])).filter((u: string[]) => u.length > 0) : undefined,
  })) as Table[]
  return tables
}
