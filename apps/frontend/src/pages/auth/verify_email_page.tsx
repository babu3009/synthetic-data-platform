import React from 'react'
import { useToasts } from '../../hooks/use_toasts'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { verifyEmail, resendEmailOtp } from '../../services/auth'

const VerifyEmailPage: React.FC = () => {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const emailParam = params.get('email') || ''
  const [email, setEmail] = React.useState(emailParam)
  const [otp, setOtp] = React.useState('')
  const [loading, setLoading] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  const [info, setInfo] = React.useState<string | null>(null)
  const [resent, setResent] = React.useState(false)
  const { push } = useToasts()

  async function handleVerify(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setInfo(null)
    try {
      const resp = await verifyEmail({ email, otp })
      if (/APPROVED|PENDING_ADMIN_APPROVAL/.test(resp.status)) {
        push('success', 'Email verified')
        navigate('/login?email=' + encodeURIComponent(email), { replace: true })
      } else {
        setInfo(resp.message || 'Status: ' + resp.status)
      }
    } catch (err: unknown) {
      const msg = (err instanceof Error ? err.message : 'Verification failed')
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  async function handleResend() {
    setError(null)
    setInfo(null)
    setLoading(true)
    try {
  await resendEmailOtp({ email })
  setResent(true)
  push('info', 'Verification code resent (if email exists).')
    } catch (err: unknown) {
      const msg = (err instanceof Error ? err.message : 'Resend failed')
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container py-4 auth-narrow">
      <h2>Verify Email</h2>
      <form onSubmit={handleVerify} className="mt-3">
        <div className="mb-3">
          <label htmlFor="verify-email" className="form-label">Email</label>
          <input id="verify-email" className="form-control" type="email" value={email} placeholder="you@example.com" onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div className="mb-3">
          <label htmlFor="verify-otp" className="form-label">Verification Code</label>
          <input id="verify-otp" className="form-control" value={otp} placeholder="123456" onChange={(e) => setOtp(e.target.value)} required />
        </div>
        {error && <div className="alert alert-danger">{error}</div>}
        {info && <div className="alert alert-info">{info}</div>}
        <button className="btn btn-primary" disabled={loading}>Verify {loading && '...'}</button>
      </form>
      <div className="mt-3">
        <button className="btn btn-link" onClick={handleResend} disabled={loading}>{loading ? 'Resending...' : 'Resend Code'}</button>
        {loading && (
          <div className="mt-3" aria-hidden="true">
            <div className="skeleton skeleton-line40" />
            <div className="skeleton skeleton-line30 mt-2" />
          </div>
        )}
        {resent && !loading && <small className="text-muted ms-2">Resent</small>}
      </div>
    </div>
  )
}

export default VerifyEmailPage
