import React from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { approveUser, rejectUser, listAdminUsers, type AdminUser } from '../../services/admin_users'
import { useAuth } from '../../state/use_auth'
import { useToasts } from '../../hooks/use_toasts'

const AdminUsersPage: React.FC = () => {
  const { role } = useAuth()
  const { push } = useToasts()
  const qc = useQueryClient()
  const [statusFilter, setStatusFilter] = React.useState<'PENDING'|'ALL'>('PENDING')

  const { data, isLoading, error } = useQuery({
    queryKey: ['admin-users', statusFilter],
    queryFn: () => listAdminUsers(statusFilter === 'PENDING' ? { status: 'PENDING' } : undefined),
  })

  const approveMut = useMutation({
    mutationFn: (uid: string) => approveUser(uid),
    onSuccess: () => {
      push('success', 'User approved')
      qc.invalidateQueries({ queryKey: ['admin-users'] })
    },
    onError: (e: unknown) => push('error', e instanceof Error ? e.message : 'Approve failed')
  })
  const rejectMut = useMutation({
    mutationFn: (uid: string) => rejectUser(uid),
    onSuccess: () => {
      push('info', 'User rejected')
      qc.invalidateQueries({ queryKey: ['admin-users'] })
    },
    onError: (e: unknown) => push('error', e instanceof Error ? e.message : 'Reject failed')
  })

  if (role !== 'OWNER') {
    return <div className="container py-4"><div className="alert alert-warning">Forbidden: Owner role required.</div></div>
  }

  return (
    <div className="container py-4">
      <div className="d-flex align-items-center justify-content-between mb-3">
        <h2 className="mb-0">Admin Users</h2>
        <div>
          <label htmlFor="status-filter" className="form-label me-2 mb-0">Filter</label>
          <select id="status-filter" className="form-select d-inline-block w-180" value={statusFilter} onChange={e => setStatusFilter(e.target.value as 'PENDING'|'ALL')}>
            <option value="PENDING">Pending</option>
            <option value="ALL">All</option>
          </select>
        </div>
      </div>

      {isLoading && (
        <div className="card p-3">
          <div className="skeleton skeleton-line50" />
          <div className="skeleton skeleton-line50 mt-2" />
          <div className="skeleton skeleton-line50 mt-2" />
        </div>
      )}
      {error && <div className="alert alert-danger">{(error as Error).message}</div>}

      {data && data.length === 0 && <div className="alert alert-info">No users found for this filter.</div>}

      {data && data.length > 0 && (
        <div className="table-responsive">
          <table className="table table-sm align-middle">
            <thead>
              <tr>
                <th>Email</th>
                <th>Organization</th>
                <th>Status</th>
                <th>Role</th>
                <th>Joined</th>
                <th className="col-actions-180">Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.map((u: AdminUser) => (
                <tr key={u.id}>
                  <td>{u.email}</td>
                  <td>{u.organization || '-'}</td>
                  <td><span className={`badge ${u.status === 'PENDING' ? 'text-bg-warning' : u.status === 'APPROVED' ? 'text-bg-success' : 'text-bg-secondary'}`}>{u.status || '-'}</span></td>
                  <td>{u.role || '-'}</td>
                  <td>{u.created_at ? new Date(u.created_at).toLocaleString() : '-'}</td>
                  <td>
                    <div className="btn-group">
                      <button className="btn btn-sm btn-success" disabled={approveMut.isPending} onClick={() => approveMut.mutate(u.id)}>Approve</button>
                      <button className="btn btn-sm btn-outline-danger" disabled={rejectMut.isPending} onClick={() => rejectMut.mutate(u.id)}>Reject</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default AdminUsersPage
