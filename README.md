# Loom — Resume Tailoring Tool

A Python-based CLI for tailoring resumes to job descriptions using AI models from OpenAI, Anthropic (Claude), or local Ollama.

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

Create a `.env` file in the project root and add your API keys as needed:
```bash
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here   # optional (Claude)
# Ollama requires a local server; no API key needed
```

## Architecture

Loom is a Typer-based CLI organized into focused packages. High-level layout:

```
src/
├── ai/                      # 🧠 AI prompts, types, clients
│   ├── clients/
│   │   ├── openai_client.py  # OpenAI integration
│   │   ├── claude_client.py  # Anthropic Claude integration
│   │   ├── ollama_client.py  # Local Ollama integration
│   │   └── factory.py        # Provider selection
│   ├── models.py             # Supported models & validation
│   ├── prompts.py            # Prompt templates (sectionize, edits, corrections)
│   ├── test_prompts.py       # Prompt sanity helpers
│   └── types.py              # AI result types
├── cli/                     # 💻 CLI entry + commands
│   ├── app.py               # Typer app and command registration
│   ├── helpers.py           # Shared CLI helpers (I/O glue, reporting)
│   ├── logic.py             # CLI orchestration around core pipeline
│   ├── params.py            # Argument/option definitions
│   ├── typer_styles.py      # Custom Typer styling & theme integration
│   └── commands/            # Individual command modules
│       ├── sectionize.py    # Resume section parsing
│       ├── generate.py      # Edit generation
│       ├── apply.py         # Apply edits
│       ├── tailor.py        # End-to-end (generate+apply; supports --edits-only/--apply)
│       ├── plan.py          # Planning workflow
│       ├── config.py        # Configuration management
│       ├── models.py        # List/test models by provider
│       └── help.py          # Enhanced help system
├── config/                  # ⚙️ Settings & persistence
│   └── settings.py          # Settings manager (~/.loom/config.json)
├── core/                    # 🎯 Pure business logic (no I/O)
│   ├── pipeline.py          # Edit generation/application
│   ├── validation.py        # Validation gates and helpers
│   ├── exceptions.py        # Domain exceptions
│   └── constants.py         # Enums and constants
├── loom_io/                 # 📁 File & console I/O
│   ├── documents.py         # DOCX read/write + LaTeX/text support
│   ├── generics.py          # Generic fs/json helpers
│   ├── console.py           # Rich console utilities
│   └── types.py             # I/O-related types
├── ui/                      # ✨ Progress, input, timers, art & theming
│   ├── ascii_art.py         # Banner display
│   ├── banner.txt           # ASCII art banner
│   ├── colors.py            # Color schemes
│   ├── console_theme.py     # Rich theme wiring
│   ├── pausable_timer.py    # Timer utilities
│   ├── progress.py          # Progress bars
│   ├── reporting.py         # Output & diff reporting
│   ├── theme_selector.py    # Interactive theme selection
│   ├── ui.py                # Progress & input utilities
│   ├── help/                # Enhanced help system
│   │   ├── help_renderer.py # Custom help rendering
│   │   └── help_data.py     # Help content & metadata
│   └── quick/               # Quick usage utilities
│       └── quick_usage.py   # Quick command shortcuts
└── main.py                  # Entry point
```

## Key Features

- **Multi‑provider AI**: OpenAI, Anthropic (Claude), or local Ollama
- **Structured Outputs**: Consistent JSON edit operations across providers
- **Surgical Editing**: Operates on line-numbered text for precise, targeted modifications
- **Document Format Preservation**: Maintains original DOCX formatting while modifying content
- **Intelligent Section Recognition**: AI-powered section identification with confidence scoring
- **Flexible Edit Operations**: Supports replace_line, replace_range, insert_after, and delete_range operations
- **Configuration Management**: Persistent settings to streamline workflow and reduce repetitive arguments
- **Section Variants Handling**: Recognizes common resume section name variations (e.g., "PROFESSIONAL SUMMARY" → SUMMARY)

## Usage

Loom provides a streamlined workflow centered around the `tailor` command:

### Quick Start

The fastest way to tailor your resume:

```bash
loom tailor job_description.txt my_resume.docx
```

This generates edits and applies them in one step, creating a tailored resume.

### Tailor Command Options

The `tailor` command supports different modes:

**Full workflow (default):** Generate edits and apply them
```bash
loom tailor job_description.txt resume.docx --output-resume tailored_resume.docx
```

**Generate edits only:** Create edits JSON but don't apply
```bash
loom tailor job_description.txt resume.docx --edits-only --edits-json edits.json
```

**Apply existing edits:** Apply previously generated edits
```bash
loom tailor resume.docx --apply --edits-json edits.json --output-resume tailored_resume.docx
```

### Sectionize Command

For better targeting, first parse your resume into sections:

```bash
loom sectionize resume.docx --out-json sections.json
loom tailor job_description.txt resume.docx --sections-path sections.json

# LaTeX (.tex) resumes are supported
loom sectionize resume.tex --out-json sections.json
loom tailor job_description.txt resume.tex --output-resume tailored_resume.tex
```

This command:
- Analyzes your resume document
- Identifies and categorizes different sections (e.g., Summary, Experience, Skills)
- Outputs structured section data for more precise edits

### Split Workflow: Generate then Apply

If you prefer to review edits before applying:

```bash
# Generate edits only
loom generate job_description.txt resume.docx --sections-path sections.json --out-json edits.json

# Apply previously generated edits
loom apply resume.docx edits.json --output-resume tailored_resume.docx
```

### Streamlined Workflow with Configuration

After setting up your configuration, you can run commands with minimal arguments:

```bash
# Set up your defaults once
loom config set data_dir ~/Documents/resumes
loom config set resume_filename my_resume.docx
loom config set model gpt-5-mini
# Or use Claude/Ollama models; see `loom models`
loom config themes                 # Interactive theme selector

# Then run commands without repeating paths
loom sectionize                    # Uses configured resume and output locations
loom tailor job_posting.txt        # Uses configured resume and sections
```

### Help & Models

View all available commands and options:
```bash
loom --help
loom models      # List available models by provider
```

## Quick Build & Smoke Tests

- Create env: `conda create -n loom python=3.12 && conda activate loom`
- Install deps: `pip install -r requirements.txt`
- Install CLI (editable): `pip install -e .` (provides `loom` command)
- Smoke tests:
  - Sectionize: `loom sectionize path/to/resume.docx --out-json sections.json` (or `.tex`)
  - Tailor: `loom tailor job.txt path/to/resume.docx --sections-path sections.json --edits-json edits.json` (or `.tex` with `--output-resume out.tex`)
  - Models: `loom models` (checks available OpenAI/Claude/Ollama models)

## Configuration Management

Loom reads defaults from `~/.loom/config.json`. You can manage settings either via the CLI or by editing the JSON directly.

### Using the CLI

```bash
# Show config file location
loom config path

# List all settings
loom config list

# Get or set a specific setting
loom config get model
loom config set model gpt-5
loom config set model claude-sonnet-4
loom config set model deepseek-r1:14b   # example Ollama model

# Interactive theme selection
loom config themes

# Reset to defaults
loom config reset
```

### Editing JSON Directly

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
  "model": "gpt-5",
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
- Validate paths & file types in `loom_io/` before processing.
- Never commit secrets. Keep API keys in `.env` or your shell, not in source.

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
