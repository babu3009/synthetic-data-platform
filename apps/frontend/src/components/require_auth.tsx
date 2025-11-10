import React from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/state/use_auth'

const RequireAuth: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { token } = useAuth()
  const location = useLocation()
  if (!token) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }
  return <>{children}</>
}

export default RequireAuth
