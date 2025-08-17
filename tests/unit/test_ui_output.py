# tests/unit/test_ui_output.py
# Unit tests for UI output components including banner, progress, & reporting

import pytest
from pathlib import Path
from unittest.mock import patch, Mock

from tests.test_support.rich_capture import (
    capture_rich_output,
    extract_plain_text,
    assert_banner_displayed,
    assert_progress_indicators,
    assert_success_output,
)
from src.ui.ascii_art import show_loom_art
from src.ui.progress import setup_ui_with_progress
from src.ui.reporting import report_result
from src.config.settings import LoomSettings


# * Test banner display renders correctly w/ gradient styling
def test_banner_display_with_gradient():
    with capture_rich_output() as console:
        show_loom_art()
        assert_banner_displayed(console)


# * Test banner display w/ custom theme colors
def test_banner_display_with_custom_theme():
    custom_colors = ["#ff6b6b", "#4ecdc4", "#45b7d1"]
    with capture_rich_output() as console:
        show_loom_art(theme_colors=custom_colors)
        assert_banner_displayed(console)


# * Test progress context manager creates proper UI elements
def test_progress_setup_creates_ui_elements():
    with capture_rich_output() as console:
        with setup_ui_with_progress("Test task", total=3) as (ui, progress, task):
            # verify UI & progress objects are created
            assert ui is not None
            assert progress is not None
            assert task is not None
            assert ui.progress == progress


# * Test progress updates appear in output
def test_progress_updates_in_output():
    with capture_rich_output() as console:
        # patch UI to use our recording console
        with patch("src.ui.ui.console", console):
            with setup_ui_with_progress("Processing files", total=2) as (ui, progress, task):
                progress.update(task, description="Reading document...")
                progress.advance(task)
                progress.update(task, description="Processing content...")
                progress.advance(task)
        
        output = extract_plain_text(console)
        # check for any progress-related content (task descriptions)
        assert "Reading document" in output or "Processing content" in output


# * Test success reporting displays checkmarks & styled messages
def test_success_reporting_sections():
    with capture_rich_output() as console:
        report_result("sections", sections_path=Path("/tmp/sections.json"))
        assert_success_output(console, ["Wrote sections to", "/tmp/sections.json"])


# * Test success reporting for edits generation
def test_success_reporting_edits():
    with capture_rich_output() as console:
        report_result("edits", edits_path=Path("/tmp/edits.json"))
        assert_success_output(console, ["Wrote edits", "/tmp/edits.json"])


# * Test complete tailor workflow reporting
def test_success_reporting_tailor():
    mock_settings = Mock(spec=LoomSettings)
    mock_settings.diff_path = Path("/tmp/diff.txt")
    
    with capture_rich_output() as console:
        report_result(
            "tailor",
            settings=mock_settings,
            edits_path=Path("/tmp/edits.json"),
            output_path=Path("/tmp/output.docx")
        )
        output = extract_plain_text(console)
        assert "Complete tailoring finished" in output
        assert "/tmp/edits.json" in output
        assert "/tmp/output.docx" in output


# * Test apply command reporting w/ formatting preservation
def test_success_reporting_apply_with_formatting():
    mock_settings = Mock(spec=LoomSettings)
    mock_settings.diff_path = Path("/tmp/diff.txt")
    
    with capture_rich_output() as console:
        report_result(
            "apply",
            settings=mock_settings,
            output_path=Path("/tmp/output.docx"),
            preserve_formatting=True,
            preserve_mode="smart"
        )
        output = extract_plain_text(console)
        assert "Wrote DOCX" in output
        assert "formatting preserved via smart mode" in output


# * Test apply command reporting w/ plain text output
def test_success_reporting_apply_plain_text():
    mock_settings = Mock(spec=LoomSettings)
    mock_settings.diff_path = Path("/tmp/diff.txt")
    
    with capture_rich_output() as console:
        report_result(
            "apply",
            settings=mock_settings,
            output_path=Path("/tmp/output.txt"),
            preserve_formatting=False
        )
        output = extract_plain_text(console)
        assert "Wrote text" in output


# * Test plan command reporting
def test_success_reporting_plan():
    mock_settings = Mock(spec=LoomSettings)
    mock_settings.plan_path = Path("/tmp/plan.json")
    
    with capture_rich_output() as console:
        report_result(
            "plan",
            settings=mock_settings,
            edits_path=Path("/tmp/edits.json")
        )
        assert_success_output(console, ["Wrote edits", "/tmp/edits.json"])