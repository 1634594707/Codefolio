/**
 * Unit tests for ActionList component
 * Validates: Requirements 10.3, 10.4
 */
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, beforeEach } from 'vitest'
import { ActionList } from './ActionList'
import type { ActionItem } from '../types/benchmark'

const labels = {
  sortBy: 'Sort by',
  filterBy: 'Filter by',
  sortPriority: 'Priority',
  sortEffort: 'Effort',
  sortImpact: 'Impact',
  allDimensions: 'All dimensions',
  quickWin: 'Quick win',
  complete: 'Mark complete',
  timeline7d: '7 day focus',
  timeline30d: '30 day plan',
  timeline90d: '90 day backlog',
  noActions: 'No action items generated.',
}

function makeAction(overrides: Partial<ActionItem> = {}): ActionItem {
  return {
    action_id: 'a1',
    dimension: 'docs',
    title: 'Add README',
    rationale: 'Improves discoverability',
    effort: 'S',
    impact: 5,
    priority_score: 4.5,
    checklist: ['Write intro', 'Add badges'],
    suggested_deadline: 'within 7 days',
    ...overrides,
  }
}

const sampleActions: ActionItem[] = [
  makeAction({ action_id: 'a1', dimension: 'docs', title: 'Add README', effort: 'S', impact: 5, priority_score: 4.5, suggested_deadline: 'within 7 days' }),
  makeAction({ action_id: 'a2', dimension: 'ci', title: 'Add CI workflow', effort: 'M', impact: 3, priority_score: 3.0, suggested_deadline: 'within 30 days' }),
  makeAction({ action_id: 'a3', dimension: 'docs', title: 'Add contributing guide', effort: 'L', impact: 2, priority_score: 1.5, suggested_deadline: 'within 90 days' }),
]

describe('ActionList', () => {
  describe('empty state', () => {
    it('shows no-actions message when actions array is empty', () => {
      render(<ActionList actions={[]} language="en" labels={labels} />)
      expect(screen.getByText('No action items generated.')).toBeInTheDocument()
    })
  })

  describe('rendering', () => {
    it('renders action titles', () => {
      render(<ActionList actions={sampleActions} language="en" labels={labels} />)
      expect(screen.getByText('Add README')).toBeInTheDocument()
      expect(screen.getByText('Add CI workflow')).toBeInTheDocument()
    })

    it('renders sort and filter controls', () => {
      render(<ActionList actions={sampleActions} language="en" labels={labels} />)
      expect(screen.getByLabelText('Sort by')).toBeInTheDocument()
      expect(screen.getByLabelText('Filter by')).toBeInTheDocument()
    })

    it('renders timeline group headers', () => {
      render(<ActionList actions={sampleActions} language="en" labels={labels} />)
      expect(screen.getByText('7 day focus')).toBeInTheDocument()
      expect(screen.getByText('30 day plan')).toBeInTheDocument()
      expect(screen.getByText('90 day backlog')).toBeInTheDocument()
    })
  })

  describe('quick win highlighting (Requirement 10.4)', () => {
    it('marks action as quick win when effort=S and impact>=4', () => {
      const quickWinAction = makeAction({ action_id: 'qw1', effort: 'S', impact: 4, suggested_deadline: 'within 7 days' })
      render(<ActionList actions={[quickWinAction]} language="en" labels={labels} />)
      expect(screen.getByLabelText('Quick win')).toBeInTheDocument()
    })

    it('does not mark as quick win when effort=M even with high impact', () => {
      const notQuickWin = makeAction({ action_id: 'nqw1', effort: 'M', impact: 5, suggested_deadline: 'within 7 days' })
      render(<ActionList actions={[notQuickWin]} language="en" labels={labels} />)
      expect(screen.queryByLabelText('Quick win')).not.toBeInTheDocument()
    })

    it('does not mark as quick win when effort=S but impact=3', () => {
      const notQuickWin = makeAction({ action_id: 'nqw2', effort: 'S', impact: 3, suggested_deadline: 'within 7 days' })
      render(<ActionList actions={[notQuickWin]} language="en" labels={labels} />)
      expect(screen.queryByLabelText('Quick win')).not.toBeInTheDocument()
    })

    it('marks as quick win when effort=S and impact=5', () => {
      const quickWin = makeAction({ action_id: 'qw2', effort: 'S', impact: 5, suggested_deadline: 'within 7 days' })
      render(<ActionList actions={[quickWin]} language="en" labels={labels} />)
      expect(screen.getByLabelText('Quick win')).toBeInTheDocument()
    })
  })

  describe('sorting (Requirement 10.3)', () => {
    it('defaults to priority sort', () => {
      render(<ActionList actions={sampleActions} language="en" labels={labels} />)
      const sortSelect = screen.getByLabelText('Sort by') as HTMLSelectElement
      expect(sortSelect.value).toBe('priority')
    })

    it('can switch to effort sort', () => {
      render(<ActionList actions={sampleActions} language="en" labels={labels} />)
      const sortSelect = screen.getByLabelText('Sort by')
      fireEvent.change(sortSelect, { target: { value: 'effort' } })
      expect((sortSelect as HTMLSelectElement).value).toBe('effort')
    })

    it('can switch to impact sort', () => {
      render(<ActionList actions={sampleActions} language="en" labels={labels} />)
      const sortSelect = screen.getByLabelText('Sort by')
      fireEvent.change(sortSelect, { target: { value: 'impact' } })
      expect((sortSelect as HTMLSelectElement).value).toBe('impact')
    })
  })

  describe('filtering by dimension (Requirement 10.3)', () => {
    it('shows all dimensions option by default', () => {
      render(<ActionList actions={sampleActions} language="en" labels={labels} />)
      const filterSelect = screen.getByLabelText('Filter by') as HTMLSelectElement
      expect(filterSelect.value).toBe('all')
    })

    it('populates dimension options from actions', () => {
      render(<ActionList actions={sampleActions} language="en" labels={labels} />)
      expect(screen.getByRole('option', { name: 'docs' })).toBeInTheDocument()
      expect(screen.getByRole('option', { name: 'ci' })).toBeInTheDocument()
    })

    it('filters to show only selected dimension', () => {
      render(<ActionList actions={sampleActions} language="en" labels={labels} />)
      const filterSelect = screen.getByLabelText('Filter by')
      fireEvent.change(filterSelect, { target: { value: 'ci' } })
      // ci action should be visible
      expect(screen.getByText('Add CI workflow')).toBeInTheDocument()
      // docs actions should be hidden
      expect(screen.queryByText('Add README')).not.toBeInTheDocument()
    })
  })

  describe('group collapse/expand', () => {
    it('groups are expanded by default', () => {
      render(<ActionList actions={sampleActions} language="en" labels={labels} />)
      const toggleBtn = screen.getAllByRole('button').find(
        (btn) => btn.getAttribute('aria-expanded') === 'true'
      )
      expect(toggleBtn).toBeTruthy()
    })

    it('collapses a group when toggle is clicked', () => {
      render(<ActionList actions={[sampleActions[0]]} language="en" labels={labels} />)
      // Find the 7d group toggle button
      const toggleBtn = screen.getByRole('button', { name: /7 day focus/i })
      expect(toggleBtn).toHaveAttribute('aria-expanded', 'true')
      fireEvent.click(toggleBtn)
      expect(toggleBtn).toHaveAttribute('aria-expanded', 'false')
    })
  })
})
