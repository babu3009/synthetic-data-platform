import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { listProjects, type Project } from '../../services/projects'
import { Link } from 'react-router-dom'
import ProjectCreateModal from '../../components/project_create_modal'

const ProjectsListPage: React.FC = () => {
  const { data, isLoading, error } = useQuery<Project[]>({ queryKey: ['projects.all'], queryFn: listProjects })
  const [query, setQuery] = React.useState('')
  const [page, setPage] = React.useState(1)
  const [showCreateModal, setShowCreateModal] = React.useState(false)
  const pageSize = 10
  const filtered = React.useMemo(() => {
    const all = data || []
    const q = query.trim().toLowerCase()
    const f = q ? all.filter(p => p.name.toLowerCase().includes(q) || (p.owner && p.owner.toLowerCase().includes(q))) : all
    const start = (page - 1) * pageSize
    return { total: f.length, items: f.slice(start, start + pageSize) }
  }, [data, query, page])

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <div className="container-fluid py-4">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2 className="mb-0">Projects</h2>
        <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
          <i className="bi bi-plus-circle me-2"></i>New Project
        </button>
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
          <table className="table table-hover align-middle">
            <thead className="table-light">
              <tr>
                <th style={{ width: '50px' }}>#</th>
                <th>Project Name</th>
                <th>Description</th>
                <th>Tags</th>
                <th>Settings</th>
                <th>Created Date</th>
                <th>Updated Date</th>
                <th style={{ width: '200px' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.items.map((p, idx) => (
                <tr key={p.id}>
                  <td className="text-muted">{(page - 1) * pageSize + idx + 1}</td>
                  <td>
                    <Link to={`/projects/${p.id}`} className="text-decoration-none fw-semibold">
                      {p.name}
                    </Link>
                  </td>
                  <td className="text-muted small" style={{ maxWidth: '300px' }}>
                    {p.description || <span className="text-muted fst-italic">No description</span>}
                  </td>
                  <td className="small">
                    {p.tags && p.tags.length > 0 ? (
                      <div className="d-flex flex-wrap gap-1">
                        {p.tags.map((tag, i) => (
                          <span key={i} className="badge bg-secondary">{tag}</span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-muted fst-italic">No tags</span>
                    )}
                  </td>
                  <td className="text-muted small">
                    {p.webhook_run_status_url && (
                      <div><i className="bi bi-webhook me-1"></i>Webhook</div>
                    )}
                    {p.artifact_ttl_days !== null && p.artifact_ttl_days !== undefined && (
                      <div><i className="bi bi-clock-history me-1"></i>TTL: {p.artifact_ttl_days}d</div>
                    )}
                    {!p.webhook_run_status_url && (p.artifact_ttl_days === null || p.artifact_ttl_days === undefined) && (
                      <span className="text-muted fst-italic">Default</span>
                    )}
                  </td>
                  <td className="text-muted small">{formatDate(p.created_at)}</td>
                  <td className="text-muted small">{formatDate(p.updated_at)}</td>
                  <td>
                    <div className="d-flex gap-1">
                      <Link className="btn btn-sm btn-outline-primary" to={`/projects/${p.id}`} title="View Project">
                        <i className="bi bi-eye"></i>
                      </Link>
                      <Link className="btn btn-sm btn-outline-secondary" to={`/projects/${p.id}/edit`} title="Edit Project">
                        <i className="bi bi-pencil"></i>
                      </Link>
                      <Link className="btn btn-sm btn-outline-success" to={`/projects/${p.id}/wizard`} title="Data Wizard">
                        <i className="bi bi-magic"></i>
                      </Link>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filtered.total > pageSize && (
            <div className="d-flex justify-content-between align-items-center mt-3">
              <div className="text-muted">
                Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, filtered.total)} of {filtered.total} projects
              </div>
              <div className="d-flex align-items-center gap-2">
                <button className="btn btn-sm btn-outline-secondary" disabled={page === 1} onClick={() => setPage(p => Math.max(1, p-1))}>
                  <i className="bi bi-chevron-left"></i> Prev
                </button>
                <span className="text-muted">Page {page} of {Math.ceil(filtered.total / pageSize)}</span>
                <button className="btn btn-sm btn-outline-secondary" disabled={page >= Math.ceil(filtered.total / pageSize)} onClick={() => setPage(p => p+1)}>
                  Next <i className="bi bi-chevron-right"></i>
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      <ProjectCreateModal show={showCreateModal} onClose={() => setShowCreateModal(false)} />
    </div>
  )
}

export default ProjectsListPage
