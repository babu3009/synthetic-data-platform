import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import ProjectApiKeysPage from '../pages/projects/project_api_keys_page'
import { TestProviders, withRoute } from './utils/TestProviders'
import * as svc from '../services/apiKeys'
import { describe, it, beforeEach, expect, vi } from 'vitest'

vi.mock('../services/apiKeys', () => ({
  listApiKeys: vi.fn(),
  createApiKey: vi.fn(),
  revokeApiKey: vi.fn(),
  listApiKeyScopes: vi.fn(),
}))

const listApiKeys = svc.listApiKeys as unknown as ReturnType<typeof vi.fn>
const createApiKey = svc.createApiKey as unknown as ReturnType<typeof vi.fn>
const revokeApiKey = svc.revokeApiKey as unknown as ReturnType<typeof vi.fn>
const listApiKeyScopes = svc.listApiKeyScopes as unknown as ReturnType<typeof vi.fn>

function renderPage(initial = ['/projects/p123/api-keys']) {
  return render(
    <TestProviders initialEntries={initial} routes={withRoute('/projects/:projectId/api-keys', <ProjectApiKeysPage />)}>
      <div />
    </TestProviders>
  )
}

describe('ProjectApiKeysPage', () => {
  beforeEach(() => {
    listApiKeys.mockResolvedValue([
      { id: 'k1', project_id: 'p123', name: 'default', scopes: ['read:project'], created_at: new Date('2025-11-11T00:00:00Z').toISOString() }
    ])
    listApiKeyScopes.mockResolvedValue(['read:project', 'write:project', 'run:request', 'read:artifacts'])
    createApiKey.mockResolvedValue({ id: 'k2', project_id: 'p123', name: 'new', scopes: ['read:project','write:project'], created_at: new Date().toISOString(), plaintext_key: 'PLAINTEXT' })
    revokeApiKey.mockResolvedValue({ id: 'k1', project_id: 'p123', name: 'default', scopes: ['read'], created_at: new Date().toISOString() })
  })

  it('renders list of API keys', async () => {
    renderPage()
    expect(await screen.findByText('API Keys')).toBeInTheDocument()
    expect(await screen.findByText('default')).toBeInTheDocument()
  })

  it('creates an API key and shows plaintext once', async () => {
    renderPage()
    fireEvent.click(await screen.findByText('Create Key'))
    const scopesLabels = screen.getAllByText('Scopes')
    const labelEl = scopesLabels.find(el => (el as HTMLElement).tagName.toLowerCase() === 'label') as HTMLElement
    const form = labelEl.closest('form') as HTMLElement
    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'new' } })
    // Select dynamic scopes returned by backend
    fireEvent.click(within(form).getByRole('button', { name: 'read:project' }))
    fireEvent.click(within(form).getByRole('button', { name: 'write:project' }))
    fireEvent.click(screen.getByText('Create'))
    await waitFor(() => expect(createApiKey).toHaveBeenCalled())
    expect(screen.getByText(/Copy your new key now/)).toBeInTheDocument()
    expect(screen.getByText('PLAINTEXT')).toBeInTheDocument()
  })

  it('revokes an API key', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderPage()
    const revokeBtn = await screen.findByText('Revoke')
    fireEvent.click(revokeBtn)
    await waitFor(() => expect(revokeApiKey).toHaveBeenCalled())
  })
})
