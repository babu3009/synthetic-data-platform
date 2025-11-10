import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { listProjects, type Project } from '../../services/projects'
import { Link } from 'react-router-dom'

const ProjectsListPage: React.FC = () => {
  const { data, isLoading, error } = useQuery<Project[]>({ queryKey: ['projects.all'], queryFn: listProjects })
  const [query, setQuery] = React.useState('')
  const [page, setPage] = React.useState(1)
  const pageSize = 10
  const filtered = React.useMemo(() => {
    const all = data || []
    const q = query.trim().toLowerCase()
    const f = q ? all.filter(p => p.name.toLowerCase().includes(q) || p.owner.toLowerCase().includes(q)) : all
    const start = (page - 1) * pageSize
    return { total: f.length, items: f.slice(start, start + pageSize) }
  }, [data, query, page])

  return (
    <div className="container py-4">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h2 className="mb-0">Projects</h2>
        <Link to="/projects/new" className="btn btn-primary">New Project</Link>
      </div>

      {isLoading && (
        <div className="card p-3">
          <div className="skeleton skeleton-line50" />
          <div className="skeleton skeleton-line50 mt-2" />
          <div className="skeleton skeleton-line50 mt-2" />
        </div>
      )}
      {error && <div className="alert alert-danger">{(error as Error).message}</div>}

      {data && data.length === 0 && <div className="alert alert-info">No projects yet. Create your first project.</div>}

      {data && data.length > 0 && (
        <div className="mb-3 d-flex align-items-center gap-2">
          <label htmlFor="project-search" className="form-label mb-0">Search</label>
          <input id="project-search" className="form-control maxw-280" value={query} onChange={e => { setPage(1); setQuery(e.target.value) }} placeholder="name or owner" />
        </div>
      )}

      {data && data.length > 0 && (
        <div className="table-responsive">
          <table className="table align-middle">
            <thead>
              <tr>
                <th>Name</th>
                <th>Owner</th>
                <th>Webhook URL</th>
                <th>Created</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.items.map((p) => (
                <tr key={p.id}>
                  <td>{p.name}</td>
                  <td>{p.owner}</td>
                  <td className="text-truncate maxw-280">{p.webhook_run_status_url || '-'}</td>
                  <td>{p.created_at ? new Date(p.created_at).toLocaleString() : '-'}</td>
                  <td><Link className="btn btn-sm btn-outline-secondary" to={`/projects/${p.id}`}>Open</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
          {filtered.total > pageSize && (
            <div className="d-flex justify-content-end align-items-center gap-2">
              <button className="btn btn-sm btn-outline-secondary" disabled={page === 1} onClick={() => setPage(p => Math.max(1, p-1))}>Prev</button>
              <span className="text-muted">Page {page} / {Math.ceil(filtered.total / pageSize)}</span>
              <button className="btn btn-sm btn-outline-secondary" disabled={page >= Math.ceil(filtered.total / pageSize)} onClick={() => setPage(p => p+1)}>Next</button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default ProjectsListPage
