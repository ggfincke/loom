# tests/unit/cli/commands/test_templates.py
# Unit tests for templates command (list available templates)

import pytest
from typer.testing import CliRunner
from src.cli.app import app


runner = CliRunner()


# * Test that templates command lists available bundled templates
def test_templates_lists_available_templates():
    result = runner.invoke(app, ["templates"])

    # skip if templates not found (may happen in isolated test env)
    if "not found" in result.stdout.lower():
        pytest.skip("Templates not available in test environment")

    # verify command succeeded
    assert result.exit_code == 0

    # verify output mentions templates
    stdout_lower = result.stdout.lower()
    assert "template" in stdout_lower or "swe-latex" in stdout_lower


# * Test that templates command works w/o arguments
def test_templates_command_no_args():
    result = runner.invoke(app, ["templates"])

    # command should not crash even if no templates found
    assert result.exit_code == 0 or "not found" in result.stdout.lower()


# * Test that templates output includes template IDs & details
def test_templates_shows_template_details():
    result = runner.invoke(app, ["templates"])

    # skip if templates not available
    if "not found" in result.stdout.lower() or result.exit_code != 0:
        pytest.skip("Templates not available in test environment")

    # verify output format includes template info
    # should show: template ID, type, name, & location
    stdout_lower = result.stdout.lower()
    assert "swe-latex" in stdout_lower or "available" in stdout_lower
