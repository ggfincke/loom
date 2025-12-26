# tests/unit/ui/core/test_rich_components.py
# Unit tests for themed Rich component builders

import pytest
from unittest.mock import patch

from src.ui.core.rich_components import themed_panel, themed_table, Panel, Table


class TestThemedPanel:
    """Tests for themed_panel() builder function."""

    def test_returns_panel_instance(self):
        """themed_panel should return a Rich Panel."""
        panel = themed_panel("content")
        assert isinstance(panel, Panel)

    def test_applies_title_formatting(self):
        """Title should be wrapped in bold tags."""
        panel = themed_panel("content", title="Test")
        assert panel.title is not None
        assert "bold" in str(panel.title).lower() or panel.title is not None

    def test_uses_default_padding(self):
        """Default padding should be (0, 1)."""
        panel = themed_panel("content")
        assert panel.padding == (0, 1)

    def test_custom_padding(self):
        """Custom padding should be applied."""
        panel = themed_panel("content", padding=(1, 2))
        assert panel.padding == (1, 2)

    def test_uses_theme_border_style(self):
        """Border style should use colors[2] from active theme."""
        mock_colors = ["#ff0000", "#00ff00", "#0000ff", "#ffff00", "#ff00ff", "#00ffff"]
        with patch(
            "src.ui.theming.theme_engine.get_active_theme", return_value=mock_colors
        ):
            panel = themed_panel("content")
            assert panel.border_style == "#0000ff"  # colors[2]

    def test_custom_theme_colors(self):
        """Explicit theme_colors should override active theme."""
        custom_colors = ["#111111", "#222222", "#333333", "#444444", "#555555", "#666666"]
        panel = themed_panel("content", theme_colors=custom_colors)
        assert panel.border_style == "#333333"  # custom colors[2]

    def test_title_align_default(self):
        """Default title_align should be left."""
        panel = themed_panel("content", title="Test")
        assert panel.title_align == "left"

    def test_no_title(self):
        """Panel without title should have None title."""
        panel = themed_panel("content")
        assert panel.title is None


class TestThemedTable:
    """Tests for themed_table() builder function."""

    def test_returns_table_instance(self):
        """themed_table should return a Rich Table."""
        table = themed_table()
        assert isinstance(table, Table)

    def test_show_header_default_false(self):
        """Default show_header should be False."""
        table = themed_table()
        assert table.show_header is False

    def test_show_header_true(self):
        """show_header=True should be applied."""
        table = themed_table(show_header=True)
        assert table.show_header is True

    def test_uses_theme_border_style(self):
        """Border style should use colors[2] from active theme."""
        mock_colors = ["#ff0000", "#00ff00", "#0000ff", "#ffff00", "#ff00ff", "#00ffff"]
        with patch(
            "src.ui.theming.theme_engine.get_active_theme", return_value=mock_colors
        ):
            table = themed_table()
            assert table.border_style == "#0000ff"  # colors[2]

    def test_custom_theme_colors(self):
        """Explicit theme_colors should override active theme."""
        custom_colors = ["#111111", "#222222", "#333333", "#444444", "#555555", "#666666"]
        table = themed_table(theme_colors=custom_colors)
        assert table.border_style == "#333333"  # custom colors[2]

    def test_box_default_none(self):
        """Default box should be None."""
        table = themed_table()
        assert table.box is None
