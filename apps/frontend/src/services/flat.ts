import api from './api'

export interface FlatPreviewInput {
  schema: unknown
  n?: number
}

export interface FlatPreviewResponse {
  rows: Array<Record<string, unknown>>
}

export async function flatPreview(input: FlatPreviewInput): Promise<FlatPreviewResponse> {
  const res = await api.post('/api/v1/flat/preview', input)
  return res.data as FlatPreviewResponse
}
