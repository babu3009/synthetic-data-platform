import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import LlmProvidersPage from '../pages/admin/llm_providers_page'

const markDefaultMock = vi.fn()
const refetchMock = vi.fn()

vi.mock('../hooks/use_llm_admin', () => {
  return {
    useLlmProviders: () => ({
      data: [
        { id: 'prov1', kind: 'openai', name: 'OpenAI', base_url: '', is_enabled: true, updated_at: new Date().toISOString() },
      ],
      isLoading: false,
      isError: false,
    }),
    useUpdateLlmProvider: () => ({ mutate: vi.fn(), isPending: false }),
    useCreateLlmProvider: () => ({ mutate: vi.fn(), isPending: false, isError: false }),
    useCreateLlmModel: () => ({ mutate: vi.fn(), isPending: false }),
    useLlmModels: () => ({
      data: [
        { id: 'm1', provider_id: 'prov1', name: 'gpt-3.5-turbo', display_name: 'gpt-3.5-turbo', is_default: true },
        { id: 'm2', provider_id: 'prov1', name: 'gpt-4o-mini', display_name: 'gpt-4o-mini', is_default: false },
      ],
      isLoading: false,
      isError: false,
      refetch: refetchMock,
    }),
    useMarkModelDefault: () => ({ mutate: markDefaultMock, isPending: false }),
  }
})

vi.mock('../hooks/use_toasts', () => ({ useToasts: () => ({ push: vi.fn() }) }))

function renderPage() {
  const qc = new QueryClient()
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <LlmProvidersPage />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Admin LLM Providers inline models', () => {
  beforeEach(() => {
    markDefaultMock.mockReset()
    refetchMock.mockReset()
    localStorage.setItem('role', 'OWNER')
  })

  it('shows models and allows selecting default via radio', async () => {
    renderPage()
    const user = userEvent.setup()

    // Expand models
  const showBtn = await screen.findByLabelText(/toggle models list/i)
    await user.click(showBtn)

    // Radios should be present; verify clicking non-default triggers mutation
    const radios = await screen.findAllByRole('radio')
    expect(radios.length).toBeGreaterThanOrEqual(2)
    // Click the non-default radio to call mark default
    await user.click(radios[1])
    expect(markDefaultMock).toHaveBeenCalled()
  })

  it('refresh button refetches models when visible', async () => {
    // Ensure expanded state via persisted storage
    localStorage.setItem('llm:showModels:prov1', '1')
    renderPage()
    const user = userEvent.setup()

    const refreshBtn = await screen.findByLabelText(/refresh models/i)
    await user.click(refreshBtn)
    expect(refetchMock).toHaveBeenCalled()
  })
})
