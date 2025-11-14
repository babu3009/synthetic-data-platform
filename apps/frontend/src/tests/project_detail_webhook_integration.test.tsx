import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ProjectDetailPage from '../pages/projects/project_detail_page'
import * as svc from '../services/projects'
import { TestProviders } from './utils/TestProviders'
import { Routes, Route } from 'react-router-dom'
import { describe, it, beforeEach, expect, vi } from 'vitest'
import type { Mock } from 'vitest'

vi.mock('../services/projects', async () => {
  const mod = await vi.importActual<typeof import('../services/projects')>('../services/projects')
  return {
    ...mod,
    getProject: vi.fn(),
    registerRunStatusWebhook: vi.fn(),
    updateProject: vi.fn(),
    deleteProject: vi.fn(),
  }
})

describe('ProjectDetailPage - webhook registration integration', () => {
  const user = userEvent.setup()
  const routes = (
    <Routes>
      <Route path="/projects/:id" element={<ProjectDetailPage />} />
    </Routes>
  )

  beforeEach(() => {
    vi.clearAllMocks()
    ;(svc.getProject as unknown as Mock).mockResolvedValue({
      id: '123',
      name: 'Alpha',
      owner: 'alice',
      webhook_run_status_url: '',
    })
    ;(svc.registerRunStatusWebhook as unknown as Mock).mockResolvedValue({ ok: true })
  })

  it('enables Register Webhook when URL present and calls service with id and URL', async () => {
    render(
      <TestProviders initialEntries={["/projects/123"]} routes={routes}>
        <div />
      </TestProviders>
    )

    // Wait for load
    expect(await screen.findByRole('heading', { name: 'Project' })).toBeInTheDocument()

    const urlInput = screen.getByLabelText('Run Status Webhook URL') as HTMLInputElement
    const button = screen.getByRole('button', { name: 'Register Webhook' })

    // Initially disabled due to empty URL
    expect(button).toBeDisabled()

    // Enter a URL
    await user.type(urlInput, 'https://example.com/webhook')
    expect(urlInput.value).toBe('https://example.com/webhook')

    // Button should enable
    expect(button).toBeEnabled()

    await user.click(button)

    await waitFor(() =>
      expect(svc.registerRunStatusWebhook).toHaveBeenCalledWith('123', 'https://example.com/webhook')
    )
  })
})
