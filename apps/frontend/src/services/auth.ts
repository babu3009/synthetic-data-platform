import api from './api'

export interface RegisterInput {
  email: string
  password: string
  organization?: string
}
export interface RegisterResponse { status: string; message: string }

export async function register(input: RegisterInput): Promise<RegisterResponse> {
  const res = await api.post('/api/v1/auth/register', input)
  return res.data as RegisterResponse
}

export interface VerifyEmailInput { email: string; otp: string }
export interface VerifyEmailResponse { status: string; message?: string }
export async function verifyEmail(input: VerifyEmailInput): Promise<VerifyEmailResponse> {
  const res = await api.post('/api/v1/auth/verify-email', input)
  return res.data as VerifyEmailResponse
}

export interface ResendEmailOtpInput { email: string }
export async function resendEmailOtp(input: ResendEmailOtpInput): Promise<{ status: string }> {
  const res = await api.post('/api/v1/auth/resend-email-otp', input)
  return res.data
}

export interface ForgotPasswordInput { email: string }
export async function forgotPassword(input: ForgotPasswordInput): Promise<{ status: string }> {
  const res = await api.post('/api/v1/auth/forgot-password', input)
  return res.data
}

export interface ResetPasswordInput { email: string; otp: string; new_password: string }
export async function resetPassword(input: ResetPasswordInput): Promise<{ status: string }> {
  const res = await api.post('/api/v1/auth/reset-password', input)
  return res.data
}

export async function requestChangePasswordOtp(): Promise<{ status: string }> {
  const res = await api.post('/api/v1/auth/request-change-password-otp')
  return res.data
}

export interface ChangePasswordInput {
  current_password?: string
  otp?: string
  new_password: string
}
export async function changePassword(input: ChangePasswordInput): Promise<{ status: string }> {
  const res = await api.post('/api/v1/auth/change-password', input)
  return res.data
}

export interface UserProfile { id: string; email: string; role?: string; organization?: string; avatar_url?: string }
export async function getProfile(): Promise<UserProfile> {
  const res = await api.get('/api/v1/users/me')
  return res.data as UserProfile
}

export async function uploadAvatar(file: File): Promise<{ ok: boolean }> {
  const fd = new FormData()
  fd.append('file', file)
  const res = await api.patch('/api/v1/users/me/avatar', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
  return res.data
}

// ---- OIDC SSO Helpers ----
export interface OidcAuthorizeResponse {
  enabled: boolean
  authorize_url?: string
  reason?: string
}

export async function fetchOidcAuthorize(): Promise<OidcAuthorizeResponse> {
  const res = await api.get('/api/v1/auth/login')
  return res.data as OidcAuthorizeResponse
}

export interface OidcCallbackResult {
  verified?: boolean
  claims?: { sub?: string; email?: string; name?: string }
  received?: Record<string, string>
  note?: string
}

export async function completeOidcCallback(queryString: string): Promise<OidcCallbackResult> {
  const path = '/api/v1/auth/callback' + (queryString?.startsWith('?') ? queryString : `?${queryString || ''}`)
  const res = await api.get(path)
  return res.data as OidcCallbackResult
}
