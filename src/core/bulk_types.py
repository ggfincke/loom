# src/core/bulk_types.py
# Pure dataclasses for bulk job processing - no I/O dependencies

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any
from enum import Enum


# status of bulk job processing run
class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


# specification for single job to process
@dataclass
class JobSpec:
    path: Path
    id: str
    name: Optional[str] = None
    company: Optional[str] = None

    # create JobSpec from file path using stem as id
    @classmethod
    def from_path(cls, path: Path) -> "JobSpec":
        return cls(path=path, id=path.stem, name=path.stem)


# breakdown of edit operations by type & section
@dataclass
class EditBreakdown:
    total_count: int = 0
    lines_touched: int = 0
    sections_touched: list[str] = field(default_factory=list)
    inserts: int = 0
    replacements: int = 0
    deletes: int = 0

    # serialize to JSON-compatible dict
    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total_count,
            "lines_touched": self.lines_touched,
            "sections": self.sections_touched,
            "by_type": {
                "inserts": self.inserts,
                "replacements": self.replacements,
                "deletes": self.deletes,
            },
        }


# job keyword matching analysis
@dataclass
class KeywordCoverage:
    required_matched: int = 0
    required_total: int = 0
    preferred_matched: int = 0
    preferred_total: int = 0
    missing_required: list[str] = field(default_factory=list)

    # ratio of required keywords matched
    @property
    def required_ratio(self) -> float:
        if self.required_total == 0:
            return 0.0
        return self.required_matched / self.required_total

    # ratio of preferred keywords matched
    @property
    def preferred_ratio(self) -> float:
        if self.preferred_total == 0:
            return 0.0
        return self.preferred_matched / self.preferred_total

    # serialize to JSON-compatible dict
    def to_dict(self) -> dict[str, Any]:
        return {
            "required": f"{self.required_matched}/{self.required_total}",
            "required_ratio": round(self.required_ratio, 2),
            "preferred": f"{self.preferred_matched}/{self.preferred_total}",
            "preferred_ratio": round(self.preferred_ratio, 2),
            "missing_required": self.missing_required[:5],
        }


# summary of validation warnings & issues
@dataclass
class ValidationSummary:
    warnings_by_severity: dict[str, int] = field(default_factory=dict)
    unsafe_claims: int = 0
    total_warnings: int = 0

    # serialize to JSON-compatible dict
    def to_dict(self) -> dict[str, Any]:
        return {
            "total_warnings": self.total_warnings,
            "by_severity": self.warnings_by_severity,
            "unsafe_claims": self.unsafe_claims,
        }


# result of processing single job
@dataclass
class JobResult:
    spec: JobSpec
    status: JobStatus = JobStatus.PENDING

    # timing
    runtime_seconds: float = 0.0

    # edits breakdown
    edits: EditBreakdown = field(default_factory=EditBreakdown)

    # keyword coverage
    coverage: KeywordCoverage = field(default_factory=KeywordCoverage)

    # validation summary
    validation: ValidationSummary = field(default_factory=ValidationSummary)

    # resume delta quality
    new_claims_count: int = 0
    keyword_stuffing_score: float = 0.0

    # computed fit score
    fit_score: float = 0.0

    # output paths
    output_dir: Optional[Path] = None
    edits_path: Optional[Path] = None
    resume_path: Optional[Path] = None

    # error info (if failed)
    error: Optional[str] = None

    # serialize to JSON-compatible dict
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.spec.id,
            "name": self.spec.name,
            "company": self.spec.company,
            "status": self.status.value,
            "runtime_seconds": round(self.runtime_seconds, 2),
            "edits": self.edits.to_dict(),
            "coverage": self.coverage.to_dict(),
            "validation": self.validation.to_dict(),
            "fit_score": round(self.fit_score, 2),
            "keyword_stuffing_score": round(self.keyword_stuffing_score, 2),
            "outputs": {
                "dir": str(self.output_dir) if self.output_dir else None,
                "edits": str(self.edits_path) if self.edits_path else None,
                "resume": str(self.resume_path) if self.resume_path else None,
            },
            "error": self.error,
        }


# aggregated result of bulk processing run
@dataclass
class BulkResult:
    resume_path: Path
    model: str
    timestamp: str
    output_dir: Path
    jobs: list[JobResult] = field(default_factory=list)

    # count of successfully processed jobs
    @property
    def success_count(self) -> int:
        return sum(1 for j in self.jobs if j.status == JobStatus.SUCCESS)

    # count of failed jobs
    @property
    def failed_count(self) -> int:
        return sum(1 for j in self.jobs if j.status == JobStatus.FAILED)

    # count of skipped jobs
    @property
    def skipped_count(self) -> int:
        return sum(1 for j in self.jobs if j.status == JobStatus.SKIPPED)

    # total runtime across all jobs
    @property
    def total_runtime(self) -> float:
        return sum(j.runtime_seconds for j in self.jobs)

    # return successful jobs sorted by fit_score descending
    def ranked_jobs(self) -> list[JobResult]:
        return sorted(
            [j for j in self.jobs if j.status == JobStatus.SUCCESS],
            key=lambda j: j.fit_score,
            reverse=True,
        )

    # serialize to JSON-compatible dict
    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "meta": {
                "resume": str(self.resume_path),
                "model": self.model,
                "timestamp": self.timestamp,
                "output_dir": str(self.output_dir),
            },
            "summary": {
                "total": len(self.jobs),
                "success": self.success_count,
                "failed": self.failed_count,
                "skipped": self.skipped_count,
                "total_runtime_seconds": round(self.total_runtime, 2),
            },
            "jobs": [j.to_dict() for j in self.jobs],
            "ranking": [j.spec.id for j in self.ranked_jobs()],
        }
