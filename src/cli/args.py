# src/cli/args.py
# Type annotations and argument definitions for CLI commands

from pathlib import Path
from typing import Annotated, Optional
import typer

from ..config.settings import settings_manager

# load settings once
SETTINGS = settings_manager.load()

ResumeArg = Annotated[
    Path,
    typer.Argument(help="Path to resume .docx", exists=True, file_okay=True, dir_okay=False, readable=True, resolve_path=True),
]

JobArg = Annotated[
    Path,
    typer.Argument(help="Path to job description", exists=True, file_okay=True, dir_okay=False, readable=True, resolve_path=True),
]

ModelOpt = Annotated[
    str,
    typer.Option("--model", "-m", help="OpenAI model name", show_default=True),
]

RiskOpt = Annotated[
    str,
    typer.Option("--risk", help="Risk level: low|med|high|strict", show_default=True),
]

OnErrorOpt = Annotated[
    str,
    typer.Option("--on-error", help="ask|fail|fail:soft|fail:hard|manual|retry", show_default=True),
]

EditsArg = Annotated[
    Path,
    typer.Argument(..., help="Path to edits JSON file", exists=True, file_okay=True, dir_okay=False, readable=True, resolve_path=True),
]

OutputArg = Annotated[
    Path,
    typer.Argument(..., help="Output path for tailored resume .docx", resolve_path=True),
]

ConfigKeyArg = Annotated[
    str,
    typer.Argument(..., help="Configuration setting name"),
]

ConfigValueArg = Annotated[
    str,
    typer.Argument(..., help="New value to assign to the setting"),
]

# Single-artifact commands - use --out/-o (infer type by extension)
OutOpt = Annotated[
    Path,
    typer.Option("--out", "-o", help="Output path (infer type by extension: .docx/.json)", resolve_path=True, show_default=True),
]

# Multi-artifact commands - specific artifact flags
EditsJsonOpt = Annotated[
    Path,
    typer.Option("--edits-json", help="Path to write edits JSON", resolve_path=True, show_default=True),
]

ResumeDocxOpt = Annotated[
    Path,
    typer.Option("--resume-docx", help="Path to write tailored DOCX", resolve_path=True, show_default=True),
]

# Optional skips for multi-artifact commands
NoEditsJsonOpt = Annotated[
    bool,
    typer.Option("--no-edits-json", help="Skip writing edits JSON", show_default=True),
]

NoResumeDocxOpt = Annotated[
    bool,
    typer.Option("--no-resume-docx", help="Skip writing tailored DOCX", show_default=True),
]

# Other options
SectionsPathOpt = Annotated[
    Path,
    typer.Option("--sections-path", "-s", help="Optional sections.json path", resolve_path=True, show_default=True),
]

# Consolidated planning flag - use Optional[int] to support --plan (no value) or --plan=N
PlanOpt = Annotated[
    Optional[int],
    typer.Option("--plan", help="Plan mode: no value=plan only, =N for max N steps", show_default=True),
]