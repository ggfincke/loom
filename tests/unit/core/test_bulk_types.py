# tests/unit/core/test_bulk_types.py
# Unit tests for bulk processing data types

from pathlib import Path

import pytest

from src.core.bulk_types import (
    JobSpec,
    JobStatus,
    EditBreakdown,
    KeywordCoverage,
    ValidationSummary,
    JobResult,
    BulkResult,
)


class TestJobSpec:
    # * from_path creates spec w/ stem as id & name
    def test_from_path(self, tmp_path):
        job_file = tmp_path / "senior_swe.txt"
        job_file.write_text("test")

        spec = JobSpec.from_path(job_file)

        assert spec.path == job_file
        assert spec.id == "senior_swe"
        assert spec.name == "senior_swe"
        assert spec.company is None

    # * Manual construction w/ all fields
    def test_manual_construction(self):
        spec = JobSpec(
            path=Path("jobs/role.txt"),
            id="custom_id",
            name="Custom Role",
            company="TechCorp",
        )

        assert spec.id == "custom_id"
        assert spec.name == "Custom Role"
        assert spec.company == "TechCorp"


class TestEditBreakdown:
    # * to_dict serializes correctly
    def test_to_dict(self):
        breakdown = EditBreakdown(
            total_count=5,
            lines_touched=10,
            sections_touched=["EXPERIENCE", "SKILLS"],
            inserts=1,
            replacements=3,
            deletes=1,
        )

        result = breakdown.to_dict()

        assert result["total"] == 5
        assert result["lines_touched"] == 10
        assert result["sections"] == ["EXPERIENCE", "SKILLS"]
        assert result["by_type"]["inserts"] == 1
        assert result["by_type"]["replacements"] == 3
        assert result["by_type"]["deletes"] == 1

    # * Default values are all zero/empty
    def test_defaults(self):
        breakdown = EditBreakdown()

        assert breakdown.total_count == 0
        assert breakdown.lines_touched == 0
        assert breakdown.sections_touched == []


class TestKeywordCoverage:
    # * required_ratio calculates correctly
    def test_required_ratio(self):
        coverage = KeywordCoverage(required_matched=3, required_total=5)
        assert coverage.required_ratio == 0.6

    # * required_ratio returns 0 when total is 0
    def test_required_ratio_zero_total(self):
        coverage = KeywordCoverage(required_matched=0, required_total=0)
        assert coverage.required_ratio == 0.0

    # * preferred_ratio calculates correctly
    def test_preferred_ratio(self):
        coverage = KeywordCoverage(preferred_matched=2, preferred_total=4)
        assert coverage.preferred_ratio == 0.5

    # * to_dict serializes w/ formatted ratios
    def test_to_dict(self):
        coverage = KeywordCoverage(
            required_matched=3,
            required_total=5,
            preferred_matched=2,
            preferred_total=4,
            missing_required=["Docker", "Kubernetes", "Terraform"],
        )

        result = coverage.to_dict()

        assert result["required"] == "3/5"
        assert result["required_ratio"] == 0.6
        assert result["preferred"] == "2/4"
        assert result["missing_required"] == ["Docker", "Kubernetes", "Terraform"]


class TestJobResult:
    # * to_dict serializes all fields
    def test_to_dict(self, tmp_path):
        spec = JobSpec(path=tmp_path / "job.txt", id="test_job", name="Test Job")
        result = JobResult(
            spec=spec,
            status=JobStatus.SUCCESS,
            runtime_seconds=5.5,
            fit_score=0.75,
            edits=EditBreakdown(total_count=3),
            coverage=KeywordCoverage(required_matched=4, required_total=5),
        )

        data = result.to_dict()

        assert data["id"] == "test_job"
        assert data["name"] == "Test Job"
        assert data["status"] == "success"
        assert data["runtime_seconds"] == 5.5
        assert data["fit_score"] == 0.75

    # * Failed result includes error
    def test_failed_result(self, tmp_path):
        spec = JobSpec.from_path(tmp_path / "job.txt")
        result = JobResult(
            spec=spec,
            status=JobStatus.FAILED,
            error="API rate limit exceeded",
        )

        data = result.to_dict()

        assert data["status"] == "failed"
        assert data["error"] == "API rate limit exceeded"


class TestBulkResult:
    # * success_count counts successful jobs
    def test_success_count(self, tmp_path):
        jobs = [
            JobResult(
                spec=JobSpec.from_path(tmp_path / "a.txt"),
                status=JobStatus.SUCCESS,
            ),
            JobResult(
                spec=JobSpec.from_path(tmp_path / "b.txt"),
                status=JobStatus.FAILED,
            ),
            JobResult(
                spec=JobSpec.from_path(tmp_path / "c.txt"),
                status=JobStatus.SUCCESS,
            ),
        ]

        result = BulkResult(
            resume_path=tmp_path / "resume.docx",
            model="gpt-4o",
            timestamp="2025-01-01T00:00:00",
            output_dir=tmp_path / "output",
            jobs=jobs,
        )

        assert result.success_count == 2
        assert result.failed_count == 1

    # * ranked_jobs returns successful jobs sorted by fit_score
    def test_ranked_jobs(self, tmp_path):
        jobs = [
            JobResult(
                spec=JobSpec(path=tmp_path / "a.txt", id="a"),
                status=JobStatus.SUCCESS,
                fit_score=0.5,
            ),
            JobResult(
                spec=JobSpec(path=tmp_path / "b.txt", id="b"),
                status=JobStatus.FAILED,
                fit_score=0.9,  # should be excluded
            ),
            JobResult(
                spec=JobSpec(path=tmp_path / "c.txt", id="c"),
                status=JobStatus.SUCCESS,
                fit_score=0.8,
            ),
        ]

        result = BulkResult(
            resume_path=tmp_path / "resume.docx",
            model="gpt-4o",
            timestamp="2025-01-01T00:00:00",
            output_dir=tmp_path / "output",
            jobs=jobs,
        )

        ranked = result.ranked_jobs()

        assert len(ranked) == 2
        assert ranked[0].spec.id == "c"  # highest score
        assert ranked[1].spec.id == "a"

    # * to_dict serializes complete result
    def test_to_dict(self, tmp_path):
        result = BulkResult(
            resume_path=tmp_path / "resume.docx",
            model="gpt-4o",
            timestamp="2025-01-01T00:00:00",
            output_dir=tmp_path / "output",
            jobs=[],
        )

        data = result.to_dict()

        assert data["version"] == 1
        assert data["meta"]["model"] == "gpt-4o"
        assert data["summary"]["total"] == 0
