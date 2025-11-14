import React, { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { completeOidcCallback } from '../../services/auth'
import { useToasts } from '../../hooks/use_toasts'

// Minimal OIDC callback handler. In a full implementation we'd exchange the code for tokens server-side.
// For current scaffolding, backend may return verified claims when id_token is present.
const OidcCallbackPage: React.FC = () => {
  const location = useLocation()
  const navigate = useNavigate()
  const { push } = useToasts()
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [claims, setClaims] = useState<{ sub?: string; email?: string; name?: string } | null>(null)

  useEffect(() => {
    async function run() {
      setLoading(true)
      try {
        const result = await completeOidcCallback(location.search)
        if (result.verified && result.claims) {
          setClaims(result.claims)
          // Store a temporary testing token so backend dev principal accepts it
          if (result.claims.sub) {
            localStorage.setItem('access_token', `testing:${result.claims.sub}`)
          }
          // Normally we'd have an access token here; for scaffolding, show success and redirect.
          push('success', 'SSO login verified')
          setTimeout(() => navigate('/'), 1200)
        } else {
          // Not verified; show raw response for troubleshooting
          setError('OIDC callback did not include a verified id_token')
        }
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : 'OIDC callback failed'
        setError(msg)
      } finally {
        setLoading(false)
      }
    }
    run()
  }, [location.search, navigate, push])

  return (
    <div className="container py-4">
      <h2>Single Sign-On</h2>
      {loading && <p>Processing sign-in...</p>}
      {!loading && claims && (
        <div className="alert alert-success" role="alert">
          <strong>Welcome{claims.name ? `, ${claims.name}` : ''}!</strong> Redirecting...
        </div>
      )}
      {!loading && error && (
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      )}
      {!loading && !claims && !error && (
        <div className="alert alert-warning" role="alert">
          Unexpected callback state.
        </div>
      )}
    </div>
  )
}

export default OidcCallbackPage
