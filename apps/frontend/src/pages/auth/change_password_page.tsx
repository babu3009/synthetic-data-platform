import React from 'react'
import { useNavigate } from 'react-router-dom'
import { requestChangePasswordOtp, changePassword } from '../../services/auth'
import { useAuth } from '../../state/use_auth'

const ChangePasswordPage: React.FC = () => {
  const navigate = useNavigate()
  const { token } = useAuth()
  const [mode, setMode] = React.useState<'current' | 'otp'>('current')
  const [currentPassword, setCurrentPassword] = React.useState('')
  const [otp, setOtp] = React.useState('')
  const [newPwd, setNewPwd] = React.useState('')
  const [loading, setLoading] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  const [info, setInfo] = React.useState<string | null>(null)

  async function handleRequestOtp() {
    setLoading(true); setError(null); setInfo(null)
    try {
      await requestChangePasswordOtp()
      setInfo('OTP sent if session valid. Switch to OTP mode below.')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to request OTP')
    } finally { setLoading(false) }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true); setError(null); setInfo(null)
    try {
      const body: { new_password: string; current_password?: string; otp?: string } = { new_password: newPwd }
      if (mode === 'current') body.current_password = currentPassword
      else body.otp = otp
      await changePassword(body)
      setInfo('Password changed.')
      navigate('/profile')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Change failed')
    } finally { setLoading(false) }
  }

  if (!token) return <div className="container py-4"><p>Login required.</p></div>

  return (
    <div className="container py-4 auth-narrow">
      <h2>Change Password</h2>
      <div className="btn-group mb-3" role="group" aria-label="Mode select">
        <button type="button" className={`btn btn-sm ${mode==='current' ? 'btn-primary' : 'btn-outline-primary'}`} onClick={() => setMode('current')}>Use Current Password</button>
        <button type="button" className={`btn btn-sm ${mode==='otp' ? 'btn-primary' : 'btn-outline-primary'}`} onClick={() => setMode('otp')}>Use OTP</button>
      </div>
      <form onSubmit={handleSubmit}>
        {mode === 'current' && (
          <div className="mb-3">
            <label htmlFor="cp-current" className="form-label">Current Password</label>
            <input id="cp-current" className="form-control" type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} required />
          </div>
        )}
        {mode === 'otp' && (
          <div className="mb-3">
            <label htmlFor="cp-otp" className="form-label">OTP</label>
            <input id="cp-otp" className="form-control" value={otp} onChange={(e) => setOtp(e.target.value)} required />
          </div>
        )}
        <div className="mb-3">
          <label htmlFor="cp-new" className="form-label">New Password</label>
          <input id="cp-new" className="form-control" type="password" value={newPwd} onChange={(e) => setNewPwd(e.target.value)} required />
        </div>
        {error && <div className="alert alert-danger">{error}</div>}
        {info && <div className="alert alert-info">{info}</div>}
        <button className="btn btn-primary" disabled={loading}>Change {loading && '...'}</button>
      </form>
      <div className="mt-3">
        <button className="btn btn-link" onClick={handleRequestOtp} disabled={loading || mode==='otp'}>Request OTP</button>
      </div>
    </div>
  )
}

export default ChangePasswordPage
