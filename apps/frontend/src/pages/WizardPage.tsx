import { useEffect } from 'react'
import { Tabs, Tab, Container } from 'react-bootstrap'
import { useSearchParams } from 'react-router-dom'
import { WizardProvider, useWizard } from '../state/wizard'
import EntitiesPage from './wizard/EntitiesPage'
import DiagramPage from './wizard/DiagramPage'

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
      <Tabs activeKey={state.activeTab || 'entities'} onSelect={(k) => dispatch({ type: 'setActiveTab', tab: (k as any) || 'entities' })}>
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
