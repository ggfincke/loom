# Loom Architecture & Internal Design

This document explains how Loom is structured & built: its architecture, data flow, key modules, & the design decisions behind them.

## Overview

Loom is a Python CLI application built with Typer that uses AI providers (OpenAI, Anthropic/Claude, or local Ollama) to intelligently tailor resumes to job descriptions. The tool operates through a pipeline architecture with two main phases: **sectionization** (parsing) and **tailoring** (editing).

## Project Structure

```
src/
├── main.py                # Entry point (delegates to cli.app)
├── ai/
│   ├── clients/openai_client.py  # OpenAI API integration
│   ├── clients/claude_client.py  # Anthropic Claude integration
│   ├── clients/ollama_client.py  # Local Ollama integration
│   └── clients/factory.py        # Provider selection
│   ├── prompts.py         # Prompt engineering for AI interactions
│   ├── test_prompts.py    # Prompt sanity helpers
│   └── types.py           # AI result types
├── cli/
│   ├── app.py             # Typer app + command registration
│   ├── helpers.py         # CLI-layer orchestration + I/O glue
│   ├── logic.py           # CLI business logic coordination
│   ├── params.py          # Argument and option definitions
│   └── commands/          # Individual command modules
│       ├── sectionize.py  # Resume section parsing command
│       ├── generate.py    # Edit generation command
│       ├── apply.py       # Edit application command
│       ├── tailor.py      # End-to-end tailoring command
│       ├── plan.py        # Planning workflow command
│       ├── config.py      # Configuration management command
│       └── help.py        # Enhanced help system
├── config/
│   └── settings.py        # Settings manager (~/.loom/config.json)
├── core/
│   ├── pipeline.py        # Core processing pipeline and edit operations
│   ├── validation.py      # Validation gates and helpers
│   ├── exceptions.py      # Custom exception classes
│   └── constants.py       # Enums and constants
├── loom_io/
│   ├── documents.py       # DOCX reading/writing, line numbering
│   ├── console.py         # Console output helpers
│   ├── generics.py        # Generic file helpers (json/text)
│   └── types.py           # I/O type definitions
└── ui/
    ├── ascii_art.py       # Banner display functionality
    ├── banner.txt         # ASCII art banner
    ├── colors.py          # Color scheme definitions
    ├── typer_styles.py    # Custom Typer styling & theme integration
    ├── console_theme.py   # Rich theme wiring
    ├── progress.py        # Progress indicators
    ├── reporting.py       # Output & diff reporting
    ├── pausable_timer.py  # Timer utilities
    ├── theme_selector.py  # Interactive theme selection
    ├── ui.py              # Progress/input utilities
    ├── help/              # Enhanced help system
    │   ├── help_renderer.py # Custom help rendering
    │   └── help_data.py     # Help content & metadata
    └── quick/             # Quick usage utilities
        └── quick_usage.py # Quick command shortcuts
```

## Core Architecture

### 1. CLI Layer (`src/cli/app.py` and `src/cli/commands/*`)
Typer-based CLI w/ Rich for progress & custom theming. Commands:

- `sectionize`: Parses resume into structured sections
- `generate`: Creates edits JSON from job description + resume
- `apply`: Applies existing edits to produce tailored resume
- `tailor`: End-to-end: generate+apply to produce tailored resume
- `plan`: Planning-based edit generation
- `config`: Configuration management with theme selection

Enhanced help system:
- Custom branded help screens with gradient styling
- Theme-aware color schemes and visual styling
- Interactive theme selector (`config themes`)
- Contextual help templates and improved UX

Command execution pattern:
1. Load settings and validate inputs
2. Create Rich progress tracker with theme-aware styling
3. Execute pipeline operations with progress updates
4. Handle validation warnings
5. Write outputs and display success messages

### 2. Pipeline Layer (`pipeline.py`)
Core processing engine:

**Edit Generation (`generate_edits`)**:
- Builds AI prompts using job description and resume
- Calls OpenAI API for structured JSON edit operations
- Validates response structure and operations
- Handles error policies (ask/fail/retry/manual)
- Returns validated edits JSON

**Edit Application (`apply_edits`)**:
- Takes resume lines dict and edits JSON
- Sorts operations by line number (descending to avoid conflicts)
- Applies four operation types:
  - `replace_line`: Single line replacement
  - `replace_range`: Multi-line replacement  
  - `insert_after`: Add content after specific line
  - `delete_range`: Remove line ranges
- Returns modified lines dict

**Validation System**:
- Pre-generation validation of AI responses
- Pre-application validation of edit operations
- Line bounds checking, conflict detection
- Risk-based validation levels (low/med/high/strict)
- Warning generation and policy enforcement

### 3. Document Layer (`src/loom_io/documents.py`)
Document I/O operations:

- **DOCX Reading**: Extracts text from Word documents into line-numbered dict
- **DOCX Writing**: Reconstructs Word documents from line dict
- **Line Numbering**: Converts line dict to numbered text format for AI
- **Text/JSON I/O**: Utility functions for file operations

Key data structure: `Lines = Dict[int, str]` — maps line numbers to text content.

### 4. AI Integration (`src/ai/clients/*`, `src/ai/prompts.py`, `src/ai/models.py`)

Providers:
- OpenAI: Responses-style JSON outputs
- Anthropic (Claude): JSON-compatible responses
- Ollama: Local models; availability detection; prompts enforce JSON

Provider selection via `clients/factory.py`. Model aliasing, validation, & availability in `ai/models.py`.

Prompt Engineering:
- Sectionizer: identifies sections, subsections, confidence scores
- Generate: strict policies on truthfulness, job alignment, bounded edits

### 5. Configuration (`src/config/settings.py`)
Persistent user preferences:

- **LoomSettings dataclass**: Default paths, filenames, model selection
- **SettingsManager**: JSON-based persistence in `~/.loom/config.json`
- **Property methods**: Dynamic path construction from base settings
- **CRUD operations**: get, set, reset, list settings

### 6. CLI Enhancements & UI (`src/cli/`, `src/ui/`)
CLI Types (`src/cli/params.py`): argument validation, path resolution, normalized flags (e.g., `--risk`, `--on-error`).

UI System (`src/ui/`):
- Theme Management: interactive selector + persistent theme
- Custom Help: branded help screens w/ gradients
- Progress Indicators: theme-aware Rich progress
- Reporting: unified result messages & diffs
- Quick Access: quick usage shortcuts

## Data Flow

### Sectionize Workflow
```
resume.docx → read_docx() → Lines dict → number_lines() → 
numbered text → build_sectionizer_prompt() → OpenAI API → 
sections JSON → validate & save
```

### Tailor Workflow
```
job.txt + resume.docx + sections.json → 
generate_edits() → validated edits.json →
apply_edits() → modified Lines dict → 
write_docx() → tailored_resume.docx
```

### Generate-Apply Split
The tool supports separating edit generation from application:
1. **Generate**: `job + resume + sections → edits.json`
2. **Apply**: `resume + edits.json → tailored_resume.docx`

This enables manual review/editing of the generated operations.

## Key Design Patterns

### 1. Pipeline Architecture
Operations are composable functions that transform data through standardized interfaces (Lines dict, JSON objects).

### 2. Validation Gates
Two validation checkpoints:
- **Gate A**: Post-generation validation of AI response
- **Gate B**: Pre-application validation of edit operations

### 3. Error Policy System
Configurable error handling (`ask|fail|fail:soft|fail:hard|manual|retry`) allows users to control behavior when validation fails.

### 4. Progressive Enhancement
- Works without sections.json; sections improve targeting
- Granular validation via risk levels
- Theme system doesn’t affect core logic

### 5. Immutable Transformations
Line dictionaries are copied, not modified in place; operations return new state.

### 6. Modular UI Architecture
Focused modules for theming, help, progress, reporting, & interactive elements.

## AI Integration Strategy

### Structured Output
Provider integrations enforce JSON structure rather than parsing free-form text.

### Prompt Engineering
- Constraints: truthfulness, evidence-based editing, bounded changes
- Context: job description, numbered resume text, optional sections
- Operations: line-level edit operations with validation
- Safety: multi-layer validation & user policies

### Model Flexibility
Supports OpenAI, Anthropic (Claude), & local Ollama with availability checks. `loom models` lists usable models by provider.

## Configuration Philosophy

### Convention over Configuration
Provides sensible defaults while allowing customization of:
- File paths and naming conventions
- Model selection and parameters  
- Validation strictness levels
- Error handling policies

### Settings Inheritance
CLI args override settings, which override hardcoded defaults.

## Extensibility Points

1. New edit operations in `core/pipeline.py`
2. Prompt templates in `ai/prompts.py`
3. Readers/writers in `loom_io/documents.py`
4. Validation rules in `core/validation.py`
5. CLI commands in `cli/commands/`
6. UI themes in `ui/colors.py`
7. Help content in `ui/help/help_data.py`
8. Interactive UI components in `ui/`

## Error Handling & Policies

- Validation policies: `ask`, `retry`, `manual`, `fail:soft`, `fail:hard` (mapped via `--on-error`)
- Risk levels: `low`, `med`, `high`, `strict` adjust validation gates
- Exceptions captured via `core/exceptions.py` and surfaced with user-friendly messages

## Document Editing Modes

- DOCX in-place: preserves styles & formatting by editing paragraphs directly
- DOCX rebuild: constructs a new document from lines (faster; may lose some styles)
- LaTeX: basic structural preservation; writes plain text back out

## Debugging & Logging

- `core/debug.py` enables verbose mode (`--verbose` in commands that support it)
- Progress bars & step names surface where time is spent

## Known Limitations & Future Work

- PDF not supported (convert to DOCX/LaTeX first)
- LaTeX support is basic; complex templates may need manual review
- Model availability varies by environment; `loom models` helps discoverable sets
