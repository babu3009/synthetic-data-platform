import React from 'react'
import { useParams } from 'react-router-dom'
import { Button, Table, Badge, Spinner, Form } from 'react-bootstrap'
import { useLlmProviders, useUpdateLlmProvider } from '../../hooks/use_llm_admin'
import type { LLMProvider } from '../../services/llm_admin'
import { ProviderFormModal } from '../../components/admin/llm/provider_form_modal'
import { CredentialsModal } from '../../components/admin/llm/credentials_modal'
import { DiscoverDrawer } from '../../components/admin/llm/discover_drawer'

// Simple OWNER guard: checks localStorage role (server enforces RBAC regardless)
function useOwnerGuard() {
  const role = localStorage.getItem('role') || 'OWNER'
  return role === 'OWNER'
}

export default function LlmProvidersPage() {
  // Project context: prefer route param like /admin/:projectId/llm-providers, fallback to ?projectId
  const params = useParams()
  const search = new URLSearchParams(window.location.search)
  const projectId = params.projectId || search.get('projectId') || ''
  const isOwner = useOwnerGuard()
  const [showAdd, setShowAdd] = React.useState(false)
  const [credTarget, setCredTarget] = React.useState<{ id: string; masked?: { api_key?: string; org_id?: string } } | null>(null)
  const [discoverTarget, setDiscoverTarget] = React.useState<string | null>(null)

  const providersQ = useLlmProviders(projectId)

  const columns = ['Name', 'Kind', 'Base URL', 'Enabled', 'Models', 'Updated', 'Actions']

  React.useEffect(() => {
    if (!projectId) {
      // Navigate to home if no project context; in a real app, pick from selector
      console.warn('Missing projectId; append ?projectId=<uuid> to URL to scope admin APIs')
    }
  }, [projectId])

  if (!isOwner) {
    return <div className="container mt-4">You need OWNER role to view this page.</div>
  }

  return (
    <div className="container mt-4">
      <div className="d-flex align-items-center justify-content-between mb-3">
        <h2 className="m-0">LLM Providers</h2>
        <div className="d-flex gap-2">
          <Button variant="primary" onClick={() => setShowAdd(true)}>Add Provider</Button>
        </div>
      </div>
      {providersQ.isLoading && (
        <div className="d-flex align-items-center gap-2"><Spinner size="sm" /> <span>Loading providers…</span></div>
      )}
      {providersQ.isError && (
        <div className="text-danger">Failed to load providers.</div>
      )}
      {providersQ.data && (
        <Table striped hover responsive>
          <thead>
            <tr>
              {columns.map((c) => <th key={c}>{c}</th>)}
            </tr>
          </thead>
          <tbody>
            {providersQ.data.map((p) => (
              <ProviderRow key={p.id} projectId={projectId} provider={p} onManageCreds={() => setCredTarget({ id: p.id })} onDiscover={() => setDiscoverTarget(p.id)} />
            ))}
          </tbody>
        </Table>
      )}

      <ProviderFormModal projectId={projectId} show={showAdd} onHide={() => setShowAdd(false)} />
      {credTarget && (
        <CredentialsModal
          projectId={projectId}
          providerId={credTarget.id}
          show={!!credTarget}
          onHide={() => setCredTarget(null)}
          masked={{}}
        />
      )}
      {discoverTarget && (
        <DiscoverDrawer projectId={projectId} providerId={discoverTarget} show={!!discoverTarget} onHide={() => setDiscoverTarget(null)} />
      )}
    </div>
  )
}

function ProviderRow({ projectId, provider, onManageCreds, onDiscover }: { projectId: string; provider: LLMProvider; onManageCreds: () => void; onDiscover: () => void }) {
  const toggleMut = useUpdateLlmProvider(projectId, provider.id)

  const onToggle = () => {
    toggleMut.mutate({ is_enabled: !provider.is_enabled })
  }

  return (
    <tr>
      <td>{provider.name}</td>
      <td><Badge bg="secondary">{provider.kind}</Badge></td>
  <td className="text-truncate" data-maxwidth="320">{provider.base_url}</td>
      <td>
        <Form.Check
          type="switch"
          checked={provider.is_enabled}
          disabled={toggleMut.isPending}
          onChange={onToggle}
          aria-label={`Toggle ${provider.name}`}
        />
      </td>
      <td>{provider.models_count ?? '—'}</td>
      <td>{provider.updated_at ? new Date(provider.updated_at).toLocaleString() : '—'}</td>
      <td className="text-end">
        <div className="d-flex justify-content-end gap-2">
          <Button size="sm" variant="outline-secondary" onClick={onManageCreds}>Credentials</Button>
          <Button size="sm" variant="outline-primary" onClick={onDiscover}>Discover</Button>
        </div>
      </td>
    </tr>
  )
}
