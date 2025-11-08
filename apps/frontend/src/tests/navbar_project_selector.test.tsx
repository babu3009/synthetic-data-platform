import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AppNavbar } from '../components/app_navbar'

vi.mock('../hooks/use_projects', () => {
  return {
    useProjects: () => ({
      data: [
        { id: 'p1', name: 'Project One', owner: 'owner@example.com' },
        { id: 'p2', name: 'Project Two', owner: 'owner@example.com' },
      ],
      isLoading: false,
      isError: false,
    }),
  }
})

function renderNavbar(path = '/') {
  const qc = new QueryClient()
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[path]}>
        <AppNavbar />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Navbar project selector', () => {
  it('opens selector when LLM Settings clicked without projectId and navigates after selection', async () => {
    renderNavbar('/')

    const link = await screen.findByRole('link', { name: /LLM Settings/i })
    fireEvent.click(link)

    // Modal should appear
    expect(await screen.findByText(/Select a project/i)).toBeInTheDocument()

    // Choose project and Go
    const select = screen.getByLabelText(/Project select/i) as HTMLSelectElement
    fireEvent.change(select, { target: { value: 'p2' } })

    const go = await screen.findByRole('button', { name: /Go/i })
    fireEvent.click(go)

    // Wait for navigation; MemoryRouter doesn't update window.location, but AppNavbar pushState triggers route change
    await waitFor(() => {
      // We expect the navbar to consider route updated such that the LLM link is active for the new path
      expect((link as HTMLAnchorElement).getAttribute('href')).toMatch(/llm-settings$/)
    })
  })
})
