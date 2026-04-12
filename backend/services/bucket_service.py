"""
Bucket service for grouping repositories by language, topics, and size.

This service ensures repositories are compared within similar categories,
generating bucket descriptions and warnings for size disparities.

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
"""
from typing import List
from datetime import datetime, timezone

from benchmark_models import RepositoryProfile, BucketDescription


def determine_bucket(profiles: List[RepositoryProfile]) -> BucketDescription:
    """
    Determine comparison bucket and generate description with warnings.
    
    Bucketing logic (Requirements 5.1, 5.2):
    1. Priority: Matching primary_language + overlapping topics
    2. Fallback: Matching primary_language + similar size category
    
    Size categories (Requirement 5.3):
    - Small: < 100 stars
    - Medium: 100-1000 stars
    - Large: 1000+ stars
    
    Args:
        profiles: List of RepositoryProfile objects to compare
        
    Returns:
        BucketDescription with label and optional warning
        
    Raises:
        ValueError: If profiles list is empty
    """
    if not profiles:
        raise ValueError("Cannot determine bucket for empty profiles list")
    
    # Extract common characteristics
    languages = [p.language for p in profiles if p.language]
    all_topics = [set(p.topics) for p in profiles]
    
    # Find common language
    common_language = None
    if languages:
        # Use the most common language
        language_counts = {}
        for lang in languages:
            language_counts[lang] = language_counts.get(lang, 0) + 1
        common_language = max(language_counts, key=language_counts.get)
    
    # Find overlapping topics
    overlapping_topics = set()
    if len(all_topics) >= 2:
        # Find topics that appear in at least 2 repositories
        topic_counts = {}
        for topic_set in all_topics:
            for topic in topic_set:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
        overlapping_topics = {topic for topic, count in topic_counts.items() if count >= 2}
    
    # Build bucket label
    label_parts = []
    
    if common_language:
        label_parts.append(common_language)
    
    if overlapping_topics:
        # Show up to 2 overlapping topics
        topics_list = sorted(overlapping_topics)[:2]
        topics_str = ", ".join(topics_list)
        label_parts.append(f"shared topic: {topics_str}")
    
    # If no meaningful label, use generic description
    if not label_parts:
        label_parts.append("mixed repositories")
    
    label = " | ".join(label_parts)
    
    # Check for size disparity (Requirement 5.4)
    warning = _generate_size_warning(profiles)
    
    return BucketDescription(label=label, warning=warning)


def _categorize_size(stars: int) -> str:
    """
    Categorize repository by star count (Requirement 5.3).
    
    Args:
        stars: Star count
        
    Returns:
        Size category: "small", "medium", or "large"
    """
    if stars < 100:
        return "small"
    elif stars < 1000:
        return "medium"
    else:
        return "large"


def _generate_size_warning(profiles: List[RepositoryProfile]) -> str | None:
    """
    Generate warning if repositories have significant size differences (Requirement 5.4).
    
    Args:
        profiles: List of RepositoryProfile objects
        
    Returns:
        Warning message if size disparity exists, None otherwise
    """
    if len(profiles) < 2:
        return None
    
    size_categories = [_categorize_size(p.stars) for p in profiles]
    unique_categories = set(size_categories)
    
    # Warning if repositories span more than one size category
    if len(unique_categories) > 1:
        star_counts = [p.stars for p in profiles]
        min_stars = min(star_counts)
        max_stars = max(star_counts)
        return f"Size disparity: repositories range from {min_stars} to {max_stars} stars"
    
    return None


def _is_young_repository(profile: RepositoryProfile, months_threshold: int = 6) -> bool:
    """
    Check if repository is younger than threshold (Requirement 5.5).
    
    Args:
        profile: RepositoryProfile to check
        months_threshold: Age threshold in months (default: 6)
        
    Returns:
        True if repository is younger than threshold, False otherwise
    """
    if not profile.created_at:
        return False
    
    now = datetime.now(timezone.utc)
    age_days = (now - profile.created_at).days
    age_months = age_days / 30.44  # Average days per month
    
    return age_months < months_threshold


def apply_age_based_interpretation(profile: RepositoryProfile) -> dict:
    """
    Apply different growth rate interpretation for young repositories (Requirement 5.5).
    
    For repositories < 6 months old, growth metrics should be interpreted differently
    as they haven't had time to establish community patterns.
    
    Args:
        profile: RepositoryProfile to analyze
        
    Returns:
        Dictionary with age-based interpretation flags and metadata
    """
    is_young = _is_young_repository(profile)
    
    result = {
        "is_young_repository": is_young,
        "age_months": None,
        "interpretation_note": None
    }
    
    if profile.created_at:
        now = datetime.now(timezone.utc)
        age_days = (now - profile.created_at).days
        result["age_months"] = age_days / 30.44
        
        if is_young:
            result["interpretation_note"] = (
                "Repository is less than 6 months old. Growth metrics should be "
                "interpreted with caution as the project is still establishing its community."
            )
    
    return result
