import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ProjectDetailPage from '../pages/projects/project_detail_page'
import { ToastProvider } from '../state/toast_context'

vi.mock('../services/projects', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../services/projects')>()
  return {
    ...actual,
    getProject: vi.fn().mockResolvedValue({ id: 'p1', name: 'Alpha', owner: 'owner@a.com', webhook_run_status_url: null }),
    updateProject: vi.fn().mockResolvedValue({ id: 'p1', name: 'Alpha-2', owner: 'new@b.com', webhook_run_status_url: null }),
  }
})

const { updateProject } = await import('../services/projects')

function setup() {
  const qc = new QueryClient()
  return render(
    <QueryClientProvider client={qc}>
      <ToastProvider>
        <MemoryRouter initialEntries={["/projects/p1"]}>
          <Routes>
            <Route path="/projects/:id" element={<ProjectDetailPage />} />
          </Routes>
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>
  )
}

describe('ProjectDetailPage owner reassignment confirmation', () => {
  it('asks for confirmation when owner changes and submits; proceeds on confirm=true', async () => {
    setup()
    const user = userEvent.setup()
    expect(await screen.findByLabelText(/Owner/i)).toBeInTheDocument()

    const ownerInput = screen.getByLabelText(/Owner/i) as HTMLInputElement
    await user.clear(ownerInput)
    await user.type(ownerInput, 'new@b.com')

    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)

    const saveBtn = screen.getByRole('button', { name: /Save/i })
    await user.click(saveBtn)

    expect(confirmSpy).toHaveBeenCalled()
    expect(updateProject).toHaveBeenCalledWith('p1', expect.objectContaining({ owner: 'new@b.com' }))
  })

  it('blocks submit when confirmation is cancelled', async () => {
    setup()
    const user = userEvent.setup()

    const ownerInput = await screen.findByLabelText(/Owner/i)
    await user.clear(ownerInput)
    await user.type(ownerInput, 'another@c.com')

    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false)

    const saveBtn = screen.getByRole('button', { name: /Save/i })
    await user.click(saveBtn)

    expect(confirmSpy).toHaveBeenCalled()
    expect(updateProject).not.toHaveBeenCalledWith('p1', expect.objectContaining({ owner: 'another@c.com' }))
  })
})
