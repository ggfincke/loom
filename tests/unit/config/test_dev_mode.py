# tests/unit/config/test_dev_mode.py
# Unit tests for unified dev mode detection

import pytest
from unittest.mock import Mock, patch
import typer

from src.config.dev_mode import is_dev_mode_enabled, reset_dev_mode_cache


# * Tests for is_dev_mode_enabled() function


class TestIsDevModeEnabled:
    # Tests for is_dev_mode_enabled() function.

    # * Verify returns false by default
    def test_returns_false_by_default(self, isolate_config):
        # Default config has dev_mode=False.
        reset_dev_mode_cache()
        assert is_dev_mode_enabled() is False

    # * Verify returns true when enabled
    def test_returns_true_when_enabled(self, dev_mode_enabled):
        # Returns True when dev_mode is enabled in config.
        reset_dev_mode_cache()
        assert is_dev_mode_enabled() is True

    # * Verify caches global result
    def test_caches_global_result(self, isolate_config):
        # Global lookups are cached after first call.
        reset_dev_mode_cache()

        # patch at the source location since it's imported inside the function
        with patch("src.config.settings.settings_manager") as mock_manager:
            mock_settings = Mock()
            mock_settings.dev_mode = False
            mock_manager.load.return_value = mock_settings

            # first call loads settings
            is_dev_mode_enabled()
            assert mock_manager.load.call_count == 1

            # second call uses cache
            is_dev_mode_enabled()
            assert mock_manager.load.call_count == 1

    # * Verify ctx bypasses cache
    def test_ctx_bypasses_cache(self, isolate_config):
        # When ctx is provided, always uses get_settings(ctx).
        reset_dev_mode_cache()

        mock_ctx = Mock(spec=typer.Context)
        mock_settings = Mock()
        mock_settings.dev_mode = True

        # patch at the source location since it's imported inside the function
        with patch("src.config.settings.get_settings") as mock_get:
            mock_get.return_value = mock_settings

            result = is_dev_mode_enabled(mock_ctx)

            assert result is True
            mock_get.assert_called_once_with(mock_ctx)

    # * Verify ctx does not pollute cache
    def test_ctx_does_not_pollute_cache(self, isolate_config):
        # Ctx-based lookups don't affect cached global value.
        reset_dev_mode_cache()

        # set up ctx w/ dev_mode=True
        mock_ctx = Mock(spec=typer.Context)
        mock_settings = Mock()
        mock_settings.dev_mode = True

        with patch("src.config.settings.get_settings") as mock_get:
            mock_get.return_value = mock_settings
            assert is_dev_mode_enabled(mock_ctx) is True

        # global should still return False (from fixture config)
        assert is_dev_mode_enabled() is False

    # * Verify handles import error gracefully
    def test_handles_import_error_gracefully(self, isolate_config):
        # Returns False if settings import fails.
        reset_dev_mode_cache()

        with patch("src.config.settings.settings_manager") as mock_manager:
            mock_manager.load.side_effect = ImportError("settings not available")

            result = is_dev_mode_enabled()

            assert result is False

    # * Verify handles attribute error gracefully
    def test_handles_attribute_error_gracefully(self, isolate_config):
        # Returns False if settings.dev_mode doesn't exist.
        reset_dev_mode_cache()

        with patch("src.config.settings.settings_manager") as mock_manager:
            mock_manager.load.side_effect = AttributeError("no dev_mode")

            result = is_dev_mode_enabled()

            assert result is False


# * Tests for reset_dev_mode_cache() function


class TestResetDevModeCache:
    # Tests for reset_dev_mode_cache() function.

    # * Verify reset clears cache
    def test_reset_clears_cache(self, isolate_config):
        # reset_dev_mode_cache() clears the cached value.
        # prime the cache
        is_dev_mode_enabled()

        with patch("src.config.settings.settings_manager") as mock_manager:
            mock_settings = Mock()
            mock_settings.dev_mode = True
            mock_manager.load.return_value = mock_settings

            # reset & verify re-fetch happens
            reset_dev_mode_cache()
            result = is_dev_mode_enabled()

            mock_manager.load.assert_called_once()
            assert result is True

    # * Verify reset allows different value
    def test_reset_allows_different_value(self, isolate_config, dev_mode_enabled):
        # After reset, new value from settings is returned.
        # first read w/ dev_mode=True
        reset_dev_mode_cache()
        assert is_dev_mode_enabled() is True

        # simulate config change (dev_mode -> False)
        import json

        config_file = isolate_config / ".loom" / "config.json"
        with open(config_file, "r") as f:
            config_data = json.load(f)
        config_data["dev_mode"] = False
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        # reset settings_manager cache too
        from src.config.settings import settings_manager

        settings_manager._settings = None

        # reset dev_mode cache & verify new value
        reset_dev_mode_cache()
        assert is_dev_mode_enabled() is False
