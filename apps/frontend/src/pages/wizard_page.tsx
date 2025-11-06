import { useEffect } from 'react'
import { Tabs, Tab, Container } from 'react-bootstrap'
import { useSearchParams } from 'react-router-dom'
import { WizardProvider, useWizard } from '../state/wizard'
import { useUnsavedChangesWarning } from '../hooks/use_unsaved_changes'
import EntitiesPage from './wizard/entities_page'
import DiagramPage from './wizard/diagram_page'
import ProvidersPiiPage from './wizard/providers_pii_page'
import RulesPage from './wizard/rules_page'
import OutputsRunPage from './wizard/outputs_run_page'

function WizardInner() {
  const { state, dispatch } = useWizard()
  const [params] = useSearchParams()

  // Global unsaved-changes guard
  const { confirmProceed } = useUnsavedChangesWarning(state.isDirty)

  useEffect(() => {
    const pid = params.get('projectId') || undefined
    if (pid) dispatch({ type: 'setProject', projectId: pid })
  }, [params, dispatch])

  return (
    <Container className="py-3">
      <h2 className="mb-3">Data Wizard</h2>
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
