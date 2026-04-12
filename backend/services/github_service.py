"""
GitHub Service Module
"""
import asyncio
import base64
import httpx
import logging
import re
from datetime import datetime, timezone
from typing import Dict, Any
from models import ContributionDay, Contributions, Repository, UserData
from config import settings
from utils.redis_client import redis_client
from cache_keys import github_user_cache_key, github_user_cache_keys_to_clear, repository_profile_cache_key

logger = logging.getLogger(__name__)

README_CANDIDATE_ALIASES = [
    "readmeMd",
    "readmeLowerMd",
    "readmeRst",
    "readmeTxt",
    "readmePlain",
    "docsReadme",
]

NESTED_TREE_ALIASES = [
    "srcTree",
    "appTree",
    "packagesTree",
    "backendTree",
    "frontendTree",
    "libTree",
    "cmdTree",
    "internalTree",
]

README_MAX_CHARS = 3200
README_SECTION_LIMIT = 6

BADGE_LINE_PATTERN = re.compile(r"^\s*(?:\[[^\]]*\]\([^)]+\)\s*)+$")
MARKDOWN_IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\([^)]+\)")
HTML_IMAGE_PATTERN = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
HTML_COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.DOTALL)
MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\([^)]+\)")
INLINE_CODE_PATTERN = re.compile(r"`([^`]+)`")
TOC_HEADING_PATTERN = re.compile(r"^(#{1,6}\s*)?(table of contents|toc|目录)\s*$", re.IGNORECASE)
TOC_LIST_ITEM_PATTERN = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+\[.*?\]\(#.*\)\s*$", re.IGNORECASE)
NOISE_HEADING_PATTERN = re.compile(
    r"^(#{1,6}\s*)?(installation|setup|getting started|usage|quick start|quickstart|license|contributing|faq|acknowledg(?:e)?ments?)\s*$",
    re.IGNORECASE,
)
USEFUL_HEADING_PATTERN = re.compile(
    r"^(#{1,6}\s*)?(overview|about|features?|highlights?|architecture|design|tech stack|stack|project structure|modules?|components?|api|workflow|demo|results?|背景|简介|特性|亮点|架构|技术栈|项目结构|模块|组件|工作流|效果|结果)\s*$",
    re.IGNORECASE,
)


class GitHubService:
    """Service for fetching and normalizing GitHub user data via GraphQL API"""
    
    def __init__(self):
        self.api_url = "https://api.github.com/graphql"
        self.rest_api_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github+json",
        }

    async def fetch_repository_profile(self, full_name: str) -> Dict[str, Any]:
        normalized_full_name = full_name.strip().lower()
        cache_key = repository_profile_cache_key(normalized_full_name)
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for repository: {normalized_full_name}")
            return cached_data

        owner, repo = normalized_full_name.split("/", 1)
        logger.info(f"Cache miss for repository: {normalized_full_name}, fetching from GitHub API")

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                repo_response, root_response, workflows_response, issue_templates_response, readme_response = await asyncio.gather(
                    client.get(f"{self.rest_api_url}/repos/{owner}/{repo}", headers=self.headers),
                    client.get(f"{self.rest_api_url}/repos/{owner}/{repo}/contents", headers=self.headers),
                    client.get(f"{self.rest_api_url}/repos/{owner}/{repo}/contents/.github/workflows", headers=self.headers),
                    client.get(f"{self.rest_api_url}/repos/{owner}/{repo}/contents/.github/ISSUE_TEMPLATE", headers=self.headers),
                    client.get(f"{self.rest_api_url}/repos/{owner}/{repo}/readme", headers=self.headers),
                )

                repo_response.raise_for_status()
                repo_payload = repo_response.json()

                root_entries = root_response.json() if root_response.status_code == 200 else []
                workflow_entries = workflows_response.json() if workflows_response.status_code == 200 else []
                issue_template_entries = issue_templates_response.json() if issue_templates_response.status_code == 200 else []
                readme_payload = readme_response.json() if readme_response.status_code == 200 else None

                profile = self._normalize_repository_profile(
                    repo_payload=repo_payload,
                    root_entries=root_entries if isinstance(root_entries, list) else [],
                    workflow_entries=workflow_entries if isinstance(workflow_entries, list) else [],
                    issue_template_entries=issue_template_entries if isinstance(issue_template_entries, list) else [],
                    readme_payload=readme_payload if isinstance(readme_payload, dict) else None,
                )
                await redis_client.set(cache_key, profile, settings.GITHUB_CACHE_TTL)
                return profile
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise ValueError(
                        f"GitHub repository '{normalized_full_name}' not found. "
                        f"Please check the repository name and try again."
                    )
                if e.response.status_code == 401:
                    raise RuntimeError(
                        "GitHub API authentication failed. "
                        "Invalid or missing GitHub token. "
                        "Please check GITHUB_TOKEN configuration."
                    )
                if e.response.status_code == 403:
                    raise RuntimeError(
                        "GitHub API rate limit exceeded. "
                        "Please try again later or use authentication to increase limits."
                    )
                raise RuntimeError(
                    f"GitHub API request failed with status {e.response.status_code}: {e.response.text}"
                )
            except httpx.TimeoutException:
                raise RuntimeError(
                    "GitHub API request timed out after 30 seconds. "
                    "Please check your network connection and try again."
                )
            except (ValueError, RuntimeError):
                raise
            except Exception as e:
                logger.error(f"Unexpected error fetching repository data: {e}")
                raise RuntimeError(f"Failed to fetch GitHub repository data: {str(e)}")
    
    async def fetch_user_data(self, username: str) -> UserData:
        """
        Fetch comprehensive user data from GitHub GraphQL API.
        
        Args:
            username: GitHub username to fetch data for
            
        Returns:
            UserData object containing profile, repositories, contributions, and languages
            
        Raises:
            ValueError: If username is invalid or user not found
            RuntimeError: If GitHub API request fails or rate limit exceeded
        """
        # Check cache first (with version to force refresh on code updates)
        cache_key = github_user_cache_key(username)
        cached_data = await redis_client.get(cache_key)
        
        if cached_data:
            logger.info(f"Cache hit for user: {username}")
            return self._deserialize_user_data(cached_data)
        
        logger.info(f"Cache miss for user: {username}, fetching from GitHub API")
        
        # Proactively check rate limit before making API call
        try:
            rate_limit_info = await self.check_rate_limit()
            if rate_limit_info["remaining"] == 0:
                reset_time = rate_limit_info["reset_at"]
                raise RuntimeError(
                    f"GitHub API rate limit exceeded. "
                    f"Limit resets at {reset_time}. "
                    f"Please try again later."
                )
            logger.info(f"Rate limit check: {rate_limit_info['remaining']}/{rate_limit_info['limit']} remaining")
        except RuntimeError as e:
            # If rate limit check itself fails, log but continue (might be network issue)
            if "rate limit exceeded" in str(e).lower():
                raise  # Re-raise if it's actually a rate limit error
            logger.warning(f"Rate limit check failed, continuing anyway: {e}")
        
        # Build and execute GraphQL query
        query = self._build_graphql_query()
        variables = {"username": username}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    self.api_url,
                    json={"query": query, "variables": variables},
                    headers=self.headers
                )
                response.raise_for_status()
                data = response.json()
                
                # Check for GraphQL errors
                if "errors" in data:
                    error_msg = data["errors"][0].get("message", "Unknown error")
                    if "Could not resolve to a User" in error_msg:
                        raise ValueError(
                            f"GitHub user '{username}' not found. "
                            f"Please check the username and try again."
                        )
                    raise RuntimeError(f"GitHub API error: {error_msg}")
                
                # Normalize data to UserData model
                user_data = self._normalize_response(data["data"], username)
                
                # Cache the normalized data
                serialized_data = self._serialize_user_data(user_data)
                await redis_client.set(cache_key, serialized_data, settings.GITHUB_CACHE_TTL)
                
                # Also invalidate legacy cache key formats
                for legacy in github_user_cache_keys_to_clear(username):
                    if legacy != cache_key:
                        await redis_client.delete(legacy)
                logger.info(f"Cached data for user: {username}")
                
                return user_data
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    raise RuntimeError(
                        "GitHub API authentication failed. "
                        "Invalid or missing GitHub token. "
                        "Please check GITHUB_TOKEN configuration."
                    )
                elif e.response.status_code == 403:
                    # Check if it's rate limit or other forbidden error
                    error_data = e.response.json() if e.response.text else {}
                    if "rate limit" in str(error_data).lower():
                        raise RuntimeError(
                            "GitHub API rate limit exceeded. "
                            "Please try again later or use authentication to increase limits."
                        )
                    raise RuntimeError(f"GitHub API access forbidden: {error_data}")
                elif e.response.status_code == 404:
                    raise ValueError(
                        f"GitHub user '{username}' not found. "
                        f"Please check the username and try again."
                    )
                else:
                    raise RuntimeError(
                        f"GitHub API request failed with status {e.response.status_code}: "
                        f"{e.response.text}"
                    )
            except httpx.TimeoutException:
                raise RuntimeError(
                    "GitHub API request timed out after 30 seconds. "
                    "Please check your network connection and try again."
                )
            except (ValueError, RuntimeError):
                # Re-raise our custom errors
                raise
            except Exception as e:
                logger.error(f"Unexpected error fetching GitHub data: {e}")
                raise RuntimeError(f"Failed to fetch GitHub data: {str(e)}")

    def _build_graphql_query(self) -> str:
        """
        Build comprehensive GraphQL query for fetching user data.
        
        Fetches:
        - User profile (name, avatar, bio, followers, following)
        - Repositories (top 100 by stars with metadata)
        - Contributions (commits and PRs in last year)
        - Language distribution across repositories
        """
        return """
        query($username: String!) {
          user(login: $username) {
            name
            login
            avatarUrl
            bio
            followers {
              totalCount
            }
            following {
              totalCount
            }
            repositories(
              first: 100,
              ownerAffiliations: OWNER,
              orderBy: {field: STARGAZERS, direction: DESC}
            ) {
              nodes {
                name
                description
                url
                pushedAt
                stargazerCount
                forkCount
                primaryLanguage {
                  name
                }
                repositoryTopics(first: 10) {
                  nodes {
                    topic {
                      name
                    }
                  }
                }
                languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
                  edges {
                    size
                    node {
                      name
                    }
                  }
                }
                readmeMd: object(expression: "HEAD:README.md") {
                  ... on Blob {
                    id
                    text
                  }
                }
                readmeLowerMd: object(expression: "HEAD:readme.md") {
                  ... on Blob {
                    id
                    text
                  }
                }
                readmeRst: object(expression: "HEAD:README.rst") {
                  ... on Blob {
                    id
                    text
                  }
                }
                readmeTxt: object(expression: "HEAD:README.txt") {
                  ... on Blob {
                    id
                    text
                  }
                }
                readmePlain: object(expression: "HEAD:README") {
                  ... on Blob {
                    id
                    text
                  }
                }
                docsReadme: object(expression: "HEAD:docs/README.md") {
                  ... on Blob {
                    id
                    text
                  }
                }
                rootTree: object(expression: "HEAD:") {
                  ... on Tree {
                    entries {
                      name
                      type
                    }
                  }
                }
                srcTree: object(expression: "HEAD:src") {
                  ... on Tree {
                    entries {
                      name
                      type
                    }
                  }
                }
                appTree: object(expression: "HEAD:app") {
                  ... on Tree {
                    entries {
                      name
                      type
                    }
                  }
                }
                packagesTree: object(expression: "HEAD:packages") {
                  ... on Tree {
                    entries {
                      name
                      type
                    }
                  }
                }
                backendTree: object(expression: "HEAD:backend") {
                  ... on Tree {
                    entries {
                      name
                      type
                    }
                  }
                }
                frontendTree: object(expression: "HEAD:frontend") {
                  ... on Tree {
                    entries {
                      name
                      type
                    }
                  }
                }
                libTree: object(expression: "HEAD:lib") {
                  ... on Tree {
                    entries {
                      name
                      type
                    }
                  }
                }
                cmdTree: object(expression: "HEAD:cmd") {
                  ... on Tree {
                    entries {
                      name
                      type
                    }
                  }
                }
                internalTree: object(expression: "HEAD:internal") {
                  ... on Tree {
                    entries {
                      name
                      type
                    }
                  }
                }
                licenseInfo {
                  name
                }
              }
            }
            contributionsCollection {
              totalCommitContributions
              totalPullRequestContributions
              contributionCalendar {
                totalContributions
                weeks {
                  contributionDays {
                    contributionCount
                    date
                  }
                }
              }
            }
          }
        }
        """
    
    def _normalize_response(self, data: Dict[str, Any], username: str) -> UserData:
        """
        Normalize GitHub API response to UserData model.
        
        Args:
            data: Raw GraphQL response data
            username: GitHub username
            
        Returns:
            Normalized UserData object
        """
        user = data.get("user")
        if not user:
            raise ValueError(
                f"GitHub user '{username}' not found. "
                f"Please check the username and try again."
            )
        
        # Extract repositories
        repositories = []
        language_bytes = {}
        
        for repo_node in user.get("repositories", {}).get("nodes", []):
            if not repo_node:
                continue
            repo_name = repo_node.get("name")
            repo_url = repo_node.get("url")
            if not repo_name or not repo_url:
                continue
            repo_langs: Dict[str, int] = {}
            language_edges = repo_node.get("languages", {}).get("edges", []) if repo_node.get("languages") else []
            if language_edges:
                for edge in language_edges:
                    if not edge or not edge.get("node") or not edge["node"].get("name"):
                        continue
                    repo_langs[edge["node"]["name"]] = edge.get("size", 0)
            elif repo_node.get("primaryLanguage"):
                repo_langs[repo_node["primaryLanguage"]["name"]] = 1

            pushed_raw = repo_node.get("pushedAt") or ""
            topics = []
            for node in repo_node.get("repositoryTopics", {}).get("nodes", []):
                if not node:
                    continue
                topic = node.get("topic") or {}
                topic_name = topic.get("name")
                if topic_name:
                    topics.append(topic_name)
            readme_text = self._extract_best_readme_text(repo_node)
            file_tree = self._extract_file_tree(repo_node)

            # Process repository
            repo = Repository(
                name=repo_name,
                description=repo_node.get("description") or "",
                stars=repo_node.get("stargazerCount", 0),
                forks=repo_node.get("forkCount", 0),
                language=repo_node["primaryLanguage"]["name"] if repo_node.get("primaryLanguage") else "Unknown",
                has_readme=bool(readme_text),
                has_license=repo_node.get("licenseInfo") is not None,
                url=repo_url,
                pushed_at=pushed_raw[:10] if pushed_raw else "",
                topics=topics,
                readme_text=readme_text,
                file_tree=file_tree,
                languages=repo_langs,
            )
            repositories.append(repo)
            
            # Aggregate language statistics
            if language_edges:
                for edge in language_edges:
                    if not edge or not edge.get("node") or not edge["node"].get("name"):
                        continue
                    lang_name = edge["node"]["name"]
                    lang_size = edge.get("size", 0)
                    language_bytes[lang_name] = language_bytes.get(lang_name, 0) + lang_size

        contribution_calendar = (
            user.get("contributionsCollection", {}).get("contributionCalendar")
            or {"weeks": []}
        )

        # Calculate longest streak from contribution calendar
        longest_streak = self._calculate_longest_streak(contribution_calendar)
        contribution_days = []
        for week in contribution_calendar.get("weeks", []):
            if not week:
                continue
            for day in week.get("contributionDays", []):
                if not day or not day.get("date"):
                    continue
                contribution_days.append(
                    ContributionDay(
                        date=day["date"],
                        contribution_count=day.get("contributionCount", 0),
                    )
                )
        
        # Extract contributions
        contributions = Contributions(
            total_commits_last_year=user.get("contributionsCollection", {}).get("totalCommitContributions", 0),
            total_prs_last_year=user.get("contributionsCollection", {}).get("totalPullRequestContributions", 0),
            longest_streak=longest_streak,
            contribution_days=contribution_days,
        )
        
        # Build UserData object
        user_data = UserData(
            username=username,
            name=user.get("name") or username,
            avatar_url=user.get("avatarUrl") or "",
            bio=user.get("bio") or "",
            followers=user.get("followers", {}).get("totalCount", 0),
            following=user.get("following", {}).get("totalCount", 0),
            repositories=repositories,
            contributions=contributions,
            languages=language_bytes
        )
        
        return user_data

    def _extract_best_readme_text(self, repo_node: Dict[str, Any]) -> str:
        for alias in README_CANDIDATE_ALIASES:
            blob = repo_node.get(alias)
            if isinstance(blob, dict) and blob.get("text"):
                return self._sanitize_readme_text(blob["text"])
        return ""

    def _sanitize_readme_text(self, raw_text: str) -> str:
        if not raw_text:
            return ""

        text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
        text = HTML_COMMENT_PATTERN.sub("", text)
        text = self._collapse_fenced_code_blocks(text)

        lines = text.split("\n")
        cleaned_lines: list[str] = []
        in_toc_block = False
        toc_list_count = 0
        blank_streak = 0

        for line in lines:
            stripped = line.strip()

            if TOC_HEADING_PATTERN.match(stripped):
                in_toc_block = True
                toc_list_count = 0
                continue
            if in_toc_block and TOC_LIST_ITEM_PATTERN.match(stripped):
                toc_list_count += 1
                continue
            if in_toc_block:
                if not stripped:
                    continue
                if toc_list_count >= 2:
                    in_toc_block = False
                else:
                    in_toc_block = False

            if not stripped:
                if blank_streak < 1:
                    cleaned_lines.append("")
                blank_streak += 1
                continue

            if BADGE_LINE_PATTERN.match(stripped):
                continue

            image_only_line = MARKDOWN_IMAGE_PATTERN.sub("", stripped)
            image_only_line = HTML_IMAGE_PATTERN.sub("", image_only_line).strip()
            if not image_only_line:
                continue

            line = MARKDOWN_IMAGE_PATTERN.sub("", line)
            line = HTML_IMAGE_PATTERN.sub("", line)
            line = MARKDOWN_LINK_PATTERN.sub(r"\1", line)
            line = INLINE_CODE_PATTERN.sub(r"\1", line)
            line = re.sub(r"\s+", " ", line).strip()
            if not line:
                continue

            cleaned_lines.append(line)
            blank_streak = 0

        sections = self._extract_useful_readme_sections(cleaned_lines)
        sanitized = "\n".join(sections).strip()
        sanitized = re.sub(r"\n{3,}", "\n\n", sanitized)
        return sanitized[:README_MAX_CHARS].strip()

    def _collapse_fenced_code_blocks(self, text: str) -> str:
        lines = text.split("\n")
        collapsed: list[str] = []
        in_block = False
        fence = ""

        for line in lines:
            stripped = line.strip()
            if not in_block and (stripped.startswith("```") or stripped.startswith("~~~")):
                in_block = True
                fence = stripped[:3]
                language = stripped[3:].strip()
                collapsed.append(f"[code example omitted{f': {language}' if language else ''}]")
                continue
            if in_block:
                if stripped.startswith(fence):
                    in_block = False
                    fence = ""
                continue
            collapsed.append(line)
        return "\n".join(collapsed)

    def _extract_useful_readme_sections(self, lines: list[str]) -> list[str]:
        sections: list[tuple[str | None, list[str]]] = []
        current_heading: str | None = None
        current_lines: list[str] = []

        def flush_section() -> None:
            nonlocal current_heading, current_lines
            if current_heading is not None or current_lines:
                sections.append((current_heading, current_lines[:]))
            current_heading = None
            current_lines = []

        for line in lines:
            if line.startswith("#"):
                flush_section()
                current_heading = line.lstrip("#").strip() or None
                continue
            current_lines.append(line)
        flush_section()

        selected: list[str] = []
        useful_sections = 0

        for heading, body_lines in sections:
            body = "\n".join(item for item in body_lines if item.strip()).strip()
            if not heading and not body:
                continue

            is_noise_heading = bool(heading and NOISE_HEADING_PATTERN.match(heading))
            is_useful_heading = bool(heading and USEFUL_HEADING_PATTERN.match(heading))
            if is_noise_heading and useful_sections >= 2:
                continue

            if heading:
                selected.append(f"## {heading}")

            if body:
                summary_lines = body.split("\n")
                if len(summary_lines) > 10:
                    summary_lines = summary_lines[:10]
                selected.extend(summary_lines)

            if heading is None or is_useful_heading or (body and useful_sections < 2):
                useful_sections += 1
            if useful_sections >= README_SECTION_LIMIT:
                break

        if not selected:
            return lines[:24]
        return selected

    def _extract_file_tree(self, repo_node: Dict[str, Any]) -> list[str]:
        entries: list[str] = []
        seen: set[str] = set()

        def add_entry(prefix: str, name: str, entry_type: str) -> None:
            if not name:
                return
            value = f"{prefix}{name}{'/' if entry_type == 'tree' else ''}"
            if value in seen:
                return
            seen.add(value)
            entries.append(value)

        root_tree = repo_node.get("rootTree") or {}
        for entry in root_tree.get("entries", [])[:20]:
            if not entry:
                continue
            add_entry("", entry.get("name", ""), entry.get("type", "blob"))

        nested_prefixes = {
            "srcTree": "src/",
            "appTree": "app/",
            "packagesTree": "packages/",
            "backendTree": "backend/",
            "frontendTree": "frontend/",
            "libTree": "lib/",
            "cmdTree": "cmd/",
            "internalTree": "internal/",
        }
        for alias in NESTED_TREE_ALIASES:
            tree = repo_node.get(alias) or {}
            prefix = nested_prefixes[alias]
            for entry in tree.get("entries", [])[:8]:
                if not entry:
                    continue
                add_entry(prefix, entry.get("name", ""), entry.get("type", "blob"))

        return entries[:40]

    def _normalize_repository_profile(
        self,
        repo_payload: Dict[str, Any],
        root_entries: list[Dict[str, Any]],
        workflow_entries: list[Dict[str, Any]],
        issue_template_entries: list[Dict[str, Any]],
        readme_payload: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        full_name = str(repo_payload.get("full_name", "")).lower()
        license_info = repo_payload.get("license") or {}
        topics = repo_payload.get("topics") or []
        description = repo_payload.get("description") or ""
        primary_language = None
        if isinstance(repo_payload.get("language"), str) and repo_payload.get("language"):
            primary_language = repo_payload.get("language")

        root_tree: list[str] = []
        has_contributing = False
        has_code_of_conduct = False
        has_security_policy = False
        has_examples_dir = False
        has_docs_dir = False
        has_issue_templates = False

        for entry in root_entries[:20]:
            name = str(entry.get("name", ""))
            entry_type = str(entry.get("type", "file"))
            path = f"{name}{'/' if entry_type == 'dir' else ''}"
            if name:
                root_tree.append(path)
            lowered = name.lower()
            has_contributing = has_contributing or lowered.startswith("contributing")
            has_code_of_conduct = has_code_of_conduct or lowered in {"code_of_conduct.md", "code-of-conduct.md"}
            has_security_policy = has_security_policy or lowered.startswith("security")
            has_examples_dir = has_examples_dir or lowered == "examples"
            has_docs_dir = has_docs_dir or lowered == "docs"
        
        # Check for issue templates in .github/ISSUE_TEMPLATE/
        # Issue templates can be .md, .yml, or .yaml files
        if issue_template_entries:
            for entry in issue_template_entries:
                name = str(entry.get("name", "")).lower()
                if name.endswith(('.md', '.yml', '.yaml')):
                    has_issue_templates = True
                    break

        readme_text = self._decode_rest_readme_text(readme_payload)
        readme_sections = self._extract_readme_headings(readme_text)
        readme_structure = self._extract_readme_structure(readme_text)
        has_screenshot = readme_structure["has_images"]
        quickstart_signals = ("install", "quick start", "quickstart", "getting started", "usage", "run")
        has_quickstart = any(any(signal in heading.lower() for signal in quickstart_signals) for heading in readme_sections)

        profile = {
            "full_name": full_name,
            "description": description,
            "stars": int(repo_payload.get("stargazers_count") or 0),
            "forks": int(repo_payload.get("forks_count") or 0),
            "language": primary_language,
            "topics": [str(topic) for topic in topics][:10],
            "license": license_info.get("spdx_id") or license_info.get("name"),
            "default_branch": repo_payload.get("default_branch"),
            "created_at": repo_payload.get("created_at"),
            "pushed_at": repo_payload.get("pushed_at"),
            "has_readme": bool(readme_text),
            "readme_sections": readme_sections,
            "has_license_file": bool(license_info),
            "workflow_file_count": len(workflow_entries),
            "has_contributing": has_contributing,
            "has_code_of_conduct": has_code_of_conduct,
            "has_security_policy": has_security_policy,
            "has_issue_templates": has_issue_templates,
            "root_tree": root_tree,
            "readme_excerpt": readme_text,
            "has_screenshot": has_screenshot,
            "has_quickstart": has_quickstart,
            "has_examples_dir": has_examples_dir,
            "has_docs_dir": has_docs_dir,
            "homepage": repo_payload.get("homepage"),
            "open_issues_count": int(repo_payload.get("open_issues_count") or 0),
            "archived": bool(repo_payload.get("archived")),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            # README structure for first_impression analysis
            "readme_h2_sections": readme_structure["h2_sections"],
            "readme_image_count": readme_structure["image_count"],
            "readme_badge_count": readme_structure["badge_count"],
            "readme_has_toc": readme_structure["has_toc"],
        }
        return profile

    def _decode_rest_readme_text(self, readme_payload: Dict[str, Any] | None) -> str:
        if not readme_payload:
            return ""
        if isinstance(readme_payload.get("content"), str):
            try:
                decoded = base64.b64decode(readme_payload["content"]).decode("utf-8", errors="ignore")
                return self._sanitize_readme_text(decoded)
            except Exception:
                return ""
        return ""

    def _extract_readme_headings(self, readme_text: str) -> list[str]:
        headings: list[str] = []
        for line in readme_text.splitlines():
            stripped = line.strip()
            if not stripped.startswith("#"):
                continue
            heading = stripped.lstrip("#").strip()
            if heading:
                headings.append(heading)
            if len(headings) >= 8:
                break
        return headings
    
    def _extract_readme_structure(self, readme_text: str) -> Dict[str, Any]:
        """
        Extract detailed README structure for first_impression analysis.
        
        Extracts:
        - Section headings (## level specifically)
        - Images/GIFs in README content
        - Badge count (shields.io, travis-ci, etc.)
        - Table of contents detection
        
        Args:
            readme_text: Raw README markdown content
            
        Returns:
            Dictionary with structure information:
            {
                "h2_sections": list[str],  # ## level headings
                "has_images": bool,
                "image_count": int,
                "badge_count": int,
                "has_toc": bool
            }
        """
        if not readme_text:
            return {
                "h2_sections": [],
                "has_images": False,
                "image_count": 0,
                "badge_count": 0,
                "has_toc": False
            }
        
        lines = readme_text.splitlines()
        h2_sections = []
        badge_count = 0
        image_count = 0
        has_toc = False
        
        # Track if we're in a potential TOC section
        in_toc_section = False
        toc_list_items = 0
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Extract ## level headings (h2)
            if stripped.startswith("## "):
                heading = stripped[3:].strip()
                if heading:
                    h2_sections.append(heading)
                    
                    # Check if this heading indicates a TOC
                    if TOC_HEADING_PATTERN.match(heading):
                        in_toc_section = True
                        toc_list_items = 0
            
            # Count badges (lines with multiple badge-style links)
            # Badges typically appear as: [![text](image-url)](link-url)
            if "shields.io" in stripped or "travis-ci" in stripped or "badge" in stripped.lower():
                # Count individual badge patterns in the line
                badge_matches = re.findall(r'\[!\[[^\]]*\]\([^)]+\)\]\([^)]+\)', stripped)
                badge_count += len(badge_matches)
                
                # Also count standalone badge images
                if not badge_matches:
                    standalone_badges = re.findall(r'!\[[^\]]*badge[^\]]*\]\([^)]+\)', stripped, re.IGNORECASE)
                    badge_count += len(standalone_badges)
            
            # Detect TOC list items (links with # anchors)
            if in_toc_section and TOC_LIST_ITEM_PATTERN.match(stripped):
                toc_list_items += 1
                # If we have 3+ list items with anchor links, it's likely a TOC
                if toc_list_items >= 3:
                    has_toc = True
                    in_toc_section = False  # Stop looking once confirmed
            elif in_toc_section and stripped and not stripped.startswith(("#", "-", "*", "+")):
                # Reset if we hit non-list content
                in_toc_section = False
                toc_list_items = 0
        
        # Count images (both markdown and HTML)
        markdown_images = MARKDOWN_IMAGE_PATTERN.findall(readme_text)
        html_images = HTML_IMAGE_PATTERN.findall(readme_text)
        image_count = len(markdown_images) + len(html_images)
        
        return {
            "h2_sections": h2_sections[:20],  # Limit to first 20 h2 sections
            "has_images": image_count > 0,
            "image_count": image_count,
            "badge_count": badge_count,
            "has_toc": has_toc
        }
    
    def _calculate_longest_streak(self, calendar: Dict[str, Any]) -> int:
        """
        Calculate the longest consecutive contribution streak.
        
        Args:
            calendar: GitHub contribution calendar data
            
        Returns:
            Longest streak in days
        """
        current_streak = 0
        longest_streak = 0
        
        for week in calendar.get("weeks", []):
            if not week:
                continue
            for day in week.get("contributionDays", []):
                if not day:
                    continue
                if day["contributionCount"] > 0:
                    current_streak += 1
                    longest_streak = max(longest_streak, current_streak)
                else:
                    current_streak = 0
        
        return longest_streak
    
    def _serialize_user_data(self, user_data: UserData) -> Dict[str, Any]:
        """
        Serialize UserData object to dictionary for caching.
        
        Args:
            user_data: UserData object to serialize
            
        Returns:
            Dictionary representation
        """
        return {
            "username": user_data.username,
            "name": user_data.name,
            "avatar_url": user_data.avatar_url,
            "bio": user_data.bio,
            "followers": user_data.followers,
            "following": user_data.following,
            "repositories": [
                {
                    "name": repo.name,
                    "description": repo.description,
                    "stars": repo.stars,
                    "forks": repo.forks,
                    "language": repo.language,
                    "has_readme": repo.has_readme,
                    "has_license": repo.has_license,
                    "url": repo.url,
                    "pushed_at": repo.pushed_at,
                    "topics": list(repo.topics),
                    "readme_text": repo.readme_text,
                    "file_tree": list(repo.file_tree),
                    "languages": dict(repo.languages),
                }
                for repo in user_data.repositories
            ],
            "contributions": {
                "total_commits_last_year": user_data.contributions.total_commits_last_year,
                "total_prs_last_year": user_data.contributions.total_prs_last_year,
                "longest_streak": user_data.contributions.longest_streak,
                "contribution_days": [
                    {
                        "date": day.date,
                        "contribution_count": day.contribution_count,
                    }
                    for day in user_data.contributions.contribution_days
                ],
            },
            "languages": user_data.languages
        }
    
    def _deserialize_user_data(self, data: Dict[str, Any]) -> UserData:
        """
        Deserialize dictionary to UserData object from cache.
        
        Args:
            data: Dictionary from cache
            
        Returns:
            UserData object
        """
        repositories = []
        for repo_data in data["repositories"]:
            repositories.append(
                Repository(
                    name=repo_data["name"],
                    description=repo_data.get("description") or "",
                    stars=repo_data["stars"],
                    forks=repo_data["forks"],
                    language=repo_data.get("language") or "Unknown",
                    has_readme=repo_data.get("has_readme", False),
                    has_license=repo_data.get("has_license", False),
                    url=repo_data["url"],
                    pushed_at=repo_data.get("pushed_at") or "",
                    topics=repo_data.get("topics") or [],
                    readme_text=repo_data.get("readme_text") or "",
                    file_tree=repo_data.get("file_tree") or [],
                    languages=repo_data.get("languages") or {},
                )
            )
        
        raw_contributions = data["contributions"]
        contribution_days = [
            ContributionDay(**day_data)
            for day_data in raw_contributions.get("contribution_days", [])
        ]
        contributions = Contributions(
            total_commits_last_year=raw_contributions["total_commits_last_year"],
            total_prs_last_year=raw_contributions["total_prs_last_year"],
            longest_streak=raw_contributions["longest_streak"],
            contribution_days=contribution_days,
        )
        
        return UserData(
            username=data["username"],
            name=data["name"],
            avatar_url=data["avatar_url"],
            bio=data["bio"],
            followers=data["followers"],
            following=data["following"],
            repositories=repositories,
            contributions=contributions,
            languages=data["languages"]
        )
    
    async def check_rate_limit(self) -> Dict[str, Any]:
        """
        Check current GitHub API rate limit status.
        
        Returns:
            Dictionary with rate limit information:
            - limit: Maximum requests per hour
            - remaining: Remaining requests
            - reset_at: Timestamp when limit resets
            
        Raises:
            RuntimeError: If rate limit check fails
        """
        query = """
        query {
          rateLimit {
            limit
            remaining
            resetAt
          }
        }
        """
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(
                    self.api_url,
                    json={"query": query},
                    headers=self.headers
                )
                response.raise_for_status()
                data = response.json()
                
                if "errors" in data:
                    raise RuntimeError(f"Rate limit check failed: {data['errors']}")
                
                rate_limit = data["data"]["rateLimit"]
                return {
                    "limit": rate_limit["limit"],
                    "remaining": rate_limit["remaining"],
                    "reset_at": rate_limit["resetAt"]
                }
                
            except Exception as e:
                logger.error(f"Failed to check rate limit: {e}")
                raise RuntimeError(f"Rate limit check failed: {str(e)}")
    
    @staticmethod
    def create_error_response(error: Exception) -> Dict[str, Any]:
        """
        Create a structured error response from an exception.
        
        This method converts exceptions into standardized error responses
        that can be returned by the API layer with appropriate HTTP status codes.
        
        Args:
            error: The exception to convert
            
        Returns:
            Dictionary with error information:
            - error_type: Type of error (user_not_found, rate_limit, api_error, etc.)
            - message: User-friendly error message
            - details: Additional error details (optional)
            
        Examples:
            >>> try:
            ...     await service.fetch_user_data("nonexistent")
            ... except Exception as e:
            ...     error_response = GitHubService.create_error_response(e)
            ...     # Returns: {"error_type": "user_not_found", "message": "...", ...}
        """
        error_msg = str(error)
        
        if isinstance(error, ValueError):
            # User not found or invalid input
            if "not found" in error_msg.lower():
                return {
                    "error_type": "user_not_found",
                    "message": error_msg,
                    "details": "The specified GitHub username does not exist."
                }
            return {
                "error_type": "invalid_input",
                "message": error_msg,
                "details": "Please provide a valid GitHub username."
            }
        
        elif isinstance(error, RuntimeError):
            # API errors, rate limits, authentication issues
            if "rate limit" in error_msg.lower():
                return {
                    "error_type": "rate_limit_exceeded",
                    "message": error_msg,
                    "details": "GitHub API rate limit has been exceeded. Please try again later."
                }
            elif "authentication failed" in error_msg.lower():
                return {
                    "error_type": "authentication_error",
                    "message": error_msg,
                    "details": "GitHub API authentication failed. Please contact support."
                }
            elif "timed out" in error_msg.lower():
                return {
                    "error_type": "timeout_error",
                    "message": error_msg,
                    "details": "The request took too long to complete. Please try again."
                }
            return {
                "error_type": "api_error",
                "message": error_msg,
                "details": "An error occurred while communicating with GitHub API."
            }
        
        # Unknown error type
        return {
            "error_type": "unknown_error",
            "message": error_msg,
            "details": "An unexpected error occurred. Please try again later."
        }
