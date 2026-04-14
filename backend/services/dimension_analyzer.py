"""
Rule-based dimension analysis service for repository benchmarking.

This module implements the 8-dimensional analysis framework for comparing repositories
based on observable, verifiable features from GitHub data.

Validates Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8
"""
import re
from typing import Dict, Any
from benchmark_models import (
    AnalysisDimension,
    DimensionScore,
    RepositoryProfile
)


def analyze_first_impression(profile: RepositoryProfile) -> DimensionScore:
    """
    Analyze first impression dimension (Requirement 4.2).
    
    Checks:
    - README has screenshot/GIF (detect image links)
    - Badge count (shields.io, travis, etc.)
    - Table of contents present
    - Multi-language README support
    
    Args:
        profile: Repository profile with README structure data
        
    Returns:
        DimensionScore with level (missing, weak, medium, strong) and raw features
    """
    features = {
        "has_screenshot": profile.readme_image_count > 0,
        "badge_count": profile.readme_badge_count,
        "has_toc": profile.readme_has_toc,
        "has_multilang_readme": False  # Phase 1: not detected yet
    }
    
    # Scoring logic: weighted sum
    score = sum([
        features["has_screenshot"] * 2,
        min(features["badge_count"], 5),
        features["has_toc"] * 2,
        features["has_multilang_readme"]
    ])
    
    # Level assignment
    if score >= 8:
        level = "strong"
    elif score >= 5:
        level = "medium"
    elif score >= 2:
        level = "weak"
    else:
        level = "missing"
    
    return DimensionScore(
        dimension=AnalysisDimension.FIRST_IMPRESSION,
        level=level,
        raw_features=features
    )


def analyze_onboarding(profile: RepositoryProfile) -> DimensionScore:
    """
    Analyze onboarding dimension (Requirement 4.3).
    
    Checks:
    - Quickstart sections in README
    - Installation steps
    - Example directories
    - Demo links
    
    Args:
        profile: Repository profile with README and file structure
        
    Returns:
        DimensionScore with level and raw features
    """
    features = {
        "has_quickstart": profile.has_quickstart,
        "has_installation": _has_installation_section(profile),
        "has_examples_dir": profile.has_examples_dir,
        "has_demo_link": profile.homepage is not None
    }
    
    score = sum(features.values())
    
    # Level assignment
    if score >= 3:
        level = "strong"
    elif score == 2:
        level = "medium"
    elif score == 1:
        level = "weak"
    else:
        level = "missing"
    
    return DimensionScore(
        dimension=AnalysisDimension.ONBOARDING,
        level=level,
        raw_features=features
    )


def analyze_engineering_quality(profile: RepositoryProfile) -> DimensionScore:
    """
    Analyze engineering quality dimension (Requirement 4.4).
    
    Checks:
    - Test files present (test/, __tests__, *.test.*, *.spec.*)
    - CI workflows (workflow_file_count > 0)
    - Type checking (TypeScript, mypy, etc.)
    - Security policy file
    - Dependency management (package-lock, yarn.lock, requirements.txt)
    
    Args:
        profile: Repository profile with workflow and file data
        
    Returns:
        DimensionScore with level and raw features
    """
    features = {
        "has_tests": _detect_test_files(profile),
        "has_ci": profile.workflow_file_count > 0,
        "has_type_checking": _detect_type_checking(profile),
        "has_security_policy": profile.has_security_policy,
        "has_dependency_lock": False  # Phase 1: requires file tree analysis
    }
    
    score = sum(features.values())
    
    # Level assignment
    if score >= 4:
        level = "strong"
    elif score == 3:
        level = "medium"
    elif score >= 1:
        level = "weak"
    else:
        level = "missing"
    
    return DimensionScore(
        dimension=AnalysisDimension.ENGINEERING_QUALITY,
        level=level,
        raw_features=features
    )


def analyze_releases(profile: RepositoryProfile) -> DimensionScore:
    """
    Analyze releases dimension (Requirement 4.5).
    
    Checks:
    - Semantic versioning usage
    - Changelog files (CHANGELOG.md, HISTORY.md)
    - Release frequency (releases in past year)
    
    Args:
        profile: Repository profile with release data
        
    Returns:
        DimensionScore with level and raw features
    """
    features = {
        "has_releases": (profile.release_count_1y or 0) > 0,
        "release_frequency": profile.release_count_1y or 0,
        "has_changelog": _detect_changelog(profile),
        "uses_semver": False  # Phase 1: requires release tag analysis
    }
    
    # Scoring based on release frequency
    release_count = features["release_frequency"]
    score = 0
    
    if release_count >= 12:  # Monthly or more
        score += 3
    elif release_count >= 4:  # Quarterly
        score += 2
    elif release_count >= 1:  # At least one
        score += 1
    
    if features["has_changelog"]:
        score += 2
    
    # Level assignment
    if score >= 4:
        level = "strong"
    elif score >= 2:
        level = "medium"
    elif score >= 1:
        level = "weak"
    else:
        level = "missing"
    
    return DimensionScore(
        dimension=AnalysisDimension.RELEASES,
        level=level,
        raw_features=features
    )


def analyze_community(profile: RepositoryProfile) -> DimensionScore:
    """
    Analyze community dimension (Requirement 4.6).
    
    Checks:
    - CONTRIBUTING file
    - Code of Conduct
    - Issue templates
    - Good first issue labels (Phase 2+)
    
    Args:
        profile: Repository profile with community file data
        
    Returns:
        DimensionScore with level and raw features
    """
    features = {
        "has_contributing": profile.has_contributing,
        "has_code_of_conduct": profile.has_code_of_conduct,
        "has_issue_templates": profile.has_issue_templates,
        "has_good_first_issue": False  # Phase 2: requires labels API
    }
    
    score = sum(features.values())
    
    # Level assignment
    if score >= 3:
        level = "strong"
    elif score == 2:
        level = "medium"
    elif score == 1:
        level = "weak"
    else:
        level = "missing"
    
    return DimensionScore(
        dimension=AnalysisDimension.COMMUNITY,
        level=level,
        raw_features=features
    )


def analyze_discovery(profile: RepositoryProfile) -> DimensionScore:
    """
    Analyze discovery dimension (Requirement 4.7).
    
    Checks:
    - Topics count (GitHub repository topics)
    - Description quality (length, clarity)
    - Repository type (CLI, library, application)
    
    Args:
        profile: Repository profile with topics and description
        
    Returns:
        DimensionScore with level and raw features
    """
    features = {
        "topics_count": len(profile.topics),
        "has_description": profile.description is not None and len(profile.description.strip()) > 0,
        "description_length": len(profile.description) if profile.description else 0,
        "repo_type": _infer_repo_type(profile)
    }
    
    # Scoring logic
    score = 0
    
    # Topics scoring
    topics_count = features["topics_count"]
    if topics_count >= 5:
        score += 3
    elif topics_count >= 3:
        score += 2
    elif topics_count >= 1:
        score += 1
    
    # Description scoring
    if features["has_description"]:
        desc_len = features["description_length"]
        if desc_len >= 50:
            score += 2
        elif desc_len >= 20:
            score += 1
    
    # Level assignment
    if score >= 4:
        level = "strong"
    elif score >= 2:
        level = "medium"
    elif score >= 1:
        level = "weak"
    else:
        level = "missing"
    
    return DimensionScore(
        dimension=AnalysisDimension.DISCOVERY,
        level=level,
        raw_features=features
    )


def analyze_compliance(profile: RepositoryProfile) -> DimensionScore:
    """
    Analyze compliance dimension (Requirement 4.8).
    
    Checks:
    - License file presence
    - License clarity (recognized license type)
    - Commercial-friendliness (permissive licenses)
    
    Args:
        profile: Repository profile with license data
        
    Returns:
        DimensionScore with level and raw features
    """
    features = {
        "has_license_file": profile.has_license_file,
        "license_type": profile.license if profile.license is not None else "not detected",
        "is_permissive": _is_permissive_license(profile.license),
        "license_clarity": profile.license is not None
    }
    
    # Scoring logic
    score = 0
    
    if features["has_license_file"]:
        score += 2
    
    if features["license_clarity"]:
        score += 1
    
    if features["is_permissive"]:
        score += 2
    
    # Level assignment
    if score >= 4:
        level = "strong"
    elif score >= 2:
        level = "medium"
    elif score >= 1:
        level = "weak"
    else:
        level = "missing"
    
    return DimensionScore(
        dimension=AnalysisDimension.COMPLIANCE,
        level=level,
        raw_features=features
    )


def analyze_positioning(profile: RepositoryProfile) -> DimensionScore:
    """
    Analyze positioning dimension (Requirement 4.1).
    
    Checks:
    - README first paragraph quality
    - Description quality
    - Clear value proposition
    
    Args:
        profile: Repository profile with README and description
        
    Returns:
        DimensionScore with level and raw features
    """
    features = {
        "has_description": profile.description is not None and len(profile.description.strip()) > 0,
        "description_quality": _assess_description_quality(profile.description),
        "readme_h2_count": len(profile.readme_h2_sections),
        "has_clear_purpose": _has_clear_purpose(profile)
    }
    
    # Scoring logic
    score = 0
    
    if features["has_description"]:
        score += 1
    
    score += features["description_quality"]
    
    # README structure scoring
    h2_count = features["readme_h2_count"]
    if h2_count >= 5:
        score += 2
    elif h2_count >= 3:
        score += 1
    
    if features["has_clear_purpose"]:
        score += 1
    
    # Level assignment
    if score >= 4:
        level = "strong"
    elif score >= 2:
        level = "medium"
    elif score >= 1:
        level = "weak"
    else:
        level = "missing"
    
    return DimensionScore(
        dimension=AnalysisDimension.POSITIONING,
        level=level,
        raw_features=features
    )


# Helper functions

def _has_installation_section(profile: RepositoryProfile) -> bool:
    """Check if README has installation section."""
    installation_keywords = ["install", "setup", "getting started", "quick start"]
    sections_lower = [s.lower() for s in profile.readme_sections]
    return any(keyword in section for section in sections_lower for keyword in installation_keywords)


def _detect_test_files(profile: RepositoryProfile) -> bool:
    """
    Detect presence of test files.
    Phase 1: Use heuristics based on common patterns.
    """
    # Check if README mentions testing
    test_keywords = ["test", "testing", "spec", "jest", "pytest", "mocha"]
    sections_lower = [s.lower() for s in profile.readme_sections]
    has_test_section = any(keyword in section for section in sections_lower for keyword in test_keywords)
    
    # Assume projects with CI likely have tests
    has_ci = profile.workflow_file_count > 0
    
    return has_test_section or has_ci


def _detect_type_checking(profile: RepositoryProfile) -> bool:
    """Detect type checking based on language."""
    if profile.language in ["TypeScript", "Kotlin", "Swift", "Rust", "Go"]:
        return True
    
    # Check for type checking in topics
    type_topics = ["typescript", "mypy", "types", "typing"]
    return any(topic in profile.topics for topic in type_topics)


def _detect_changelog(profile: RepositoryProfile) -> bool:
    """Check if README mentions changelog."""
    changelog_keywords = ["changelog", "history", "releases", "what's new"]
    sections_lower = [s.lower() for s in profile.readme_sections]
    return any(keyword in section for section in sections_lower for keyword in changelog_keywords)


def _infer_repo_type(profile: RepositoryProfile) -> str:
    """Infer repository type from topics and description."""
    topics_lower = [t.lower() for t in profile.topics]
    desc_lower = (profile.description or "").lower()
    
    if any(t in topics_lower for t in ["cli", "command-line", "terminal"]):
        return "cli"
    elif any(t in topics_lower for t in ["library", "framework", "sdk"]):
        return "library"
    elif any(t in topics_lower for t in ["app", "application", "web-app"]):
        return "application"
    elif "cli" in desc_lower or "command" in desc_lower:
        return "cli"
    elif "library" in desc_lower or "framework" in desc_lower:
        return "library"
    else:
        return "unknown"


def _is_permissive_license(license_type: str | None) -> bool:
    """Check if license is permissive (commercial-friendly)."""
    if not license_type:
        return False
    
    permissive_licenses = [
        "MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause",
        "ISC", "0BSD", "Unlicense", "CC0-1.0"
    ]
    
    return license_type in permissive_licenses


def _assess_description_quality(description: str | None) -> int:
    """
    Assess description quality (0-2 points).
    
    Returns:
        0: No description or very short
        1: Basic description (20-50 chars)
        2: Good description (50+ chars with clear purpose)
    """
    if not description:
        return 0
    
    desc_len = len(description.strip())
    
    if desc_len < 20:
        return 0
    elif desc_len < 50:
        return 1
    else:
        return 2


def _has_clear_purpose(profile: RepositoryProfile) -> bool:
    """Check if repository has clear purpose statement."""
    # Check if description exists and is substantial
    if profile.description and len(profile.description.strip()) >= 30:
        return True
    
    # Check if README has multiple sections (indicates structure)
    if len(profile.readme_sections) >= 3:
        return True
    
    return False
