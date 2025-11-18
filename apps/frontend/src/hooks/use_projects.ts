import { useQuery } from '@tanstack/react-query'
import { listProjects, type Project } from '../services/projects'
import { useAuth } from '../state/use_auth'

const key = ['projects.all']

export function useProjects() {
  const { token } = useAuth()
  
  return useQuery<Project[]>({ 
    queryKey: key, 
    queryFn: () => listProjects(),
    enabled: !!token // Only fetch when authenticated
  })
}
