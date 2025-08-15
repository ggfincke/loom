# src/ui/help/help_templates.py  
# Help content templates & metadata for branded CLI help screens

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


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
    default: str | None = None
    required: bool = False


# command help templates w/ rich descriptions & examples
COMMAND_HELP = {
    "sectionize": CommandHelp(
        name="sectionize",
        description="Parse resume document into structured sections using AI",
        long_description=(
            "Analyzes your resume document and identifies distinct sections like "
            "SUMMARY, EXPERIENCE, EDUCATION, etc. Creates a JSON mapping that "
            "enables precise targeting during the tailoring process."
        ),
        examples=[
            "loom sectionize resume.docx --out-json sections.json",
            "loom sectionize my_resume.docx  # Uses config defaults for output",
            "loom sectionize resume.docx --model gpt-4o  # Use specific model",
        ],
        see_also=["generate", "tailor", "config"],
    ),
    
    "generate": CommandHelp(
        name="generate", 
        description="Generate edits.json with AI-powered resume tailoring for job requirements",
        long_description=(
            "Analyzes a job description against your resume and generates precise "
            "line-by-line edits to optimize your resume for the specific role. "
            "Outputs edits in JSON format for review before application."
        ),
        examples=[
            "loom generate job_posting.txt resume.docx --out-json edits.json",
            "loom generate job.txt resume.docx --sections-path sections.json",
            "loom generate job.txt resume.docx --model gpt-4o-mini",
        ],
        see_also=["apply", "tailor", "sectionize"],
    ),
    
    "apply": CommandHelp(
        name="apply",
        description="Apply edits from JSON to resume document & generate tailored output", 
        long_description=(
            "Takes an edits JSON file (from 'generate' command) and applies all "
            "modifications to your resume document. Preserves original formatting "
            "while making precise content changes."
        ),
        examples=[
            "loom apply edits.json resume.docx --output tailored_resume.docx",
            "loom apply edits.json resume.docx --no-preserve-formatting",
            "loom apply edits.json resume.docx  # Uses config defaults",
        ],
        see_also=["generate", "tailor"],
    ),
    
    "tailor": CommandHelp(
        name="tailor",
        description="Complete end-to-end resume tailoring: generate edits & apply in one step",
        long_description=(
            "Combines 'generate' and 'apply' into a single workflow. Analyzes the "
            "job description, generates edits, and produces a tailored resume "
            "document ready for submission."
        ),
        examples=[
            "loom tailor job_posting.txt resume.docx",
            "loom tailor job.txt resume.docx --output custom_name.docx", 
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
            "edit generation for complex tailoring scenarios."
        ),
        examples=[
            "loom plan job_posting.txt resume.docx",
            "loom plan job.txt resume.docx --sections-path sections.json",
            "loom plan job.txt resume.docx --out-json planned_edits.json",
        ],
        see_also=["tailor", "generate"],
    ),
    
    "config": CommandHelp(
        name="config",
        description="Manage Loom settings & configuration",
        long_description=(
            "Configure default directories, file names, AI model, and visual themes "
            "to streamline your workflow. Settings are persisted and reduce the need "
            "for command-line arguments."
        ),
        examples=[
            "loom config  # Show all current settings",
            "loom config set model gpt-4o",
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
    "resume_path": OptionHelp(
        name="resume_path",
        type_name="PATH",
        description="Path to resume DOCX file",
        required=True,
    ),
    "job_path": OptionHelp(
        name="job_path", 
        type_name="PATH",
        description="Path to job description text file",
        required=True,
    ),
    "out_json": OptionHelp(
        name="--out-json",
        type_name="PATH",
        description="Output path for JSON file",
    ),
    "output": OptionHelp(
        name="--output",
        type_name="PATH", 
        description="Output path for tailored resume DOCX",
    ),
    "sections_path": OptionHelp(
        name="--sections-path",
        type_name="PATH",
        description="Path to sections JSON file (from sectionize)",
    ),
    "edits_path": OptionHelp(
        name="edits_path",
        type_name="PATH",
        description="Path to edits JSON file",
        required=True,
    ),
    "model": OptionHelp(
        name="--model",
        type_name="TEXT",
        description="OpenAI model to use (gpt-4o, gpt-4o-mini, etc.)",
    ),
    "preserve_formatting": OptionHelp(
        name="--preserve-formatting/--no-preserve-formatting",
        type_name="FLAG",
        description="Preserve original document formatting",
        default="True",
    ),
    "preserve_mode": OptionHelp(
        name="--preserve-mode",
        type_name="CHOICE",
        description="How to preserve formatting (styles, replace, hybrid)",
        default="styles",
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
            "loom config set model gpt-4o  # Set your preferred AI model",
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