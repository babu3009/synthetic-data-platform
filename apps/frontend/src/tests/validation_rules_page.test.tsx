import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, beforeEach, expect, vi } from 'vitest'
import { TestProviders, withRoute } from './utils/TestProviders'
import ValidationRulesPage from '../pages/projects/validation_rules_page'
import * as valSvc from '../services/validation'

vi.mock('../services/validation', () => ({
  validateRules: vi.fn(),
}))

const validateRules = valSvc.validateRules as unknown as ReturnType<typeof vi.fn>

describe('Validation Rules UI', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.clearAllMocks()
    // Ensure no cross-test leakage from persistence
    localStorage.clear()
  })

  it('adds a uniqueness rule and renders report', async () => {
    validateRules.mockResolvedValue({
      report: {
        sample: [
          { type: 'uniqueness', table: 'patients', checked: 100, violations: 0, violation_rate: 0 }
        ],
        final: []
      }
    })

    render(
      <TestProviders initialEntries={["/projects/p123/validation"]} routes={withRoute('/projects/:projectId/validation', <ValidationRulesPage />)}>
        <div />
      </TestProviders>
    )

    expect(await screen.findByRole('heading', { name: 'Validation Rules' })).toBeInTheDocument()

    // Add rule
    const select = screen.getByRole('combobox')
    fireEvent.change(select, { target: { value: 'uniqueness' } })
    // Fill fields
  const tblInputs = screen.getAllByLabelText('Uniqueness table') as HTMLInputElement[]
  fireEvent.change(tblInputs[0], { target: { value: 'patients' } })
  const colInputs = screen.getAllByLabelText('Uniqueness columns') as HTMLInputElement[]
  fireEvent.change(colInputs[0], { target: { value: 'id' } })

    fireEvent.click(screen.getByRole('button', { name: 'Run' }))

    await waitFor(() => expect(validateRules).toHaveBeenCalled())
    expect(await screen.findByText('patients')).toBeInTheDocument()
    expect(screen.getByText(/0\.00%|0%/)).toBeInTheDocument()
  })

  it('persists rules to localStorage and restores on remount', async () => {
    validateRules.mockResolvedValue({ report: { sample: [], final: [] } })
    const { unmount } = render(
      <TestProviders initialEntries={["/projects/p123/validation"]} routes={withRoute('/projects/:projectId/validation', <ValidationRulesPage />)}>
        <div />
      </TestProviders>
    )
    const select = await screen.findByRole('combobox')
    fireEvent.change(select, { target: { value: 'uniqueness' } })
  const tblInputs = screen.getAllByLabelText('Uniqueness table') as HTMLInputElement[]
  fireEvent.change(tblInputs[0], { target: { value: 'orders' } })
  const colInputs = screen.getAllByLabelText('Uniqueness columns') as HTMLInputElement[]
  fireEvent.change(colInputs[0], { target: { value: 'order_id' } })
    unmount()
    // remount
    render(
      <TestProviders initialEntries={["/projects/p123/validation"]} routes={withRoute('/projects/:projectId/validation', <ValidationRulesPage />)}>
        <div />
      </TestProviders>
    )
    expect(await screen.findByDisplayValue('orders')).toBeInTheDocument()
    expect(screen.getByDisplayValue('order_id')).toBeInTheDocument()
  })

  it('styles failing rows as table-danger', async () => {
    validateRules.mockResolvedValue({
      report: {
        sample: [
          { type: 'uniqueness', table: 'bad_table', checked: 10, violations: 2, violation_rate: 0.2 }
        ],
        final: []
      }
    })
    render(
      <TestProviders initialEntries={["/projects/p123/validation"]} routes={withRoute('/projects/:projectId/validation', <ValidationRulesPage />)}>
        <div />
      </TestProviders>
    )
  const select = await screen.findByRole('combobox')
  fireEvent.change(select, { target: { value: 'uniqueness' } })
  const inputs = screen.getAllByLabelText('Uniqueness table') as HTMLInputElement[]
  fireEvent.change(inputs[0], { target: { value: 'bad_table' } })
  const cols = screen.getAllByLabelText('Uniqueness columns') as HTMLInputElement[]
  fireEvent.change(cols[0], { target: { value: 'id' } })
    fireEvent.click(screen.getByRole('button', { name: /Run/ }))
    await waitFor(() => expect(validateRules).toHaveBeenCalled())
    const row = screen.getByText('bad_table').closest('tr')!
    expect(row.className).toMatch(/table-danger/)
  })
})
