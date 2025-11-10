import { createContext } from 'react'

export interface AuthContextValue {
  token: string | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  role: string | null
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined)
