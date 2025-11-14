import React from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getProject, updateProject, deleteProject, registerRunStatusWebhook, type Project } from '../../services/projects'
import { useToasts } from '../../hooks/use_toasts'

const ProjectDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { push } = useToasts()
  const qc = useQueryClient()

  const { data, isLoading, error } = useQuery<Project>({
    queryKey: ['project.byId', id],
    queryFn: () => getProject(id!),
    enabled: !!id,
  })

  const [name, setName] = React.useState('')
  const [owner, setOwner] = React.useState('')
  const [webhookUrl, setWebhookUrl] = React.useState('')
  React.useEffect(() => {
    if (data) {
      setName(data.name)
      setOwner(data.owner)
  setWebhookUrl(data.webhook_run_status_url || '')
    }
  }, [data])

  const saveMut = useMutation({
    mutationFn: () => updateProject(id!, { name, owner, webhook_run_status_url: webhookUrl || null }),
    onMutate: async () => {
      await qc.cancelQueries({ queryKey: ['project.byId', id] })
  const prevById = qc.getQueryData(['project.byId', id]) as Project | undefined
  const prevAll = qc.getQueryData(['projects.all']) as Project[] | undefined
  const nextById = { ...(prevById || { id: id!, name, owner, webhook_run_status_url: webhookUrl || null }), name, owner, webhook_run_status_url: webhookUrl || null }
  qc.setQueryData(['project.byId', id], nextById)
      if (prevAll) {
        qc.setQueryData(['projects.all'], prevAll.map(p => p.id === id ? { ...p, name, owner, webhook_run_status_url: webhookUrl || null } : p))
      }
      return { prevById, prevAll }
    },
    onError: (_e, _vars, ctx) => {
      if (ctx?.prevById) qc.setQueryData(['project.byId', id], ctx.prevById)
      if (ctx?.prevAll) qc.setQueryData(['projects.all'], ctx.prevAll)
    },
    onSuccess: () => {
      push('success', 'Project updated')
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['projects.all'] })
      qc.invalidateQueries({ queryKey: ['project.byId', id] })
    }
  })

  const delMut = useMutation({
    mutationFn: () => deleteProject(id!),
    onSuccess: () => {
      push('info', 'Project deleted')
      qc.invalidateQueries({ queryKey: ['projects.all'] })
      navigate('/projects')
    },
    onError: (e: unknown) => push('error', e instanceof Error ? e.message : 'Delete failed')
  })

  // Register/test webhook URL
  const testWebhookMut = useMutation({
    mutationFn: async () => {
      if (!webhookUrl) throw new Error('Enter a URL first')
      return registerRunStatusWebhook(id!, webhookUrl)
    },
    onSuccess: () => push('success', 'Webhook registered'),
    onError: (e: unknown) => push('error', e instanceof Error ? e.message : 'Webhook test failed'),
  })

  const isBusy = saveMut.isPending || testWebhookMut.isPending || delMut.isPending

  function handleDelete() {
    if (confirm('Delete this project? This cannot be undone.')) {
      delMut.mutate()
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (data?.owner && data.owner !== owner) {
      const ok = confirm('You changed the project owner. Continue with reassignment?')
      if (!ok) return
    }
    saveMut.mutate()
  }

  if (isLoading) return (
    <div className="container py-4 auth-narrow">
      <div className="card p-3">
        <div className="skeleton skeleton-line40" />
        <div className="skeleton skeleton-line30 mt-2" />
        <div className="skeleton skeleton-line50 mt-2" />
      </div>
    </div>
  )
  if (error) return <div className="container py-4"><div className="alert alert-danger">{(error as Error).message}</div></div>
  if (!data) return null

  return (
    <div className="container py-4 auth-narrow">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h2 className="mb-0">Project</h2>
        <div className="d-flex gap-2">
          <Link className="btn btn-outline-secondary" to={`/projects/${id}/sources`}>Sources</Link>
          <Link className="btn btn-outline-secondary" to={`/projects/${id}/api-keys`}>API Keys</Link>
          <Link className="btn btn-outline-secondary" to={`/projects/${id}/requests`}>Requests</Link>
          <Link className="btn btn-outline-secondary" to={`/projects/${id}/validation`}>Validation</Link>
          <button className="btn btn-outline-danger" disabled={delMut.isPending} onClick={handleDelete}>Delete</button>
        </div>
      </div>
  <form onSubmit={handleSubmit}>
        <div className="mb-3">
          <label htmlFor="pname" className="form-label">Name</label>
          <input id="pname" className="form-control" value={name} onChange={(e) => setName(e.target.value)} required />
        </div>
        <div className="mb-3">
          <label htmlFor="powner" className="form-label">Owner</label>
          <input id="powner" className="form-control" value={owner} onChange={(e) => setOwner(e.target.value)} required />
        </div>
        <div className="mb-3">
          <label htmlFor="pwebhook" className="form-label">Run Status Webhook URL</label>
          <input id="pwebhook" className="form-control" type="url" placeholder="https://example.com/webhook" value={webhookUrl} onChange={(e) => setWebhookUrl(e.target.value)} />
          <small className="text-muted">Receives job status POST callbacks. Use the button to register/update.</small>
        </div>
        <div className="d-flex gap-2">
          <button className="btn btn-primary" disabled={isBusy}>Save</button>
          <button type="button" className="btn btn-outline-info" disabled={testWebhookMut.isPending || !webhookUrl} onClick={() => testWebhookMut.mutate()}>Register Webhook</button>
          <Link className="btn btn-outline-secondary" to="/projects">Back</Link>
        </div>
      </form>
    </div>
  )
}

export default ProjectDetailPage
