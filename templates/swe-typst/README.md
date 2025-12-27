# Software Engineering Typst Resume Template

A clean, ATS-friendly resume template for software engineers using Typst.

## Files

- `resume.typ` - Main resume template with sample content
- `loom-template.toml` - Loom template descriptor for section detection

## Usage

1. Copy `resume.typ` to your working directory
2. Edit the content to match your experience
3. Use Loom to tailor for job descriptions:

```bash
loom tailor job.txt resume.typ --output-resume tailored.typ
```

## Compiling

Compile the resume with Typst:

```bash
typst compile resume.typ resume.pdf
```

## Template Features

- Self-contained helper functions (`#name`, `#contact`, `#entry`)
- Section headings with horizontal rules
- Grid-based entry layout for experience/education
- ATS-friendly formatting
- Frozen structural elements (preamble, helper functions) protected during editing
