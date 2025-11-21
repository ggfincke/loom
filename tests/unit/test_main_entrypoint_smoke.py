# tests/unit/test_main_entrypoint_smoke.py
# Smoke test: import main & invoke entrypoint via CliRunner

import sys
import types
from typer.testing import CliRunner


# ensure optional modules used by CLI commands are present as dummies
def _ensure_dummy_optional_modules():
    # simple_term_menu is used by a UI helper imported via CLI command modules
    if "simple_term_menu" not in sys.modules:
        mod = types.ModuleType("simple_term_menu")
        setattr(mod, "TerminalMenu", object)
        sys.modules["simple_term_menu"] = mod


# * verify main entrypoint runs & exits 0
def test_main_entrypoint_runs():
    _ensure_dummy_optional_modules()
    from src import main

    runner = CliRunner()
    # invoking with no args triggers quick usage and exits cleanly
    result = runner.invoke(main.app, [])
    assert result.exit_code == 0
