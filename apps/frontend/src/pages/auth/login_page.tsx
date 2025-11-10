import React, { useState, useEffect } from 'react'
import { useAuth } from '../../state/use_auth'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { useToasts } from '../../hooks/use_toasts'

const LoginPage: React.FC = () => {
  const { login, loading } = useAuth()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { push } = useToasts()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const prefill = searchParams.get('email')
    if (prefill) setEmail(prefill)
  }, [searchParams])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      await login(email, password)
      push('success', 'Logged in successfully')
      const next = searchParams.get('next')
      if (next) navigate(next)
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Login failed'
      setError(msg)
    }
  }

  return (
  <div className="container login-container">
      <h2 className="mt-4 mb-3">Login</h2>
      <form onSubmit={handleSubmit} noValidate>
        <div className="mb-3">
          <label htmlFor="email" className="form-label">Email</label>
          <input
            id="email"
            type="email"
            className="form-control"
            value={email}
            onChange={e => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
        </div>
        <div className="mb-3">
          <label htmlFor="password" className="form-label">Password</label>
          <input
            id="password"
            type="password"
            className="form-control"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
        </div>
        {error && <div className="alert alert-danger py-2" role="alert">{error}</div>}
        <button type="submit" className="btn btn-primary" disabled={loading}> {loading ? 'Logging in...' : 'Login'} </button>
        <div className="mt-3">
          <a href="/forgot-password">Forgot password?</a>
        </div>
      </form>
    </div>
  )
}

export default LoginPage
