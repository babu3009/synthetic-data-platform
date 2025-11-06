import dagre from 'dagre'
import { Edge, Node, XYPosition } from 'reactflow'

export function autoLayout(nodes: Node[], edges: Edge[], direction: 'LR' | 'TB' = 'LR'): { positions: Record<string, XYPosition> } {
  const g = new dagre.graphlib.Graph()
  g.setGraph({ rankdir: direction })
  g.setDefaultEdgeLabel(() => ({}))

  nodes.forEach((n) => {
    const width = (n.width as number | undefined) ?? 260
    const height = (n.height as number | undefined) ?? 120
    g.setNode(n.id, { width, height })
  })
  edges.forEach((e) => g.setEdge(e.source, e.target))

  dagre.layout(g)
  const positions: Record<string, XYPosition> = {}
  nodes.forEach((n) => {
    const pos = g.node(n.id)
    if (pos) positions[n.id] = { x: pos.x - (pos.width ?? 260) / 2, y: pos.y - (pos.height ?? 120) / 2 }
  })
  return { positions }
}
