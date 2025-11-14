import { render, screen } from '@testing-library/react'
import { TestProviders, withRoute } from './utils/TestProviders'
import SourcesListPage from '../pages/projects/sources_list_page'
import SourceSchemaPage from '../pages/projects/source_schema_page'
import SourceDagPage from '../pages/projects/source_dag_page'
import * as sourcesSvc from '../services/sources'
import { describe, it, beforeEach, expect, vi } from 'vitest'
import type { Mock } from 'vitest'

vi.mock('../services/sources', async () => {
  const mod = await vi.importActual<typeof import('../services/sources')>('../services/sources')
  return {
    ...mod,
    listSources: vi.fn(),
    getSourceSchema: vi.fn(),
    getSourceDag: vi.fn(),
  }
})

describe('Sources pages integration', () => {
  // userEvent reserved for potential future interactions
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders sources list with items and navigation links', async () => {
  (sourcesSvc.listSources as unknown as Mock).mockResolvedValue([
      { id: 'src-1', kind: 'ddl', created_at: new Date().toISOString(), tables_count: 3 },
      { id: 'src-2', kind: 'json', created_at: new Date().toISOString(), tables_count: 1 },
    ])

    render(
      <TestProviders initialEntries={["/projects/p123/sources"]} routes={withRoute('/projects/:projectId/sources', <SourcesListPage />)}>
        <div />
      </TestProviders>
    )

    expect(await screen.findByRole('heading', { name: 'Sources' })).toBeInTheDocument()
    expect(screen.getAllByRole('row').length).toBeGreaterThan(2) // header + rows
    const schemaLinks = screen.getAllByRole('link', { name: 'Schema' })
    expect(schemaLinks.length).toBe(2)
  })

  it('renders source schema with tables and columns', async () => {
  (sourcesSvc.getSourceSchema as unknown as Mock).mockResolvedValue({
      schema: {
        tables: [
          { name: 'patients', columns: [{ name: 'id', dtype: 'uuid', nullable: false }], pk: ['id'] },
          { name: 'visits', columns: [{ name: 'patient_id', dtype: 'uuid', nullable: false }], pk: [] },
        ],
      },
    })

    render(
      <TestProviders initialEntries={["/projects/p123/sources/src-1/schema"]} routes={withRoute('/projects/:projectId/sources/:sourceId/schema', <SourceSchemaPage />)}>
        <div />
      </TestProviders>
    )

    expect(await screen.findByRole('heading', { name: 'Source Schema' })).toBeInTheDocument()
    expect(screen.getByText('patients')).toBeInTheDocument()
    expect(screen.getByText('visits')).toBeInTheDocument()
  expect(screen.getAllByText('id').length).toBeGreaterThan(0)
  })

  it('renders source dag graph', async () => {
  (sourcesSvc.getSourceDag as unknown as Mock).mockResolvedValue({
      nodes: ['patients', 'visits'],
      edges: [['visits', 'patients']],
    })

    render(
      <TestProviders initialEntries={["/projects/p123/sources/src-1/dag"]} routes={withRoute('/projects/:projectId/sources/:sourceId/dag', <SourceDagPage />)}>
        <div />
      </TestProviders>
    )

    expect(await screen.findByRole('heading', { name: 'Source DAG' })).toBeInTheDocument()
    // ReactFlow renders nodes with labels; query by text
    expect(screen.getByText('patients')).toBeInTheDocument()
    expect(screen.getByText('visits')).toBeInTheDocument()
  })
})
