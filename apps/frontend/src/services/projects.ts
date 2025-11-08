import api from './api'

export type Project = {
  id: string
  name: string
  owner: string
}

export async function listProjects(): Promise<Project[]> {
  const res = await api.get('/api/v1/projects')
  return res.data
}
