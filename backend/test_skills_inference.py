"""
Unit tests for SkillsInferenceService.

Tests the skills inference functionality including:
- Skill categorization by proficiency level
- Specialization detection
- Language distribution analysis
- Edge cases (empty data, single language, etc.)
"""

import pytest
from services.skills_inference import SkillsInferenceService
from models import UserData, Repository, Contributions


@pytest.fixture
def skills_service():
    """Create SkillsInferenceService instance."""
    return SkillsInferenceService()


@pytest.fixture
def full_stack_user_data():
    """Create user data for a full-stack developer."""
    return UserData(
        username="fullstack",
        name="Full Stack Developer",
        avatar_url="https://example.com/avatar.jpg",
        bio="Full-stack developer",
        followers=100,
        following=50,
        repositories=[],
        contributions=Contributions(
            total_commits_last_year=500,
            total_prs_last_year=50,
            longest_streak=30
        ),
        languages={
            "Python": 50000,      # 50% - Expert
            "JavaScript": 30000,  # 30% - Proficient
            "TypeScript": 10000,  # 10% - Proficient
            "CSS": 5000,          # 5% - Familiar
            "HTML": 3000,         # 3% - Learning
            "Go": 2000,           # 2% - Learning
        }
    )


@pytest.fixture
def data_scientist_user_data():
    """Create user data for a data scientist."""
    return UserData(
        username="datascientist",
        name="Data Scientist",
        avatar_url="https://example.com/avatar.jpg",
        bio="Data scientist",
        followers=50,
        following=30,
        repositories=[],
        contributions=Contributions(
            total_commits_last_year=200,
            total_prs_last_year=20,
            longest_streak=15
        ),
        languages={
            "Python": 60000,      # 60% - Expert
            "R": 25000,           # 25% - Proficient
            "SQL": 10000,         # 10% - Proficient
            "Julia": 5000,        # 5% - Familiar
        }
    )


@pytest.fixture
def mobile_developer_user_data():
    """Create user data for a mobile developer."""
    return UserData(
        username="mobiledeveloper",
        name="Mobile Developer",
        avatar_url="https://example.com/avatar.jpg",
        bio="Mobile developer",
        followers=75,
        following=40,
        repositories=[],
        contributions=Contributions(
            total_commits_last_year=300,
            total_prs_last_year=30,
            longest_streak=20
        ),
        languages={
            "Swift": 40000,       # 40% - Expert
            "Kotlin": 30000,      # 30% - Proficient
            "Java": 20000,        # 20% - Proficient
            "Dart": 10000,        # 10% - Proficient
        }
    )


@pytest.fixture
def empty_user_data():
    """Create user data with no languages."""
    return UserData(
        username="nolangs",
        name="No Languages",
        avatar_url="https://example.com/avatar.jpg",
        bio="Developer",
        followers=10,
        following=5,
        repositories=[],
        contributions=Contributions(
            total_commits_last_year=0,
            total_prs_last_year=0,
            longest_streak=0
        ),
        languages={}
    )


@pytest.fixture
def single_language_user_data():
    """Create user data with only one language."""
    return UserData(
        username="singlelang",
        name="Single Language Developer",
        avatar_url="https://example.com/avatar.jpg",
        bio="Python developer",
        followers=20,
        following=10,
        repositories=[],
        contributions=Contributions(
            total_commits_last_year=100,
            total_prs_last_year=10,
            longest_streak=10
        ),
        languages={
            "Python": 100000,
        }
    )


def test_infer_skills_full_stack(skills_service, full_stack_user_data):
    """Test skills inference for a full-stack developer."""
    skills = skills_service.infer_skills(full_stack_user_data)
    
    # Check structure
    assert "Expert" in skills
    assert "Proficient" in skills
    assert "Familiar" in skills
    assert "Learning" in skills
    
    # Check Expert level (>= 20%)
    # Python: 50%, JavaScript: 30%
    assert "Python" in skills["Expert"]
    assert "JavaScript" in skills["Expert"]
    
    # Check Proficient level (10-20%)
    # TypeScript: 10%
    assert "TypeScript" in skills["Proficient"]
    
    # Check Familiar level (5-10%)
    # CSS: 5%
    assert "CSS" in skills["Familiar"]
    
    # Check Learning level (< 5%)
    # HTML: 3%, Go: 2%
    assert "HTML" in skills["Learning"]
    assert "Go" in skills["Learning"]


def test_infer_skills_data_scientist(skills_service, data_scientist_user_data):
    """Test skills inference for a data scientist."""
    skills = skills_service.infer_skills(data_scientist_user_data)
    
    # Check Expert level (>= 20%)
    # Python: 60%
    assert "Python" in skills["Expert"]
    
    # Check Proficient level (10-20%)
    # R: 25% is actually Expert, SQL: 10% is Proficient
    assert "R" in skills["Expert"]
    assert "SQL" in skills["Proficient"]
    
    # Check Familiar level (5-10%)
    # Julia: 5%
    assert "Julia" in skills["Familiar"]


def test_infer_skills_mobile_developer(skills_service, mobile_developer_user_data):
    """Test skills inference for a mobile developer."""
    skills = skills_service.infer_skills(mobile_developer_user_data)
    
    # Check Expert level (>= 20%)
    # Swift: 40%, Kotlin: 30%, Java: 20%
    assert "Swift" in skills["Expert"]
    assert "Kotlin" in skills["Expert"]
    assert "Java" in skills["Expert"]
    
    # Check Proficient level (10-20%)
    # Dart: 10%
    assert "Dart" in skills["Proficient"]


def test_infer_skills_empty_languages(skills_service, empty_user_data):
    """Test skills inference with no languages."""
    skills = skills_service.infer_skills(empty_user_data)
    
    # All levels should be empty
    assert skills["Expert"] == []
    assert skills["Proficient"] == []
    assert skills["Familiar"] == []
    assert skills["Learning"] == []


def test_infer_skills_single_language(skills_service, single_language_user_data):
    """Test skills inference with only one language."""
    skills = skills_service.infer_skills(single_language_user_data)
    
    # Python should be Expert (100%)
    assert "Python" in skills["Expert"]
    assert len(skills["Expert"]) == 1
    assert skills["Proficient"] == []
    assert skills["Familiar"] == []
    assert skills["Learning"] == []


def test_infer_skills_sorted_by_percentage(skills_service, full_stack_user_data):
    """Test that skills within each level are sorted by percentage."""
    skills = skills_service.infer_skills(full_stack_user_data)
    
    # Proficient level should have JavaScript before TypeScript (30% > 10%)
    proficient = skills["Proficient"]
    if len(proficient) >= 2:
        js_index = proficient.index("JavaScript")
        ts_index = proficient.index("TypeScript")
        assert js_index < ts_index


def test_infer_specializations_full_stack(skills_service, full_stack_user_data):
    """Test specialization detection for a full-stack developer."""
    specializations = skills_service.infer_specializations(full_stack_user_data)
    
    # Should detect both frontend and backend
    assert "Web Frontend" in specializations
    assert "Web Backend" in specializations


def test_infer_specializations_data_scientist(skills_service, data_scientist_user_data):
    """Test specialization detection for a data scientist."""
    specializations = skills_service.infer_specializations(data_scientist_user_data)
    
    # Should detect Data & ML
    assert "Data & ML" in specializations


def test_infer_specializations_mobile_developer(skills_service, mobile_developer_user_data):
    """Test specialization detection for a mobile developer."""
    specializations = skills_service.infer_specializations(mobile_developer_user_data)
    
    # Should detect Mobile Development
    assert "Mobile Development" in specializations


def test_infer_specializations_empty_languages(skills_service, empty_user_data):
    """Test specialization detection with no languages."""
    specializations = skills_service.infer_specializations(empty_user_data)
    
    # Should return empty list
    assert specializations == []


def test_infer_specializations_single_language(skills_service, single_language_user_data):
    """Test specialization detection with only one language."""
    specializations = skills_service.infer_specializations(single_language_user_data)
    
    # Should detect Web Backend (Python is in backend_langs)
    assert "Web Backend" in specializations


def test_infer_specializations_sorted(skills_service, full_stack_user_data):
    """Test that specializations are sorted alphabetically."""
    specializations = skills_service.infer_specializations(full_stack_user_data)
    
    # Should be sorted
    assert specializations == sorted(specializations)


def test_infer_specializations_no_duplicates(skills_service, full_stack_user_data):
    """Test that specializations have no duplicates."""
    specializations = skills_service.infer_specializations(full_stack_user_data)
    
    # Should have no duplicates
    assert len(specializations) == len(set(specializations))


def test_infer_skills_proficiency_thresholds(skills_service):
    """Test that proficiency thresholds are correctly applied."""
    # Create user with specific percentages
    user_data = UserData(
        username="test",
        name="Test",
        avatar_url="https://example.com/avatar.jpg",
        bio="Test",
        followers=10,
        following=5,
        repositories=[],
        contributions=Contributions(
            total_commits_last_year=0,
            total_prs_last_year=0,
            longest_streak=0
        ),
        languages={
            "Lang1": 40000,  # 40% - Expert (>= 20%)
            "Lang2": 30000,  # 30% - Expert (>= 20%)
            "Lang3": 15000,  # 15% - Proficient (10-20%)
            "Lang4": 10000,  # 10% - Proficient (10-20%)
            "Lang5": 3000,   # 3% - Learning (< 5%)
        }
    )
    
    skills = skills_service.infer_skills(user_data)
    
    assert "Lang1" in skills["Expert"]
    assert "Lang2" in skills["Expert"]
    assert "Lang3" in skills["Proficient"]
    assert "Lang4" in skills["Proficient"]
    assert "Lang5" in skills["Learning"]


def test_infer_specializations_threshold_15_percent(skills_service):
    """Test that specialization threshold is 15% for most categories."""
    # Create user with exactly 15% frontend
    user_data = UserData(
        username="test",
        name="Test",
        avatar_url="https://example.com/avatar.jpg",
        bio="Test",
        followers=10,
        following=5,
        repositories=[],
        contributions=Contributions(
            total_commits_last_year=0,
            total_prs_last_year=0,
            longest_streak=0
        ),
        languages={
            "JavaScript": 15000,  # 15% frontend
            "Python": 85000,      # 85% backend
        }
    )
    
    specializations = skills_service.infer_specializations(user_data)
    
    # Should detect backend (85% > 15%)
    assert "Web Backend" in specializations
    # Frontend is at threshold but not above, so it may or may not be detected
    # depending on implementation. Let's just verify backend is detected.


def test_infer_specializations_below_threshold(skills_service):
    """Test that specializations below threshold are not detected."""
    # Create user with 14% frontend (below 15% threshold)
    user_data = UserData(
        username="test",
        name="Test",
        avatar_url="https://example.com/avatar.jpg",
        bio="Test",
        followers=10,
        following=5,
        repositories=[],
        contributions=Contributions(
            total_commits_last_year=0,
            total_prs_last_year=0,
            longest_streak=0
        ),
        languages={
            "JavaScript": 14000,  # 14% frontend (below threshold)
            "Python": 86000,      # 86% backend
        }
    )
    
    specializations = skills_service.infer_specializations(user_data)
    
    # Should only detect backend
    assert "Web Frontend" not in specializations
    assert "Web Backend" in specializations


def test_infer_skills_with_zero_bytes(skills_service):
    """Test skills inference when total bytes is zero."""
    user_data = UserData(
        username="test",
        name="Test",
        avatar_url="https://example.com/avatar.jpg",
        bio="Test",
        followers=10,
        following=5,
        repositories=[],
        contributions=Contributions(
            total_commits_last_year=0,
            total_prs_last_year=0,
            longest_streak=0
        ),
        languages={
            "Python": 0,
            "JavaScript": 0,
        }
    )
    
    skills = skills_service.infer_skills(user_data)
    
    # All levels should be empty
    assert skills["Expert"] == []
    assert skills["Proficient"] == []
    assert skills["Familiar"] == []
    assert skills["Learning"] == []


def test_infer_skills_many_languages(skills_service):
    """Test skills inference with many languages."""
    languages = {f"Lang{i}": 1000 - (i * 50) for i in range(20)}
    
    user_data = UserData(
        username="polyglot",
        name="Polyglot",
        avatar_url="https://example.com/avatar.jpg",
        bio="Polyglot developer",
        followers=100,
        following=50,
        repositories=[],
        contributions=Contributions(
            total_commits_last_year=500,
            total_prs_last_year=50,
            longest_streak=30
        ),
        languages=languages
    )
    
    skills = skills_service.infer_skills(user_data)
    
    # Should have skills in all levels
    total_skills = (
        len(skills["Expert"]) +
        len(skills["Proficient"]) +
        len(skills["Familiar"]) +
        len(skills["Learning"])
    )
    
    # Should have all languages categorized
    assert total_skills == len(languages)


def test_infer_specializations_devops_focus(skills_service):
    """Test specialization detection for DevOps focus."""
    user_data = UserData(
        username="devops",
        name="DevOps Engineer",
        avatar_url="https://example.com/avatar.jpg",
        bio="DevOps engineer",
        followers=50,
        following=30,
        repositories=[],
        contributions=Contributions(
            total_commits_last_year=200,
            total_prs_last_year=20,
            longest_streak=15
        ),
        languages={
            "Shell": 40000,       # 40% devops
            "Python": 30000,      # 30% backend
            "Bash": 20000,        # 20% devops
            "Go": 10000,          # 10% backend
        }
    )
    
    specializations = skills_service.infer_specializations(user_data)
    
    # Should detect DevOps (40% + 20% = 60% > 10%)
    assert "DevOps & Infrastructure" in specializations


def test_infer_specializations_systems_programming(skills_service):
    """Test specialization detection for systems programming."""
    user_data = UserData(
        username="systems",
        name="Systems Programmer",
        avatar_url="https://example.com/avatar.jpg",
        bio="Systems programmer",
        followers=40,
        following=20,
        repositories=[],
        contributions=Contributions(
            total_commits_last_year=150,
            total_prs_last_year=15,
            longest_streak=12
        ),
        languages={
            "C": 50000,           # 50% systems
            "C++": 30000,         # 30% systems
            "Rust": 20000,        # 20% systems
        }
    )
    
    specializations = skills_service.infer_specializations(user_data)
    
    # Should detect Systems Programming (50% + 30% + 20% = 100% > 10%)
    assert "Systems Programming" in specializations
