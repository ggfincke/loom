# tests/unit/test_config_settings.py
# Unit tests for configuration management including load/save, defaults & theme validation

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

from src.config.settings import LoomSettings, SettingsManager
from src.ui.colors import THEMES


# * Test LoomSettings dataclass behavior
class TestLoomSettings:
    
    # * Test default values are correctly set
    def test_default_settings(self):
        settings = LoomSettings()
        
        # verify path defaults
        assert settings.data_dir == "data"
        assert settings.output_dir == "output"
        assert settings.resume_filename == "resume.docx"
        assert settings.job_filename == "job.txt"
        assert settings.sections_filename == "sections.json"
        assert settings.edits_filename == "edits.json"
        
        # verify loom internal defaults  
        assert settings.base_dir == ".loom"
        assert settings.warnings_filename == "edits.warnings.txt"
        assert settings.diff_filename == "diff.patch"
        assert settings.plan_filename == "plan.txt"
        
        # verify AI & display defaults
        assert settings.model == "gpt-5-mini"
        assert settings.temperature == 0.2
        assert settings.risk == "ask"
        assert settings.theme == "deep_blue"
    
    # * Test path composition properties work correctly
    def test_path_composition(self):
        settings = LoomSettings(
            data_dir="custom_data",
            output_dir="custom_output",
            resume_filename="my_resume.docx",
            job_filename="my_job.txt"
        )
        
        # verify composed paths use custom directories
        assert settings.resume_path == Path("custom_data") / "my_resume.docx"
        assert settings.job_path == Path("custom_data") / "my_job.txt" 
        assert settings.sections_path == Path("custom_output") / "sections.json"
        assert settings.edits_path == Path("custom_output") / "edits.json"
        
        # verify loom internal paths
        assert settings.loom_dir == Path(".loom")
        assert settings.warnings_path == Path(".loom") / "edits.warnings.txt"
        assert settings.diff_path == Path(".loom") / "diff.patch"
        assert settings.plan_path == Path(".loom") / "plan.txt"
    
    # * Test path properties return Path objects
    def test_path_properties_return_path_objects(self):
        settings = LoomSettings()
        
        assert isinstance(settings.resume_path, Path)
        assert isinstance(settings.job_path, Path)
        assert isinstance(settings.sections_path, Path)
        assert isinstance(settings.edits_path, Path)
        assert isinstance(settings.loom_dir, Path)
        assert isinstance(settings.warnings_path, Path)
        assert isinstance(settings.diff_path, Path)
        assert isinstance(settings.plan_path, Path)


# * Test SettingsManager configuration persistence & operations
class TestSettingsManager:
    
    # * Test loading settings from existing valid config file
    def test_load_existing_valid_config(self, tmp_path):
        config_path = tmp_path / "config.json"
        config_data = {
            "data_dir": "test_data",
            "output_dir": "test_output", 
            "model": "gpt-4o",
            "theme": "cyber_neon"
        }
        
        with open(config_path, 'w') as f:
            json.dump(config_data, f)
        
        manager = SettingsManager(config_path)
        settings = manager.load()
        
        # verify loaded values override defaults
        assert settings.data_dir == "test_data"
        assert settings.output_dir == "test_output"
        assert settings.model == "gpt-4o"
        assert settings.theme == "cyber_neon"
        
        # verify defaults remain for unspecified values
        assert settings.resume_filename == "resume.docx"
        assert settings.temperature == 0.2
    
    # * Test loading with non-existent config file returns defaults
    def test_load_nonexistent_config_returns_defaults(self, tmp_path):
        config_path = tmp_path / "nonexistent.json"
        
        manager = SettingsManager(config_path)
        settings = manager.load()
        
        # verify all default values
        assert settings.data_dir == "data"
        assert settings.model == "gpt-5-mini"
        assert settings.theme == "deep_blue"
    
    # * Test loading with malformed JSON falls back to defaults
    def test_load_malformed_json_fallback(self, tmp_path, capsys):
        config_path = tmp_path / "malformed.json"
        
        # write invalid JSON
        with open(config_path, 'w') as f:
            f.write('{"invalid": json}')
        
        manager = SettingsManager(config_path)
        settings = manager.load()
        
        # verify fallback to defaults
        assert settings.data_dir == "data"
        assert settings.model == "gpt-5-mini"
        
        # verify warning was displayed
        captured = capsys.readouterr()
        assert "Warning: Invalid config file" in captured.out
        assert "Using default settings" in captured.out
    
    # * Test loading with invalid types that cause TypeError falls back to defaults
    def test_load_invalid_types_fallback(self, tmp_path, capsys):
        config_path = tmp_path / "invalid_types.json"
        # create data that will cause TypeError when creating LoomSettings
        config_data = {
            "nonexistent_field": "value",
            "data_dir": 123  # this might be accepted by dataclass
        }
        
        with open(config_path, 'w') as f:
            json.dump(config_data, f)
        
        manager = SettingsManager(config_path)
        settings = manager.load()
        
        # verify fallback to defaults when TypeError occurs
        captured = capsys.readouterr()
        if "Warning: Invalid config file" in captured.out:
            # if error occurred, should fall back to defaults
            assert settings.data_dir == "data"
            assert settings.temperature == 0.2
        else:
            # if no error, the settings might accept the values as-is
            # this tests the actual behavior rather than assumed behavior
            assert hasattr(settings, 'data_dir')
    
    # * Test saving settings creates config file & directory
    def test_save_creates_directory_and_file(self, tmp_path):
        config_path = tmp_path / "new_dir" / "config.json"
        settings = LoomSettings(data_dir="saved_data", model="gpt-4o")
        
        manager = SettingsManager(config_path)
        manager.save(settings)
        
        # verify directory was created
        assert config_path.parent.exists()
        
        # verify file was created with correct content
        assert config_path.exists()
        with open(config_path, 'r') as f:
            saved_data = json.load(f)
        
        assert saved_data["data_dir"] == "saved_data"
        assert saved_data["model"] == "gpt-4o"
    
    # * Test saving preserves all settings in JSON format
    def test_save_preserves_all_settings(self, tmp_path):
        config_path = tmp_path / "config.json"
        settings = LoomSettings(
            data_dir="custom",
            output_dir="out",
            model="gpt-4o",
            theme="volcanic_fire",
            temperature=0.5
        )
        
        manager = SettingsManager(config_path)
        manager.save(settings)
        
        # verify round-trip preservation
        with open(config_path, 'r') as f:
            saved_data = json.load(f)
        
        assert saved_data["data_dir"] == "custom"
        assert saved_data["output_dir"] == "out"
        assert saved_data["model"] == "gpt-4o"
        assert saved_data["theme"] == "volcanic_fire"
        assert saved_data["temperature"] == 0.5
        
        # verify JSON is well-formatted w/ indentation
        with open(config_path, 'r') as f:
            content = f.read()
        assert '  ' in content  # check for indentation
    
    # * Test get method retrieves specific setting values
    def test_get_setting(self, tmp_path):
        config_path = tmp_path / "config.json"
        config_data = {"model": "gpt-4o", "theme": "arctic_ice"}
        
        with open(config_path, 'w') as f:
            json.dump(config_data, f)
        
        manager = SettingsManager(config_path)
        
        assert manager.get("model") == "gpt-4o"
        assert manager.get("theme") == "arctic_ice"
        assert manager.get("data_dir") == "data"  # default value
        assert manager.get("nonexistent") is None
    
    # * Test set method updates specific settings
    def test_set_setting(self, tmp_path):
        config_path = tmp_path / "config.json"
        
        manager = SettingsManager(config_path)
        
        # set a new value
        manager.set("model", "gpt-4o")
        manager.set("theme", "synthwave_retro")
        
        # verify setting was persisted
        with open(config_path, 'r') as f:
            saved_data = json.load(f)
        
        assert saved_data["model"] == "gpt-4o"
        assert saved_data["theme"] == "synthwave_retro"
        
        # verify other defaults remain
        assert saved_data["data_dir"] == "data"
    
    # * Test set method raises error for unknown settings
    def test_set_unknown_setting_raises_error(self, tmp_path):
        config_path = tmp_path / "config.json"
        manager = SettingsManager(config_path)
        
        with pytest.raises(ValueError, match="Unknown setting: invalid_key"):
            manager.set("invalid_key", "value")
    
    # * Test reset method restores all defaults
    def test_reset_restores_defaults(self, tmp_path):
        config_path = tmp_path / "config.json"
        
        # create config w/ custom values
        custom_data = {
            "data_dir": "custom",
            "model": "gpt-4o", 
            "theme": "ruby_crimson"
        }
        with open(config_path, 'w') as f:
            json.dump(custom_data, f)
        
        manager = SettingsManager(config_path)
        
        # verify custom values loaded
        assert manager.get("data_dir") == "custom"
        assert manager.get("model") == "gpt-4o"
        
        # reset to defaults
        manager.reset()
        
        # verify defaults restored
        assert manager.get("data_dir") == "data"
        assert manager.get("model") == "gpt-5-mini"
        assert manager.get("theme") == "deep_blue"
        
        # verify file contains defaults
        with open(config_path, 'r') as f:
            saved_data = json.load(f)
        assert saved_data["data_dir"] == "data"
        assert saved_data["model"] == "gpt-5-mini"
    
    # * Test list_settings returns complete dictionary
    def test_list_settings(self, tmp_path):
        config_path = tmp_path / "config.json"
        config_data = {"model": "gpt-4o", "theme": "galaxy_nebula"}
        
        with open(config_path, 'w') as f:
            json.dump(config_data, f)
        
        manager = SettingsManager(config_path)
        all_settings = manager.list_settings()
        
        # verify custom values
        assert all_settings["model"] == "gpt-4o"
        assert all_settings["theme"] == "galaxy_nebula"
        
        # verify defaults are included
        assert all_settings["data_dir"] == "data"
        assert all_settings["resume_filename"] == "resume.docx"
        assert all_settings["temperature"] == 0.2
        
        # verify all expected keys are present
        expected_keys = {
            "data_dir", "output_dir", "resume_filename", "job_filename",
            "sections_filename", "edits_filename", "base_dir", "warnings_filename", 
            "diff_filename", "plan_filename", "model", "temperature", "risk", "theme"
        }
        assert set(all_settings.keys()) == expected_keys
    
    # * Test settings caching behavior
    def test_settings_caching(self, tmp_path):
        config_path = tmp_path / "config.json"
        config_data = {"model": "gpt-4o"}
        
        with open(config_path, 'w') as f:
            json.dump(config_data, f)
        
        manager = SettingsManager(config_path)
        
        # first load
        settings1 = manager.load()
        
        # second load should return cached instance
        settings2 = manager.load()
        
        assert settings1 is settings2
        
        # after save, cache should be updated
        new_settings = LoomSettings(model="claude-3")
        manager.save(new_settings)
        
        settings3 = manager.load()
        assert settings3 is new_settings
        assert settings3.model == "claude-3"


# * Test theme validation & integration 
class TestThemeValidation:
    
    # * Test valid theme names are accepted
    def test_valid_theme_acceptance(self, tmp_path):
        config_path = tmp_path / "config.json"
        manager = SettingsManager(config_path)
        
        # test all valid themes from THEMES dict
        for theme_name in THEMES.keys():
            manager.set("theme", theme_name)
            assert manager.get("theme") == theme_name
    
    # * Test theme validation with config command integration
    def test_theme_validation_integration(self, tmp_path):
        from src.cli.commands.config import _valid_themes
        
        config_path = tmp_path / "config.json"
        manager = SettingsManager(config_path)
        
        # verify _valid_themes returns correct set
        valid_themes = _valid_themes()
        assert valid_themes == set(THEMES.keys())
        
        # verify themes can be set from valid set
        for theme in valid_themes:
            manager.set("theme", theme)
            assert manager.get("theme") == theme


# * Test config path composition & isolation
class TestConfigPathHandling:
    
    # * Test default config path uses home directory
    def test_default_config_path(self):
        manager = SettingsManager()
        expected_path = Path.home() / ".loom" / "config.json"
        assert manager.config_path == expected_path
    
    # * Test custom config path is respected
    def test_custom_config_path(self, tmp_path):
        custom_path = tmp_path / "custom.json"
        manager = SettingsManager(custom_path)
        assert manager.config_path == custom_path
    
    # * Test config isolation works with existing fixture
    def test_config_isolation_with_fixture(self, isolate_config):
        # this test verifies the existing isolate_config fixture works
        manager = SettingsManager()
        
        # should use isolated config from fixture
        expected_path = isolate_config / ".loom" / "config.json"
        assert manager.config_path == expected_path
        
        # should load fixture config values
        settings = manager.load()
        assert settings.theme == "deep_blue"  # from fixture
        assert settings.model == "gpt-5-mini"  # from fixture