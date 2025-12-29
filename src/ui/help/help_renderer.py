# src/ui/help/help_renderer.py
# Custom help renderer that bypasses Typer's default help w/ Rich panels & theme integration

from __future__ import annotations

import typer
from ..core.rich_components import Panel, Table, Text, Group, themed_panel, themed_table
from typing import Any

from ...loom_io.console import console
from ..theming.theme_engine import accent_gradient, LoomColors
from ..display.ascii_art import show_loom_art
from .help_data import get_command_help, get_option_help, get_command_metadata
from .option_introspection import introspect_command_options, IntrospectedOption


# * Custom help renderer for branded CLI help screens w/ Rich styling & theme integration
class HelpRenderer:
    # init
    def __init__(self):
        pass

    def _create_styled_panel(
        self, content, title: str, padding: tuple[int, int] = (0, 1)
    ) -> Panel:
        # create consistently styled panel for help output
        return themed_panel(content, title=title, padding=padding)

    def _create_commands_table(self) -> Table:
        # create consistently styled commands table
        table = themed_table()
        table.add_column("Command", style=f"bold {LoomColors.ACCENT_PRIMARY}", width=12)
        table.add_column("Description", style="white")
        return table

    def _create_options_table(self, show_default: bool = True) -> Table:
        # create consistently styled options table
        table = themed_table(show_header=True)
        table.title = "Options"
        table.title_style = f"bold {LoomColors.ACCENT_PRIMARY}"
        table.padding = (0, 1)
        table.add_column("Option", style=f"bold {LoomColors.ACCENT_PRIMARY}", width=30)
        table.add_column("Type", style=LoomColors.ACCENT_SECONDARY, width=10)
        table.add_column("Description", style="white")
        if show_default:
            table.add_column("Default", style="dim")
        return table

    # * Render main application help screen w/ banner & command overview
    def render_main_help(self, app: typer.Typer) -> None:
        console.print()
        show_loom_art()
        console.print()

        # usage section
        usage_panel = self._create_styled_panel(
            "[bold white]loom[/] [dim]<command>[/] [dim]<options>[/]",
            "Usage",
        )
        console.print(usage_panel)
        console.print()

        # commands organized by category
        self._render_commands_table(app)
        console.print()

        # help note
        help_note = f"[{LoomColors.ACCENT_PRIMARY}]Run 'loom <command> -h' (or --help) for detailed options[/]"
        console.print(help_note)
        console.print()

        # examples section
        self._render_examples()
        console.print()

        # global options
        self._render_global_options()

    # * Render help for specific command w/ detailed options & examples
    def render_command_help(self, command_name: str, command: Any = None) -> None:
        console.print()

        # try to get command help from metadata system first, fall back to templates
        cmd_help = get_command_metadata(command_name)
        if not cmd_help:
            cmd_help = get_command_help(command_name)

        if not cmd_help:
            console.print(f"[red]No help available for command: {command_name}[/]")
            return

        # command header
        header = accent_gradient(f"loom {command_name}")
        console.print(header)
        console.print(f"[dim]{cmd_help.description}[/]")

        if cmd_help.long_description:
            console.print()
            console.print(cmd_help.long_description)
        console.print()

        # usage
        usage_text = f"[bold white]loom {command_name}[/] [dim]<options>[/]"
        usage_panel = self._create_styled_panel(usage_text, "Usage")
        console.print(usage_panel)
        console.print()

        # detailed options table - try introspection first, fall back to template metadata
        self._render_command_options_detailed(command_name, command)
        console.print()

        # command-specific examples from templates
        if cmd_help.examples:
            self._render_command_examples_from_template(cmd_help.examples)
            console.print()

        # see also section
        if cmd_help.see_also:
            self._render_see_also(cmd_help.see_also)

    # render commands organized in separate visual sections
    def _render_commands_table(self, app: typer.Typer) -> None:
        # group commands by workflow
        core_commands = [
            ("sectionize", "Parse resume into structured sections"),
            ("tailor", "Complete end-to-end resume tailoring"),
        ]

        utility_commands = [
            ("ats", "Check resume for ATS compatibility"),
            ("plan", "Generate edits w/ planning workflow"),
            ("config", "Manage settings & configuration"),
            ("templates", "List available templates"),
            ("init", "Initialize from a template"),
        ]

        # core workflow section
        core_table = self._create_commands_table()
        for cmd, desc in core_commands:
            core_table.add_row(cmd, desc)

        core_panel = self._create_styled_panel(
            core_table, f"[bold {LoomColors.ACCENT_LIGHT}]Core Workflow[/]"
        )
        console.print(core_panel)
        console.print()

        # utilities section
        utility_table = self._create_commands_table()
        for cmd, desc in utility_commands:
            utility_table.add_row(cmd, desc)

        utility_panel = self._create_styled_panel(
            utility_table, f"[bold {LoomColors.ACCENT_LIGHT}]Utilities[/]"
        )
        console.print(utility_panel)

    # render common usage examples
    def _render_examples(self) -> None:
        examples_content = Group(
            Text(
                "# Quick tailoring workflow", style=f"dim {LoomColors.ACCENT_SECONDARY}"
            ),
            Text("loom tailor job_posting.txt my_resume.docx", style="white"),
            Text(""),
            Text("# Step-by-step workflow", style=f"dim {LoomColors.ACCENT_SECONDARY}"),
            Text("loom sectionize resume.docx --out-json sections.json", style="white"),
            Text("loom tailor job.txt resume.docx --edits-only", style="white"),
            Text(
                "loom tailor resume.docx --apply --output-resume tailored_resume.docx",
                style="white",
            ),
            Text(
                "loom tailor job.txt resume.tex --output-resume tailored_resume.tex",
                style="white",
            ),
            Text(""),
            Text("# Templates", style=f"dim {LoomColors.ACCENT_SECONDARY}"),
            Text("loom templates  # List bundled LaTeX templates", style="white"),
            Text("loom init --template swe-latex --output my-resume", style="white"),
            Text(""),
            Text(
                "# Configure defaults to simplify commands",
                style=f"dim {LoomColors.ACCENT_SECONDARY}",
            ),
            Text("loom config set data_dir /path/to/job_applications", style="white"),
            Text("loom config themes  # Interactive theme selector", style="white"),
        )

        examples_panel = self._create_styled_panel(
            examples_content, "Examples", padding=(1, 2)
        )
        console.print(examples_panel)

    # render global options available to all commands
    def _render_global_options(self) -> None:
        options_content = Group(
            Text("--help           Show this help message", style="white"),
            Text("--help-raw       Show raw Typer help output", style="white"),
            Text("--install-completion    Install shell completion", style="white"),
            Text("--show-completion       Show completion script", style="white"),
        )

        options_panel = self._create_styled_panel(
            options_content, "Global Options", padding=(0, 2)
        )
        console.print(options_panel)

    # render options table for specific command
    def _render_command_options(self, command: Any) -> None:
        if not hasattr(command, "params") or not command.params:
            console.print("[dim]No options available for this command.[/]")
            return

        table = themed_table(show_header=True)
        table.title = "Options"
        table.title_style = f"bold {LoomColors.ACCENT_PRIMARY}"
        table.padding = (0, 1)
        table.add_column("Option", style=f"bold {LoomColors.ACCENT_PRIMARY}", width=20)
        table.add_column("Type", style=LoomColors.ACCENT_SECONDARY, width=10)
        table.add_column("Description", style="white")

        for param in command.params:
            # extract option names
            option_names = []
            if hasattr(param, "opts"):
                option_names = param.opts
            elif hasattr(param, "name"):
                option_names = [f"--{param.name.replace('_', '-')}"]

            option_str = ", ".join(option_names) if option_names else param.name

            # get type info
            type_str = "str"
            if hasattr(param, "type"):
                if param.type == bool:
                    type_str = "flag"
                elif hasattr(param.type, "__name__"):
                    type_str = param.type.__name__

            # get description
            description = getattr(param, "help", "") or "No description available"

            table.add_row(option_str, type_str, description)

        console.print(table)

    # render detailed options table for command - uses introspection w/ fallback to metadata
    def _render_command_options_detailed(
        self, command_name: str, command: Any = None
    ) -> None:
        # try introspection first if command object is available
        if command is not None:
            introspected = introspect_command_options(command)
            if introspected:
                self._render_introspected_options(introspected)
                return

        # fall back to hardcoded options_map
        self._render_options_from_metadata(command_name)

    def _render_introspected_options(self, options: list[IntrospectedOption]) -> None:
        # render options table from introspected data
        table = self._create_options_table(show_default=True)

        for opt in options:
            # try to enhance w/ help_data if available
            help_key = opt.name.lstrip("-").replace("-", "_")
            enhanced = get_option_help(help_key)

            # compose option name including aliases
            name_display = opt.name
            if opt.aliases:
                name_display += f", {', '.join(opt.aliases)}"
            if opt.required:
                name_display += " *"

            # use enhanced description if available, else introspected
            description = enhanced.description if enhanced else opt.description
            if opt.required:
                description += " (required)"

            # use enhanced default if available, else introspected
            default = (enhanced.default if enhanced else opt.default) or ""

            # use enhanced type if available
            type_name = enhanced.type_name if enhanced else opt.type_name

            table.add_row(name_display, type_name, description, default)

        console.print(table)

    def _render_options_from_metadata(self, command_name: str) -> None:
        # render options table from hardcoded metadata (fallback)
        # map commands to option keys defined in help_data.OPTION_HELP
        options_map = {
            "sectionize": [
                ("resume", True),
                ("out_json", False),
                ("model", False),
            ],
            "generate": [
                ("job", True),
                ("resume", True),
                ("edits_json", False),
                ("sections_path", False),
                ("model", False),
                ("risk", False),
                ("on_error", False),
            ],
            "apply": [
                ("resume", True),
                ("edits_json", False),
                ("output_resume", False),
                ("preserve_formatting", False),
                ("preserve_mode", False),
                ("risk", False),
                ("on_error", False),
            ],
            "tailor": [
                ("job", True),
                ("resume", True),
                ("output_resume", False),
                ("sections_path", False),
                ("model", False),
                ("edits_json", False),
                ("preserve_formatting", False),
                ("preserve_mode", False),
                ("risk", False),
                ("on_error", False),
                ("edits_only", False),
                ("apply", False),
            ],
            "plan": [
                ("job", True),
                ("resume", True),
                ("edits_json", False),
                ("sections_path", False),
                ("model", False),
                ("risk", False),
                ("on_error", False),
                ("plan", False),
            ],
            "init": [
                ("template", True),
                ("output", False),
            ],
            "templates": [],
            "config": [],
        }

        table = self._create_options_table(show_default=True)

        entries = options_map.get(command_name, [])
        if not entries:
            console.print("[dim]No options available for this command.[/]")
            return

        for key, required in entries:
            meta = get_option_help(key)
            if not meta:
                # fallback minimal row
                table.add_row(key + (" *" if required else ""), "", "", "")
                continue
            # compose option name incl aliases
            name = meta.name
            if meta.aliases:
                alias_str = ", ".join(meta.aliases)
                name = f"{name}, {alias_str}"
            if required:
                name = f"{name} *"
            # description
            desc = meta.description + (" (required)" if required else "")
            # default
            default = meta.default or ""
            table.add_row(name, meta.type_name, desc, default)

        console.print(table)

    # render examples from template data
    def _render_command_examples_from_template(self, examples: list[str]) -> None:
        examples_content = Group(
            *[Text(example, style="white") for example in examples]
        )

        examples_panel = self._create_styled_panel(
            examples_content, "Examples", padding=(1, 2)
        )
        console.print(examples_panel)

    # render see also section
    def _render_see_also(self, see_also: list[str]) -> None:
        see_also_text = ", ".join(
            [f"[{LoomColors.ACCENT_PRIMARY}]loom {cmd}[/]" for cmd in see_also]
        )

        see_also_panel = self._create_styled_panel(
            see_also_text, "See Also", padding=(0, 2)
        )
        console.print(see_also_panel)
