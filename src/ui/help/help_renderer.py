# src/ui/help/help_renderer.py
# Custom help renderer that bypasses Typer's default help w/ Rich panels & theme integration

from __future__ import annotations

import typer
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.console import Group
from typing import Any

from ...loom_io.console import console
from ..colors import accent_gradient, get_active_theme
from ..ascii_art import show_loom_art
from .help_templates import get_command_help


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
        
        # examples section
        self._render_examples()
        console.print()
        
        # global options
        self._render_global_options()
        
    # * render help for specific command w/ detailed options & examples
    def render_command_help(self, command_name: str, command: Any = None) -> None:
        console.print()
        
        # get command help from templates
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
        
        # options table (simplified for now, since we don't have easy access to typer command objects)
        self._render_command_options_simplified(command_name)
        console.print()
        
        # command-specific examples from templates
        if cmd_help.examples:
            self._render_command_examples_from_template(cmd_help.examples)
            console.print()
        
        # see also section
        if cmd_help.see_also:
            self._render_see_also(cmd_help.see_also)
        
    # render commands organized in styled table
    def _render_commands_table(self, app: typer.Typer) -> None:
        table = Table(
            title="Commands",
            title_style=f"bold {self.theme_colors[0]}",
            border_style=self.theme_colors[2],
            header_style=f"bold {self.theme_colors[1]}",
            show_header=False,
            padding=(0, 1, 0, 0)
        )
        table.add_column("Command", style=f"bold {self.theme_colors[0]}", width=12)
        table.add_column("Description", style="white")
        
        # group commands by workflow
        core_commands = [
            ("sectionize", "Parse resume into structured sections"),
            ("tailor", "Complete end-to-end resume tailoring"),
            ("generate", "Generate edits.json for job requirements"),
            ("apply", "Apply edits to resume document"),
        ]
        
        utility_commands = [
            ("plan", "Generate edits w/ planning workflow"),
            ("config", "Manage settings & configuration"),
        ]
        
        # core workflow section
        table.add_row(
            f"[{self.theme_colors[1]}]Core Workflow[/]",
            "",
        )
        for cmd, desc in core_commands:
            table.add_row(f"  {cmd}", desc)
        
        # spacer
        table.add_row("", "") 
        
        # utilities section  
        table.add_row(
            f"[{self.theme_colors[1]}]Utilities[/]",
            "",
        )
        for cmd, desc in utility_commands:
            table.add_row(f"  {cmd}", desc)
            
        console.print(table)
    
    # render common usage examples
    def _render_examples(self) -> None:
        examples_content = Group(
            Text("# Quick tailoring workflow", style=f"dim {self.theme_colors[2]}"),
            Text("loom tailor job_posting.txt my_resume.docx", style="white"),
            Text(""),
            Text("# Step-by-step workflow", style=f"dim {self.theme_colors[2]}"),
            Text("loom sectionize resume.docx --out-json sections.json", style="white"),
            Text("loom generate job.txt resume.docx --out-json edits.json", style="white"),
            Text("loom apply edits.json resume.docx --output tailored_resume.docx", style="white"),
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
    
    # render simplified options table for command
    def _render_command_options_simplified(self, command_name: str) -> None:
        # define common options per command
        options_map = {
            "sectionize": [
                ("resume_path", "PATH", "Path to resume DOCX file", True),
                ("--out-json", "PATH", "Output path for sections JSON", False),
                ("--model", "TEXT", "OpenAI model to use", False),
            ],
            "generate": [
                ("job_path", "PATH", "Path to job description text file", True),
                ("resume_path", "PATH", "Path to resume DOCX file", True),
                ("--out-json", "PATH", "Output path for edits JSON", False),
                ("--sections-path", "PATH", "Path to sections JSON file", False),
                ("--model", "TEXT", "OpenAI model to use", False),
            ],
            "apply": [
                ("edits_path", "PATH", "Path to edits JSON file", True),
                ("resume_path", "PATH", "Path to resume DOCX file", True),
                ("--output", "PATH", "Output path for tailored resume", False),
                ("--preserve-formatting/--no-preserve-formatting", "FLAG", "Preserve document formatting", False),
                ("--preserve-mode", "CHOICE", "Formatting preservation mode", False),
            ],
            "tailor": [
                ("job_path", "PATH", "Path to job description text file", True),
                ("resume_path", "PATH", "Path to resume DOCX file", True),
                ("--output", "PATH", "Output path for tailored resume", False),
                ("--sections-path", "PATH", "Path to sections JSON file", False),
                ("--model", "TEXT", "OpenAI model to use", False),
                ("--preserve-formatting/--no-preserve-formatting", "FLAG", "Preserve document formatting", False),
                ("--preserve-mode", "CHOICE", "Formatting preservation mode", False),
            ],
            "plan": [
                ("job_path", "PATH", "Path to job description text file", True),
                ("resume_path", "PATH", "Path to resume DOCX file", True),
                ("--out-json", "PATH", "Output path for edits JSON", False),
                ("--sections-path", "PATH", "Path to sections JSON file", False),
                ("--model", "TEXT", "OpenAI model to use", False),
            ],
            "config": [
                ("key", "TEXT", "Setting key to get/set", False),
                ("value", "TEXT", "Setting value (for set command)", False),
                ("--help", "FLAG", "Show command help", False),
            ],
        }
        
        if command_name not in options_map:
            console.print("[dim]No options available for this command.[/]")
            return
            
        table = Table(
            title="Options",
            title_style=f"bold {self.theme_colors[0]}",
            border_style=self.theme_colors[2],
            show_header=True,
            padding=(0, 1)
        )
        table.add_column("Option", style=f"bold {self.theme_colors[0]}", width=25)
        table.add_column("Type", style=self.theme_colors[2], width=8)
        table.add_column("Description", style="white")
        
        for option, type_name, description, required in options_map[command_name]:
            if required:
                option = f"{option} *"
                description = f"{description} (required)"
            table.add_row(option, type_name, description)
        
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