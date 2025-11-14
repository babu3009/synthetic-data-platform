import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, beforeEach, expect, vi } from 'vitest'
import type { Mock } from 'vitest'
import { TestProviders, withRoute } from './utils/TestProviders'
import FlatPreviewPage from '../pages/flat_preview_page'
import * as flatSvc from '../services/flat'

vi.mock('../services/flat', async () => {
  const mod = await vi.importActual<typeof import('../services/flat')>('../services/flat')
  return {
    ...mod,
    flatPreview: vi.fn(),
  }
})

describe('FlatPreviewPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders preview table after successful run', async () => {
    (flatSvc.flatPreview as unknown as Mock).mockResolvedValue({
      rows: [
        { id: 1, email: 'a@example.com', age: '18-29' },
        { id: 2, email: 'b@example.com', age: '30-44' },
      ],
    })

    render(
      <TestProviders initialEntries={["/flat/preview"]} routes={withRoute('/flat/preview', <FlatPreviewPage />)}>
        <div />
      </TestProviders>
    )

    expect(await screen.findByRole('heading', { name: 'Flat Preview' })).toBeInTheDocument()
    expect(screen.getByText('No rows yet. Click Preview to generate.')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Preview' }))

    // Headers appear
    expect(await screen.findByRole('columnheader', { name: 'id' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'email' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'age' })).toBeInTheDocument()

    // Two data rows should render
    const bodyRows = screen.getAllByRole('row').slice(1) // drop header
    expect(bodyRows.length).toBe(2)

    // A sample cell value
    expect(screen.getByText('a@example.com')).toBeInTheDocument()
  })

  it('disables Preview on invalid JSON/schema and re-enables after fix', async () => {
    (flatSvc.flatPreview as unknown as Mock).mockResolvedValue({ rows: [] })

    render(
      <TestProviders initialEntries={["/flat/preview"]} routes={withRoute('/flat/preview', <FlatPreviewPage />)}>
        <div />
      </TestProviders>
    )

    const textarea = await screen.findByRole('textbox', { name: 'Schema JSON' })
    const previewBtn = screen.getByRole('button', { name: 'Preview' })
    
    // Invalid JSON should disable the button and show inline error
    await userEvent.clear(textarea)
    await userEvent.type(textarea, 'not-json')
    expect(previewBtn).toBeDisabled()
    expect(await screen.findByRole('alert')).toHaveTextContent(/invalid json/i)

    // Fix JSON but provide invalid schema to still disable
  await userEvent.clear(textarea)
  fireEvent.change(textarea, { target: { value: '{"foo":1}' } })
    expect(previewBtn).toBeDisabled()
    expect(await screen.findByRole('alert')).toHaveTextContent(/columns/i)

    // Provide minimal valid schema -> button enabled
  await userEvent.clear(textarea)
  fireEvent.change(textarea, { target: { value: '{"columns":[{"name":"id","provider":{"type":"sequence"}}]}' } })
    expect(previewBtn).toBeEnabled()
  })
})
