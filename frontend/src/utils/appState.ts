import { githubLoginEquals } from './githubLogin'
import type { ContentLanguage, ResumeProject } from '../context/AppContext'
import type { RepositoryAnalysisPayload } from './resumeProjects'

export function getGenerateRequestKey(username: string, lang: ContentLanguage): string {
  return `${username.trim().toLowerCase()}:${lang}`
}

export function toggleResumeProjectsForUser(
  projects: ResumeProject[],
  project: ResumeProject,
  maxPerUser: number,
): ResumeProject[] {
  const exists = projects.some(
    (item) => githubLoginEquals(item.user, project.user) && item.repoName === project.repoName,
  )
  if (exists) {
    return projects.filter(
      (item) => !(githubLoginEquals(item.user, project.user) && item.repoName === project.repoName),
    )
  }

  const sameUserProjects = projects.filter((item) => githubLoginEquals(item.user, project.user))
  const otherProjects = projects.filter((item) => !githubLoginEquals(item.user, project.user))
  const nextForUser = [project, ...sameUserProjects].slice(0, maxPerUser)
  return [...otherProjects, ...nextForUser]
}

export function upsertRepoAnalysisCache(
  cache: Map<string, RepositoryAnalysisPayload>,
  key: string,
  payload: RepositoryAnalysisPayload,
  limit = 50,
): Map<string, RepositoryAnalysisPayload> {
  const next = new Map(cache)
  if (next.has(key)) next.delete(key)
  next.set(key, payload)

  while (next.size > limit) {
    const oldestKey = next.keys().next().value
    if (oldestKey === undefined) break
    next.delete(oldestKey)
  }

  return next
}
