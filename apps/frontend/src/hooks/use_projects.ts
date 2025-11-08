import { useQuery } from '@tanstack/react-query'
import { listProjects, type Project } from '../services/projects'

const key = ['projects.all']

export function useProjects() {
  return useQuery<Project[]>({ queryKey: key, queryFn: () => listProjects() })
}
