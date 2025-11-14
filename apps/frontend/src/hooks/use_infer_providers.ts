import { useMutation } from '@tanstack/react-query'
import { inferProviders, inferProvidersAlias } from '../services/providers'
import type { EntitySchema } from '../types/schema'

type TaskType = 'chat' | 'embeddings' | 'tools'

export function useInferProviders(
  projectId?: string,
  opts?: {
    taskType?: TaskType
    // Optional mapping of task -> model_id, usually sourced from admin task-defaults endpoint
    taskDefaults?: Partial<Record<TaskType, string>>
  }
) {
  return useMutation({
    mutationFn: (entity: EntitySchema) => {
      const headers: Record<string, string> = {}
      if (opts?.taskType) headers['X-LLM-Task-Type'] = opts.taskType
      const modelId = opts?.taskType ? opts.taskDefaults?.[opts.taskType] : undefined
      if (modelId) headers['X-LLM-Model-Id'] = modelId
      return projectId ? inferProviders(projectId, entity, headers) : inferProvidersAlias(entity, headers)
    },
  })
}
