# Contributing to Loom

Thanks for your interest in improving Loom! This guide outlines the workflow and expectations for contributions.

## Workflow

- Use Python 3.12 and follow PEP 8 with 4-space indents; add type hints in new/modified code.
- Follow `docs/comment-style.md` exactly - single-line comments only, use `&` instead of "and", place comments above code.
- Keep `core/` pure (no I/O). CLI/UI lives under `cli/` and `ui/`. File/JSON ops under `loom_io/`.
- Small, focused changes only; avoid drive-by fixes unrelated to your PR.

## Setup

1. Create env: `conda create -n loom python=3.12 && conda activate loom`
2. Install deps: `pip install -r requirements.txt`
3. Install CLI (editable): `pip install -e .` (gives the `loom` command)
4. Configure `.env` with `OPENAI_API_KEY` and optionally `ANTHROPIC_API_KEY` (do not commit these). For local models, run an Ollama server.

## Smoke Tests

- Basic help: `loom --help` (verify enhanced help system displays correctly)
- Theme system: `loom config themes` (verify interactive theme selector works)
- Models list: `loom models` (verify provider detection and lists)
- Sectionize: `loom sectionize path/to/resume.docx --out-json sections.json`
- Tailor: `loom tailor job.txt path/to/resume.docx --sections-path sections.json --edits-json edits.json`

## Tests

- Run all tests: `pytest -q` (offline; no API keys or Ollama required)
- Tests live under `tests/` (unit, integration, stress). Keep fixtures small & avoid large binaries.

## Commits & PRs

- Conventional Commits: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`, etc.
- PR description should include: what/why, reproduction steps (commands), before/after behavior, and any config changes (`.env`, `~/.loom`).
- Update `README.md` or `docs/` when user-facing behavior changes; include sample CLI output when useful.

## Security & Configuration

- Never commit secrets. Keep `OPENAI_API_KEY` & `ANTHROPIC_API_KEY` in `.env`.
- Settings persist at `~/.loom/config.json`. Prefer `settings_manager` for reads/writes; do not hard-code defaults.
- Validate paths and file types in `loom_io/` before processing.

## Style Notes

- **Naming**: modules/files `snake_case.py`; classes `PascalCase`; functions/vars `snake_case`; constants `UPPER_SNAKE_CASE`.
- **Comments**: Follow `docs/comment-style.md` - semantic tags (`# *`, `# !`, `# ?`, `# todo`), use `&` instead of "and".
- **File headers**: Required format: `# src/path/filename.py` followed by brief description.
- **Formatters**: Prefer `black` and `ruff` locally (not enforced in repo).

## Folder Conventions

- **Source**: `src/` w/ packages `ai/`, `cli/`, `config/`, `core/`, `loom_io/`, `ui/`.
- **Docs**: `docs/` for architecture, contributing, instructions; enhanced help system in `ui/help/`.
- **Data**: Sample inputs in `data/`; generated artifacts in `output/` (git-ignored).
- **Config**: Local settings at `~/.loom/config.json`; environment variables via `.env`.

Appreciate your contributions!
