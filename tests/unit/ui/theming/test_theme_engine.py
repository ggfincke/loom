# tests/unit/ui/theming/test_theme_engine.py
# Unit tests for theme engine functionality

import pytest
from unittest.mock import patch, MagicMock

from src.ui.theming.theme_engine import (
    LoomColors,
    reset_color_cache,
    get_active_theme,
    _get_current_theme_name,
    _LazyColorDescriptor,
)


class TestLoomColorsLazyLoading:

    # * Test LoomColors has expected attributes
    def test_loomcolors_has_expected_attributes(self):
        # dynamic colors (lazy-loaded)
        assert hasattr(LoomColors, "ACCENT_PRIMARY")
        assert hasattr(LoomColors, "ACCENT_SECONDARY")
        assert hasattr(LoomColors, "ACCENT_DEEP")
        assert hasattr(LoomColors, "ARROW")

        # static colors
        assert hasattr(LoomColors, "SUCCESS_BRIGHT")
        assert hasattr(LoomColors, "WARNING")
        assert hasattr(LoomColors, "ERROR")

    # * Test dynamic colors return valid hex strings
    def test_dynamic_colors_return_hex_strings(self):
        reset_color_cache()

        accent = LoomColors.ACCENT_PRIMARY
        assert isinstance(accent, str)
        assert accent.startswith("#")
        assert len(accent) == 7  # #RRGGBB format

    # * Test static colors are unchanged
    def test_static_colors_unchanged(self):
        assert LoomColors.SUCCESS_BRIGHT == "#10b981"
        assert LoomColors.SUCCESS_MEDIUM == "#059669"
        assert LoomColors.WARNING == "#ffaa00"
        assert LoomColors.ERROR == "#ff4444"

    # * Test lazy loading caches values
    def test_lazy_loading_caches_values(self):
        reset_color_cache()

        # access twice - should return same cached value
        first_access = LoomColors.ACCENT_PRIMARY
        second_access = LoomColors.ACCENT_PRIMARY

        assert first_access == second_access

    # * Test reset_color_cache clears cache
    def test_reset_color_cache_clears_cache(self):
        # access to populate cache
        _ = LoomColors.ACCENT_PRIMARY

        # reset cache
        reset_color_cache()

        # verify descriptor cache is cleared (access via __dict__ to get descriptor)
        desc = LoomColors.__dict__["ACCENT_PRIMARY"]
        assert desc._cached_value is None
        assert desc._cached_theme is None


class TestLazyColorDescriptor:

    # * Test descriptor initialization
    def test_descriptor_initialization(self):
        desc = _LazyColorDescriptor(0)
        assert desc._index == 0
        assert desc._cached_theme is None
        assert desc._cached_value is None

    # * Test descriptor reset method
    def test_descriptor_reset_method(self):
        desc = _LazyColorDescriptor(0)
        desc._cached_theme = "test_theme"
        desc._cached_value = "#ffffff"

        desc.reset()

        assert desc._cached_theme is None
        assert desc._cached_value is None

    # * Test descriptor uses correct index
    def test_descriptor_uses_correct_index(self):
        reset_color_cache()

        theme_colors = get_active_theme()

        # ACCENT_PRIMARY uses index 0
        assert LoomColors.ACCENT_PRIMARY == theme_colors[0]

        # ACCENT_SECONDARY uses index 2
        assert LoomColors.ACCENT_SECONDARY == theme_colors[2]

        # ACCENT_DEEP uses index 4
        assert LoomColors.ACCENT_DEEP == theme_colors[4]


class TestThemeNameHelper:

    # * Test _get_current_theme_name returns string
    def test_get_current_theme_name_returns_string(self):
        result = _get_current_theme_name()
        assert isinstance(result, str)
        assert len(result) > 0

    # * Test _get_current_theme_name fallback when settings unavailable
    def test_get_current_theme_name_fallback(self):
        with patch(
            "src.ui.theming.theme_engine._get_settings_manager", return_value=None
        ):
            result = _get_current_theme_name()
            assert result == "deep_blue"


class TestThemeChangeInvalidation:

    # * Test cache invalidates when theme changes
    def test_cache_invalidates_on_theme_change(self):
        reset_color_cache()

        # get initial value
        initial = LoomColors.ACCENT_PRIMARY
        desc = LoomColors.__dict__["ACCENT_PRIMARY"]
        initial_theme = desc._cached_theme

        # mock theme name change
        with patch(
            "src.ui.theming.theme_engine._get_current_theme_name",
            return_value="different_theme",
        ):
            with patch(
                "src.ui.theming.theme_engine.get_active_theme",
                return_value=["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF"],
            ):
                # access again - should re-fetch due to theme change
                new_value = LoomColors.ACCENT_PRIMARY

                # value should come from mocked theme
                assert new_value == "#FF0000"
                assert desc._cached_theme == "different_theme"
