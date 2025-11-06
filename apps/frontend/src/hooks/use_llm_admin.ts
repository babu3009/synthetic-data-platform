import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  listProviders,
  createProvider,
  updateProvider,
  upsertCredentials,
  listModels,
  createModel,
  probeProvider,
  discoverModels,
  markModelDefault,
  type LLMProvider,
  type CreateProviderInput,
  type UpdateProviderInput,
  type UpsertCredentialsInput,
  type LLMModel,
  type CreateModelInput,
  type DiscoverModelsResponse,
  type ProbeResult,
} from '../services/llm_admin'

// Query keys
const providersKey = (projectId: string) => ['llm.providers', projectId]
const modelsKey = (projectId: string, providerId: string) => ['llm.models', projectId, providerId]

export function useLlmProviders(projectId: string) {
  return useQuery<LLMProvider[]>({
    queryKey: providersKey(projectId),
    queryFn: () => listProviders(projectId),
    enabled: !!projectId,
  })
}

export function useCreateLlmProvider(projectId: string) {
  const qc = useQueryClient()
  return useMutation<LLMProvider, unknown, CreateProviderInput>({
    mutationFn: (input) => createProvider(projectId, input),
    onSuccess: () => qc.invalidateQueries({ queryKey: providersKey(projectId) }),
  })
}

export function useUpdateLlmProvider(projectId: string, providerId: string) {
  const qc = useQueryClient()
  return useMutation<LLMProvider, unknown, UpdateProviderInput>({
    mutationFn: (input) => updateProvider(projectId, providerId, input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: providersKey(projectId) })
    },
  })
}

export function useUpsertLlmCredentials(projectId: string, providerId: string) {
  const qc = useQueryClient()
  return useMutation<unknown, unknown, UpsertCredentialsInput>({
    mutationFn: (input) => upsertCredentials(projectId, providerId, input),
    onSuccess: () => qc.invalidateQueries({ queryKey: providersKey(projectId) }),
  })
}

export function useLlmModels(projectId: string, providerId: string) {
  return useQuery<LLMModel[]>({
    queryKey: modelsKey(projectId, providerId),
    queryFn: () => listModels(projectId, providerId),
    enabled: !!projectId && !!providerId,
  })
}

export function useCreateLlmModel(projectId: string, providerId: string) {
  const qc = useQueryClient()
  return useMutation<LLMModel, unknown, CreateModelInput>({
    mutationFn: (input) => createModel(projectId, providerId, input),
    onSuccess: () => qc.invalidateQueries({ queryKey: modelsKey(projectId, providerId) }),
  })
}

export function useProbeProvider(projectId: string, providerId: string) {
  return useMutation<ProbeResult, unknown, void>({
    mutationFn: () => probeProvider(projectId, providerId),
  })
}

export function useDiscoverModels(projectId: string, providerId: string) {
  const qc = useQueryClient()
  return useMutation<DiscoverModelsResponse, unknown, void>({
    mutationFn: () => discoverModels(projectId, providerId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: modelsKey(projectId, providerId) })
    },
  })
}

export function useMarkModelDefault(projectId: string, providerId: string) {
  const qc = useQueryClient()
  return useMutation<LLMModel, unknown, LLMModel>({
    mutationFn: (model) => markModelDefault(projectId, providerId, model),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: modelsKey(projectId, providerId) })
    },
  })
}
