# src/loom_io/shared_patterns.py
# Format-agnostic semantic matchers for resume section detection

import re
from typing import Pattern

# * Common semantic matchers shared by all document formats
# These patterns identify resume sections by heading text regardless of format
COMMON_SEMANTIC_MATCHERS: dict[str, Pattern[str]] = {
    "education": re.compile(r"\beducation\b|\bacademic", re.IGNORECASE),
    "experience": re.compile(r"\bexperience\b|\bemployment\b|\bwork\b", re.IGNORECASE),
    "projects": re.compile(r"\bprojects?\b", re.IGNORECASE),
    "skills": re.compile(r"\bskills?\b|\btechnologies\b|\btools\b", re.IGNORECASE),
    "publications": re.compile(r"\bpublications?\b|\bresearch\b", re.IGNORECASE),
    "certifications": re.compile(r"\bcertifications?\b|\blicenses?\b", re.IGNORECASE),
}


# * Infer section type from heading text using semantic matchers
def infer_section_kind(
    heading_text: str,
    extra_matchers: dict[str, Pattern[str]] | None = None,
) -> str | None:
    matchers = {**COMMON_SEMANTIC_MATCHERS, **(extra_matchers or {})}
    for kind, pattern in matchers.items():
        if pattern.search(heading_text):
            return kind
    return None


__all__ = [
    "COMMON_SEMANTIC_MATCHERS",
    "infer_section_kind",
]
