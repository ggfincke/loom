# tests/unit/test_validation_interactive.py
# Tests for interactive validation strategy prompts & user choice handling

import pytest
from unittest.mock import Mock, patch
import sys

from tests.test_support.rich_capture import (
    MockUI,
    capture_rich_output,
    extract_plain_text,
)

from src.core.validation import (
    AskStrategy,
    RetryStrategy,
    ManualStrategy,
    FailSoftStrategy,
    ModelRetryStrategy,
    ValidationOutcome,
    ValidationError,
)
from src.config.settings import LoomSettings


@pytest.fixture
def mock_settings():
    settings = Mock(spec=LoomSettings)
    settings.edits_path = "/tmp/edits.json"
    settings.diff_path = Mock()
    settings.diff_path.exists.return_value = True
    settings.diff_path.__str__ = Mock(return_value="/tmp/diff.txt")
    settings.plan_path = Mock()
    settings.plan_path.exists.return_value = True
    settings.plan_path.__str__ = Mock(return_value="/tmp/plan.json")
    return settings


# * Test AskStrategy prompts user w/ validation choices
def test_ask_strategy_soft_fail_choice(mock_settings):
    warnings = ["Invalid edit format", "Missing required field"]
    mock_ui = MockUI(responses=["s"])
    strategy = AskStrategy()

    # patch isatty to simulate interactive environment
    with patch("sys.stdin.isatty", return_value=True):
        with pytest.raises(SystemExit):
            strategy.handle(warnings, mock_ui, mock_settings)

    # verify correct prompt was shown
    prompts = mock_ui.get_prompts()
    assert len(prompts) == 1
    assert "oft-fail" in prompts[0]
    assert "ard-fail" in prompts[0]
    assert "anual" in prompts[0]


# * Test AskStrategy w/ retry choice
def test_ask_strategy_retry_choice():
    warnings = ["Validation error"]
    mock_ui = MockUI(responses=["r"])
    strategy = AskStrategy()

    with patch("sys.stdin.isatty", return_value=True):
        result = strategy.handle(warnings, mock_ui)

    assert isinstance(result, ValidationOutcome)
    assert result.success is False
    assert result.should_continue is True
    assert result.value == warnings


# * Test AskStrategy w/ manual choice
def test_ask_strategy_manual_choice():
    warnings = ["Manual intervention needed"]
    mock_ui = MockUI(responses=["m"])
    strategy = AskStrategy()

    with patch("sys.stdin.isatty", return_value=True):
        result = strategy.handle(warnings, mock_ui)

    assert isinstance(result, ValidationOutcome)
    assert result.success is False
    assert result.should_continue is False


# * Test AskStrategy w/ invalid choice then valid choice
def test_ask_strategy_invalid_then_valid_choice():
    warnings = ["Test warning"]
    mock_ui = MockUI(responses=["invalid", "r"])
    strategy = AskStrategy()

    with patch("sys.stdin.isatty", return_value=True):
        result = strategy.handle(warnings, mock_ui)

    # should have prompted twice
    prompts = mock_ui.get_prompts()
    assert len(prompts) == 2
    assert result.should_continue is True


# * Test AskStrategy in non-interactive environment
def test_ask_strategy_non_interactive():
    warnings = ["Error in non-interactive mode"]
    mock_ui = MockUI()
    strategy = AskStrategy()

    with patch("sys.stdin.isatty", return_value=False):
        with pytest.raises(ValidationError) as exc_info:
            strategy.handle(warnings, mock_ui)

        assert "ask not possible - non-interactive" in str(exc_info.value)
        assert not exc_info.value.recoverable


# * Test ModelRetryStrategy prompts w/ model selection
def test_model_retry_strategy_valid_selection():
    warnings = ["Model performance issues"]
    mock_ui = MockUI(responses=["2"])  # Select gpt-5-mini
    strategy = ModelRetryStrategy()

    with patch("sys.stdin.isatty", return_value=True):
        result = strategy.handle(warnings, mock_ui)

    # verify model selection prompt
    prompts = mock_ui.get_prompts()
    assert len(prompts) == 1
    assert "Enter model number" in prompts[0]

    # should return retry w/ new model
    assert result.should_continue is True
    assert result.value == "gpt-5-mini"


# * Test ModelRetryStrategy w/ model name input
def test_model_retry_strategy_model_name():
    warnings = ["Model issues"]
    mock_ui = MockUI(responses=["gpt-4o"])
    strategy = ModelRetryStrategy()

    with patch("sys.stdin.isatty", return_value=True):
        result = strategy.handle(warnings, mock_ui)

    assert result.value == "gpt-4o"
    assert result.should_continue is True


# * Test ModelRetryStrategy w/ invalid selection then valid
def test_model_retry_strategy_invalid_then_valid():
    warnings = ["Model error"]
    mock_ui = MockUI(responses=["99", "1"])  # Invalid then GPT-5
    strategy = ModelRetryStrategy()

    with patch("sys.stdin.isatty", return_value=True):
        result = strategy.handle(warnings, mock_ui)

    # should prompt twice
    prompts = mock_ui.get_prompts()
    assert len(prompts) == 2
    assert result.value == "gpt-5"


# * Test ModelRetryStrategy in non-interactive environment
def test_model_retry_strategy_non_interactive():
    warnings = ["Model change needed"]
    mock_ui = MockUI()
    strategy = ModelRetryStrategy()

    with patch("sys.stdin.isatty", return_value=False):
        with pytest.raises(ValidationError) as exc_info:
            strategy.handle(warnings, mock_ui)

        assert "Model change not available" in str(exc_info.value)


# * Test ManualStrategy in non-interactive mode
def test_manual_strategy_non_interactive():
    warnings = ["Manual fix required"]
    mock_ui = MockUI()
    strategy = ManualStrategy()

    with patch("sys.stdin.isatty", return_value=False):
        with pytest.raises(ValidationError) as exc_info:
            strategy.handle(warnings, mock_ui)

        assert "Manual mode not available" in str(exc_info.value)


# * Test FailSoftStrategy displays warnings & file paths
def test_fail_soft_strategy_displays_info(mock_settings):
    warnings = ["Soft fail test", "File validation error"]
    mock_ui = MockUI()
    strategy = FailSoftStrategy()

    with pytest.raises(SystemExit):
        strategy.handle(warnings, mock_ui, mock_settings)

    # verify print calls include warnings & file paths
    print_calls = mock_ui.print_calls
    assert len(print_calls) > 0

    # flatten all print call args to check content
    all_printed = " ".join(str(call[0]) for call in print_calls)
    assert "Validation failed (soft fail)" in all_printed
    assert "edits.json" in all_printed
    assert "diff.txt" in all_printed


# * Test RetryStrategy returns correct outcome
def test_retry_strategy():
    warnings = ["Retry needed"]
    mock_ui = MockUI()
    strategy = RetryStrategy()

    result = strategy.handle(warnings, mock_ui)

    assert result.success is False
    assert result.should_continue is True
    assert result.value == warnings


# * Test interactive flow w/ Rich console recording
def test_interactive_validation_output_capture():
    warnings = ["Test validation error"]

    with capture_rich_output() as console:
        # patch the console in UI to capture output
        mock_ui = Mock()
        mock_ui.print = console.print
        mock_ui.ask.return_value = "s"
        mock_ui.input_mode.return_value.__enter__ = Mock()
        mock_ui.input_mode.return_value.__exit__ = Mock()

        strategy = AskStrategy()

        # patch isatty for interactive environment
        with patch("sys.stdin.isatty", return_value=True):
            # this will exit via FailSoftStrategy
            with pytest.raises(SystemExit):
                strategy.handle(warnings, mock_ui)

        output = extract_plain_text(console)
        assert "Validation errors found" in output
        assert "Test validation error" in output
