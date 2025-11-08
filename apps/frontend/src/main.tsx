import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import HomePage from './pages/home_page'
import WizardPage from './pages/wizard_page'
import RequestDetailPage from './pages/request_detail_page'
import LlmSettingsPage from './pages/llm_settings_page'
import LlmProvidersPage from './pages/admin/llm_providers_page'
import AppNavbar from './components/app_navbar'
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

// Only mount the app if a real root element exists (prevents side-effects during Vitest unit tests
// that import symbols from this module, e.g. AppNavbar). This avoids ReactDOM attempting to mount
// into a null container which was causing test failures.
const rootEl = document.getElementById('root')
if (rootEl) {
  ReactDOM.createRoot(rootEl).render(
    <React.StrictMode>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AppNavbar />
          <main className="container-fluid px-0">
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/wizard" element={<WizardPage />} />
              <Route path="/projects/:projectId/wizard" element={<WizardPage />} />
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
}

// AppNavbar moved to ./components/app_navbar to allow tests to import it without side-effects.