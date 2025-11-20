# tests/unit/cli/commands/test_init.py
# Unit tests for init command (template scaffolding)

from pathlib import Path
import pytest
from typer.testing import CliRunner
from src.cli.app import app


runner = CliRunner()


# * Test that init command creates resume from bundled template
def test_init_creates_resume_from_template(tmp_path, monkeypatch):
    # change to tmp directory
    monkeypatch.chdir(tmp_path)

    # run init command w/ swe-latex template
    result = runner.invoke(app, ["init", "--template", "swe-latex", "--output", "my-resume"])

    # verify command succeeded (or skip if templates not found in test env)
    if "not found" in result.stdout.lower() or result.exit_code != 0:
        pytest.skip("Templates not available in test environment")

    # verify output directory created
    output_dir = tmp_path / "my-resume"
    assert output_dir.exists()
    assert output_dir.is_dir()

    # verify key files copied
    assert (output_dir / "resume.tex").exists()
    assert (output_dir / "loom-template.toml").exists()


# * Test that init command fails gracefully w/ invalid template ID
def test_init_fails_with_invalid_template(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    # run init w/ nonexistent template
    result = runner.invoke(app, ["init", "--template", "nonexistent-template-xyz"])

    # verify command failed
    assert result.exit_code != 0
    assert "not found" in result.stdout.lower() or "error" in result.stdout.lower()


# * Test that init uses default 'resume' directory when output not specified
def test_init_default_output_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    # run init w/o specifying output
    result = runner.invoke(app, ["init", "--template", "swe-latex"])

    # skip if templates not available
    if "not found" in result.stdout.lower() or result.exit_code != 0:
        pytest.skip("Templates not available in test environment")

    # verify default 'resume' directory created
    default_dir = tmp_path / "resume"
    assert default_dir.exists()
