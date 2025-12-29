# tests/unit/cli/test_output_manager.py
# Unit tests for OutputManager implementation

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.core.output import OutputLevel, OutputInterface
from src.cli.output_manager import OutputManager


class TestOutputManagerBasics:

    # * Verify OutputManager implements protocol
    def test_implements_protocol(self):

        manager = OutputManager()
        assert isinstance(manager, OutputInterface)

    # * Verify default level is NORMAL
    def test_default_level_is_normal(self):

        manager = OutputManager()
        assert manager.get_level() == OutputLevel.NORMAL


class TestInitialize:

    # * Verify default initialization
    def test_default_initialization(self):

        manager = OutputManager()
        manager.initialize()
        assert manager.get_level() == OutputLevel.NORMAL
        assert manager.is_debug_enabled() is False
        assert manager.is_verbose_enabled() is False

    # * Verify VERBOSE level
    def test_verbose_level(self):

        manager = OutputManager()
        manager.initialize(requested_level=OutputLevel.VERBOSE)
        assert manager.get_level() == OutputLevel.VERBOSE
        assert manager.is_verbose_enabled() is True
        assert manager.is_debug_enabled() is False

    # * Verify DEBUG requires dev_mode
    def test_debug_requires_dev_mode(self):

        manager = OutputManager()
        manager.initialize(requested_level=OutputLevel.DEBUG, dev_mode=False)
        assert manager.get_level() == OutputLevel.VERBOSE

    # * Verify DEBUG w/ dev_mode
    def test_debug_with_dev_mode(self):

        manager = OutputManager()
        manager.initialize(requested_level=OutputLevel.DEBUG, dev_mode=True)
        assert manager.get_level() == OutputLevel.DEBUG
        assert manager.is_debug_enabled() is True

    # * Verify --quiet overrides everything
    def test_quiet_overrides_everything(self):

        manager = OutputManager()
        manager.initialize(
            requested_level=OutputLevel.DEBUG,
            dev_mode=True,
            quiet=True,
        )
        assert manager.get_level() == OutputLevel.QUIET

    # * Verify --quiet overrides verbose
    def test_quiet_overrides_verbose(self):

        manager = OutputManager()
        manager.initialize(requested_level=OutputLevel.VERBOSE, quiet=True)
        assert manager.get_level() == OutputLevel.QUIET


class TestOutputMethods:

    # * Verify debug only at DEBUG level
    def test_debug_only_at_debug_level(self):

        manager = OutputManager()

        with patch("src.loom_io.console.console") as mock_console:
            # NORMAL level - no output
            manager.initialize(requested_level=OutputLevel.NORMAL)
            manager.debug("test message")
            mock_console.print.assert_not_called()

            # DEBUG level - output
            manager.initialize(requested_level=OutputLevel.DEBUG, dev_mode=True)
            manager.debug("test message")
            mock_console.print.assert_called_once()

    # * Verify verbose at VERBOSE & DEBUG
    def test_verbose_at_verbose_and_debug(self):

        manager = OutputManager()

        with patch("src.loom_io.console.console") as mock_console:
            # NORMAL - no output
            manager.initialize(requested_level=OutputLevel.NORMAL)
            manager.verbose("test")
            mock_console.print.assert_not_called()

            # VERBOSE - output
            manager.initialize(requested_level=OutputLevel.VERBOSE)
            manager.verbose("test")
            assert mock_console.print.called

    # * Verify info at NORMAL & above
    def test_info_at_normal_and_above(self):

        manager = OutputManager()

        with patch("src.loom_io.console.console") as mock_console:
            # QUIET - no output
            manager.initialize(quiet=True)
            manager.info("test")
            mock_console.print.assert_not_called()

            # NORMAL - output
            mock_console.reset_mock()
            manager.initialize(requested_level=OutputLevel.NORMAL)
            manager.info("test")
            mock_console.print.assert_called_once()

    # * Verify verbose w/ detail
    def test_verbose_with_detail(self):

        manager = OutputManager()
        manager.initialize(requested_level=OutputLevel.VERBOSE)

        with patch("src.loom_io.console.console") as mock_console:
            manager.verbose("message", "CATEGORY", "line1\nline2")
            # Should have 3 calls: main message + 2 detail lines
            assert mock_console.print.call_count == 3


class TestFileLogging:

    # * Verify log file is created
    def test_log_file_created(self, tmp_path):

        log_file = tmp_path / "test.log"
        manager = OutputManager()
        manager.initialize(requested_level=OutputLevel.VERBOSE, log_file=log_file)
        manager.verbose("test message", "TEST")
        manager.cleanup()

        assert log_file.exists()
        content = log_file.read_text()
        assert "test message" in content

    # * Verify cleanup closes file
    def test_cleanup_closes_file(self, tmp_path):

        log_file = tmp_path / "test.log"
        manager = OutputManager()
        manager.initialize(log_file=log_file)
        manager.cleanup()
        # File should be closed, can open again
        with open(log_file, "a") as f:
            f.write("test")

    # * Verify session start/end
    def test_session_logging(self, tmp_path):

        log_file = tmp_path / "session.log"
        manager = OutputManager()
        manager.initialize(requested_level=OutputLevel.VERBOSE, log_file=log_file)
        manager.start_session()
        manager.verbose("mid-session", "TEST")
        manager.end_session()

        content = log_file.read_text()
        assert "Session Started" in content
        assert "mid-session" in content
        assert "Session Ended" in content


class TestDeprecationWarnings:

    def setup_method(self):

        OutputManager.reset_warnings()

    # * Verify no warning without dev_mode
    def test_warning_only_in_dev_mode(self):

        import warnings

        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")
            OutputManager.emit_deprecation_warning("test_func", dev_mode=False)
        # No DeprecationWarning should be raised
        deprecation_warnings = [
            w for w in warning_list if issubclass(w.category, DeprecationWarning)
        ]
        assert len(deprecation_warnings) == 0

    # * Verify warning in dev_mode
    def test_warning_emitted_in_dev_mode(self):

        with pytest.warns(DeprecationWarning, match="test_func"):
            OutputManager.emit_deprecation_warning("test_func", dev_mode=True)

    # * Verify warning only once per function
    def test_warning_only_once_per_function(self):

        import warnings

        with pytest.warns(DeprecationWarning):
            OutputManager.emit_deprecation_warning("once_func", dev_mode=True)

        # Second call - no warning (already warned for this function)
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")
            OutputManager.emit_deprecation_warning("once_func", dev_mode=True)
        # Filter for our specific warning
        our_warnings = [w for w in warning_list if "once_func" in str(w.message)]
        assert len(our_warnings) == 0

    # * Verify reset_warnings allows re-warning
    def test_reset_warnings(self):

        OutputManager.emit_deprecation_warning("reset_test", dev_mode=True)
        OutputManager.reset_warnings()

        # Should warn again after reset
        with pytest.warns(DeprecationWarning, match="reset_test"):
            OutputManager.emit_deprecation_warning("reset_test", dev_mode=True)


class TestLevelComputation:

    # * Verify quiet has highest precedence
    def test_quiet_precedence(self):

        manager = OutputManager()

        # Even w/ DEBUG + dev_mode, quiet wins
        manager.initialize(requested_level=OutputLevel.DEBUG, dev_mode=True, quiet=True)
        assert manager.get_level() == OutputLevel.QUIET

    # * Verify dev_mode caps at VERBOSE
    def test_dev_mode_caps_level(self):

        manager = OutputManager()
        manager.initialize(requested_level=OutputLevel.DEBUG, dev_mode=False)
        assert manager.get_level() == OutputLevel.VERBOSE

    # * Verify normal level is not affected
    def test_normal_level_unaffected(self):

        manager = OutputManager()
        manager.initialize(requested_level=OutputLevel.NORMAL, dev_mode=False)
        assert manager.get_level() == OutputLevel.NORMAL

        manager.initialize(requested_level=OutputLevel.NORMAL, dev_mode=True)
        assert manager.get_level() == OutputLevel.NORMAL
