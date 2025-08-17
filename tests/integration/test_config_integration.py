# tests/integration/test_config_integration.py
# integration test for config system w/ file system isolation

import pytest
import json
from pathlib import Path
from src.config.settings import SettingsManager, LoomSettings


@pytest.mark.integration
def test_settings_manager_integration(isolate_config, temp_output_dirs):
    # test full settings manager workflow w/ isolated config
    fake_home = isolate_config
    config_path = fake_home / ".loom" / "config.json"
    
    # create settings manager w/ isolated config path
    settings_manager = SettingsManager(config_path)
    
    # load settings should use isolated config
    settings = settings_manager.load()
    assert settings.model == "gpt-4o-mini"
    assert settings.data_dir == "data"
    
    # modify & save settings
    settings_manager.set("model", "gpt-4o")
    settings_manager.set("data_dir", "custom_data")
    
    # verify changes persisted
    updated_settings = settings_manager.load()
    assert updated_settings.model == "gpt-4o"
    assert updated_settings.data_dir == "custom_data"
    
    # verify config file was updated
    with open(config_path) as f:
        config_data = json.load(f)
    assert config_data["model"] == "gpt-4o"
    assert config_data["data_dir"] == "custom_data"


@pytest.mark.integration
def test_settings_paths_work_correctly(isolate_config):
    # test that settings paths resolve correctly w/ isolation
    fake_home = isolate_config
    config_path = fake_home / ".loom" / "config.json"
    
    settings_manager = SettingsManager(config_path)
    settings = settings_manager.load()
    
    # test path properties
    assert settings.resume_path == Path("data") / "resume.docx"
    assert settings.sections_path == Path("output") / "sections.json" 
    assert settings.loom_dir == Path(".loom")
    assert settings.warnings_path == Path(".loom") / "edits.warnings.txt"


@pytest.mark.integration
def test_settings_reset_functionality(isolate_config):
    # test settings reset restores defaults
    fake_home = isolate_config
    config_path = fake_home / ".loom" / "config.json"
    
    settings_manager = SettingsManager(config_path)
    
    # modify settings
    settings_manager.set("model", "custom-model")
    settings_manager.set("theme", "custom-theme")
    
    # reset to defaults
    settings_manager.reset()
    
    # verify defaults restored
    settings = settings_manager.load()
    assert settings.model == "gpt-5-mini"  # default from LoomSettings
    assert settings.theme == "deep_blue"