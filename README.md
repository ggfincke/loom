# Loom — Resume Tailoring Tool

[![Version](https://img.shields.io/badge/version-1.3.0-blue.svg)](https://github.com/ggfincke/loom)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![AI Models](https://img.shields.io/badge/AI-OpenAI%20%7C%20Claude%20%7C%20Ollama-purple.svg)](https://github.com/ggfincke/loom)
[![CLI](https://img.shields.io/badge/interface-CLI-orange.svg)](https://github.com/ggfincke/loom)

A Python-based CLI that intelligently tailors resumes to job descriptions using AI models. Features structured JSON edits, interactive diff resolution, and support for OpenAI, Anthropic (Claude), and local Ollama models.

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

Loom is a Typer-based CLI organized into focused packages. For internals & package layout, see `docs/architecture.md`.

## What Loom Does

- Tailors resumes to job descriptions using AI with structured JSON edits
- Preserves DOCX formatting (DOCX in-place or rebuild modes); supports LaTeX/text
- Works with OpenAI, Anthropic (Claude), & local Ollama models
- Offers validation controls via `--risk` & `--on-error` policies

## Interactive Features

**Diff Resolution Workflow**: Review and approve changes with a built-in diff viewer before applying them to your resume. Use `--auto` flag for streamlined interactive editing.

**Planning Mode**: Experimental step-by-step planning workflow (`loom plan`) that provides detailed reasoning for complex tailoring scenarios.

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
# DOCX (.docx) resumes are supported
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

### Split Workflow: Review Before Apply

If you prefer to review edits before applying:

```bash
# Generate edits only (review them first)
loom tailor job_description.txt resume.docx --edits-only --edits-json edits.json

# Apply previously generated edits
loom tailor resume.docx --apply --edits-json edits.json --output-resume tailored_resume.docx

# Alternative: Use the experimental planning workflow
loom plan job_description.txt resume.docx --edits-json planned_edits.json
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

**Supported AI Models:**
- **OpenAI**: gpt-5, gpt-5-mini, gpt-5-nano, gpt-4o, gpt-4o-mini
- **Claude**: claude-opus-4-1-20250805, claude-sonnet-4-20250514, claude-3-7-sonnet-20250219
- Local LLMs supported via **Ollama**

## Quick Build & Smoke Tests

- Create env: `conda create -n loom python=3.12 && conda activate loom`
- Install deps: `pip install -r requirements.txt`
- Install CLI (editable): `pip install -e .` (provides `loom` command)
- Smoke tests:
  - Sectionize: `loom sectionize path/to/resume.docx --out-json sections.json` (or `.tex`)
  - Tailor: `loom tailor job.txt path/to/resume.docx --sections-path sections.json --edits-json edits.json` (or `.tex` with `--output-resume out.tex`)
  - Models: `loom models` (checks available OpenAI/Claude/Ollama models)

## Testing

Run tests with `pytest -q`. Smoke test via:

```bash
loom sectionize data/resume.docx --out-json data/sections.json
loom tailor data/job.txt data/resume.docx --output-resume output/tailored_resume.docx
```

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
  "model": "gpt-5-mini",
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

- Source lives under `src/`; generated artifacts go to `output/` (git-ignored)
- Sample inputs under `data/` for experimentation
- Local config stored at `~/.loom/config.json`; environment variables via `.env`

For deeper internals, see `docs/architecture.md`. For testing, see `docs/testing.md`.
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
