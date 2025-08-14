# Loom — Resume Tailoring Tool

A Python-based tool that uses the OpenAI API to tailor resumes to job descriptions.

## Installation

### 1. Create Conda Environment
```bash
conda create -n loom python=3.12
conda activate loom
```

### 2. Install Dependencies and CLI Tool
```bash
pip install -r requirements.txt
pip install -e .
```

The `pip install -e .` command installs Loom in editable mode, making the `loom` command available from anywhere in your terminal.

### 3. Set Up Environment Variables

Create a `.env` file in the project root and add your OpenAI API key:
```bash
OPENAI_API_KEY=your_api_key_here
```

## Architecture

Loom is a Typer-based CLI organized into focused packages. High-level layout:

```
src/
├── ai/                      # 🧠 AI prompts, types, clients
│   ├── clients/
│   │   └── openai_client.py # OpenAI Responses API integration
│   ├── prompts.py           # Prompt templates (sectionize, edits, corrections)
│   ├── test_prompts.py      # Prompt sanity helpers
│   └── types.py             # AI result types
├── cli/                     # 💻 CLI entry + commands
│   ├── app.py               # Typer app and command registration
│   ├── helpers.py           # Shared CLI helpers (I/O glue, reporting)
│   ├── logic.py             # CLI orchestration around core pipeline
│   ├── params.py            # Argument/option definitions
│   ├── banner.txt           # ASCII art
│   └── commands/
│       ├── sectionize.py
│       ├── generate.py
│       ├── apply.py
│       ├── tailor.py
│       └── plan.py
├── config/                  # ⚙️ Settings & persistence
│   └── settings.py          # Settings manager (~/.loom/config.json)
├── core/                    # 🎯 Pure business logic (no I/O)
│   ├── pipeline.py          # Edit generation/application
│   ├── validation.py        # Validation gates and helpers
│   ├── exceptions.py        # Domain exceptions
│   └── constants.py         # Enums and constants
├── loom_io/                 # 📁 File & console I/O
│   ├── documents.py         # DOCX read/write + line maps
│   ├── generics.py          # Generic fs/json helpers
│   ├── console.py           # Rich console utilities
│   └── types.py             # I/O-related types
└── ui/                      # ✨ Progress, input, timers, art
    ├── ascii_art.py
    ├── pausable_timer.py
    └── ui.py
```

## Key Features

- **OpenAI Responses API Integration**: Uses structured JSON outputs for reliable, consistent AI responses
- **Surgical Editing**: Operates on line-numbered text for precise, targeted modifications
- **Document Format Preservation**: Maintains original DOCX formatting while modifying content
- **Intelligent Section Recognition**: AI-powered section identification with confidence scoring
- **Flexible Edit Operations**: Supports replace_line, replace_range, insert_after, and delete_range operations
- **Configuration Management**: Persistent settings to streamline workflow and reduce repetitive arguments
- **Section Variants Handling**: Recognizes common resume section name variations (e.g., "PROFESSIONAL SUMMARY" → SUMMARY)

## Usage

Loom provides two main commands for resume tailoring:

### Sectionize Command

Parse a resume (.docx) into structured sections:

```bash
loom sectionize path/to/resume.docx --out-json sections.json
```

This command:
- Analyzes your resume document
- Identifies and categorizes different sections (e.g., Summary, Experience, Skills)
- Outputs structured section data to a JSON file

### Tailor Command

Generate targeted edits for your resume based on a job description:

```bash
loom tailor job_description.txt path/to/resume.docx \
  --sections-path sections.json \
  --edits-json edits.json \
  --output-resume tailored_resume.docx
```

This command:
- Takes a job description text file as input
- Analyzes your resume sections (from the sectionize output)
- Generates line-by-line edits to tailor your resume
- Outputs surgical editing instructions to optimize your resume for the specific job

### Streamlined Workflow with Configuration

After setting up your configuration, you can run commands with minimal arguments:

```bash
# Set up your defaults once
loom config set data_dir ~/Documents/resumes
loom config set resume_filename my_resume.docx
loom config set model gpt-4o

# Then run commands without repeating paths
loom sectionize                    # Uses configured resume and output locations
loom tailor job_posting.txt        # Uses configured resume and sections
```

### Help

View all available commands and options:
```bash
loom --help
```

## Quick Build & Smoke Tests

- Create env: `conda create -n loom python=3.12 && conda activate loom`
- Install deps: `pip install -r requirements.txt`
- Install CLI (editable): `pip install -e .` (provides `loom` command)
- Smoke tests:
  - Sectionize: `loom sectionize path/to/resume.docx --out-json sections.json`
  - Tailor: `loom tailor job.txt path/to/resume.docx --sections-path sections.json --edits-json edits.json`

## Configuration Management

Loom reads defaults from `~/.loom/config.json`. Create or edit this file to avoid repeating common options.

Example `~/.loom/config.json`:
```json
{
  "data_dir": "data",
  "output_dir": "output",
  "resume_filename": "resume.docx",
  "job_filename": "job.txt",
  "sections_filename": "sections.json",
  "edits_filename": "edits.json",
  "base_dir": ".loom",
  "model": "gpt-4o",
  "temperature": 0.2
}
```

Once configured, commands can be run with fewer arguments:
```bash
# If defaults are set, these commands will use configured paths/model
loom sectionize
loom tailor
```

## Repository & Local Files

- Source lives under `src/`; generated artifacts go to `output/` (git-ignored).
- Sample inputs under `data/` for experimentation.
- Local config stored at `~/.loom/config.json`; environment variables via `.env`.

## Uninstallation

To remove the CLI tool:
```bash
pip uninstall loom
```

To remove the entire environment:
```bash
conda deactivate
conda remove -n loom --all
```
