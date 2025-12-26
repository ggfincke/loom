# tests/unit/ui/theming/test_styled_helpers.py
# Unit tests for pre-composed styling helpers

import pytest

from src.ui.theming.styled_helpers import (
    styled_success_line,
    styled_setting_line,
    styled_provider_line,
    format_setting_value,
)


class TestStyledSuccessLine:
    """Tests for styled_success_line() helper."""

    def test_returns_list(self):
        """Result should be a list."""
        result = styled_success_line("Test")
        assert isinstance(result, list)

    def test_without_value_has_two_elements(self):
        """Without value, should have checkmark + gradient."""
        result = styled_success_line("Label")
        assert len(result) == 2

    def test_with_value_has_four_elements(self):
        """With value, should have checkmark + gradient + arrow + value."""
        result = styled_success_line("Label", "value")
        assert len(result) == 4

    def test_value_included_in_result(self):
        """The value string should appear in result."""
        result = styled_success_line("Label", "my_path")
        assert "my_path" in result


class TestStyledSettingLine:
    """Tests for styled_setting_line() helper."""

    def test_returns_list(self):
        """Result should be a list."""
        result = styled_setting_line("key", "value")
        assert isinstance(result, list)

    def test_has_four_elements(self):
        """Should have bullet + key + arrow + value."""
        result = styled_setting_line("key", "value")
        assert len(result) == 4

    def test_key_in_result(self):
        """Key should appear in result with bold styling."""
        result = styled_setting_line("my_key", "value")
        assert any("my_key" in str(item) for item in result)

    def test_value_in_result(self):
        """Value should appear in result."""
        result = styled_setting_line("key", "my_value")
        assert "my_value" in result


class TestStyledProviderLine:
    """Tests for styled_provider_line() helper."""

    def test_returns_list(self):
        """Result should be a list."""
        result = styled_provider_line("OPENAI", "[green]ok[/]", "Available")
        assert isinstance(result, list)

    def test_has_three_elements(self):
        """Should have provider + status_icon + status_text."""
        result = styled_provider_line("OPENAI", "X", "Unavailable")
        assert len(result) == 3


class TestFormatSettingValue:
    """Tests for format_setting_value() helper."""

    def test_string_quoted(self):
        """String values should be quoted."""
        result = format_setting_value("hello")
        assert '"hello"' in result

    def test_string_has_accent_styling(self):
        """String values should have loom.accent2 styling."""
        result = format_setting_value("test")
        assert "loom.accent2" in result

    def test_bool_lowercase_true(self):
        """Boolean True should be lowercase 'true'."""
        result = format_setting_value(True)
        assert "true" in result
        assert "True" not in result

    def test_bool_lowercase_false(self):
        """Boolean False should be lowercase 'false'."""
        result = format_setting_value(False)
        assert "false" in result
        assert "False" not in result

    def test_integer(self):
        """Integer should be formatted as-is."""
        result = format_setting_value(42)
        assert "42" in result

    def test_float(self):
        """Float should be formatted as-is."""
        result = format_setting_value(0.7)
        assert "0.7" in result

    def test_dict_json_serialized(self):
        """Dict should be JSON-serialized."""
        result = format_setting_value({"a": 1})
        # JSON format includes quotes around keys
        assert "a" in result

    def test_list_json_serialized(self):
        """List should be JSON-serialized."""
        result = format_setting_value([1, 2, 3])
        assert "1" in result and "2" in result and "3" in result
