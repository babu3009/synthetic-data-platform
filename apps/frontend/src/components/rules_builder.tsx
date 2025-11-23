import { useState } from 'react'
import { Modal, Button, Form, Alert, Badge, ListGroup, InputGroup } from 'react-bootstrap'
import type { Rule } from '../services/validation'
import type { EntitySchema } from '../state/wizard'

interface RulesBuilderProps {
  show: boolean
  onHide: () => void
  entity: EntitySchema
  existingRules?: Rule[]
  onSave: (rule: Rule) => void
}

type RuleType = 'implication' | 'uniqueness' | 'distribution' | 'temporal'
type TemporalOp = '<=' | '<' | '>=' | '>' | '==' | '!='

interface CategoryProb {
  value: string
  probability: number
}

export default function RulesBuilder({
  show,
  onHide,
  entity,
  existingRules = [],
  onSave,
}: RulesBuilderProps) {
  const [ruleType, setRuleType] = useState<RuleType>('uniqueness')
  const [error, setError] = useState<string | null>(null)
  
  // Common fields
  const [selectedTable, setSelectedTable] = useState<string>(entity.tables[0]?.name || '')
  
  // Implication fields
  const [whenCondition, setWhenCondition] = useState<string>('')
  const [thenConditions, setThenConditions] = useState<string[]>([''])
  
  // Uniqueness fields
  const [uniqueColumns, setUniqueColumns] = useState<string[]>([])
  
  // Distribution fields
  const [distributionColumn, setDistributionColumn] = useState<string>('')
  const [categoryProbs, setCategoryProbs] = useState<CategoryProb[]>([
    { value: '', probability: 1.0 }
  ])
  
  // Temporal fields
  const [leftColumn, setLeftColumn] = useState<string>('')
  const [temporalOp, setTemporalOp] = useState<TemporalOp>('<=')
  const [rightColumn, setRightColumn] = useState<string>('')
  const [offsetDays, setOffsetDays] = useState<number>(0)

  const tables = entity.tables || []
  const currentTable = tables.find(t => t.name === selectedTable)
  const columns = currentTable?.columns || []

  function resetForm() {
    setError(null)
    setSelectedTable(entity.tables[0]?.name || '')
    setWhenCondition('')
    setThenConditions([''])
    setUniqueColumns([])
    setDistributionColumn('')
    setCategoryProbs([{ value: '', probability: 1.0 }])
    setLeftColumn('')
    setTemporalOp('<=')
    setRightColumn('')
    setOffsetDays(0)
  }

  function handleRuleTypeChange(type: RuleType) {
    setRuleType(type)
    resetForm()
  }

  function addThenCondition() {
    setThenConditions([...thenConditions, ''])
  }

  function removeThenCondition(index: number) {
    setThenConditions(thenConditions.filter((_, i) => i !== index))
  }

  function updateThenCondition(index: number, value: string) {
    setThenConditions(thenConditions.map((c, i) => i === index ? value : c))
  }

  function toggleUniqueColumn(colName: string) {
    if (uniqueColumns.includes(colName)) {
      setUniqueColumns(uniqueColumns.filter(c => c !== colName))
    } else {
      setUniqueColumns([...uniqueColumns, colName])
    }
  }

  function addCategoryProb() {
    setCategoryProbs([...categoryProbs, { value: '', probability: 0.0 }])
  }

  function removeCategoryProb(index: number) {
    setCategoryProbs(categoryProbs.filter((_, i) => i !== index))
  }

  function updateCategoryProb(index: number, field: 'value' | 'probability', value: string | number) {
    setCategoryProbs(categoryProbs.map((cat, i) =>
      i === index ? { ...cat, [field]: value } : cat
    ))
  }

  function normalizeProbs() {
    const total = categoryProbs.reduce((sum, c) => sum + c.probability, 0)
    if (total === 0) return
    
    setCategoryProbs(categoryProbs.map(cat => ({
      ...cat,
      probability: cat.probability / total
    })))
  }

  function handleSave() {
    setError(null)
    
    try {
      let rule: Rule
      
      switch (ruleType) {
        case 'implication': {
          if (!whenCondition.trim()) {
            setError('When condition is required')
            return
          }
          const validThens = thenConditions.filter(t => t.trim())
          if (validThens.length === 0) {
            setError('At least one then condition is required')
            return
          }
          rule = {
            type: 'implication',
            table: selectedTable,
            when: whenCondition,
            then: validThens
          }
          break
        }
        
        case 'uniqueness': {
          if (uniqueColumns.length === 0) {
            setError('Select at least one column for uniqueness check')
            return
          }
          rule = {
            type: 'uniqueness',
            table: selectedTable,
            columns: uniqueColumns
          }
          break
        }
        
        case 'distribution': {
          if (!distributionColumn) {
            setError('Select a column for distribution check')
            return
          }
          const validCats = categoryProbs.filter(c => c.value.trim())
          if (validCats.length === 0) {
            setError('At least one category is required')
            return
          }
          const total = validCats.reduce((sum, c) => sum + c.probability, 0)
          if (Math.abs(total - 1.0) > 0.001) {
            setError(`Probabilities must sum to 1.0 (current: ${total.toFixed(3)})`)
            return
          }
          const probs: Record<string, number> = {}
          validCats.forEach(cat => {
            probs[cat.value] = cat.probability
          })
          rule = {
            type: 'distribution',
            table: selectedTable,
            column: distributionColumn,
            probs
          }
          break
        }
        
        case 'temporal': {
          if (!leftColumn) {
            setError('Select a left column')
            return
          }
          if (!rightColumn) {
            setError('Select a right column')
            return
          }
          rule = {
            type: 'temporal',
            table: selectedTable,
            left: `${selectedTable}.${leftColumn}`,
            op: temporalOp,
            right: {
              column: rightColumn,
              offset_days: offsetDays
            }
          }
          break
        }
        
        default:
          setError('Invalid rule type')
          return
      }
      
      onSave(rule)
      resetForm()
      onHide()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create rule')
    }
  }

  function renderRuleTypeFields() {
    switch (ruleType) {
      case 'implication':
        return (
          <>
            <Alert variant="info" className="small">
              <strong>Implication Rules:</strong> Define conditional logic - "If condition X is true, then condition Y must also be true"
              <div className="mt-2">
                <strong>Example:</strong> If <code>total &gt; 1000</code> then <code>payment_method == 'WIRE'</code>
              </div>
            </Alert>
            
            <Form.Group className="mb-3">
              <Form.Label>When Condition <Badge bg="info">Required</Badge></Form.Label>
              <Form.Control
                as="textarea"
                rows={2}
                value={whenCondition}
                onChange={e => setWhenCondition(e.target.value)}
                placeholder="total > 1000"
              />
              <Form.Text className="text-muted">
                Expression that triggers the rule (e.g., <code>column_name &gt; value</code>)
              </Form.Text>
            </Form.Group>
            
            <Form.Label>Then Conditions <Badge bg="info">Required</Badge></Form.Label>
            <ListGroup className="mb-3">
              {thenConditions.map((cond, idx) => (
                <ListGroup.Item key={idx} className="d-flex gap-2 align-items-center">
                  <Form.Control
                    type="text"
                    value={cond}
                    onChange={e => updateThenCondition(idx, e.target.value)}
                    placeholder="payment_method == 'WIRE'"
                    className="flex-grow-1"
                  />
                  <Button
                    variant="outline-danger"
                    size="sm"
                    onClick={() => removeThenCondition(idx)}
                    disabled={thenConditions.length === 1}
                  >
                    Remove
                  </Button>
                </ListGroup.Item>
              ))}
            </ListGroup>
            
            <Button variant="outline-primary" size="sm" onClick={addThenCondition}>
              Add Then Condition
            </Button>
            
            <Alert variant="secondary" className="small mt-3">
              <strong>Supported operators:</strong> ==, !=, &gt;, &lt;, &gt;=, &lt;=, and, or
            </Alert>
          </>
        )
      
      case 'uniqueness':
        return (
          <>
            <Alert variant="info" className="small">
              <strong>Uniqueness Rules:</strong> Ensure specified columns contain only unique values (no duplicates)
              <div className="mt-2">
                <strong>Example:</strong> Customer email addresses must be unique
              </div>
            </Alert>
            
            <Form.Label>Select Columns to Check <Badge bg="info">Required</Badge></Form.Label>
            <ListGroup className="mb-3">
              {columns.length === 0 ? (
                <ListGroup.Item className="text-muted">No columns available</ListGroup.Item>
              ) : (
                columns.map(col => (
                  <ListGroup.Item
                    key={col.name}
                    action
                    active={uniqueColumns.includes(col.name)}
                    onClick={() => toggleUniqueColumn(col.name)}
                    className="d-flex justify-content-between align-items-center"
                  >
                    <div>
                      <strong>{col.name}</strong>
                      <span className="ms-2 text-muted">({col.dtype})</span>
                    </div>
                    {uniqueColumns.includes(col.name) && (
                      <Badge bg="success">Selected</Badge>
                    )}
                  </ListGroup.Item>
                ))
              )}
            </ListGroup>
            
            {uniqueColumns.length > 0 && (
              <Alert variant="secondary" className="small">
                <strong>Selected columns:</strong> {uniqueColumns.join(', ')}
              </Alert>
            )}
          </>
        )
      
      case 'distribution':
        return (
          <>
            <Alert variant="info" className="small">
              <strong>Distribution Rules:</strong> Validate that categorical values follow expected probability distributions
              <div className="mt-2">
                <strong>Example:</strong> Product categories should be 30% Electronics, 25% Clothing, 45% Food
              </div>
            </Alert>
            
            <Form.Group className="mb-3">
              <Form.Label>Column to Check <Badge bg="info">Required</Badge></Form.Label>
              <Form.Select
                value={distributionColumn}
                onChange={e => setDistributionColumn(e.target.value)}
                aria-label="Select column for distribution check"
              >
                <option value="">-- Select column --</option>
                {columns.map(col => (
                  <option key={col.name} value={col.name}>
                    {col.name} ({col.dtype})
                  </option>
                ))}
              </Form.Select>
            </Form.Group>
            
            <Form.Label>Expected Distribution <Badge bg="info">Required</Badge></Form.Label>
            <ListGroup className="mb-3">
              {categoryProbs.map((cat, idx) => (
                <ListGroup.Item key={idx} className="d-flex gap-2 align-items-center">
                  <Form.Control
                    type="text"
                    value={cat.value}
                    onChange={e => updateCategoryProb(idx, 'value', e.target.value)}
                    placeholder="Category value"
                    className="flex-grow-1"
                  />
                  <InputGroup style={{ width: '150px' }}>
                    <Form.Control
                      type="number"
                      step="0.01"
                      min="0"
                      max="1"
                      value={cat.probability}
                      onChange={e => updateCategoryProb(idx, 'probability', Number(e.target.value))}
                      placeholder="0.25"
                    />
                    <InputGroup.Text>prob</InputGroup.Text>
                  </InputGroup>
                  <Button
                    variant="outline-danger"
                    size="sm"
                    onClick={() => removeCategoryProb(idx)}
                    disabled={categoryProbs.length === 1}
                  >
                    Remove
                  </Button>
                </ListGroup.Item>
              ))}
            </ListGroup>
            
            <div className="d-flex gap-2 mb-3">
              <Button variant="outline-primary" size="sm" onClick={addCategoryProb}>
                Add Category
              </Button>
              <Button variant="outline-secondary" size="sm" onClick={normalizeProbs}>
                Normalize Probabilities
              </Button>
            </div>
            
            <Alert variant="secondary" className="small">
              <div>Total probability: <strong>{categoryProbs.reduce((s, c) => s + c.probability, 0).toFixed(3)}</strong></div>
              <div className="text-muted mt-1">Must sum to 1.0. Uses Chi-squared test for validation.</div>
            </Alert>
          </>
        )
      
      case 'temporal':
        return (
          <>
            <Alert variant="info" className="small">
              <strong>Temporal Rules:</strong> Enforce date/time relationships and constraints
              <div className="mt-2">
                <strong>Example:</strong> Shipment date must be within 2 days after order date
              </div>
            </Alert>
            
            <Form.Group className="mb-3">
              <Form.Label>Left Column (Date/Timestamp) <Badge bg="info">Required</Badge></Form.Label>
              <Form.Select
                value={leftColumn}
                onChange={e => setLeftColumn(e.target.value)}
                aria-label="Select left column for temporal rule"
              >
                <option value="">-- Select column --</option>
                {columns
                  .filter(c => c.dtype === 'date' || c.dtype === 'timestamp')
                  .map(col => (
                    <option key={col.name} value={col.name}>
                      {col.name} ({col.dtype})
                    </option>
                  ))}
              </Form.Select>
              <Form.Text className="text-muted">
                Only date/timestamp columns shown
              </Form.Text>
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Operator</Form.Label>
              <div className="d-flex gap-2">
                {['<=', '<', '>=', '>', '==', '!='].map(op => (
                  <Button
                    key={op}
                    variant={temporalOp === op ? 'primary' : 'outline-primary'}
                    size="sm"
                    onClick={() => setTemporalOp(op as TemporalOp)}
                  >
                    {op}
                  </Button>
                ))}
              </div>
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Right Column (Date/Timestamp) <Badge bg="info">Required</Badge></Form.Label>
              <Form.Select
                value={rightColumn}
                onChange={e => setRightColumn(e.target.value)}
                aria-label="Select right column for temporal rule"
              >
                <option value="">-- Select column --</option>
                {columns
                  .filter(c => c.dtype === 'date' || c.dtype === 'timestamp')
                  .map(col => (
                    <option key={col.name} value={col.name}>
                      {col.name} ({col.dtype})
                    </option>
                  ))}
              </Form.Select>
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Offset Days</Form.Label>
              <Form.Control
                type="number"
                value={offsetDays}
                onChange={e => setOffsetDays(Number(e.target.value))}
                placeholder="0"
              />
              <Form.Text className="text-muted">
                Number of days to add/subtract from right column (can be negative)
              </Form.Text>
            </Form.Group>
            
            {leftColumn && rightColumn && (
              <Alert variant="secondary" className="small">
                <strong>Generated rule:</strong><br />
                <code>{selectedTable}.{leftColumn} {temporalOp} {selectedTable}.{rightColumn}{offsetDays !== 0 ? ` + ${offsetDays}d` : ''}</code>
              </Alert>
            )}
          </>
        )
    }
  }

  const totalProb = categoryProbs.reduce((s, c) => s + c.probability, 0)
  const isProbValid = Math.abs(totalProb - 1.0) <= 0.001

  return (
    <Modal show={show} onHide={onHide} size="lg" animation={false}>
      <Modal.Header closeButton>
        <Modal.Title>
          Create Validation Rule
          <div className="text-muted small mt-1">
            Entity: <code>{entity.name}</code>
          </div>
        </Modal.Title>
      </Modal.Header>
      
      <Modal.Body>
        {error && (
          <Alert variant="danger" onClose={() => setError(null)} dismissible>
            {error}
          </Alert>
        )}
        
        {existingRules.length > 0 && (
          <Alert variant="info" className="mb-3">
            <div className="d-flex justify-content-between align-items-center mb-2">
              <strong>📋 Existing Rules ({existingRules.length})</strong>
            </div>
            <ListGroup variant="flush" className="small">
              {existingRules.slice(0, 5).map((rule, idx) => (
                <ListGroup.Item key={idx} className="px-0 py-1">
                  <Badge bg="secondary" className="me-2">{rule.type}</Badge>
                  {rule.type === 'uniqueness' && (
                    <span>{rule.table}: {rule.columns.join(', ')}</span>
                  )}
                  {rule.type === 'distribution' && (
                    <span>{rule.table}.{rule.column}</span>
                  )}
                  {rule.type === 'implication' && (
                    <span>{rule.when} → {rule.then.join(', ')}</span>
                  )}
                  {rule.type === 'temporal' && (
                    <span>{rule.left} {rule.op} {rule.right.column}</span>
                  )}
                </ListGroup.Item>
              ))}
              {existingRules.length > 5 && (
                <ListGroup.Item className="px-0 py-1 text-muted">
                  ... and {existingRules.length - 5} more
                </ListGroup.Item>
              )}
            </ListGroup>
          </Alert>
        )}
        
        <Form.Group className="mb-3">
          <Form.Label>Rule Type</Form.Label>
          <div className="d-flex gap-2 flex-wrap">
            {[
              { type: 'uniqueness' as const, label: 'Uniqueness', icon: '🔑' },
              { type: 'implication' as const, label: 'Implication', icon: '➡️' },
              { type: 'distribution' as const, label: 'Distribution', icon: '📊' },
              { type: 'temporal' as const, label: 'Temporal', icon: '📅' },
            ].map(({ type, label, icon }) => (
              <Button
                key={type}
                variant={ruleType === type ? 'primary' : 'outline-primary'}
                onClick={() => handleRuleTypeChange(type)}
              >
                {icon} {label}
              </Button>
            ))}
          </div>
        </Form.Group>
        
        <Form.Group className="mb-3">
          <Form.Label>Table</Form.Label>
          <Form.Select
            value={selectedTable}
            onChange={e => setSelectedTable(e.target.value)}
            aria-label="Select table for rule"
          >
            {tables.map(t => (
              <option key={t.name} value={t.name}>
                {t.name} ({t.columns.length} columns)
              </option>
            ))}
          </Form.Select>
        </Form.Group>
        
        <hr />
        
        {renderRuleTypeFields()}
      </Modal.Body>
      
      <Modal.Footer>
        <div className="d-flex justify-content-between w-100">
          <div className="text-muted small align-self-center">
            {ruleType === 'distribution' && !isProbValid && (
              <span className="text-danger">⚠ Probabilities must sum to 1.0</span>
            )}
          </div>
          <div className="d-flex gap-2">
            <Button variant="secondary" onClick={onHide}>
              Cancel
            </Button>
            <Button variant="primary" onClick={handleSave}>
              Add Rule
            </Button>
          </div>
        </div>
      </Modal.Footer>
    </Modal>
  )
}
