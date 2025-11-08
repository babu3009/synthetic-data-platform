import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { act } from 'react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import LlmSettingsPage from '../pages/llm_settings_page'

// Mocks for hooks used by the page
const saveMutate = vi.fn()
const inferMutate = vi.fn()

vi.mock('../hooks/use_llm_settings', () => {
  return {
  useLlmSettings: (_projectId: string) => ({
      data: {
        enabled: true,
        provider_id: 'prov1',
        model_id: null,
        temperature: 0.7,
        top_p: 1,
        max_tokens: 256,
        guardrails: { block_pii: true, allow_tool_use: false },
      },
      isLoading: false,
      isError: false,
    }),
    useSaveLlmSettings: () => ({ mutate: saveMutate, isPending: false }),
  }
})

vi.mock('../hooks/use_llm_admin', () => {
  return {
    useLlmProviders: () => ({
      data: [
        { id: 'prov1', kind: 'openai', name: 'openai-admin', base_url: '', is_enabled: true },
        { id: 'prov2', kind: 'ollama', name: 'ollama-local', base_url: 'http://localhost:11434', is_enabled: false },
      ],
      isLoading: false,
      isError: false,
    }),
    useLlmModels: (_projectId: string, providerId: string) => ({
      data: providerId === 'prov1'
        ? [
            { id: 'm1', provider_id: 'prov1', name: 'gpt-3.5-turbo', display_name: 'gpt-3.5-turbo' },
            { id: 'm2', provider_id: 'prov1', name: 'gpt-4o-mini', display_name: 'gpt-4o-mini' },
          ]
        : [],
      isLoading: false,
      isError: false,
    }),
  }
})

vi.mock('../hooks/use_infer_providers', () => {
  return {
    useInferProviders: () => ({ mutate: inferMutate, isPending: false, isError: false, data: [] }),
  }
})

function renderWithProviders(path = '/projects/abc/llm-settings') {
  const qc = new QueryClient()
  return render(
    <QueryClientProvider client={qc}>
      {/* Remove future flags to avoid startTransition warnings in tests */}
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/projects/:projectId/llm-settings" element={<LlmSettingsPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('LLM Settings Page', () => {
  beforeEach(() => {
    saveMutate.mockReset()
    inferMutate.mockReset()
  })

  it('disables editing for VIEWER role', async () => {
    localStorage.setItem('role', 'VIEWER')
    renderWithProviders()

    const saveBtn = await screen.findByRole('button', { name: /save settings/i })
    expect(saveBtn).toBeDisabled()

    const providerSelect = screen.getByLabelText(/LLM provider select/i) as HTMLSelectElement
    expect(providerSelect).toBeDisabled()
  })

  it('lists only enabled providers and models for selected provider', async () => {
    localStorage.setItem('role', 'OWNER')
    renderWithProviders()

    // Provider select should include only the enabled provider (prov1)
    const providerSelect = await screen.findByLabelText(/LLM provider select/i)
    const options = Array.from((providerSelect as HTMLSelectElement).options).map(o => o.textContent?.trim())
    expect(options.some(t => t?.includes('openai-admin'))).toBe(true)
    expect(options.some(t => t?.includes('ollama-local'))).toBe(false)

    // Models should reflect the selected provider (prov1)
    const modelSelect = await screen.findByLabelText(/LLM model select/i)
    expect(modelSelect).not.toBeDisabled()
    const modelOptions = Array.from((modelSelect as HTMLSelectElement).options).map(o => o.textContent?.trim())
    expect(modelOptions.some(t => t === 'gpt-3.5-turbo')).toBe(true)
    expect(modelOptions.some(t => t === 'gpt-4o-mini')).toBe(true)
  })

  it('opens Test Suggestions panel on click', async () => {
    localStorage.setItem('role', 'OWNER')
    renderWithProviders()
    const user = userEvent.setup()

    const testBtn = await screen.findByRole('button', { name: /test suggestion/i })
    await act(async () => { await user.click(testBtn) })

    expect(inferMutate).toHaveBeenCalled()
    expect(await screen.findByText(/Test Suggestions/i)).toBeInTheDocument()
  })

  it('submits and calls save with current settings', async () => {
    localStorage.setItem('role', 'OWNER')
    renderWithProviders()
    const user = userEvent.setup()

    const saveBtn = await screen.findByRole('button', { name: /save settings/i })
    saveMutate.mockReset()
    saveMutate.mockImplementation(() => {})

    if (saveBtn) {
      await act(async () => { await user.click(saveBtn) })
    }

    expect(saveMutate).toHaveBeenCalled()
    // Validate essential fields are passed through
    const payload = saveMutate.mock.calls[0]?.[0]
    expect(payload).toMatchObject({
      enabled: true,
      provider_id: 'prov1',
    })
  })

  it('updates and saves advanced params (temperature, top_p, max_tokens)', async () => {
    localStorage.setItem('role', 'OWNER')
    renderWithProviders()
    const user = userEvent.setup()

    // Expand advanced
  const toggle = await screen.findByRole('button', { name: /show advanced/i })
  await act(async () => { await user.click(toggle) })

    // Simulate edits: temperature -> 0.9, top_p -> 0.95, max_tokens -> 512
    const tempInput = await screen.findByLabelText(/Temperature/i)
    const topPInput = await screen.findByLabelText(/Top P/i)
  const maxTokensInput = await screen.findByLabelText(/Max Tokens/i)
    
  // Reset mock before changes
  saveMutate.mockReset()
    
    // Revert to fireEvent.change for numeric inputs to avoid intermediate empty string parsing (NaN) and ensure mutation triggers.
    await act(async () => {
      fireEvent.change(tempInput, { target: { value: '0.9' } })
      fireEvent.change(topPInput, { target: { value: '0.95' } })
      fireEvent.change(maxTokensInput, { target: { value: '512' } })
    })

  // Should have been called at least once per field (allow extra internal debounced/derived calls)
  expect(saveMutate.mock.calls.length).toBeGreaterThanOrEqual(3)
  const lastPayload = saveMutate.mock.calls.slice(-1)[0]?.[0]
        expect(lastPayload.temperature).toBeCloseTo(0.9)
        expect(lastPayload.top_p).toBeCloseTo(0.95)
        expect(lastPayload.max_tokens).toBe(512)
  })

  it('toggles and saves guardrails switches (block_pii, allow_tool_use)', async () => {
    localStorage.setItem('role', 'OWNER')
    renderWithProviders()
    const user = userEvent.setup()

    // Expand advanced
  const toggle = await screen.findByRole('button', { name: /show advanced/i })
  await act(async () => { await user.click(toggle) })

    const piiSwitch = screen.getByLabelText(/Block PII in prompts/i)
    const toolUseSwitch = screen.getByLabelText(/Allow Tool Use/i)

    saveMutate.mockReset()

    // Toggle block_pii off and allow_tool_use on
    await act(async () => {
      await user.click(piiSwitch)
      await user.click(toolUseSwitch)
    })

    // Two mutations expected
    expect(saveMutate).toHaveBeenCalledTimes(2)
    const finalPayload = saveMutate.mock.calls[1]?.[0]
    expect(finalPayload.guardrails.block_pii).toBe(false)
    expect(finalPayload.guardrails.allow_tool_use).toBe(true)
  })
})
