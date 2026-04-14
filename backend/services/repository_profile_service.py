"""
Repository Profile Service

This service is responsible for fetching and caching repository metadata.
It reuses the existing GitHubService for API calls and implements repository
name normalization and caching strategies.
"""
import logging
from datetime import datetime
from typing import Optional

from services.github_service import GitHubService
from utils.redis_client import redis_client
from cache_keys import repository_profile_cache_key
from benchmark_models import RepositoryProfile
from config import settings

logger = logging.getLogger(__name__)

# Differential TTL strategy (Requirement 13.3)
# Metadata changes infrequently; README content is refreshed less often;
# star history (Phase 2+) is the most stable and cached longest.
TTL_METADATA: int = getattr(settings, "REPOSITORY_METADATA_TTL", 3600)       # 1 hour
TTL_README: int = getattr(settings, "REPOSITORY_README_TTL", 21600)           # 6 hours
TTL_STAR_HISTORY: int = getattr(settings, "REPOSITORY_STAR_HISTORY_TTL", 86400)  # 24 hours (Phase 2+)


class RepositoryProfileService:
    """Service for fetching and caching repository profiles."""
    
    def __init__(self, github_service: Optional[GitHubService] = None):
        """
        Initialize the repository profile service.
        
        Args:
            github_service: Optional GitHubService instance. If not provided,
                          a new instance will be created.
        """
        self.github = github_service or GitHubService()
    
    def normalize_repo_name(self, full_name: str) -> str:
        """
        Normalize repository name to canonical GitHub format (owner/repo).
        
        Args:
            full_name: Repository identifier in various formats
            
        Returns:
            Normalized repository name in format "owner/repo"
            
        Raises:
            ValueError: If the repository name format is invalid
        """
        # Strip whitespace
        normalized = full_name.strip()
        
        # Check for valid format
        if "/" not in normalized:
            raise ValueError(
                f"Invalid repository format: '{full_name}'. "
                f"Expected format: 'owner/repo'"
            )
        
        parts = normalized.split("/")
        if len(parts) != 2:
            raise ValueError(
                f"Invalid repository format: '{full_name}'. "
                f"Expected format: 'owner/repo'"
            )
        
        owner, repo = parts
        owner = owner.strip()
        repo = repo.strip()
        
        if not owner or not repo:
            raise ValueError(
                f"Invalid repository format: '{full_name}'. "
                f"Owner and repo name cannot be empty"
            )
        
        # Return normalized format (lowercase for consistency)
        return f"{owner}/{repo}".lower()
    
    async def get_profile(
        self,
        full_name: str,
        force_refresh: bool = False
    ) -> RepositoryProfile:
        """
        Fetch or return cached repository profile.
        
        Args:
            full_name: Repository in format "owner/repo"
            force_refresh: Skip cache and fetch fresh data
            
        Returns:
            RepositoryProfile with metadata and structural signals
            
        Raises:
            ValueError: Invalid full_name format or repository not found
            RuntimeError: GitHub API errors (rate limit, timeout, etc.)
        """
        # Normalize repository name
        try:
            normalized_name = self.normalize_repo_name(full_name)
        except ValueError:
            raise
        
        # Check cache first (unless force refresh)
        if not force_refresh:
            cache_key = repository_profile_cache_key(normalized_name)
            cached_data = await redis_client.get(cache_key)
            
            if cached_data:
                logger.info(f"Cache hit for repository profile: {normalized_name}")
                return self._deserialize_profile(cached_data)
        
        # Fetch from GitHub API
        logger.info(f"Fetching repository profile from GitHub: {normalized_name}")
        try:
            raw_profile = await self.github.fetch_repository_profile(normalized_name)
        except ValueError as e:
            # Repository not found
            raise ValueError(str(e))
        except RuntimeError as e:
            # API errors (rate limit, timeout, etc.)
            raise RuntimeError(str(e))
        
        # Convert to RepositoryProfile model
        profile = self._normalize_to_profile(raw_profile, normalized_name)
        
        # Cache the profile
        cache_key = repository_profile_cache_key(normalized_name)
        serialized = self._serialize_profile(profile)
        
        # Use metadata TTL (1 hour as per requirements)
        ttl = TTL_METADATA
        await redis_client.set(cache_key, serialized, ttl)
        logger.info(f"Cached repository profile: {normalized_name}")
        
        return profile
    
    def _normalize_to_profile(
        self,
        raw_profile: dict,
        normalized_name: str
    ) -> RepositoryProfile:
        """
        Convert raw GitHub API response to RepositoryProfile model.
        
        Args:
            raw_profile: Raw profile data from GitHubService
            normalized_name: Normalized repository name
            
        Returns:
            RepositoryProfile instance
        """
        # Parse dates
        created_at = None
        if raw_profile.get("created_at"):
            try:
                created_at = datetime.fromisoformat(
                    raw_profile["created_at"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass
        
        pushed_at = None
        if raw_profile.get("pushed_at"):
            try:
                pushed_at = datetime.fromisoformat(
                    raw_profile["pushed_at"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass
        
        # Extract license - handle both string and dict formats
        license_value = raw_profile.get("license")
        if isinstance(license_value, dict):
            license_value = license_value.get("spdx_id") or license_value.get("name")
        
        return RepositoryProfile(
            full_name=normalized_name,
            description=raw_profile.get("description"),
            stars=raw_profile.get("stars", raw_profile.get("stargazers_count", 0)),
            forks=raw_profile.get("forks", raw_profile.get("forks_count", 0)),
            language=raw_profile.get("language"),
            topics=raw_profile.get("topics", []),
            license=license_value,
            default_branch=raw_profile.get("default_branch"),
            created_at=created_at,
            pushed_at=pushed_at,
            has_readme=raw_profile.get("has_readme", False),
            readme_sections=raw_profile.get("readme_sections", []),
            has_license_file=raw_profile.get("has_license_file", False),
            workflow_file_count=raw_profile.get("workflow_file_count", 0),
            has_contributing=raw_profile.get("has_contributing", False),
            has_code_of_conduct=raw_profile.get("has_code_of_conduct", False),
            has_security_policy=raw_profile.get("has_security_policy", False),
            has_issue_templates=raw_profile.get("has_issue_templates", False),
            release_count_1y=raw_profile.get("release_count_1y"),
            fetched_at=datetime.now(),
            has_screenshot=raw_profile.get("has_screenshot", False),
            homepage=raw_profile.get("homepage"),
            has_quickstart=raw_profile.get("has_quickstart", False),
            has_examples_dir=raw_profile.get("has_examples_dir", False),
            has_docs_dir=raw_profile.get("has_docs_dir", False),
            open_issues_count=raw_profile.get("open_issues_count", 0),
            readme_h2_sections=raw_profile.get("readme_h2_sections", []),
            readme_image_count=raw_profile.get("readme_image_count", 0),
            readme_badge_count=raw_profile.get("readme_badge_count", 0),
            readme_has_toc=raw_profile.get("readme_has_toc", False),
        )
    
    def _serialize_profile(self, profile: RepositoryProfile) -> dict:
        """
        Serialize RepositoryProfile to dictionary for caching.
        
        Args:
            profile: RepositoryProfile instance
            
        Returns:
            Dictionary representation
        """
        return {
            "full_name": profile.full_name,
            "description": profile.description,
            "stars": profile.stars,
            "forks": profile.forks,
            "language": profile.language,
            "topics": profile.topics,
            "license": profile.license,
            "default_branch": profile.default_branch,
            "created_at": profile.created_at.isoformat() if profile.created_at else None,
            "pushed_at": profile.pushed_at.isoformat() if profile.pushed_at else None,
            "has_readme": profile.has_readme,
            "readme_sections": profile.readme_sections,
            "has_license_file": profile.has_license_file,
            "workflow_file_count": profile.workflow_file_count,
            "has_contributing": profile.has_contributing,
            "has_code_of_conduct": profile.has_code_of_conduct,
            "has_security_policy": profile.has_security_policy,
            "has_issue_templates": profile.has_issue_templates,
            "release_count_1y": profile.release_count_1y,
            "fetched_at": profile.fetched_at.isoformat(),
            "has_screenshot": profile.has_screenshot,
            "homepage": profile.homepage,
            "has_quickstart": profile.has_quickstart,
            "has_examples_dir": profile.has_examples_dir,
            "has_docs_dir": profile.has_docs_dir,
            "open_issues_count": profile.open_issues_count,
            "readme_h2_sections": profile.readme_h2_sections,
            "readme_image_count": profile.readme_image_count,
            "readme_badge_count": profile.readme_badge_count,
            "readme_has_toc": profile.readme_has_toc,
        }
    
    def _deserialize_profile(self, data: dict) -> RepositoryProfile:
        """
        Deserialize dictionary to RepositoryProfile.
        
        Args:
            data: Dictionary from cache
            
        Returns:
            RepositoryProfile instance
        """
        # Parse dates
        created_at = None
        if data.get("created_at"):
            try:
                created_at = datetime.fromisoformat(data["created_at"])
            except (ValueError, AttributeError):
                pass
        
        pushed_at = None
        if data.get("pushed_at"):
            try:
                pushed_at = datetime.fromisoformat(data["pushed_at"])
            except (ValueError, AttributeError):
                pass
        
        fetched_at = datetime.now()
        if data.get("fetched_at"):
            try:
                fetched_at = datetime.fromisoformat(data["fetched_at"])
            except (ValueError, AttributeError):
                pass
        
        return RepositoryProfile(
            full_name=data.get("full_name", ""),
            description=data.get("description"),
            stars=data.get("stars", 0),
            forks=data.get("forks", 0),
            language=data.get("language"),
            topics=data.get("topics", []),
            license=data.get("license"),
            default_branch=data.get("default_branch"),
            created_at=created_at,
            pushed_at=pushed_at,
            has_readme=data.get("has_readme", False),
            readme_sections=data.get("readme_sections", []),
            has_license_file=data.get("has_license_file", False),
            workflow_file_count=data.get("workflow_file_count", 0),
            has_contributing=data.get("has_contributing", False),
            has_code_of_conduct=data.get("has_code_of_conduct", False),
            has_security_policy=data.get("has_security_policy", False),
            has_issue_templates=data.get("has_issue_templates", False),
            release_count_1y=data.get("release_count_1y"),
            fetched_at=fetched_at,
            has_screenshot=data.get("has_screenshot", False),
            homepage=data.get("homepage"),
            has_quickstart=data.get("has_quickstart", False),
            has_examples_dir=data.get("has_examples_dir", False),
            has_docs_dir=data.get("has_docs_dir", False),
            open_issues_count=data.get("open_issues_count", 0),
            readme_h2_sections=data.get("readme_h2_sections", []),
            readme_image_count=data.get("readme_image_count", 0),
            readme_badge_count=data.get("readme_badge_count", 0),
            readme_has_toc=data.get("readme_has_toc", False),
        )
