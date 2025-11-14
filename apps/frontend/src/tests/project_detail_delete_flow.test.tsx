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
    deleteProject: vi.fn(),
    updateProject: vi.fn(),
    registerRunStatusWebhook: vi.fn(),
  }
})

describe('ProjectDetailPage - deletion flow', () => {
  const user = userEvent.setup()
  const routes = (
    <Routes>
      <Route path="/projects" element={<div>Projects List</div>} />
      <Route path="/projects/:id" element={<ProjectDetailPage />} />
    </Routes>
  )

  beforeEach(() => {
    vi.clearAllMocks()
  ;(svc.getProject as unknown as Mock).mockResolvedValue({
      id: '123',
      name: 'Alpha',
      owner: 'alice',
      webhook_run_status_url: null,
    })
  ;(svc.deleteProject as unknown as Mock).mockResolvedValue(undefined)
    // Prevent real confirm dialogs
    vi.spyOn(window, 'confirm').mockReturnValue(true)
  })

  it('confirms and deletes, then navigates back to projects list', async () => {
    render(
      <TestProviders initialEntries={["/projects/123"]} routes={routes}>
        {/* Child required by wrapper; routes prop overrides rendering */}
        <div />
      </TestProviders>
    )

    // Wait for project to load
    expect(await screen.findByRole('heading', { name: 'Project' })).toBeInTheDocument()

    // Click Delete
    await user.click(screen.getByRole('button', { name: 'Delete' }))

    // Ensures confirm was shown
    expect(window.confirm).toHaveBeenCalledWith('Delete this project? This cannot be undone.')

    // Wait until service called and navigation occurs
    await waitFor(() => expect(svc.deleteProject).toHaveBeenCalledWith('123'))
    // Navigated to /projects route
    expect(await screen.findByText('Projects List')).toBeInTheDocument()
  })
})
