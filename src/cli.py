from pathlib import Path
import typer
import json

from .document import read_docx, number_lines, read_text
from .prompts import build_sectionizer_prompt, build_tailor_prompt
from .openai_client import openai_json
from .settings import settings_manager

app = typer.Typer(help="Tailor resumes using the OpenAI Responses API")

# load once 
SETTINGS = settings_manager.load()

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

    lines = read_docx(resume_path)
    numbered = number_lines(lines)
    prompt = build_sectionizer_prompt(numbered)
    data = openai_json(prompt, model=model)
    out_json.write_text(json.dumps(data, indent=2), encoding="utf-8")
    typer.echo(f"Wrote {out_json}")

# * Tailor - tailor resume to job description
# uses OpenAI Responses API to tailor a resume to a job description; generates a JSON object with edits by line number
@app.command()
def tailor(
    job_info: Path = typer.Argument(
        SETTINGS.job_path,
        help="Job description text to tailor resume for",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    ),
    resume_path: Path = typer.Argument(
        SETTINGS.resume_path,
        help="Path to source resume .docx",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    ),
    sections_path: Path = typer.Option(
        SETTINGS.sections_path,
        "--sections-path",
        "-s",
        help="Optional sections.json from the 'sections' command",
        resolve_path=True,
        show_default=True,
    ),
    out_json: Path = typer.Option(
        SETTINGS.edits_path,
        "--out-json",
        "-o",
        help="Where to write the edits JSON",
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
    job_text = read_text(job_info)
    lines = read_docx(resume_path)
    numbered = number_lines(lines)
    sections_json_str = None
    if sections_path and sections_path.exists():
        sections_json_str = sections_path.read_text(encoding="utf-8")

    prompt = build_tailor_prompt(job_text, numbered, sections_json_str)
    data = openai_json(prompt, model=model)
    out_json.write_text(json.dumps(data, indent=2), encoding="utf-8")
    typer.echo(f"Wrote {out_json}")


# * Config management commands
config_app = typer.Typer(help="Manage Loom configuration settings", invoke_without_command=True)
app.add_typer(config_app, name="config")

@config_app.callback()
def config_callback(ctx: typer.Context):
    """Manage Loom configuration settings"""
    if ctx.invoked_subcommand is None:
        # Show help when no subcommand is provided
        typer.echo(ctx.get_help())

# * List - list all current settings
@config_app.command("list", help="Show all current configuration settings")
def config_list():
    settings = settings_manager.list_settings()
    typer.echo("Current Loom settings:")
    for key, value in settings.items():
        typer.echo(f"  {key}: {value}")

# * Get - get a specific setting value
@config_app.command("get", help="Get the value of a specific setting")
def config_get(key: str = typer.Argument(..., help="Setting name to retrieve (e.g., model, data_dir, resume_filename)")):
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
@config_app.command("set", help="Set a configuration value")
def config_set(
    key: str = typer.Argument(..., help="Setting name (model, data_dir, output_dir, resume_filename, job_filename)"),
    value: str = typer.Argument(..., help="New value for the setting")
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
@config_app.command("reset", help="Reset all settings to their default values")
def config_reset():
    if typer.confirm("Reset all settings to defaults?"):
        settings_manager.reset()
        typer.echo("Settings reset to defaults")
    else:
        typer.echo("Reset cancelled")

# * Path - show config file path
@config_app.command("path", help="Show the path to the configuration file")
def config_path():
    typer.echo(f"Config file: {settings_manager.config_path}")