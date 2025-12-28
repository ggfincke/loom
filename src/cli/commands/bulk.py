# src/cli/commands/bulk.py
# Bulk job processing command for processing resume against multiple job postings

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from ...config.settings import get_settings
from ...core.bulk_types import JobStatus
from ...core.constants import RiskLevel, ValidationPolicy
from ...loom_io.console import console

from ..app import app
from ..decorators import handle_loom_error
from ..bulk_runner import BulkRunner, BulkConfig
from ..params import (
    ResumeArg,
    ModelOpt,
    SectionsPathOpt,
    RiskOpt,
    OnErrorOpt,
    PreserveFormattingOpt,
    PreserveModeOpt,
)
from ...ui.help.help_data import command_help


@command_help(
    name="bulk",
    description="Process resume against multiple job postings & generate comparison matrix",
    long_description=(
        "Run tailoring pipeline against multiple job descriptions. Supports "
        "directory of job files (*.txt, *.md), YAML/JSON manifest with metadata, "
        "or glob patterns. Generates per-job tailored resumes and a comparison "
        "matrix ranking jobs by fit score."
    ),
    examples=[
        "loom bulk jobs/ resume.docx",
        "loom bulk jobs/*.txt resume.docx --parallel 4",
        "loom bulk manifest.json resume.docx --output-dir results/",
        "loom bulk 'postings/*.txt' resume.tex --model gpt-4o",
    ],
    see_also=["tailor", "generate"],
)
@app.command(
    help="Process resume against multiple job postings & generate comparison matrix"
)
@handle_loom_error
def bulk(
    ctx: typer.Context,
    jobs: str = typer.Argument(
        ...,
        help="Jobs source: directory, manifest file (.yaml/.json), or glob pattern",
    ),
    resume: Optional[Path] = ResumeArg(),
    model: Optional[str] = ModelOpt(),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Base output directory for bulk results (default: output/)",
    ),
    parallel: int = typer.Option(
        1,
        "--parallel",
        "-p",
        help="Number of parallel workers (default: 1 = sequential)",
        min=1,
        max=16,
    ),
    fail_fast: bool = typer.Option(
        False,
        "--fail-fast",
        help="Stop on first failure (default: collect errors & continue)",
    ),
    sections_path: Optional[Path] = SectionsPathOpt(),
    risk: Optional[RiskLevel] = RiskOpt(),
    on_error: Optional[ValidationPolicy] = OnErrorOpt(),
    preserve_formatting: bool = PreserveFormattingOpt(),
    preserve_mode: str = PreserveModeOpt(),
) -> None:
    # Resolve settings
    settings = get_settings(ctx)

    # Resolve defaults
    if resume is None:
        resume = settings.resume_path
    if model is None:
        model = settings.model
    if output_dir is None:
        output_dir = Path(settings.output_dir)
    if risk is None:
        risk = RiskLevel.MED
    if on_error is None:
        # Bulk defaults to fail_soft (non-interactive)
        on_error = ValidationPolicy.FAIL_SOFT

    # Validate required args
    if resume is None or not resume.exists():
        console.print("[red]Error: Resume file not found[/]")
        raise typer.Exit(1)
    if model is None:
        console.print("[red]Error: Model required (--model or set in config)[/]")
        raise typer.Exit(1)

    # Build config
    config = BulkConfig(
        resume=resume,
        jobs_path=Path(jobs) if not any(c in jobs for c in "*?[") else jobs,
        model=model,
        output_dir=output_dir,
        sections_path=sections_path,
        risk=risk,
        on_error=on_error,
        parallel=parallel,
        fail_fast=fail_fast,
        preserve_formatting=preserve_formatting,
        preserve_mode=preserve_mode,
    )

    # Create runner w/ progress callbacks
    runner = BulkRunner(config, settings)

    # Progress callbacks
    def on_start(spec, current, total):
        name = spec.name or spec.id
        console.print(f"[dim]({current}/{total})[/] Processing [cyan]{name}[/]...")

    def on_complete(result, current, total):
        if result.status == JobStatus.SUCCESS:
            console.print(
                f"  [green]✓[/] Fit score: {result.fit_score:.2f}, {result.edits.total_count} edits"
            )
        elif result.status == JobStatus.FAILED:
            console.print(f"  [red]✗[/] {result.error}")
        elif result.status == JobStatus.SKIPPED:
            console.print(f"  [yellow]⊘[/] Skipped")

    def on_retry(msg):
        console.print(f"[yellow]{msg}[/]")

    runner.on_job_start = on_start
    runner.on_job_complete = on_complete
    runner.on_retry = on_retry

    # Header
    console.print()
    console.print("[bold]Bulk Processing[/]")
    console.print(f"  Jobs: {jobs}")
    console.print(f"  Resume: {resume}")
    console.print(f"  Model: {model}")
    console.print(f"  Workers: {parallel}")
    console.print()

    # Run
    result = runner.run()

    # Summary
    console.print()
    console.print("[bold]Results[/]")
    console.print(f"  Total: {len(result.jobs)}")
    console.print(f"  Success: [green]{result.success_count}[/]")
    if result.failed_count > 0:
        console.print(f"  Failed: [red]{result.failed_count}[/]")
    if result.skipped_count > 0:
        console.print(f"  Skipped: [yellow]{result.skipped_count}[/]")
    console.print(f"  Runtime: {result.total_runtime:.1f}s")
    console.print()
    console.print(f"  Output: {result.output_dir}")
    console.print(f"  Matrix: {result.output_dir / 'matrix.md'}")

    # Show top 3
    ranked = result.ranked_jobs()[:3]
    if ranked:
        console.print()
        console.print("[bold]Top Matches[/]")
        for i, job in enumerate(ranked, 1):
            name = job.spec.name or job.spec.id
            cov = f"{job.coverage.required_matched}/{job.coverage.required_total}"
            console.print(
                f"  {i}. [cyan]{name}[/] (score: {job.fit_score:.2f}, coverage: {cov})"
            )
