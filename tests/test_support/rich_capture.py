# tests/test_support/rich_capture.py
# Rich Console recording utilities for capturing & asserting CLI output

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator
from unittest.mock import patch

from src.ui.core.rich_components import Console


# * Console recording fixture for capturing Rich output in tests
@contextmanager
def capture_rich_output() -> Generator[Console, None, None]:
    from rich.theme import Theme

    # create recording console that captures all output w/ basic theme
    theme = Theme(
        {
            "loom.accent": "blue",
            "loom.accent2": "cyan",
            "progress.path": "magenta",
            "warning": "yellow",
            "error": "red",
            "progress.elapsed": "dim cyan",
            "progress.description": "white",
        }
    )
    recording_console = Console(
        record=True, width=80, height=24, force_terminal=True, theme=theme
    )

    # patch both the global console and modules that have already imported it
    patches = [
        patch("src.loom_io.console.console", recording_console),
        # these modules import console directly at module level, so need individual patches
        patch("src.ui.display.ascii_art.console", recording_console),
        patch("src.ui.display.reporting.console", recording_console),
        patch("src.ui.help.help_renderer.console", recording_console),
        patch("src.ui.diff_resolution.diff_display.console", recording_console),
        patch("src.ui.quick.quick_usage.console", recording_console),
        patch("src.ui.theming.console_theme.console", recording_console),
        patch("src.ui.theming.theme_selector.console", recording_console),
    ]

    # apply all patches
    for p in patches:
        p.start()

    try:
        yield recording_console
    finally:
        for p in patches:
            try:
                p.stop()
            except:
                pass


# * Extract plain text from Rich console recording, stripping ANSI codes
def extract_plain_text(console: Console) -> str:
    exported = console.export_text()
    # clean up extra whitespace & normalize line endings
    return "\n".join(line.rstrip() for line in exported.split("\n"))


# * Extract HTML from Rich console recording for detailed style inspection
def extract_html(console: Console) -> str:
    return console.export_html()


# * Check if banner appears in console output
def assert_banner_displayed(console: Console) -> None:
    output = extract_plain_text(console)
    # check for LOOM ASCII art patterns - use distinctive parts that will definitely match
    # Use different Unicode block chars or fallback to text content
    has_blocks = (
        "██" in output or "█" in output or "╗" in output or "LOOM" in output.upper()
    )
    assert (
        has_blocks
    ), f"Expected banner blocks not found in output: {repr(output[:200])}"
    assert "Smart, precise resume tailoring" in output


# * Check if progress indicators appear in console output
def assert_progress_indicators(console: Console, expected_steps: list[str]) -> None:
    output = extract_plain_text(console)
    for step in expected_steps:
        assert step in output, f"Expected progress step '{step}' not found in output"


# * Check if success checkmarks & styled output appear
def assert_success_output(console: Console, expected_messages: list[str]) -> None:
    output = extract_plain_text(console)
    for message in expected_messages:
        assert message in output, f"Expected success message '{message}' not found"


# * Check if error messages appear w/ proper styling
def assert_error_output(console: Console, expected_errors: list[str]) -> None:
    output = extract_plain_text(console)
    for error in expected_errors:
        assert error in output, f"Expected error message '{error}' not found"


# * Mock UI class for testing interactive scenarios
class MockUI:
    def __init__(self, responses: list[str | None] | None = None):
        self.responses = responses or []
        self.response_index = 0
        self.prompts = []
        self.print_calls = []

    def ask(self, prompt: str, *, default: str | None = "s") -> str | None:
        self.prompts.append(prompt)
        if self.response_index < len(self.responses):
            response = self.responses[self.response_index]
            self.response_index += 1
            return response
        return default

    def input(self, prompt: str = "", **kw) -> str | None:
        return self.ask(prompt, **kw)

    def print(self, *args, **kwargs) -> None:
        self.print_calls.append((args, kwargs))

    # * Mock input_mode context manager for UI interaction
    @contextmanager
    def input_mode(self):
        # simple mock that just yields without doing anything special
        yield

    # * Get all prompts that were shown to user
    def get_prompts(self) -> list[str]:
        return self.prompts

    # * Reset mock state for reuse
    def reset(self):
        self.responses = []
        self.response_index = 0
        self.prompts = []
        self.print_calls = []


# * Context manager to mock UI interactions w/ predefined responses
@contextmanager
def mock_ui_interactions(
    responses: list[str | None] | None = None,
) -> Generator[MockUI, None, None]:
    mock_ui = MockUI(responses)
    with patch("src.ui.core.ui.UI", return_value=mock_ui):
        yield mock_ui
