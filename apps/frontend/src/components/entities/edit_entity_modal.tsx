import { useMemo, useState } from 'react'
import { Modal, Button, Form, Alert, InputGroup, Table } from 'react-bootstrap'
import { EntitySchema, Table as EntityTable } from '../../state/wizard'

type Props = {
  show: boolean
  onHide: () => void
  entity: EntitySchema
  existingNames: string[]
  onUpdated: (entity: EntitySchema) => void
}

export default function EditEntityModal({ show, onHide, entity, existingNames, onUpdated }: Props) {
  const [name, setName] = useState(entity.name)
  const [tables, setTables] = useState<EntityTable[]>(entity.tables || [])
  const [error, setError] = useState<string | null>(null)

  const nameUnique = useMemo(() => {
    if (name.trim() === entity.name) return true
    const lower = name.trim().toLowerCase()
    return !existingNames.some(n => n.toLowerCase() === lower)
  }, [name, entity.name, existingNames])

  function closeAndReset() {
    onHide()
    setTimeout(() => {
      setName(entity.name)
      setTables(entity.tables || [])
      setError(null)
    }, 200)
  }

  function addTable() {
    const idx = tables.length + 1
    setTables([...tables, { name: `table_${idx}`, columns: [], pk: [] }])
  }

  function removeTable(i: number) {
    setTables(tables.filter((_, idx) => idx !== i))
  }

  function updateTableName(i: number, tableName: string) {
    const next = [...tables]
    next[i] = { ...next[i], name: tableName }
    setTables(next)
  }

  function addColumn(i: number) {
    const next = [...tables]
    next[i] = { 
      ...next[i], 
      columns: [...next[i].columns, { name: `col_${next[i].columns.length + 1}`, dtype: 'text', nullable: true }] 
    }
    setTables(next)
  }

  function removeColumn(i: number, j: number) {
    const next = [...tables]
    next[i] = { ...next[i], columns: next[i].columns.filter((_, idx) => idx !== j) }
    setTables(next)
  }

  function updateColumn(i: number, j: number, patch: Partial<EntityTable['columns'][number]>) {
    const next = [...tables]
    const cols = [...next[i].columns]
    cols[j] = { ...cols[j], ...patch }
    next[i] = { ...next[i], columns: cols }
    setTables(next)
  }

  function togglePk(i: number, colName: string) {
    const next = [...tables]
    const pk = new Set(next[i].pk || [])
    if (pk.has(colName)) pk.delete(colName)
    else pk.add(colName)
    next[i] = { ...next[i], pk: Array.from(pk) }
    setTables(next)
  }

  function canUpdate(): boolean {
    return Boolean(name.trim()) && nameUnique && tables.length > 0
  }

  function handleUpdate() {
    if (!canUpdate()) return
    const updated: EntitySchema = {
      ...entity,
      name: name.trim(),
      tables,
      updatedAt: new Date().toISOString(),
    }
    onUpdated(updated)
  }

  return (
    <Modal show={show} onHide={closeAndReset} size="lg" backdrop="static" animation={false}>
      <Modal.Header closeButton>
        <Modal.Title>Edit Entity</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        {error && (
          <Alert variant="danger" onClose={() => setError(null)} dismissible>
            {error}
          </Alert>
        )}
        <Form.Group className="mb-3" controlId="entityName">
          <Form.Label>Entity name</Form.Label>
          <Form.Control
            type="text"
            placeholder="e.g. Healthcare North DB"
            value={name}
            onChange={(e) => setName(e.target.value)}
            isInvalid={!!name && !nameUnique}
          />
          <Form.Control.Feedback type="invalid">Name must be unique in this project.</Form.Control.Feedback>
        </Form.Group>

        <div className="d-flex justify-content-between align-items-center mb-2">
          <strong>Tables</strong>
          <Button size="sm" onClick={addTable}>Add table</Button>
        </div>

        {tables.map((t, i) => (
          <div key={i} className="mb-3 p-2 border rounded">
            <div className="d-flex align-items-center gap-2 mb-2">
              <InputGroup>
                <InputGroup.Text>Table</InputGroup.Text>
                <Form.Control value={t.name} onChange={(e) => updateTableName(i, e.target.value)} />
              </InputGroup>
              <Button variant="outline-danger" size="sm" onClick={() => removeTable(i)}>
                Remove
              </Button>
              <Button variant="outline-secondary" size="sm" onClick={() => addColumn(i)}>
                Add column
              </Button>
            </div>
            <Table size="sm" bordered>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Nullable</th>
                  <th>PK</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {t.columns.map((c, j) => (
                  <tr key={j}>
                    <td>
                      <Form.Control value={c.name} onChange={(e) => updateColumn(i, j, { name: e.target.value })} />
                    </td>
                    <td>
                      <Form.Select value={c.dtype} onChange={(e) => updateColumn(i, j, { dtype: e.target.value })}>
                        <option value="uuid">uuid</option>
                        <option value="text">text</option>
                        <option value="varchar">varchar</option>
                        <option value="int">int</option>
                        <option value="bigint">bigint</option>
                        <option value="numeric">numeric</option>
                        <option value="timestamp">timestamp</option>
                        <option value="date">date</option>
                        <option value="bool">bool</option>
                      </Form.Select>
                    </td>
                    <td>
                      <Form.Check type="switch" checked={c.nullable} onChange={(e) => updateColumn(i, j, { nullable: e.target.checked })} />
                    </td>
                    <td>
                      <Form.Check type="checkbox" checked={(t.pk || []).includes(c.name)} onChange={() => togglePk(i, c.name)} />
                    </td>
                    <td>
                      <Button variant="outline-danger" size="sm" onClick={() => removeColumn(i, j)}>
                        Remove
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </div>
        ))}
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={closeAndReset}>
          Cancel
        </Button>
        <Button onClick={handleUpdate} disabled={!canUpdate()}>
          Update Entity
        </Button>
      </Modal.Footer>
    </Modal>
  )
}
