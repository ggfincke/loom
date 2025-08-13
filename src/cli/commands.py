# src/cli/commands.py
# Main CLI interface for Loom with all command definitions and user interaction

from pathlib import Path
import typer


from ..loom_io import read_docx, number_lines, read_text, write_docx, apply_edits_to_docx
from ..loom_io.console import console
from ..loom_io.ui import UI
from ..ai.prompts import build_sectionizer_prompt
from ..ai.clients.openai_client import run_generate
from ..config.settings import settings_manager
from ..loom_io import write_json_safe, read_json_safe, ensure_parent
from ..core.pipeline import Pipeline
from ..core.exceptions import handle_loom_error, ConfigurationError
from ..core.constants import normalize_risk, normalize_validation_policy
from .args import (
    ResumeArg, JobArg, EditsArg, ModelOpt, RiskOpt, OnErrorOpt, 
    OutOpt, SectionsPathOpt, PlanOpt, OutputDocxArg, PreserveFormattingOpt,
    PreserveModeOpt, OutJsonOpt, OutputResumeOpt
)
from .art import show_loom_art
from typing import TypedDict
from ..core.constants import RiskLevel, ValidationPolicy
from ..loom_io.types import Lines
from ..config.settings import LoomSettings

app = typer.Typer()

# main callback when no subcommand is provided and settings loader
@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context):
    # load settings & store in context for all commands to access
    ctx.obj = settings_manager.load()
    
    if ctx.invoked_subcommand is None:
        show_loom_art()
        console.print(ctx.get_help())
        ctx.exit()

# helper for merging provided values w/ settings defaults
def _resolve(provided_value, settings_default):
    return settings_default if provided_value is None else provided_value
class OptionsResolved(TypedDict):
    risk: RiskLevel
    on_error: ValidationPolicy

# class for resolving args w/ settings defaults
class ArgResolver:
    def __init__(self, settings):
        self.settings = settings
        
    def resolve_common(self, **kwargs):
        return {
            'resume': _resolve(kwargs.get('resume'), self.settings.resume_path),
            'job': _resolve(kwargs.get('job'), self.settings.job_path),
            'model': _resolve(kwargs.get('model'), self.settings.model),
            'sections_path': _resolve(kwargs.get('sections_path'), self.settings.sections_path),
            'out': _resolve(kwargs.get('out'), self.settings.edits_path),
            'out_json': _resolve(kwargs.get('out_json'), self.settings.sections_path),
        }
    
    # resolve path-specific arguments
    def resolve_paths(self, **kwargs):
        return {
            'output_resume': _resolve(kwargs.get('output_resume'), Path(self.settings.output_dir) / "tailored_resume.docx"),
            'edits': _resolve(kwargs.get('edits'), self.settings.edits_path),
        }
    
    # resolve option arguments
    def resolve_options(self, **kwargs) -> OptionsResolved:
        return {
            'risk': _resolve(kwargs.get('risk'), normalize_risk("med")),
            'on_error': _resolve(kwargs.get('on_error'), normalize_validation_policy("ask")),
        }


# load resume lines & job text with progress updates
def _load_resume_and_job(resume_path: Path, job_path: Path, progress, task):
    progress.update(task, description="Reading resume document...")
    lines = read_docx(resume_path)
    progress.advance(task)
    
    progress.update(task, description="Reading job description...")
    job_text = read_text(job_path)
    progress.advance(task)
    
    return lines, job_text

# load sections JSON if available
def _load_sections(sections_path: Path | None, progress, task):
    progress.update(task, description="Loading sections data...")
    sections_json_str = None
    if sections_path and Path(sections_path).exists():
        sections_json_str = Path(sections_path).read_text(encoding="utf-8")
    progress.advance(task)
    return sections_json_str


# * Core processing primitives

# generate edits using pipeline
def _generate_edits_core(settings: LoomSettings, resume_lines: Lines, job_text: str, sections_json: str | None, model: str, risk: RiskLevel, policy: ValidationPolicy, ui) -> dict:
    pipeline = Pipeline(settings)
    return pipeline.generate_edits(
        resume_lines=resume_lines,
        job_text=job_text, 
        sections_json=sections_json,
        model=model,
        risk=risk,
        on_error=policy,
        ui=ui
    )

# apply edits using pipeline
def _apply_edits_core(settings: LoomSettings, resume_lines: Lines, edits: dict, risk: RiskLevel, policy: ValidationPolicy, ui) -> Lines:
    pipeline = Pipeline(settings)
    return pipeline.apply_edits(resume_lines, edits, risk, policy, ui)


# * Helpers for validation warnings and JSON persistence

# persist edits JSON to disk
def _persist_edits_json(edits, out_path: Path, progress, task, description: str = "Writing edits JSON...") -> None:
    progress.update(task, description=description)
    write_json_safe(edits, out_path)
    progress.advance(task)


# * CLI command definitions

# Sectionize command - parse resume into sections
@app.command()
@handle_loom_error
def sectionize(
    ctx: typer.Context,
    resume_path: Path | None = ResumeArg(),
    out_json: Path | None = OutJsonOpt(),
    model: str | None = ModelOpt(),
):
    settings = ctx.obj
    resolver = ArgResolver(settings)
    
    # resolve arguments w/ settings defaults
    resolved = resolver.resolve_common(resume=resume_path, out_json=out_json, model=model)
    resume_path, out_json, model = resolved['resume'], resolved['out_json'], resolved['model']
    
    # validate required arguments
    if not resume_path:
        raise typer.BadParameter("Resume path is required (provide argument or set in config)")
    if not out_json:
        raise typer.BadParameter("Output path is required (provide --out-json or set sections_path in config)")
    if not model:
        raise typer.BadParameter("Model is required (provide --model or set in config)")
    
    # type assertions after validation
    assert resume_path is not None
    assert out_json is not None
    assert model is not None
    
    ui = UI()
    with ui.build_progress() as progress:
        
        task = progress.add_task("Processing resume...", total=4)
        
        progress.update(task, description="Reading resume document...")
        lines = read_docx(resume_path)
        progress.advance(task)
        
        progress.update(task, description="Numbering lines...")
        numbered = number_lines(lines)
        progress.advance(task)
        
        progress.update(task, description="Building prompt and calling OpenAI...")
        prompt = build_sectionizer_prompt(numbered)
        result = run_generate(prompt, model=model)
        
        # handle JSON parsing errors
        if not result.success:
            from ..core.exceptions import AIError
            raise AIError(f"AI failed to generate valid JSON: {result.error}\n\nRaw response:\n{result.raw_text}\n\nExtracted JSON:\n{result.json_text}")
        
        data = result.data
        assert data is not None, "Expected non-None data from successful AI result"
        progress.advance(task)
        
        progress.update(task, description="Writing sections JSON...")
        write_json_safe(data, out_json)
        progress.advance(task)
    
    console.print(f"✅ Wrote sections to {out_json}", style="green")

# Tailor command - tailor resume to job description and produce final tailored resume
# Uses OpenAI Responses API to generate line-by-line edits and applies them
@app.command()
@handle_loom_error
def tailor(
    ctx: typer.Context,
    job: Path | None = JobArg(),
    resume: Path | None = ResumeArg(),
    model: str | None = ModelOpt(),
    sections_path: Path | None = SectionsPathOpt(),
    out: Path | None = OutOpt(),
    output_resume: Path | None = OutputResumeOpt(),
    risk: RiskLevel | None = RiskOpt(),
    on_error: ValidationPolicy | None = OnErrorOpt(),
    preserve_formatting: bool = PreserveFormattingOpt(),
    preserve_mode: str = PreserveModeOpt(),
):
    settings = ctx.obj
    resolver = ArgResolver(settings)
    
    # resolve args w/ settings defaults
    common_resolved = resolver.resolve_common(job=job, resume=resume, model=model, sections_path=sections_path, out=out)
    path_resolved = resolver.resolve_paths(output_resume=output_resume)
    option_resolved = resolver.resolve_options(risk=risk, on_error=on_error)
    
    job, resume, model, sections_path, out = common_resolved['job'], common_resolved['resume'], common_resolved['model'], common_resolved['sections_path'], common_resolved['out']
    output_resume = path_resolved['output_resume']
    risk_enum: RiskLevel = option_resolved['risk']
    on_error_policy: ValidationPolicy = option_resolved['on_error']

    # validate required arguments
    if not job:
        raise typer.BadParameter("Job description path is required (provide argument or set in config)")
    if not resume:
        raise typer.BadParameter("Resume path is required (provide argument or set in config)")
    if not model:
        raise typer.BadParameter("Model is required (provide --model or set in config)")
    if not output_resume:
        raise typer.BadParameter("Output resume path is required (provide argument or set output_dir in config)")
    
    # type assertions after validation
    assert job is not None
    assert resume is not None
    assert out is not None
    assert model is not None
    assert output_resume is not None
    
    # pipeline instance
    pipeline = Pipeline(settings)
    
    ui = UI()
    with ui.build_progress() as progress:
        ui.progress = progress  # update UI with progress reference
        
        task = progress.add_task("Tailoring resume...", total=8)
        
        # read resume + job
        lines, job_text = _load_resume_and_job(resume, job, progress, task)
        
        # load optional sections
        sections_json_str = _load_sections(sections_path, progress, task)
        
        # generate edits using pipeline
        progress.update(task, description="Generating edits with AI...")
        edits = pipeline.generate_edits(
            resume_lines=lines,
            job_text=job_text,
            sections_json=sections_json_str,
            model=model,
            risk=risk_enum,
            on_error=on_error_policy,
            ui=ui,
        )
        progress.advance(task)
        
        # persist edits (for inspection / re-run)
        _persist_edits_json(edits, out, progress, task)
        
        # apply edits using pipeline
        progress.update(task, description="Applying edits...")
        new_lines = pipeline.apply_edits(lines, edits, risk_enum, on_error_policy, ui)
        progress.advance(task)
        
        # generate diff using pipeline
        progress.update(task, description="Generating diff...")
        diff = pipeline.diff_lines(lines, new_lines)
        ensure_parent(settings.diff_path)
        settings.diff_path.write_text(diff, encoding="utf-8")
        progress.advance(task)
        
        # write output
        progress.update(task, description="Writing tailored resume...")
        if preserve_formatting:
            apply_edits_to_docx(resume, new_lines, output_resume, preserve_mode=preserve_mode)
        else:
            write_docx(new_lines, output_resume)
        progress.advance(task)
    
    console.print("✅ Complete tailoring finished", style="green")
    console.print(f"   Edits -> {out}", style="dim")
    console.print(f"   Resume -> {output_resume}", style="dim")
    console.print(f"   Diff -> {settings.diff_path}", style="dim")

# Generate command - create edits.json from job description and resume
@app.command()
@handle_loom_error
def generate(
    ctx: typer.Context,
    model: str | None = ModelOpt(),
    out: Path | None = OutOpt(),
    sections_path: Path | None = SectionsPathOpt(),
    resume: Path | None = ResumeArg(),
    job: Path | None = JobArg(),
    risk: RiskLevel | None = RiskOpt(),
    on_error: ValidationPolicy | None = OnErrorOpt(),
):
    settings = ctx.obj
    resolver = ArgResolver(settings)
    
    # resolve arguments w/ settings defaults
    common_resolved = resolver.resolve_common(model=model, out=out, sections_path=sections_path, resume=resume, job=job)
    option_resolved = resolver.resolve_options(risk=risk, on_error=on_error)
    
    model, out, sections_path, resume, job = common_resolved['model'], common_resolved['out'], common_resolved['sections_path'], common_resolved['resume'], common_resolved['job']
    risk_enum: RiskLevel = option_resolved['risk']
    on_error_policy: ValidationPolicy = option_resolved['on_error']

    # validate required arguments
    if not resume:
        raise typer.BadParameter("Resume path is required (provide argument or set in config)")
    if not job:
        raise typer.BadParameter("Job description path is required (provide argument or set in config)")
    if not model:
        raise typer.BadParameter("Model is required (provide --model or set in config)")
    
    # type assertions after validation
    assert resume is not None
    assert job is not None
    assert out is not None
    assert model is not None
    
    # pipeline instance
    pipeline = Pipeline(settings)
    
    ui = UI()
    with ui.build_progress() as progress:
        ui.progress = progress  # update UI with progress reference
        
        task = progress.add_task("Generating edits...", total=4)
        
        # read resume + job
        lines, job_text = _load_resume_and_job(resume, job, progress, task)
        
        # load optional sections
        sections_json_str = _load_sections(sections_path, progress, task)
        
        # generate edits using pipeline
        progress.update(task, description="Generating edits with AI...")
        edits = pipeline.generate_edits(
            resume_lines=lines,
            job_text=job_text,
            sections_json=sections_json_str,
            model=model,
            risk=risk_enum,
            on_error=on_error_policy,
            ui=ui,
        )
        progress.advance(task)
        
        # write edits
        _persist_edits_json(edits, out, progress, task)
    
    console.print(f"✅ Wrote edits -> {out}", style="green")

# Apply command - apply edits.json to resume and generate output
@app.command()
@handle_loom_error
def apply(
    ctx: typer.Context,
    resume: Path | None = ResumeArg(),
    edits: Path | None = EditsArg(),
    out: Path | None = OutputDocxArg(),
    risk: RiskLevel | None = RiskOpt(),
    on_error: ValidationPolicy | None = OnErrorOpt(),
    preserve_formatting: bool = PreserveFormattingOpt(),
    preserve_mode: str = PreserveModeOpt(),
):
    settings = ctx.obj
    resolver = ArgResolver(settings)
    
    # resolve arguments w/ settings defaults
    common_resolved = resolver.resolve_common(resume=resume)
    path_resolved = resolver.resolve_paths(edits=edits, output_resume=out)
    option_resolved = resolver.resolve_options(risk=risk, on_error=on_error)
    
    resume = common_resolved['resume']
    edits, out = path_resolved['edits'], path_resolved['output_resume']
    risk, on_error = option_resolved['risk'], option_resolved['on_error']
    
    # validate required arguments
    if not resume:
        raise typer.BadParameter("Resume path is required (provide argument or set in config)")
    if not edits:
        raise typer.BadParameter("Edits path is required (provide argument or set in config)")
    if not out:
        raise typer.BadParameter("Output path is required (provide argument)")
    
    # pipeline instance
    pipeline = Pipeline(settings)
    
    ui = UI()
    with ui.build_progress() as progress:
        ui.progress = progress  # update UI with progress reference
        
        task = progress.add_task("Applying edits...", total=6)
        
        # read resume
        progress.update(task, description="Reading resume document...")
        lines = read_docx(resume)
        progress.advance(task)
        
        # read edits
        progress.update(task, description="Loading edits JSON...")
        edits_obj = read_json_safe(edits)
        progress.advance(task)
        
        # apply edits using pipeline
        progress.update(task, description="Applying edits...")
        new_lines = pipeline.apply_edits(lines, edits_obj, risk, on_error, ui)
        progress.advance(task)
        
        # generate diff using pipeline
        progress.update(task, description="Generating diff...")
        diff = pipeline.diff_lines(lines, new_lines)
        ensure_parent(settings.diff_path)
        settings.diff_path.write_text(diff, encoding="utf-8")
        progress.advance(task)
        
        # write output
        progress.update(task, description="Writing tailored resume...")
        if preserve_formatting:
            apply_edits_to_docx(resume, new_lines, out, preserve_mode=preserve_mode)
        else:
            write_docx(new_lines, out)
        progress.advance(task)
    
    if preserve_formatting:
        format_msg = f" (formatting preserved via {preserve_mode} mode)"
    else:
        format_msg = " (plain text)"
    console.print(f"✅ Wrote DOCX{format_msg} -> {out}", style="green")
    console.print(f"✅ Diff -> {settings.diff_path}", style="dim")

# Plan command - create edits.json with planning pipeline
@app.command()
@handle_loom_error
def plan(
    ctx: typer.Context,
    resume: Path | None = ResumeArg(),
    job: Path | None = JobArg(),
    out: Path | None = OutOpt(),
    plan: int | None = PlanOpt(),
    risk: str | None = RiskOpt(),
    on_error: str | None = OnErrorOpt(),
    model: str | None = ModelOpt(),
    sections_path: Path | None = SectionsPathOpt(),
):
    settings = ctx.obj
    resolver = ArgResolver(settings)
    
    # Resolve arguments with settings defaults
    common_resolved = resolver.resolve_common(resume=resume, job=job, out=out, model=model, sections_path=sections_path)
    option_resolved = resolver.resolve_options(risk=risk, on_error=on_error)

    resume, job, out = common_resolved['resume'], common_resolved['job'], common_resolved['out']
    model, sections_path = common_resolved['model'], common_resolved['sections_path']
    risk_enum: RiskLevel = option_resolved['risk']
    on_error_policy: ValidationPolicy = option_resolved['on_error']
    # unused byt planned
    _ = plan
    
    # validate required arguments
    if not resume:
        raise typer.BadParameter("Resume path is required (provide argument or set in config)")
    if not job:
        raise typer.BadParameter("Job description path is required (provide argument or set in config)")
    if not model:
        raise typer.BadParameter("Model is required (provide --model or set in config)")
    
    # type assertions after validation
    assert resume is not None
    assert job is not None
    assert out is not None
    assert model is not None
    
    # Create pipeline instance
    pipeline = Pipeline(settings)
    
    ui = UI()
    with ui.build_progress() as progress:
        ui.progress = progress  # update UI with progress reference

        task = progress.add_task("Planning edits...", total=5)

        lines, job_text = _load_resume_and_job(resume, job, progress, task)

        # load optional sections
        sections_json_str = _load_sections(sections_path, progress, task)

        # generate edits using pipeline
        progress.update(task, description="Generating edits with AI...")
        edits = pipeline.generate_edits(
            resume_lines=lines,
            job_text=job_text,
            sections_json=sections_json_str,
            model=model,
            risk=risk_enum,
            on_error=on_error_policy,
            ui=ui,
        )

        progress.advance(task)

        _persist_edits_json(edits, out, progress, task)

        # create simple plan file
        progress.update(task, description="Writing plan...")
        ensure_parent(settings.plan_path)
        settings.plan_path.write_text("# Plan\n\n- single-shot (stub)\n", encoding="utf-8")
        progress.advance(task)
    
    console.print(f"✅ Wrote edits -> {out}", style="green")
    console.print(f"✅ Plan -> {settings.plan_path}", style="dim")


# Config management commands
config_app = typer.Typer(
    help="""Manage Loom configuration settings.

Configuration allows you to set default values for commonly used options,
reducing the need to specify them repeatedly. Settings are stored in
~/.loom/config.json and persist across sessions.

Available settings:
  - model: OpenAI model to use (default: gpt-5-mini)  
  - data_dir: Default directory for input files (default: current directory)
  - output_dir: Default directory for output files (default: current directory)
  - resume_filename: Default resume filename (default: resume.docx)
  - job_filename: Default job description filename (default: job.txt)

Examples:
  loom config                    # Show current settings
  loom config set model gpt-4o   # Set OpenAI model
  loom config get data_dir       # Get specific setting
  loom config reset              # Reset all to defaults""",
    invoke_without_command=True
)
app.add_typer(config_app, name="config")

# manage Loom configuration settings
@config_app.callback()
def config_callback(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        # show current settings when no subcommand is provided
        config_list()

# List command - display all current configuration settings
@config_app.command("list", help="Display all current configuration settings with their values")
def config_list():
    settings = settings_manager.list_settings()
    typer.echo("Current Loom settings:")
    for key, value in settings.items():
        typer.echo(f"  {key}: {value}")

# Get command - retrieve a specific setting value
@config_app.command("get", help="Retrieve the current value of a specific configuration setting")
@handle_loom_error
def config_get(key: str = typer.Argument(..., help="Configuration setting name to retrieve. Valid options: model, data_dir, output_dir, resume_filename, job_filename")):
    value = settings_manager.get(key)
    if value is None:
        raise ConfigurationError(f"Setting '{key}' not found")
    typer.echo(f"{key}: {value}")

# Set command - update a specific setting value
@config_app.command("set", help="Set or update a configuration setting with a new value")
@handle_loom_error
def config_set(
    key: str = typer.Argument(..., help="Configuration setting name. Valid options: model, data_dir, output_dir, resume_filename, job_filename"),
    value: str = typer.Argument(..., help="New value to assign to the setting. For directories, use absolute or relative paths")
):
    try:
        settings_manager.set(key, value)
        typer.echo(f"Set {key} = {value}")
    except ValueError as e:
        raise ConfigurationError(str(e))

# Reset command - restore all settings to defaults
@config_app.command("reset", help="Reset all configuration settings to their factory default values (requires confirmation)")
def config_reset():
    if typer.confirm("Reset all settings to defaults?"):
        settings_manager.reset()
        typer.echo("Settings reset to defaults")
    else:
        typer.echo("Reset cancelled")

# Path command - display configuration file location
@config_app.command("path", help="Display the filesystem path to the configuration file (~/.loom/config.json)")
def config_path():
    typer.echo(f"Config file: {settings_manager.config_path}")