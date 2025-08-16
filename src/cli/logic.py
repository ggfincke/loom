# src/cli/logic.py
# CLI-layer logic wrappers and argument resolution

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from ..config.settings import LoomSettings
from ..loom_io.types import Lines
from ..core.constants import RiskLevel, ValidationPolicy
from ..core.pipeline import (
    generate_edits,
    generate_corrected_edits,
    apply_edits,
)
from ..core.validation import validate_edits
from ..core.exceptions import EditError
from ..core.validation import handle_validation_error


def _resolve(provided_value, settings_default):
    return settings_default if provided_value is None else provided_value


class OptionsResolved(TypedDict):
    risk: RiskLevel
    on_error: ValidationPolicy


# * Resolve CLI arguments using settings defaults when values are not provided
class ArgResolver:

    def __init__(self, settings: LoomSettings):
        self.settings = settings

    def resolve_common(self, **kwargs):
        return {
            "resume": _resolve(kwargs.get("resume"), self.settings.resume_path),
            "job": _resolve(kwargs.get("job"), self.settings.job_path),
            "model": _resolve(kwargs.get("model"), self.settings.model),
            "sections_path": _resolve(
                kwargs.get("sections_path"), self.settings.sections_path
            ),
            "edits_json": _resolve(
                kwargs.get("edits_json"), self.settings.edits_path
            ),
            "out_json": _resolve(
                kwargs.get("out_json"), self.settings.sections_path
            ),
        }

    def resolve_paths(self, **kwargs):
        return {
            "output_resume": _resolve(
                kwargs.get("output_resume"),
                Path(self.settings.output_dir) / "tailored_resume.docx",
            ),
        }

    def resolve_options(self, **kwargs) -> OptionsResolved:
        return {
            "risk": _resolve(kwargs.get("risk"), RiskLevel.MED),
            "on_error": _resolve(kwargs.get("on_error"), ValidationPolicy.ASK),
        }


# * Generate & validate edits; persist intermediate edits to disk for manual flows
def generate_edits_core(
    settings: LoomSettings,
    resume_lines: Lines,
    job_text: str,
    sections_json: str | None,
    model: str,
    risk: RiskLevel,
    policy: ValidationPolicy,
    ui,
) -> dict:
    # create initial edits using AI
    edits = generate_edits(
        resume_lines=resume_lines, job_text=job_text, sections_json=sections_json, model=model
    )

    # persist edits immediately for manual editing
    settings.loom_dir.mkdir(exist_ok=True)
    settings.edits_path.write_text(__import__("json").dumps(edits, indent=2), encoding="utf-8")

    # validate using updatable closure
    current_edits = [edits]

    def validate_current():
        return (
            validate_edits(current_edits[0], resume_lines, risk)
            if current_edits[0] is not None
            else ["Edits not initialized"]
        )

    def edit_edits_and_update(validation_warnings):
        # load current edits from disk
        if settings.edits_path.exists():
            current_edits_json = settings.edits_path.read_text(encoding="utf-8")
        else:
            raise EditError("No existing edits file found for correction")

        # generate corrected edits via pipeline
        new_edits = generate_corrected_edits(
            current_edits_json,
            resume_lines,
            job_text,
            sections_json,
            model,
            validation_warnings,
        )
        # update current edits for validation
        current_edits[0] = new_edits
        return new_edits

    def reload_from_disk(data):
        current_edits[0] = data

    # perform validation
    result = handle_validation_error(
        settings,
        validate_fn=validate_current,
        policy=policy,
        edit_fn=edit_edits_and_update,
        reload_fn=reload_from_disk,
        ui=ui,
    )

    # handle regeneration result if present
    if isinstance(result, dict):
        edits = result
    elif edits is None:
        raise EditError("Failed to generate valid edits")

    return current_edits[0]


# * Validate & apply edits to resume lines, returning new lines
def apply_edits_core(
    settings: LoomSettings,
    resume_lines: Lines,
    edits: dict,
    risk: RiskLevel,
    policy: ValidationPolicy,
    ui,
) -> Lines:
    # use mutable container for reload support
    current = [edits]

    def validate_current():
        return validate_edits(current[0], resume_lines, risk)

    def reload_from_disk(data):
        current[0] = data

    # validate before applying edits
    handle_validation_error(
        settings,
        validate_fn=validate_current,
        policy=policy,
        reload_fn=reload_from_disk,
        ui=ui,
    )

    # execute edit application
    return apply_edits(resume_lines, current[0])
