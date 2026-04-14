/**
 * Unit tests for BenchmarkMatrix component
 * Validates: Requirements 2.3, 17.1, 17.3
 */
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { BenchmarkMatrix } from './BenchmarkMatrix'
import type { FeatureRow } from '../types/benchmark'

function makeRow(overrides: Partial<FeatureRow> = {}): FeatureRow {
  return {
    dimension_id: 'docs',
    label_key: 'docs',
    label: 'Documentation',
    cells: [
      { repo: 'owner/mine', level: 'weak', score: 0.3, raw: { has_readme: true } },
      { repo: 'owner/bench', level: 'strong', score: 0.9, raw: { has_readme: true, has_quickstart: true } },
    ],
    ...overrides,
  }
}

describe('BenchmarkMatrix', () => {
  describe('rendering with various matrix sizes', () => {
    it('renders a single row', () => {
      render(<BenchmarkMatrix rows={[makeRow()]} />)
      expect(screen.getByText('Documentation')).toBeInTheDocument()
    })

    it('renders two rows', () => {
      const rows = [
        makeRow({ dimension_id: 'docs', label: 'Documentation' }),
        makeRow({ dimension_id: 'ci', label: 'CI/CD', cells: [
          { repo: 'owner/mine', level: 'missing', score: 0, raw: {} },
          { repo: 'owner/bench', level: 'medium', score: 0.6, raw: { workflows: 3 } },
        ]}),
      ]
      render(<BenchmarkMatrix rows={rows} />)
      expect(screen.getByText('Documentation')).toBeInTheDocument()
      expect(screen.getByText('CI/CD')).toBeInTheDocument()
    })

    it('renders three rows (3 benchmarks)', () => {
      const rows = [
        makeRow({ dimension_id: 'docs', label: 'Documentation' }),
        makeRow({ dimension_id: 'ci', label: 'CI/CD' }),
        makeRow({ dimension_id: 'security', label: 'Security' }),
      ]
      render(<BenchmarkMatrix rows={rows} />)
      expect(screen.getByText('Documentation')).toBeInTheDocument()
      expect(screen.getByText('CI/CD')).toBeInTheDocument()
      expect(screen.getByText('Security')).toBeInTheDocument()
    })

    it('renders repo names in cells', () => {
      render(<BenchmarkMatrix rows={[makeRow()]} />)
      expect(screen.getByText('owner/mine')).toBeInTheDocument()
      expect(screen.getByText('owner/bench')).toBeInTheDocument()
    })
  })

  describe('color coding (Requirement 17.1)', () => {
    it('applies missing class for missing level', () => {
      const row = makeRow({ cells: [{ repo: 'r', level: 'missing', score: 0, raw: {} }] })
      render(<BenchmarkMatrix rows={[row]} />)
      const cell = screen.getByRole('gridcell', { name: /r Documentation/i })
      expect(cell).toHaveClass('compare-level-missing')
    })

    it('applies weak class for weak level', () => {
      const row = makeRow({ cells: [{ repo: 'r', level: 'weak', score: 0.2, raw: {} }] })
      render(<BenchmarkMatrix rows={[row]} />)
      const cell = screen.getByRole('gridcell', { name: /r Documentation/i })
      expect(cell).toHaveClass('compare-level-weak')
    })

    it('applies medium class for medium level', () => {
      const row = makeRow({ cells: [{ repo: 'r', level: 'medium', score: 0.5, raw: {} }] })
      render(<BenchmarkMatrix rows={[row]} />)
      const cell = screen.getByRole('gridcell', { name: /r Documentation/i })
      expect(cell).toHaveClass('compare-level-medium')
    })

    it('applies strong class for strong level', () => {
      const row = makeRow({ cells: [{ repo: 'r', level: 'strong', score: 0.9, raw: {} }] })
      render(<BenchmarkMatrix rows={[row]} />)
      const cell = screen.getByRole('gridcell', { name: /r Documentation/i })
      expect(cell).toHaveClass('compare-level-strong')
    })
  })

  describe('cell expand/collapse', () => {
    it('cells start collapsed', () => {
      render(<BenchmarkMatrix rows={[makeRow()]} />)
      const cells = screen.getAllByRole('gridcell')
      cells.forEach((cell) => {
        expect(cell).toHaveAttribute('aria-expanded', 'false')
      })
    })

    it('expands cell on click to show raw signals', () => {
      const row = makeRow({ cells: [{ repo: 'r', level: 'strong', score: 0.9, raw: { has_readme: true } }] })
      render(<BenchmarkMatrix rows={[row]} />)
      const cell = screen.getByRole('gridcell', { name: /r Documentation/i })
      fireEvent.click(cell)
      expect(cell).toHaveAttribute('aria-expanded', 'true')
      expect(screen.getByText('has_readme')).toBeInTheDocument()
    })

    it('shows empty label when raw signals are empty', () => {
      const row = makeRow({ cells: [{ repo: 'r', level: 'missing', score: 0, raw: {} }] })
      render(<BenchmarkMatrix rows={[row]} emptyLabel="No signals" />)
      const cell = screen.getByRole('gridcell', { name: /r Documentation/i })
      fireEvent.click(cell)
      expect(screen.getByText('No signals')).toBeInTheDocument()
    })
  })

  describe('keyboard navigation (Requirement 17.3)', () => {
    it('renders grid with role=grid', () => {
      render(<BenchmarkMatrix rows={[makeRow()]} />)
      expect(screen.getByRole('grid')).toBeInTheDocument()
    })

    it('cells have data-cell-index attributes for keyboard navigation', () => {
      render(<BenchmarkMatrix rows={[makeRow()]} />)
      const cells = screen.getAllByRole('gridcell')
      cells.forEach((cell, index) => {
        expect(cell).toHaveAttribute('data-cell-index', String(index))
      })
    })

    it('ArrowRight key is handled by the grid', () => {
      const rows = [makeRow()]
      render(<BenchmarkMatrix rows={rows} />)
      const grid = screen.getByRole('grid')
      const cells = screen.getAllByRole('gridcell')
      cells[0].focus()
      // Verify the grid handles keyboard events without throwing
      fireEvent.keyDown(cells[0], { key: 'ArrowRight' })
      expect(grid).toBeInTheDocument()
    })

    it('cells have role=gridcell', () => {
      render(<BenchmarkMatrix rows={[makeRow()]} />)
      const cells = screen.getAllByRole('gridcell')
      expect(cells.length).toBeGreaterThan(0)
    })
  })

  describe('labels', () => {
    it('uses custom score label', () => {
      render(<BenchmarkMatrix rows={[makeRow()]} scoreLabel="Rating" />)
      expect(screen.getAllByText(/Rating:/i).length).toBeGreaterThan(0)
    })

    it('uses default English labels when no language specified', () => {
      render(<BenchmarkMatrix rows={[makeRow()]} />)
      expect(screen.getAllByText(/Score:/i).length).toBeGreaterThan(0)
    })

    it('uses Chinese labels when language=zh', () => {
      render(<BenchmarkMatrix rows={[makeRow()]} language="zh" />)
      expect(screen.getAllByText(/评分:/i).length).toBeGreaterThan(0)
    })
  })
})
