import { useMutation } from '@tanstack/react-query'
import { inferProviders } from '../services/providers'
import type { EntitySchema } from '../types/schema'

export function useInferProviders(projectId?: string) {
  return useMutation({
    mutationFn: (entity: EntitySchema) => inferProviders(projectId!, entity),
  })
}
