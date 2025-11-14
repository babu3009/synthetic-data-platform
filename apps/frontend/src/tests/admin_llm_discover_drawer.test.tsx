import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import LlmProvidersPage from '../pages/admin/llm_providers_page'
import type { DiscoverModelsResponse } from '../services/llm_admin'

const discoverMutateMock = vi.fn()
const markDefaultMock = vi.fn()

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
    useCreateLlmProvider: () => ({ mutate: vi.fn(), isPending: false }),
    useLlmModels: () => ({ data: [], isLoading: false, isError: false, refetch: vi.fn() }),
    useCreateLlmModel: () => ({ mutate: vi.fn(), isPending: false }),
    useDiscoverModels: () => ({ mutate: discoverMutateMock, isPending: false, data: { added_count: 1, updated_count: 0, unchanged_count: 0 } }),
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

describe('Discover drawer parity', () => {
  beforeEach(() => {
    // jsdom doesn't implement matchMedia; react-bootstrap Offcanvas uses it via useBreakpoint
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    })
  discoverMutateMock.mockImplementation((_v: unknown, opts?: { onSuccess?: (resp: DiscoverModelsResponse) => void }) => {
      // Simulate successful discovery returning two models
      opts?.onSuccess?.({
        models: [
          { id: 'm1', provider_id: 'prov1', name: 'gpt-3.5-turbo', display_name: 'gpt-3.5-turbo', is_default: true },
          { id: 'm2', provider_id: 'prov1', name: 'gpt-4o-mini', display_name: 'gpt-4o-mini', is_default: false },
        ],
        added_count: 1,
        updated_count: 0,
        unchanged_count: 0,
      })
    })
    markDefaultMock.mockReset()
    localStorage.setItem('role', 'OWNER')
  })

  it('opens drawer, shows models, and allows Make Default', async () => {
    renderPage()
    const user = userEvent.setup()

    // Open Discover drawer
    const discoverBtn = await screen.findByRole('button', { name: /discover/i })
    await user.click(discoverBtn)

    // Drawer title should appear
    await screen.findByText(/discover models/i)

    // We should see the Make Default button for the non-default model
    const makeDefaultBtns = await screen.findAllByRole('button', { name: /make default/i })
    expect(makeDefaultBtns.length).toBeGreaterThanOrEqual(1)
    await user.click(makeDefaultBtns[0])
    expect(markDefaultMock).toHaveBeenCalled()
  })
})
