# LaTeX Templates Design: Universal Handler + Optional Template Metadata

## Overview

This document outlines Loom's layered approach to LaTeX resume processing, separating universal format handling from template-specific enhancements.

## Architecture Philosophy

Think of Loom's `.tex` story as two layers:

### Layer 1: LaTeX Format Handler (Universal)

**Triggered purely by `*.tex` extension.**

Responsible for:
- Stripping preamble vs body
- Tokenizing commands vs text
- Finding sections & bullets in a generic way
- Generating/applying edits
- **Knows nothing about "Garrett's template" specifically**

### Layer 2: Template Definitions (Optional, Per-Template Sugar)

Small bit of metadata (YAML/TOML/Python) that tells Loom:
- Which macros correspond to "sections" (`\section`, `\cvsection`, `\sectionhead`, etc.)
- Which environments/commands contain bullets (`\item`, `\entry`, `\cventry`, etc.)
- Which parts are frozen (preamble, macros file, etc.)
- **Used only if present; otherwise the generic heuristics run**

### Result

- Any random `.tex` resume on the internet still goes through generic LaTeX handling
- Your template just has extra hints so the output is nicer and safer

---

## Universal LaTeX Behavior (Works for Any resume.tex)

Here's what the generic `.tex` pipeline does, regardless of template:

### 1. Detection

- File extension `.tex` → select LaTeX handler
- No dependency on folder layout, template IDs, etc.

### 2. Generic Sectionization Heuristics

On `loom sectionize resume.tex`:

**Preamble:** Strip everything before `\begin{document}` and after `\end{document}`

**Section Detection:** Match common commands (`\section`, `\subsection`, `\cvsection`) and semantic titles (Education, Experience, Projects, Skills)

**Bullet Detection:** Identify `\item` entries within `\itemize`, `\cvitems`, and similar environments

**Output:** Generate `sections.json` with name, kind, and LaTeX body. Falls back to generic "body" section if standard sections aren't found.

### 3. Universal Editing Rules

**Editing Rules (apply to all LaTeX files):**
- Preserve structure: no changes to `\begin{}`/`\end{}` pairs, `\documentclass`, packages, or macros
- Modify text content only: keep LaTeX commands intact (e.g., `\textbf{...}`, `\item`)
- Drop edits that would remove commands starting with `\`

This provides DOCX-like formatting preservation for arbitrary LaTeX resumes.

---

## Template Enhancement via Optional Metadata

Templates enhance the universal handler through opt-in metadata files, not hardcoded paths.

### 1. Add a Tiny Template Descriptor

In your packaged template (and in your own swe-latex-resume repo), drop something like:

**`loom-template.toml`:**
```toml
[template]
id = "swe-latex"
type = "resume"

[sections.experience]
pattern = "\\sectionhead{Experience}"
pattern_type = "literal"
split_items = true

[sections.projects]
pattern = "\\sectionhead{Projects}"
pattern_type = "literal"
split_items = true

[sections.skills]
pattern = "\\sectionhead{Skills}"
pattern_type = "literal"
split_items = false

[frozen]
# relative to resume.tex
paths = ["src/custom-commands.tex", "src/heading.tex"]
```

This file tells Loom:
- "When you see `\sectionhead{Experience}`, that's the Experience section; split its `\item`s into separate edit units"
- "Don't ever rewrite `custom-commands.tex` or `heading.tex`"

### 2. Autodetection Flow

On `loom sectionize resume.tex`, the handler searches for `loom-template.toml` (same dir or parent), loads it if found, otherwise uses universal heuristics.

Inline markers provide an alternative:
```latex
% loom-template: swe-latex
```
This ensures correct behavior when folder structures change.

### 3. Template-Specific Enhancements

When a template descriptor is found, the handler can use template-specific knowledge (e.g., `\sectionhead` for swe-latex) while falling back to generic rules when the descriptor is absent.

---

## How `loom init --template swe-latex` Fits Into This

The init/templates UX is just a **distribution mechanism**, not a requirement for `.tex` to work:

### Template Discovery
```bash
loom templates
# Lists known templates (swe-latex, maybe others)
```

### Template Initialization
```bash
loom init --template swe-latex
```

This command copies the LaTeX skeleton, including `loom-template.toml` and optional `% loom-template: swe-latex` marker, and may set default config (`resume_filename`, etc.).

### Universal Support Still Works

If someone never runs `loom init` and simply does:
```bash
loom sectionize my_weird_resume.tex
loom tailor job.txt my_weird_resume.tex --output-resume out.tex
```

Everything still works via the generic LaTeX handler.

---

## Summary

✅ **Universal:** Any `.tex` resume works via autodetection and safe text-only edits

✅ **Enhanced:** Templates with descriptors get refined parsing and validation

---

## Implementation Phases (Current Status)

### Phase 1: Universal LaTeX Handler
- [x] Create `src/loom_io/latex_handler.py`
- [x] Preamble/body separation logic
- [x] Generic section detection (regex for `\section`, `\subsection`, `\cvsection`, etc.)
- [x] Semantic section matching (Education, Experience, Projects, Skills)
- [x] Generic `\item` detection for bullets
- [x] Safe text-only editing rules

### Phase 2: Template Metadata System
- [x] Define `loom-template.toml` schema
- [x] Template descriptor loader
- [x] Autodetection logic (search for `loom-template.toml` in cwd/parent)
- [x] Inline marker support (`% loom-template: swe-latex`)
- [x] Frozen file path enforcement

### Phase 3: Integration with Existing Commands
- [ ] Update `src/loom_io/documents.py` to use `latex_handler`
- [x] Enhance `sectionize` for `.tex` files
- [x] Ensure `tailor`, `generate`, `apply` work with LaTeX
- [x] Add template awareness to file detection logic

### Phase 4: Template Management CLI
- [x] `loom templates` command (list available templates)
- [x] `loom init --template <name>` command (scaffold new resume)
- [ ] Package templates in distribution (add to `pyproject.toml` as package data)
- [ ] Template validation command (check `loom-template.toml` syntax)

### Phase 5: Documentation & Examples
- [ ] Update `docs/architecture.md` with LaTeX handler details
- [ ] Create user guide for using templates
- [ ] Add examples of custom templates
- [ ] Document template descriptor format spec

---

## Template Descriptor Format Specification

### Section Keys

Section keys (e.g., `sections.experience`, `sections.projects`) are **logical names** that identify the semantic purpose of each section. These should match standard resume section types: `heading`, `education`, `experience`, `projects`, `skills`, `publications`, `certifications`, etc.

The `kind` field in generated `sections.json` is inferred from the section key by default (e.g., `sections.experience` → `"kind": "experience"`). You can override this with an explicit `kind` field if your template uses non-standard naming.

### Schema (TOML)

```toml
[template]
id = "template-identifier"       # Unique ID for this template
type = "resume"                   # Document type (resume, cv, cover-letter, etc.)
name = "Display Name"             # Optional human-readable name
version = "1.0.0"                 # Optional version

[sections.<section_key>]
pattern = "\\command{Title}"      # LaTeX pattern to match section start
pattern_type = "literal"          # Optional: "literal" (default) or "regex"
kind = "experience"               # Optional: override inferred kind from section_key
split_items = true|false          # Whether to split \item entries
optional = true|false             # Whether section is required

[frozen]
paths = ["relative/path.tex"]     # Files that should never be edited
patterns = ["\\documentclass"]    # LaTeX commands to preserve

[custom]
# Template-specific metadata
# Can be anything the template needs
```

### Example: swe-latex Template

```toml
[template]
id = "swe-latex"
type = "resume"
name = "Software Engineering LaTeX Resume"
version = "1.0.0"

[sections.heading]
pattern = "\\input{src/heading.tex}"
pattern_type = "literal"
split_items = false
optional = false

[sections.education]
pattern = "\\sectionhead{Education}"
pattern_type = "literal"
split_items = true
optional = false

[sections.experience]
pattern = "\\sectionhead{Experience}"
pattern_type = "literal"
split_items = true
optional = false

[sections.projects]
pattern = "\\sectionhead{Projects}"
pattern_type = "literal"
split_items = true
optional = false

[sections.skills]
pattern = "\\sectionhead{Skills}"
pattern_type = "literal"
split_items = false
optional = false

[sections.publications]
pattern = "\\sectionhead{Publications}"
pattern_type = "literal"
split_items = true
optional = true

[sections.certifications]
pattern = "\\sectionhead{Certifications}"
pattern_type = "literal"
split_items = true
optional = true

[frozen]
paths = [
  "src/custom-commands.tex",
  "src/heading.tex"
]
patterns = [
  "\\documentclass",
  "\\usepackage",
  "\\newcommand",
  "\\renewcommand"
]

[custom]
# swe-latex specific settings
partials_dir = "src"
main_file = "resume.tex"
```

---

## Relationship to Existing Code

### Baseline LaTeX Support

Loom currently treats `.tex` files as plain text with no LaTeX-aware sectionization. This design introduces a dedicated LaTeX handler while keeping the existing DOCX/JSON pipelines unchanged.

The new LaTeX handler will live in `src/loom_io/latex_handler.py` and integrate with the existing document pipeline without breaking current functionality.

### Prompts vs Templates

**Prompt templates** (in `src/ai/prompts.py`) are for AI operations and prompt engineering. **Document templates** (this design) are for LaTeX resume structures. These are distinct domains with no naming conflicts.

---

## Migration Path

### For Existing Users
- No breaking changes
- `.tex` files automatically get universal handler
- Users can optionally add `loom-template.toml` for better results

### For Template Authors
1. Create your LaTeX resume structure
2. Add `loom-template.toml` alongside main `.tex` file
3. Document your template's sections and frozen zones
4. Optionally add `% loom-template: <id>` comment in main file

### For Loom Development
1. Implement universal handler first (works without templates)
2. Add template metadata loader (enhances experience)
3. Add CLI commands last (distribution convenience)

---

## FAQ

### Q: Does every `.tex` file need a template descriptor?
**A:** No. The universal handler works fine without it. Templates just make the experience better.

### Q: Can I use Loom with moderncv, altacv, or other LaTeX resume classes?
**A:** Yes! The universal handler should work with any LaTeX resume. Add a `loom-template.toml` to teach Loom about class-specific commands.

### Q: What if my template has custom section commands?
**A:** Add them to `loom-template.toml` under `[sections.<key>]` with the appropriate `pattern` field.

### Q: Can templates be nested or inherit from others?
**A:** Not in v1. Future versions could support template inheritance/composition.

### Q: How does this differ from DOCX handling?
**A:** Same philosophy: preserve formatting, edit content only. LaTeX just requires different parsing (commands vs XML).

---

## Related Documentation

- [Architecture Overview](architecture.md) - Overall Loom architecture
- [Comment Style Guide](comment-style.md) - Code style conventions
- [Templates README](../templates/README.md) - swe-latex template usage

---

**Last Updated:** 2025-11-19
**Status:** Implemented (initial LaTeX handler + template CLI)
