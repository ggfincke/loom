# src/core/comparison_matrix.py
# Pure scoring & aggregation logic for bulk results - no I/O dependencies

from __future__ import annotations

import json
import re
from collections import Counter

from .bulk_types import (
    JobResult,
    EditBreakdown,
    KeywordCoverage,
    ValidationSummary,
)


# multi-word tech terms to recognize
MULTI_WORD_TERMS = [
    "machine learning",
    "deep learning",
    "natural language processing",
    "distributed systems",
    "event-driven",
    "microservices architecture",
    "continuous integration",
    "continuous deployment",
    "infrastructure as code",
    "test-driven development",
    "object-oriented programming",
    "functional programming",
    "data engineering",
    "data science",
    "cloud native",
    "high availability",
    "real-time",
    "full-stack",
    "front-end",
    "back-end",
]

# single-word tech patterns
TECH_PATTERNS = [
    r"\b(Python|Java|JavaScript|TypeScript|Go|Rust|C\+\+|C#|Ruby|PHP|Swift|Kotlin|Scala)\b",
    r"\b(React|Angular|Vue|Next\.js|Node\.js|Django|Flask|FastAPI|Spring|Rails|Express)\b",
    r"\b(AWS|Azure|GCP|Docker|Kubernetes|Terraform|Ansible|Jenkins|CircleCI|GitHub Actions)\b",
    r"\b(PostgreSQL|MySQL|MongoDB|Redis|Elasticsearch|Kafka|RabbitMQ|DynamoDB|Cassandra)\b",
    r"\b(REST|GraphQL|gRPC|WebSocket|HTTP|HTTPS)\b",
    r"\b(Linux|Unix|Bash|Shell|PowerShell)\b",
    r"\b(Git|GitHub|GitLab|Bitbucket)\b",
    r"\b(Agile|Scrum|Kanban)\b",
    r"\b(SQL|NoSQL|ORM)\b",
    r"\b(HTML|CSS|SASS|LESS)\b",
]


# * Calculate fit score from job result components
# weighted score: required_coverage * 0.6 + preferred_coverage * 0.2 + impact_score * 0.2 - validation penalty
def calculate_fit_score(result: JobResult) -> float:
    required = result.coverage.required_ratio
    preferred = result.coverage.preferred_ratio

    # impact_score: normalize edit count (diminishing returns after 10 edits)
    edit_impact = min(result.edits.total_count / 10.0, 1.0)

    # validation penalty (max 0.3)
    validation_penalty = min(result.validation.total_warnings * 0.05, 0.3)

    raw_score = (required * 0.6) + (preferred * 0.2) + (edit_impact * 0.2)
    return max(0.0, min(1.0, raw_score - validation_penalty))


# * Map line numbers to section names using sections.json structure
def _map_lines_to_sections(lines_touched: set[int], sections_json: str) -> list[str]:
    try:
        data = json.loads(sections_json)
    except (json.JSONDecodeError, TypeError):
        return []

    touched_sections: set[str] = set()
    sections = data.get("sections", [])

    def check_section(section: dict) -> None:
        # check if any touched line falls within this section's range
        start = section.get("start_line", 0)
        end = section.get("end_line", 0)
        name = section.get("name", "UNKNOWN")

        for line in lines_touched:
            if start <= line <= end:
                touched_sections.add(name)
                break

        # also check subsections (e.g., individual jobs within EXPERIENCE)
        for subsection in section.get("subsections", []):
            check_section(subsection)

    for section in sections:
        check_section(section)

    return sorted(touched_sections)


# * Analyze edits dict to produce EditBreakdown
# extract edit statistics from edits.json structure
def analyze_edits(edits: dict, sections_json: str | None = None) -> EditBreakdown:
    ops = edits.get("ops", [])

    inserts = 0
    deletes = 0
    replacements = 0
    lines_touched: set[int] = set()

    for op in ops:
        op_type = op.get("op")

        if op_type == "insert_after":
            inserts += 1
            line = op.get("l") or op.get("line")
            if line:
                lines_touched.add(line)

        elif op_type == "delete_range":
            deletes += 1
            start = op.get("s") or op.get("start")
            end = op.get("e") or op.get("end")
            if start and end:
                lines_touched.update(range(start, end + 1))

        elif op_type in ("replace_line", "replace_range"):
            replacements += 1
            if op_type == "replace_line":
                line = op.get("l") or op.get("line")
                if line:
                    lines_touched.add(line)
            else:
                start = op.get("s") or op.get("start")
                end = op.get("e") or op.get("end")
                if start and end:
                    lines_touched.update(range(start, end + 1))

    # map lines to sections if sections_json provided
    sections_touched: list[str] = []
    if sections_json:
        sections_touched = _map_lines_to_sections(lines_touched, sections_json)

    return EditBreakdown(
        total_count=len(ops),
        lines_touched=len(lines_touched),
        sections_touched=sections_touched,
        inserts=inserts,
        replacements=replacements,
        deletes=deletes,
    )


# * Extract required & preferred keywords from job description
# extract required & preferred keywords w/ section-aware parsing; returns sorted lists for deterministic output
def extract_job_keywords(job_text: str) -> tuple[list[str], list[str]]:
    required: set[str] = set()
    preferred: set[str] = set()

    lines = job_text.split("\n")
    in_required = True  # default to required section

    for line in lines:
        line_lower = line.lower()

        # detect section headers
        if any(
            kw in line_lower
            for kw in ["required", "must have", "requirements", "qualifications", "minimum"]
        ):
            in_required = True
        elif any(
            kw in line_lower
            for kw in ["preferred", "nice to have", "bonus", "plus", "desired"]
        ):
            in_required = False

        target = required if in_required else preferred

        # extract multi-word terms from this line
        for term in MULTI_WORD_TERMS:
            if term in line_lower:
                target.add(term)

        # extract single-word terms from this line
        for pattern in TECH_PATTERNS:
            for match in re.findall(pattern, line, re.IGNORECASE):
                target.add(match)

    # return sorted for determinism
    return sorted(required, key=str.lower), sorted(preferred, key=str.lower)


# * Calculate keyword coverage for a resume against job keywords
# calculate how many job keywords appear in resume
def calculate_keyword_coverage(
    resume_text: str,
    required_keywords: list[str],
    preferred_keywords: list[str],
) -> KeywordCoverage:
    resume_lower = resume_text.lower()

    required_matched = sum(1 for kw in required_keywords if kw.lower() in resume_lower)
    preferred_matched = sum(1 for kw in preferred_keywords if kw.lower() in resume_lower)

    missing_required = [kw for kw in required_keywords if kw.lower() not in resume_lower]

    return KeywordCoverage(
        required_matched=required_matched,
        required_total=len(required_keywords),
        preferred_matched=preferred_matched,
        preferred_total=len(preferred_keywords),
        missing_required=missing_required[:10],
    )


# * Detect keyword stuffing in tailored resume
# heuristic: detect if same keyword appears too many times; returns 0.0 (no stuffing) to 1.0 (severe stuffing)
def detect_keyword_stuffing(resume_text: str) -> float:
    words = re.findall(r"\b\w+\b", resume_text.lower())
    word_counts = Counter(words)

    # filter to meaningful words (length > 4)
    meaningful = {w: c for w, c in word_counts.items() if len(w) > 4}

    if not meaningful:
        return 0.0

    # count words appearing > 5 times (suspicious)
    stuffed_words = sum(1 for c in meaningful.values() if c > 5)

    return min(stuffed_words / 10.0, 1.0)


# * Categorize validation warnings by severity
# categorize validation warnings into severity buckets
def categorize_warnings(warnings: list[str]) -> dict[str, int]:
    categories: dict[str, int] = {
        "bounds": 0,
        "duplicate": 0,
        "mismatch": 0,
        "missing": 0,
        "other": 0,
    }

    for warning in warnings:
        warning_lower = warning.lower()
        if "bounds" in warning_lower or "not in resume" in warning_lower:
            categories["bounds"] += 1
        elif "duplicate" in warning_lower:
            categories["duplicate"] += 1
        elif "mismatch" in warning_lower:
            categories["mismatch"] += 1
        elif "missing" in warning_lower:
            categories["missing"] += 1
        else:
            categories["other"] += 1

    # remove zero counts
    return {k: v for k, v in categories.items() if v > 0}


# * Count potential unsafe claims in edits
# heuristic: count edits that might introduce unverifiable claims (numbers, percentages, scope escalation words)
def count_unsafe_claims(edits: dict) -> int:
    unsafe_patterns = [
        r"\b\d+%",  # percentages
        r"\$\d+",  # dollar amounts
        r"\b(led|owned|architected|spearheaded)\b",  # scope escalation
        r"\b\d+\s*(million|billion|k|K)\b",  # large numbers
    ]

    count = 0
    ops = edits.get("ops", [])

    for op in ops:
        text = op.get("t") or op.get("text") or ""
        for pattern in unsafe_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                count += 1
                break  # only count once per op

    return count


# * Build ValidationSummary from warnings list
# build ValidationSummary from validation warnings & edits
def build_validation_summary(warnings: list[str], edits: dict) -> ValidationSummary:
    return ValidationSummary(
        warnings_by_severity=categorize_warnings(warnings),
        total_warnings=len(warnings),
        unsafe_claims=count_unsafe_claims(edits),
    )
