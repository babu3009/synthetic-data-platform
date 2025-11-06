import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { EntitySchema, EntitySchemaCreate, EntitySchemaUpdate } from '../types/schema'
import { listEntities, createEntity, updateEntity, deleteEntity } from '../services/entities'

export function useEntities(projectId?: string) {
  const qc = useQueryClient()
  const key = ['entities', projectId]

  const list = useQuery({
    queryKey: key,
    queryFn: () => listEntities(projectId!),
    enabled: !!projectId,
  })

  const create = useMutation({
    mutationFn: (payload: EntitySchemaCreate) => createEntity(projectId!, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: key }),
  })

  const update = useMutation({
    mutationFn: (args: { id: string; patch: EntitySchemaUpdate }) => updateEntity(projectId!, args.id, args.patch),
    onSuccess: (_data: EntitySchema) => qc.invalidateQueries({ queryKey: key }),
  })

  const remove = useMutation({
    mutationFn: (id: string) => deleteEntity(projectId!, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: key }),
  })

  return { list, create, update, remove }
}
