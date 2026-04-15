from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class Repository:
    name: str
    description: str
    stars: int
    forks: int
    language: str
    has_readme: bool
    has_license: bool
    url: str
    pushed_at: str = ""
    topics: List[str] = field(default_factory=list)
    readme_text: str = ""
    file_tree: List[str] = field(default_factory=list)
    languages: Dict[str, int] = field(default_factory=dict)

@dataclass
class ContributionDay:
    date: str
    contribution_count: int

@dataclass
class Contributions:
    total_commits_last_year: int
    total_prs_last_year: int
    longest_streak: int
    contribution_days: List[ContributionDay]
    issues_opened_last_year: int = 0

@dataclass
class UserData:
    username: str
    name: str
    avatar_url: str
    bio: str
    followers: int
    following: int
    repositories: List[Repository]
    contributions: Contributions
    languages: Dict[str, int]  # language -> bytes of code

@dataclass
class GitScore:
    total: float  # 0-100
    dimensions: Dict[str, float]  # impact, contribution, community, tech_breadth, documentation

@dataclass
class AIInsights:
    style_tags: List[str]
    roast_comment: str
    tech_summary: str

@dataclass
class CardData:
    username: str
    avatar_url: str
    gitscore: float
    radar_chart_data: List[float]  # 5 dimension values
    style_tags: List[str]
    roast_comment: str
    tech_icons: List[str]  # URLs or names of tech stack icons


@dataclass
class RepositoryAIAnalysis:
    repo_name: str
    title: str
    summary: str
    highlights: List[str]
    keywords: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)

@dataclass
class GenerateRequest:
    username: str
    language: str = "en"  # "en" or "zh"

@dataclass
class GenerateResponse:
    resume_markdown: str
    gitscore: GitScore
    ai_insights: AIInsights
    card_data: CardData
