# src/ui/display/ats_report.py
# Rich console rendering for ATS compatibility reports

from __future__ import annotations

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ...core.ats_analyzer import ATSReport, Severity
from ...loom_io.console import console
from ..theming.theme_engine import (
    LoomColors,
    natural_gradient,
)


# get icon for severity level
def _severity_icon(severity: Severity) -> Text:
    icons = {
        Severity.CRITICAL: Text("X", style=LoomColors.ERROR),
        Severity.WARNING: Text("!", style=LoomColors.WARNING),
        Severity.INFO: Text("i", style=LoomColors.INFO),
    }
    return icons.get(severity, Text("?"))


# get styled label for severity level
def _severity_label(severity: Severity) -> Text:
    labels = {
        Severity.CRITICAL: Text("CRITICAL", style=f"bold {LoomColors.ERROR}"),
        Severity.WARNING: Text("WARNING", style=f"bold {LoomColors.WARNING}"),
        Severity.INFO: Text("INFO", style=f"bold {LoomColors.INFO}"),
    }
    return labels.get(severity, Text("UNKNOWN"))


# get color based on score value
def _score_color(score: int) -> str:
    if score >= 80:
        return LoomColors.SUCCESS_BRIGHT
    elif score >= 60:
        return LoomColors.WARNING
    else:
        return LoomColors.ERROR


# get descriptive label for score
def _score_label(score: int) -> str:
    if score >= 90:
        return "Excellent"
    elif score >= 80:
        return "Good"
    elif score >= 60:
        return "Needs Work"
    elif score >= 40:
        return "Poor"
    else:
        return "Critical Issues"


# render ATS compatibility report to console
def render_ats_report(report: ATSReport) -> None:
    # header panel w/ score
    score_color = _score_color(report.score)
    score_text = Text()
    score_text.append("Score: ", style="bold")
    score_text.append(f"{report.score}", style=f"bold {score_color}")
    score_text.append("/100 ", style="dim")
    score_text.append(f"({_score_label(report.score)})", style=score_color)

    # pass/fail indicator
    if report.passed:
        status = Text(" PASS ", style=f"bold white on {LoomColors.SUCCESS_BRIGHT}")
    else:
        status = Text(" NEEDS WORK ", style=f"bold white on {LoomColors.ERROR}")

    header_content = Text()
    header_content.append_text(score_text)
    header_content.append("  ")
    header_content.append_text(status)

    # summary counts
    summary = Text("\n")
    if report.critical_count > 0:
        summary.append(f"{report.critical_count} critical", style=LoomColors.ERROR)
        summary.append("  ")
    if report.warning_count > 0:
        summary.append(f"{report.warning_count} warning", style=LoomColors.WARNING)
        summary.append("  ")
    if report.info_count > 0:
        summary.append(f"{report.info_count} info", style=LoomColors.INFO)

    header_content.append_text(summary)

    header_panel = Panel(
        header_content,
        title=natural_gradient("ATS Compatibility Report"),
        border_style=LoomColors.ACCENT_SECONDARY,
        padding=(0, 1),
    )

    console.print(header_panel)
    console.print()

    # issues by severity
    for severity in [Severity.CRITICAL, Severity.WARNING, Severity.INFO]:
        issues = report.issues_by_severity(severity)
        if not issues:
            continue

        # section header
        label = _severity_label(severity)
        count = Text(f" ({len(issues)})", style="dim")
        console.print(Text.assemble(label, count))

        # issue table
        table = Table(show_header=False, box=None, padding=(0, 1, 0, 2))
        table.add_column("icon", width=3)
        table.add_column("description")

        for issue in issues:
            icon = _severity_icon(severity)

            # build description w/ location & suggestion
            desc = Text()
            desc.append(issue.description)

            if issue.location:
                desc.append(f" [{issue.location}]", style="dim")

            if issue.suggestion:
                desc.append("\n    -> ", style=LoomColors.ACCENT_SECONDARY)
                desc.append(issue.suggestion, style="dim italic")

            table.add_row(icon, desc)

        console.print(table)
        console.print()

    # recommendations
    if report.recommendations:
        console.print(
            Text("Recommendations", style=f"bold {LoomColors.ACCENT_PRIMARY}")
        )
        for rec in report.recommendations:
            bullet = Text("  * ", style=LoomColors.ACCENT_SECONDARY)
            console.print(Text.assemble(bullet, Text(rec, style="dim")))
        console.print()


# render brief ATS summary after analysis
def render_ats_summary(report: ATSReport, json_path: str | None = None) -> None:
    score_color = _score_color(report.score)

    # one-liner summary
    summary = Text()
    summary.append("ATS Score: ", style="bold")
    summary.append(f"{report.score}/100", style=f"bold {score_color}")

    if report.critical_count > 0:
        summary.append(
            f" ({report.critical_count} critical issues)", style=LoomColors.ERROR
        )
    elif report.warning_count > 0:
        summary.append(f" ({report.warning_count} warnings)", style=LoomColors.WARNING)
    else:
        summary.append(" (no issues)", style=LoomColors.SUCCESS_BRIGHT)

    console.print(summary)

    if json_path:
        from ..theming.theme_engine import styled_arrow

        arrow = styled_arrow()
        console.print(Text.assemble("  Report ", arrow, f" {json_path}"), style="dim")
