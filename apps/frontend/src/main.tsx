import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import HomePage from './pages/home_page'
import LoginPage from './pages/auth/login_page'
import OidcCallbackPage from './pages/auth/oidc_callback_page'
import RegisterPage from './pages/auth/register_page'
import VerifyEmailPage from './pages/auth/verify_email_page'
import ForgotPasswordPage from './pages/auth/forgot_password_page'
import ResetPasswordPage from './pages/auth/reset_password_page'
import ChangePasswordPage from './pages/auth/change_password_page'
import ProfilePage from './pages/profile_page'
import WizardPage from './pages/wizard_page'
import RequestDetailPage from './pages/request_detail_page'
import LlmSettingsPage from './pages/llm_settings_page'
import LlmProvidersPage from './pages/admin/llm_providers_page'
import ProjectsListPage from './pages/projects/projects_list_page'
import ProjectCreatePage from './pages/projects/project_create_page'
import ProjectDetailPage from './pages/projects/project_detail_page'
import SourcesListPage from './pages/projects/sources_list_page'
import SourceSchemaPage from './pages/projects/source_schema_page'
import SourceDagPage from './pages/projects/source_dag_page'
import ProjectApiKeysPage from './pages/projects/project_api_keys_page'
import RequestsListPage from './pages/projects/requests_list_page'
import ValidationRulesPage from './pages/projects/validation_rules_page'
import FlatPreviewPage from './pages/flat_preview_page'
import AdminUsersPage from './pages/admin/admin_users_page'
import AppNavbar from './components/app_navbar'
import RequireAuth from './components/require_auth'
import 'bootstrap/dist/css/bootstrap.min.css'
import 'bootstrap-icons/font/bootstrap-icons.css'
import { AuthProvider } from './state/auth_context'
import './index.css'
import { ToastProvider } from './state/toast_context'
import ErrorBoundary from './components/error_boundary'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 0, // Always treat data as stale - no caching
      gcTime: 0, // Garbage collect immediately (formerly cacheTime)
      refetchOnMount: true, // Always refetch on component mount
      refetchOnWindowFocus: true, // Refetch when window regains focus
      refetchOnReconnect: true, // Refetch on network reconnect
      retry: false, // Fail immediately when backend unreachable
      networkMode: 'always', // Always attempt the request
    },
    mutations: {
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
        {/* Opt-in to React Router v7 future flags for smoother upgrade path */}
        <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <ToastProvider>
            <AuthProvider>
              <ErrorBoundary>
                <AppNavbar />
                <main className="container-fluid px-0">
                  <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route path="/oidc/callback" element={<OidcCallbackPage />} />
                <Route path="/register" element={<RegisterPage />} />
                <Route path="/verify-email" element={<VerifyEmailPage />} />
                <Route path="/forgot-password" element={<ForgotPasswordPage />} />
                <Route path="/reset-password" element={<ResetPasswordPage />} />
                <Route path="/change-password" element={<RequireAuth><ChangePasswordPage /></RequireAuth>} />
                <Route path="/profile" element={<RequireAuth><ProfilePage /></RequireAuth>} />
                <Route path="/" element={<RequireAuth><HomePage /></RequireAuth>} />
                <Route path="/projects" element={<RequireAuth><ProjectsListPage /></RequireAuth>} />
                <Route path="/projects/new" element={<RequireAuth><ProjectCreatePage /></RequireAuth>} />
                <Route path="/projects/:id" element={<RequireAuth><ProjectDetailPage /></RequireAuth>} />
                <Route path="/projects/:projectId/sources" element={<RequireAuth><SourcesListPage /></RequireAuth>} />
                <Route path="/projects/:projectId/api-keys" element={<RequireAuth><ProjectApiKeysPage /></RequireAuth>} />
                <Route path="/projects/:projectId/requests" element={<RequireAuth><RequestsListPage /></RequireAuth>} />
                <Route path="/projects/:projectId/validation" element={<RequireAuth><ValidationRulesPage /></RequireAuth>} />
                <Route path="/flat/preview" element={<RequireAuth><FlatPreviewPage /></RequireAuth>} />
                <Route path="/projects/:projectId/sources/:sourceId/schema" element={<RequireAuth><SourceSchemaPage /></RequireAuth>} />
                <Route path="/projects/:projectId/sources/:sourceId/dag" element={<RequireAuth><SourceDagPage /></RequireAuth>} />
                <Route path="/wizard" element={<RequireAuth><WizardPage /></RequireAuth>} />
                <Route path="/projects/:projectId/wizard" element={<RequireAuth><WizardPage /></RequireAuth>} />
                <Route path="/projects/:projectId/requests/:requestId" element={<RequireAuth><RequestDetailPage /></RequireAuth>} />
                <Route path="/projects/:projectId/llm-settings" element={<RequireAuth><LlmSettingsPage /></RequireAuth>} />
                <Route path="/admin/:projectId/llm-providers" element={<RequireAuth><LlmProvidersPage /></RequireAuth>} />
                <Route path="/admin/llm-providers" element={<RequireAuth><LlmProvidersPage /></RequireAuth>} />
                <Route path="/admin/users" element={<RequireAuth><AdminUsersPage /></RequireAuth>} />
                  </Routes>
                </main>
              </ErrorBoundary>
            </AuthProvider>
          </ToastProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </React.StrictMode>,
  )
}

// AppNavbar moved to ./components/app_navbar to allow tests to import it without side-effects.