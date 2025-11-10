import { useContext } from 'react'
import { AuthContext } from './auth_context_public'
import type { AuthContextValue } from './auth_context_public'

export const useAuth = (): AuthContextValue => {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
