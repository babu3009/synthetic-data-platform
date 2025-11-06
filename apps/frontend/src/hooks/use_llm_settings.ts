import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getProjectLlmSettings, updateProjectLlmSettings, type ProjectLlmSettings } from '../services/llm_settings'

const settingsKey = (projectId: string) => ['project.llm.settings', projectId]

export function useLlmSettings(projectId: string) {
  return useQuery<ProjectLlmSettings>({
    queryKey: settingsKey(projectId),
    queryFn: () => getProjectLlmSettings(projectId),
    enabled: !!projectId,
  })
}

export function useSaveLlmSettings(projectId: string) {
  const qc = useQueryClient()
  return useMutation<ProjectLlmSettings, unknown, ProjectLlmSettings>({
    mutationFn: (s) => updateProjectLlmSettings(projectId, s),
    onSuccess: () => qc.invalidateQueries({ queryKey: settingsKey(projectId) }),
  })
}
