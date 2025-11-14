import { useEffect } from 'react'
import { Tabs, Tab, Container, Card, Badge } from 'react-bootstrap'
import { useSearchParams, useLocation, useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getProject, type Project } from '../services/projects'
import { WizardProvider, useWizard } from '../state/wizard'
import { useUnsavedChangesWarning } from '../hooks/use_unsaved_changes'
import EntitiesPage from './wizard/entities_page'
import DiagramPage from './wizard/diagram_page'
import ProvidersPiiPage from './wizard/providers_pii_page'
import RulesPage from './wizard/rules_page'
import OutputsRunPage from './wizard/outputs_run_page'

function WizardInner() {
  const { state, dispatch } = useWizard()
  const [query] = useSearchParams()
  const params = useParams()
  const navigate = useNavigate()
  const location = useLocation()

  // Global unsaved-changes guard
  const { confirmProceed } = useUnsavedChangesWarning(state.isDirty)

  useEffect(() => {
    const routePid = params.projectId
    const queryPid = query.get('projectId') || undefined
    // Redirect legacy /wizard?projectId=... to /projects/:projectId/wizard
    if (!routePid && queryPid && location.pathname === '/wizard') {
      navigate(`/projects/${queryPid}/wizard`, { replace: true })
      return
    }
    const pid = (routePid || queryPid) as string | undefined
    if (pid) dispatch({ type: 'setProject', projectId: pid })
  }, [params, query, dispatch, navigate, location.pathname])

  // Fetch project details
  const { data: project, isLoading: projectLoading } = useQuery<Project>({
    queryKey: ['projects.detail', state.projectId],
    queryFn: () => getProject(state.projectId!),
    enabled: !!state.projectId,
  })

  return (
    <Container className="py-3">
      <h2 className="mb-3">Data Wizard</h2>
      
      {/* Project Info Card */}
      {state.projectId && (
        <Card className="mb-3">
          <Card.Body>
            {projectLoading ? (
              <div className="d-flex align-items-center">
                <div className="spinner-border spinner-border-sm me-2" role="status">
                  <span className="visually-hidden">Loading...</span>
                </div>
                <span className="text-muted">Loading project details...</span>
              </div>
            ) : project ? (
              <div>
                <div className="d-flex justify-content-between align-items-start mb-2">
                  <div>
                    <h5 className="mb-1">{project.name}</h5>
                    {project.description && (
                      <p className="text-muted mb-2">{project.description}</p>
                    )}
                  </div>
                  {project.tags && project.tags.length > 0 && (
                    <div className="d-flex flex-wrap gap-1">
                      {project.tags.map((tag, i) => (
                        <Badge key={i} bg="secondary">{tag}</Badge>
                      ))}
                    </div>
                  )}
                </div>
                <div className="text-muted small">
                  {project.webhook_run_status_url && (
                    <span className="me-3">
                      <i className="bi bi-webhook me-1"></i>Webhook enabled
                    </span>
                  )}
                  {project.artifact_ttl_days !== null && project.artifact_ttl_days !== undefined && (
                    <span>
                      <i className="bi bi-clock-history me-1"></i>Artifact TTL: {project.artifact_ttl_days} days
                    </span>
                  )}
                </div>
              </div>
            ) : (
              <div className="text-muted">Project not found</div>
            )}
          </Card.Body>
        </Card>
      )}
      
      <Tabs
        activeKey={state.activeTab || 'entities'}
        onSelect={(k) => {
          const next = ((k as 'entities' | 'diagram' | 'providers' | 'rules' | 'run' | null) || 'entities')
          if (!confirmProceed()) return
          dispatch({ type: 'setActiveTab', tab: next })
        }}
      >
        <Tab eventKey="entities" title="Entities">
          <div className="pt-3">
            <EntitiesPage />
          </div>
        </Tab>
        <Tab eventKey="diagram" title="Diagram">
          <div className="pt-3">
            <DiagramPage />
          </div>
        </Tab>
        <Tab eventKey="providers" title="Providers & PII">
          <div className="pt-3">
            <ProvidersPiiPage />
          </div>
        </Tab>
        <Tab eventKey="rules" title="Rules">
          <div className="pt-3">
            <RulesPage />
          </div>
        </Tab>
        <Tab eventKey="run" title="Outputs & Run">
          <div className="pt-3">
            <OutputsRunPage />
          </div>
        </Tab>
      </Tabs>
    </Container>
  )
}

export default function WizardPage() {
  return (
    <WizardProvider>
      <WizardInner />
    </WizardProvider>
  )
}
