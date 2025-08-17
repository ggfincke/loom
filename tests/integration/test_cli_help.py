# tests/integration/test_cli_help.py
# Integration tests for CLI help commands & main help functionality

import pytest
from typer.testing import CliRunner
from pathlib import Path


# * Ensure CLI entrypoint wired & main help shows core commands
def test_main_help_displays_key_commands(isolate_config):
    from src.cli.app import app
    
    runner = CliRunner()
    
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["--help"], env={"NO_COLOR": "1", "TERM": "dumb"})
        
        assert result.exit_code == 0
        output = result.stdout
        
        # check key command names appear in help
        assert "sectionize" in output
        assert "tailor" in output
        assert "config" in output
        assert "plan" in output
        
        # check usage pattern appears
        assert "Usage" in output or "Commands" in output or "loom" in output


# * Ensure --help-raw flag shows raw Typer help instead of branded help
def test_main_help_raw_flag_shows_typer_help(isolate_config):
    from src.cli.app import app
    
    runner = CliRunner()
    
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["--help-raw"], env={"NO_COLOR": "1", "TERM": "dumb"})
        
        assert result.exit_code == 0
        output = result.stdout
        
        # raw typer help should contain usage pattern
        assert "Usage:" in output


# * Ensure config --help displays config help content (branded)
def test_config_help_shows_description(isolate_config):
    from src.cli.app import app
    
    runner = CliRunner()
    
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["config", "--help"], env={"NO_COLOR": "1", "TERM": "dumb"})
        
        assert result.exit_code == 0
        output = result.stdout
        
        # branded help emphasizes description & usage, not subcommand list
        assert "config" in output.lower()
        assert "usage" in output.lower() or "manage" in output.lower() or "settings" in output.lower()


# * Ensure models --help displays models command info
def test_models_help_shows_description(isolate_config):
    from src.cli.app import app
    
    runner = CliRunner()
    
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["models", "--help"], env={"NO_COLOR": "1", "TERM": "dumb"})
        
        assert result.exit_code == 0
        output = result.stdout
        
        # check models-related content
        assert "models" in output.lower()
        assert "provider" in output.lower() or "AI" in output or "OpenAI" in output or "available" in output.lower()


# * Ensure models command exists & can be invoked
def test_models_command_functionality(isolate_config):
    from src.cli.app import app
    
    runner = CliRunner()
    
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["models"], env={"NO_COLOR": "1", "TERM": "dumb"})
        
        assert result.exit_code == 0
        output = result.stdout
        
        # should show some model provider information
        assert "model" in output.lower() or "provider" in output.lower() or "available" in output.lower()


# * Ensure 'loom help config' shows specific config help
def test_help_command_with_config_argument(isolate_config):
    from src.cli.app import app
    
    runner = CliRunner()
    
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["help", "config"], env={"NO_COLOR": "1", "TERM": "dumb"})
        
        assert result.exit_code == 0
        output = result.stdout
        
        # should show config-specific help content
        assert "config" in output.lower()


# * Ensure 'loom help' w/o args shows available commands
def test_help_command_without_argument_shows_available_commands(isolate_config):
    from src.cli.app import app
    
    runner = CliRunner()
    
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["help"], env={"NO_COLOR": "1", "TERM": "dumb"})
        
        assert result.exit_code == 0
        output = result.stdout
        
        # should show available commands or help message
        assert "command" in output.lower()
