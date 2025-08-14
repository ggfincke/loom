# Contributing to Loom

Thanks for your interest in improving Loom! This guide outlines the workflow and expectations for contributions.

## Workflow

- Use Python 3.12 and follow PEP 8 with 4-space indents; add type hints in new/modified code.
- Keep `core/` pure (no I/O). CLI/UI lives under `cli/` and `ui/`. File/JSON ops under `loom_io/`.
- Small, focused changes only; avoid drive-by fixes unrelated to your PR.

## Setup

1. Create env: `conda create -n loom python=3.12 && conda activate loom`
2. Install deps: `pip install -r requirements.txt`
3. Install CLI (editable): `pip install -e .` (gives the `loom` command)
4. Configure `.env` with `OPENAI_API_KEY` (do not commit this)

## Smoke Tests

- Sectionize: `loom sectionize path/to/resume.docx --out-json sections.json`
- Tailor: `loom tailor job.txt path/to/resume.docx --sections-path sections.json --edits-json edits.json`

## Commits & PRs

- Conventional Commits: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`, etc.
- PR description should include: what/why, reproduction steps (commands), before/after behavior, and any config changes (`.env`, `~/.loom`).
- Update `README.md` or `docs/` when user-facing behavior changes; include sample CLI output when useful.

## Security & Configuration

- Never commit secrets. Keep `OPENAI_API_KEY` in `.env`.
- Settings persist at `~/.loom/config.json`. Prefer `settings_manager` for reads/writes; do not hard-code defaults.
- Validate paths and file types in `loom_io/` before processing.

## Style Notes

- Match existing naming: modules/files `snake_case.py`; classes `PascalCase`; functions/vars `snake_case`; constants `UPPER_SNAKE_CASE`.
- Prefer `black` and `ruff` locally (not enforced in repo).

## Folder Conventions

- Source under `src/`; docs under `docs/`; sample inputs in `data/`; generated artifacts in `output/` (git-ignored).

Appreciate your contributions!
