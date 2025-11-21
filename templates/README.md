# Loom Templates

Bundled resume templates that ship with Loom. Each template lives in its own folder with a descriptor file so the CLI can discover & scaffold it.

## Layout
- `swe-latex/` — default LaTeX template (see `templates/swe-latex/README.md`)
- Each template folder should include `loom-template.toml`, a main resume file (`resume.tex` or `.docx`), and any supporting partials under `src/` or similar.

## Using Templates
- List available templates: `loom templates`
- Scaffold a workspace: `loom init --template swe-latex --output my-resume`
- Manual copy: `cp -r templates/swe-latex/. my-resume`

## Adding a New Template
- Create `templates/<template-id>/` with a README, `loom-template.toml`, and your template assets.
- Keep paths in the descriptor relative to the main resume file.
- Ensure new assets stay covered by `MANIFEST.in` if they need to be packaged (recursive include already covers `.tex`, `.toml`, `.md`).
