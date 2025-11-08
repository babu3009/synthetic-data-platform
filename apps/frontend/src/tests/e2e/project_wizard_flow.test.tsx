import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import AppNavbar from '../../components/app_navbar'
import WizardPage from '../../pages/wizard_page'

// Mock projects hook to provide selectable projects
vi.mock('../../hooks/use_projects', () => {
  return {
    useProjects: () => ({
      data: [
        { id: 'projA', name: 'Project A', owner: 'owner@example.com' },
        { id: 'projB', name: 'Project B', owner: 'owner@example.com' },
      ],
      isLoading: false,
      isError: false,
    }),
  }
})

function setup(initialPath = '/') {
  const qc = new QueryClient()
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[initialPath]}>
        {/* Render navbar and wizard routes */}
        <AppNavbar />
        <WizardPage />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Project selection → wizard flow', () => {
  it('opens project selector then navigates to wizard with projectId and renders Entities tab', async () => {
    setup('/')

    // Click Data Wizard without project in route → should open modal
    const wizardLink = await screen.findByRole('link', { name: /Data Wizard/i })
    fireEvent.click(wizardLink)

    expect(await screen.findByText(/Select a project/i)).toBeInTheDocument()

    // Choose a project
    const select = screen.getByLabelText(/Project select/i) as HTMLSelectElement
    fireEvent.change(select, { target: { value: 'projB' } })

    const goBtn = screen.getByRole('button', { name: /Go/i })
    fireEvent.click(goBtn)

    // Wait for wizard page to show Entities with Project: projB
    await waitFor(() => {
      expect(screen.getByText(/Project:\s*projB/i)).toBeInTheDocument()
    })

    // Tabs should be present
    expect(screen.getByRole('tab', { name: /Entities/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /Diagram/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /Providers & PII/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /Rules/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /Outputs & Run/i })).toBeInTheDocument()
  })
})
