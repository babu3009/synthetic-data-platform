import { memo, type ChangeEvent } from 'react'
import { Handle, Position, NodeProps } from 'reactflow'
import { Badge, Button, ButtonGroup, Dropdown, Form, InputGroup } from 'react-bootstrap'
import { Column, Table } from '../../state/wizard'

type Data = {
  table: Table
  onTogglePk: (col: string) => void
  onRowTargetChange: (patch: Partial<Table['rowTarget']> | null) => void
  onOpenColumn: (col: Column) => void
  allTables: string[]
}

function KeyIcon() {
  return <span role="img" aria-label="pk">🔑</span>
}

export default memo(function TableNode({ data }: NodeProps<Data>) {
  const t = data.table
  const pk = new Set(t.pk || [])
  const rowTarget = t.rowTarget

  return (
    <div className="card table-card">
      <div className="card-header d-flex justify-content-between align-items-center py-1">
        <strong>{t.name}</strong>
      </div>
      <div className="card-body py-2">
        <div className="mb-2">
          <InputGroup size="sm">
            <InputGroup.Text>Rows</InputGroup.Text>
            <Dropdown as={ButtonGroup}>
              <Button size="sm" variant="outline-secondary" disabled>
                {rowTarget?.type === 'ratioTo' ? 'ratioTo' : 'absolute'}
              </Button>
              <Dropdown.Toggle split size="sm" variant="outline-secondary" id="rt-toggle" />
              <Dropdown.Menu>
                <Dropdown.Item onClick={() => data.onRowTargetChange({ type: 'absolute', value: 1000 })}>absolute</Dropdown.Item>
                <Dropdown.Item onClick={() => data.onRowTargetChange({ type: 'ratioTo', table: data.allTables[0] || t.name, ratio: 0.5 })}>ratioTo</Dropdown.Item>
              </Dropdown.Menu>
            </Dropdown>
            {rowTarget?.type === 'ratioTo' ? (
              <>
                <Form.Select aria-label="Pick reference table" size="sm" value={rowTarget.table} onChange={(e: ChangeEvent<HTMLSelectElement>) => data.onRowTargetChange({ type: 'ratioTo', table: e.target.value, ratio: rowTarget.ratio })}>
                  {data.allTables.map((n: string) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </Form.Select>
                <Form.Control
                  size="sm"
                  type="number"
                  step="0.01"
                  value={rowTarget.ratio}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => data.onRowTargetChange({ type: 'ratioTo', table: rowTarget.table, ratio: Number(e.target.value) })}
                />
              </>
            ) : (
              <Form.Control
                size="sm"
                type="number"
                value={rowTarget && rowTarget.type === 'absolute' ? rowTarget.value : 1000}
                onChange={(e: ChangeEvent<HTMLInputElement>) => data.onRowTargetChange({ type: 'absolute', value: Number(e.target.value) })}
              />
            )}
          </InputGroup>
        </div>
        <ul className="list-unstyled mb-0">
          {t.columns.map((c: Column) => (
            <li key={c.name} className="d-flex align-items-center justify-content-between gap-2 py-1">
              <div className="d-flex align-items-center gap-2" role="button" onClick={() => data.onTogglePk(c.name)}>
                <Handle id={`in-${t.name}-${c.name}`} type="target" position={Position.Left} className="handle-in" />
                <span>{c.name}</span>
                {pk.has(c.name) && (
                  <Badge bg="warning" text="dark">
                    <KeyIcon />
                  </Badge>
                )}
                <small className="text-muted">({c.dtype}{c.nullable ? ', null' : ''})</small>
              </div>
              <div>
                <Button size="sm" variant="outline-secondary" onClick={() => data.onOpenColumn(c)}>
                  Edit
                </Button>
                <Handle id={`out-${t.name}-${c.name}`} type="source" position={Position.Right} className="handle-out" />
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
})
