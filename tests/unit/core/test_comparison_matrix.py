# tests/unit/core/test_comparison_matrix.py
# Unit tests for comparison matrix scoring & keyword extraction

import pytest

from src.core.comparison_matrix import (
    extract_job_keywords,
    calculate_keyword_coverage,
    detect_keyword_stuffing,
    analyze_edits,
    calculate_fit_score,
    categorize_warnings,
    count_unsafe_claims,
    build_validation_summary,
)
from src.core.bulk_types import JobResult, JobSpec, KeywordCoverage, ValidationSummary
from pathlib import Path


class TestExtractJobKeywords:
    # * Extracts common tech keywords
    def test_extracts_tech_keywords(self):
        job_text = """
        Requirements:
        - 3+ years Python experience
        - Experience with PostgreSQL
        - Familiarity with Docker
        """

        required, preferred = extract_job_keywords(job_text)

        assert "Python" in required
        assert "PostgreSQL" in required
        assert "Docker" in required

    # * Distinguishes between required & preferred sections
    def test_section_aware_extraction(self):
        job_text = """
        Requirements:
        - Python programming
        - PostgreSQL database

        Nice to Have:
        - Kubernetes experience
        - GraphQL knowledge
        """

        required, preferred = extract_job_keywords(job_text)

        assert "Python" in required
        assert "PostgreSQL" in required
        assert "Kubernetes" in preferred
        assert "GraphQL" in preferred

    # * Extracts multi-word technical terms
    def test_multi_word_terms(self):
        job_text = """
        Requirements:
        - Experience with machine learning
        - Knowledge of distributed systems
        """

        required, preferred = extract_job_keywords(job_text)

        assert "machine learning" in required
        assert "distributed systems" in required

    # * Returns deterministic sorted lists
    def test_returns_sorted_lists(self):
        job_text = """
        Requirements:
        - Terraform
        - Ansible
        - Docker
        """

        required, _ = extract_job_keywords(job_text)

        # should be sorted alphabetically (case-insensitive)
        assert required == sorted(required, key=str.lower)

    # * Same keyword appearing multiple times is deduplicated
    def test_deduplicates_keywords(self):
        job_text = """
        Requirements:
        - Python for backend
        - Python for scripting
        - More Python
        """

        required, _ = extract_job_keywords(job_text)

        assert required.count("Python") == 1


class TestCalculateKeywordCoverage:
    # * All keywords matched gives perfect coverage
    def test_full_coverage(self):
        resume = "I know Python, PostgreSQL, and Docker."
        required = ["Python", "PostgreSQL", "Docker"]
        preferred = ["Kubernetes"]

        coverage = calculate_keyword_coverage(resume, required, preferred)

        assert coverage.required_matched == 3
        assert coverage.required_total == 3
        assert coverage.required_ratio == 1.0

    # * Partial keyword match
    def test_partial_coverage(self):
        resume = "I know Python and PostgreSQL."
        required = ["Python", "PostgreSQL", "Docker", "Kubernetes"]
        preferred = []

        coverage = calculate_keyword_coverage(resume, required, preferred)

        assert coverage.required_matched == 2
        assert coverage.required_total == 4
        assert coverage.required_ratio == 0.5

    # * Missing required keywords are tracked
    def test_missing_required_tracked(self):
        resume = "I know Python."
        required = ["Python", "PostgreSQL", "Docker"]
        preferred = []

        coverage = calculate_keyword_coverage(resume, required, preferred)

        assert "PostgreSQL" in coverage.missing_required
        assert "Docker" in coverage.missing_required
        assert "Python" not in coverage.missing_required

    # * Keyword matching is case-insensitive
    def test_case_insensitive_matching(self):
        resume = "I know PYTHON and postgresql."
        required = ["Python", "PostgreSQL"]
        preferred = []

        coverage = calculate_keyword_coverage(resume, required, preferred)

        assert coverage.required_matched == 2


class TestDetectKeywordStuffing:
    # * Normal text has no stuffing
    def test_no_stuffing(self):
        resume = "I am a software engineer with Python experience."

        score = detect_keyword_stuffing(resume)

        assert score == 0.0

    # * Some repetition is acceptable
    def test_mild_repetition_ok(self):
        resume = "Python Python Python Python"  # 4 times

        score = detect_keyword_stuffing(resume)

        assert score == 0.0  # threshold is > 5

    # * Excessive repetition flagged
    def test_severe_stuffing_detected(self):
        resume = " ".join(["Python"] * 10)  # 10 times

        score = detect_keyword_stuffing(resume)

        assert score > 0.0


class TestAnalyzeEdits:
    # * Correctly counts insert/replace/delete operations
    def test_counts_operation_types(self):
        edits = {
            "ops": [
                {"op": "replace_line", "line": 5, "text": "new"},
                {"op": "replace_range", "start": 10, "end": 12, "text": "new"},
                {"op": "insert_after", "line": 15, "text": "inserted"},
                {"op": "delete_range", "start": 20, "end": 21},
            ]
        }

        breakdown = analyze_edits(edits)

        assert breakdown.total_count == 4
        assert breakdown.replacements == 2
        assert breakdown.inserts == 1
        assert breakdown.deletes == 1

    # * Counts unique lines affected
    def test_calculates_lines_touched(self):
        edits = {
            "ops": [
                {"op": "replace_line", "line": 5, "text": "new"},
                {"op": "replace_range", "start": 10, "end": 12, "text": "new"},
            ]
        }

        breakdown = analyze_edits(edits)

        # line 5 + lines 10, 11, 12 = 4 lines
        assert breakdown.lines_touched == 4

    # * Handles empty ops list
    def test_empty_ops(self):
        edits = {"ops": []}

        breakdown = analyze_edits(edits)

        assert breakdown.total_count == 0


class TestCalculateFitScore:
    # * Perfect keyword coverage gives high score
    def test_perfect_coverage_high_score(self):
        result = JobResult(
            spec=JobSpec(path=Path("job.txt"), id="test"),
            coverage=KeywordCoverage(
                required_matched=5,
                required_total=5,
                preferred_matched=3,
                preferred_total=3,
            ),
        )
        result.edits.total_count = 5

        score = calculate_fit_score(result)

        assert score > 0.8

    # * Validation warnings reduce score
    def test_validation_penalty(self):
        result = JobResult(
            spec=JobSpec(path=Path("job.txt"), id="test"),
            coverage=KeywordCoverage(
                required_matched=5,
                required_total=5,
            ),
            validation=ValidationSummary(total_warnings=5),
        )

        score = calculate_fit_score(result)

        # 5 warnings * 0.05 = 0.25 penalty
        assert score < 0.8

    # * Score is bounded to [0, 1]
    def test_score_bounds(self):
        # terrible result
        result = JobResult(
            spec=JobSpec(path=Path("job.txt"), id="test"),
            coverage=KeywordCoverage(
                required_matched=0,
                required_total=10,
            ),
            validation=ValidationSummary(total_warnings=10),
        )

        score = calculate_fit_score(result)

        assert 0.0 <= score <= 1.0


class TestCategorizeWarnings:
    # * Bounds warnings categorized correctly
    def test_categorizes_bounds_warnings(self):
        warnings = ["Op 1: line 50 not in resume bounds"]

        categories = categorize_warnings(warnings)

        assert categories.get("bounds", 0) == 1

    # * Duplicate warnings categorized correctly
    def test_categorizes_duplicate_warnings(self):
        warnings = ["Op 2: duplicate operation on line 5"]

        categories = categorize_warnings(warnings)

        assert categories.get("duplicate", 0) == 1

    # * Zero-count categories are excluded
    def test_removes_zero_counts(self):
        warnings = ["Op 1: duplicate operation"]

        categories = categorize_warnings(warnings)

        assert "bounds" not in categories
        assert "mismatch" not in categories


class TestCountUnsafeClaims:
    # * Percentages flagged as unsafe
    def test_detects_percentages(self):
        edits = {"ops": [{"op": "replace_line", "text": "Improved performance by 50%"}]}

        count = count_unsafe_claims(edits)

        assert count == 1

    # * Scope escalation words flagged
    def test_detects_scope_escalation(self):
        edits = {"ops": [{"op": "replace_line", "text": "Led team of engineers"}]}

        count = count_unsafe_claims(edits)

        assert count == 1

    # * Normal text not flagged
    def test_normal_text_ok(self):
        edits = {"ops": [{"op": "replace_line", "text": "Developed backend services"}]}

        count = count_unsafe_claims(edits)

        assert count == 0


class TestSectionsTouched:
    # * Maps lines to correct sections
    def test_maps_lines_to_sections(self):
        sections_json = """{
            "sections": [
                {"name": "EXPERIENCE", "start_line": 10, "end_line": 25, "subsections": []},
                {"name": "SKILLS", "start_line": 30, "end_line": 40, "subsections": []}
            ]
        }"""
        edits = {
            "ops": [
                {"op": "replace_line", "line": 15, "text": "new text"},
                {"op": "replace_line", "line": 35, "text": "more text"},
            ]
        }

        breakdown = analyze_edits(edits, sections_json=sections_json)

        assert "EXPERIENCE" in breakdown.sections_touched
        assert "SKILLS" in breakdown.sections_touched
        assert len(breakdown.sections_touched) == 2

    # * Single section touched
    def test_single_section_touched(self):
        sections_json = """{
            "sections": [
                {"name": "EXPERIENCE", "start_line": 10, "end_line": 25, "subsections": []},
                {"name": "SKILLS", "start_line": 30, "end_line": 40, "subsections": []}
            ]
        }"""
        edits = {"ops": [{"op": "replace_line", "line": 15, "text": "new text"}]}

        breakdown = analyze_edits(edits, sections_json=sections_json)

        assert breakdown.sections_touched == ["EXPERIENCE"]

    # * Lines outside all sections not mapped
    def test_no_overlap(self):
        sections_json = """{
            "sections": [
                {"name": "EXPERIENCE", "start_line": 10, "end_line": 25, "subsections": []}
            ]
        }"""
        edits = {"ops": [{"op": "replace_line", "line": 50, "text": "new text"}]}

        breakdown = analyze_edits(edits, sections_json=sections_json)

        assert breakdown.sections_touched == []

    # * Handles nested subsections
    def test_handles_subsections(self):
        sections_json = """{
            "sections": [
                {
                    "name": "EXPERIENCE",
                    "start_line": 10,
                    "end_line": 50,
                    "subsections": [
                        {"name": "JOB", "start_line": 15, "end_line": 25},
                        {"name": "JOB", "start_line": 30, "end_line": 40}
                    ]
                }
            ]
        }"""
        edits = {"ops": [{"op": "replace_line", "line": 20, "text": "new text"}]}

        breakdown = analyze_edits(edits, sections_json=sections_json)

        # should match both parent EXPERIENCE and nested JOB
        assert "EXPERIENCE" in breakdown.sections_touched
        assert "JOB" in breakdown.sections_touched

    # * Graceful handling of invalid JSON
    def test_invalid_json_returns_empty(self):
        sections_json = "not valid json {{{"
        edits = {"ops": [{"op": "replace_line", "line": 15, "text": "new text"}]}

        breakdown = analyze_edits(edits, sections_json=sections_json)

        assert breakdown.sections_touched == []

    # * No sections_json returns empty list
    def test_no_sections_json_returns_empty(self):
        edits = {"ops": [{"op": "replace_line", "line": 15, "text": "new text"}]}

        breakdown = analyze_edits(edits, sections_json=None)

        assert breakdown.sections_touched == []

    # * Results are sorted alphabetically
    def test_results_sorted(self):
        sections_json = """{
            "sections": [
                {"name": "SKILLS", "start_line": 10, "end_line": 20, "subsections": []},
                {"name": "EDUCATION", "start_line": 25, "end_line": 35, "subsections": []},
                {"name": "EXPERIENCE", "start_line": 40, "end_line": 50, "subsections": []}
            ]
        }"""
        edits = {
            "ops": [
                {"op": "replace_line", "line": 15, "text": "skills edit"},
                {"op": "replace_line", "line": 30, "text": "edu edit"},
                {"op": "replace_line", "line": 45, "text": "exp edit"},
            ]
        }

        breakdown = analyze_edits(edits, sections_json=sections_json)

        assert breakdown.sections_touched == ["EDUCATION", "EXPERIENCE", "SKILLS"]
