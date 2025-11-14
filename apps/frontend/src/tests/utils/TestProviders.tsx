/* eslint-disable react-refresh/only-export-components */
import React from 'react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthContext, type AuthContextValue } from '../../state/auth_context_public'
import { ToastProvider } from '../../state/toast_context'

export interface TestProvidersProps {
  children: React.ReactNode
  initialEntries?: string[]
  auth?: Partial<AuthContextValue>
  routes?: React.ReactElement // Optional custom <Routes> element; if omitted, children rendered directly
}

export const TestProviders: React.FC<TestProvidersProps> = ({ children, initialEntries = ['/'], auth, routes }) => {
  const qc = React.useMemo(() => new QueryClient(), [])
  const defaultAuth: AuthContextValue = {
    token: 'test-token',
    loading: false,
    role: 'OWNER',
    login: async () => {},
    logout: () => {},
    ...auth,
  }
  return (
    <QueryClientProvider client={qc}>
      <AuthContext.Provider value={defaultAuth}>
        <ToastProvider>
          <MemoryRouter initialEntries={initialEntries}>
            {routes ? routes : children}
          </MemoryRouter>
        </ToastProvider>
      </AuthContext.Provider>
    </QueryClientProvider>
  )
}

// Helper for common pattern where you need to supply a route definition with a param
export function withRoute(path: string, element: React.ReactElement) {
  return (
    <Routes>
      <Route path={path} element={element} />
    </Routes>
  )
}
