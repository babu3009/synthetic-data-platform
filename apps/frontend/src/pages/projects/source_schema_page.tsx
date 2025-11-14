import React from 'react'
import { useParams, Link } from 'react-router-dom'
import { useSourceSchema } from '../../hooks/use_sources'

type Column = { name: string; dtype: string; nullable?: boolean }
type Table = { name: string; columns?: Column[]; pk?: string[] }
type Canonical = { tables?: Table[] }

const SourceSchemaPage: React.FC = () => {
  const { projectId, sourceId } = useParams<{ projectId: string; sourceId: string }>()
  const { data, isLoading, error } = useSourceSchema(projectId, sourceId)

  if (isLoading) return <div className="container py-4"><div className="skeleton skeleton-line40" /></div>
  if (error) return <div className="container py-4"><div className="alert alert-danger">{(error as Error).message}</div></div>
  if (!data) return null

  const canonical = (data as unknown as { schema?: Canonical; canonical_schema?: Canonical }).schema ||
    (data as unknown as { schema?: Canonical; canonical_schema?: Canonical }).canonical_schema
  const tables: Table[] = canonical?.tables || []

  return (
    <div className="container py-4">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h2 className="mb-0">Source Schema</h2>
        <div className="d-flex gap-2">
          <Link className="btn btn-outline-secondary" to={`/projects/${projectId}/sources/${sourceId}/dag`}>View DAG</Link>
          <Link className="btn btn-outline-secondary" to={`/projects/${projectId}/sources`}>Back to Sources</Link>
        </div>
      </div>
      {tables.length === 0 ? (
        <div className="alert alert-warning">No tables found.</div>
      ) : (
        <div className="table-responsive">
          <table className="table table-sm">
            <thead>
              <tr>
                <th>Table</th>
                <th>Columns</th>
                <th>PK</th>
              </tr>
            </thead>
            <tbody>
              {tables.map((t) => (
                <tr key={t.name}>
                  <td><strong>{t.name}</strong></td>
                  <td>
                    <ul className="mb-0">
                      {t.columns?.map((c) => (
                        <li key={c.name}><code>{c.name}</code> <small className="text-muted">{c.dtype}{c.nullable ? '' : ' not null'}</small></li>
                      ))}
                    </ul>
                  </td>
                  <td>{Array.isArray(t.pk) && t.pk.length > 0 ? t.pk.join(', ') : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default SourceSchemaPage
