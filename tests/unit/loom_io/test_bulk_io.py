# tests/unit/loom_io/test_bulk_io.py
# Unit tests for bulk I/O operations

import json
from pathlib import Path

import pytest

from src.loom_io.bulk_io import (
    discover_jobs,
    deduplicate_job_specs,
    create_bulk_output_layout,
    write_run_metadata,
    write_job_artifacts,
    write_matrix_files,
)
from src.core.bulk_types import JobSpec, JobStatus, JobResult, BulkResult


class TestDiscoverJobs:
    # * Discovers .txt & .md files from directory
    def test_discover_from_directory(self, tmp_path):
        (tmp_path / "job1.txt").write_text("job 1")
        (tmp_path / "job2.txt").write_text("job 2")
        (tmp_path / "job3.md").write_text("job 3")
        (tmp_path / "notes.py").write_text("not a job")

        specs = discover_jobs(tmp_path)

        assert len(specs) == 3
        ids = [s.id for s in specs]
        assert "job1" in ids
        assert "job2" in ids
        assert "job3" in ids

    # * Parses JSON manifest file
    def test_discover_from_json_manifest(self, tmp_path):
        manifest = tmp_path / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "jobs": [
                        {"path": "job1.txt", "id": "swe", "name": "Software Engineer"},
                        {"path": "job2.txt", "id": "devops"},
                    ]
                }
            )
        )
        (tmp_path / "job1.txt").write_text("job 1")
        (tmp_path / "job2.txt").write_text("job 2")

        specs = discover_jobs(manifest)

        assert len(specs) == 2
        assert specs[0].id == "swe"
        assert specs[0].name == "Software Engineer"
        assert specs[1].id == "devops"

    # * Parses YAML manifest if PyYAML available
    def test_discover_from_yaml_manifest(self, tmp_path):
        yaml = pytest.importorskip("yaml")

        manifest = tmp_path / "manifest.yaml"
        manifest.write_text(
            """
jobs:
  - path: job1.txt
    id: backend
    name: Backend Engineer
    company: TechCo
"""
        )
        (tmp_path / "job1.txt").write_text("job 1")

        specs = discover_jobs(manifest)

        assert len(specs) == 1
        assert specs[0].id == "backend"
        assert specs[0].company == "TechCo"

    # * Single file returns single JobSpec
    def test_discover_single_file(self, tmp_path):
        job_file = tmp_path / "single_job.txt"
        job_file.write_text("single job")

        specs = discover_jobs(job_file)

        assert len(specs) == 1
        assert specs[0].id == "single_job"

    # * Glob patterns expanded correctly
    def test_discover_glob_pattern(self, tmp_path):
        (tmp_path / "swe_job.txt").write_text("swe")
        (tmp_path / "devops_job.txt").write_text("devops")
        (tmp_path / "other.md").write_text("other")

        pattern = str(tmp_path / "*_job.txt")
        specs = discover_jobs(pattern)

        assert len(specs) == 2
        ids = [s.id for s in specs]
        assert "swe_job" in ids
        assert "devops_job" in ids

    # * Non-existent path raises FileNotFoundError
    def test_discover_not_found_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            discover_jobs(tmp_path / "nonexistent")


class TestDeduplicateJobSpecs:
    # * Non-duplicate IDs pass through unchanged
    def test_no_duplicates_unchanged(self, tmp_path):
        specs = [
            JobSpec(path=tmp_path / "a.txt", id="alpha"),
            JobSpec(path=tmp_path / "b.txt", id="beta"),
        ]

        result = deduplicate_job_specs(specs)

        assert [s.id for s in result] == ["alpha", "beta"]

    # * Duplicate IDs get numeric suffix
    def test_duplicates_get_suffix(self, tmp_path):
        specs = [
            JobSpec(path=tmp_path / "a.txt", id="job"),
            JobSpec(path=tmp_path / "b.txt", id="job"),
            JobSpec(path=tmp_path / "c.txt", id="job"),
        ]

        result = deduplicate_job_specs(specs)

        ids = [s.id for s in result]
        assert ids[0] == "job"
        assert ids[1] == "job_2"
        assert ids[2] == "job_3"

    # * IDs that collide after truncation get unique suffixes
    def test_truncation_collisions_handled(self, tmp_path):
        # 48 char prefix + different 3-char suffixes
        prefix = "a" * 48
        specs = [
            JobSpec(path=tmp_path / "1.txt", id=f"{prefix}_xyz"),
            JobSpec(path=tmp_path / "2.txt", id=f"{prefix}_abc"),
        ]

        result = deduplicate_job_specs(specs, max_len=50)

        ids = [s.id for s in result]
        # both get truncated to same 50-char prefix, so second needs suffix
        assert len(set(ids)) == 2  # all unique
        assert all(len(id) <= 50 for id in ids)

    # * Name & company preserved through dedup
    def test_preserves_metadata(self, tmp_path):
        specs = [
            JobSpec(
                path=tmp_path / "a.txt",
                id="job",
                name="Job A",
                company="CompanyA",
            ),
            JobSpec(
                path=tmp_path / "b.txt",
                id="job",
                name="Job B",
                company="CompanyB",
            ),
        ]

        result = deduplicate_job_specs(specs)

        assert result[0].name == "Job A"
        assert result[1].name == "Job B"


class TestCreateBulkOutputLayout:
    # * Creates bulk_TIMESTAMP directory
    def test_creates_timestamped_dir(self, tmp_path):
        specs = [JobSpec(path=tmp_path / "job.txt", id="test")]

        bulk_dir, job_dirs = create_bulk_output_layout(tmp_path, specs)

        assert bulk_dir.exists()
        assert bulk_dir.name.startswith("bulk_")
        assert "test" in job_dirs
        assert job_dirs["test"].exists()

    # * Creates subdirectory for each job
    def test_creates_per_job_subdirs(self, tmp_path):
        specs = [
            JobSpec(path=tmp_path / "a.txt", id="alpha"),
            JobSpec(path=tmp_path / "b.txt", id="beta"),
        ]

        bulk_dir, job_dirs = create_bulk_output_layout(tmp_path, specs)

        assert (bulk_dir / "alpha").exists()
        assert (bulk_dir / "beta").exists()


class TestWriteRunMetadata:
    # * Writes run.json w/ metadata
    def test_writes_run_json(self, tmp_path):
        bulk_dir = tmp_path / "bulk_test"
        bulk_dir.mkdir()
        specs = [JobSpec(path=tmp_path / "job.txt", id="test")]
        (tmp_path / "job.txt").write_text("job content")

        write_run_metadata(
            bulk_dir,
            resume_path=tmp_path / "resume.docx",
            model="gpt-4o",
            settings_snapshot={"risk": "med"},
            job_specs=specs,
        )

        run_json = bulk_dir / "run.json"
        assert run_json.exists()

        data = json.loads(run_json.read_text())
        assert data["model"] == "gpt-4o"
        assert "test" in data["jobs"]
        assert data["jobs"]["test"]["content_hash"] is not None


class TestWriteJobArtifacts:
    # * Writes job.json & job.txt to job directory
    def test_writes_job_json_and_txt(self, tmp_path):
        job_dir = tmp_path / "test_job"
        job_dir.mkdir()
        spec = JobSpec(path=tmp_path / "job.txt", id="test", name="Test Job")

        write_job_artifacts(
            job_dir,
            spec,
            job_text="Normalized job description",
            model="gpt-4o",
            settings_snapshot={"risk": "med"},
        )

        assert (job_dir / "job.json").exists()
        assert (job_dir / "job.txt").exists()

        job_json = json.loads((job_dir / "job.json").read_text())
        assert job_json["id"] == "test"
        assert job_json["name"] == "Test Job"

        job_txt = (job_dir / "job.txt").read_text()
        assert job_txt == "Normalized job description"


class TestWriteMatrixFiles:
    # * Writes both matrix.json & matrix.md
    def test_writes_json_and_md(self, tmp_path):
        result = BulkResult(
            resume_path=tmp_path / "resume.docx",
            model="gpt-4o",
            timestamp="2025-01-01T00:00:00",
            output_dir=tmp_path,
            jobs=[
                JobResult(
                    spec=JobSpec(path=tmp_path / "job.txt", id="test", name="Test"),
                    status=JobStatus.SUCCESS,
                    fit_score=0.75,
                )
            ],
        )

        write_matrix_files(tmp_path, result)

        assert (tmp_path / "matrix.json").exists()
        assert (tmp_path / "matrix.md").exists()

    # * matrix.json contains ranked job IDs
    def test_json_contains_ranking(self, tmp_path):
        result = BulkResult(
            resume_path=tmp_path / "resume.docx",
            model="gpt-4o",
            timestamp="2025-01-01T00:00:00",
            output_dir=tmp_path,
            jobs=[
                JobResult(
                    spec=JobSpec(path=tmp_path / "a.txt", id="low"),
                    status=JobStatus.SUCCESS,
                    fit_score=0.3,
                ),
                JobResult(
                    spec=JobSpec(path=tmp_path / "b.txt", id="high"),
                    status=JobStatus.SUCCESS,
                    fit_score=0.9,
                ),
            ],
        )

        write_matrix_files(tmp_path, result)

        data = json.loads((tmp_path / "matrix.json").read_text())
        assert data["ranking"][0] == "high"  # highest score first
        assert data["ranking"][1] == "low"

    # * matrix.md contains markdown table
    def test_md_contains_table(self, tmp_path):
        result = BulkResult(
            resume_path=tmp_path / "resume.docx",
            model="gpt-4o",
            timestamp="2025-01-01T00:00:00",
            output_dir=tmp_path,
            jobs=[
                JobResult(
                    spec=JobSpec(path=tmp_path / "job.txt", id="test", name="Test"),
                    status=JobStatus.SUCCESS,
                    fit_score=0.75,
                )
            ],
        )

        write_matrix_files(tmp_path, result)

        md_content = (tmp_path / "matrix.md").read_text()
        assert "# Bulk Processing Results" in md_content
        assert "| Rank |" in md_content
