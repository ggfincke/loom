# src/cli/commands.py
# Main CLI interface for Loom with all command definitions and user interaction

from pathlib import Path
import typer
import json

from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.console import Console

from ..loom_io import read_docx, number_lines, read_text, write_docx
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

# load once 
SETTINGS = settings_manager.load()

# shows validation warnings
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

# ** CLI commands

# * Sectionize - parse resume into sections
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
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        
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

# * Tailor - tailor resume to job description
# uses OpenAI Responses API to tailor a resume to a job description; generates a JSON object with edits by line number
@app.command()
def tailor(
    job: JobArg,
    resume: ResumeArg,
    sections_path: SectionsPathOpt = SETTINGS.sections_path,
    out: OutOpt = SETTINGS.edits_path,
    model: ModelOpt = SETTINGS.model,
    on_error: OnErrorOpt = "ask",
):
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("Tailoring resume...", total=7)
        
        progress.update(task, description="Reading job description...")
        job_text = read_text(job)
        progress.advance(task)
        
        progress.update(task, description="Reading resume document...")
        lines = read_docx(resume)
        progress.advance(task)
        
        progress.update(task, description="Numbering lines...")
        numbered = number_lines(lines)
        progress.advance(task)
        
        progress.update(task, description="Loading sections data...")
        sections_json_str = None
        if sections_path and sections_path.exists():
            sections_json_str = sections_path.read_text(encoding="utf-8")
        progress.advance(task)
        
        progress.update(task, description="Generating edits with AI...")
        edits = pipeline.generate_edits(lines, job_text, sections_json_str, model, "med", on_error)
        progress.advance(task)
        
        progress.update(task, description="Validating edits...")
        _show_validation_warnings(console)
        progress.advance(task)
        
        progress.update(task, description="Writing edits JSON...")
        write_json_safe(edits, out)
        progress.advance(task)
    
    console.print(f"✅ Wrote tailored edits to {out}", style="green")

# * Generate - create edits.json from job description and resume
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
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("Generating edits...", total=6)
        
        progress.update(task, description="Reading resume document...")
        lines = read_docx(resume)
        progress.advance(task)
        
        progress.update(task, description="Reading job description...")
        job_text = read_text(job)
        progress.advance(task)
        
        progress.update(task, description="Loading sections data...")
        sections_json_str = None
        if sections_path and sections_path.exists():
            sections_json_str = sections_path.read_text(encoding="utf-8")
        progress.advance(task)
        
        progress.update(task, description="Generating edits with AI...")
        edits = pipeline.generate_edits(lines, job_text, sections_json_str, model, risk, on_error)
        progress.advance(task)
        
        progress.update(task, description="Validating edits...")
        _show_validation_warnings(console)
        progress.advance(task)
        
        progress.update(task, description="Writing edits JSON...")
        write_json_safe(edits, out)
        progress.advance(task)
    
    console.print(f"✅ Wrote edits -> {out}", style="green")

# * Apply - apply edits.json to resume and generate output
@app.command()
def apply(
    resume: Path = typer.Argument(
        SETTINGS.resume_path,
        help="Path to resume .docx",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    ),
    edits: Path = typer.Argument(
        SETTINGS.edits_path,
        help="Path to edits JSON file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    ),
    out: OutputArg = Path(SETTINGS.output_dir) / "tailored_resume.docx",
    risk: RiskOpt = "med",
    on_error: OnErrorOpt = "ask",
):
    lines = read_docx(resume)
    edits_obj = read_json_safe(edits)
    
    try:
        new_lines = pipeline.apply_edits(lines, edits_obj, risk, on_error)
    except ValueError as e:
        console.print(f"❌ {e}", style="red")
        raise typer.Exit(1)
    
    _show_validation_warnings(console)
    
    diff = pipeline.diff_lines(lines, new_lines)
    ensure_parent(SETTINGS.diff_path)
    SETTINGS.diff_path.write_text(diff, encoding="utf-8")
    
    write_docx(new_lines, out)
    
    console.print(f"✅ Wrote DOCX -> {out}", style="green")
    console.print(f"✅ Diff -> {SETTINGS.diff_path}", style="dim")

# * Plan - create edits.json with planning pipeline
@app.command()
def plan(
    resume: ResumeArg,
    job: JobArg,
    out: OutOpt = SETTINGS.edits_path,
    plan: PlanOpt = None,
    risk: RiskOpt = "med",
    on_error: OnErrorOpt = "ask",
):
    settings = settings_manager.load()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("Planning edits...", total=6)
        
        progress.update(task, description="Reading resume document...")
        lines = read_docx(resume)
        progress.advance(task)
        
        progress.update(task, description="Reading job description...")
        job_text = read_text(job)
        progress.advance(task)
        
        progress.update(task, description="Loading sections data...")
        sections_json_str = None
        sections_path = Path(settings.sections_path)
        if sections_path and sections_path.exists():
            sections_json_str = sections_path.read_text(encoding="utf-8")
        progress.advance(task)
        
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


# * Config management commands
config_app = typer.Typer(
    help="""Manage Loom configuration settings.

Configuration allows you to set default values for commonly used options,
reducing the need to specify them repeatedly. Settings are stored in
~/.loom/config.json and persist across sessions.

Available settings:
  - model: OpenAI model to use (default: gpt-4o-mini)  
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

# manage Loom config settings
@config_app.callback()
def config_callback(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        # show current settings when no subcommand is provided
        config_list()

# * List - list all current settings
@config_app.command("list", help="Display all current configuration settings with their values")
def config_list():
    settings = settings_manager.list_settings()
    typer.echo("Current Loom settings:")
    for key, value in settings.items():
        typer.echo(f"  {key}: {value}")

# * Get - get a specific setting value
@config_app.command("get", help="Retrieve the current value of a specific configuration setting")
def config_get(key: str = typer.Argument(..., help="Configuration setting name to retrieve. Valid options: model, data_dir, output_dir, resume_filename, job_filename")):
    try:
        value = settings_manager.get(key)
        if value is None:
            typer.echo(f"Setting '{key}' not found", err=True)
            raise typer.Exit(1)
        typer.echo(f"{key}: {value}")
    except Exception as e:
        typer.echo(f"Error getting setting: {e}", err=True)
        raise typer.Exit(1)

# * Set - set a specific setting value
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
        typer.echo(f"Error setting value: {e}", err=True)
        raise typer.Exit(1)

# * Reset - reset all settings to defaults
@config_app.command("reset", help="Reset all configuration settings to their factory default values (requires confirmation)")
def config_reset():
    if typer.confirm("Reset all settings to defaults?"):
        settings_manager.reset()
        typer.echo("Settings reset to defaults")
    else:
        typer.echo("Reset cancelled")

# * Path - show config file path
@config_app.command("path", help="Display the filesystem path to the configuration file (~/.loom/config.json)")
def config_path():
    typer.echo(f"Config file: {settings_manager.config_path}")