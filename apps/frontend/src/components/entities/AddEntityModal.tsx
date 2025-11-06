import { useMemo, useState } from 'react'
import { Modal, Button, Form, Tabs, Tab, Alert, Row, Col, Table, Spinner, InputGroup } from 'react-bootstrap'
import { EntitySchema, Table as EntityTable, isEntityNameUnique, tablesFromCanonicalSchema } from '../../state/wizard'
import { getSourceSchema, uploadDDLSource, uploadJSONSource } from '../../services/sources'

type Props = {
  show: boolean
  onHide: () => void
  projectId: string
  existingNames: string[]
  onCreated: (entity: EntitySchema) => void
}

export default function AddEntityModal({ show, onHide, projectId, existingNames, onCreated }: Props) {
  const [tab, setTab] = useState<'ddl' | 'json' | 'fields'>('ddl')
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)

  // DDL state
  const [ddlText, setDdlText] = useState('')
  const [ddlFile, setDdlFile] = useState<File | null>(null)
  const [dialect, setDialect] = useState('postgres')
  const [ddlParsing, setDdlParsing] = useState(false)
  const [ddlTables, setDdlTables] = useState<EntityTable[] | null>(null)

  // JSON state
  const [jsonText, setJsonText] = useState('')
  const [jsonValidating, setJsonValidating] = useState(false)
  const [jsonTables, setJsonTables] = useState<EntityTable[] | null>(null)

  // Fields designer state
  const [tables, setTables] = useState<EntityTable[]>([{
    name: 'table_1',
    columns: [
      { name: 'id', dtype: 'uuid', nullable: false },
    ],
    pk: ['id'],
  }])

  const nameUnique = useMemo(() => isEntityNameUnique(name, existingNames.map((n) => ({ name: n } as any) as EntitySchema) as any), [name, existingNames])

  function resetState() {
    setError(null)
    setDdlText('')
    setDdlFile(null)
    setDialect('postgres')
    setDdlParsing(false)
    setDdlTables(null)
    setJsonText('')
    setJsonValidating(false)
    setJsonTables(null)
    setTables([{ name: 'table_1', columns: [{ name: 'id', dtype: 'uuid', nullable: false }], pk: ['id'] }])
  }

  function closeAndReset() {
    onHide()
    setTimeout(() => {
      setName('')
      resetState()
      setTab('ddl')
    }, 200)
  }

  async function handleParseDDL() {
    setError(null)
    setDdlParsing(true)
    try {
      let file: File
      if (ddlFile) {
        file = ddlFile
      } else if (ddlText.trim().length > 0) {
        const blob = new Blob([ddlText], { type: 'text/plain' })
        file = new File([blob], 'schema.sql', { type: 'text/plain' })
      } else {
        setError('Provide DDL via file upload or textarea.')
        setDdlParsing(false)
        return
      }
      const created = await uploadDDLSource(projectId, file, dialect)
      const canonical = await getSourceSchema(projectId, created.id)
      const mapped = tablesFromCanonicalSchema(canonical)
      setDdlTables(mapped)
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Failed to parse DDL')
    } finally {
      setDdlParsing(false)
    }
  }

  async function handleValidateJSON() {
    setError(null)
    setJsonValidating(true)
    try {
      if (jsonText.trim().length === 0) {
        setError('Paste a normalized schema JSON first.')
        setJsonValidating(false)
        return
      }
      // Prefer backend validation by uploading as a file
      const blob = new Blob([jsonText], { type: 'application/json' })
      const file = new File([blob], 'schema.json', { type: 'application/json' })
      const created = await uploadJSONSource(projectId, file)
      const canonical = await getSourceSchema(projectId, created.id)
      const mapped = tablesFromCanonicalSchema(canonical)
      setJsonTables(mapped)
    } catch (e: any) {
      // Fallback: try parsing locally to give feedback
      try {
        const parsed = JSON.parse(jsonText)
        const mapped = tablesFromCanonicalSchema(parsed)
        setJsonTables(mapped)
      } catch (_) {
        setError(e?.response?.data?.detail || e?.message || 'Invalid JSON schema')
      }
    } finally {
      setJsonValidating(false)
    }
  }

  function addTable() {
    const idx = tables.length + 1
    setTables([...tables, { name: `table_${idx}`, columns: [], pk: [] }])
  }
  function removeTable(i: number) {
    setTables(tables.filter((_, idx) => idx !== i))
  }
  function updateTableName(i: number, name: string) {
    const next = [...tables]
    next[i] = { ...next[i], name }
    setTables(next)
  }
  function addColumn(i: number) {
    const next = [...tables]
    next[i] = { ...next[i], columns: [...next[i].columns, { name: `col_${next[i].columns.length + 1}`, dtype: 'text', nullable: true }] }
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

  function currentTables(): EntityTable[] | null {
    if (tab === 'ddl') return ddlTables
    if (tab === 'json') return jsonTables
    return tables
  }

  function canCreate(): boolean {
    const t = currentTables()
    return Boolean(name.trim()) && nameUnique && Array.isArray(t) && t.length > 0
  }

  function handleCreate() {
    const t = currentTables()
    if (!t || !canCreate()) return
    const entity: EntitySchema = {
      id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}`,
      name: name.trim(),
      tables: t,
      updatedAt: new Date().toISOString(),
    }
    onCreated(entity)
  }

  return (
    <Modal show={show} onHide={closeAndReset} size="lg" backdrop="static">
      <Modal.Header closeButton>
        <Modal.Title>Add Entity</Modal.Title>
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

        <Tabs activeKey={tab} onSelect={(k) => setTab((k as any) || 'ddl')}>
          <Tab eventKey="ddl" title="DDL">
            <div className="pt-3">
              <Row className="mb-2">
                <Col md={6}>
                  <Form.Group controlId="ddlFile" className="mb-2">
                    <Form.Label>Upload DDL file</Form.Label>
                    <Form.Control type="file" accept=".sql,.txt" onChange={(e) => setDdlFile(e.target.files?.[0] || null)} />
                  </Form.Group>
                </Col>
                <Col md={6}>
                  <Form.Group controlId="dialect" className="mb-2">
                    <Form.Label>SQL Dialect</Form.Label>
                    <Form.Select value={dialect} onChange={(e) => setDialect(e.target.value)}>
                      <option value="postgres">Postgres</option>
                      <option value="mysql">MySQL</option>
                      <option value="sqlite">SQLite</option>
                    </Form.Select>
                  </Form.Group>
                </Col>
              </Row>
              <Form.Group controlId="ddlText" className="mb-2">
                <Form.Label>Or paste DDL</Form.Label>
                <Form.Control as="textarea" rows={6} value={ddlText} onChange={(e) => setDdlText(e.target.value)} placeholder="CREATE TABLE ..." />
              </Form.Group>
              <div className="d-flex align-items-center gap-2">
                <Button variant="secondary" onClick={handleParseDDL} disabled={ddlParsing}>
                  {ddlParsing ? (
                    <>
                      <Spinner animation="border" size="sm" /> Parsing...
                    </>
                  ) : (
                    'Parse'
                  )}
                </Button>
                {ddlTables && <small className="text-success">Parsed {ddlTables.length} tables</small>}
              </div>
            </div>
          </Tab>
          <Tab eventKey="json" title="JSON">
            <div className="pt-3">
              <Form.Group controlId="jsonText" className="mb-2">
                <Form.Label>Paste normalized schema JSON</Form.Label>
                <Form.Control as="textarea" rows={10} value={jsonText} onChange={(e) => setJsonText(e.target.value)} placeholder='{"tables": [{"name": "...", "columns": [...]}]}' />
              </Form.Group>
              <div className="d-flex align-items-center gap-2">
                <Button variant="secondary" onClick={handleValidateJSON} disabled={jsonValidating}>
                  {jsonValidating ? (
                    <>
                      <Spinner animation="border" size="sm" /> Validating...
                    </>
                  ) : (
                    'Validate'
                  )}
                </Button>
                {jsonTables && <small className="text-success">Detected {jsonTables.length} tables</small>}
              </div>
            </div>
          </Tab>
          <Tab eventKey="fields" title="Fields">
            <div className="pt-3">
              <div className="d-flex justify-content-between align-items-center mb-2">
                <strong>Manual designer</strong>
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
            </div>
          </Tab>
        </Tabs>
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={closeAndReset}>
          Cancel
        </Button>
        <Button onClick={handleCreate} disabled={!canCreate()}>
          Create Entity
        </Button>
      </Modal.Footer>
    </Modal>
  )
}
