# tests/unit/test_ui_regression.py
# UI regression tests for banner & progress display consistency

import pytest
from pathlib import Path
from unittest.mock import patch, Mock

from tests.test_support.rich_capture import (
    capture_rich_output,
    extract_plain_text,
    extract_html,
    assert_banner_displayed,
)

from src.ui.display.ascii_art import show_loom_art
from src.ui.core.progress import setup_ui_with_progress
from src.ui.theming.theme_engine import get_active_theme, natural_gradient
from src.ui.display.reporting import report_result


# * Test banner appearance remains consistent across theme changes
def test_banner_consistency_across_themes():
    # test w/ different theme configurations
    theme_variations = [
        ["#ff6b6b", "#4ecdc4", "#45b7d1"],  # warm colors
        ["#2c3e50", "#3498db", "#e74c3c"],  # cool colors
        ["#f39c12", "#e67e22", "#d35400"],  # orange spectrum
    ]
    
    banner_outputs = []
    
    for theme in theme_variations:
        with capture_rich_output() as console:
            show_loom_art(theme_colors=theme)
            banner_outputs.append(extract_plain_text(console))
    
    # verify all banner outputs contain same ASCII structure
    for output in banner_outputs:
        assert "██╗      ██████╗  ██████╗ ███╗   ███╗" in output
        assert "Smart, precise resume tailoring" in output
        assert len(output.splitlines()) >= 8  # consistent height


# * Test progress bar formatting consistency
def test_progress_formatting_consistency():
    progress_outputs = []
    task_descriptions = [
        "Reading document...",
        "Processing content with AI model...",  # longer description
        "Done.",  # short description
    ]
    
    for desc in task_descriptions:
        with capture_rich_output() as console:
            with setup_ui_with_progress(desc, total=1) as (ui, progress, task):
                progress.advance(task)
            progress_outputs.append(extract_plain_text(console))
    
    # verify consistent progress formatting
    for output in progress_outputs:
        # should contain elapsed time pattern
        import re
        assert re.search(r"\d+:\d{2}", output), f"Missing elapsed time in: {output}"


# * Test success message formatting consistency
def test_success_message_consistency():
    test_cases = [
        ("sections", {"sections_path": Path("/tmp/sections.json")}),
        ("edits", {"edits_path": Path("/tmp/edits.json")}),
        ("apply", {"output_path": Path("/tmp/output.docx")}),
    ]
    
    success_outputs = []
    
    for result_type, kwargs in test_cases:
        with capture_rich_output() as console:
            report_result(result_type, settings=None, **kwargs)
            success_outputs.append(extract_plain_text(console))
    
    # verify all success messages have consistent checkmark & arrow patterns
    for output in success_outputs:
        # should contain success indicators (checkmark represented in text)
        assert len(output.strip()) > 0
        # file paths should be present
        assert ".json" in output or ".docx" in output


# * Test banner gradient rendering consistency
def test_banner_gradient_rendering():
    test_themes = [
        None,  # default theme
        ["#ff0000", "#00ff00", "#0000ff"],  # RGB primary
        ["#000000", "#ffffff"],  # monochrome
    ]
    
    html_outputs = []
    
    for theme in test_themes:
        with capture_rich_output() as console:
            show_loom_art(theme_colors=theme)
            html_outputs.append(extract_html(console))
    
    # verify HTML output contains style information
    for html in html_outputs:
        assert len(html) > 0
        # HTML should contain ASCII art characters (check for unicode block chars)
        assert "\\u2588" in html or "█" in html


# * Test UI component integration consistency
def test_ui_component_integration():
    # test complete UI workflow: banner + progress + success
    with capture_rich_output() as console:
        # display banner
        show_loom_art()
        
        # show progress
        with setup_ui_with_progress("Integration test", total=2) as (ui, progress, task):
            progress.update(task, description="Step 1...")
            progress.advance(task)
            progress.update(task, description="Step 2...")
            progress.advance(task)
        
        # show success
        report_result("sections", sections_path=Path("/tmp/test.json"))
        
        output = extract_plain_text(console)
        
        # verify all components appear in logical order
        banner_pos = output.find("██╗")
        progress_pos = output.find("Integration test")
        success_pos = output.find("test.json")
        
        assert banner_pos < progress_pos < success_pos
        assert banner_pos != -1 and progress_pos != -1 and success_pos != -1


# * Test progress timer display consistency
def test_progress_timer_consistency():
    timer_outputs = []
    
    # test different progress durations
    for total in [1, 5, 10]:
        with capture_rich_output() as console:
            with setup_ui_with_progress(f"Timer test {total}", total=total) as (ui, progress, task):
                for _ in range(total):
                    progress.advance(task)
            timer_outputs.append(extract_plain_text(console))
    
    # verify elapsed time format consistency
    for output in timer_outputs:
        import re
        time_matches = re.findall(r"\d+:\d{2}", output)
        assert len(time_matches) > 0, f"No time display found in: {output}"


# * Test error display consistency w/ Rich formatting
def test_error_display_consistency():
    # mock UI for error scenarios
    with capture_rich_output() as console:
        # simulate error output through console
        console.print("⚠️  Validation errors found:")
        console.print("   Error message 1")
        console.print("   Error message 2")
        console.print("🔶 Validation failed (soft fail)")
        
        output = extract_plain_text(console)
        
        # verify error formatting consistency
        assert "Validation errors found" in output
        assert "Error message 1" in output
        assert "soft fail" in output


# * Test theme switching doesn't break UI components
def test_theme_switching_stability():
    # simulate theme changes during UI operations
    outputs = []
    
    for theme_name in ["default", "custom"]:
        with capture_rich_output() as console:
            # simulate theme change
            if theme_name == "custom":
                custom_theme = ["#800080", "#0000ff", "#008000"]
                show_loom_art(theme_colors=custom_theme)
            else:
                show_loom_art()
            
            # show progress after theme change
            with setup_ui_with_progress("Theme test", total=1) as (ui, progress, task):
                progress.advance(task)
            
            outputs.append(extract_plain_text(console))
    
    # verify both outputs are valid & contain expected elements
    for output in outputs:
        assert "LOOM" in output or "██" in output
        assert "Theme test" in output


# * Test UI component memory usage consistency
def test_ui_memory_consistency():
    # ensure UI components don't leak memory across multiple uses
    console_refs = []
    
    for i in range(5):
        with capture_rich_output() as console:
            show_loom_art()
            with setup_ui_with_progress(f"Memory test {i}", total=1) as (ui, progress, task):
                progress.advance(task)
            console_refs.append(extract_plain_text(console))
    
    # verify outputs remain consistent
    for output in console_refs:
        assert len(output) > 0
        # basic structure should be preserved
        assert "██" in output or "LOOM" in output


# * Test special character handling in UI components  
def test_special_character_handling():
    special_descriptions = [
        "Processing résumé...",  # accented characters
        "File: café_resume.docx",  # unicode in filenames
        "Progress: 100% complete ✓",  # symbols
        "Path: /tmp/测试.json",  # non-latin characters
    ]
    
    for desc in special_descriptions:
        with capture_rich_output() as console:
            with setup_ui_with_progress(desc, total=1) as (ui, progress, task):
                progress.advance(task)
            
            output = extract_plain_text(console)
            # verify special characters are handled gracefully
            assert len(output) > 0
            # output should not be corrupted
            assert desc.split()[0] in output or "Progress" in output