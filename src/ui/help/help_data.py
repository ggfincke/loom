# src/ui/help/help_data.py
# Help data structures & option metadata for CLI help system

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Callable


@dataclass
class CommandHelp:
    # help metadata for command
    name: str
    description: str
    long_description: str | None = None
    examples: List[str] | None = None
    see_also: List[str] | None = None


@dataclass
class OptionHelp:
    # help metadata for command option
    name: str
    type_name: str
    description: str
    default: Optional[str] = None
    required: bool = False
    aliases: Optional[List[str]] = None
    config_key: Optional[str] = None


# * registry to store command metadata
_command_metadata: Dict[str, CommandHelp] = {}


def command_help(
    name: str,
    description: str,
    long_description: str | None = None,
    examples: List[str] | None = None,
    see_also: List[str] | None = None,
) -> Callable:
    # * decorator to attach help metadata directly to command functions
    def decorator(func: Callable) -> Callable:
        metadata = CommandHelp(
            name=name,
            description=description,
            long_description=long_description,
            examples=examples,
            see_also=see_also,
        )
        _command_metadata[name] = metadata

        # attach metadata to function for introspection
        setattr(func, "_help_metadata", metadata)

        return func

    return decorator


def get_command_metadata(command_name: str) -> CommandHelp | None:
    # get help metadata for command
    return _command_metadata.get(command_name)


def get_all_command_metadata() -> Dict[str, CommandHelp]:
    # get all registered command metadata
    return _command_metadata.copy()


def extract_help_from_function(func: Callable) -> CommandHelp | None:
    # extract help metadata directly from a function if it has the decorator
    return getattr(func, "_help_metadata", None)


# * legacy command help dict - kept for backward compatibility
COMMAND_HELP = {}


# option help metadata for consistent descriptions
OPTION_HELP = {
    # positional args
    "resume": OptionHelp(
        name="resume_path",
        type_name="PATH",
        description="Path to resume (.docx or .tex)",
        required=True,
        config_key="resume_path",
    ),
    "job": OptionHelp(
        name="job_path",
        type_name="PATH",
        description="Path to job description text file",
        required=True,
        config_key="job_path",
    ),
    # shared options
    "model": OptionHelp(
        name="--model",
        type_name="TEXT",
        description="OpenAI model to use (see 'loom --help' for supported models)",
        aliases=["-m"],
        default="from config: model",
        config_key="model",
    ),
    "sections_path": OptionHelp(
        name="--sections-path",
        type_name="PATH",
        description="Path to sections JSON (from 'sectionize')",
        aliases=["-s"],
        default="from config: sections_path",
        config_key="sections_path",
    ),
    "edits_json": OptionHelp(
        name="--edits-json",
        type_name="PATH",
        description="Path to edits JSON (read/write depending on command)",
        aliases=["-e"],
        default="from config: edits_path",
        config_key="edits_path",
    ),
    "template": OptionHelp(
        name="--template",
        type_name="TEXT",
        description="Template id to initialize from",
        aliases=["-t"],
        required=True,
    ),
    "output": OptionHelp(
        name="--output",
        type_name="PATH",
        description="Destination directory for template copy",
        aliases=["-o"],
    ),
    "out_json": OptionHelp(
        name="--out-json",
        type_name="PATH",
        description="Where to write sections JSON",
        aliases=["-o"],
        default="from config: sections_path",
        config_key="sections_path",
    ),
    "output_resume": OptionHelp(
        name="--output-resume",
        type_name="PATH",
        description="Where to write the tailored resume (.docx or .tex)",
        aliases=["-r"],
        default="<output_dir>/tailored_resume.docx",
        config_key="output_dir",
    ),
    "risk": OptionHelp(
        name="--risk",
        type_name="CHOICE",
        description="Validation strictness for edits: low | med | high | strict",
        default="med",
    ),
    "on_error": OptionHelp(
        name="--on-error",
        type_name="CHOICE",
        description="Policy when validation finds issues: ask | retry | manual | fail:soft | fail:hard",
        default="ask",
    ),
    "preserve_formatting": OptionHelp(
        name="--preserve-formatting/--no-preserve-formatting",
        type_name="FLAG",
        description="Preserve original DOCX formatting (fonts, styles, etc.)",
        default="true",
    ),
    "preserve_mode": OptionHelp(
        name="--preserve-mode",
        type_name="CHOICE",
        description="Formatting approach: in_place (best preservation) | rebuild (new doc)",
        default="in_place",
    ),
    "plan": OptionHelp(
        name="--plan",
        type_name="INT",
        description="Planning mode: omit for plan-only; set N to cap steps",
    ),
    "edits_only": OptionHelp(
        name="--edits-only",
        type_name="FLAG",
        description="Generate edits JSON only (don't apply)",
        default="false",
    ),
    "apply": OptionHelp(
        name="--apply",
        type_name="FLAG",
        description="Apply existing edits JSON to resume",
        default="false",
    ),
}


# workflow descriptions for help organization
WORKFLOW_HELP = {
    "quick_start": {
        "title": "Quick Start",
        "description": "Get started with Loom in 30 seconds",
        "steps": [
            "loom config set data_dir /path/to/your/applications",
            "loom tailor job_posting.txt my_resume.docx",
            "Review the generated tailored_resume.docx",
        ],
    },
    "step_by_step": {
        "title": "Step-by-Step Workflow",
        "description": "Break down the process for more control",
        "steps": [
            "loom sectionize resume.docx --out-json sections.json",
            "loom generate job.txt resume.docx --out-json edits.json",
            "Review edits.json for accuracy",
            "loom apply edits.json resume.docx --output final_resume.docx",
        ],
    },
    "configuration": {
        "title": "Configuration Setup",
        "description": "Configure Loom for your workflow",
        "steps": [
            "loom config themes  # Choose your preferred visual theme",
            "loom config set data_dir /path/to/job_applications",
            "loom config set output_dir /path/to/tailored_resumes",
            "loom config set model gpt-5-mini",
            "loom config set resume_filename my_standard_resume.docx",
        ],
    },
}


# retrieve help metadata for command (legacy function - now uses decorator registry)
def get_command_help(command_name: str) -> CommandHelp | None:
    return get_command_metadata(command_name)


# get help metadata for option
def get_option_help(option_name: str) -> OptionHelp | None:
    return OPTION_HELP.get(option_name)


# get workflow help information
def get_workflow_help(workflow_name: str) -> Dict | None:
    return WORKFLOW_HELP.get(workflow_name)
