# src/cli/bulk_runner.py
# Orchestration layer for bulk job processing

from __future__ import annotations

import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, TypeVar

from ..config.settings import LoomSettings
from ..core.bulk_types import (
    JobSpec,
    JobResult,
    BulkResult,
    JobStatus,
)
from ..core.comparison_matrix import (
    analyze_edits,
    extract_job_keywords,
    calculate_keyword_coverage,
    calculate_fit_score,
    detect_keyword_stuffing,
    build_validation_summary,
)
from ..core.constants import RiskLevel, ValidationPolicy
from ..core.validation import validate_edits
from ..loom_io import read_text, read_resume
from ..loom_io.bulk_io import (
    discover_jobs,
    deduplicate_job_specs,
    create_bulk_output_layout,
    write_run_metadata,
    write_job_artifacts,
    write_matrix_files,
)
from ..loom_io.generics import read_json_safe
from ..loom_io.types import Lines
from .runner import TailoringMode, TailoringRunner, build_tailoring_context
from .logic import ArgResolver


T = TypeVar("T")


# configuration for bulk processing run
@dataclass
class BulkConfig:
    resume: Path
    jobs_path: Path
    model: str
    output_dir: Path
    sections_path: Optional[Path] = None
    risk: RiskLevel = RiskLevel.MED
    on_error: ValidationPolicy = ValidationPolicy.FAIL_SOFT
    parallel: int = 1
    fail_fast: bool = False
    preserve_formatting: bool = True
    preserve_mode: str = "in_place"


# run function w/ jittered backoff on retryable errors
def _run_with_retry(
    fn: Callable[[], T],
    job_id: str,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    logger: Optional[Callable[[str], None]] = None,
) -> T:
    last_error: Optional[Exception] = None

    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception as e:
            error_str = str(e).lower()
            is_retryable = any(
                code in error_str
                for code in ["429", "rate limit", "500", "502", "503", "504"]
            )

            if not is_retryable or attempt == max_attempts - 1:
                raise

            last_error = e
            delay = base_delay * (2**attempt) * (0.5 + random.random())
            if logger:
                logger(f"[{job_id}] Retry {attempt + 1}/{max_attempts} after {delay:.1f}s: {e}")
            time.sleep(delay)

    if last_error:
        raise last_error
    raise RuntimeError(f"Max retries exceeded for {job_id}")


# read tailored resume as text for keyword analysis
def _read_tailored_resume_text(output_path: Path, original_lines: Lines) -> str:
    suffix = output_path.suffix.lower()

    if suffix == ".docx":
        # DOCX is binary - use existing reader
        from ..loom_io import read_docx

        lines = read_docx(output_path)
        return "\n".join(str(v) for v in lines.values())
    else:
        # Text formats (.tex, .typ, .md, .txt) can be read directly
        return output_path.read_text(encoding="utf-8")


# orchestrates bulk job processing
class BulkRunner:
    def __init__(self, config: BulkConfig, settings: LoomSettings):
        self.config = config
        self.settings = settings
        self.resolver = ArgResolver(settings)
        # cached sections JSON string for analyze_edits
        self._sections_json: Optional[str] = None

        # callbacks for progress reporting
        self.on_job_start: Optional[Callable[[JobSpec, int, int], None]] = None
        self.on_job_complete: Optional[Callable[[JobResult, int, int], None]] = None
        self.on_retry: Optional[Callable[[str], None]] = None

    # * Load sections JSON if sections_path is configured
    def _load_sections_json(self) -> Optional[str]:
        if self._sections_json is not None:
            return self._sections_json

        if self.config.sections_path and self.config.sections_path.exists():
            try:
                self._sections_json = self.config.sections_path.read_text(encoding="utf-8")
            except OSError:
                self._sections_json = None

        return self._sections_json

    # execute bulk processing & return aggregated results
    def run(self) -> BulkResult:
        # discover jobs
        raw_specs = discover_jobs(self.config.jobs_path)
        if not raw_specs:
            raise ValueError(f"No jobs found at {self.config.jobs_path}")

        # deduplicate IDs (handles truncation collisions)
        job_specs = deduplicate_job_specs(raw_specs)

        # create output layout
        bulk_dir, job_dirs = create_bulk_output_layout(
            self.config.output_dir,
            job_specs,
        )

        # settings snapshot for reproducibility
        settings_snapshot = {
            "risk": self.config.risk.value,
            "on_error": self.config.on_error.value,
            "preserve_formatting": self.config.preserve_formatting,
            "preserve_mode": self.config.preserve_mode,
            "parallel": self.config.parallel,
        }

        # write run metadata
        write_run_metadata(
            bulk_dir,
            self.config.resume,
            self.config.model,
            settings_snapshot,
            job_specs,
        )

        # process jobs
        timestamp = datetime.now().isoformat()

        if self.config.parallel > 1:
            results = self._run_parallel(job_specs, job_dirs, settings_snapshot)
        else:
            results = self._run_sequential(job_specs, job_dirs, settings_snapshot)

        # build final result
        bulk_result = BulkResult(
            resume_path=self.config.resume,
            model=self.config.model,
            timestamp=timestamp,
            output_dir=bulk_dir,
            jobs=results,
        )

        # write matrix files
        write_matrix_files(bulk_dir, bulk_result)

        return bulk_result

    # process jobs sequentially
    def _run_sequential(
        self,
        job_specs: list[JobSpec],
        job_dirs: dict[str, Path],
        settings_snapshot: dict,
    ) -> list[JobResult]:
        results: list[JobResult] = []
        total = len(job_specs)

        for i, spec in enumerate(job_specs):
            if self.on_job_start:
                self.on_job_start(spec, i + 1, total)

            result = self._process_single_job(spec, job_dirs[spec.id], settings_snapshot)
            results.append(result)

            if self.on_job_complete:
                self.on_job_complete(result, i + 1, total)

            if self.config.fail_fast and result.status == JobStatus.FAILED:
                # mark remaining as skipped
                for remaining_spec in job_specs[i + 1 :]:
                    results.append(
                        JobResult(
                            spec=remaining_spec,
                            status=JobStatus.SKIPPED,
                            error="Skipped due to --fail-fast",
                        )
                    )
                break

        return results

    # process jobs in parallel w/ bounded concurrency & retry
    def _run_parallel(
        self,
        job_specs: list[JobSpec],
        job_dirs: dict[str, Path],
        settings_snapshot: dict,
    ) -> list[JobResult]:
        results: list[JobResult] = []
        total = len(job_specs)
        completed = 0

        def process_with_retry(spec: JobSpec) -> JobResult:
            return _run_with_retry(
                lambda: self._process_single_job(spec, job_dirs[spec.id], settings_snapshot),
                job_id=spec.id,
                logger=self.on_retry,
            )

        with ThreadPoolExecutor(max_workers=self.config.parallel) as executor:
            future_to_spec = {
                executor.submit(process_with_retry, spec): spec for spec in job_specs
            }

            for future in as_completed(future_to_spec):
                spec = future_to_spec[future]
                completed += 1

                try:
                    result = future.result()
                except Exception as e:
                    result = JobResult(
                        spec=spec,
                        status=JobStatus.FAILED,
                        error=str(e),
                    )

                results.append(result)

                if self.on_job_complete:
                    self.on_job_complete(result, completed, total)

        # sort results back to original order
        spec_order = {spec.id: i for i, spec in enumerate(job_specs)}
        results.sort(key=lambda r: spec_order.get(r.spec.id, 999))

        return results

    # process single job & return result
    def _process_single_job(
        self,
        spec: JobSpec,
        output_dir: Path,
        settings_snapshot: dict,
    ) -> JobResult:
        start_time = time.time()
        result = JobResult(spec=spec, status=JobStatus.RUNNING)

        try:
            # read job text
            job_text = read_text(spec.path)

            # write job artifacts (normalized text for reproducibility)
            write_job_artifacts(
                output_dir,
                spec,
                job_text,
                self.config.model,
                settings_snapshot,
            )

            # determine output paths
            resume_suffix = self.config.resume.suffix
            edits_path = output_dir / "edits.json"
            output_resume_path = output_dir / f"tailored_resume{resume_suffix}"

            # build tailoring context
            ctx = build_tailoring_context(
                self.settings,
                self.resolver,
                resume=self.config.resume,
                job=spec.path,
                model=self.config.model,
                sections_path=self.config.sections_path,
                edits_json=edits_path,
                output_resume=output_resume_path,
                risk=self.config.risk,
                on_error=self.config.on_error,
                preserve_formatting=self.config.preserve_formatting,
                preserve_mode=self.config.preserve_mode,
                interactive=False,  # bulk mode is always non-interactive
            )

            # run tailoring
            runner = TailoringRunner(TailoringMode.TAILOR, ctx)
            runner.run()

            # analyze results
            edits = read_json_safe(edits_path)
            sections_json = self._load_sections_json()
            result.edits = analyze_edits(edits, sections_json=sections_json)

            # read resume for validation & coverage analysis
            resume_lines = read_resume(self.config.resume)

            # capture validation warnings
            validation_warnings = validate_edits(edits, resume_lines, self.config.risk)
            result.validation = build_validation_summary(validation_warnings, edits)

            # keyword coverage analysis
            required_kw, preferred_kw = extract_job_keywords(job_text)
            tailored_text = _read_tailored_resume_text(output_resume_path, resume_lines)
            result.coverage = calculate_keyword_coverage(
                tailored_text, required_kw, preferred_kw
            )

            # keyword stuffing check
            result.keyword_stuffing_score = detect_keyword_stuffing(tailored_text)

            # calculate fit score
            result.fit_score = calculate_fit_score(result)

            # set output paths
            result.output_dir = output_dir
            result.edits_path = edits_path
            result.resume_path = output_resume_path
            result.status = JobStatus.SUCCESS

        except Exception as e:
            result.status = JobStatus.FAILED
            result.error = str(e)

        result.runtime_seconds = time.time() - start_time
        return result
