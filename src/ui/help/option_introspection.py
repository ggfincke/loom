# src/ui/help/option_introspection.py
# Typer command introspection utilities for dynamic option discovery

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class IntrospectedOption:

    name: str
    aliases: list[str]
    type_name: str
    description: str
    default: str | None
    required: bool


# extract option metadata from Typer command via introspection; returns list of IntrospectedOption w/ metadata for each parameter
def introspect_command_options(command: Any) -> list[IntrospectedOption]:
    if not hasattr(command, "params") or not command.params:
        return []

    options = []
    for param in command.params:
        # skip help flag (handled separately)
        if hasattr(param, "opts") and "--help" in param.opts:
            continue

        # extract option names and aliases
        if hasattr(param, "opts") and param.opts:
            primary = param.opts[0]
            aliases = list(param.opts[1:]) if len(param.opts) > 1 else []
        elif hasattr(param, "name"):
            primary = f"--{param.name.replace('_', '-')}"
            aliases = []
        else:
            continue

        # determine type
        type_name = _get_type_name(param)

        # get description
        description = getattr(param, "help", "") or "No description available"

        # get default
        default = _format_default(param)

        # check required
        required = getattr(param, "required", False)

        options.append(
            IntrospectedOption(
                name=primary,
                aliases=aliases,
                type_name=type_name,
                description=description,
                default=default,
                required=required,
            )
        )

    return options


def _get_type_name(param: Any) -> str:
    if hasattr(param, "type"):
        ptype = param.type
        if ptype is None:
            return "TEXT"
        if ptype == bool:
            return "FLAG"
        if hasattr(ptype, "__name__"):
            name = ptype.__name__
            if name == "str":
                return "TEXT"
            if name == "int":
                return "INT"
            if name == "float":
                return "FLOAT"
            if name == "bool":
                return "FLAG"
            if name == "Path":
                return "PATH"
            return name.upper()
        if hasattr(ptype, "name"):
            return ptype.name.upper()
        # check for click.Choice
        if hasattr(ptype, "choices"):
            return "CHOICE"
    return "TEXT"


def _format_default(param: Any) -> str | None:
    default = getattr(param, "default", None)
    if default is None:
        return None
    if callable(default):
        return None  # skip factory functions
    if default is False:
        return "false"
    if default is True:
        return "true"
    if isinstance(default, str) and not default:
        return None
    return str(default)


# get command object from Typer app by name; returns command object if found or None
def get_command_from_app(app: Any, command_name: str) -> Any | None:
    if not hasattr(app, "registered_commands"):
        return None

    # Typer stores commands in registered_commands list
    for info in app.registered_commands:
        if info.name == command_name:
            # need to get the actual Click command
            if hasattr(info, "callback"):
                # try to get the Click command from the Typer app's internal mapping
                pass
    return None


# try to extract command object from Typer context; returns command object if found or None
def get_command_from_context(ctx: Any, command_name: str) -> Any | None:
    # try to get parent app
    if ctx and hasattr(ctx, "parent") and ctx.parent:
        parent = ctx.parent
        if hasattr(parent, "command"):
            app = parent.command
            # Click apps have a commands dict
            if hasattr(app, "commands") and command_name in app.commands:
                return app.commands[command_name]

    # if we're directly on the command context
    if ctx and hasattr(ctx, "command"):
        return ctx.command

    return None
