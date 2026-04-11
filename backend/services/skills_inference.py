"""
SkillsInferenceService: Infer technical skills from GitHub data.
"""

from typing import Dict, List, Set
from models import UserData, Repository


class SkillsInferenceService:
    """Service for inferring technical skills from GitHub data."""

    # Mapping of programming languages to skill categories
    LANGUAGE_CATEGORIES = {
        # Web Frontend
        "JavaScript": "Web Frontend",
        "TypeScript": "Web Frontend",
        "React": "Web Frontend",
        "Vue": "Web Frontend",
        "Angular": "Web Frontend",
        "CSS": "Web Frontend",
        "HTML": "Web Frontend",
        "Svelte": "Web Frontend",
        
        # Web Backend
        "Python": "Web Backend",
        "Java": "Web Backend",
        "Go": "Web Backend",
        "Rust": "Web Backend",
        "C#": "Web Backend",
        "PHP": "Web Backend",
        "Ruby": "Web Backend",
        "Node.js": "Web Backend",
        "Express": "Web Backend",
        "Django": "Web Backend",
        "FastAPI": "Web Backend",
        "Spring": "Web Backend",
        
        # Mobile
        "Swift": "Mobile",
        "Kotlin": "Mobile",
        "Objective-C": "Mobile",
        "Dart": "Mobile",
        "React Native": "Mobile",
        "Flutter": "Mobile",
        
        # Data & ML
        "Python": "Data & ML",
        "R": "Data & ML",
        "SQL": "Data & ML",
        "Scala": "Data & ML",
        "Julia": "Data & ML",
        
        # DevOps & Infrastructure
        "Shell": "DevOps & Infrastructure",
        "Bash": "DevOps & Infrastructure",
        "Docker": "DevOps & Infrastructure",
        "Kubernetes": "DevOps & Infrastructure",
        "Terraform": "DevOps & Infrastructure",
        "CloudFormation": "DevOps & Infrastructure",
        
        # Systems & Low-level
        "C": "Systems & Low-level",
        "C++": "Systems & Low-level",
        "Assembly": "Systems & Low-level",
        "Rust": "Systems & Low-level",
    }

    # Proficiency level thresholds (percentage of total code)
    PROFICIENCY_THRESHOLDS = {
        "Expert": 0.20,      # 20%+ of codebase
        "Proficient": 0.10,  # 10-20% of codebase
        "Familiar": 0.05,    # 5-10% of codebase
        "Learning": 0.0,     # <5% of codebase
    }

    def infer_skills(self, user_data: UserData) -> Dict[str, List[str]]:
        """
        Infer technical skills from GitHub data.
        
        Returns a dictionary with proficiency levels as keys and skill lists as values:
        {
            "Expert": ["Python", "JavaScript", ...],
            "Proficient": ["React", "Django", ...],
            "Familiar": ["Go", "Rust", ...],
            "Learning": ["Kotlin", "Swift", ...]
        }
        """
        if not user_data.languages:
            return {
                "Expert": [],
                "Proficient": [],
                "Familiar": [],
                "Learning": [],
            }

        # Calculate total bytes of code
        total_bytes = sum(user_data.languages.values())
        if total_bytes == 0:
            return {
                "Expert": [],
                "Proficient": [],
                "Familiar": [],
                "Learning": [],
            }

        # Categorize languages by proficiency
        skills_by_level = {
            "Expert": [],
            "Proficient": [],
            "Familiar": [],
            "Learning": [],
        }

        for language, bytes_count in user_data.languages.items():
            percentage = bytes_count / total_bytes
            
            # Determine proficiency level
            if percentage >= self.PROFICIENCY_THRESHOLDS["Expert"]:
                level = "Expert"
            elif percentage >= self.PROFICIENCY_THRESHOLDS["Proficient"]:
                level = "Proficient"
            elif percentage >= self.PROFICIENCY_THRESHOLDS["Familiar"]:
                level = "Familiar"
            else:
                level = "Learning"
            
            skills_by_level[level].append(language)

        # Sort each level by percentage (descending)
        for level in skills_by_level:
            skills_by_level[level].sort(
                key=lambda lang: user_data.languages.get(lang, 0),
                reverse=True
            )

        return skills_by_level

    def infer_specializations(self, user_data: UserData) -> List[str]:
        """
        Infer specializations based on language distribution and project patterns.
        
        Returns a list of specialization categories the developer likely focuses on.
        """
        specializations: Set[str] = set()
        
        if not user_data.languages:
            return []

        # Analyze language distribution
        total_bytes = sum(user_data.languages.values())
        language_percentages = {
            lang: bytes_count / total_bytes
            for lang, bytes_count in user_data.languages.items()
        }

        # Check for specialization patterns
        frontend_langs = {"JavaScript", "TypeScript", "CSS", "HTML", "React", "Vue", "Angular", "Svelte"}
        backend_langs = {"Python", "Java", "Go", "Rust", "C#", "PHP", "Ruby", "Node.js"}
        mobile_langs = {"Swift", "Kotlin", "Objective-C", "Dart", "React Native", "Flutter"}
        data_langs = {"Python", "R", "SQL", "Scala", "Julia"}
        devops_langs = {"Shell", "Bash", "Docker", "Kubernetes", "Terraform"}
        systems_langs = {"C", "C++", "Assembly", "Rust"}

        # Calculate specialization scores
        frontend_score = sum(
            language_percentages.get(lang, 0)
            for lang in frontend_langs
        )
        backend_score = sum(
            language_percentages.get(lang, 0)
            for lang in backend_langs
        )
        mobile_score = sum(
            language_percentages.get(lang, 0)
            for lang in mobile_langs
        )
        data_score = sum(
            language_percentages.get(lang, 0)
            for lang in data_langs
        )
        devops_score = sum(
            language_percentages.get(lang, 0)
            for lang in devops_langs
        )
        systems_score = sum(
            language_percentages.get(lang, 0)
            for lang in systems_langs
        )

        # Add specializations if score is significant (>15% of codebase)
        if frontend_score > 0.15:
            specializations.add("Web Frontend")
        if backend_score > 0.15:
            specializations.add("Web Backend")
        if mobile_score > 0.10:
            specializations.add("Mobile Development")
        if data_score > 0.10:
            specializations.add("Data & ML")
        if devops_score > 0.10:
            specializations.add("DevOps & Infrastructure")
        if systems_score > 0.10:
            specializations.add("Systems Programming")

        # If no specializations detected, infer from top languages
        if not specializations and user_data.languages:
            top_language = max(user_data.languages.items(), key=lambda x: x[1])[0]
            if top_language in frontend_langs:
                specializations.add("Web Frontend")
            elif top_language in backend_langs:
                specializations.add("Web Backend")
            elif top_language in mobile_langs:
                specializations.add("Mobile Development")
            elif top_language in data_langs:
                specializations.add("Data & ML")
            elif top_language in devops_langs:
                specializations.add("DevOps & Infrastructure")
            elif top_language in systems_langs:
                specializations.add("Systems Programming")

        return sorted(list(specializations))
