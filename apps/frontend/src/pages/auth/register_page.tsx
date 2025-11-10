import React from 'react'
import { useNavigate } from 'react-router-dom'
import { register } from '../../services/auth'

const RegisterPage: React.FC = () => {
  const navigate = useNavigate()
  const [email, setEmail] = React.useState('')
  const [password, setPassword] = React.useState('')
  const [organization, setOrganization] = React.useState('')
  const [loading, setLoading] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  const [message, setMessage] = React.useState<string | null>(null)

  function isAxiosLike(e: unknown): e is { response?: { data?: { detail?: string } } } {
    return typeof e === 'object' && e !== null && 'response' in (e as Record<string, unknown>)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setMessage(null)
    setLoading(true)
    try {
      const resp = await register({ email, password, organization })
      setMessage(resp.message)
      navigate('/verify-email?email=' + encodeURIComponent(email), { replace: true })
    } catch (err: unknown) {
      const msg = isAxiosLike(err) && err.response?.data?.detail
        ? String(err.response.data.detail)
        : (err instanceof Error ? err.message : 'Registration failed')
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container py-4 auth-narrow">
      <h2>Create Account</h2>
      <form onSubmit={handleSubmit} className="mt-3">
        <div className="mb-3">
          <label className="form-label" htmlFor="reg-email">Email</label>
          <input id="reg-email" className="form-control" type="email" value={email} placeholder="you@example.com" onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div className="mb-3">
          <label className="form-label" htmlFor="reg-org">Organization (optional)</label>
          <input id="reg-org" className="form-control" value={organization} placeholder="Org Inc." onChange={(e) => setOrganization(e.target.value)} />
        </div>
        <div className="mb-3">
          <label className="form-label" htmlFor="reg-password">Password</label>
          <input id="reg-password" className="form-control" type="password" value={password} placeholder="••••••••" onChange={(e) => setPassword(e.target.value)} required />
          <small className="text-muted">Min length 8; include upper/lower/number.</small>
        </div>
        {error && <div className="alert alert-danger" role="alert">{error}</div>}
        {message && <div className="alert alert-info" role="alert">{message}</div>}
        <button className="btn btn-primary" disabled={loading}>Register {loading && '...'}</button>
      </form>
      <hr />
      <p>Already have an account? <a href="/login">Login</a></p>
    </div>
  )
}

export default RegisterPage
