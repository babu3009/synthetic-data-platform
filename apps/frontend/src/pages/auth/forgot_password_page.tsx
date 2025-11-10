import React from 'react'
import { useNavigate } from 'react-router-dom'
import { forgotPassword } from '../../services/auth'

const ForgotPasswordPage: React.FC = () => {
  const navigate = useNavigate()
  const [email, setEmail] = React.useState('')
  const [loading, setLoading] = React.useState(false)
  const [message, setMessage] = React.useState<string | null>(null)
  const [error, setError] = React.useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setMessage(null)
    try {
      await forgotPassword({ email })
      setMessage('If the email exists, an OTP has been sent.')
      navigate('/reset-password?email=' + encodeURIComponent(email))
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Request failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container py-4 auth-narrow">
      <h2>Forgot Password</h2>
      <form onSubmit={handleSubmit} className="mt-3">
        <div className="mb-3">
          <label className="form-label" htmlFor="fp-email">Email</label>
          <input id="fp-email" className="form-control" type="email" value={email} placeholder="you@example.com" onChange={(e) => setEmail(e.target.value)} required />
        </div>
        {error && <div className="alert alert-danger">{error}</div>}
        {message && <div className="alert alert-info">{message}</div>}
        <button className="btn btn-primary" disabled={loading}>Continue {loading && '...'}</button>
      </form>
    </div>
  )
}

export default ForgotPasswordPage
