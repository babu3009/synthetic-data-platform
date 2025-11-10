import React from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createProject } from '../../services/projects'
import { useNavigate } from 'react-router-dom'
import { useToasts } from '../../hooks/use_toasts'

const ProjectCreatePage: React.FC = () => {
  const [name, setName] = React.useState('')
  const [owner, setOwner] = React.useState('')
  const [webhookUrl, setWebhookUrl] = React.useState('')
  const navigate = useNavigate()
  const { push } = useToasts()
  const qc = useQueryClient()

  const mut = useMutation({
    mutationFn: () => createProject({ name, owner, webhook_run_status_url: webhookUrl || undefined }),
    onMutate: async () => {
      await qc.cancelQueries({ queryKey: ['projects.all'] })
  const prev = qc.getQueryData<unknown>(['projects.all']) as Array<{ id:string; name:string; owner:string; webhook_run_status_url?:string|null; created_at?:string }> | undefined
      // optimistic: add a temp item
      const tempId = 'temp-' + Date.now()
  const optimistic = [...(prev || []), { id: tempId, name, owner, webhook_run_status_url: webhookUrl || null, created_at: new Date().toISOString() }]
      qc.setQueryData(['projects.all'], optimistic)
      return { prev }
    },
    onError: (_e, _vars, ctx) => {
      if (ctx?.prev) qc.setQueryData(['projects.all'], ctx.prev)
    },
    onSuccess: (p) => {
      push('success', 'Project created')
      // replace temp with real by invalidating
      qc.invalidateQueries({ queryKey: ['projects.all'] })
      navigate(`/projects/${p.id}`)
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['projects.all'] })
    }
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    mut.mutate()
  }

  return (
    <div className="container py-4 auth-narrow">
      <h2>New Project</h2>
      <form onSubmit={handleSubmit} className="mt-3">
        <div className="mb-3">
          <label htmlFor="pname" className="form-label">Name</label>
          <input id="pname" className="form-control" value={name} onChange={(e) => setName(e.target.value)} required />
        </div>
        <div className="mb-3">
          <label htmlFor="powner" className="form-label">Owner</label>
          <input id="powner" className="form-control" value={owner} onChange={(e) => setOwner(e.target.value)} required />
        </div>
        <div className="mb-3">
          <label htmlFor="pwebhook" className="form-label">Run Status Webhook URL (optional)</label>
          <input id="pwebhook" className="form-control" type="url" placeholder="https://example.com/webhook" value={webhookUrl} onChange={(e) => setWebhookUrl(e.target.value)} />
          <small className="text-muted">Receives job status POST callbacks.</small>
        </div>
        <button className="btn btn-primary" disabled={mut.isPending}>Create</button>
      </form>
    </div>
  )
}

export default ProjectCreatePage
