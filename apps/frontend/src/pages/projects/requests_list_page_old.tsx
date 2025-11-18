import React from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { listRequests, type Request } from '../../services/requests'

const statusVariant: Record<Request['status'], string> = {
  pending: 'secondary',
  running: 'primary',
  completed: 'success',
  failed: 'danger',
  cancelled: 'warning',
}

const RequestsListPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>()
  const pid = projectId!
  const [page, setPage] = React.useState(1)
  const [pageSize] = React.useState(10)
  const [search, setSearch] = React.useState('')

  const { data: requests, isLoading, error } = useQuery<Request[]>({
    queryKey: ['requests.list', pid, page, pageSize, search],
    queryFn: () => listRequests(pid, { page, pageSize, search }),
    enabled: !!pid,
  })

  return (
    <div className="container py-4">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h2 className="mb-0">Requests</h2>
        <input className="form-control form-control-sm w-240" placeholder="Search by id or type..." value={search} onChange={e => { setPage(1); setSearch(e.target.value) }} />
      </div>

      {isLoading && (
        <table className="table table-sm">
          <thead>
            <tr>
              <th>ID</th>
              <th>Type</th>
              <th>Status</th>
              <th>Created</th>
              <th>Last Run</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: 8 }).map((_, i) => (
              <tr key={i}>
                <td><span className="placeholder col-8" /></td>
                <td><span className="placeholder col-4" /></td>
                <td><span className="placeholder col-3" /></td>
                <td><span className="placeholder col-6" /></td>
                <td><span className="placeholder col-6" /></td>
                <td className="text-end"><span className="placeholder col-4" /></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {error && <div className="alert alert-danger">{(error as Error).message}</div>}

      <table className="table table-sm table-striped" aria-busy={isLoading ? true : undefined}
        aria-describedby={isLoading ? 'requests-loading' : undefined}>
        <thead>
          <tr>
            <th>ID</th>
            <th>Type</th>
            <th>Status</th>
            <th>Created</th>
            <th>Last Run</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {!requests || requests.length === 0 ? (
            <tr><td colSpan={6} className="text-muted">No requests found.</td></tr>
          ) : requests.map(r => (
            <tr key={r.id}>
              <td><code>{r.id}</code></td>
              <td>{r.type}</td>
              <td><span className={`badge text-bg-${statusVariant[r.status]}`}>{r.status}</span></td>
              <td>{new Date(r.created_at).toLocaleString()}</td>
              <td>{r.finished_at ? new Date(r.finished_at).toLocaleString() : (r.started_at ? new Date(r.started_at).toLocaleString() : '—')}</td>
              <td className="text-end">
                <Link className="btn btn-sm btn-outline-secondary" to={`/projects/${pid}/requests/${r.id}`}>View</Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="d-flex justify-content-between align-items-center">
        <div className="text-muted small">Page {page}</div>
        <div className="d-flex gap-2">
          <button className="btn btn-sm btn-outline-secondary" disabled={page <= 1} onClick={() => setPage(p => Math.max(1, p - 1))}>Prev</button>
          <button className="btn btn-sm btn-outline-secondary" disabled={!requests || requests.length < pageSize} onClick={() => setPage(p => p + 1)}>Next</button>
        </div>
      </div>
    </div>
  )
}

export default RequestsListPage
