import React from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { resetPassword } from '../../services/auth'

const ResetPasswordPage: React.FC = () => {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const emailParam = params.get('email') || ''
  const [email, setEmail] = React.useState(emailParam)
  const [otp, setOtp] = React.useState('')
  const [newPwd, setNewPwd] = React.useState('')
  const [loading, setLoading] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  const [info, setInfo] = React.useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setInfo(null)
    try {
      await resetPassword({ email, otp, new_password: newPwd })
      setInfo('Password reset. You may now login.')
      navigate('/login?email=' + encodeURIComponent(email))
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Reset failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container py-4 auth-narrow">
      <h2>Reset Password</h2>
      <form onSubmit={handleSubmit} className="mt-3">
        <div className="mb-3">
          <label htmlFor="rp-email" className="form-label">Email</label>
          <input id="rp-email" className="form-control" type="email" value={email} placeholder="you@example.com" onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div className="mb-3">
          <label htmlFor="rp-otp" className="form-label">OTP</label>
          <input id="rp-otp" className="form-control" value={otp} placeholder="123456" onChange={(e) => setOtp(e.target.value)} required />
        </div>
        <div className="mb-3">
          <label htmlFor="rp-newpwd" className="form-label">New Password</label>
          <input id="rp-newpwd" className="form-control" type="password" value={newPwd} placeholder="••••••••" onChange={(e) => setNewPwd(e.target.value)} required />
        </div>
        {error && <div className="alert alert-danger">{error}</div>}
        {info && <div className="alert alert-info">{info}</div>}
        <button className="btn btn-primary" disabled={loading}>Reset {loading && '...'}</button>
      </form>
    </div>
  )
}

export default ResetPasswordPage
