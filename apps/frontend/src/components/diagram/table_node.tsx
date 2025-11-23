import { memo, useMemo, useState, type ChangeEvent, type KeyboardEvent } from 'react'
import { Handle, Position, NodeProps } from 'reactflow'
import { Badge, Button, ButtonGroup, Dropdown, Form, InputGroup, OverlayTrigger, Tooltip } from 'react-bootstrap'
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
  const pageSize = 50
  const [page, setPage] = useState(0)
  const total = t.columns.length
  const start = page * pageSize
  const end = Math.min(total, start + pageSize)
  const visible = useMemo(() => t.columns.slice(start, end), [t.columns, start, end])

  function onItemKeyDown(e: KeyboardEvent<HTMLLIElement>, colName: string) {
    // space/enter toggles PK; e opens editor
    if (e.key === ' ' || e.key === 'Enter') {
      e.preventDefault()
      data.onTogglePk(colName)
      return
    }
    if (e.key.toLowerCase() === 'e') {
      const c = t.columns.find((c) => c.name === colName)
      if (c) data.onOpenColumn(c)
      return
    }
    // Arrow navigation between items
    const current = e.currentTarget
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      const next = current.nextElementSibling as HTMLLIElement | null
      next?.focus()
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      const prev = current.previousElementSibling as HTMLLIElement | null
      prev?.focus()
    }
  }

  return (
    <div className="card table-card">
      <div className="card-header d-flex justify-content-between align-items-center py-1">
        <strong>{t.name}</strong>
      </div>
      <div className="card-body py-2">
        <div className="mb-2">
          <InputGroup size="sm">
            <InputGroup.Text aria-label="Row target type">
              Rows
              <OverlayTrigger placement="top" overlay={<Tooltip>absolute: fixed rows; ratioTo: proportion of another table</Tooltip>}>
                <span className="ms-1" aria-label="Row target help" role="img">❔</span>
              </OverlayTrigger>
            </InputGroup.Text>
            <Dropdown as={ButtonGroup}>
              <Button size="sm" variant="outline-secondary" disabled aria-label="Current row target mode">
                {rowTarget?.type === 'ratioTo' ? 'ratioTo' : 'absolute'}
              </Button>
              <Dropdown.Toggle split size="sm" variant="outline-secondary" id="rt-toggle" aria-label="Change row target mode" />
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
                  aria-label="Row ratio"
                  size="sm"
                  type="number"
                  step="0.01"
                  min="0"
                  value={rowTarget.ratio}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => {
                    const val = e.target.value === '' ? 0 : Number(e.target.value);
                    data.onRowTargetChange({ type: 'ratioTo', table: rowTarget.table, ratio: val });
                  }}
                  onFocus={(e: React.FocusEvent<HTMLInputElement>) => e.target.select()}
                />
              </>
            ) : (
              <Form.Control
                aria-label="Absolute row count"
                size="sm"
                type="number"
                min="1"
                step="1"
                value={rowTarget && rowTarget.type === 'absolute' ? rowTarget.value : 1000}
                onChange={(e: ChangeEvent<HTMLInputElement>) => {
                  const val = e.target.value === '' ? 1 : Number(e.target.value);
                  data.onRowTargetChange({ type: 'absolute', value: val });
                }}
                onFocus={(e: React.FocusEvent<HTMLInputElement>) => e.target.select()}
              />
            )}
          </InputGroup>
        </div>
        <div className="small text-muted mb-1 d-flex justify-content-between align-items-center px-1">
          <span>Columns</span>
          <span className="text-end">
            <OverlayTrigger placement="top" overlay={<Tooltip>Click column name to toggle PK</Tooltip>}>
              <span role="img" aria-label="Primary Key indicator">🔑 = PK</span>
            </OverlayTrigger>
          </span>
        </div>
        <ul
          className="list-unstyled mb-0"
          role="listbox"
          aria-label={`Columns of table ${t.name}`}
        >
          {visible.map((c: Column) => (
            <li
              key={c.name}
              className="d-flex align-items-center justify-content-between gap-2 py-1"
              tabIndex={0}
              role="option"
              onKeyDown={(e) => onItemKeyDown(e, c.name)}
            >
              <div
                className="d-flex align-items-center gap-2"
                role="button"
                aria-label={`Toggle primary key for ${c.name}`}
                onClick={() => data.onTogglePk(c.name)}
                style={{ cursor: 'pointer' }}
              >
                <Handle id={`in-${t.name}-${c.name}`} type="target" position={Position.Left} className="handle-in" />
                <OverlayTrigger 
                  placement="top" 
                  overlay={<Tooltip>Click to {pk.has(c.name) ? 'remove from' : 'set as'} primary key</Tooltip>}
                >
                  <div className="d-flex align-items-center gap-1">
                    <span>{c.name}</span>
                    {pk.has(c.name) && (
                      <Badge bg="warning" text="dark" aria-label="Primary key">
                        <KeyIcon />
                      </Badge>
                    )}
                  </div>
                </OverlayTrigger>
                <small className="text-muted">({c.dtype}{c.nullable ? ', null' : ''})</small>
              </div>
              <div>
                <Button size="sm" variant="outline-secondary" onClick={() => data.onOpenColumn(c)} aria-label={`Edit column ${c.name}`}>
                  Edit
                </Button>
                <Handle id={`out-${t.name}-${c.name}`} type="source" position={Position.Right} className="handle-out" />
              </div>
            </li>
          ))}
        </ul>
        {total > end && (
          <div className="d-flex justify-content-center mt-2">
            <Button size="sm" variant="outline-secondary" onClick={() => setPage((p) => p + 1)} aria-label="Load more columns">
              Load more…
            </Button>
          </div>
        )}
        {start > 0 && (
          <div className="d-flex justify-content-center mt-2">
            <Button size="sm" variant="outline-secondary" onClick={() => setPage((p) => Math.max(0, p - 1))} aria-label="Show previous columns">
              Show previous…
            </Button>
          </div>
        )}
      </div>
    </div>
  )
})
