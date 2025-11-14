import React from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listApiKeys, createApiKey, revokeApiKey, listApiKeyScopes, type ApiKey, type CreateApiKeyInput } from '../../services/apiKeys';
import { useToasts } from '../../hooks/use_toasts';

const fallbackScopes = ['read:project', 'write:project', 'run:request', 'read:artifacts'];

const ProjectApiKeysPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const qc = useQueryClient();
  const { push } = useToasts();
  const pid = projectId!;

  const [page, setPage] = React.useState(1);
  const [pageSize] = React.useState(10);
  const [search, setSearch] = React.useState('');

  const { data: keys, isLoading, error } = useQuery<ApiKey[]>({
    queryKey: ['api-keys.list', pid, page, pageSize, search],
    queryFn: () => listApiKeys(pid, { page, pageSize, search }),
    enabled: !!pid,
  });

  const { data: scopeList } = useQuery<string[]>({
    queryKey: ['api-keys.scopes', pid],
    queryFn: () => listApiKeyScopes(pid),
    enabled: !!pid,
  })

  const [showCreate, setShowCreate] = React.useState(false);
  const [name, setName] = React.useState('');
  const [selectedScopes, setSelectedScopes] = React.useState<string[]>([]);
  const [createdPlaintext, setCreatedPlaintext] = React.useState<string | null>(null);

  const createMut = useMutation({
    mutationFn: async () => {
      const payload: CreateApiKeyInput = { name, scopes: selectedScopes };
      return createApiKey(pid, payload);
    },
    onSuccess: (resp) => {
      setCreatedPlaintext(resp.plaintext_key || null);
      push('success', 'API key created');
      setShowCreate(false);
      setName('');
      setSelectedScopes([]);
      qc.invalidateQueries({ queryKey: ['api-keys.list', pid] });
    },
    onError: (e: unknown) => push('error', e instanceof Error ? e.message : 'Create failed'),
  });

  const revokeMut = useMutation({
    mutationFn: async (keyId: string) => revokeApiKey(pid, keyId),
    onMutate: async (keyId: string) => {
      await qc.cancelQueries({ queryKey: ['api-keys.list', pid, page, pageSize, search] })
      const prev = qc.getQueryData<ApiKey[]>(['api-keys.list', pid, page, pageSize, search])
      if (prev) {
        qc.setQueryData<ApiKey[]>(['api-keys.list', pid, page, pageSize, search], prev.filter(k => k.id !== keyId))
      }
      return { prev }
    },
    onError: (e: unknown, _vars, ctx) => {
      if (ctx?.prev) qc.setQueryData(['api-keys.list', pid, page, pageSize, search], ctx.prev)
      push('error', e instanceof Error ? e.message : 'Revoke failed')
    },
    onSuccess: () => {
      push('info', 'API key revoked');
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['api-keys.list', pid] })
    }
  });

  function toggleScope(scope: string) {
    setSelectedScopes(s => s.includes(scope) ? s.filter(x => x !== scope) : [...s, scope]);
  }

  function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    createMut.mutate();
  }

  if (isLoading) return <div className="container py-4"><div className="skeleton skeleton-line40" /><div className="skeleton skeleton-line30 mt-2" /></div>;
  if (error) return <div className="container py-4"><div className="alert alert-danger">{(error as Error).message}</div></div>;

  return (
    <div className="container py-4 auth-narrow">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h2 className="mb-0">API Keys</h2>
        <div className="d-flex gap-2">
          <input className="form-control form-control-sm w-240" placeholder="Search by name..." value={search} onChange={e => { setPage(1); setSearch(e.target.value) }} />
          <button className="btn btn-primary" onClick={() => { setShowCreate(true); setCreatedPlaintext(null); }}>Create Key</button>
        </div>
      </div>

      {createdPlaintext && (
        <div className="alert alert-warning" role="alert">
            <strong>Copy your new key now:</strong> <code className="select-all">{createdPlaintext}</code>
          <div className="small mt-1">This plaintext will not be shown again after a page refresh.</div>
        </div>
      )}

      {showCreate && (
        <form onSubmit={handleCreate} className="card p-3 mb-4">
          <div className="mb-3">
            <label className="form-label" htmlFor="kname">Name</label>
            <input id="kname" className="form-control" value={name} onChange={e => setName(e.target.value)} required />
          </div>
          <div className="mb-3">
            <label className="form-label">Scopes</label>
            <div className="d-flex flex-wrap gap-2">
              {(scopeList ?? fallbackScopes).map(sc => (
                <button type="button" key={sc} className={`btn btn-sm ${selectedScopes.includes(sc) ? 'btn-secondary' : 'btn-outline-secondary'}`} onClick={() => toggleScope(sc)}>{sc}</button>
              ))}
            </div>
          </div>
          <div className="d-flex gap-2">
            <button className="btn btn-success" disabled={createMut.isPending}>Create</button>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
          </div>
        </form>
      )}

      <table className="table table-sm table-striped">
        <thead>
          <tr><th>Name</th><th>Scopes</th><th>Created</th><th /></tr>
        </thead>
        <tbody>
          {keys && keys.length > 0 ? keys.map(k => (
            <tr key={k.id}>
              <td>{k.name}</td>
              <td>{k.scopes?.map(s => <span key={s} className="badge text-bg-light me-1">{s}</span>)}</td>
              <td>{new Date(k.created_at).toLocaleString()}</td>
              <td className="text-end">
                <button className="btn btn-sm btn-outline-danger" disabled={revokeMut.isPending} onClick={() => { if (confirm('Revoke this key?')) revokeMut.mutate(k.id); }}>Revoke</button>
              </td>
            </tr>
          )) : (
            <tr><td colSpan={4} className="text-muted">No API keys yet.</td></tr>
          )}
        </tbody>
      </table>
      <div className="d-flex justify-content-between align-items-center">
        <div className="text-muted small">Page {page}</div>
        <div className="d-flex gap-2">
          <button className="btn btn-sm btn-outline-secondary" disabled={page <= 1} onClick={() => setPage(p => Math.max(1, p - 1))}>Prev</button>
          <button className="btn btn-sm btn-outline-secondary" disabled={!keys || keys.length < pageSize} onClick={() => setPage(p => p + 1)}>Next</button>
        </div>
      </div>
    </div>
  );
};

export default ProjectApiKeysPage;
