# Loom Usage Instructions

This document provides comprehensive usage instructions for the Loom resume tailoring tool.

## Quick Start

### Installation & Setup

1. **Environment Setup**:
   ```bash
   conda create -n loom python=3.12
   conda activate loom
   pip install -r requirements.txt
   ```

2. **API Configuration**:
   ```bash
   # Set your provider API keys (as needed)
   export OPENAI_API_KEY="your-openai-key-here"
   export ANTHROPIC_API_KEY="your-anthropic-key-here"
   
   # Or create a .env file in the project root
   cat > .env << 'EOF'
   OPENAI_API_KEY=your-openai-key-here
   ANTHROPIC_API_KEY=your-anthropic-key-here
   EOF
   
   # Ollama: run a local server and pull a model (no API key required)
   #   brew install ollama && ollama serve && ollama pull deepseek-r1:14b
   ```

3. **Verify Installation**:
   ```bash
   loom --help
   ```

## Configuration Management

Loom supports persistent configuration to streamline your workflow. Settings are read from `~/.loom/config.json` and can be managed via CLI.

### Using the CLI

```bash
# Show config location
loom config path

# List settings
loom config list

# Get / Set specific values (values are JSON-coerced)
loom config get model
loom config set model "gpt-5"
loom config set temperature 0.2

# Interactive theme selector
loom config themes

# Reset to defaults
loom config reset
```

### Editing JSON Directly

Create or edit `~/.loom/config.json` to set defaults:

```json
{
  "data_dir": "/path/to/your/data",
  "output_dir": "/path/to/your/output",
  "resume_filename": "my_resume.docx",
  "job_filename": "job_posting.txt",
  "sections_filename": "sections.json",
  "edits_filename": "edits.json",
  "model": "gpt-5",
  "temperature": 0.2,
  "base_dir": ".loom"
}
```

With defaults set, you can omit many CLI arguments:
```bash
loom sectionize
loom generate
loom apply
loom tailor

# Access enhanced help system
loom --help
loom sectionize --help
loom models            # List available models by provider
```

## Core Workflows

### Workflow 1: Full Pipeline (Recommended)

For most users, the `tailor` command provides the complete workflow:

```bash
# With explicit paths
loom tailor job_description.txt resume.docx --output-resume tailored_resume.docx

# With configured defaults (recommended)
loom tailor
```

This single command:
1. Parses your resume into sections
2. Analyzes the job description
3. Generates targeted edits
4. Applies edits to create a tailored resume

### Workflow 2: Step-by-Step Process

For more control, you can break the process into steps:

#### Step 1: Parse Resume Sections
```bash
# Create sections JSON file
loom sectionize resume.docx --out-json sections.json

# With defaults configured
loom sectionize
```

#### Step 2: Generate Edits
```bash
# Generate edit operations
loom generate job_description.txt resume.docx --sections-path sections.json --out-json edits.json

# With defaults configured
loom generate
```

#### Step 3: Apply Edits
```bash
# Apply edits to create tailored resume
loom apply resume.docx edits.json --output-resume tailored_resume.docx

# With defaults configured
loom apply
```

## Command Reference

### `loom sectionize`

Parses a resume into structured sections for better AI understanding.

**Usage:**
```bash
loom sectionize [RESUME_PATH] [OPTIONS]
```

**Options:**
- `--out-json PATH`: Output path for sections JSON file
- `--model TEXT`: Model to use (see `loom models`)
- `--help`: Show enhanced command help

**Example Output:** Creates a JSON file with identified resume sections, subsections, and confidence scores.

### `loom tailor`

Complete resume tailoring workflow in one command.

**Usage:**
```bash
loom tailor [JOB_PATH] [RESUME_PATH] [OPTIONS]
```

**Options:**
- `--sections-path PATH`: Path to existing sections JSON
- `--output-resume PATH`: Output path for tailored resume (.docx or .tex)
- `--edits-json PATH`: Save generated edits as JSON
- `--model TEXT`: Model to use (OpenAI/Claude/Ollama)
- `--on-error TEXT`: Error handling policy (ask|retry|manual|fail|fail:soft|fail:hard)
- `--risk TEXT`: Validation risk level (low|med|high|strict)
- `--help`: Show enhanced command help

### `loom generate`

Generate edit operations without applying them.

**Usage:**
```bash
loom generate [JOB_PATH] [RESUME_PATH] [OPTIONS]
```

**Options:**
- `--sections-path PATH`: Path to sections JSON file
- `--out-json PATH`: Output path for edits JSON
- `--model TEXT`: Model to use (see `loom models`)
- `--on-error TEXT`: Error handling policy
- `--risk TEXT`: Validation risk level

### `loom apply`

Apply previously generated edits to a resume.

**Usage:**
```bash
loom apply [RESUME_PATH] [EDITS_PATH] [OPTIONS]
```

**Options:**
- `--output-resume PATH`: Output path for tailored resume (.docx or .tex)
- `--on-error TEXT`: Error handling policy
- `--risk TEXT`: Validation risk level

### `loom config`

Manage Loom settings & configuration including visual themes.

**Usage:**
```bash
loom config [SUBCOMMAND] [OPTIONS]
```

**Subcommands:**
- `list`: Show all current settings
- `get KEY`: Get specific setting value
- `set KEY VALUE`: Set specific setting
- `themes`: Interactive theme selector
- `path`: Show config file location
- `reset`: Reset all settings to defaults

**Configuration File:** Loom reads defaults from `~/.loom/config.json`. Edit this file to change paths, filenames, model defaults, and theme preferences.

## Advanced Usage

### Error Handling Policies

Control how Loom handles validation errors:

- `ask` (default): Prompt user for action when errors occur
- `fail`: Stop execution on any error
- `retry`: Automatically retry failed operations
- `manual`: Allow manual intervention and continuation

```bash
loom tailor job.txt resume.docx --on-error retry
```

### Risk Levels

Control validation strictness:

- `low`: Minimal validation, faster processing
- `med` (default): Balanced validation and performance
- `high`: Strict validation, slower but safer
- `strict`: Maximum validation, may catch edge cases

```bash
loom tailor job.txt resume.docx --risk high
```

### Model Selection

Choose models from OpenAI, Anthropic (Claude), or local Ollama. See `loom models` for availability.

```bash
# OpenAI examples
loom tailor job.txt resume.docx --model gpt-5
loom tailor job.txt resume.docx --model gpt-5-mini
loom tailor job.txt resume.docx --model gpt-5-nano

# Claude examples
loom tailor job.txt resume.docx --model claude-sonnet-4
loom tailor job.txt resume.docx --model claude-3-5-haiku-20241022

# Ollama example (ensure server running and model pulled)
loom tailor job.txt resume.docx --model deepseek-r1:14b
```

## File Organization

### Recommended Directory Structure

```
~/loom-work/
├── data/
│   ├── master_resume.docx
│   ├── software_engineer_job.txt
│   ├── product_manager_job.txt
│   └── sections.json
├── output/
│   ├── tailored_software_engineer.docx
│   ├── tailored_product_manager.docx
│   └── edits_software_engineer.json
└── .env
```

### File Naming Conventions

- **Resumes**: Use descriptive names like `john_doe_resume.docx`
- **Job Descriptions**: Include company/role like `google_swe_job.txt`
- **Output Files**: Use format like `tailored_google_swe.docx`
- **Edit Files**: Match job description like `edits_google_swe.json`

## Tips & Best Practices

### Initial Setup

1. **Configure Defaults**: Use `loom config` to set up your directories and preferences once
2. **Choose Theme**: Use `loom config themes` to select a visual theme that works well in your terminal
3. **Test Help System**: Run `loom --help` to verify the enhanced help display works correctly

### Resume Preparation

1. **Use Standard Sections**: Ensure your resume has clear section headers (Summary, Experience, Education, Skills, etc.)
2. **Consistent Formatting**: Use consistent bullet points and formatting throughout
3. **Save as DOCX**: Loom works best with .docx files (not .doc or PDF)

### Job Description Preparation

1. **Complete Text**: Copy the full job description, including requirements and nice-to-haves
2. **Clean Formatting**: Remove excessive formatting, but keep structure
3. **Save as TXT**: Plain text files work best for job descriptions

### Configuration Strategy

1. **Set Defaults Early**: Configure your directories and filenames once
2. **Use Descriptive Paths**: Choose clear, consistent directory structures
3. **Keep Backups**: Always keep your original resume safe

### Quality Control

1. **Review Sections**: Check the sections.json output to ensure proper parsing
2. **Validate Edits**: Review generated edits.json before applying
3. **Test Different Models**: Try different models for quality/speed trade-offs
4. **Use Higher Risk Levels**: For important applications, use `--risk high`

## Troubleshooting

### Common Issues

**"File not found" errors:**
- Check file paths are correct
- Ensure files have proper extensions (.docx, .txt)
- Use absolute paths if relative paths fail

**Display/theme issues:**
- Try `loom config themes` to select a different theme
- Verify your terminal supports color output
- Use `loom --help-raw` for basic Typer help if enhanced help fails

**OpenAI API errors:**
- Verify your API key is set correctly
- Check your OpenAI account has credits
- Try a different model if one is experiencing issues

**Validation errors:**
- Try a lower risk level (`--risk low`)
- Use `--policy ask` to handle errors interactively
- Check that your resume has clear section structure

**Poor edit quality:**
- Use a more powerful model (`gpt-5` instead of `gpt-5-mini`)
- Ensure your job description is complete and detailed
- Try generating sections first with `loom sectionize`

### Getting Help

- Use `loom --help` for enhanced general help with visual styling
- Use `loom [command] --help` for command-specific help
- Use `loom --help-raw` for basic Typer help if enhanced help has issues
- Use `loom config themes` to adjust visual appearance
- Check your JSON config at `~/.loom/config.json`
- Review generated files (sections.json, edits.json) to debug issues

## Next Steps

Once you're comfortable with basic usage:

1. Set up your configuration for streamlined workflows
2. Customize your visual theme with `loom config themes`
3. Experiment with different models and risk levels
4. Create templates for common job types
5. Build a library of tailored resumes for different roles

For advanced usage and extending Loom's capabilities, see the architecture documentation.
