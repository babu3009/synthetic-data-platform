import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, beforeEach, expect, vi } from 'vitest'
import { TestProviders, withRoute } from './utils/TestProviders'
import RequestsListPage from '../pages/projects/requests_list_page'
import RequestDetailPage from '../pages/request_detail_page'
import * as reqSvc from '../services/requests'

vi.mock('../services/requests', () => ({
  listRequests: vi.fn(),
  getRequest: vi.fn(),
  listArtifacts: vi.fn(),
  signArtifact: vi.fn(),
}))

const listRequests = reqSvc.listRequests as unknown as ReturnType<typeof vi.fn>
const getRequest = reqSvc.getRequest as unknown as ReturnType<typeof vi.fn>
const listArtifacts = reqSvc.listArtifacts as unknown as ReturnType<typeof vi.fn>
const signArtifact = reqSvc.signArtifact as unknown as ReturnType<typeof vi.fn>

describe('Requests & Artifacts pages', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.clearAllMocks()
  })

  it('renders requests list with status badges and view link', async () => {
    listRequests.mockResolvedValue([
      { id: 'r1', project_id: 'p123', type: 'relational', status: 'completed', created_at: new Date().toISOString() },
      { id: 'r2', project_id: 'p123', type: 'flat', status: 'running', created_at: new Date().toISOString() },
    ])

    render(
      <TestProviders initialEntries={["/projects/p123/requests"]} routes={withRoute('/projects/:projectId/requests', <RequestsListPage />)}>
        <div />
      </TestProviders>
    )

  expect(await screen.findByRole('heading', { name: 'Requests' })).toBeInTheDocument()
  // wait for the first View link to appear
  const viewLinks = await screen.findAllByRole('link', { name: 'View' })
  expect(viewLinks.length).toBeGreaterThan(0)
  })

  it('clicking Get Signed URL calls sign endpoint and opens URL', async () => {
    // mock window.open
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null)

    getRequest.mockResolvedValue({ id: 'r1', project_id: 'p123', type: 'relational', status: 'completed', created_at: new Date().toISOString() })
    listArtifacts.mockResolvedValue([
      { id: 'a1', request_id: 'r1', format: 'csv', storage_uri: 's3://bucket/obj.csv', size_bytes: 10, created_at: new Date().toISOString() },
    ])
    signArtifact.mockResolvedValue({ url: 'https://signed.example.com/obj.csv' })

    render(
      <TestProviders initialEntries={["/projects/p123/requests/r1"]} routes={withRoute('/projects/:projectId/requests/:requestId', <RequestDetailPage />)}>
        <div />
      </TestProviders>
    )

    // wait for artifacts to load
    const btn = await screen.findByRole('button', { name: 'Get Signed URL' })
    fireEvent.click(btn)

    await waitFor(() => expect(signArtifact).toHaveBeenCalledWith('r1', 'a1'))
    expect(openSpy).toHaveBeenCalledWith('https://signed.example.com/obj.csv', '_blank', 'noopener,noreferrer')
  })
})
