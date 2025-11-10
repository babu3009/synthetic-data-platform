import React from 'react'
import { getProfile, uploadAvatar, type UserProfile } from '../services/auth'

const ProfilePage: React.FC = () => {
  const [profile, setProfile] = React.useState<UserProfile | null>(null)
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)
  const [avatarUploading, setAvatarUploading] = React.useState(false)

  React.useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        const p = await getProfile()
        if (mounted) setProfile(p)
      } catch (err: unknown) {
        if (mounted) setError(err instanceof Error ? err.message : 'Failed to load profile')
      } finally {
        if (mounted) setLoading(false)
      }
    })()
    return () => { mounted = false }
  }, [])

  async function handleAvatarChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setAvatarUploading(true)
    setError(null)
      try {
        await uploadAvatar(file)
        const p = await getProfile()
        setProfile(p)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setAvatarUploading(false)
    }
  }

    if (loading) return (
      <div className="container py-4 auth-narrow">
        <div className="card p-3">
          <div className="d-flex align-items-center mb-3">
            <div className="avatar-placeholder skeleton" />
            <div className="ms-3 w-100">
              <div className="skeleton skeleton-line40" />
              <div className="skeleton skeleton-line30 mt-2" />
              <div className="skeleton skeleton-line50 mt-2" />
            </div>
          </div>
          <div className="skeleton skeleton-block-full" />
        </div>
      </div>
    )
  if (error) return <div className="container py-4"><div className="alert alert-danger">{error}</div></div>

  return (
    <div className="container py-4 auth-narrow">
      <h2>Profile</h2>
      {profile && (
        <div className="card mt-3">
          <div className="card-body">
            <div className="d-flex align-items-center mb-3">
              <div className="avatar-placeholder">
                {/* Placeholder; backend can return avatar_url */}
              </div>
              <div className="ms-3">
                <div><strong>{profile.email}</strong></div>
                <div className="text-muted">Role: {profile.role || 'user'}</div>
                {profile.organization && <div className="text-muted">Org: {profile.organization}</div>}
              </div>
            </div>
            <div className="mb-3">
              <label htmlFor="avatar" className="form-label">Avatar</label>
              <input id="avatar" className="form-control" type="file" accept="image/*" onChange={handleAvatarChange} disabled={avatarUploading} />
            </div>
            <a className="btn btn-outline-secondary" href="/change-password">Change Password</a>
          </div>
        </div>
      )}
    </div>
  )
}

export default ProfilePage
