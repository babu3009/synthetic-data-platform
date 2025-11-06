import { Container, Row, Col, Card, Button } from 'react-bootstrap'
import { useQuery } from '@tanstack/react-query'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

import { api } from '../services/api'

// Mock data for the chart
const sampleData = [
  { name: 'Jan', datasets: 120, records: 45000 },
  { name: 'Feb', datasets: 150, records: 62000 },
  { name: 'Mar', datasets: 180, records: 78000 },
  { name: 'Apr', datasets: 200, records: 85000 },
  { name: 'May', datasets: 170, records: 72000 },
  { name: 'Jun', datasets: 220, records: 95000 },
]

function HomePage() {
  const { data: healthData, isLoading: healthLoading } = useQuery({
    queryKey: ['health'],
    queryFn: () => api.get('/health').then((res) => res.data),
  })

  return (
    <>
      {/* Hero Section */}
      <section className="hero-section">
        <Container>
          <Row>
            <Col>
              <h1 className="display-4 fw-bold mb-4">
                Generate High-Quality Synthetic Data
              </h1>
              <p className="lead mb-4">
                Create realistic, privacy-compliant datasets for testing, development, 
                and machine learning with our advanced synthetic data platform.
              </p>
              <Button variant="light" size="lg" className="me-3">
                Get Started
              </Button>
              <Button variant="outline-light" size="lg">
                Learn More
              </Button>
            </Col>
          </Row>
        </Container>
      </section>

      {/* Main Content */}
      <Container className="my-5">
        {/* Status Check */}
        <Row className="mb-5">
          <Col md={6}>
            <Card className="h-100 feature-card">
              <Card.Body>
                <Card.Title>
                  <i className="bi bi-check-circle-fill text-success me-2"></i>
                  System Status
                </Card.Title>
                {healthLoading ? (
                  <div className="text-muted">Checking system status...</div>
                ) : healthData ? (
                  <div>
                    <div className="text-success">✓ API: {healthData.status === 'ok' ? 'Online' : 'Offline'}</div>
                    <small className="text-muted">{healthData.message}</small>
                  </div>
                ) : (
                  <div className="text-warning">Status check failed</div>
                )}
              </Card.Body>
            </Card>
          </Col>

          <Col md={6}>
            <Card className="h-100 feature-card">
              <Card.Body>
                <Card.Title>
                  <i className="bi bi-graph-up text-primary me-2"></i>
                  Quick Stats
                </Card.Title>
                <div>
                  <div><strong>220</strong> datasets generated this month</div>
                  <div><strong>95k</strong> records created</div>
                  <div><strong>99.9%</strong> uptime</div>
                </div>
              </Card.Body>
            </Card>
          </Col>
        </Row>

        {/* Synthetic Data Wizard Placeholder */}
        <Row className="mb-5">
          <Col>
            <div className="wizard-placeholder text-center">
              <h3 className="mb-3">🎲 Synthetic Data Wizard</h3>
              <p className="mb-4">
                This is where the synthetic data generation wizard will be implemented.
                Users will be able to define schemas, configure data types, and generate
                realistic datasets with just a few clicks.
              </p>
              <Button variant="primary" size="lg" disabled>
                Launch Wizard (Coming Soon)
              </Button>
            </div>
          </Col>
        </Row>

        {/* Data Generation Analytics */}
        <Row className="mb-5">
          <Col>
            <Card>
              <Card.Header>
                <h4 className="mb-0">Data Generation Analytics</h4>
              </Card.Header>
              <Card.Body>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={sampleData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis yAxisId="left" />
                    <YAxis yAxisId="right" orientation="right" />
                    <Tooltip />
                    <Bar yAxisId="left" dataKey="datasets" fill="#8884d8" name="Datasets" />
                    <Bar yAxisId="right" dataKey="records" fill="#82ca9d" name="Records" />
                  </BarChart>
                </ResponsiveContainer>
              </Card.Body>
            </Card>
          </Col>
        </Row>

        {/* Features Grid */}
        <Row>
          <Col md={4} className="mb-4">
            <Card className="h-100 feature-card">
              <Card.Body>
                <Card.Title>
                  <i className="bi bi-table text-primary me-2"></i>
                  Schema Builder
                </Card.Title>
                <Card.Text>
                  Define custom data schemas with various field types, 
                  constraints, and relationships.
                </Card.Text>
              </Card.Body>
            </Card>
          </Col>

          <Col md={4} className="mb-4">
            <Card className="h-100 feature-card">
              <Card.Body>
                <Card.Title>
                  <i className="bi bi-shield-check text-success me-2"></i>
                  Privacy Compliant
                </Card.Title>
                <Card.Text>
                  Generate datasets that maintain statistical properties 
                  while ensuring privacy protection.
                </Card.Text>
              </Card.Body>
            </Card>
          </Col>

          <Col md={4} className="mb-4">
            <Card className="h-100 feature-card">
              <Card.Body>
                <Card.Title>
                  <i className="bi bi-download text-info me-2"></i>
                  Multiple Formats
                </Card.Title>
                <Card.Text>
                  Export your synthetic data in various formats including 
                  CSV, JSON, Parquet, and Excel.
                </Card.Text>
              </Card.Body>
            </Card>
          </Col>
        </Row>
      </Container>
    </>
  )
}

export default HomePage
