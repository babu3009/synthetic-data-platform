import React from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import ReactFlow, { Background, Controls, MiniMap, Node, Edge } from 'reactflow'
import 'reactflow/dist/style.css'
import { getSourceDag } from '../../services/sources'
import { autoLayout } from '../../utils/layout'

const SourceDagPage: React.FC = () => {
  const { projectId, sourceId } = useParams<{ projectId: string; sourceId: string }>()
  const { data, isLoading, error } = useQuery({
    queryKey: ['source.dag', projectId, sourceId],
    queryFn: () => getSourceDag(projectId!, sourceId!),
    enabled: !!projectId && !!sourceId,
  })

  if (isLoading) return <div className="container py-4"><div className="skeleton skeleton-line40" /></div>
  if (error) return <div className="container py-4"><div className="alert alert-danger">{(error as Error).message}</div></div>
  if (!data) return null

  const nodes: Node[] = (data.nodes || []).map((n) => ({ id: n, data: { label: n }, position: { x: 0, y: 0 } }))
  const edges: Edge[] = (data.edges || []).map(([from, to]) => ({ id: `${from}->${to}`, source: from, target: to }))
  const { positions } = autoLayout(nodes, edges, 'LR')
  const laidOutNodes = nodes.map((n) => ({ ...n, position: positions[n.id] || n.position }))

  return (
    <div className="container py-4">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h2 className="mb-0">Source DAG</h2>
        <div className="d-flex gap-2">
          <Link className="btn btn-outline-secondary" to={`/projects/${projectId}/sources/${sourceId}/schema`}>View Schema</Link>
          <Link className="btn btn-outline-secondary" to={`/projects/${projectId}/sources`}>Back to Sources</Link>
        </div>
      </div>
  <div className="border rounded rf-container-580">
        <ReactFlow nodes={laidOutNodes} edges={edges} fitView>
          <Background />
          <MiniMap />
          <Controls />
        </ReactFlow>
      </div>
    </div>
  )
}

export default SourceDagPage
