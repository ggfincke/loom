# src/cli/args.py
# CLI argument definitions

import typer

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
        help="Risk level: low|med|high|strict",
    )

def OnErrorOpt():
    def _norm(v: str | None) -> str | None:
        return v.strip().lower() if isinstance(v, str) else v
    return typer.Option(
        None,
        "--on-error",
        callback=lambda v: _norm(v),
        help="ask|fail|fail:soft|fail:hard|manual|retry",
    )

def EditsArg():
    return typer.Argument(
        None,
        help="Path to edits JSON file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    )

def OutputArg():
    return typer.Argument(
        help="Output path for tailored resume .docx",
        resolve_path=True,
    )

def ConfigKeyArg():
    return typer.Argument(
        help="Configuration setting name",
    )

def ConfigValueArg():
    return typer.Argument(
        help="New value to assign to the setting",
    )

def OutOpt():
    return typer.Option(
        None,
        "--out",
        "-o",
        help="Output path (infer type by extension: .docx/.json)",
        resolve_path=True,
    )

def EditsJsonOpt():
    return typer.Option(
        None,
        "--edits-json",
        help="Path to write edits JSON",
        resolve_path=True,
    )

def ResumeDocxOpt():
    return typer.Option(
        None,
        "--resume-docx",
        help="Path to write tailored DOCX",
        resolve_path=True,
    )

def NoEditsJsonOpt():
    return typer.Option(
        False,
        "--no-edits-json",
        help="Skip writing edits JSON",
    )

def NoResumeDocxOpt():
    return typer.Option(
        False,
        "--no-resume-docx",
        help="Skip writing tailored DOCX",
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

def OutputDocxArg():
    return typer.Argument(
        None,
        help="Output path for tailored resume .docx",
        resolve_path=True,
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
        help="How to preserve formatting: 'in_place' (edit original, best preservation) or 'rebuild' (create new doc, may lose some formatting)",
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
        "--output-resume", "-r",
        help="Path to write the tailored resume .docx",
        resolve_path=True,
    )