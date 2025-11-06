import { useEffect } from 'react'
import { Tabs, Tab, Container } from 'react-bootstrap'
import { useSearchParams } from 'react-router-dom'
import { WizardProvider, useWizard } from '../state/wizard'
import EntitiesPage from './wizard/entities_page'
import DiagramPage from './wizard/diagram_page'
import ProvidersPiiPage from './wizard/providers_pii_page'

function WizardInner() {
  const { state, dispatch } = useWizard()
  const [params] = useSearchParams()

  useEffect(() => {
    const pid = params.get('projectId') || undefined
    if (pid) dispatch({ type: 'setProject', projectId: pid })
  }, [params, dispatch])

  return (
    <Container className="py-3">
      <h2 className="mb-3">Data Wizard</h2>
      <Tabs
        activeKey={state.activeTab || 'entities'}
        onSelect={(k) =>
          dispatch({
            type: 'setActiveTab',
            tab: ((k as 'entities' | 'diagram' | 'providers' | null) || 'entities'),
          })
        }
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
