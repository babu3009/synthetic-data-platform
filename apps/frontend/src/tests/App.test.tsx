import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import HomePage from '../pages/home_page'
import WizardPage from '../pages/wizard_page'

function TestApp() {
  return (
    <main className="container-fluid px-0">
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/wizard" element={<WizardPage />} />
      </Routes>
    </main>
  )
}

describe('App', () => {
  it('renders without crashing', async () => {
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        {/* Use default behavior to avoid startTransition warnings in tests */}
        <BrowserRouter>
          <TestApp />
        </BrowserRouter>
      </QueryClientProvider>
    )
    expect(await screen.findByRole('heading', { name: /Generate High-Quality Synthetic Data/i })).toBeInTheDocument()
  })
})