# src/loom_io/bulk_io.py
# I/O operations for bulk processing: discovery, layout, matrix writing

from __future__ import annotations

import glob as glob_module
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .generics import ensure_parent, write_json_safe
from ..core.bulk_types import JobSpec, BulkResult


# * Discover jobs from path (directory, manifest, or glob pattern)
# discover jobs from directory (glob *.txt & *.md), manifest file (.yaml/.json), or glob pattern (*, ?, [)
def discover_jobs(jobs_path: Path | str) -> list[JobSpec]:
    path_str = str(jobs_path)

    # check for glob characters
    if any(c in path_str for c in "*?["):
        return _discover_from_glob(path_str)

    path = Path(jobs_path)

    if path.is_dir():
        return _discover_from_directory(path)
    elif path.suffix.lower() in (".yaml", ".yml", ".json"):
        return _discover_from_manifest(path)
    elif path.is_file():
        # single file - treat as single job
        return [JobSpec.from_path(path)]
    else:
        raise FileNotFoundError(f"Jobs path not found: {jobs_path}")


# discover job files from directory (*.txt, *.md)
def _discover_from_directory(directory: Path) -> list[JobSpec]:
    jobs: list[JobSpec] = []
    for pattern in ("*.txt", "*.md"):
        for path in sorted(directory.glob(pattern)):
            jobs.append(JobSpec.from_path(path))
    return jobs


# expand glob pattern to job specs
def _discover_from_glob(pattern: str) -> list[JobSpec]:
    paths = sorted(Path(p) for p in glob_module.glob(pattern))
    return [JobSpec.from_path(p) for p in paths if p.is_file()]


# parse manifest file (YAML or JSON) for job specs
def _discover_from_manifest(manifest_path: Path) -> list[JobSpec]:
    content = manifest_path.read_text(encoding="utf-8")

    if manifest_path.suffix.lower() in (".yaml", ".yml"):
        try:
            import yaml

            data = yaml.safe_load(content)
        except ImportError:
            raise ImportError(
                "PyYAML required for YAML manifest files.\n"
                "Options:\n"
                "  1. Install: pip install pyyaml\n"
                "  2. Use JSON manifest instead (same schema, .json extension)"
            )
    else:
        data = json.loads(content)

    jobs: list[JobSpec] = []
    base_dir = manifest_path.parent

    for job_data in data.get("jobs", []):
        path = base_dir / job_data["path"]
        jobs.append(
            JobSpec(
                path=path,
                id=job_data.get("id", path.stem),
                name=job_data.get("name"),
                company=job_data.get("company"),
            )
        )

    return jobs


# sanitize string for use as directory name
def _sanitize_dirname(name: str) -> str:
    # replace unsafe chars w/ underscore
    safe = re.sub(r'[<>:"/\\|?*\s]+', "_", name)
    # remove leading/trailing underscores & dots
    return safe.strip("_.")


# ensure unique IDs by sanitizing & truncating to max_len, then suffixing duplicates AFTER truncation to handle prefix collisions
def deduplicate_job_specs(job_specs: list[JobSpec], max_len: int = 50) -> list[JobSpec]:
    result: list[JobSpec] = []
    seen: dict[str, int] = {}

    for spec in job_specs:
        # sanitize & truncate first
        base_id = _sanitize_dirname(spec.id)[:max_len]

        # now deduplicate
        if base_id in seen:
            seen[base_id] += 1
            # suffix may push over max_len, so re-truncate base
            suffix = f"_{seen[base_id]}"
            new_id = base_id[: max_len - len(suffix)] + suffix
        else:
            seen[base_id] = 1
            new_id = base_id

        result.append(
            JobSpec(
                path=spec.path,
                id=new_id,
                name=spec.name,
                company=spec.company,
            )
        )

    return result


# * Create output directory structure for bulk run
# create timestamped output directory w/ per-job subdirs; returns (bulk_output_dir, {job_id: job_output_dir})
def create_bulk_output_layout(
    base_dir: Path,
    job_specs: list[JobSpec],
) -> tuple[Path, dict[str, Path]]:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    bulk_dir = base_dir / f"bulk_{timestamp}"
    bulk_dir.mkdir(parents=True, exist_ok=True)

    job_dirs: dict[str, Path] = {}
    for spec in job_specs:
        job_dir = bulk_dir / spec.id
        job_dir.mkdir(parents=True, exist_ok=True)
        job_dirs[spec.id] = job_dir

    return bulk_dir, job_dirs


# * Write run.json at bulk root for reproducibility
# write run.json w/ metadata for reproducibility
def write_run_metadata(
    bulk_dir: Path,
    resume_path: Path,
    model: str,
    settings_snapshot: dict[str, Any],
    job_specs: list[JobSpec],
) -> None:
    # hash each job file
    job_hashes: dict[str, str] = {}
    for spec in job_specs:
        if spec.path.exists():
            content = spec.path.read_bytes()
            job_hashes[spec.id] = hashlib.sha256(content).hexdigest()[:16]

    # get loom version
    try:
        from importlib.metadata import version

        loom_version = version("loom")
    except Exception:
        loom_version = "unknown"

    run_meta = {
        "version": 1,
        "loom_version": loom_version,
        "timestamp": datetime.now().isoformat(),
        "resume": str(resume_path),
        "model": model,
        "settings": settings_snapshot,
        "jobs": {
            spec.id: {
                "path": str(spec.path),
                "name": spec.name,
                "company": spec.company,
                "content_hash": job_hashes.get(spec.id),
            }
            for spec in job_specs
        },
    }

    write_json_safe(run_meta, bulk_dir / "run.json")


# * Write per-job artifacts
# write per-job metadata & normalized job text
def write_job_artifacts(
    job_dir: Path,
    spec: JobSpec,
    job_text: str,
    model: str,
    settings_snapshot: dict[str, Any],
) -> None:
    # job.json - metadata
    write_json_safe(
        {
            "id": spec.id,
            "name": spec.name,
            "company": spec.company,
            "original_path": str(spec.path),
            "model": model,
            "timestamp": datetime.now().isoformat(),
            "settings": settings_snapshot,
        },
        job_dir / "job.json",
    )

    # job.txt - normalized text fed to model
    (job_dir / "job.txt").write_text(job_text, encoding="utf-8")


# * Write comparison matrix files
# write matrix.json & matrix.md to bulk output directory
def write_matrix_files(bulk_dir: Path, result: BulkResult) -> None:
    # JSON matrix
    write_json_safe(result.to_dict(), bulk_dir / "matrix.json")

    # Markdown matrix
    md_content = _generate_markdown_matrix(result)
    (bulk_dir / "matrix.md").write_text(md_content, encoding="utf-8")


# generate human-readable markdown comparison table
def _generate_markdown_matrix(result: BulkResult) -> str:
    lines = [
        "# Bulk Processing Results",
        "",
        f"**Resume:** {result.resume_path.name}",
        f"**Model:** {result.model}",
        f"**Timestamp:** {result.timestamp}",
        f"**Total Jobs:** {len(result.jobs)} ({result.success_count} success, {result.failed_count} failed, {result.skipped_count} skipped)",
        f"**Total Runtime:** {result.total_runtime:.1f}s",
        "",
    ]

    # ranked table
    ranked = result.ranked_jobs()
    if ranked:
        lines.extend(
            [
                "## Ranking",
                "",
                "| Rank | Job | Fit Score | Required Coverage | Edits | Runtime |",
                "|------|-----|-----------|-------------------|-------|---------|",
            ]
        )
        for i, job in enumerate(ranked, 1):
            cov = f"{job.coverage.required_matched}/{job.coverage.required_total}"
            name = job.spec.name or job.spec.id
            lines.append(
                f"| {i} | {name} | {job.fit_score:.2f} | {cov} | {job.edits.total_count} | {job.runtime_seconds:.1f}s |"
            )
        lines.append("")

    # detailed results
    lines.extend(["## Detailed Results", ""])
    for job in result.jobs:
        status_emoji = {
            "success": "✓",
            "failed": "✗",
            "skipped": "⊘",
            "pending": "○",
            "running": "◌",
        }.get(job.status.value, "?")

        name = job.spec.name or job.spec.id
        lines.append(f"### {status_emoji} {name}")
        lines.append("")

        if job.status.value == "success":
            lines.append(f"- **Fit Score:** {job.fit_score:.2f}")
            lines.append(
                f"- **Required Keywords:** {job.coverage.required_matched}/{job.coverage.required_total}"
            )
            lines.append(
                f"- **Preferred Keywords:** {job.coverage.preferred_matched}/{job.coverage.preferred_total}"
            )
            lines.append(f"- **Edits:** {job.edits.total_count} ({job.edits.replacements} replacements, {job.edits.inserts} inserts, {job.edits.deletes} deletes)")
            lines.append(f"- **Runtime:** {job.runtime_seconds:.1f}s")
            if job.coverage.missing_required:
                missing = ", ".join(job.coverage.missing_required[:5])
                lines.append(f"- **Missing Required:** {missing}")
            if job.validation.total_warnings > 0:
                lines.append(f"- **Warnings:** {job.validation.total_warnings}")
        elif job.status.value == "failed":
            lines.append(f"- **Error:** {job.error or 'Unknown error'}")
        elif job.status.value == "skipped":
            lines.append(f"- **Reason:** {job.error or 'Skipped'}")

        lines.append("")

    return "\n".join(lines)
