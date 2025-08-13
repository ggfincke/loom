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

Loom is built as a CLI tool using Typer with a clean, modular package structure:

```
src/
├── ai/                     # 🧠 AI functionality
│   ├── clients/            # OpenAI API integration
│   │   └── openai_client.py
│   ├── prompts.py          # Prompt templates
│   ├── test_prompts.py     # Test prompts for validation
│   └── types.py            # AI-related type definitions
├── cli/                    # 💻 Command-line interface
│   ├── commands.py         # All CLI commands and handlers
│   ├── args.py             # Argument definitions
│   ├── art.py              # Banner display functionality
│   └── banner.txt          # ASCII art banner
├── config/                 # ⚙️ Configuration management
│   └── settings.py         # Settings, defaults, and config handling
├── core/                   # 🎯 Core business logic
│   ├── pipeline.py         # Main processing pipeline
│   └── exceptions.py       # Custom exception classes
└── loom_io/               # 📁 I/O operations
    ├── documents.py        # DOCX file processing
    ├── generics.py         # Generic file operations
    ├── console.py          # Console output handling
    ├── ui.py               # User interface components
    └── types.py            # I/O type definitions
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
loom tailor job_description.txt path/to/resume.docx --sections-path sections.json --out-json edits.json
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

## Configuration Management

Loom supports persistent configuration settings to avoid repeating common options. Settings are stored in `~/.loom/config.json`.

### View current settings
```bash
loom config list
```

### Set default directories and model
```bash
loom config set data_dir /path/to/your/data
loom config set output_dir /path/to/your/output
loom config set model gpt-4o
```

### Set default filenames
```bash
loom config set resume_filename my_resume.docx
loom config set job_filename job_posting.txt
```

### Get a specific setting
```bash
loom config get model
```

### Reset all settings to defaults
```bash
loom config reset
```

### Show config file location
```bash
loom config path
```

Once configured, commands can be run with fewer arguments:
```bash
# If defaults are set, these commands will use configured paths/model
loom sectionize
loom tailor
```

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
