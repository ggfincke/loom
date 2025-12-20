# src/cli/runner.py
# Unified tailoring runner for CLI commands (generate, apply, tailor, plan)

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from ..config.settings import LoomSettings
from ..core.constants import RiskLevel, ValidationPolicy
from ..core.exceptions import EditError
from ..loom_io import read_resume, TemplateDescriptor
from ..loom_io.generics import ensure_parent
from ..loom_io.types import Lines
from ..ui.core.progress import (
    setup_ui_with_progress,
    load_resume_and_job,
    load_sections,
    load_edits_json,
)
from ..ui.display.reporting import (
    persist_edits_json,
    report_result,
    write_output_with_diff,
)
from .logic import (
    ArgResolver,
    generate_edits_core,
    apply_edits_core,
    build_latex_context,
)
from .helpers import validate_required_args


# mode of operation for the tailoring runner
class TailoringMode(Enum):
    GENERATE = "generate"  # generate edits only
    APPLY = "apply"  # apply existing edits
    TAILOR = "tailor"  # generate + apply
    PLAN = "plan"  # generate with planning


# context data prepared from resume, job & sections loading
@dataclass
class ResumeContext:
    lines: Lines
    job_text: str | None = None
    descriptor: TemplateDescriptor | None = None
    auto_sections_json: str | None = None
    template_notes: list[str] = field(default_factory=list)
    sections_json_str: str | None = None


# holds all resolved arguments for a tailoring operation
@dataclass
class TailoringContext:
    settings: LoomSettings
    resume: Path | None = None
    job: Path | None = None
    model: str | None = None
    edits_json: Path | None = None
    output_resume: Path | None = None
    sections_path: Path | None = None
    risk: RiskLevel = RiskLevel.MED
    on_error: ValidationPolicy = ValidationPolicy.ASK
    preserve_formatting: bool = True
    preserve_mode: str = "in_place"
    interactive: bool = True

    @property
    def is_latex(self) -> bool:
        return self.resume is not None and self.resume.suffix.lower() == ".tex"


# validation requirements per mode
VALIDATION_REQUIREMENTS: dict[TailoringMode, dict[str, str]] = {
    TailoringMode.GENERATE: {
        "resume": "Resume path",
        "job": "Job description path",
        "model": "Model (provide --model or set in config)",
    },
    TailoringMode.APPLY: {
        "resume": "Resume path",
        "edits_json": "Edits path",
        "output_resume": "Output path",
    },
    TailoringMode.TAILOR: {
        "resume": "Resume path",
        "job": "Job description path",
        "model": "Model (provide --model or set in config)",
        "output_resume": "Output resume path (provide argument or set output_dir in config)",
    },
    TailoringMode.PLAN: {
        "resume": "Resume path",
        "job": "Job description path",
        "model": "Model (provide --model or set in config)",
    },
}


# consolidated resume context preparation: resume/job loading, LaTeX detection & sections
def prepare_resume_context(
    ctx: TailoringContext,
    ui,
    progress,
    task,
    load_job: bool = True,
) -> ResumeContext:
    # load resume + optional job
    if load_job and ctx.job is not None:
        lines, job_text = load_resume_and_job(ctx.resume, ctx.job, progress, task)
    else:
        progress.update(task, description="Reading resume document...")
        lines = read_resume(ctx.resume)
        progress.advance(task)
        job_text = None

    # build LaTeX context if applicable
    descriptor = None
    auto_sections_json = None
    template_notes: list[str] = []

    if ctx.is_latex:
        progress.update(task, description="Analyzing LaTeX structure...")
        descriptor, auto_sections_json, template_notes = build_latex_context(
            ctx.resume, lines
        )
        progress.advance(task)

        # display LaTeX info
        if descriptor:
            ui.print(f"[green]Detected LaTeX template:[/] {descriptor.id}")
        if template_notes:
            ui.print("[yellow]Template notes:[/]")
            for note in template_notes:
                ui.print(f" - {note}")

    # resolve sections (explicit path takes precedence over auto-LaTeX)
    if ctx.sections_path:
        sections_json_str = load_sections(ctx.sections_path, progress, task)
    elif ctx.is_latex:
        sections_json_str = auto_sections_json
    else:
        sections_json_str = None

    return ResumeContext(
        lines=lines,
        job_text=job_text,
        descriptor=descriptor,
        auto_sections_json=auto_sections_json,
        template_notes=template_notes,
        sections_json_str=sections_json_str,
    )


def build_tailoring_context(
    settings: LoomSettings,
    resolver: ArgResolver,
    *,
    resume: Path | None = None,
    job: Path | None = None,
    model: str | None = None,
    sections_path: Path | None = None,
    edits_json: Path | None = None,
    output_resume: Path | None = None,
    risk: RiskLevel | None = None,
    on_error: ValidationPolicy | None = None,
    preserve_formatting: bool = True,
    preserve_mode: str = "in_place",
    interactive: bool = True,
) -> TailoringContext:
    # build TailoringContext w/ resolved arguments via ArgResolver
    common = resolver.resolve_common(
        resume=resume,
        job=job,
        model=model,
        sections_path=sections_path,
        edits_json=edits_json,
    )
    paths = resolver.resolve_paths(
        resume_path=common["resume"], output_resume=output_resume
    )
    options = resolver.resolve_options(risk=risk, on_error=on_error)

    return TailoringContext(
        settings=settings,
        resume=common["resume"],
        job=common["job"],
        model=common["model"],
        sections_path=common["sections_path"],
        edits_json=common["edits_json"],
        output_resume=paths["output_resume"],
        risk=options["risk"],
        on_error=options["on_error"],
        preserve_formatting=preserve_formatting,
        preserve_mode=preserve_mode,
        interactive=interactive,
    )


# unified runner for tailoring operations (generate, apply, tailor, plan)
class TailoringRunner:
    def __init__(self, mode: TailoringMode, ctx: TailoringContext):
        self.mode = mode
        self.ctx = ctx
        # state for reporting
        self._edits: dict | None = None
        self._new_lines: Lines | None = None
        self._resume_ctx: ResumeContext | None = None

    # validate required arguments based on mode
    def validate(self) -> None:
        requirements = VALIDATION_REQUIREMENTS[self.mode]
        args_to_validate = {}

        for key, description in requirements.items():
            value = getattr(self.ctx, key)
            args_to_validate[key] = (value, description)

        validate_required_args(**args_to_validate)

    # calculate total progress steps based on mode & context
    def calculate_total_steps(self) -> int:
        base_steps = {
            TailoringMode.GENERATE: 4,  # resume, job, sections?, generate, persist
            TailoringMode.APPLY: 5,  # resume, latex?, job?, sections?, edits, apply, diff, write
            TailoringMode.TAILOR: 7,  # resume, job, latex?, sections?, generate, persist, apply, diff, write
            TailoringMode.PLAN: 5,  # resume, job, sections?, generate, persist, plan_file
        }

        total = base_steps[self.mode]

        # add optional LaTeX step (all modes use LaTeX analysis)
        if self.ctx.is_latex:
            total += 1

        # add optional job step (apply only - job is optional for PROMPT support)
        if self.mode == TailoringMode.APPLY and self.ctx.job is not None:
            total += 1

        # add sections step if provided
        if self.ctx.sections_path is not None:
            total += 1

        return total

    # main entry point - orchestrates the full workflow
    def run(self) -> None:
        # validate before running
        self.validate()

        # calculate steps
        total_steps = self.calculate_total_steps()

        # task descriptions per mode
        task_descriptions = {
            TailoringMode.GENERATE: "Generating edits...",
            TailoringMode.APPLY: "Applying edits...",
            TailoringMode.TAILOR: "Tailoring resume...",
            TailoringMode.PLAN: "Planning edits...",
        }

        with setup_ui_with_progress(task_descriptions[self.mode], total=total_steps) as (
            ui,
            progress,
            task,
        ):
            self._execute(ui, progress, task)

        # report results
        self._report()

    # execute the appropriate workflow based on mode
    def _execute(self, ui, progress, task) -> None:
        if self.mode == TailoringMode.GENERATE:
            self._run_generate(ui, progress, task)
        elif self.mode == TailoringMode.APPLY:
            self._run_apply(ui, progress, task)
        elif self.mode == TailoringMode.TAILOR:
            self._run_full_tailor(ui, progress, task)
        elif self.mode == TailoringMode.PLAN:
            self._run_plan(ui, progress, task)

    # generate mode: create edits.json only
    def _run_generate(self, ui, progress, task) -> None:
        resume_ctx = prepare_resume_context(
            self.ctx, ui, progress, task, load_job=True
        )
        self._resume_ctx = resume_ctx

        # generate edits using core helper
        progress.update(task, description="Generating edits with AI...")
        self._edits = generate_edits_core(
            self.ctx.settings,
            resume_ctx.lines,
            resume_ctx.job_text,
            resume_ctx.sections_json_str,
            self.ctx.model,
            self.ctx.risk,
            self.ctx.on_error,
            ui,
            persist_path=self.ctx.edits_json,
        )
        progress.advance(task)

        # persist edits
        if self._edits is None:
            raise EditError("Failed to generate valid edits")
        persist_edits_json(self._edits, self.ctx.edits_json, progress, task)

    # apply mode: apply existing edits to resume
    def _run_apply(self, ui, progress, task) -> None:
        from pathlib import Path

        # read resume (apply reads resume separately from job)
        progress.update(task, description="Reading resume document...")
        lines = read_resume(self.ctx.resume)
        progress.advance(task)

        # build LaTeX context if applicable
        descriptor = None
        auto_sections_json = None
        template_notes: list[str] = []

        if self.ctx.is_latex:
            progress.update(task, description="Analyzing LaTeX structure...")
            descriptor, auto_sections_json, template_notes = build_latex_context(
                self.ctx.resume, lines
            )
            progress.advance(task)

            # display LaTeX info
            if descriptor:
                ui.print(f"[green]Detected LaTeX template:[/] {descriptor.id}")
            if template_notes:
                ui.print("[yellow]Template notes:[/]")
                for note in template_notes:
                    ui.print(f" - {note}")

        # read job description if available (for PROMPT support)
        job_text = None
        if self.ctx.job is not None:
            progress.update(task, description="Reading job description...")
            if Path(self.ctx.job).exists():
                job_text = Path(self.ctx.job).read_text(encoding="utf-8")
            progress.advance(task)

        # resolve sections (explicit path or auto-LaTeX)
        if self.ctx.sections_path:
            sections_json_str = load_sections(self.ctx.sections_path, progress, task)
        elif self.ctx.is_latex:
            sections_json_str = auto_sections_json
        else:
            sections_json_str = None

        # load edits
        edits_obj = load_edits_json(self.ctx.edits_json, progress, task)

        # apply edits using core helper
        progress.update(task, description="Applying edits...")
        self._new_lines = apply_edits_core(
            self.ctx.settings,
            lines,
            edits_obj,
            self.ctx.risk,
            self.ctx.on_error,
            ui,
            self.ctx.interactive,
            job_text=job_text,
            sections_json=sections_json_str,
            model=self.ctx.model,
            persist_special_ops=self.ctx.interactive,
            edits_json_path=self.ctx.edits_json,
            resume_path=self.ctx.resume,
            descriptor=descriptor,
        )
        progress.advance(task)

        # store for reporting
        self._resume_ctx = ResumeContext(
            lines=lines,
            job_text=job_text,
            descriptor=descriptor,
            auto_sections_json=auto_sections_json,
            template_notes=template_notes,
            sections_json_str=sections_json_str,
        )

        # write output w/ diff generation
        write_output_with_diff(
            self.ctx.settings,
            self.ctx.resume,
            lines,
            self._new_lines,
            self.ctx.output_resume,
            self.ctx.preserve_formatting,
            self.ctx.preserve_mode,
            progress,
            task,
        )

    # tailor mode: generate edits then apply
    def _run_full_tailor(self, ui, progress, task) -> None:
        resume_ctx = prepare_resume_context(
            self.ctx, ui, progress, task, load_job=True
        )
        self._resume_ctx = resume_ctx

        # generate edits using core helper
        progress.update(task, description="Generating edits with AI...")
        self._edits = generate_edits_core(
            self.ctx.settings,
            resume_ctx.lines,
            resume_ctx.job_text,
            resume_ctx.sections_json_str,
            self.ctx.model,
            self.ctx.risk,
            self.ctx.on_error,
            ui,
            persist_path=self.ctx.edits_json,
        )
        progress.advance(task)

        if self._edits is None:
            raise EditError("Failed to generate valid edits")

        # persist edits (for inspection / re-run)
        persist_edits_json(self._edits, self.ctx.edits_json, progress, task)

        # apply edits using core helper
        progress.update(task, description="Applying edits...")
        self._new_lines = apply_edits_core(
            self.ctx.settings,
            resume_ctx.lines,
            self._edits,
            self.ctx.risk,
            self.ctx.on_error,
            ui,
            self.ctx.interactive,
            job_text=resume_ctx.job_text,
            sections_json=resume_ctx.sections_json_str,
            model=self.ctx.model,
            persist_special_ops=self.ctx.interactive,
            edits_json_path=self.ctx.edits_json,
            resume_path=self.ctx.resume,
            descriptor=resume_ctx.descriptor,
        )
        progress.advance(task)

        # write output w/ diff generation
        write_output_with_diff(
            self.ctx.settings,
            self.ctx.resume,
            resume_ctx.lines,
            self._new_lines,
            self.ctx.output_resume,
            self.ctx.preserve_formatting,
            self.ctx.preserve_mode,
            progress,
            task,
        )

    # plan mode: generate edits w/ planning (experimental)
    def _run_plan(self, ui, progress, task) -> None:
        # generate phase (same as generate)
        self._run_generate(ui, progress, task)

        # create plan file
        progress.update(task, description="Writing plan...")
        ensure_parent(self.ctx.settings.plan_path)
        self.ctx.settings.plan_path.write_text(
            "# Plan\n\n- single-shot (stub)\n", encoding="utf-8"
        )
        progress.advance(task)

    # generate final report based on mode
    def _report(self) -> None:
        if self.mode == TailoringMode.GENERATE:
            report_result("edits", edits_path=self.ctx.edits_json)
        elif self.mode == TailoringMode.APPLY:
            report_result(
                "apply",
                settings=self.ctx.settings,
                output_path=self.ctx.output_resume,
                preserve_formatting=self.ctx.preserve_formatting,
                preserve_mode=self.ctx.preserve_mode,
            )
        elif self.mode == TailoringMode.TAILOR:
            report_result(
                "tailor",
                settings=self.ctx.settings,
                edits_path=self.ctx.edits_json,
                output_path=self.ctx.output_resume,
            )
        elif self.mode == TailoringMode.PLAN:
            report_result("plan", settings=self.ctx.settings, edits_path=self.ctx.edits_json)
