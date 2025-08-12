# src/cli/commands.py
# Main CLI interface for Loom with all command definitions and user interaction

from pathlib import Path
import typer

from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.console import Console

from ..loom_io import read_docx, number_lines, read_text, write_docx, apply_edits_to_docx
from ..ai.prompts import build_sectionizer_prompt, build_generate_prompt
from ..ai.clients.openai_client import run_generate
from ..config.settings import settings_manager
from ..loom_io import write_json_safe, read_json_safe, ensure_parent
from ..core import pipeline
from .args import (
    ResumeArg, JobArg, EditsArg, OutputArg, ConfigKeyArg, ConfigValueArg,
    ModelOpt, RiskOpt, OnErrorOpt, OutOpt, EditsJsonOpt, ResumeDocxOpt, 
    NoEditsJsonOpt, NoResumeDocxOpt, SectionsPathOpt, PlanOpt
)
from .art import show_loom_art

app = typer.Typer()
console = Console()

# main callback when no subcommand is provided
@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        show_loom_art()
        print(ctx.get_help())
        ctx.exit()

# Load settings once at module initialization
SETTINGS = settings_manager.load()

# Show validation warnings from file

def _show_validation_warnings(console: Console) -> bool:
    warnings_file = SETTINGS.warnings_path
    if not warnings_file.exists():
        return False
    text = warnings_file.read_text(encoding="utf-8").strip()
    if not text:
        return False
    console.print("⚠️  Validation warnings:", style="yellow")
    for line in text.splitlines():
        console.print(f"   {line}", style="yellow")
    console.print(f"   Full warnings → {warnings_file}", style="dim")
    return True

# standard progress context for CLI
def _with_progress():
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console
    )

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

# standard error handling for config operations
def _handle_config_error(operation: str, error: Exception) -> None:
    typer.echo(f"Error {operation}: {error}", err=True)
    raise typer.Exit(1)


# core logic for generating edits (shared by commands)
def _generate_edits_core(
    lines,
    job_text,
    sections_path,
    model,
    risk,
    on_error,
    progress,
    task,
):
    # load optional sections
    sections_json_str = _load_sections(sections_path, progress, task)
    
    # generate edits via AI
    progress.update(task, description="Generating edits with AI...")
    edits = pipeline.generate_edits(lines, job_text, sections_json_str, model, risk, on_error)
    progress.advance(task)
    
    # validate & show warnings
    progress.update(task, description="Validating edits...")
    _show_validation_warnings(console)
    progress.advance(task)
    
    return edits

# core logic for applying edits (shared by commands)
def _apply_edits_core(
    lines,
    edits,
    resume_path,
    output_path,
    risk,
    on_error,
    preserve_formatting,
    preserve_mode,
    progress,
    task,
):
    progress.update(task, description="Applying edits...")
    try:
        new_lines = pipeline.apply_edits(lines, edits, risk, on_error)
    except ValueError as e:
        console.print(f"❌ {e}", style="red")
        raise typer.Exit(1)
    progress.advance(task)
    
    progress.update(task, description="Validating results...")
    _show_validation_warnings(console)
    progress.advance(task)
    
    progress.update(task, description="Generating diff...")
    diff = pipeline.diff_lines(lines, new_lines)
    ensure_parent(SETTINGS.diff_path)
    SETTINGS.diff_path.write_text(diff, encoding="utf-8")
    progress.advance(task)
    
    progress.update(task, description="Writing tailored resume...")
    if preserve_formatting:
        apply_edits_to_docx(resume_path, new_lines, output_path, preserve_mode=preserve_mode)
    else:
        write_docx(new_lines, output_path)
    progress.advance(task)
    
    return new_lines

# CLI command definitions

# Sectionize command - parse resume into sections
@app.command()
def sectionize(
    resume_path: Path = typer.Argument(
        SETTINGS.resume_path,
        help="Path to source resume .docx",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    ),
    out_json: Path = typer.Option(
        SETTINGS.sections_path,
        "--out-json",
        "-o",
        help="Where to write the sections JSON",
        resolve_path=True,
        show_default=True,
    ),
    model: str = typer.Option(
        SETTINGS.model,
        "--model",
        "-m",
        help="OpenAI model name",
        show_default=True,
    ),
):
    with _with_progress() as progress:
        
        task = progress.add_task("Processing resume...", total=4)
        
        progress.update(task, description="Reading resume document...")
        lines = read_docx(resume_path)
        progress.advance(task)
        
        progress.update(task, description="Numbering lines...")
        numbered = number_lines(lines)
        progress.advance(task)
        
        progress.update(task, description="Building prompt and calling OpenAI...")
        prompt = build_sectionizer_prompt(numbered)
        data = run_generate(prompt, model=model)
        progress.advance(task)
        
        progress.update(task, description="Writing sections JSON...")
        write_json_safe(data, out_json)
        progress.advance(task)
    
    console.print(f"✅ Wrote sections to {out_json}", style="green")

# Tailor command - tailor resume to job description and produce final tailored resume
# Uses OpenAI Responses API to generate line-by-line edits and applies them
@app.command()
def tailor(
    job: JobArg = SETTINGS.job_path,
    resume: ResumeArg = SETTINGS.resume_path,
    sections_path: SectionsPathOpt = SETTINGS.sections_path,
    out: OutOpt = SETTINGS.edits_path,
    output_resume: Path = typer.Option(
        Path(SETTINGS.output_dir) / "tailored_resume.docx",
        "--output-resume", "-r",
        help="Path to write the tailored resume .docx",
        resolve_path=True,
        show_default=True,
    ),
    model: ModelOpt = SETTINGS.model,
    risk: RiskOpt = "med",
    on_error: OnErrorOpt = "ask",
    preserve_formatting: bool = typer.Option(
        True,
        "--preserve-formatting/--no-preserve-formatting",
        help="Preserve original DOCX formatting (fonts, styles, etc.)",
        show_default=True,
    ),
    preserve_mode: str = typer.Option(
        "in_place",
        "--preserve-mode",
        help="How to preserve formatting: 'in_place' (edit original, best preservation) or 'rebuild' (create new doc, may lose some formatting)",
        show_default=True,
    ),
):
    with _with_progress() as progress:
        
        task = progress.add_task("Tailoring resume...", total=10)
        
        # generate phase
        lines, job_text = _load_resume_and_job(resume, job, progress, task)
        edits = _generate_edits_core(lines, job_text, sections_path, model, risk, on_error, progress, task)
        
        # persist edits (for inspection / re-run)
        progress.update(task, description="Writing edits JSON...")
        write_json_safe(edits, out)
        progress.advance(task)
        
        # apply phase
        _apply_edits_core(
            lines,
            edits,
            resume,
            output_resume,
            risk,
            on_error,
            preserve_formatting,
            preserve_mode,
            progress,
            task,
        )
    
    console.print("✅ Complete tailoring finished", style="green")
    console.print(f"   Edits -> {out}", style="dim")
    console.print(f"   Resume -> {output_resume}", style="dim")
    console.print(f"   Diff -> {SETTINGS.diff_path}", style="dim")

# Generate command - create edits.json from job description and resume
@app.command()
def generate(
    resume: Path = typer.Argument(
        SETTINGS.resume_path,
        help="Path to resume .docx",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    ),
    job: Path = typer.Argument(
        SETTINGS.job_path,
        help="Path to job description",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    ),
    out: OutOpt = SETTINGS.edits_path,
    sections_path: SectionsPathOpt = SETTINGS.sections_path,
    model: ModelOpt = SETTINGS.model,
    risk: RiskOpt = "med",
    on_error: OnErrorOpt = "ask",
):
    with _with_progress() as progress:
        
        task = progress.add_task("Generating edits...", total=6)
        
        # read resume + job
        lines, job_text = _load_resume_and_job(resume, job, progress, task)
        
        # generate & validate edits
        edits = _generate_edits_core(lines, job_text, sections_path, model, risk, on_error, progress, task)
        
        # write edits
        progress.update(task, description="Writing edits JSON...")
        write_json_safe(edits, out)
        progress.advance(task)
    
    console.print(f"✅ Wrote edits -> {out}", style="green")

# Apply command - apply edits.json to resume and generate output
@app.command()
def apply(
    resume: ResumeArg = SETTINGS.resume_path,
    edits: EditsArg = SETTINGS.edits_path,
    out: OutputArg = Path(SETTINGS.output_dir) / "tailored_resume.docx",
    risk: RiskOpt = "med",
    on_error: OnErrorOpt = "ask",
    preserve_formatting: bool = typer.Option(
        True,
        "--preserve-formatting/--no-preserve-formatting",
        help="Preserve original DOCX formatting (fonts, styles, etc.)",
        show_default=True,
    ),
    preserve_mode: str = typer.Option(
        "in_place",
        "--preserve-mode",
        help="How to preserve formatting: 'in_place' (edit original, best preservation) or 'rebuild' (create new doc, may lose some formatting)",
        show_default=True,
    ),
):
    with _with_progress() as progress:
        
        task = progress.add_task("Applying edits...", total=6)
        
        # read resume
        progress.update(task, description="Reading resume document...")
        lines = read_docx(resume)
        progress.advance(task)
        
        # read edits
        progress.update(task, description="Loading edits JSON...")
        edits_obj = read_json_safe(edits)
        progress.advance(task)
        
        # apply + validate + diff + write output
        _apply_edits_core(
            lines,
            edits_obj,
            resume,
            out,
            risk,
            on_error,
            preserve_formatting,
            preserve_mode,
            progress,
            task,
        )
    
    if preserve_formatting:
        format_msg = f" (formatting preserved via {preserve_mode} mode)"
    else:
        format_msg = " (plain text)"
    console.print(f"✅ Wrote DOCX{format_msg} -> {out}", style="green")
    console.print(f"✅ Diff -> {SETTINGS.diff_path}", style="dim")

# Plan command - create edits.json with planning pipeline
@app.command()
def plan(
    resume: ResumeArg = SETTINGS.resume_path,
    job: JobArg = SETTINGS.job_path,
    out: OutOpt = SETTINGS.edits_path,
    plan: PlanOpt = None,
    risk: RiskOpt = "med",
    on_error: OnErrorOpt = "ask",
):
    settings = settings_manager.load()
    
    with _with_progress() as progress:
        
        task = progress.add_task("Planning edits...", total=6)
        
        lines, job_text = _load_resume_and_job(resume, job, progress, task)
        sections_json_str = _load_sections(Path(settings.sections_path), progress, task)
        
        progress.update(task, description="Generating edits with AI...")
        edits = pipeline.generate_edits(lines, job_text, sections_json_str, settings.model, risk, on_error)
        progress.advance(task)
        
        progress.update(task, description="Validating edits...")
        _show_validation_warnings(console)
        progress.advance(task)
        
        progress.update(task, description="Writing edits and plan...")
        write_json_safe(edits, out)
        
        # create simple plan file
        ensure_parent(SETTINGS.plan_path)
        SETTINGS.plan_path.write_text("# Plan\n\n- single-shot (stub)\n", encoding="utf-8")
        progress.advance(task)
    
    console.print(f"✅ Wrote edits -> {out}", style="green")
    console.print(f"✅ Plan -> {SETTINGS.plan_path}", style="dim")


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

# Manage Loom configuration settings
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
def config_get(key: str = typer.Argument(..., help="Configuration setting name to retrieve. Valid options: model, data_dir, output_dir, resume_filename, job_filename")):
    try:
        value = settings_manager.get(key)
        if value is None:
            typer.echo(f"Setting '{key}' not found", err=True)
            raise typer.Exit(1)
        typer.echo(f"{key}: {value}")
    except Exception as e:
        _handle_config_error("getting setting", e)

# Set command - update a specific setting value
@config_app.command("set", help="Set or update a configuration setting with a new value")
def config_set(
    key: str = typer.Argument(..., help="Configuration setting name. Valid options: model, data_dir, output_dir, resume_filename, job_filename"),
    value: str = typer.Argument(..., help="New value to assign to the setting. For directories, use absolute or relative paths")
):
    try:
        settings_manager.set(key, value)
        typer.echo(f"Set {key} = {value}")
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        _handle_config_error("setting value", e)

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