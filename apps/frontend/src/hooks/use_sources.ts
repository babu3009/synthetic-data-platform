import { useMutation, useQuery } from '@tanstack/react-query'
import { uploadDDLSource, uploadJSONSource, getSourceSchema } from '../services/sources'

export function useSources(projectId?: string) {
  const uploadDDL = useMutation({
    mutationFn: (args: { file: File; dialect?: string; headers?: Record<string, string> }) =>
      uploadDDLSource(projectId!, args.file, args.dialect, args.headers),
  })

  const uploadJSON = useMutation({
    mutationFn: (args: { file: File; headers?: Record<string, string> }) => uploadJSONSource(projectId!, args.file, args.headers),
  })

  return { uploadDDL, uploadJSON }
}

export function useSourceSchema(projectId: string | undefined, sourceId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: ['source-schema', projectId, sourceId],
    queryFn: () => getSourceSchema(projectId!, sourceId!),
    enabled: !!projectId && !!sourceId && enabled,
  })
}
