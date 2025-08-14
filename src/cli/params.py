# src/cli/params.py
# CLI argument definitions and normalization helpers (renamed from args.py)

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


def ResumeArg():
    return typer.Argument(
        None,
        help="Path to resume .docx",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    )


def JobArg():
    return typer.Argument(
        None,
        help="Path to job description",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    )


def ModelOpt():
    return typer.Option(
        None,
        "--model",
        "-m",
        help="OpenAI model name",
    )


def RiskOpt():
    return typer.Option(
        None,
        "--risk",
        callback=lambda v: _normalize_risk(v),
        help="Risk level: low|med|high|strict",
    )


def OnErrorOpt():
    return typer.Option(
        None,
        "--on-error",
        callback=lambda v: _normalize_validation_policy(v),
        help="ask|retry|manual|fail|fail:soft|fail:hard",
    )


def ConfigKeyArg():
    return typer.Argument(
        help="Configuration setting name",
    )


def ConfigValueArg():
    return typer.Argument(
        help="New value to assign to the setting",
    )


def EditsJsonOpt():
    return typer.Option(
        None,
        "--edits-json",
        "-e",
        help="Path to edits.json (read or write depending on command)",
        resolve_path=True,
    )


def SectionsPathOpt():
    return typer.Option(
        None,
        "--sections-path",
        "-s",
        help="Optional sections.json path",
        resolve_path=True,
    )


def PlanOpt():
    return typer.Option(
        None,
        "--plan",
        help="Plan mode: no value=plan only, =N for max N steps",
    )


def PreserveFormattingOpt():
    return typer.Option(
        True,
        "--preserve-formatting/--no-preserve-formatting",
        help="Preserve original DOCX formatting (fonts, styles, etc.)",
        show_default=True,
    )


def PreserveModeOpt():
    return typer.Option(
        "in_place",
        "--preserve-mode",
        help=(
            "How to preserve formatting: 'in_place' (edit original, best preservation) or "
            "'rebuild' (create new doc, may lose some formatting)"
        ),
        show_default=True,
    )


def OutJsonOpt():
    return typer.Option(
        None,
        "--out-json",
        "-o",
        help="Where to write the sections JSON",
        resolve_path=True,
    )


def OutputResumeOpt():
    return typer.Option(
        None,
        "--output-resume",
        "-r",
        help="Path to write the tailored resume .docx",
        resolve_path=True,
    )

