import api from './api'

export interface AdminUser {
  id: string
  email: string
  role?: string
  status?: string
  organization?: string | null
  created_at?: string
}

export async function listAdminUsers(params?: { status?: string }) {
  const res = await api.get<AdminUser[]>('/api/v1/admin/users', { params })
  return res.data
}

export async function approveUser(userId: string) {
  const res = await api.post(`/api/v1/admin/users/${encodeURIComponent(userId)}/approve`)
  return res.data as { status?: string; message?: string }
}

export async function rejectUser(userId: string) {
  const res = await api.post(`/api/v1/admin/users/${encodeURIComponent(userId)}/reject`)
  return res.data as { status?: string; message?: string }
}
