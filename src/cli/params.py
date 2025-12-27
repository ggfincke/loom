# src/cli/params.py
# CLI argument definitions & normalization helpers (renamed from args.py)

from __future__ import annotations

import typer
from ..core.constants import RiskLevel, ValidationPolicy


def _normalize_risk(value: str | None) -> RiskLevel:
    if value is None:
        return RiskLevel.MED
    v = value.strip().lower()
    mapping = {
        "low": RiskLevel.LOW,
        "med": RiskLevel.MED,
        "medium": RiskLevel.MED,
        "high": RiskLevel.HIGH,
        "strict": RiskLevel.STRICT,
    }
    try:
        return mapping[v]
    except KeyError:
        raise typer.BadParameter("Invalid risk. Choose: low|med|high|strict")


def _normalize_validation_policy(value: str | None) -> ValidationPolicy:
    if value is None:
        return ValidationPolicy.ASK
    v = value.strip().lower()
    mapping = {
        "ask": ValidationPolicy.ASK,
        "retry": ValidationPolicy.RETRY,
        "manual": ValidationPolicy.MANUAL,
        # aliases for soft/hard
        "fail": ValidationPolicy.FAIL_SOFT,
        "fail:soft": ValidationPolicy.FAIL_SOFT,
        "fail_soft": ValidationPolicy.FAIL_SOFT,
        "fail-soft": ValidationPolicy.FAIL_SOFT,
        "fail:hard": ValidationPolicy.FAIL_HARD,
        "fail_hard": ValidationPolicy.FAIL_HARD,
        "fail-hard": ValidationPolicy.FAIL_HARD,
    }
    try:
        return mapping[v]
    except KeyError:
        raise typer.BadParameter(
            "Invalid on-error policy. Choose: ask|retry|manual|fail|fail:soft|fail:hard"
        )


def ResumeArg() -> typer.Argument:
    return typer.Argument(
        None,
        help="Path to resume (.docx or .tex)",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    )


def JobArg() -> typer.Argument:
    return typer.Argument(
        None,
        help="Path to job description",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    )


def ModelOpt() -> typer.Option:
    return typer.Option(
        None,
        "--model",
        "-m",
        help="OpenAI model (see 'loom --help' for supported models); defaults to config",
    )


def RiskOpt() -> typer.Option:
    return typer.Option(
        None,
        "--risk",
        callback=lambda v: _normalize_risk(v),
        help="Risk level: low|med|high|strict",
    )


def OnErrorOpt() -> typer.Option:
    return typer.Option(
        None,
        "--on-error",
        callback=lambda v: _normalize_validation_policy(v),
        help="ask|retry|manual|fail|fail:soft|fail:hard",
    )


def ConfigKeyArg() -> typer.Argument:
    return typer.Argument(
        help="Configuration setting name",
    )


def ConfigValueArg() -> typer.Argument:
    return typer.Argument(
        help="New value to assign to the setting",
    )


def EditsJsonOpt() -> typer.Option:
    return typer.Option(
        None,
        "--edits-json",
        "-e",
        help="Path to edits.json (read/write); defaults to config edits_path",
        resolve_path=True,
    )


def SectionsPathOpt() -> typer.Option:
    return typer.Option(
        None,
        "--sections-path",
        "-s",
        help="Path to sections.json; defaults to config sections_path",
        resolve_path=True,
    )


def PlanOpt() -> typer.Option:
    return typer.Option(
        None,
        "--plan",
        help="Plan mode: no value=plan only, =N for max N steps",
    )


def PreserveFormattingOpt() -> typer.Option:
    return typer.Option(
        True,
        "--preserve-formatting/--no-preserve-formatting",
        help="Preserve original DOCX formatting (fonts, styles, etc.)",
        show_default=True,
    )


def PreserveModeOpt() -> typer.Option:
    return typer.Option(
        "in_place",
        "--preserve-mode",
        help=(
            "How to preserve formatting: 'in_place' (edit original, best preservation) or "
            "'rebuild' (create new doc, may lose some formatting)"
        ),
        show_default=True,
    )


def OutJsonOpt() -> typer.Option:
    return typer.Option(
        None,
        "--out-json",
        "-o",
        help="Where to write sections JSON; defaults to config sections_path",
        resolve_path=True,
    )


def OutputResumeOpt() -> typer.Option:
    return typer.Option(
        None,
        "--output-resume",
        "-r",
        help="Path to write tailored resume (.docx or .tex); defaults to <output_dir>/tailored_resume.docx",
        resolve_path=True,
    )


def AutoOpt() -> typer.Option:
    return typer.Option(
        False,
        "--auto",
        help="Apply all edits automatically without interactive review",
    )


def OutputEditsOpt() -> typer.Option:
    return typer.Option(
        None,
        "--output-edits",
        "-o",
        help="Path to write processed edits.json; defaults to input edits_json",
        resolve_path=True,
    )


def UserPromptOpt() -> typer.Option:
    return typer.Option(
        None,
        "--prompt",
        "-p",
        help="Custom instructions for the AI to prioritize during tailoring",
    )


def VerboseOpt() -> typer.Option:
    return typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging for debugging & troubleshooting",
    )


def LogFileOpt() -> typer.Option:
    return typer.Option(
        None,
        "--log-file",
        help="Write verbose logs to file (enables verbose mode automatically)",
        resolve_path=True,
    )


def NoCacheOpt() -> typer.Option:
    return typer.Option(
        False,
        "--no-cache",
        help="Bypass AI response cache for this invocation",
    )


def WatchOpt() -> typer.Option:
    return typer.Option(
        False,
        "--watch",
        "-w",
        help="Watch input files for changes & re-run automatically",
    )
