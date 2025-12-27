# src/cli/commands/ats.py
# ATS compatibility checker command for analyzing resume ATS-friendliness

from __future__ import annotations

from pathlib import Path
from typing import Optional, List

import typer

from ...ai.prompts import build_ats_prompt
from ...ai.clients import run_generate
from ...loom_io import read_resume, write_json_safe, number_lines
from ...core.ats_analyzer import (
    ATSReport,
    ATSIssue,
    Severity,
    IssueCategory,
    analyze_resume_ats,
    calculate_score,
    generate_recommendations,
)
from ...core.exceptions import handle_loom_error, ATSError

from ..app import app
from ..helpers import handle_help_flag, validate_required_args
from ...ui.core.progress import setup_ui_with_progress
from ...ui.display.ats_report import render_ats_report, render_ats_summary
from ..logic import ArgResolver
from ..params import ResumeArg, OutJsonOpt, ModelOpt
from ...ui.help.help_data import command_help
from ...config.settings import get_settings


# parse AI response into ATSIssue objects
def _parse_ai_issues(data: dict) -> List[ATSIssue]:
    issues: List[ATSIssue] = []

    # severity mapping
    severity_map = {
        "critical": Severity.CRITICAL,
        "warning": Severity.WARNING,
        "info": Severity.INFO,
    }

    # contact issues
    for item in data.get("contact_issues", []):
        sev = severity_map.get(item.get("severity", "warning"), Severity.WARNING)
        issues.append(
            ATSIssue(
                category=IssueCategory.CONTACT,
                severity=sev,
                description=item.get(
                    "description", f"Contact issue: {item.get('type', 'unknown')}"
                ),
                suggestion=item.get("suggestion"),
            )
        )

    # section issues
    for item in data.get("section_issues", []):
        sev = severity_map.get(item.get("severity", "info"), Severity.INFO)
        current = item.get("current_name", "Unknown")
        suggestion = item.get("suggestion", "Use standard section name")
        issues.append(
            ATSIssue(
                category=IssueCategory.SECTION_HEADERS,
                severity=sev,
                description=f"Non-standard section name: '{current}'",
                suggestion=suggestion,
            )
        )

    # bullet issues
    for item in data.get("bullet_issues", []):
        sev = severity_map.get(item.get("severity", "warning"), Severity.WARNING)
        char = item.get("char", "?")
        line = item.get("line")
        issues.append(
            ATSIssue(
                category=IssueCategory.BULLETS,
                severity=sev,
                description=f"Non-standard bullet character: '{char}'",
                location=f"Line {line}" if line else None,
                suggestion=item.get("suggestion", "Replace with standard bullet"),
            )
        )

    # unicode issues
    for item in data.get("unicode_issues", []):
        sev = severity_map.get(item.get("severity", "warning"), Severity.WARNING)
        line = item.get("line")
        issues.append(
            ATSIssue(
                category=IssueCategory.UNICODE,
                severity=sev,
                description=item.get(
                    "description", "Unusual unicode character detected"
                ),
                location=f"Line {line}" if line else None,
                suggestion=item.get("suggestion"),
            )
        )

    # date issues
    for item in data.get("date_issues", []):
        sev = severity_map.get(item.get("severity", "info"), Severity.INFO)
        line = item.get("line")
        fmt = item.get("format", "unknown")
        issues.append(
            ATSIssue(
                category=IssueCategory.DATES,
                severity=sev,
                description=f"Non-standard date format: '{fmt}'",
                location=f"Line {line}" if line else None,
                suggestion=item.get("suggestion", "Use consistent date format"),
            )
        )

    return issues


# * Analyze resume for ATS compatibility issues
@command_help(
    name="ats",
    description="Analyze resume for ATS (Applicant Tracking System) compatibility",
    long_description=(
        "scan resume (.docx) for common ATS parsing problems including:\n\n"
        "Structural issues (no AI required):\n"
        "  - Tables, multi-column layouts, text boxes\n"
        "  - Headers/footers with content, images/drawings\n\n"
        "Content issues (AI-assisted):\n"
        "  - Non-standard section headers, unusual bullets\n"
        "  - Contact info formatting, special unicode characters\n\n"
        "Use --no-ai for fast structural-only checks (no API cost).\n"
        "Use --fail-on for CI integration (exit non-zero on issues)."
    ),
    examples=[
        "loom ats resume.docx",
        "loom ats resume.docx --out-json ats_report.json",
        "loom ats resume.docx --no-ai  # structural checks only",
        "loom ats resume.docx --fail-on critical  # CI mode",
    ],
    see_also=["tailor", "sectionize"],
)
@app.command(help="Analyze resume for ATS compatibility")
@handle_loom_error
def ats(
    ctx: typer.Context,
    resume_path: Optional[Path] = ResumeArg(),
    out_json: Optional[Path] = OutJsonOpt(),
    model: Optional[str] = ModelOpt(),
    no_ai: bool = typer.Option(
        False,
        "--no-ai",
        help="Skip AI content analysis (structural checks only)",
    ),
    fail_on: Optional[str] = typer.Option(
        None,
        "--fail-on",
        help="Exit non-zero if issues at level: critical|warning",
    ),
    help: bool = typer.Option(False, "--help", "-h", help="Show help message & exit."),
) -> None:
    handle_help_flag(ctx, help, "ats")
    settings = get_settings(ctx)
    resolver = ArgResolver(settings)

    # resolve arguments w/ settings defaults
    resolved = resolver.resolve_common(
        resume=resume_path, out_json=out_json, model=model
    )
    resume_path = resolved["resume"]
    out_json = resolved["out_json"]
    model = resolved["model"]

    # validate required arguments
    required_args = {
        "resume_path": (resume_path, "Resume path"),
    }

    # model only required if AI analysis enabled
    if not no_ai:
        required_args["model"] = (
            model,
            "Model (provide --model or set in config, or use --no-ai)",
        )

    validate_required_args(**required_args)

    assert resume_path is not None

    # validate file type (DOCX only for V1)
    if resume_path.suffix.lower() != ".docx":
        raise ATSError(
            f"ATS analysis currently supports .docx files only. Got: {resume_path.suffix}\n"
            "LaTeX files don't have the same structural issues (tables, columns, etc.)."
        )

    # validate fail_on value
    if fail_on and fail_on.lower() not in ("critical", "warning"):
        raise ATSError("--fail-on must be 'critical' or 'warning'")

    # determine number of steps
    total_steps = 2 if no_ai else 4

    with setup_ui_with_progress(
        "Analyzing ATS compatibility...", total=total_steps
    ) as (
        ui,
        progress,
        task,
    ):
        # step 1: structural analysis
        progress.update(task, description="Scanning document structure...")
        report = analyze_resume_ats(resume_path)
        progress.advance(task)

        # step 2: AI content analysis (optional)
        if not no_ai:
            assert model is not None

            progress.update(task, description="Reading resume content...")
            lines = read_resume(resume_path)
            numbered = number_lines(lines)
            progress.advance(task)

            progress.update(task, description="Analyzing content with AI...")
            prompt = build_ats_prompt(numbered)
            result = run_generate(prompt, model=model)

            if result.success and result.data:
                ai_issues = _parse_ai_issues(result.data)
                # merge AI issues into report
                report.issues.extend(ai_issues)
                report.score = calculate_score(report.issues)
                report.recommendations = generate_recommendations(report.issues)
            else:
                # AI failed but structural analysis still valid
                from ...loom_io.console import console

                console.print(
                    f"[yellow]Warning: AI content analysis failed, showing structural issues only[/]"
                )
                if result.error:
                    console.print(f"[dim]{result.error}[/]")

            progress.advance(task)

        # step 3: output
        progress.update(task, description="Generating report...")
        if out_json:
            write_json_safe(report.to_dict(), out_json)
        progress.advance(task)

    # render report to console
    render_ats_report(report)

    # show JSON path if written
    if out_json:
        render_ats_summary(report, str(out_json))

    # handle --fail-on exit codes
    if fail_on:
        fail_level = fail_on.lower()
        if fail_level == "critical" and report.critical_count > 0:
            raise SystemExit(2)
        elif fail_level == "warning" and (
            report.critical_count > 0 or report.warning_count > 0
        ):
            raise SystemExit(2)
