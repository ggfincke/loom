# tests/unit/core/test_validation.py
# Unit tests for validation logic w/ bounds checking & strategy pattern

import pytest
import json
import sys
from unittest.mock import patch, MagicMock
from src.core.validation import (
    validate_edits,
    ValidationOutcome,
    ValidationStrategy,
    AskStrategy,
    RetryStrategy,
    ManualStrategy,
    FailSoftStrategy,
    FailHardStrategy,
    ModelRetryStrategy,
    validate,
)
from src.cli.validation_handlers import handle_validation_error
from src.loom_io.latex_handler import (
    validate_latex_compilation,
    validate_basic_latex_syntax,
)
from src.core.constants import RiskLevel, ValidationPolicy
from src.core.exceptions import ValidationError
from src.loom_io.types import Lines


# * Fixtures for validation testing


@pytest.fixture
def sample_resume_lines() -> Lines:
    # standard resume lines for validation testing
    return {
        1: "John Doe",
        2: "Software Engineer",
        3: "",
        4: "SUMMARY",
        5: "Experienced developer",
        6: "",
        7: "SKILLS",
        8: "• Python, JavaScript",
        9: "• Docker, AWS",
        10: "",
    }


@pytest.fixture
def valid_ops():
    # collection of valid edit operations
    return [
        {"op": "replace_line", "line": 5, "text": "Senior developer"},
        {
            "op": "replace_range",
            "start": 8,
            "end": 9,
            "text": "• Python, Go\n• Kubernetes, AWS",
        },
        {"op": "insert_after", "line": 9, "text": "• Machine Learning"},
        {"op": "delete_range", "start": 6, "end": 6},
    ]


@pytest.fixture
def invalid_ops():
    # collection of invalid edit operations for testing error detection
    return [
        # missing required fields
        {"op": "replace_line"},
        {"op": "replace_range", "start": 1},
        {"op": "insert_after", "text": "test"},
        {"op": "delete_range", "end": 5},
        # invalid types
        {"op": "replace_line", "line": "not_int", "text": "test"},
        {"op": "replace_range", "start": 1, "end": 2, "text": 123},
        {"op": "insert_after", "line": 1.5, "text": "test"},
        # invalid ranges
        {"op": "replace_line", "line": 0, "text": "test"},
        {"op": "replace_range", "start": 5, "end": 3, "text": "test"},
        {"op": "delete_range", "start": -1, "end": 5},
        # out of bounds
        {"op": "replace_line", "line": 99, "text": "test"},
        {"op": "insert_after", "line": 99, "text": "test"},
        {"op": "delete_range", "start": 99, "end": 100},
        # newline in replace_line
        {"op": "replace_line", "line": 5, "text": "line 1\nline 2"},
        # unknown operation
        {"op": "unknown_op", "line": 1, "text": "test"},
    ]


# * Test validate_edits function


class TestValidateEdits:

    @pytest.mark.parametrize(
        "risk_level", [RiskLevel.LOW, RiskLevel.MED, RiskLevel.HIGH, RiskLevel.STRICT]
    )
    # * Test valid edits produce no warnings across all risk levels
    def test_valid_edits_no_warnings(self, sample_resume_lines, valid_ops, risk_level):
        edits = {"ops": valid_ops}
        warnings = validate_edits(edits, sample_resume_lines, risk_level)
        assert warnings == []

    # * Test missing 'ops' field produces warning
    def test_missing_ops_field(self, sample_resume_lines):
        edits = {"meta": "data"}
        warnings = validate_edits(edits, sample_resume_lines, RiskLevel.LOW)
        assert len(warnings) == 1
        assert "Missing 'ops' field" in warnings[0]

    # * Test non-list 'ops' field produces warning
    def test_ops_not_list(self, sample_resume_lines):
        edits = {"ops": "not_a_list"}
        warnings = validate_edits(edits, sample_resume_lines, RiskLevel.LOW)
        assert len(warnings) == 1
        assert "'ops' field must be a list" in warnings[0]

    # * Test empty ops list produces warning
    def test_empty_ops_list(self, sample_resume_lines):
        edits = {"ops": []}
        warnings = validate_edits(edits, sample_resume_lines, RiskLevel.LOW)
        assert len(warnings) == 1
        assert "'ops' list is empty" in warnings[0]

    @pytest.mark.parametrize(
        "invalid_op,expected_field",
        [
            ({"op": "replace_line"}, "line"),  # missing line
            ({"op": "replace_line", "line": 5}, "text"),  # missing text
            ({"op": "replace_range", "start": 1}, "end"),  # missing end
            ({"op": "insert_after", "text": "test"}, "line"),  # missing line
            ({"op": "delete_range", "end": 5}, "start"),  # missing start
        ],
    )
    # * Test operations missing required fields produce warnings
    def test_missing_required_fields(
        self, sample_resume_lines, invalid_op, expected_field
    ):
        edits = {"ops": [invalid_op]}
        warnings = validate_edits(edits, sample_resume_lines, RiskLevel.LOW)
        assert len(warnings) >= 1
        assert any("missing" in w and expected_field in w for w in warnings)

    @pytest.mark.parametrize(
        "invalid_op,expected_error",
        [
            (
                {"op": "replace_line", "line": "string", "text": "test"},
                "'line' must be integer",
            ),
            (
                {"op": "replace_line", "line": 0, "text": "test"},
                "'line' must be integer >= 1",
            ),
            (
                {"op": "replace_range", "start": "1", "end": 2, "text": "test"},
                "start and end must be integers",
            ),
            (
                {"op": "replace_range", "start": 5, "end": 3, "text": "test"},
                "invalid range 5-3",
            ),
        ],
    )
    # * Test invalid field types & values produce specific warnings
    def test_invalid_field_types_and_values(
        self, sample_resume_lines, invalid_op, expected_error
    ):
        edits = {"ops": [invalid_op]}
        warnings = validate_edits(edits, sample_resume_lines, RiskLevel.LOW)
        assert len(warnings) >= 1
        assert any(expected_error in w for w in warnings)

    # * Test line numbers outside resume bounds produce warnings
    def test_out_of_bounds_line_numbers(self, sample_resume_lines):
        out_of_bounds_ops = [
            {"op": "replace_line", "line": 99, "text": "test"},
            {"op": "replace_range", "start": 1, "end": 99, "text": "test"},
            {"op": "insert_after", "line": 99, "text": "test"},
            {"op": "delete_range", "start": 99, "end": 100},
        ]

        edits = {"ops": out_of_bounds_ops}
        warnings = validate_edits(edits, sample_resume_lines, RiskLevel.LOW)

        # should have warnings for all out of bounds operations
        assert len(warnings) >= 4
        assert any("not in resume bounds" in w for w in warnings)

    # * Test newline in replace_line text produces warning
    def test_newline_in_replace_line_text(self, sample_resume_lines):
        invalid_op = {"op": "replace_line", "line": 5, "text": "line 1\nline 2"}
        edits = {"ops": [invalid_op]}
        warnings = validate_edits(edits, sample_resume_lines, RiskLevel.LOW)

        assert len(warnings) >= 1
        assert any(
            "contains newline" in w and "use replace_range" in w for w in warnings
        )

    # * Test duplicate operations on same line produce warnings
    def test_duplicate_line_operations(self, sample_resume_lines):
        duplicate_ops = [
            {"op": "replace_line", "line": 5, "text": "first"},
            {"op": "replace_line", "line": 5, "text": "second"},
        ]

        edits = {"ops": duplicate_ops}
        warnings = validate_edits(edits, sample_resume_lines, RiskLevel.LOW)

        assert len(warnings) >= 1
        assert any("duplicate operation" in w for w in warnings)

    # * Test replace_range line count mismatch behavior across risk levels
    def test_replace_range_line_count_mismatch_warnings(self, sample_resume_lines):
        mismatch_op = {
            "op": "replace_range",
            "start": 8,
            "end": 9,  # 2 lines
            "text": "single line",  # 1 line
        }

        # test different risk levels
        for risk_level in [
            RiskLevel.LOW,
            RiskLevel.MED,
            RiskLevel.HIGH,
            RiskLevel.STRICT,
        ]:
            edits = {"ops": [mismatch_op]}
            warnings = validate_edits(edits, sample_resume_lines, risk_level)

            mismatch_warnings = [w for w in warnings if "line count mismatch" in w]
            assert len(mismatch_warnings) >= 1

            if risk_level in [RiskLevel.MED, RiskLevel.HIGH, RiskLevel.STRICT]:
                assert any("will cause line collisions" in w for w in mismatch_warnings)

    # * Test insert_after on line that gets deleted produces warning
    def test_insert_after_deleted_line(self, sample_resume_lines):
        conflicting_ops = [
            {"op": "delete_range", "start": 5, "end": 7},
            {"op": "insert_after", "line": 6, "text": "test"},  # line 6 gets deleted
        ]

        edits = {"ops": conflicting_ops}
        warnings = validate_edits(edits, sample_resume_lines, RiskLevel.LOW)

        assert len(warnings) >= 1
        assert any("insert_after on line" in w and "deleted by" in w for w in warnings)

    # * Test overlapping delete_range & replace_range operations
    def test_overlapping_delete_and_replace_ranges(self, sample_resume_lines):
        overlapping_ops = [
            {"op": "replace_range", "start": 5, "end": 7, "text": "replacement"},
            {"op": "delete_range", "start": 6, "end": 8},  # overlaps w/ replace_range
        ]

        edits = {"ops": overlapping_ops}
        warnings = validate_edits(edits, sample_resume_lines, RiskLevel.LOW)

        assert len(warnings) >= 1
        assert any("overlaps a replace_range" in w for w in warnings)

    # * Test multiple insert_after operations on same line
    def test_multiple_insert_after_same_line(self, sample_resume_lines):
        duplicate_inserts = [
            {"op": "insert_after", "line": 5, "text": "first insert"},
            {"op": "insert_after", "line": 5, "text": "second insert"},
        ]

        edits = {"ops": duplicate_inserts}
        warnings = validate_edits(edits, sample_resume_lines, RiskLevel.LOW)

        assert len(warnings) >= 1
        assert any("multiple insert_after" in w for w in warnings)

    # * Test unknown operation type produces warning
    def test_unknown_operation_type(self, sample_resume_lines):
        unknown_op = {"op": "unknown_operation", "line": 1, "text": "test"}
        edits = {"ops": [unknown_op]}
        warnings = validate_edits(edits, sample_resume_lines, RiskLevel.LOW)

        assert len(warnings) >= 1
        assert any("unknown operation type" in w for w in warnings)


# * Test validation strategy pattern


class TestValidationStrategies:

    # * Test AskStrategy raises error in non-interactive environment
    def test_ask_strategy_non_interactive(self):
        strategy = AskStrategy()
        mock_ui = MagicMock()

        with patch("sys.stdin.isatty", return_value=False):
            with pytest.raises(ValidationError) as exc_info:
                strategy.handle(["test warning"], mock_ui)

            assert not exc_info.value.recoverable
            assert "non-interactive" in str(exc_info.value)

    # * Test RetryStrategy returns should_continue=True
    def test_retry_strategy(self):
        strategy = RetryStrategy()
        mock_ui = MagicMock()

        outcome = strategy.handle(["test warning"], mock_ui)

        assert not outcome.success
        assert outcome.should_continue

    # * Test ManualStrategy raises error in non-interactive environment
    def test_manual_strategy_non_interactive(self):
        strategy = ManualStrategy()
        mock_ui = MagicMock()

        with patch("sys.stdin.isatty", return_value=False):
            with pytest.raises(ValidationError) as exc_info:
                strategy.handle(["test warning"], mock_ui)

            assert not exc_info.value.recoverable
            assert "non-interactive" in str(exc_info.value)

    # * Test ManualStrategy returns control in interactive environment
    def test_manual_strategy_interactive(self):
        strategy = ManualStrategy()
        mock_ui = MagicMock()

        with patch("sys.stdin.isatty", return_value=True):
            outcome = strategy.handle(["test warning"], mock_ui)

            assert not outcome.success
            assert not outcome.should_continue

    # * Test FailSoftStrategy exits w/ code 0
    def test_fail_soft_strategy(self):
        strategy = FailSoftStrategy()
        mock_ui = MagicMock()
        mock_settings = MagicMock()
        mock_settings.edits_path = "/path/to/edits.json"
        mock_settings.diff_path.exists.return_value = True
        mock_settings.plan_path.exists.return_value = False

        with pytest.raises(SystemExit) as exc_info:
            strategy.handle(["test warning"], mock_ui, mock_settings)

        assert exc_info.value.code == 0
        mock_ui.print.assert_called()

    # * Test FailHardStrategy deletes files & exits w/ code 1
    def test_fail_hard_strategy_cleanup(self):
        strategy = FailHardStrategy()
        mock_ui = MagicMock()
        mock_settings = MagicMock()

        # mock file paths that exist
        mock_edits_path = MagicMock()
        mock_edits_path.exists.return_value = True
        mock_settings.edits_path = mock_edits_path

        mock_diff_path = MagicMock()
        mock_diff_path.exists.return_value = False
        mock_settings.diff_path = mock_diff_path

        mock_plan_path = MagicMock()
        mock_plan_path.exists.return_value = True
        mock_settings.plan_path = mock_plan_path

        mock_warnings_path = MagicMock()
        mock_warnings_path.exists.return_value = True
        mock_settings.warnings_path = mock_warnings_path

        with pytest.raises(SystemExit) as exc_info:
            strategy.handle(["test warning"], mock_ui, mock_settings)

        assert exc_info.value.code == 1
        mock_edits_path.unlink.assert_called_once()
        mock_plan_path.unlink.assert_called_once()
        mock_warnings_path.unlink.assert_called_once()

    @patch("src.core.validation.settings_manager")
    # * Test ModelRetryStrategy updates model & returns should_continue
    def test_model_retry_strategy_interactive(self, mock_settings_manager):
        strategy = ModelRetryStrategy()
        mock_ui = MagicMock()
        mock_ui.ask.return_value = "1"  # select gpt-5

        mock_settings = MagicMock()
        mock_current_settings = MagicMock()
        mock_settings_manager.load.return_value = mock_current_settings

        with patch("sys.stdin.isatty", return_value=True):
            outcome = strategy.handle(["test warning"], mock_ui, mock_settings)

        assert not outcome.success
        assert outcome.should_continue
        assert mock_current_settings.model == "gpt-5"
        mock_settings_manager.save.assert_called_once()

    # * Test ModelRetryStrategy raises error in non-interactive environment
    def test_model_retry_strategy_non_interactive(self):
        strategy = ModelRetryStrategy()
        mock_ui = MagicMock()

        with patch("sys.stdin.isatty", return_value=False):
            with pytest.raises(ValidationError) as exc_info:
                strategy.handle(["test warning"], mock_ui)

            assert not exc_info.value.recoverable
            assert "non-interactive" in str(exc_info.value)

    @patch("src.core.validation.settings_manager")
    # * Test ModelRetryStrategy w/ invalid choice (covers lines 140-142)
    def test_model_retry_strategy_invalid_choice(self, mock_settings_manager):
        strategy = ModelRetryStrategy()
        mock_ui = MagicMock()
        mock_ui.ask.side_effect = ["invalid", "1"]  # first invalid, then valid choice

        mock_current_settings = MagicMock()
        mock_settings_manager.load.return_value = mock_current_settings

        with patch("sys.stdin.isatty", return_value=True):
            outcome = strategy.handle(["test warning"], mock_ui)

        # should have printed error message about invalid choice
        calls = [str(call) for call in mock_ui.print.call_args_list]
        invalid_choice_call = any("Invalid choice" in call for call in calls)
        assert invalid_choice_call

        # should eventually succeed
        assert not outcome.success
        assert outcome.should_continue

    # * Test FailSoftStrategy when some files don't exist (covers lines 87-90)
    def test_fail_soft_strategy_with_missing_files(self):
        strategy = FailSoftStrategy()
        mock_ui = MagicMock()
        mock_settings = MagicMock()
        mock_settings.edits_path = "/path/to/edits.json"
        mock_settings.diff_path.exists.return_value = False  # diff doesn't exist
        mock_settings.plan_path.exists.return_value = False  # plan doesn't exist

        with pytest.raises(SystemExit) as exc_info:
            strategy.handle(["test warning"], mock_ui, mock_settings)

        assert exc_info.value.code == 0
        # should still print edits path even if others don't exist
        calls = [str(call) for call in mock_ui.print.call_args_list]
        edits_mentioned = any("edits.json" in call for call in calls)
        assert edits_mentioned


# * Test validate function & handle_validation_error


class TestValidationFlow:

    # * Test validate returns success when no warnings
    def test_validate_no_warnings_success(self):
        def mock_validate_fn():
            return []

        mock_ui = MagicMock()
        outcome = validate(mock_validate_fn, ValidationPolicy.ASK, mock_ui)

        assert outcome.success

    # * Test validate calls strategy when warnings found
    def test_validate_with_warnings_calls_strategy(self):
        def mock_validate_fn():
            return ["test warning"]

        mock_strategy = MagicMock()
        mock_outcome = ValidationOutcome(success=False, should_continue=True)
        mock_strategy.handle.return_value = mock_outcome

        mock_ui = MagicMock()

        with patch("src.core.validation.AskStrategy", return_value=mock_strategy):
            outcome = validate(mock_validate_fn, ValidationPolicy.ASK, mock_ui)

        assert outcome == mock_outcome
        mock_strategy.handle.assert_called_once()

    # * Test handle_validation_error retry mechanism
    def test_handle_validation_error_retry_loop(self):
        call_count = 0

        def mock_validate_fn():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ["test warning"]
            return []  # success on second call

        def mock_edit_fn(warnings):
            return {"corrected": "edits"}

        mock_settings = MagicMock()
        mock_settings.loom_dir.mkdir = MagicMock()
        mock_settings.edits_path.write_text = MagicMock()

        mock_ui = MagicMock()

        result = handle_validation_error(
            mock_settings,
            mock_validate_fn,
            ValidationPolicy.RETRY,
            mock_edit_fn,
            None,
            mock_ui,
        )

        # the result should be the corrected edits dict on first successful validation
        assert result == {"corrected": "edits"}
        assert call_count == 2
        mock_settings.edits_path.write_text.assert_called_once()


# * Test LaTeX validation functions


class TestLatexValidation:

    # * Test valid LaTeX syntax
    def test_validate_basic_latex_syntax_valid(self):
        valid_latex = r"""
        \documentclass{article}
        \begin{document}
        Hello \textbf{world}!
        \end{document}
        """

        assert validate_basic_latex_syntax(valid_latex) is True

    # * Test unbalanced braces
    def test_validate_basic_latex_syntax_unbalanced_braces(self):
        invalid_latex = r"\textbf{unbalanced"
        assert validate_basic_latex_syntax(invalid_latex) is False

        invalid_latex2 = r"unbalanced}"
        assert validate_basic_latex_syntax(invalid_latex2) is False

    # * Test missing document begin/end
    def test_validate_basic_latex_syntax_missing_document_structure(self):
        invalid_latex = r"""
        \documentclass{article}
        Hello world!
        """

        assert validate_basic_latex_syntax(invalid_latex) is False

    @patch("subprocess.run")
    # * Test successful LaTeX compilation
    def test_validate_latex_compilation_success(self, mock_subprocess):
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "LaTeX compilation successful"
        mock_process.stderr = ""
        mock_subprocess.return_value = mock_process

        # mock PDF file creation
        with patch("pathlib.Path.exists", return_value=True):
            result = validate_latex_compilation(
                "\\documentclass{article}\\begin{document}Hello\\end{document}"
            )

        assert result["success"] is True
        assert result["compiler_available"] is True
        assert len(result["errors"]) == 0

    @patch("subprocess.run")
    # * Test missing LaTeX compiler
    def test_validate_latex_compilation_compiler_not_found(self, mock_subprocess):
        mock_subprocess.side_effect = FileNotFoundError()

        result = validate_latex_compilation("test content")

        assert result["success"] is False
        assert result["compiler_available"] is False
        assert "not found" in result["errors"][0]

    @patch("subprocess.run")
    # * Test LaTeX compilation failure
    def test_validate_latex_compilation_failure(self, mock_subprocess):
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stdout = "LaTeX error"
        mock_process.stderr = "! Missing control sequence inserted."
        mock_subprocess.return_value = mock_process

        # mock no PDF file created
        with patch("pathlib.Path.exists", return_value=False):
            result = validate_latex_compilation("\\invalid{latex}")

        assert result["success"] is False
        assert result["compiler_available"] is True
        assert len(result["errors"]) > 0

    @patch("subprocess.run")
    # * Test LaTeX compilation w/ warnings but success
    def test_validate_latex_compilation_with_warnings(self, mock_subprocess):
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = (
            "LaTeX Warning: Overfull \\hbox\nUnderfull \\vbox (badness 10000)"
        )
        mock_process.stderr = ""
        mock_subprocess.return_value = mock_process

        with patch("pathlib.Path.exists", return_value=True):
            result = validate_latex_compilation("valid latex")

        assert result["success"] is True
        assert len(result["warnings"]) >= 2  # should capture both warnings

    @patch("src.loom_io.latex_handler.subprocess.run")
    # * Test check_latex_availability when all compilers available
    def test_check_latex_availability_all_available(self, mock_subprocess):
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        from src.loom_io.latex_handler import check_latex_availability

        result = check_latex_availability()

        assert result["pdflatex"] is True
        assert result["xelatex"] is True
        assert result["lualatex"] is True

    @patch("src.loom_io.latex_handler.subprocess.run")
    # * Test check_latex_availability when some compilers missing
    def test_check_latex_availability_some_missing(self, mock_subprocess):
        def side_effect(cmd, **kwargs):
            if "pdflatex" in cmd:
                return MagicMock(returncode=0)
            else:
                raise FileNotFoundError()

        mock_subprocess.side_effect = side_effect

        from src.loom_io.latex_handler import check_latex_availability

        result = check_latex_availability()

        assert result["pdflatex"] is True
        assert result["xelatex"] is False
        assert result["lualatex"] is False

    # * Test validate_latex_document w/ valid syntax only
    def test_validate_latex_document_syntax_valid(self):
        from src.loom_io.latex_handler import validate_latex_document

        valid_latex = r"""
        \documentclass{article}
        \begin{document}
        Hello world!
        \end{document}
        """

        result = validate_latex_document(valid_latex, check_compilation=False)

        assert result["syntax_valid"] is True
        assert result["compilation_checked"] is False
        assert len(result["errors"]) == 0

    # * Test validate_latex_document w/ invalid syntax
    def test_validate_latex_document_syntax_invalid(self):
        from src.loom_io.latex_handler import validate_latex_document

        invalid_latex = r"\textbf{unbalanced"

        result = validate_latex_document(invalid_latex, check_compilation=False)

        assert result["syntax_valid"] is False
        assert result["compilation_checked"] is False
        assert len(result["errors"]) > 0
        assert "syntax validation failed" in result["errors"][0].lower()

    @patch("src.loom_io.latex_handler.validate_latex_compilation")
    # * Test validate_latex_document w/ compilation check
    def test_validate_latex_document_with_compilation(self, mock_validate_compilation):
        from src.loom_io.latex_handler import validate_latex_document

        mock_validate_compilation.return_value = {
            "success": True,
            "errors": [],
            "warnings": ["Some warning"],
        }

        valid_latex = r"""
        \documentclass{article}
        \begin{document}
        Hello world!
        \end{document}
        """

        result = validate_latex_document(valid_latex, check_compilation=True)

        assert result["syntax_valid"] is True
        assert result["compilation_checked"] is True
        assert len(result["warnings"]) == 1
        mock_validate_compilation.assert_called_once()

    @patch("src.loom_io.latex_handler.validate_latex_compilation")
    # * Test validate_latex_document when compilation validation raises exception
    def test_validate_latex_document_compilation_error(self, mock_validate_compilation):
        from src.loom_io.latex_handler import validate_latex_document

        mock_validate_compilation.side_effect = Exception("Compilation test failed")

        valid_latex = r"""
        \documentclass{article}
        \begin{document}
        Hello world!
        \end{document}
        """

        result = validate_latex_document(valid_latex, check_compilation=True)

        assert result["syntax_valid"] is True
        assert result["compilation_checked"] is False
        assert len(result["errors"]) > 0
        assert "Compilation validation error" in result["errors"][0]


# * Test ensure_interactive base method


class TestEnsureInteractive:

    # * Test ensure_interactive raises ValidationError when not TTY
    def test_ensure_interactive_non_tty_raises(self):
        strategy = AskStrategy()
        with patch("sys.stdin.isatty", return_value=False):
            with pytest.raises(ValidationError) as exc_info:
                strategy.ensure_interactive("Test mode", ["original warning"])

            assert not exc_info.value.recoverable
            assert "Test mode not available" in str(exc_info.value)
            assert "non-interactive" in str(exc_info.value)

    # * Test ensure_interactive preserves original warnings
    def test_ensure_interactive_preserves_warnings(self):
        strategy = AskStrategy()
        original_warnings = ["warning 1", "warning 2"]

        with patch("sys.stdin.isatty", return_value=False):
            with pytest.raises(ValidationError) as exc_info:
                strategy.ensure_interactive("Test mode", original_warnings)

            # original warnings should be preserved (prepended w/ mode-specific message)
            assert "warning 1" in str(exc_info.value)
            assert "warning 2" in str(exc_info.value)

    # * Test ensure_interactive passes when TTY available
    def test_ensure_interactive_tty_passes(self):
        strategy = AskStrategy()
        with patch("sys.stdin.isatty", return_value=True):
            # should not raise - just returns None
            result = strategy.ensure_interactive("Test mode", ["warning"])
            assert result is None

    # * Test all interactive strategies use ensure_interactive guard (parametrized)
    @pytest.mark.parametrize(
        "strategy_class,mode_name",
        [
            (AskStrategy, "Ask mode"),
            (ManualStrategy, "Manual mode"),
            (ModelRetryStrategy, "Model change"),
        ],
    )
    # * Verify interactive strategies guard tty
    def test_interactive_strategies_guard_tty(self, strategy_class, mode_name):
        strategy = strategy_class()
        mock_ui = MagicMock()

        with patch("sys.stdin.isatty", return_value=False):
            with pytest.raises(ValidationError) as exc_info:
                strategy.handle(["test warning"], mock_ui)

            # verify error mentions non-interactive (standardized format)
            error_msg = str(exc_info.value)
            assert "non-interactive" in error_msg
            assert not exc_info.value.recoverable


# * Test ModelRetryStrategy uses model source of truth


class TestModelRetrySourceOfTruth:

    # * Test model options come from ai/models.py, not hardcoded
    @patch("src.core.validation.settings_manager")
    # * Verify model options from models module
    def test_model_options_from_models_module(self, mock_settings_manager):
        from src.ai.models import OPENAI_MODELS

        strategy = ModelRetryStrategy()
        mock_ui = MagicMock()
        mock_ui.ask.return_value = "1"  # Select first option
        mock_settings_manager.load.return_value = MagicMock()

        with patch("sys.stdin.isatty", return_value=True):
            outcome = strategy.handle(["test"], mock_ui)

        # verify first model selected matches OPENAI_MODELS[0]
        assert outcome.value == OPENAI_MODELS[0]

    # * Test model options don't include Claude/Ollama models
    @patch("src.core.validation.settings_manager")
    # * Verify model options openai only
    def test_model_options_openai_only(self, mock_settings_manager):
        strategy = ModelRetryStrategy()
        mock_ui = MagicMock()

        # capture printed output
        printed_lines = []
        mock_ui.print.side_effect = lambda x="": printed_lines.append(str(x))
        mock_ui.ask.return_value = "1"
        mock_settings_manager.load.return_value = MagicMock()

        with patch("sys.stdin.isatty", return_value=True):
            strategy.handle(["test"], mock_ui)

        output = "\n".join(printed_lines)
        assert "claude" not in output.lower()
        assert "llama" not in output.lower()
        assert "gpt" in output.lower()

    # * Test all OPENAI_MODELS are available as options
    @patch("src.core.validation.settings_manager")
    # * Verify all openai models available
    def test_all_openai_models_available(self, mock_settings_manager):
        from src.ai.models import OPENAI_MODELS

        strategy = ModelRetryStrategy()
        mock_ui = MagicMock()

        # capture printed output
        printed_lines = []
        mock_ui.print.side_effect = lambda x="": printed_lines.append(str(x))
        mock_ui.ask.return_value = "1"
        mock_settings_manager.load.return_value = MagicMock()

        with patch("sys.stdin.isatty", return_value=True):
            strategy.handle(["test"], mock_ui)

        output = "\n".join(printed_lines)
        # all OpenAI models should appear in output
        for model in OPENAI_MODELS:
            assert model in output, f"Model {model} should be in options"

    # * Test numeric selection matches OPENAI_MODELS order
    @pytest.mark.parametrize(
        "choice,expected_index",
        [
            ("1", 0),
            ("2", 1),
            ("3", 2),
        ],
    )
    @patch("src.core.validation.settings_manager")
    # * Verify numeric selection order
    def test_numeric_selection_order(
        self, mock_settings_manager, choice, expected_index
    ):
        from src.ai.models import OPENAI_MODELS

        strategy = ModelRetryStrategy()
        mock_ui = MagicMock()
        mock_ui.ask.return_value = choice
        mock_settings_manager.load.return_value = MagicMock()

        with patch("sys.stdin.isatty", return_value=True):
            outcome = strategy.handle(["test"], mock_ui)

        assert outcome.value == OPENAI_MODELS[expected_index]

    # * Test direct model name input works
    @patch("src.core.validation.settings_manager")
    # * Verify direct model name input
    def test_direct_model_name_input(self, mock_settings_manager):
        from src.ai.models import OPENAI_MODELS

        strategy = ModelRetryStrategy()
        mock_ui = MagicMock()
        # use a model name directly instead of number
        mock_ui.ask.return_value = OPENAI_MODELS[2]
        mock_settings_manager.load.return_value = MagicMock()

        with patch("sys.stdin.isatty", return_value=True):
            outcome = strategy.handle(["test"], mock_ui)

        assert outcome.value == OPENAI_MODELS[2]
