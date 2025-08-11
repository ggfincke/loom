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

After installation, you can use the `loom` command from anywhere in your terminal.

### 3. Set Up Environment Variables

Create a `.env` file in the project root and add your OpenAI API key:
```bash
OPENAI_API_KEY=your_api_key_here
```

## Architecture

Loom is organized into clean, modular packages:

```
src/
├── ai/                     # 🧠 AI functionality
│   ├── clients/            # OpenAI API integration
│   └── prompts.py          # Prompt templates
├── cli/                    # 💻 Command-line interface
│   ├── commands.py         # All CLI commands
│   ├── args.py             # Argument definitions
│   └── art.py              # Banner display
├── config/                 # ⚙️ Configuration management
│   └── settings.py         # Settings and defaults
├── core/                   # 🎯 Core business logic
│   └── pipeline.py         # Main processing pipeline
└── loom_io/               # 📁 I/O operations
    ├── documents.py        # DOCX file handling
    └── generics.py         # Generic file operations
```

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

### Help

View all available commands and options:
```bash
loom --help
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
