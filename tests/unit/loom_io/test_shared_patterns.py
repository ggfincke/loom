# tests/unit/loom_io/test_shared_patterns.py
# Unit tests for shared semantic matchers

import re

import pytest

from src.loom_io.shared_patterns import (
    COMMON_SEMANTIC_MATCHERS,
    infer_section_kind,
)


# * Test all expected common matchers exist
def test_common_matchers_exist():
    expected_keys = {
        "education",
        "experience",
        "projects",
        "skills",
        "publications",
        "certifications",
    }
    assert set(COMMON_SEMANTIC_MATCHERS.keys()) == expected_keys


# * Test each matcher is a compiled regex pattern
def test_common_matchers_are_patterns():
    for key, pattern in COMMON_SEMANTIC_MATCHERS.items():
        assert hasattr(pattern, "search"), f"{key} is not a regex pattern"


# * Test infer_section_kind matches education headings
def test_infer_section_kind_matches_education():
    assert infer_section_kind("Education") == "education"
    assert infer_section_kind("EDUCATION") == "education"
    assert infer_section_kind("Academic Background") == "education"


# * Test infer_section_kind matches experience headings
def test_infer_section_kind_matches_experience():
    assert infer_section_kind("Experience") == "experience"
    assert infer_section_kind("Work Experience") == "experience"
    assert infer_section_kind("Professional Experience") == "experience"
    assert infer_section_kind("Employment History") == "experience"


# * Test infer_section_kind matches project headings
def test_infer_section_kind_matches_projects():
    assert infer_section_kind("Projects") == "projects"
    assert infer_section_kind("Project Portfolio") == "projects"
    assert infer_section_kind("Personal Projects") == "projects"


# * Test infer_section_kind matches skill headings
def test_infer_section_kind_matches_skills():
    assert infer_section_kind("Skills") == "skills"
    assert infer_section_kind("Technical Skills") == "skills"
    assert infer_section_kind("Technologies") == "skills"
    assert infer_section_kind("Tools & Technologies") == "skills"


# * Test infer_section_kind matches publication headings
def test_infer_section_kind_matches_publications():
    assert infer_section_kind("Publications") == "publications"
    assert infer_section_kind("Research Papers") == "publications"


# * Test infer_section_kind matches certification headings
def test_infer_section_kind_matches_certifications():
    assert infer_section_kind("Certifications") == "certifications"
    assert infer_section_kind("Licenses & Certifications") == "certifications"


# * Test infer_section_kind returns None for unknown headings
def test_infer_section_kind_returns_none_for_unknown():
    assert infer_section_kind("Contact Information") is None
    assert infer_section_kind("Hobbies") is None
    assert infer_section_kind("Random Section") is None


# * Test infer_section_kind with extra matchers
def test_infer_section_kind_with_extra_matchers():
    extra = {
        "summary": re.compile(r"\bsummary\b|\bobjective\b", re.IGNORECASE),
    }

    assert infer_section_kind("Professional Summary", extra_matchers=extra) == "summary"
    assert infer_section_kind("Career Objective", extra_matchers=extra) == "summary"


# * Test extra matchers override common matchers
def test_extra_matchers_override_common():
    # Override "experience" with a different pattern
    extra = {
        "experience": re.compile(r"\bwork\s+history\b", re.IGNORECASE),
    }

    # "Experience" alone should NOT match the overridden pattern
    assert infer_section_kind("Experience", extra_matchers=extra) is None
    # But "Work History" should
    assert infer_section_kind("Work History", extra_matchers=extra) == "experience"


# * Test infer_section_kind is case-insensitive
def test_infer_section_kind_case_insensitive():
    assert infer_section_kind("EDUCATION") == "education"
    assert infer_section_kind("education") == "education"
    assert infer_section_kind("Education") == "education"
    assert infer_section_kind("eDuCaTiOn") == "education"


# * Test empty string returns None
def test_infer_section_kind_empty_string():
    assert infer_section_kind("") is None


# * Test whitespace-only string returns None
def test_infer_section_kind_whitespace():
    assert infer_section_kind("   ") is None
