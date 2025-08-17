# tests/integration/test_cli_config_happy.py
# Integration tests for CLI config commands happy paths w/ isolated home

import pytest
import json
from typer.testing import CliRunner
from pathlib import Path


# * Ensure config path command returns isolated temp config location
def test_config_path_returns_isolated_temp_path(isolate_config):
    from src.cli.app import app
    
    runner = CliRunner()
    
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["config", "path"], env={"NO_COLOR": "1", "TERM": "dumb"})
        
        assert result.exit_code == 0
        
        # should contain temp path components from isolation
        output = result.stdout.strip()
        assert ".loom" in output
        assert "config.json" in output
        
        # verify it's actually in the isolated location
        config_path = Path(output)
        assert config_path.exists()


# * Ensure config set key value → config get key returns same value
def test_config_set_get_round_trip(isolate_config):
    from src.cli.app import app
    
    runner = CliRunner()
    
    with runner.isolated_filesystem():
        # set a string value
        result = runner.invoke(app, ["config", "set", "model", "gpt-4o"], env={"NO_COLOR": "1", "TERM": "dumb"})
        assert result.exit_code == 0
        
        # get the value back
        # JSON-formatted output
        result = runner.invoke(app, ["config", "get", "model"], env={"NO_COLOR": "1", "TERM": "dumb"})
        assert result.exit_code == 0
        assert '"gpt-4o"' in result.stdout
        
        # Test numeric value coercion
        result = runner.invoke(app, ["config", "set", "temperature", "0.5"], env={"NO_COLOR": "1", "TERM": "dumb"})
        assert result.exit_code == 0
        
        result = runner.invoke(app, ["config", "get", "temperature"], env={"NO_COLOR": "1", "TERM": "dumb"})
        assert result.exit_code == 0
        assert "0.5" in result.stdout
        
        # Test boolean value coercion
        result = runner.invoke(app, ["config", "set", "model", "true"], env={"NO_COLOR": "1", "TERM": "dumb"})
        assert result.exit_code == 0
        
        result = runner.invoke(app, ["config", "get", "model"], env={"NO_COLOR": "1", "TERM": "dumb"})
        assert result.exit_code == 0
        assert "true" in result.stdout


# * Ensure config list displays updated configuration after setting values
def test_config_list_shows_newly_set_keys(isolate_config):
    from src.cli.app import app
    
    runner = CliRunner()
    
    with runner.isolated_filesystem():
        # Set multiple values
        runner.invoke(app, ["config", "set", "model", "gpt-4o"], env={"NO_COLOR": "1", "TERM": "dumb"})
        runner.invoke(app, ["config", "set", "data_dir", "/custom/data"], env={"NO_COLOR": "1", "TERM": "dumb"})
        
        # List all settings
        result = runner.invoke(app, ["config", "list"], env={"NO_COLOR": "1", "TERM": "dumb"})
        assert result.exit_code == 0
        
        output = result.stdout
        
        # Check newly set values appear in list
        assert "gpt-4o" in output
        assert "/custom/data" in output
        assert "model" in output
        assert "data_dir" in output
        
        # Check configuration header/formatting
        assert "Configuration" in output or "Config" in output


# * Ensure 'config' w/o subcommand shows list by default
def test_config_list_as_default_subcommand(isolate_config):
    from src.cli.app import app
    
    runner = CliRunner()
    
    with runner.isolated_filesystem():
        # Set a test value
        runner.invoke(app, ["config", "set", "model", "test-model"], env={"NO_COLOR": "1", "TERM": "dumb"})
        
        # Invoke config w/o subcommand
        result = runner.invoke(app, ["config"], env={"NO_COLOR": "1", "TERM": "dumb"})
        assert result.exit_code == 0
        
        output = result.stdout
        
        # Should show current configuration (same as 'config list')
        assert "test-model" in output
        assert "model" in output


# * Ensure config reset command restores all settings to defaults
def test_config_reset_restores_defaults(isolate_config):
    from src.cli.app import app
    
    runner = CliRunner()
    
    with runner.isolated_filesystem():
        # Set custom values
        runner.invoke(app, ["config", "set", "model", "custom-model"], env={"NO_COLOR": "1", "TERM": "dumb"})
        runner.invoke(app, ["config", "set", "data_dir", "/custom/path"], env={"NO_COLOR": "1", "TERM": "dumb"})
        
        # Verify custom values are set
        result = runner.invoke(app, ["config", "get", "model"], env={"NO_COLOR": "1", "TERM": "dumb"})
        assert "custom-model" in result.stdout
        
        # Reset to defaults
        result = runner.invoke(app, ["config", "reset"], env={"NO_COLOR": "1", "TERM": "dumb"})
        assert result.exit_code == 0
        assert "Reset" in result.stdout or "reset" in result.stdout
        
        # Verify defaults are restored
        # default model from LoomSettings
        result = runner.invoke(app, ["config", "get", "model"], env={"NO_COLOR": "1", "TERM": "dumb"})
        assert "gpt-5-mini" in result.stdout
        
        # default data_dir
        result = runner.invoke(app, ["config", "get", "data_dir"], env={"NO_COLOR": "1", "TERM": "dumb"})
        assert '"data"' in result.stdout


# * Ensure theme setting accepts valid theme values
def test_config_theme_setting_validation(isolate_config):
    from src.cli.app import app
    
    runner = CliRunner()
    
    with runner.isolated_filesystem():
        # Set valid theme
        result = runner.invoke(app, ["config", "set", "theme", "deep_blue"], env={"NO_COLOR": "1", "TERM": "dumb"})
        assert result.exit_code == 0
        
        # Verify theme was set
        result = runner.invoke(app, ["config", "get", "theme"], env={"NO_COLOR": "1", "TERM": "dumb"})
        assert result.exit_code == 0
        assert "deep_blue" in result.stdout


# * Ensure config changes persist between separate command invocations
def test_config_persistence_across_commands(isolate_config):
    from src.cli.app import app
    
    runner = CliRunner()
    
    with runner.isolated_filesystem():
        # Set value in first command
        result = runner.invoke(app, ["config", "set", "model", "persistent-test"], env={"NO_COLOR": "1", "TERM": "dumb"})
        assert result.exit_code == 0
        
        # Create new runner instance to simulate separate invocation
        runner2 = CliRunner()
        
        # Get value in second command w/ new runner
        result = runner2.invoke(app, ["config", "get", "model"], env={"NO_COLOR": "1", "TERM": "dumb"})
        assert result.exit_code == 0
        assert "persistent-test" in result.stdout
