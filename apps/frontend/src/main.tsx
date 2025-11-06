import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import { Navbar as BsNavbar, Nav, Container } from 'react-bootstrap'
import HomePage from './pages/home_page'
import WizardPage from './pages/wizard_page'
import RequestDetailPage from './pages/request_detail_page'
import LlmSettingsPage from './pages/llm_settings_page'
import LlmProvidersPage from './pages/admin/llm_providers_page'
import 'bootstrap/dist/css/bootstrap.min.css'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppNavbar />
        <main className="container-fluid px-0">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/wizard" element={<WizardPage />} />
            <Route path="/projects/:projectId/requests/:requestId" element={<RequestDetailPage />} />
            <Route path="/projects/:projectId/llm-settings" element={<LlmSettingsPage />} />
            <Route path="/admin/:projectId/llm-providers" element={<LlmProvidersPage />} />
            <Route path="/admin/llm-providers" element={<LlmProvidersPage />} />
          </Routes>
        </main>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)

export function AppNavbar() {
  const location = useLocation()
  return (
    <BsNavbar bg="dark" variant="dark" expand="lg" sticky="top">
      <Container>
        <BsNavbar.Brand as={Link} to="/">
          <strong>Synthetic Data Platform</strong>
        </BsNavbar.Brand>
        <BsNavbar.Toggle aria-controls="basic-navbar-nav" />
        <BsNavbar.Collapse id="basic-navbar-nav">
          <Nav className="me-auto">
            <Nav.Link as={Link} to="/" active={location.pathname === '/'}>
              Home
            </Nav.Link>
            <Nav.Link as={Link} to="/wizard" active={location.pathname === '/wizard'}>
              Data Wizard
            </Nav.Link>
            <Nav.Link as={Link} to="/datasets" active={location.pathname === '/datasets'}>
              Datasets
            </Nav.Link>
            <Nav.Link as={Link} to="/analytics" active={location.pathname === '/analytics'}>
              Analytics
            </Nav.Link>
          </Nav>
          <Nav>
            <Nav.Link as={Link} to="/profile" active={location.pathname === '/profile'}>
              Profile
            </Nav.Link>
          </Nav>
        </BsNavbar.Collapse>
      </Container>
    </BsNavbar>
  )
}