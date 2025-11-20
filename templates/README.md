# swe-latex Resume Template

A clean, professional LaTeX resume template optimized for software engineering positions. This is the standard template format for use with Loom.

## Overview

This template provides a modern, single-column resume layout with:
- Clean section headers with custom `\sectionhead` command
- Modular source files for easy maintenance
- Consistent formatting for dates, roles, and bullet points
- Optimized spacing and typography for readability

## Structure

```
templates/
├── resume.tex              # Main document file
└── src/                    # Modular section files
    ├── custom-commands.tex # LaTeX macros and formatting
    ├── heading.tex         # Contact information
    ├── education.tex       # Education section
    ├── experience.tex      # Work experience
    ├── projects.tex        # Project descriptions
    ├── skills.tex          # Technical skills
    ├── publications.tex    # Publications (optional)
    ├── certifications.tex  # Certifications (optional)
    ├── leadership.tex      # Leadership activities (optional)
    ├── awards.tex          # Awards and honors (optional)
    ├── opensource.tex      # Open source contributions (optional)
    ├── clearance.tex       # Security clearance (optional)
    └── courses.tex         # Relevant coursework (optional)
```

## Usage

### 1. Copy the Template

Copy this entire `templates/` directory to your working location:

```bash
cp -r templates/ my-resume/
cd my-resume/
```

### 2. Customize Your Content

Edit the files in `src/` to add your information:

- **`src/heading.tex`** - Your name and contact details
- **`src/education.tex`** - Schools, degrees, dates
- **`src/experience.tex`** - Work history and achievements
- **`src/projects.tex`** - Notable projects
- **`src/skills.tex`** - Technical skills organized by category

### 3. Enable/Disable Optional Sections

In `resume.tex`, uncomment lines to include optional sections:

```latex
% Optional sections (uncomment to include):
% \input{src/publications}
% \input{src/certifications}
% \input{src/leadership}
% \input{src/awards}
% \input{src/opensource}
% \input{src/clearance}
% \input{src/courses}
```

### 4. Compile the PDF

Using `pdflatex`:
```bash
pdflatex resume.tex
```

Using `latexmk` (recommended for auto-recompilation):
```bash
latexmk -pdf -pvc resume.tex
```

Using an online editor:
- Upload all files to [Overleaf](https://www.overleaf.com)
- Set `resume.tex` as the main document
- Compile with pdfLaTeX

## Custom Commands Reference

The template defines several custom commands in `src/custom-commands.tex`:

### `\name{First}{Last}`
Formats your name in the header.

### `\sectionhead{Title}`
Creates a section heading with consistent styling.

### `\daterange{Start}{End}`
Formats date ranges (e.g., "Jan 2020 – Present").

### `\role{Title}{Company}{Location}{Date Range}`
Formats job titles with company, location, and dates.

### `tightitemize` Environment
A compact itemize environment for bullet points:
```latex
\begin{tightitemize}
  \item First achievement
  \item Second achievement
\end{tightitemize}
```

## Using with Loom

This template is designed to work seamlessly with Loom's resume tailoring system.

### Initialize via Loom CLI

```bash
# List bundled templates
loom templates

# Initialize this template into a working directory
loom init --template swe-latex --output my-resume
```

### Current Usage (Manual)

1. Compile your base resume:
   ```bash
   pdflatex resume.tex
   ```

2. Use the `.tex` file with Loom:
   ```bash
   loom tailor job.txt resume.tex --output-resume tailored.tex
   ```

3. Compile the tailored version:
   ```bash
   pdflatex tailored.tex
   ```

## Design Philosophy

### Simplicity
- Single-column layout for ATS compatibility
- Clean typography, no excessive styling
- Focus on content over decoration

### Modularity
- Each section in its own file for easy editing
- Reusable custom commands for consistency
- Optional sections can be toggled easily

### Maintainability
- All formatting logic in `custom-commands.tex`
- Change styles in one place, applies everywhere
- Clear separation between structure and content

## Tips for Best Results

### Content
- Use action verbs to start each bullet point
- Quantify achievements with metrics when possible
- Tailor bullet points to the target role
- Keep descriptions concise (1-2 lines per bullet)

### Formatting
- Maintain consistent date formats across all sections
- Use parallel structure in bullet points within a section
- Don't exceed 1-2 pages total length
- Use appropriate white space for readability

### With Loom
- Start with a comprehensive base resume
- Let Loom tailor bullet points to specific jobs
- Review AI suggestions before compiling final version
- Keep your base resume updated with latest experience

## Customization

### Changing Fonts
Edit the preamble in `resume.tex`:
```latex
\usepackage{helvet}  % Change to your preferred font package
```

### Adjusting Margins
Modify the geometry settings in `resume.tex`:
```latex
\usepackage[margin=0.75in]{geometry}  % Adjust margin size
```

### Section Styling
Edit `\sectionhead` definition in `src/custom-commands.tex`:
```latex
\newcommand{\sectionhead}[1]{
  % Customize section header appearance here
}
```

## Upstream Source

This template is maintained in the [swe-latex-resume](https://github.com/ggfincke/swe-latex-resume) repository. The version in `data/swe-latex-resume/` is the development/test copy linked as a Git submodule.

## Troubleshooting

### Compilation Errors

**Missing packages:** Install the required LaTeX distribution:
- macOS: `brew install --cask mactex`
- Ubuntu/Debian: `sudo apt-get install texlive-full`
- Windows: Install [MiKTeX](https://miktex.org/)

**Custom command errors:** Ensure `src/custom-commands.tex` is loaded before use.

### Formatting Issues

**Spacing problems:** Check for extra blank lines in source files.

**Alignment issues:** Ensure all `\role{}{}{}{}` commands have 4 arguments.

**Section breaks:** Use `\vspace{}` commands to adjust spacing between sections.

## License

This template is provided as-is for use with the Loom resume tailoring tool. Customize and use freely for your own resumes.

## Related Documentation

- [LaTeX Templates Design](../docs/latex-templates-design.md) - Future Loom integration architecture
- [Loom Documentation](../README.md) - Main Loom CLI documentation

---

**Last Updated:** 2025-11-19
