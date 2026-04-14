/**
 * Unit tests for HypothesisCards component
 * Validates: Requirements 3.2, 17.2
 */
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { HypothesisCards } from './HypothesisCards'
import type { Hypothesis } from '../types/benchmark'

const labels = {
  transferability: 'Transferability',
  confidence: 'Confidence',
  disclaimer: 'Boundary',
  filterCategory: 'Category',
  filterTransferability: 'Transferability',
  allCategories: 'All categories',
  allTransferability: 'All levels',
  evidence: 'Show evidence',
  noHypotheses: 'No hypotheses generated.',
}

function makeHypothesis(overrides: Partial<Hypothesis> = {}): Hypothesis {
  return {
    hypothesis_id: 'h1',
    title: 'Strong documentation drives adoption',
    category: 'docs',
    evidence: [{ type: 'signal', detail: 'Has quickstart guide', repo: 'owner/bench' }],
    transferability: 'high',
    caveats: [],
    confidence: 'high',
    ...overrides,
  }
}

const sampleHypotheses: Hypothesis[] = [
  makeHypothesis({ hypothesis_id: 'h1', title: 'Strong docs drive adoption', category: 'docs', transferability: 'high' }),
  makeHypothesis({ hypothesis_id: 'h2', title: 'CI improves reliability', category: 'ci', transferability: 'medium' }),
  makeHypothesis({ hypothesis_id: 'h3', title: 'License matters', category: 'legal', transferability: 'low' }),
]

describe('HypothesisCards', () => {
  describe('empty state', () => {
    it('shows no-hypotheses message when array is empty', () => {
      render(<HypothesisCards hypotheses={[]} labels={labels} />)
      expect(screen.getByText('No hypotheses generated.')).toBeInTheDocument()
    })
  })

  describe('default collapsed state (Requirement 3.2)', () => {
    it('evidence details are hidden by default', () => {
      render(<HypothesisCards hypotheses={[sampleHypotheses[0]]} labels={labels} />)
      const evidenceBtn = screen.getByRole('button', { name: 'Show evidence' })
      expect(evidenceBtn).toHaveAttribute('aria-expanded', 'false')
    })

    it('evidence content is not visible before expanding', () => {
      render(<HypothesisCards hypotheses={[sampleHypotheses[0]]} labels={labels} />)
      // The evidence detail text should not be visible
      expect(screen.queryByText('Has quickstart guide')).not.toBeVisible()
    })
  })

  describe('expand/collapse functionality (Requirement 17.2)', () => {
    it('expands evidence when button is clicked', () => {
      render(<HypothesisCards hypotheses={[sampleHypotheses[0]]} labels={labels} />)
      const evidenceBtn = screen.getByRole('button', { name: 'Show evidence' })
      fireEvent.click(evidenceBtn)
      expect(evidenceBtn).toHaveAttribute('aria-expanded', 'true')
    })

    it('shows evidence content after expanding', () => {
      render(<HypothesisCards hypotheses={[sampleHypotheses[0]]} labels={labels} />)
      const evidenceBtn = screen.getByRole('button', { name: 'Show evidence' })
      fireEvent.click(evidenceBtn)
      expect(screen.getByText('Has quickstart guide')).toBeVisible()
    })

    it('collapses evidence when button is clicked again', () => {
      render(<HypothesisCards hypotheses={[sampleHypotheses[0]]} labels={labels} />)
      const evidenceBtn = screen.getByRole('button', { name: 'Show evidence' })
      fireEvent.click(evidenceBtn)
      fireEvent.click(evidenceBtn)
      expect(evidenceBtn).toHaveAttribute('aria-expanded', 'false')
    })

    it('each card has independent expand state', () => {
      render(<HypothesisCards hypotheses={sampleHypotheses} labels={labels} />)
      const buttons = screen.getAllByRole('button', { name: 'Show evidence' })
      // Expand first card only
      fireEvent.click(buttons[0])
      expect(buttons[0]).toHaveAttribute('aria-expanded', 'true')
      expect(buttons[1]).toHaveAttribute('aria-expanded', 'false')
    })
  })

  describe('filtering by transferability (Requirement 17.2)', () => {
    it('shows all hypotheses by default', () => {
      render(<HypothesisCards hypotheses={sampleHypotheses} labels={labels} />)
      expect(screen.getByText('Strong docs drive adoption')).toBeInTheDocument()
      expect(screen.getByText('CI improves reliability')).toBeInTheDocument()
      expect(screen.getByText('License matters')).toBeInTheDocument()
    })

    it('filters to show only high transferability', () => {
      render(<HypothesisCards hypotheses={sampleHypotheses} labels={labels} />)
      const transferFilter = screen.getByLabelText('Transferability')
      fireEvent.change(transferFilter, { target: { value: 'high' } })
      expect(screen.getByText('Strong docs drive adoption')).toBeInTheDocument()
      expect(screen.queryByText('CI improves reliability')).not.toBeInTheDocument()
      expect(screen.queryByText('License matters')).not.toBeInTheDocument()
    })

    it('filters to show only medium transferability', () => {
      render(<HypothesisCards hypotheses={sampleHypotheses} labels={labels} />)
      const transferFilter = screen.getByLabelText('Transferability')
      fireEvent.change(transferFilter, { target: { value: 'medium' } })
      expect(screen.queryByText('Strong docs drive adoption')).not.toBeInTheDocument()
      expect(screen.getByText('CI improves reliability')).toBeInTheDocument()
    })

    it('filters to show only low transferability', () => {
      render(<HypothesisCards hypotheses={sampleHypotheses} labels={labels} />)
      const transferFilter = screen.getByLabelText('Transferability')
      fireEvent.change(transferFilter, { target: { value: 'low' } })
      expect(screen.queryByText('Strong docs drive adoption')).not.toBeInTheDocument()
      expect(screen.getByText('License matters')).toBeInTheDocument()
    })

    it('shows no-hypotheses message when filter matches nothing', () => {
      const singleHigh = [makeHypothesis({ hypothesis_id: 'h1', transferability: 'high' })]
      render(<HypothesisCards hypotheses={singleHigh} labels={labels} />)
      const transferFilter = screen.getByLabelText('Transferability')
      fireEvent.change(transferFilter, { target: { value: 'low' } })
      expect(screen.getByText('No hypotheses generated.')).toBeInTheDocument()
    })
  })

  describe('category filtering', () => {
    it('filters by category', () => {
      render(<HypothesisCards hypotheses={sampleHypotheses} labels={labels} />)
      const categoryFilter = screen.getByLabelText('Category')
      fireEvent.change(categoryFilter, { target: { value: 'ci' } })
      expect(screen.queryByText('Strong docs drive adoption')).not.toBeInTheDocument()
      expect(screen.getByText('CI improves reliability')).toBeInTheDocument()
    })
  })

  describe('transferability display', () => {
    it('shows transferability label on each card', () => {
      render(<HypothesisCards hypotheses={[sampleHypotheses[0]]} labels={labels} />)
      expect(screen.getByLabelText('Transferability: high')).toBeInTheDocument()
    })

    it('shows caveats when present', () => {
      const withCaveats = makeHypothesis({
        hypothesis_id: 'hc',
        caveats: ['Only applies to open source projects'],
      })
      render(<HypothesisCards hypotheses={[withCaveats]} labels={labels} />)
      const evidenceBtn = screen.getByRole('button', { name: 'Show evidence' })
      fireEvent.click(evidenceBtn)
      expect(screen.getByText('Only applies to open source projects')).toBeInTheDocument()
    })
  })
})
