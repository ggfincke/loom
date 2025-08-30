# src/ui/help/help_renderer.py
# Custom help renderer that bypasses Typer's default help w/ Rich panels & theme integration

from __future__ import annotations

import typer
from ..core.rich_components import Panel, Table, Text, Group
from typing import Any

from ...loom_io.console import console
from ..theming.theme_engine import accent_gradient, get_active_theme
from ..display.ascii_art import show_loom_art
from .help_data import get_command_help, get_option_help, get_command_metadata


# * Custom help renderer for branded CLI help screens w/ Rich styling & theme integration
class HelpRenderer:
    # init
    def __init__(self):
        self.theme_colors = get_active_theme()
    
    # * render main application help screen w/ banner & command overview
    def render_main_help(self, app: typer.Typer) -> None:
        console.print()
        show_loom_art()
        console.print()
        
        # usage section
        usage_panel = Panel(
            "[bold white]loom[/] [dim]<command>[/] [dim]<options>[/]",
            title="[bold]Usage[/]",
            title_align="left",
            border_style=self.theme_colors[2],
            padding=(0, 1)
        )
        console.print(usage_panel)
        console.print()
        
        # commands organized by category
        self._render_commands_table(app)
        console.print()
        
        # help note
        help_note = f"[{self.theme_colors[0]}]Run 'loom <command> -h' (or --help) for detailed options[/]"
        console.print(help_note)
        console.print()
        
        # examples section
        self._render_examples()
        console.print()
        
        # global options
        self._render_global_options()
        
    # * render help for specific command w/ detailed options & examples
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
        usage_panel = Panel(
            usage_text,
            title="[bold]Usage[/]",
            title_align="left", 
            border_style=self.theme_colors[2],
            padding=(0, 1)
        )
        console.print(usage_panel)
        console.print()
        
        # detailed options table using our template metadata
        self._render_command_options_detailed(command_name)
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
            ("plan", "Generate edits w/ planning workflow"),
            ("config", "Manage settings & configuration"),
        ]
        
        # core workflow section
        core_table = Table(
            border_style=self.theme_colors[2],
            show_header=False,
            padding=(0, 1, 0, 0),
            box=None
        )
        core_table.add_column("Command", style=f"bold {self.theme_colors[0]}", width=12)
        core_table.add_column("Description", style="white")
        
        for cmd, desc in core_commands:
            core_table.add_row(cmd, desc)
        
        core_panel = Panel(
            core_table,
            title=f"[bold {self.theme_colors[1]}]Core Workflow[/]",
            title_align="left",
            border_style=self.theme_colors[2],
            padding=(0, 1)
        )
        console.print(core_panel)
        console.print()
        
        # utilities section
        utility_table = Table(
            border_style=self.theme_colors[2],
            show_header=False,
            padding=(0, 1, 0, 0),
            box=None
        )
        utility_table.add_column("Command", style=f"bold {self.theme_colors[0]}", width=12)
        utility_table.add_column("Description", style="white")
        
        for cmd, desc in utility_commands:
            utility_table.add_row(cmd, desc)
        
        utility_panel = Panel(
            utility_table,
            title=f"[bold {self.theme_colors[1]}]Utilities[/]",
            title_align="left",
            border_style=self.theme_colors[2],
            padding=(0, 1)
        )
        console.print(utility_panel)
    
    # render common usage examples
    def _render_examples(self) -> None:
        examples_content = Group(
            Text("# Quick tailoring workflow", style=f"dim {self.theme_colors[2]}"),
            Text("loom tailor job_posting.txt my_resume.docx", style="white"),
            Text(""),
            Text("# Step-by-step workflow", style=f"dim {self.theme_colors[2]}"),
            Text("loom sectionize resume.docx --out-json sections.json", style="white"),
            Text("loom tailor job.txt resume.docx --edits-only", style="white"),
            Text("loom tailor resume.docx --apply --output-resume tailored_resume.docx", style="white"),
            Text("loom tailor job.txt resume.tex --output-resume tailored_resume.tex", style="white"),
            Text(""),
            Text("# Configure defaults to simplify commands", style=f"dim {self.theme_colors[2]}"),
            Text("loom config set data_dir /path/to/job_applications", style="white"),
            Text("loom config themes  # Interactive theme selector", style="white"),
        )
        
        examples_panel = Panel(
            examples_content,
            title="[bold]Examples[/]",
            title_align="left",
            border_style=self.theme_colors[2],
            padding=(1, 2)
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
        
        options_panel = Panel(
            options_content,
            title="[bold]Global Options[/]",
            title_align="left",
            border_style=self.theme_colors[2],
            padding=(0, 2)
        )
        console.print(options_panel)
    
    # render options table for specific command 
    def _render_command_options(self, command: Any) -> None:
        if not hasattr(command, 'params') or not command.params:
            console.print("[dim]No options available for this command.[/]")
            return
            
        table = Table(
            title="Options",
            title_style=f"bold {self.theme_colors[0]}",
            border_style=self.theme_colors[2],
            show_header=True,
            padding=(0, 1)
        )
        table.add_column("Option", style=f"bold {self.theme_colors[0]}", width=20)
        table.add_column("Type", style=self.theme_colors[2], width=10)
        table.add_column("Description", style="white")
        
        for param in command.params:
            # extract option names
            option_names = []
            if hasattr(param, 'opts'):
                option_names = param.opts
            elif hasattr(param, 'name'):
                option_names = [f"--{param.name.replace('_', '-')}"]
            
            option_str = ", ".join(option_names) if option_names else param.name
            
            # get type info
            type_str = "str"
            if hasattr(param, 'type'):
                if param.type == bool:
                    type_str = "flag"
                elif hasattr(param.type, '__name__'):
                    type_str = param.type.__name__
            
            # get description
            description = getattr(param, 'help', '') or 'No description available'
            
            table.add_row(option_str, type_str, description)
        
        console.print(table)
    
    # render detailed options table for command from template metadata
    def _render_command_options_detailed(self, command_name: str) -> None:
        # map commands to option keys defined in help_templates.OPTION_HELP
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
            "config": [],
        }

        table = Table(
            title="Options",
            title_style=f"bold {self.theme_colors[0]}",
            border_style=self.theme_colors[2],
            show_header=True,
            padding=(0, 1)
        )
        table.add_column("Option", style=f"bold {self.theme_colors[0]}", width=30)
        table.add_column("Type", style=self.theme_colors[2], width=10)
        table.add_column("Description", style="white")
        table.add_column("Default", style="dim")

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
        
        examples_panel = Panel(
            examples_content,
            title="[bold]Examples[/]",
            title_align="left",
            border_style=self.theme_colors[2],
            padding=(1, 2)
        )
        console.print(examples_panel)
    
    # render see also section
    def _render_see_also(self, see_also: list[str]) -> None:
        see_also_text = ", ".join([f"[{self.theme_colors[0]}]loom {cmd}[/]" for cmd in see_also])
        
        see_also_panel = Panel(
            see_also_text,
            title="[bold]See Also[/]",
            title_align="left",
            border_style=self.theme_colors[2],
            padding=(0, 2)
        )
        console.print(see_also_panel)
