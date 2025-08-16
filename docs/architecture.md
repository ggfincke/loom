# Loom Architecture & Internal Design

This document explains how the Loom CLI tool works internally - its architecture, organization, data flow, and how components work together.

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
│   ├── typer_styles.py    # Custom Typer styling & theme integration
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
The application uses Typer for command-line interface with Rich for progress display and custom theming. Commands:

- `sectionize`: Parses resume into structured sections
- `generate`: Creates edits JSON from job description + resume
- `apply`: Applies existing edits to produce tailored resume
- `tailor`: End-to-end: generate+apply to produce tailored resume
- `plan`: Planning-based edit generation
- `config`: Configuration management with theme selection

The CLI features an enhanced help system with:
- Custom branded help screens with gradient styling
- Theme-aware color schemes and visual styling
- Interactive theme selector (`config themes`)
- Contextual help templates and improved UX

Each command follows a consistent pattern:
1. Load settings and validate inputs
2. Create Rich progress tracker with theme-aware styling
3. Execute pipeline operations with progress updates
4. Handle validation warnings
5. Write outputs and display success messages

### 2. Pipeline Layer (`pipeline.py`)
The core processing engine that handles:

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
Handles all document I/O operations:

- **DOCX Reading**: Extracts text from Word documents into line-numbered dict
- **DOCX Writing**: Reconstructs Word documents from line dict
- **Line Numbering**: Converts line dict to numbered text format for AI
- **Text/JSON I/O**: Utility functions for file operations

Key data structure: `Lines = Dict[int, str]` - maps line numbers to text content.

### 4. AI Integration (`src/ai/clients/*`, `src/ai/prompts.py`)

**Providers**:
- OpenAI: Uses Responses-like APIs for structured JSON output
- Anthropic (Claude): Compatible JSON responses with policy handling
- Ollama: Local models discovered dynamically; JSON enforced in prompts

All providers normalize to a consistent JSON edit schema with robust parsing and error messages.

**Prompt Engineering**:
- **Sectionizer Prompt**: Analyzes resume structure, identifies sections with confidence scores, detects subsections (experience items, projects, education)
- **Generate Prompt**: Comprehensive editing instructions with strict policies on truthfulness, embellishment bounds, job alignment, and safety checks

### 5. Configuration (`src/config/settings.py`)
Manages persistent user preferences:

- **LoomSettings dataclass**: Default paths, filenames, model selection
- **SettingsManager**: JSON-based persistence in `~/.loom/config.json`
- **Property methods**: Dynamic path construction from base settings
- **CRUD operations**: get, set, reset, list settings

### 6. CLI Enhancement (`src/cli/` and `src/ui/`)
**CLI Types (`src/cli/params.py`)**:
- Argument validation (file existence, readability)
- Path resolution and type checking
- Help text generation
- Default value management
- Optional parameter handling

**UI System (`src/ui/`)**:
- **Theme Management**: Interactive theme selection with persistent preferences
- **Custom Help**: Branded help screens with gradient styling and improved UX
- **Visual Elements**: ASCII art banners, color schemes, and styling consistency
- **Progress Indicators**: Rich-based progress tracking with theme integration
- **Quick Access**: Shortcuts and utility functions for common workflows

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
- Basic functionality works without sections.json
- Sections data enables more targeted editing
- Risk levels provide granular validation control
- Theme system provides visual customization without affecting functionality

### 5. Immutable Transformations
Line dictionaries are copied, not modified in place. Operations return new state rather than mutating existing state.

### 6. Modular UI Architecture
UI components are separated into focused modules:
- **Theming**: Centralized color schemes and visual styling
- **Help System**: Branded help screens with custom rendering
- **Progress Display**: Rich-based progress tracking with theme integration
- **Interactive Elements**: Theme selector, quick access utilities

## AI Integration Strategy

### Structured Output
Uses provider integrations that enforce JSON structure (via Responses-style calls or prompt constraints) rather than parsing free-form text.

### Prompt Engineering
- **Constraints**: Strict rules about truthfulness, evidence-based editing
- **Context**: Job description, numbered resume text, optional sections
- **Operations**: Line-level edit operations with validation
- **Safety**: Multiple validation layers and user confirmation

### Model Flexibility
Supports OpenAI, Anthropic (Claude), and local Ollama models with feature detection and availability checks. The `loom models` command lists usable models by provider.

## Configuration Philosophy

### Convention over Configuration
Provides sensible defaults while allowing customization of:
- File paths and naming conventions
- Model selection and parameters  
- Validation strictness levels
- Error handling policies

### Settings Inheritance
CLI arguments override settings, which override hardcoded defaults.

## Extensibility Points

1. **New Edit Operations**: Add operation types in `core/pipeline.py`
2. **Additional Prompts**: Extend prompt templates in `ai/prompts.py`
3. **Document Formats**: Add readers/writers in `loom_io/documents.py`
4. **Validation Rules**: Extend validation logic in `core/validation.py`
5. **CLI Commands**: Add new command modules in `cli/commands/`
6. **UI Themes**: Add new color schemes in `ui/colors.py`
7. **Help Content**: Extend help content in `ui/help/help_data.py`
8. **Interactive Features**: Add new UI components in `ui/` package

This architecture provides a solid foundation for resume tailoring while maintaining flexibility for future enhancements. The modular design allows for easy extension of both core functionality and user experience features.
