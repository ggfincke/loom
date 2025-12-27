# src/config/settings.py
# Configuration management for Loom CLI including default paths & OpenAI settings

from pathlib import Path
from typing import Dict, Any, Optional, cast
import typer
from dataclasses import dataclass, asdict

from ..loom_io.generics import read_json_safe, write_json_safe
from ..core.exceptions import JSONParsingError


# * Default settings dataclass for Loom CLI w/ paths & OpenAI model configuration
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

    # theme setting
    theme: str = "deep_blue"

    # interactive diff setting
    interactive: bool = True

    # dev mode setting (enables access to development commands)
    dev_mode: bool = False

    # cache settings for AI response caching
    cache_enabled: bool = True
    cache_ttl_days: int = 7
    cache_dir: str = ".loom/cache"

    # watch mode settings
    watch_debounce: float = 1.0

    def __post_init__(self) -> None:
        # Validate settings values after initialization.
        # Temperature validation (OpenAI/Anthropic range: 0.0-2.0)
        if not isinstance(self.temperature, (int, float)):
            raise ValueError(
                f"temperature must be a number, got {type(self.temperature).__name__}"
            )
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError(f"temperature must be 0.0-2.0, got {self.temperature}")

        # Risk validation
        valid_risks = {"ask", "skip", "abort", "auto"}
        if self.risk not in valid_risks:
            raise ValueError(f"risk must be one of {valid_risks}, got '{self.risk}'")

        # dev_mode strict bool validation (no coercion)
        if not isinstance(self.dev_mode, bool):
            raise ValueError(
                f"dev_mode must be a boolean (true/false), "
                f"got {type(self.dev_mode).__name__}: {self.dev_mode}"
            )

        # interactive strict bool validation
        if not isinstance(self.interactive, bool):
            raise ValueError(
                f"interactive must be a boolean (true/false), "
                f"got {type(self.interactive).__name__}"
            )

        # cache_enabled strict bool validation
        if not isinstance(self.cache_enabled, bool):
            raise ValueError(
                f"cache_enabled must be a boolean (true/false), "
                f"got {type(self.cache_enabled).__name__}"
            )

        # cache_ttl_days validation (must be positive integer)
        if not isinstance(self.cache_ttl_days, int) or self.cache_ttl_days < 1:
            raise ValueError(
                f"cache_ttl_days must be a positive integer, got {self.cache_ttl_days}"
            )

        # watch_debounce validation (must be >= 0.1 seconds)
        if (
            not isinstance(self.watch_debounce, (int, float))
            or self.watch_debounce < 0.1
        ):
            raise ValueError(
                f"watch_debounce must be >= 0.1 seconds, got {self.watch_debounce}"
            )

    @property
    def resume_path(self) -> Path:
        return Path(self.data_dir) / self.resume_filename

    @property
    def job_path(self) -> Path:
        return Path(self.data_dir) / self.job_filename

    @property
    def sections_path(self) -> Path:
        return Path(self.data_dir) / self.sections_filename

    @property
    def edits_path(self) -> Path:
        return Path(self.output_dir) / self.edits_filename

    # loom internal paths
    @property
    def loom_dir(self) -> Path:
        return Path(self.base_dir)

    @property
    def warnings_path(self) -> Path:
        return self.loom_dir / self.warnings_filename

    @property
    def diff_path(self) -> Path:
        return self.loom_dir / self.diff_filename

    @property
    def plan_path(self) -> Path:
        return self.loom_dir / self.plan_filename


# * Settings management class w/ JSON persistence for loading, saving, & modifying settings
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
                data = read_json_safe(self.config_path)
                self._settings = LoomSettings(**data)
            except (JSONParsingError, TypeError, ValueError) as e:
                typer.echo(f"Warning: Invalid config file {self.config_path}: {e}")
                typer.echo("Using default settings")
                self._settings = LoomSettings()
        else:
            self._settings = LoomSettings()

        return self._settings

    # save setting to file
    def save(self, settings: LoomSettings) -> None:
        write_json_safe(asdict(settings), self.config_path)
        self._settings = settings
        self._notify_settings_changed()

    def _notify_settings_changed(self) -> None:
        # Notify dependent caches of settings change.
        try:
            from ..ai.cache import AICache

            AICache.invalidate_all()
        except ImportError:
            pass  # AI module not loaded yet

        # Reset dev mode cache
        try:
            from .dev_mode import reset_dev_mode_cache

            reset_dev_mode_cache()
        except ImportError:
            pass  # dev_mode module not loaded yet

        # Reset response cache (in case cache settings changed)
        try:
            from ..ai.response_cache import reset_response_cache

            reset_response_cache()
        except ImportError:
            pass  # response_cache module not loaded yet

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


# * Retrieve settings preferring injected object from Typer context
def get_settings(
    ctx: typer.Context, provided: Optional[LoomSettings] = None
) -> LoomSettings:
    # prefer explicitly provided settings
    if provided is not None:
        return provided

    # search ctx, parent, & root for LoomSettings
    candidates: list[typer.Context] = [ctx]
    parent = cast(Optional[typer.Context], getattr(ctx, "parent", None))
    if parent is not None:
        candidates.append(parent)
    # Typer Context has find_root method; call if present
    find_root = getattr(ctx, "find_root", None)
    root_ctx = (
        cast(Optional[typer.Context], find_root()) if callable(find_root) else None
    )
    if root_ctx is not None:
        candidates.append(root_ctx)

    for c in candidates:
        obj = getattr(c, "obj", None)
        if isinstance(obj, LoomSettings):
            return obj

    # fallback to loading from disk
    return settings_manager.load()
