# Loom Architecture & Internal Design

This document explains how the Loom CLI tool works internally - its architecture, organization, data flow, and how components work together.

## Overview

Loom is a Python CLI application built with Typer that uses OpenAI's Responses API to intelligently tailor resumes to job descriptions. The tool operates through a pipeline architecture with two main phases: **sectionization** (parsing) and **tailoring** (editing).

## Project Structure

```
src/
├── main.py         # Entry point (imports cli.app)
├── cli.py          # Main CLI application with Typer commands  
├── cli_args.py     # Annotated argument/option type definitions
├── pipeline.py     # Core processing pipeline and edit operations
├── document.py     # Document I/O (DOCX reading/writing, line numbering)
├── openai_client.py # OpenAI API integration and response handling
├── prompts.py      # Prompt engineering for AI interactions
└── settings.py     # Configuration management and persistence
```

## Core Architecture

### 1. CLI Layer (`cli.py`)
The application uses Typer for command-line interface with Rich for progress display. Main commands:

- **`sectionize`**: Parses resume into structured sections
- **`tailor`**: Generates line-by-line edits for job alignment  
- **`generate`**: Creates edits JSON from job description + resume
- **`apply`**: Applies existing edits to produce tailored resume
- **`plan`**: Planning-based edit generation (stub implementation)
- **`config`**: Settings management subcommands

Each command follows a consistent pattern:
1. Load settings and validate inputs
2. Create Rich progress tracker
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

### 3. Document Layer (`document.py`)
Handles all document I/O operations:

- **DOCX Reading**: Extracts text from Word documents into line-numbered dict
- **DOCX Writing**: Reconstructs Word documents from line dict
- **Line Numbering**: Converts line dict to numbered text format for AI
- **Text/JSON I/O**: Utility functions for file operations

Key data structure: `Lines = Dict[int, str]` - maps line numbers to text content.

### 4. AI Integration (`openai_client.py`, `prompts.py`)

**OpenAI Client**:
- Loads environment variables and API keys
- Handles GPT-5 vs other model differences (temperature parameter)
- Uses OpenAI Responses API for structured JSON output
- Strips markdown code blocks from responses
- Validates JSON parsing with detailed error messages

**Prompt Engineering**:
- **Sectionizer Prompt**: Analyzes resume structure, identifies sections with confidence scores, detects subsections (experience items, projects, education)
- **Generate Prompt**: Comprehensive editing instructions with strict policies on truthfulness, embellishment bounds, job alignment, and safety checks

### 5. Configuration (`settings.py`)
Manages persistent user preferences:

- **LoomSettings dataclass**: Default paths, filenames, model selection
- **SettingsManager**: JSON-based persistence in `~/.loom/config.json`
- **Property methods**: Dynamic path construction from base settings
- **CRUD operations**: get, set, reset, list settings

### 6. Type System (`cli_args.py`)
Uses Python typing with Typer annotations for:
- Argument validation (file existence, readability)
- Path resolution and type checking
- Help text generation
- Default value management
- Optional parameter handling

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

### 5. Immutable Transformations
Line dictionaries are copied, not modified in place. Operations return new state rather than mutating existing state.

## AI Integration Strategy

### Structured Output
Uses OpenAI Responses API for guaranteed JSON structure rather than parsing free-form text.

### Prompt Engineering
- **Constraints**: Strict rules about truthfulness, evidence-based editing
- **Context**: Job description, numbered resume text, optional sections
- **Operations**: Line-level edit operations with validation
- **Safety**: Multiple validation layers and user confirmation

### Model Flexibility
Supports different OpenAI models with feature detection (GPT-5 temperature handling).

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

1. **New Edit Operations**: Add operation types in `pipeline.py`
2. **Additional Prompts**: Extend prompt templates in `prompts.py`
3. **Document Formats**: Add readers/writers in `document.py`
4. **Validation Rules**: Extend validation logic in `pipeline.py`
5. **CLI Commands**: Add new commands in `cli.py`

This architecture provides a solid foundation for resume tailoring while maintaining flexibility for future enhancements.