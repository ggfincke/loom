# Loom Architecture & Internal Design

This document explains how Loom is structured & built: its architecture, data flow, key modules, & the design decisions behind them.

## Overview

Loom is a Python CLI application built with Typer that uses AI providers (OpenAI, Anthropic/Claude, or local Ollama) to intelligently tailor resumes to job descriptions. The tool operates through a pipeline architecture with two main phases: **sectionization** (parsing) and **tailoring** (editing).

## Project Structure

```
src/
├── main.py                    # Entry point (delegates to cli.app)
├── ai/
│   ├── clients/
│   │   ├── openai_client.py   # OpenAI API integration
│   │   ├── claude_client.py   # Anthropic Claude integration
│   │   ├── ollama_client.py   # Local Ollama integration
│   │   └── factory.py         # Provider selection
│   ├── models.py              # Model configuration & validation
│   ├── prompts.py             # Prompt templates for AI interactions
│   ├── types.py               # AI result types (GenerateResult)
│   └── utils.py               # Shared utilities (JSON parsing, response processing)
├── cli/
│   ├── app.py                 # Typer app + command registration
│   ├── runner.py              # Unified tailoring runner (generate/apply/tailor/plan)
│   ├── logic.py               # CLI business logic coordination
│   ├── helpers.py             # CLI helpers & validation
│   ├── params.py              # Argument and option definitions
│   └── commands/
│       ├── sectionize.py      # Resume section parsing
│       ├── generate.py        # Edit generation
│       ├── apply.py           # Edit application
│       ├── tailor.py          # End-to-end tailoring
│       ├── plan.py            # Planning workflow
│       ├── config.py          # Configuration management
│       ├── models.py          # List available models
│       ├── help.py            # Enhanced help system
│       ├── init.py            # Workspace initialization
│       ├── templates.py       # Template discovery & listing
│       └── dev/
│           └── display.py     # Development utilities
├── config/
│   └── settings.py            # Settings manager (~/.loom/config.json)
├── core/
│   ├── pipeline.py            # Core processing pipeline and edit operations
│   ├── validation.py          # Strategy-based validation error handling
│   ├── edit_helpers.py        # Edit validation & utility functions
│   ├── exceptions.py          # Custom exception classes
│   ├── constants.py           # Enums and constants
│   └── debug.py               # Debug logging utilities
├── loom_io/
│   ├── documents.py           # DOCX/LaTeX/text reading with formatting
│   ├── latex_handler.py       # Comprehensive LaTeX handler with template support
│   ├── latex_patterns.py      # Shared LaTeX pattern constants
│   ├── console.py             # Rich console wrapper
│   ├── generics.py            # Generic file helpers (JSON/text I/O)
│   └── types.py               # I/O type definitions (Lines dict)
└── ui/
    ├── core/
    │   ├── ui.py              # UI abstraction layer
    │   ├── progress.py        # Progress display & loading
    │   ├── pausable_timer.py  # Timer that pauses during interaction
    │   └── rich_components.py # Centralized Rich imports
    ├── theming/
    │   ├── theme_engine.py    # Theme engine implementation
    │   ├── theme_definitions.py # Theme color definitions
    │   ├── theme_selector.py  # Interactive theme selection
    │   ├── console_theme.py   # Console-specific theming
    │   └── typer_styles.py    # Typer help styling patches
    ├── display/
    │   ├── ascii_art.py       # ASCII art rendering
    │   ├── banner.txt         # Banner text file
    │   └── reporting.py       # Result reporting & formatting
    ├── diff_resolution/
    │   └── diff_display.py    # Diff display with state machine pattern
    ├── help/
    │   ├── help_renderer.py   # Branded help screen rendering
    │   └── help_data.py       # Help metadata & command registration
    └── quick/
        └── quick_usage.py     # Quick usage guide display
```

## Core Architecture

### 1. CLI Layer (`src/cli/app.py`, `src/cli/runner.py`, and `src/cli/commands/*`)
Typer-based CLI w/ Rich for progress & custom theming. Commands:

- `sectionize`: Parses resume into structured sections
- `generate`: Creates edits JSON from job description + resume
- `apply`: Applies existing edits to produce tailored resume
- `tailor`: End-to-end: generate+apply to produce tailored resume
- `plan`: Planning-based edit generation
- `config`: Configuration management with theme selection
- `models`: List available models by provider
- `init`: Initialize workspace from template
- `templates`: Discover and list available templates

**Unified Runner** (`cli/runner.py`):
Central orchestrator for all tailoring modes via `TailoringMode` enum:
- `GENERATE`: Produce edits.json only
- `APPLY`: Apply existing edits to resume
- `TAILOR`: Generate + apply in one pass
- `PLAN`: Multi-step planning workflow

Enhanced help system:
- Custom branded help screens with gradient styling
- Theme-aware color schemes and visual styling
- Interactive theme selector (`config themes`)
- Contextual help templates and improved UX

Command execution pattern:
1. Load settings and validate inputs
2. Create Rich progress tracker with theme-aware styling
3. Execute pipeline operations via unified runner
4. Handle validation warnings with strategy pattern
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

**Validation System** (`core/validation.py`, `core/edit_helpers.py`):
- Pre-generation validation of AI responses
- Pre-application validation of edit operations
- Line bounds checking, conflict detection
- Risk-based validation levels (low/med/high/strict)
- Strategy pattern for error handling (Ask/Retry/Manual/Fail strategies)
- Warning generation and policy enforcement

### 3. Document Layer (`src/loom_io/`)
Document I/O operations across multiple modules:

**documents.py** — Core document operations:
- **DOCX Reading**: Extracts text from Word documents into line-numbered dict
- **DOCX Writing**: Reconstructs Word documents from line dict
- **Line Numbering**: Converts line dict to numbered text format for AI
- **Text/JSON I/O**: Utility functions for file operations

**latex_handler.py** — Comprehensive LaTeX support:
- Template metadata loading and validation
- Safe edit filtering to protect structural commands
- LaTeX-aware document reconstruction

**latex_patterns.py** — Shared LaTeX pattern constants:
- Structural commands (document, section, begin/end)
- Item and formatting patterns
- Regex patterns for content identification

Key data structure: `Lines = Dict[int, str]` — maps line numbers to text content.

### 4. AI Integration (`src/ai/`)

**clients/** — Provider implementations:
- OpenAI: Responses-style JSON outputs
- Anthropic (Claude): JSON-compatible responses
- Ollama: Local models; availability detection; prompts enforce JSON
- Factory: Provider selection via `clients/factory.py`

**models.py** — Model configuration:
- Model aliasing, validation, & availability checking
- Provider-specific model listings

**prompts.py** — Prompt engineering:
- Sectionizer: identifies sections, subsections, confidence scores
- Generate: strict policies on truthfulness, job alignment, bounded edits

**utils.py** — Shared utilities:
- JSON parsing and extraction from AI responses
- Markdown stripping and response processing
- Common error handling for malformed outputs

### 5. Configuration (`src/config/settings.py`)
Persistent user preferences:

- **LoomSettings dataclass**: Default paths, filenames, model selection
- **SettingsManager**: JSON-based persistence in `~/.loom/config.json`
- **Property methods**: Dynamic path construction from base settings
- **CRUD operations**: get, set, reset, list settings

### 6. CLI Enhancements & UI (`src/cli/`, `src/ui/`)
CLI Types (`src/cli/params.py`): argument validation, path resolution, normalized flags (e.g., `--risk`, `--on-error`).

UI System (`src/ui/`) organized into subdirectories:
- **core/**: UI abstraction layer, progress display, pausable timer, Rich components
- **theming/**: Theme engine, definitions, selector, console theme, Typer styling
- **display/**: ASCII art, banner, result reporting & formatting
- **diff_resolution/**: Diff display with state machine pattern for visualization
- **help/**: Branded help screen rendering & metadata
- **quick/**: Quick usage guide display

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

### 7. Layer Purity Rules

The codebase enforces strict layer separation to maintain testability and architectural clarity:

| Layer | Purpose | I/O Allowed | Imports From |
|-------|---------|-------------|--------------|
| `core/` | Pure business logic | No | Only stdlib, dataclasses |
| `ai/` | Provider integrations | Network only | core/, stdlib |
| `cli/` | User interaction | Yes | All layers |
| `loom_io/` | File & format I/O | Yes | core/, stdlib |
| `ui/` | Display & theming | Yes | core/, loom_io/, stdlib |
| `config/` | Settings persistence | Yes | core/, stdlib |

**Key rules:**
- `core/` must be pure: no `print()`, `typer.echo()`, `sys.stdin`, `console.*`, or file operations
- `core/` exceptions are pure class definitions only (no I/O in `__init__` or methods)
- I/O decorators (`handle_loom_error`, `require_dev_mode`) belong in `cli/decorators.py`
- Validation strategies that prompt users belong in `cli/validation_handlers.py`
- Model validation with error display belongs in `cli/model_helpers.py`

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
4. LaTeX handling in `loom_io/latex_handler.py`
5. Validation rules in `core/validation.py`
6. CLI commands in `cli/commands/`
7. UI themes in `ui/theming/theme_definitions.py`
8. Help content in `ui/help/help_data.py`
9. Interactive UI components in `ui/core/`

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
