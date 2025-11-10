import React, { useCallback, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AuthContext } from './auth_context_public'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// (Internal mirror of AuthContextValue to help with provider implementation if future props added.)

interface LoginResponse { access_token?: string; token?: string; accessToken?: string; role?: string }

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const navigate = useNavigate()
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('authToken') || localStorage.getItem('access_token'))
  const [role, setRole] = useState<string | null>(() => localStorage.getItem('user_role'))
  const [loading, setLoading] = useState(false)

  const login = useCallback(async (email: string, password: string) => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      })
      if (!res.ok) {
        const text = await res.text()
        throw new Error(text || `Login failed (${res.status})`)
      }
      const data: LoginResponse = await res.json()
      // Accept common token shapes
      const accessToken = data?.access_token || data?.token || data?.accessToken
      if (!accessToken) throw new Error('No access token in response')
      localStorage.setItem('authToken', accessToken)
      localStorage.setItem('access_token', accessToken)
      setToken(accessToken)
      if (data.role) {
        localStorage.setItem('user_role', data.role)
        setRole(data.role)
      }
      navigate('/')
    } finally {
      setLoading(false)
    }
  }, [navigate])

  const logout = useCallback(() => {
    localStorage.removeItem('authToken')
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_role')
    setToken(null)
    setRole(null)
    navigate('/login')
  }, [navigate])

  const value = useMemo(() => ({ token, loading, login, logout, role }), [token, loading, login, logout, role])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// Hook moved to use_auth.ts to satisfy fast refresh constraint.
