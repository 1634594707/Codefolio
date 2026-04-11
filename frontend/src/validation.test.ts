import { describe, expect, it } from 'vitest'
import {
  normalizeGitHubUsernameInput,
  splitGitHubUsernameInputs,
  validateGitHubUsername,
} from './utils/githubInput'

describe('GitHub input normalization', () => {
  it('accepts plain usernames', () => {
    expect(validateGitHubUsername('torvalds')).toMatchObject({ valid: true, username: 'torvalds' })
  })

  it('accepts @usernames', () => {
    expect(validateGitHubUsername('@torvalds')).toMatchObject({ valid: true, username: 'torvalds' })
  })

  it('accepts profile URLs', () => {
    expect(validateGitHubUsername('https://github.com/torvalds')).toMatchObject({
      valid: true,
      username: 'torvalds',
    })
  })

  it('accepts repository URLs and extracts the owner', () => {
    expect(validateGitHubUsername('https://github.com/torvalds/linux')).toMatchObject({
      valid: true,
      username: 'torvalds',
    })
  })

  it('accepts github.com links without protocol', () => {
    expect(normalizeGitHubUsernameInput('github.com/gaearon/react-hot-loader')).toBe('gaearon')
  })

  it('rejects invalid usernames after normalization', () => {
    expect(validateGitHubUsername('https://github.com/user_name/project')).toMatchObject({
      valid: false,
      message: 'invalid',
      username: 'user_name',
    })
  })
})

describe('GitHub compare input splitting', () => {
  it('splits comma and whitespace separated usernames', () => {
    expect(splitGitHubUsernameInputs('torvalds, gaearon openai')).toEqual([
      'torvalds',
      'gaearon',
      'openai',
    ])
  })

  it('normalizes links and @mentions while splitting', () => {
    expect(
      splitGitHubUsernameInputs('@torvalds https://github.com/gaearon/react-hot-loader github.com/openai/openai-node'),
    ).toEqual(['torvalds', 'gaearon', 'openai'])
  })
})
