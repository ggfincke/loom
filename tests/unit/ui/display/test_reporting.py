# tests/unit/ui/display/test_reporting.py
# Unit tests for reporting utilities

import pytest
from unittest.mock import patch, MagicMock


class TestPrintSuccessLine:
    """Tests for _print_success_line() helper."""

    def test_prints_with_path(self):
        """With path, should print 4 elements."""
        with patch("src.ui.display.reporting.console") as mock_console:
            from src.ui.display.reporting import _print_success_line

            _print_success_line("Label", "/path/to/file")
            mock_console.print.assert_called_once()
            args = mock_console.print.call_args[0]
            assert len(args) == 4  # checkmark, gradient, arrow, path

    def test_prints_without_path(self):
        """Without path, should print 2 elements."""
        with patch("src.ui.display.reporting.console") as mock_console:
            from src.ui.display.reporting import _print_success_line

            _print_success_line("Label")
            mock_console.print.assert_called_once()
            args = mock_console.print.call_args[0]
            assert len(args) == 2  # checkmark, gradient only

    def test_path_appears_in_output(self):
        """Path should appear in the print args."""
        with patch("src.ui.display.reporting.console") as mock_console:
            from src.ui.display.reporting import _print_success_line

            _print_success_line("Wrote", "/my/file.json")
            args = mock_console.print.call_args[0]
            assert "/my/file.json" in str(args[-1])
