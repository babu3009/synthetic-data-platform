import React from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { listSources, type SourceListItem } from '../../services/sources'

const SourcesListPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>()
  const { data, isLoading, error } = useQuery<SourceListItem[]>({
    queryKey: ['sources.list', projectId],
    queryFn: () => listSources(projectId!),
    enabled: !!projectId,
  })

  if (isLoading) return <div className="container py-4"><div className="skeleton skeleton-line40" /></div>
  if (error) return <div className="container py-4"><div className="alert alert-danger">{(error as Error).message}</div></div>

  const items = data || []
  return (
    <div className="container py-4">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h2 className="mb-0">Sources</h2>
        <Link className="btn btn-outline-secondary" to={`/projects/${projectId}`}>Back to Project</Link>
      </div>
      {items.length === 0 ? (
        <div className="alert alert-info">No sources yet or listing not available. Try uploading via the wizard or DDL/JSON tools.</div>
      ) : (
        <div className="table-responsive">
          <table className="table table-sm align-middle">
            <thead>
              <tr>
                <th>ID</th>
                <th>Kind</th>
                <th>Tables</th>
                <th>Created</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map(s => (
                <tr key={s.id}>
                  <td><code>{s.id}</code></td>
                  <td>{s.kind}</td>
                  <td>{s.tables_count ?? '-'}</td>
                  <td>{s.created_at ? new Date(s.created_at).toLocaleString() : '-'}</td>
                  <td className="text-nowrap">
                    <Link className="btn btn-sm btn-outline-primary me-2" to={`/projects/${projectId}/sources/${s.id}/schema`}>Schema</Link>
                    <Link className="btn btn-sm btn-outline-secondary" to={`/projects/${projectId}/sources/${s.id}/dag`}>DAG</Link>
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

export default SourcesListPage
