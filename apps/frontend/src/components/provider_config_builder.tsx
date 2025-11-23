import { useState, useEffect } from 'react'
import { Modal, Button, Form, Row, Col, Alert, Badge, ListGroup } from 'react-bootstrap'
import { Column } from '../state/wizard'

type ProviderType = NonNullable<Column['provider']>

interface ProviderConfigBuilderProps {
  show: boolean
  onHide: () => void
  provider: ProviderType
  currentConfig?: Record<string, unknown>
  onSave: (config: Record<string, unknown>) => void
  columnName: string
  columnType: string
}

interface CategoryEntry {
  value: string
  weight: number
}

export default function ProviderConfigBuilder({
  show,
  onHide,
  provider,
  currentConfig,
  onSave,
  columnName,
  columnType,
}: ProviderConfigBuilderProps) {
  // State for each provider type
  const [config, setConfig] = useState<Record<string, unknown>>({})
  const [error, setError] = useState<string | null>(null)
  
  // Specific state for complex configs
  const [categories, setCategories] = useState<CategoryEntry[]>([{ value: '', weight: 1.0 }])
  const [fakerMethods] = useState<string[]>([
    'name', 'email', 'phone_number', 'address', 'city', 'country', 'ssn',
    'credit_card_number', 'date_of_birth', 'company', 'job', 'ipv4',
    'user_name', 'url', 'text', 'word', 'sentence', 'paragraph',
  ])
  
  // Age calculation helpers
  const calculateDateFromAge = (years: number): string => {
    const today = new Date()
    const pastDate = new Date(today.getFullYear() - years, today.getMonth(), today.getDate())
    return pastDate.toISOString().split('T')[0]
  }

  // Initialize config from currentConfig
  useEffect(() => {
    if (currentConfig) {
      setConfig({ ...currentConfig })
      
      // Special handling for categorical
      if (provider === 'categorical' && currentConfig.categories) {
        const cats = currentConfig.categories as Array<{ value: unknown; weight?: number }>
        setCategories(
          cats.map(c => ({
            value: String(c.value ?? ''),
            weight: typeof c.weight === 'number' ? c.weight : 1.0,
          }))
        )
      }
    } else {
      // Initialize with defaults
      const defaults = getDefaultConfig(provider, columnType)
      setConfig(defaults)
      
      if (provider === 'categorical') {
        setCategories([{ value: '', weight: 1.0 }])
      }
    }
  }, [provider, currentConfig, columnType])

  function getDefaultConfig(provider: ProviderType, _dtype: string): Record<string, unknown> {
    switch (provider) {
      case 'faker':
        return { 
          method: 'name', 
          locale: 'en_US', 
          unique: false,
          min_age: 18,
          max_age: 65,
        }
      case 'pattern':
        return { mask: 'AAA-####', unique: false }
      case 'sequence':
        return { start: 1, step: 1, template: '', unique: false }
      case 'categorical':
        return { categories: [], unique: false }
      case 'expression':
        return { expression: 'i', unique: false }
      case 'geo':
        return { min_lat: -90, max_lat: 90, min_lon: -180, max_lon: 180, as_dict: false, unique: false }
      case 'checksum-valid':
        return { length: 16, prefix: '', unique: false }
      case 'reference':
        return { key: '', unique: false }
      case 'empirical':
        return { csv_path: '', column: '', unique: false }
      default:
        return { unique: false }
    }
  }

  function handleSave() {
    setError(null)
    
    try {
      // Validate and build final config
      const finalConfig = { ...config }
      
      if (provider === 'pattern') {
        if (!finalConfig.mask || String(finalConfig.mask).trim() === '') {
          setError('Pattern mask is required')
          return
        }
      }
      
      if (provider === 'categorical') {
        if (categories.length === 0 || categories.every(c => !c.value)) {
          setError('At least one category is required')
          return
        }
        
        const validCats = categories.filter(c => c.value.trim() !== '')
        const total = validCats.reduce((sum, c) => sum + c.weight, 0)
        
        if (Math.abs(total - 1.0) > 0.001) {
          setError(`Weights must sum to 1.0 (current: ${total.toFixed(3)})`)
          return
        }
        
        finalConfig.categories = validCats.map(c => ({
          value: c.value,
          weight: c.weight,
        }))
      }
      
      if (provider === 'sequence') {
        finalConfig.start = Number(finalConfig.start ?? 1)
        finalConfig.step = Number(finalConfig.step ?? 1)
      }
      
      if (provider === 'geo') {
        finalConfig.min_lat = Number(finalConfig.min_lat ?? -90)
        finalConfig.max_lat = Number(finalConfig.max_lat ?? 90)
        finalConfig.min_lon = Number(finalConfig.min_lon ?? -180)
        finalConfig.max_lon = Number(finalConfig.max_lon ?? 180)
      }
      
      if (provider === 'reference') {
        if (!finalConfig.key || String(finalConfig.key).trim() === '') {
          setError('Reference key is required')
          return
        }
      }
      
      onSave(finalConfig)
      onHide()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Invalid configuration')
    }
  }

  function updateConfig(key: string, value: unknown) {
    setConfig(prev => ({ ...prev, [key]: value }))
  }

  function addCategory() {
    setCategories(prev => [...prev, { value: '', weight: 1.0 }])
  }

  function removeCategory(index: number) {
    setCategories(prev => prev.filter((_, i) => i !== index))
  }

  function updateCategory(index: number, field: 'value' | 'weight', value: string | number) {
    setCategories(prev =>
      prev.map((cat, i) =>
        i === index ? { ...cat, [field]: value } : cat
      )
    )
  }

  function normalizeWeights() {
    const total = categories.reduce((sum, c) => sum + c.weight, 0)
    if (total === 0) return
    
    setCategories(prev =>
      prev.map(cat => ({
        ...cat,
        weight: cat.weight / total,
      }))
    )
  }

  function renderProviderFields() {
    switch (provider) {
      case 'faker':
        return (
          <>
            <Form.Group className="mb-3">
              <Form.Label>Faker Method <Badge bg="info">Required</Badge></Form.Label>
              <Form.Select
                value={String(config.method ?? 'name')}
                onChange={e => updateConfig('method', e.target.value)}
                aria-label="Select faker method"
              >
                {fakerMethods.map(m => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </Form.Select>
              <Form.Text className="text-muted">
                Type of fake data to generate (e.g., name, email, phone_number)
              </Form.Text>
            </Form.Group>
            
            {config.method === 'date_of_birth' && (
              <>
                <Alert variant="info" className="small mb-3">
                  <strong>Age-based Date Configuration</strong>
                  <p className="mb-0 mt-1">Specify age range to generate realistic birth dates</p>
                  <div className="mt-2">
                    <strong>Common presets:</strong>
                    <div className="d-flex gap-2 mt-1 flex-wrap">
                      <Button 
                        size="sm" 
                        variant="outline-secondary"
                        onClick={() => {
                          updateConfig('min_age', 18)
                          updateConfig('max_age', 25)
                          updateConfig('min_date', calculateDateFromAge(25))
                          updateConfig('max_date', calculateDateFromAge(18))
                        }}
                      >
                        Young Adults (18-25)
                      </Button>
                      <Button 
                        size="sm" 
                        variant="outline-secondary"
                        onClick={() => {
                          updateConfig('min_age', 25)
                          updateConfig('max_age', 65)
                          updateConfig('min_date', calculateDateFromAge(65))
                          updateConfig('max_date', calculateDateFromAge(25))
                        }}
                      >
                        Working Age (25-65)
                      </Button>
                      <Button 
                        size="sm" 
                        variant="outline-secondary"
                        onClick={() => {
                          updateConfig('min_age', 65)
                          updateConfig('max_age', 90)
                          updateConfig('min_date', calculateDateFromAge(90))
                          updateConfig('max_date', calculateDateFromAge(65))
                        }}
                      >
                        Seniors (65-90)
                      </Button>
                      <Button 
                        size="sm" 
                        variant="outline-secondary"
                        onClick={() => {
                          updateConfig('min_age', 0)
                          updateConfig('max_age', 18)
                          updateConfig('min_date', calculateDateFromAge(18))
                          updateConfig('max_date', calculateDateFromAge(0))
                        }}
                      >
                        Minors (0-18)
                      </Button>
                    </div>
                  </div>
                </Alert>
                
                <Row>
                  <Col md={6}>
                    <Form.Group className="mb-3">
                      <Form.Label>Minimum Age (years)</Form.Label>
                      <Form.Control
                        type="number"
                        min="0"
                        max="150"
                        value={Number(config.min_age ?? 18)}
                        onChange={e => {
                          const minAge = Number(e.target.value)
                          updateConfig('min_age', minAge)
                          // Auto-calculate date range
                          const maxDate = calculateDateFromAge(minAge)
                          updateConfig('max_date', maxDate)
                        }}
                      />
                      <Form.Text className="text-muted">
                        Youngest age (e.g., 18 for adults)
                      </Form.Text>
                    </Form.Group>
                  </Col>
                  <Col md={6}>
                    <Form.Group className="mb-3">
                      <Form.Label>Maximum Age (years)</Form.Label>
                      <Form.Control
                        type="number"
                        min="0"
                        max="150"
                        value={Number(config.max_age ?? 65)}
                        onChange={e => {
                          const maxAge = Number(e.target.value)
                          updateConfig('max_age', maxAge)
                          // Auto-calculate date range
                          const minDate = calculateDateFromAge(maxAge)
                          updateConfig('min_date', minDate)
                        }}
                      />
                      <Form.Text className="text-muted">
                        Oldest age (e.g., 65 for working adults)
                      </Form.Text>
                    </Form.Group>
                  </Col>
                </Row>
                
                <Alert variant="secondary" className="small">
                  <strong>Calculated Date Range:</strong>
                  <div className="mt-1">
                    From: <code>{String(config.min_date || calculateDateFromAge(Number(config.max_age ?? 65)))}</code>
                    {' '}to{' '}
                    <code>{String(config.max_date || calculateDateFromAge(Number(config.min_age ?? 18)))}</code>
                  </div>
                  <div className="text-muted mt-1">
                    Ages {String(config.min_age ?? 18)} to {String(config.max_age ?? 65)} years old
                  </div>
                </Alert>
              </>
            )}
            
            <Form.Group className="mb-3">
              <Form.Label>Locale</Form.Label>
              <Form.Control
                type="text"
                value={String(config.locale ?? 'en_US')}
                onChange={e => updateConfig('locale', e.target.value)}
                placeholder="en_US"
              />
              <Form.Text className="text-muted">
                Language/region for generated data (e.g., en_US, fr_FR, de_DE)
              </Form.Text>
            </Form.Group>
          </>
        )
      
      case 'pattern':
        return (
          <>
            <Form.Group className="mb-3">
              <Form.Label>Pattern Mask <Badge bg="info">Required</Badge></Form.Label>
              <Form.Control
                type="text"
                value={String(config.mask ?? '')}
                onChange={e => updateConfig('mask', e.target.value)}
                placeholder="AAA-####"
              />
              <Form.Text className="text-muted">
                Pattern tokens: # (digit), A (uppercase), a (lowercase), ? (alphanumeric)
              </Form.Text>
            </Form.Group>
            
            <Alert variant="secondary" className="small">
              <strong>Examples:</strong>
              <ul className="mb-0 mt-2">
                <li><code>AAA-####</code> → ABC-1234</li>
                <li><code>###-##-####</code> → 123-45-6789 (SSN format)</li>
                <li><code>????-????-????</code> → aB3f-xY9k-2Lm8</li>
              </ul>
            </Alert>
          </>
        )
      
      case 'sequence':
        return (
          <>
            <Row>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Start Value</Form.Label>
                  <Form.Control
                    type="number"
                    value={Number(config.start ?? 1)}
                    onChange={e => updateConfig('start', Number(e.target.value))}
                  />
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Step</Form.Label>
                  <Form.Control
                    type="number"
                    value={Number(config.step ?? 1)}
                    onChange={e => updateConfig('step', Number(e.target.value))}
                  />
                </Form.Group>
              </Col>
            </Row>
            
            <Form.Group className="mb-3">
              <Form.Label>Template (optional)</Form.Label>
              <Form.Control
                type="text"
                value={String(config.template ?? '')}
                onChange={e => updateConfig('template', e.target.value)}
                placeholder="ORDER-{value}"
              />
              <Form.Text className="text-muted">
                Python format string: &#123;i&#125; = row index, &#123;value&#125; = computed value
              </Form.Text>
            </Form.Group>
            
            <Alert variant="secondary" className="small">
              <strong>Example:</strong> start=100, step=10, template="ID-&#123;value&#125;" → ID-100, ID-110, ID-120...
            </Alert>
          </>
        )
      
      case 'categorical':
        return (
          <>
            <Form.Label>Categories <Badge bg="info">Required</Badge></Form.Label>
            <ListGroup className="mb-3">
              {categories.map((cat, idx) => (
                <ListGroup.Item key={idx} className="d-flex gap-2 align-items-center">
                  <Form.Control
                    type="text"
                    value={cat.value}
                    onChange={e => updateCategory(idx, 'value', e.target.value)}
                    placeholder="Category value"
                    className="flex-grow-1"
                  />
                  <Form.Control
                    type="number"
                    step="0.01"
                    min="0"
                    max="1"
                    value={cat.weight}
                    onChange={e => updateCategory(idx, 'weight', Number(e.target.value))}
                    placeholder="Weight"
                    style={{ width: '100px' }}
                  />
                  <Button
                    variant="outline-danger"
                    size="sm"
                    onClick={() => removeCategory(idx)}
                    disabled={categories.length === 1}
                  >
                    Remove
                  </Button>
                </ListGroup.Item>
              ))}
            </ListGroup>
            
            <div className="d-flex gap-2 mb-3">
              <Button variant="outline-primary" size="sm" onClick={addCategory}>
                Add Category
              </Button>
              <Button variant="outline-secondary" size="sm" onClick={normalizeWeights}>
                Normalize Weights
              </Button>
            </div>
            
            <Alert variant="secondary" className="small">
              <div>Total weight: <strong>{categories.reduce((s, c) => s + c.weight, 0).toFixed(3)}</strong></div>
              <div className="text-muted mt-1">Weights must sum to 1.0. Use "Normalize" to auto-adjust.</div>
            </Alert>
          </>
        )
      
      case 'expression':
        return (
          <>
            <Form.Group className="mb-3">
              <Form.Label>Python Expression <Badge bg="info">Required</Badge></Form.Label>
              <Form.Control
                as="textarea"
                rows={3}
                value={String(config.expression ?? '')}
                onChange={e => updateConfig('expression', e.target.value)}
                placeholder="i * 10"
              />
              <Form.Text className="text-muted">
                Available: i (row index), rng (random), math module, context dict
              </Form.Text>
            </Form.Group>
            
            <Alert variant="secondary" className="small">
              <strong>Examples:</strong>
              <ul className="mb-0 mt-2">
                <li><code>i * 10</code> → 0, 10, 20, 30...</li>
                <li><code>rng.randint(1, 100)</code> → random 1-100</li>
                <li><code>math.sqrt(i + 1)</code> → 1.0, 1.414, 1.732...</li>
              </ul>
            </Alert>
          </>
        )
      
      case 'geo':
        return (
          <>
            <Row>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Min Latitude</Form.Label>
                  <Form.Control
                    type="number"
                    step="0.000001"
                    value={Number(config.min_lat ?? -90)}
                    onChange={e => updateConfig('min_lat', Number(e.target.value))}
                  />
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Max Latitude</Form.Label>
                  <Form.Control
                    type="number"
                    step="0.000001"
                    value={Number(config.max_lat ?? 90)}
                    onChange={e => updateConfig('max_lat', Number(e.target.value))}
                  />
                </Form.Group>
              </Col>
            </Row>
            
            <Row>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Min Longitude</Form.Label>
                  <Form.Control
                    type="number"
                    step="0.000001"
                    value={Number(config.min_lon ?? -180)}
                    onChange={e => updateConfig('min_lon', Number(e.target.value))}
                  />
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Max Longitude</Form.Label>
                  <Form.Control
                    type="number"
                    step="0.000001"
                    value={Number(config.max_lon ?? 180)}
                    onChange={e => updateConfig('max_lon', Number(e.target.value))}
                  />
                </Form.Group>
              </Col>
            </Row>
            
            <Form.Group className="mb-3">
              <Form.Check
                type="checkbox"
                label="Return as dictionary (lat/lon keys)"
                checked={Boolean(config.as_dict)}
                onChange={e => updateConfig('as_dict', e.target.checked)}
              />
            </Form.Group>
          </>
        )
      
      case 'checksum-valid':
        return (
          <>
            <Form.Group className="mb-3">
              <Form.Label>Length</Form.Label>
              <Form.Control
                type="number"
                min="1"
                value={Number(config.length ?? 16)}
                onChange={e => updateConfig('length', Number(e.target.value))}
              />
              <Form.Text className="text-muted">
                Total length of generated checksum string
              </Form.Text>
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Prefix (optional)</Form.Label>
              <Form.Control
                type="text"
                value={String(config.prefix ?? '')}
                onChange={e => updateConfig('prefix', e.target.value)}
                placeholder="CHK-"
              />
            </Form.Group>
          </>
        )
      
      case 'reference':
        return (
          <>
            <Form.Group className="mb-3">
              <Form.Label>Reference Key <Badge bg="info">Required</Badge></Form.Label>
              <Form.Control
                type="text"
                value={String(config.key ?? '')}
                onChange={e => updateConfig('key', e.target.value)}
                placeholder="table_name.column_name"
              />
              <Form.Text className="text-muted">
                Format: table_name.column_name (references parent table column)
              </Form.Text>
            </Form.Group>
            
            <Alert variant="warning" className="small">
              <strong>Note:</strong> The referenced table must be generated before this table in the execution order.
            </Alert>
          </>
        )
      
      case 'empirical':
        return (
          <>
            <Form.Group className="mb-3">
              <Form.Label>CSV File Path <Badge bg="info">Required</Badge></Form.Label>
              <Form.Control
                type="text"
                value={String(config.csv_path ?? '')}
                onChange={e => updateConfig('csv_path', e.target.value)}
                placeholder="/path/to/data.csv"
              />
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Column Name (optional)</Form.Label>
              <Form.Control
                type="text"
                value={String(config.column ?? '')}
                onChange={e => updateConfig('column', e.target.value)}
                placeholder="column_name"
              />
              <Form.Text className="text-muted">
                Leave empty to use first column
              </Form.Text>
            </Form.Group>
          </>
        )
      
      default:
        return (
          <Alert variant="info">
            No additional configuration required for <strong>{provider}</strong> provider.
          </Alert>
        )
    }
  }

  const totalWeight = categories.reduce((s, c) => s + c.weight, 0)
  const isWeightValid = Math.abs(totalWeight - 1.0) <= 0.001

  return (
    <Modal show={show} onHide={onHide} size="lg" animation={false}>
      <Modal.Header closeButton>
        <Modal.Title>
          Configure {provider} Provider
          <div className="text-muted small mt-1">
            Column: <code>{columnName}</code> ({columnType})
          </div>
        </Modal.Title>
      </Modal.Header>
      
      <Modal.Body>
        {error && (
          <Alert variant="danger" onClose={() => setError(null)} dismissible>
            {error}
          </Alert>
        )}
        
        {renderProviderFields()}
        
        <hr />
        
        <Form.Group className="mb-0">
          <Form.Check
            type="checkbox"
            label="Enforce uniqueness (no duplicate values)"
            checked={Boolean(config.unique)}
            onChange={e => updateConfig('unique', e.target.checked)}
          />
          <Form.Text className="text-muted">
            When enabled, all generated values must be unique
          </Form.Text>
        </Form.Group>
      </Modal.Body>
      
      <Modal.Footer>
        <div className="d-flex justify-content-between w-100">
          <div className="text-muted small align-self-center">
            {provider === 'categorical' && !isWeightValid && (
              <span className="text-danger">⚠ Weights must sum to 1.0</span>
            )}
          </div>
          <div className="d-flex gap-2">
            <Button variant="secondary" onClick={onHide}>
              Cancel
            </Button>
            <Button variant="primary" onClick={handleSave}>
              Apply Configuration
            </Button>
          </div>
        </div>
      </Modal.Footer>
    </Modal>
  )
}
