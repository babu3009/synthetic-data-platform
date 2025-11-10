import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { act } from 'react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import AppNavbar from '../../components/app_navbar'
import WizardPage from '../../pages/wizard_page'
import { AuthContext, type AuthContextValue } from '../../state/auth_context_public'
import { ToastProvider } from '../../state/toast_context'

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

function RouteShell() {
  // Helper component to expose current path for assertions if needed
  const loc = useLocation()
  return (
    <>
      <AppNavbar />
      <WizardPage />
      <div data-testid="current-path" hidden>{loc.pathname}</div>
    </>
  )
}

function setup(initialPath = '/') {
  const qc = new QueryClient()
  const authValue: AuthContextValue = {
    token: 't',
    loading: false,
    role: 'OWNER',
    login: async () => {},
    logout: () => {},
  }
  return render(
    <QueryClientProvider client={qc}>
      <AuthContext.Provider value={authValue}>
        <ToastProvider>
          {/* Remove future flags which invoke startTransition leading to act warnings */}
          <MemoryRouter initialEntries={[initialPath]}>
            <Routes>
              <Route path="/" element={<RouteShell />} />
              <Route path="/wizard" element={<RouteShell />} />
              <Route path="/projects/:projectId/wizard" element={<RouteShell />} />
              <Route path="/projects/:projectId/llm-settings" element={<RouteShell />} />
              <Route path="/admin/:projectId/llm-providers" element={<RouteShell />} />
            </Routes>
          </MemoryRouter>
        </ToastProvider>
      </AuthContext.Provider>
    </QueryClientProvider>
  )
}

describe('Project selection → wizard flow', () => {
  it('opens project selector then navigates to wizard with projectId and renders Entities tab', async () => {
    setup('/')
    const user = userEvent.setup()

    // Click Data Wizard without project in route → should open modal
    const wizardLink = await screen.findByRole('link', { name: /Data Wizard/i })
  await act(async () => { await user.click(wizardLink) })

    expect(await screen.findByText(/Select a project/i)).toBeInTheDocument()

    // Choose a project
  const select = screen.getByLabelText(/Project select/i) as HTMLSelectElement
  await act(async () => { await user.selectOptions(select, 'projB') })

  const goBtn = screen.getByRole('button', { name: /^Go$/i })
  await act(async () => { await user.click(goBtn) })

    // Wait for wizard page to set projectId and surface in Entities page
    await waitFor(() => {
      const projectLabel = screen.getByText(/Project:\s*projB/i)
      expect(projectLabel).toBeInTheDocument()
      expect(screen.getByTestId('current-path').textContent).toMatch(/\/projects\/projB\/wizard$/)
    })

    // Tabs should be present
    expect(screen.getByRole('tab', { name: /Entities/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /Diagram/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /Providers & PII/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /Rules/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /Outputs & Run/i })).toBeInTheDocument()
  })
})
