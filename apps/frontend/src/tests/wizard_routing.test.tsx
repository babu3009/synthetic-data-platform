import { describe, it, expect } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { render, screen, waitFor } from '@testing-library/react'
import WizardPage from '../pages/wizard_page'

// This test verifies that navigating to /projects/:projectId/wizard
// sets the wizard project state and surfaces in the UI (Entities page shows Project: <id>)
describe('Wizard routing', () => {
  it('sets projectId from route param', async () => {
    render(
      <MemoryRouter initialEntries={["/projects/test-proj-123/wizard"]}>
        <Routes>
          <Route path="/projects/:projectId/wizard" element={<WizardPage />} />
        </Routes>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/Project:\s*test-proj-123/i)).toBeInTheDocument()
    })
  })

  it('redirects legacy /wizard?projectId=... to /projects/:projectId/wizard', async () => {
    render(
      <MemoryRouter initialEntries={["/wizard?projectId=legacy-001"]}>
        <Routes>
          <Route path="/wizard" element={<WizardPage />} />
          <Route path="/projects/:projectId/wizard" element={<WizardPage />} />
        </Routes>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/Project:\s*legacy-001/i)).toBeInTheDocument()
    })
  })
})
