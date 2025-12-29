# tests/unit/core/test_output.py
# Unit tests for core output module (pure layer)

import pytest

from src.core.output import (
    OutputLevel,
    OutputInterface,
    NullOutputManager,
    get_output_manager,
    set_output_manager,
    reset_output_manager,
)


class TestOutputLevel:

    # * Verify levels are ordered correctly
    def test_level_ordering(self):

        assert OutputLevel.QUIET < OutputLevel.NORMAL
        assert OutputLevel.NORMAL < OutputLevel.VERBOSE
        assert OutputLevel.VERBOSE < OutputLevel.DEBUG

    # * Verify levels have expected integer values
    def test_level_values(self):

        assert OutputLevel.QUIET == 0
        assert OutputLevel.NORMAL == 1
        assert OutputLevel.VERBOSE == 2
        assert OutputLevel.DEBUG == 3

    # * Verify levels can be compared
    def test_level_comparison(self):

        assert OutputLevel.VERBOSE >= 2
        assert OutputLevel.DEBUG >= OutputLevel.VERBOSE
        assert OutputLevel.QUIET < OutputLevel.NORMAL


class TestNullOutputManager:

    # * Verify default level is NORMAL
    def test_default_level_is_normal(self):

        manager = NullOutputManager()
        assert manager.get_level() == OutputLevel.NORMAL

    # * Verify debug is disabled by default
    def test_debug_is_disabled(self):

        manager = NullOutputManager()
        assert manager.is_debug_enabled() is False

    # * Verify verbose is disabled by default
    def test_verbose_is_disabled(self):

        manager = NullOutputManager()
        assert manager.is_verbose_enabled() is False

    # * Verify all output methods are no-ops
    def test_methods_are_noop(self):

        manager = NullOutputManager()
        # These should not raise any exceptions
        manager.debug("test message")
        manager.debug("test message", "CATEGORY")
        manager.verbose("test message")
        manager.verbose("test message", "CATEGORY", "detail")
        manager.info("test message")
        manager.start_session()
        manager.end_session()

    # * Verify NullOutputManager implements OutputInterface
    def test_implements_protocol(self):

        manager = NullOutputManager()
        assert isinstance(manager, OutputInterface)


class TestRegistry:

    def setup_method(self):

        reset_output_manager()

    def teardown_method(self):

        reset_output_manager()

    # * Verify default manager is NullOutputManager
    def test_default_is_null_manager(self):

        manager = get_output_manager()
        assert isinstance(manager, NullOutputManager)

    # * Verify set_output_manager works
    def test_set_and_get(self):

        custom = NullOutputManager()
        set_output_manager(custom)
        assert get_output_manager() is custom

    # * Verify reset_output_manager restores NullOutputManager
    def test_reset_restores_null(self):

        custom = NullOutputManager()
        set_output_manager(custom)
        reset_output_manager()
        manager = get_output_manager()
        assert isinstance(manager, NullOutputManager)
        assert manager is not custom

    # * Verify can replace manager multiple times
    def test_replace_manager(self):

        manager1 = NullOutputManager()
        manager2 = NullOutputManager()

        set_output_manager(manager1)
        assert get_output_manager() is manager1

        set_output_manager(manager2)
        assert get_output_manager() is manager2


class TestOutputInterface:

    # * Verify NullOutputManager implements protocol
    def test_null_manager_implements_protocol(self):

        manager = NullOutputManager()
        assert isinstance(manager, OutputInterface)

    # * Verify protocol has expected methods
    def test_protocol_methods(self):

        manager = NullOutputManager()
        # These should all exist and be callable
        assert callable(manager.get_level)
        assert callable(manager.is_debug_enabled)
        assert callable(manager.is_verbose_enabled)
        assert callable(manager.debug)
        assert callable(manager.verbose)
        assert callable(manager.info)
        assert callable(manager.start_session)
        assert callable(manager.end_session)
