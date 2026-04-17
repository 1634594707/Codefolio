/**
 * Unit tests for Suggestion UI in CompareRepos
 * Task 26.2 - Validates: Requirements 7.1, 7.6
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import axios from 'axios'
import { CompareRepos } from './CompareRepos'

const REPO_PLACEHOLDER = 'owner/repo…'

vi.mock('../context', () => ({
  useApp: () => ({
    saveBenchmarkWorkspaceEntry: vi.fn(),
  }),
}))

vi.mock('axios', async () => {
  const actual = await vi.importActual<typeof import('axios')>('axios')
  return {
    default: {
      ...actual.default,
      post: vi.fn().mockRejectedValue(new Error('Network error')),
      get: vi.fn(),
      isAxiosError: actual.default.isAxiosError,
    },
  }
})

const mockedAxios = axios as unknown as {
  get: ReturnType<typeof vi.fn>
  post: ReturnType<typeof vi.fn>
  isAxiosError: typeof axios.isAxiosError
}

function renderCompareRepos(initialEntries = ['/']) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <CompareRepos language="en" />
    </MemoryRouter>,
  )
}

describe('Suggestion UI (Requirements 7.1, 7.6)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockedAxios.post.mockRejectedValue(new Error('Network error'))
  })

  describe('Suggest Benchmarks button', () => {
    it('renders the "Suggest Benchmarks" button', () => {
      renderCompareRepos()
      expect(screen.getByRole('button', { name: 'Suggest Benchmarks' })).toBeInTheDocument()
    })

    it('button is enabled when page loads', () => {
      renderCompareRepos()
      expect(screen.getByRole('button', { name: 'Suggest Benchmarks' })).not.toBeDisabled()
    })

    it('shows error when clicking suggest without a valid mine repo', async () => {
      renderCompareRepos()
      fireEvent.click(screen.getByRole('button', { name: 'Suggest Benchmarks' }))
      expect(screen.getByText('Use a valid GitHub repository like owner/repo.')).toBeInTheDocument()
    })
  })

  describe('suggestions panel display', () => {
    it('shows suggestions panel after clicking suggest with valid mine repo', async () => {
      mockedAxios.get.mockResolvedValueOnce({
        data: {
          suggestions: [
            { full_name: 'org/repo-a', reason_code: 'same_language', reason_params: {}, stars: 1200 },
            { full_name: 'org/repo-b', reason_code: 'shared_topic', reason_params: {}, stars: 800 },
          ],
        },
      })

      renderCompareRepos()
      const mineInput = screen.getAllByPlaceholderText(REPO_PLACEHOLDER)[0]
      fireEvent.change(mineInput, { target: { value: 'owner/myrepo' } })
      fireEvent.click(screen.getByRole('button', { name: 'Suggest Benchmarks' }))

      await waitFor(() => {
        expect(screen.getByText('org/repo-a')).toBeInTheDocument()
        expect(screen.getByText('org/repo-b')).toBeInTheDocument()
      })
    })

    it('displays reason codes for each suggestion', async () => {
      mockedAxios.get.mockResolvedValueOnce({
        data: {
          suggestions: [
            { full_name: 'org/repo-a', reason_code: 'same_language', reason_params: {}, stars: 1200 },
            { full_name: 'org/repo-b', reason_code: 'shared_topic', reason_params: {}, stars: 800 },
          ],
        },
      })

      renderCompareRepos()
      const mineInput = screen.getAllByPlaceholderText(REPO_PLACEHOLDER)[0]
      fireEvent.change(mineInput, { target: { value: 'owner/myrepo' } })
      fireEvent.click(screen.getByRole('button', { name: 'Suggest Benchmarks' }))

      await waitFor(() => {
        expect(screen.getByText('same_language')).toBeInTheDocument()
        expect(screen.getByText('shared_topic')).toBeInTheDocument()
      })
    })

    it('displays star counts for each suggestion', async () => {
      mockedAxios.get.mockResolvedValueOnce({
        data: {
          suggestions: [
            { full_name: 'org/repo-a', reason_code: 'same_language', reason_params: {}, stars: 1200 },
          ],
        },
      })

      renderCompareRepos()
      const mineInput = screen.getAllByPlaceholderText(REPO_PLACEHOLDER)[0]
      fireEvent.change(mineInput, { target: { value: 'owner/myrepo' } })
      fireEvent.click(screen.getByRole('button', { name: 'Suggest Benchmarks' }))

      await waitFor(() => {
        expect(screen.getByText('★1,200')).toBeInTheDocument()
      })
    })
  })

  describe('empty state', () => {
    it('shows "No suggestions found" when API returns empty list', async () => {
      mockedAxios.get.mockResolvedValueOnce({ data: { suggestions: [] } })

      renderCompareRepos()
      const mineInput = screen.getAllByPlaceholderText(REPO_PLACEHOLDER)[0]
      fireEvent.change(mineInput, { target: { value: 'owner/myrepo' } })
      fireEvent.click(screen.getByRole('button', { name: 'Suggest Benchmarks' }))

      await waitFor(() => {
        expect(screen.getByText('No suggestions found.')).toBeInTheDocument()
      })
    })
  })

  describe('error state', () => {
    it('shows error message when API call fails', async () => {
      const axiosError = Object.assign(new Error('Request failed'), {
        isAxiosError: true,
        response: { data: { detail: { message: 'Failed to fetch suggestions.' } } },
      })
      mockedAxios.get.mockRejectedValueOnce(axiosError)
      mockedAxios.isAxiosError = vi.fn().mockReturnValue(true) as unknown as typeof axios.isAxiosError

      renderCompareRepos()
      const mineInput = screen.getAllByPlaceholderText(REPO_PLACEHOLDER)[0]
      fireEvent.change(mineInput, { target: { value: 'owner/myrepo' } })
      fireEvent.click(screen.getByRole('button', { name: 'Suggest Benchmarks' }))

      await waitFor(() => {
        expect(screen.getByText('Failed to fetch suggestions.')).toBeInTheDocument()
      })
    })
  })

  describe('Add suggestion functionality', () => {
    it('clicking "Add" adds the suggestion to benchmark inputs', async () => {
      mockedAxios.get.mockResolvedValueOnce({
        data: {
          suggestions: [
            { full_name: 'org/repo-a', reason_code: 'same_language', reason_params: {}, stars: 1200 },
          ],
        },
      })

      renderCompareRepos()
      const mineInput = screen.getAllByPlaceholderText(REPO_PLACEHOLDER)[0]
      fireEvent.change(mineInput, { target: { value: 'owner/myrepo' } })
      fireEvent.click(screen.getByRole('button', { name: 'Suggest Benchmarks' }))

      await waitFor(() => {
        expect(screen.getByText('org/repo-a')).toBeInTheDocument()
      })

      // Click the Add button for the suggestion
      const addButtons = screen.getAllByRole('button', { name: 'Add' })
      fireEvent.click(addButtons[0])

      // The suggestion panel should close and the benchmark input should be populated
      await waitFor(() => {
        const inputs = screen.getAllByPlaceholderText(REPO_PLACEHOLDER)
        const values = inputs.map((input) => (input as HTMLInputElement).value)
        expect(values).toContain('org/repo-a')
      })
    })

    it('hides suggestions panel after adding a suggestion', async () => {
      mockedAxios.get.mockResolvedValueOnce({
        data: {
          suggestions: [
            { full_name: 'org/repo-a', reason_code: 'same_language', reason_params: {}, stars: 1200 },
          ],
        },
      })

      renderCompareRepos()
      const mineInput = screen.getAllByPlaceholderText(REPO_PLACEHOLDER)[0]
      fireEvent.change(mineInput, { target: { value: 'owner/myrepo' } })
      fireEvent.click(screen.getByRole('button', { name: 'Suggest Benchmarks' }))

      await waitFor(() => {
        expect(screen.getByText('org/repo-a')).toBeInTheDocument()
      })

      const addButtons = screen.getAllByRole('button', { name: 'Add' })
      fireEvent.click(addButtons[0])

      await waitFor(() => {
        expect(screen.queryByText('org/repo-a')).not.toBeInTheDocument()
      })
    })

    it('"Add" button is disabled when 3 benchmarks are already present', async () => {
      mockedAxios.get.mockResolvedValueOnce({
        data: {
          suggestions: [
            { full_name: 'org/repo-d', reason_code: 'same_language', reason_params: {}, stars: 500 },
          ],
        },
      })

      renderCompareRepos()
      const inputs = screen.getAllByPlaceholderText(REPO_PLACEHOLDER)
      fireEvent.change(inputs[0], { target: { value: 'owner/myrepo' } })
      // Fill 3 benchmark slots
      fireEvent.change(inputs[1], { target: { value: 'org/bench1' } })
      fireEvent.click(screen.getByRole('button', { name: 'Add benchmark' }))
      const inputs2 = screen.getAllByPlaceholderText(REPO_PLACEHOLDER)
      fireEvent.change(inputs2[2], { target: { value: 'org/bench2' } })
      fireEvent.click(screen.getByRole('button', { name: 'Add benchmark' }))
      const inputs3 = screen.getAllByPlaceholderText(REPO_PLACEHOLDER)
      fireEvent.change(inputs3[3], { target: { value: 'org/bench3' } })

      fireEvent.click(screen.getByRole('button', { name: 'Suggest Benchmarks' }))

      await waitFor(() => {
        expect(screen.getByText('org/repo-d')).toBeInTheDocument()
      })

      const addButtons = screen.getAllByRole('button', { name: 'Add' })
      expect(addButtons[0]).toBeDisabled()
    })

    it('"Add" button is disabled when suggestion is already in benchmark inputs', async () => {
      mockedAxios.get.mockResolvedValueOnce({
        data: {
          suggestions: [
            { full_name: 'org/bench1', reason_code: 'same_language', reason_params: {}, stars: 500 },
          ],
        },
      })

      renderCompareRepos()
      const inputs = screen.getAllByPlaceholderText(REPO_PLACEHOLDER)
      fireEvent.change(inputs[0], { target: { value: 'owner/myrepo' } })
      fireEvent.change(inputs[1], { target: { value: 'org/bench1' } })

      fireEvent.click(screen.getByRole('button', { name: 'Suggest Benchmarks' }))

      await waitFor(() => {
        expect(screen.getByText('org/bench1')).toBeInTheDocument()
      })

      const addButtons = screen.getAllByRole('button', { name: 'Add' })
      expect(addButtons[0]).toBeDisabled()
    })
  })

  describe('loading state', () => {
    it('shows loading text while fetching suggestions', async () => {
      // Never resolves during this test
      mockedAxios.get.mockReturnValueOnce(new Promise(() => {}))

      renderCompareRepos()
      const mineInput = screen.getAllByPlaceholderText(REPO_PLACEHOLDER)[0]
      fireEvent.change(mineInput, { target: { value: 'owner/myrepo' } })
      fireEvent.click(screen.getByRole('button', { name: /suggest/i }))

      // Button text changes to loading state
      expect(screen.getByRole('button', { name: 'Finding suggestions…' })).toBeInTheDocument()
    })
  })
})
