# src/config/settings.py
# Configuration management for Loom CLI including default paths and OpenAI settings

import json
from pathlib import Path
from typing import Dict, Any, Optional
import typer
from dataclasses import dataclass, asdict

# * Default Settings for Loom CLI
'''
this class defines the default settings for the Loom CLI application, including paths and OpenAI model settings;
it uses dataclasses for easy instantiation and management of settings
'''
@dataclass
class LoomSettings:
    # default paths
    data_dir: str = "data"
    output_dir: str = "output" 
    resume_filename: str = "resume.docx"
    job_filename: str = "job.txt"
    sections_filename: str = "sections.json"
    edits_filename: str = "edits.json"
    
    # loom internal paths
    base_dir: str = ".loom"
    warnings_filename: str = "edits.warnings.txt"
    diff_filename: str = "diff.patch"
    plan_filename: str = "plan.txt"
    
    # OpenAI model setting
    model: str = "gpt-5-mini"
    # temp setting (note: GPT-5 models don't support temperature parameter)
    temperature: float = 0.2
    
    # risk management setting
    risk: str = "ask"
    
    @property
    def resume_path(self) -> Path:
        return Path(self.data_dir) / self.resume_filename
    
    @property
    def job_path(self) -> Path:
        return Path(self.data_dir) / self.job_filename
    
    @property
    def sections_path(self) -> Path:
        return Path(self.output_dir) / self.sections_filename
    
    @property
    def edits_path(self) -> Path:
        return Path(self.output_dir) / self.edits_filename
    
    # loom internal paths
    @property
    def loom_dir(self) -> Path:
        return Path(self.base_dir)
    
    @property
    def edits_json_path(self) -> Path:
        return self.loom_dir / self.edits_filename
    
    @property
    def warnings_path(self) -> Path:
        return self.loom_dir / self.warnings_filename
    
    @property
    def diff_path(self) -> Path:
        return self.loom_dir / self.diff_filename
    
    @property
    def plan_path(self) -> Path:
        return self.loom_dir / self.plan_filename


# * Settings management
'''
this class manages Loom settings, allowing for loading, saving, and modifying settings;
it uses a JSON file for persistence and provides methods to get, set, reset, and list settings
'''
class SettingsManager:    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path.home() / ".loom" / "config.json"
        self._settings = None
    
    # load settings from file or return defaults
    def load(self) -> LoomSettings:
        if self._settings is not None:
            return self._settings
        
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                self._settings = LoomSettings(**data)
            except (json.JSONDecodeError, TypeError, ValueError) as e:
                typer.echo(f"Warning: Invalid config file {self.config_path}: {e}")
                typer.echo("Using default settings")
                self._settings = LoomSettings()
        else:
            self._settings = LoomSettings()
        
        return self._settings
    
    # save setting to file 
    def save(self, settings: LoomSettings) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.config_path, 'w') as f:
            json.dump(asdict(settings), f, indent=2)
        
        self._settings = settings
    
    # get a specific setting value
    def get(self, key: str) -> Any:
        settings = self.load()
        return getattr(settings, key, None)
    
    # set a specific setting value 
    def set(self, key: str, value: Any) -> None:
        settings = self.load()
        if not hasattr(settings, key):
            raise ValueError(f"Unknown setting: {key}")
        
        setattr(settings, key, value)
        self.save(settings)
    
    # reset to default settings
    def reset(self) -> None:
        self.save(LoomSettings())
    
    # list all settings as a dictionary
    def list_settings(self) -> Dict[str, Any]:
        return asdict(self.load())


# global settings manager instance
settings_manager = SettingsManager()