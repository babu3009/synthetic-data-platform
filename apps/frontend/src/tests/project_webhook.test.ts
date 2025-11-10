import { expect, test, vi, type Mock } from 'vitest'
import { registerRunStatusWebhook } from '../services/projects'
import { api } from '../services/api'

// Mock axios instance post method
vi.mock('../services/api', () => {
  const mockApi = {
    post: vi.fn().mockResolvedValue({ data: { id: 'p1', name: 'P', owner: 'o', webhook_run_status_url: 'http://cb', created_at: new Date().toISOString() } })
  }
  return {
    api: mockApi,
    default: mockApi,
  }
})

test('registerRunStatusWebhook posts payload and returns updated project', async () => {
  const projectId = 'p1'
  const url = 'http://cb'
  const result = await registerRunStatusWebhook(projectId, url)
  expect(result.webhook_run_status_url).toBe(url)
  expect(result.id).toBe(projectId)
  const apiPost = api.post as unknown as Mock
  expect(apiPost).toHaveBeenCalledWith('/api/v1/webhooks/run-status', { project_id: projectId, url })
})

test('registerRunStatusWebhook propagates error', async () => {
  const apiPost = api.post as unknown as Mock
  apiPost.mockRejectedValueOnce(new Error('fail'))
  await expect(registerRunStatusWebhook('p2', 'http://x')).rejects.toThrow('fail')
})
