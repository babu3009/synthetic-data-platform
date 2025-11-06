import { useCallback, useMemo, useRef, useState, type ChangeEvent, lazy, Suspense } from 'react'
import ReactFlow, {
  addEdge,
  Background,
  BackgroundVariant,
  Controls,
  Connection,
  Edge,
  MiniMap,
  Node,
  OnConnect,
  useEdgesState,
  useNodesState,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { Button, Col, Form, Row } from 'react-bootstrap'
import TableNode from './table_node'
import { Relationship, useWizard, Column, Table, EntitySchema } from '../../state/wizard'
import EdgePanel from './edge_panel'
const ColumnEditorModal = lazy(() => import('./column_editor_modal'))
import { autoLayout } from '../../utils/layout'
import { autosaveEntity } from '../../services/entities'
import { useAutosave } from '../../hooks/use_autosave'
import './diagram.css'

type DiagramProps = Record<string, never>

const nodeTypes = { table: TableNode }

function dtypeGroup(dtype: string): 'uuid' | 'text' | 'numeric' | 'bool' | 'date' | 'timestamp' {
  const d = dtype.toLowerCase()
  if (d.includes('uuid')) return 'uuid'
  if (['int', 'bigint', 'numeric', 'decimal', 'float', 'double'].some((k) => d.includes(k))) return 'numeric'
  if (d.includes('bool')) return 'bool'
  if (d.includes('timestamp') || d.includes('timestamptz')) return 'timestamp'
  if (d.includes('date')) return 'date'
  return 'text'
}

function compatible(a: string, b: string) {
  const ga = dtypeGroup(a)
  const gb = dtypeGroup(b)
  return ga === gb || (ga === 'numeric' && gb === 'numeric')
}

export default function DiagramCanvas(_: DiagramProps) {
  const { state, dispatch } = useWizard()
  const entity = useMemo(() => state.entities.find((e: EntitySchema) => e.id === state.selectedEntityId) || state.entities[0], [state])
  const entityId = entity?.id

  const [selectedRelId, setSelectedRelId] = useState<string | null>(null)
  const [editingColumn, setEditingColumn] = useState<{ table: string; column: Column } | null>(null)

  const nodesInit: Node[] = useMemo(() => {
    if (!entity) return []
    return entity.tables.map((t: Table) => ({
      id: t.name,
      type: 'table',
      data: {
        table: t,
        allTables: entity.tables.map((x: Table) => x.name),
        onTogglePk: (col: string) => dispatch({ type: 'togglePk', entityId: entity.id, tableName: t.name, columnName: col }),
  onRowTargetChange: (patch: Table['rowTarget']) => dispatch({ type: 'updateTable', entityId: entity.id, tableName: t.name, patch: { rowTarget: patch } }),
        onOpenColumn: (col: Column) => setEditingColumn({ table: t.name, column: col }),
      },
      position: entity.layout?.[t.name] ?? { x: 0, y: 0 },
    }))
  }, [entity, dispatch])

  const edgesInit: Edge[] = useMemo(() => {
    if (!entity) return []
    return (entity.relationships || []).map((r: Relationship) => ({
      id: r.id,
      source: r.sourceTable,
      target: r.targetTable,
      sourceHandle: `out-${r.sourceTable}-${r.sourceColumn}`,
      targetHandle: `in-${r.targetTable}-${r.targetColumn}`,
      label: r.cardinality,
    }))
  }, [entity])

  const [nodes, setNodes, onNodesChange] = useNodesState(nodesInit)
  const [edges, setEdges, onEdgesChange] = useEdgesState(edgesInit)

  // Synchronize when entity changes
  const lastEntityId = useRef<string | undefined>(undefined)
  if (entityId && lastEntityId.current !== entityId) {
    setNodes(nodesInit)
    setEdges(edgesInit)
    lastEntityId.current = entityId
  }

  const onConnect: OnConnect = useCallback(
    (conn: Connection) => {
      if (!entity || !conn.source || !conn.target || !conn.sourceHandle || !conn.targetHandle) return
      const [_, sTable, sCol] = (conn.sourceHandle as string).split('-')
      const [__, tTable, tCol] = (conn.targetHandle as string).split('-')
      const st = entity.tables.find((t: Table) => t.name === sTable)
      const tt = entity.tables.find((t: Table) => t.name === tTable)
      const sc = st?.columns.find((c: Column) => c.name === sCol)
      const tc = tt?.columns.find((c: Column) => c.name === tCol)
      if (!st || !tt || !sc || !tc) return
      if (sTable === tTable) {
        if (!window.confirm('Create self-referencing foreign key?')) return
      }
      if (!compatible(sc.dtype, tc.dtype)) {
        alert('Incompatible column types for FK')
        return
      }
      const newRel: Relationship = {
        id: `rel-${Date.now()}`,
        sourceTable: sTable,
        sourceColumn: sCol,
        targetTable: tTable,
        targetColumn: tCol,
        cardinality: 'ONE_TO_MANY',
      }
      dispatch({ type: 'upsertRelationship', entityId: entity.id, rel: newRel })
      setEdges((eds: Edge[]) => addEdge({ ...conn, id: newRel.id, label: newRel.cardinality }, eds))
    },
    [entity, dispatch, setEdges]
  )

  const onEdgeClick = useCallback((_: React.MouseEvent, edge: Edge) => setSelectedRelId(edge.id), [])

  const selectedRel = useMemo(() => (entity?.relationships || []).find((r: Relationship) => r.id === selectedRelId), [entity, selectedRelId])

  const savePositions = useCallback(
    (ns: Node[]) => {
      if (!entity) return
      const layout: Record<string, { x: number; y: number }> = {}
      ns.forEach((n) => (layout[n.id] = { x: n.position.x, y: n.position.y }))
      dispatch({ type: 'saveLayout', entityId: entity.id, layout })
    },
    [entity, dispatch]
  )

  const onNodesChangeWithSave = useCallback(
    (changes: Parameters<typeof onNodesChange>[0]) => {
      onNodesChange(changes)
      // Defer save a bit
      setTimeout(() => savePositions(nodes as Node[]), 50)
    },
    [onNodesChange, savePositions, nodes]
  )

  const onAutoLayout = useCallback(() => {
    const { positions } = autoLayout(nodes, edges)
    const next = nodes.map((n: Node) => ({ ...n, position: positions[n.id] || n.position }))
    setNodes(next)
    savePositions(next)
  }, [nodes, edges, setNodes, savePositions])

  const onColumnSave = (patch: Column) => {
    if (!entity || !editingColumn) return
    const table = entity.tables.find((t: Table) => t.name === editingColumn.table)
    if (!table) return
    const patchTable: Partial<Table> = {
      columns: table.columns.map((c: Column) => (c.name === patch.name ? { ...c, ...patch } : c)),
    }
    dispatch({ type: 'updateTable', entityId: entity.id, tableName: editingColumn.table, patch: patchTable })
    setEditingColumn(null)
  }

  const onEdgeChange = (rel: Relationship) => {
    if (!entity) return
    dispatch({ type: 'upsertRelationship', entityId: entity.id, rel })
    setEdges((eds: Edge[]) => eds.map((e: Edge) => (e.id === rel.id ? { ...e, label: rel.cardinality } : e)))
  }
  const onEdgeDelete = (id: string) => {
    if (!entity) return
    dispatch({ type: 'deleteRelationship', entityId: entity.id, relId: id })
    setEdges((eds: Edge[]) => eds.filter((e: Edge) => e.id !== id))
    setSelectedRelId(null)
  }

  // Left sidebar controls
  const [selectedId, setSelectedId] = useState(entity?.id)

  const onEntitySelect = (id: string) => {
    setSelectedId(id)
    dispatch({ type: 'setSelectedEntity', id })
  }

  // Debounced autosave when entity changes (800ms)
  useAutosave([entity, state.projectId], async () => {
    if (!entity) return
    await autosaveEntity(state.projectId, entity)
  }, 800, () => dispatch({ type: 'clearDirty' }))

  return (
    <div className="position-relative diagram-container">
      <Row className="g-2 mb-2">
        <Col md="auto">
          <Form.Select aria-label="Select entity" value={selectedId} onChange={(e: ChangeEvent<HTMLSelectElement>) => onEntitySelect(e.target.value)} className="focus-ring">
            {state.entities.map((e: EntitySchema) => (
              <option key={e.id} value={e.id}>
                {e.name}
              </option>
            ))}
          </Form.Select>
        </Col>
        <Col md="auto">
          <Button variant="outline-secondary" onClick={onAutoLayout} aria-label="Auto layout tables" className="focus-ring">
            Auto Layout
          </Button>
        </Col>
      </Row>

      <div className="diagram-flow">
        <ReactFlow
          nodeTypes={nodeTypes}
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChangeWithSave}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onEdgeClick={onEdgeClick}
          fitView
        >
          <MiniMap />
          <Controls />
          <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
        </ReactFlow>
      </div>

      <EdgePanel
        show={!!selectedRel}
        onHide={() => setSelectedRelId(null)}
        relationship={selectedRel || undefined}
        onChange={onEdgeChange}
        onDelete={onEdgeDelete}
      />
      <Suspense fallback={null}>
        <ColumnEditorModal
          show={!!editingColumn}
          column={editingColumn?.column}
          onSave={onColumnSave}
          onHide={() => setEditingColumn(null)}
        />
      </Suspense>
    </div>
  )
}
