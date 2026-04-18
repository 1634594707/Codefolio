"""
Data models for repository benchmarking feature.

This module defines the core data structures used in repository comparison and analysis.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional


class AnalysisDimension(str, Enum):
    """Eight dimensions used to evaluate repositories."""
    POSITIONING = "positioning"
    FIRST_IMPRESSION = "first_impression"
    ONBOARDING = "onboarding"
    ENGINEERING_QUALITY = "engineering_quality"
    RELEASES = "releases"
    COMMUNITY = "community"
    DISCOVERY = "discovery"
    COMPLIANCE = "compliance"


@dataclass
class RepositoryProfile:
    """Comprehensive repository metadata snapshot."""
    full_name: str
    description: Optional[str]
    stars: int
    forks: int
    language: Optional[str]
    topics: List[str]
    license: Optional[str]
    default_branch: Optional[str]
    created_at: Optional[datetime]
    pushed_at: Optional[datetime]
    has_readme: bool
    readme_sections: List[str]
    has_license_file: bool
    workflow_file_count: int
    has_contributing: bool
    has_code_of_conduct: bool
    has_security_policy: bool
    release_count_1y: Optional[int]
    fetched_at: datetime
    
    # Additional fields for analysis (with defaults)
    has_issue_templates: bool = False
    has_screenshot: bool = False
    homepage: Optional[str] = None
    has_quickstart: bool = False
    has_examples_dir: bool = False
    has_docs_dir: bool = False
    open_issues_count: int = 0
    
    # README structure fields for first_impression analysis (Requirement 4.2)
    readme_h2_sections: List[str] = field(default_factory=list)
    readme_image_count: int = 0
    readme_badge_count: int = 0
    readme_has_toc: bool = False


@dataclass
class DimensionScore:
    """Score for a single analysis dimension."""
    dimension: AnalysisDimension
    level: Literal["missing", "weak", "medium", "strong"]
    raw_features: Dict[str, Any]
    
    def to_numeric(self) -> int:
        """Convert level to numeric score for calculations."""
        return {"missing": 0, "weak": 1, "medium": 2, "strong": 3}[self.level]


@dataclass
class FeatureMatrixCell:
    """Single cell in the feature comparison matrix."""
    repo: str
    level: str
    raw: Dict[str, Any]


@dataclass
class FeatureMatrixRow:
    """Single row (dimension) in the feature comparison matrix."""
    dimension_id: str
    label_key: str
    label: str
    cells: List[FeatureMatrixCell]


@dataclass
class FeatureMatrix:
    """Multi-dimensional comparison table."""
    rows: List[FeatureMatrixRow]


@dataclass
class Evidence:
    """Evidence supporting a success hypothesis."""
    type: Literal["readme_section", "metric", "file", "topic"]
    detail: str
    repo: str


@dataclass
class SuccessHypothesis:
    """Structured explanation of why a benchmark repository performs better."""
    hypothesis_id: str
    title: str
    category: str
    evidence: List[Evidence]
    transferability: Literal["high", "medium", "low"]
    caveats: List[str]
    confidence: Literal["rule_based", "llm_summarized"]


@dataclass
class ActionItem:
    """Concrete, prioritized task recommendation."""
    action_id: str
    dimension: str
    title: str
    rationale: str
    effort: Literal["S", "M", "L"]
    impact: int  # 1-5
    priority_score: float
    checklist: List[str]
    suggested_deadline: Literal["7d", "30d", "90d"]
    
    @property
    def is_quick_win(self) -> bool:
        """Quick win: Small effort + High impact (4-5)."""
        return self.effort == "S" and self.impact >= 4


@dataclass
class BucketDescription:
    """Description of the comparison context."""
    label: str
    warning: Optional[str]


@dataclass
class Narrative:
    """AI-generated summary with disclaimer."""
    summary: str
    disclaimer: str


@dataclass
class BenchmarkReport:
    """Complete repository comparison report."""
    bucket: BucketDescription
    profiles: Dict[str, RepositoryProfile]
    feature_matrix: FeatureMatrix
    hypotheses: List[SuccessHypothesis]
    actions: List[ActionItem]
    narrative: Optional[Narrative]
    generated_at: datetime
    llm_calls: int


@dataclass
class BenchmarkSuggestion:
    """Recommended benchmark repository."""
    full_name: str
    reason_code: str
    reason_params: Dict[str, Any]
    stars: int
    reason_title: str = ""
    reason_summary: str = ""
    learn_from: str = ""
    badges: List[str] = field(default_factory=list)
