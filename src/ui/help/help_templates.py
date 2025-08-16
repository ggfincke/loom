# src/ui/help/help_templates.py  
# Help content templates & metadata for branded CLI help screens

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class CommandHelp:
    # help metadata for a command
    name: str
    description: str
    long_description: str | None = None
    examples: List[str] | None = None
    see_also: List[str] | None = None


@dataclass 
class OptionHelp:
    # help metadata for a command option
    name: str
    type_name: str
    description: str
    default: Optional[str] = None
    required: bool = False
    aliases: Optional[List[str]] = None
    config_key: Optional[str] = None


# command help templates w/ rich descriptions & examples
COMMAND_HELP = {
    "sectionize": CommandHelp(
        name="sectionize",
        description="Parse resume document into structured sections using AI",
        long_description=(
            "Analyzes your resume (.docx) and identifies distinct sections such as "
            "SUMMARY, EXPERIENCE, and EDUCATION. Produces a machine-readable JSON map "
            "used to target edits precisely in later steps.\n\n"
            "Defaults: paths come from config when omitted (see 'loom config')."
        ),
        examples=[
            "loom sectionize resume.docx --out-json sections.json",
            "loom sectionize my_resume.docx  # uses config defaults",
            "loom sectionize resume.docx --model gpt-5-mini",
        ],
        see_also=["generate", "tailor", "config"],
    ),
    
    "generate": CommandHelp(
        name="generate", 
        description="Generate edits.json with AI-powered resume tailoring for job requirements",
        long_description=(
            "Compares a job description against your resume and proposes precise, "
            "line-oriented edits optimized for the role. Outputs edits in JSON for "
            "review or later application.\n\n"
            "Argument/option precedence: CLI > config defaults. When not provided, "
            "paths and model fall back to your saved settings (see 'loom config')."
        ),
        examples=[
            "loom generate job.txt resume.docx --edits-json edits.json",
            "loom generate job.txt resume.docx --sections-path sections.json",
            "loom generate job.txt resume.docx -m gpt-5-mini --risk med --on-error ask",
        ],
        see_also=["apply", "tailor", "sectionize"],
    ),
    
    "apply": CommandHelp(
        name="apply",
        description="Apply edits from JSON to resume document & generate tailored output", 
        long_description=(
            "Applies an edits JSON (from 'generate' or 'plan') to your resume and writes "
            "a tailored .docx. Supports preserving original formatting with configurable "
            "modes."
        ),
        examples=[
            "loom apply --edits-json edits.json resume.docx --output-resume tailored.docx",
            "loom apply -e edits.json resume.docx --no-preserve-formatting",
            "loom apply -e edits.json resume.docx -r output/tailored.docx",
        ],
        see_also=["generate", "tailor"],
    ),
    
    "tailor": CommandHelp(
        name="tailor",
        description="Complete end-to-end resume tailoring: generate edits & apply in one step",
        long_description=(
            "Runs generation and apply in one pass: analyzes the job description, "
            "produces edits, then writes a tailored resume. Accepts the same safety "
            "and formatting controls as 'generate'/'apply'."
        ),
        examples=[
            "loom tailor job.txt resume.docx",
            "loom tailor job.txt resume.docx --output-resume custom_name.docx", 
            "loom tailor job.txt resume.docx --sections-path sections.json",
            "loom tailor job.txt resume.docx --no-preserve-formatting",
        ],
        see_also=["generate", "apply", "plan"],
    ),
    
    "plan": CommandHelp(
        name="plan",
        description="Generate edits with step-by-step planning workflow (experimental)",
        long_description=(
            "Experimental command that uses a multi-step planning approach for "
            "resume tailoring. Provides more detailed reasoning and step-by-step "
            "edit generation for complex tailoring scenarios. Accepts the same "
            "options as 'generate' for risk and validation policies."
        ),
        examples=[
            "loom plan job.txt resume.docx",
            "loom plan job.txt resume.docx --sections-path sections.json",
            "loom plan job.txt resume.docx --edits-json planned_edits.json",
        ],
        see_also=["tailor", "generate"],
    ),
    
    "config": CommandHelp(
        name="config",
        description="Manage Loom settings & configuration",
        long_description=(
            "Configure default directories, file names, AI model, and visual theme. "
            "Settings persist to ~/.loom/config.json and are used when CLI arguments "
            "are omitted."
        ),
        examples=[
            "loom config  # Show all current settings",
            "loom config set model gpt-5 # Set default AI model",
            "loom config set data_dir /path/to/job_applications", 
            "loom config set resume_filename my_resume.docx",
            "loom config themes  # Interactive theme selector",
            "loom config get model  # Get specific setting",
            "loom config reset  # Reset all to defaults",
            "loom config path  # Show config file location",
        ],
        see_also=["themes"],
    ),
}


# option help metadata for consistent descriptions
OPTION_HELP = {
    # positional args
    "resume": OptionHelp(
        name="resume_path",
        type_name="PATH",
        description="Path to resume .docx",
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
        description="Where to write the tailored resume .docx",
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


# get help metadata for a command
def get_command_help(command_name: str) -> CommandHelp | None:
    return COMMAND_HELP.get(command_name)


# get help metadata for an option
def get_option_help(option_name: str) -> OptionHelp | None:
    return OPTION_HELP.get(option_name)


# get workflow help information
def get_workflow_help(workflow_name: str) -> Dict | None:
    return WORKFLOW_HELP.get(workflow_name)
