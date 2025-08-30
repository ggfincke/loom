# tests/unit/test_theme_selector.py
# Unit tests for theme selector interactive UI & fallback modes

from unittest.mock import Mock, patch, MagicMock
import pytest

from src.ui.theming.theme_selector import (
    _capture_banner, interactive_theme_selector, _fallback_theme_selector
)


# * Test banner capture functionality for theme previews

class TestCaptureBanner:
    # * Test banner capture w/ theme switching & restoration
    @patch('src.ui.theming.theme_selector.settings_manager')
    @patch('src.ui.theming.theme_selector.refresh_theme')
    @patch('src.ui.theming.theme_selector.console')
    @patch('src.ui.theming.theme_selector.show_loom_art')
    def test_capture_banner_basic(self, mock_show_art, mock_console, mock_refresh, mock_settings):
        # setup mocks
        mock_settings.get.return_value = "original_theme"
        mock_capture = MagicMock()
        mock_capture.get.return_value = "captured banner content"
        mock_console.capture.return_value.__enter__.return_value = mock_capture
        
        result = _capture_banner("test_theme")
        
        # verify theme switching & restoration
        assert mock_settings.set.call_count == 2
        mock_settings.set.assert_any_call("theme", "test_theme")
        mock_settings.set.assert_any_call("theme", "original_theme")
        
        # verify refresh calls
        assert mock_refresh.call_count == 2
        
        # verify art rendering & capture
        mock_show_art.assert_called_once()
        assert result == "captured banner content"
    
    # * Test banner capture exception handling & cleanup
    @patch('src.ui.theming.theme_selector.settings_manager')
    @patch('src.ui.theming.theme_selector.refresh_theme')
    @patch('src.ui.theming.theme_selector.console')
    @patch('src.ui.theming.theme_selector.show_loom_art')
    def test_capture_banner_exception_cleanup(self, mock_show_art, mock_console, mock_refresh, mock_settings):
        # setup mocks
        mock_settings.get.return_value = "original_theme"
        mock_show_art.side_effect = Exception("Art rendering failed")
        
        # should still restore original theme even if exception occurs
        with pytest.raises(Exception, match="Art rendering failed"):
            _capture_banner("test_theme")
        
        # verify cleanup occurred
        mock_settings.set.assert_any_call("theme", "original_theme")
        assert mock_refresh.call_count == 2


# * Test interactive theme selector w/ terminal menu

class TestInteractiveThemeSelector:
    # * Test successful theme selection from interactive menu
    @patch('src.ui.theming.theme_selector.THEMES', {"theme1": {}, "theme2": {}, "theme3": {}})
    @patch('src.ui.theming.theme_selector.settings_manager')
    @patch('src.ui.theming.theme_selector.TerminalMenu')
    def test_interactive_selector_success(self, mock_menu_class, mock_settings):
        # setup mocks
        mock_settings.get.return_value = "theme2"
        mock_menu = Mock()
        mock_menu.show.return_value = 1  # user selected index 1 (theme2)
        mock_menu_class.return_value = mock_menu
        
        result = interactive_theme_selector()
        
        # verify menu configuration
        mock_menu_class.assert_called_once()
        args, kwargs = mock_menu_class.call_args
        
        assert args[0] == ["theme1", "theme2", "theme3"]  # sorted theme names
        assert kwargs["title"] == "🎨 Select a theme"
        assert kwargs["cursor_index"] == 1  # starts at current theme
        assert kwargs["preview_command"] is _capture_banner
        
        assert result == "theme2"
    
    # * Test theme selection when user cancels operation
    @patch('src.ui.theming.theme_selector.THEMES', {"theme1": {}, "theme2": {}})
    @patch('src.ui.theming.theme_selector.settings_manager')
    @patch('src.ui.theming.theme_selector.TerminalMenu')
    def test_interactive_selector_cancel(self, mock_menu_class, mock_settings):
        # setup mocks
        mock_settings.get.return_value = "theme1"
        mock_menu = Mock()
        mock_menu.show.return_value = None  # user cancelled
        mock_menu_class.return_value = mock_menu
        
        result = interactive_theme_selector()
        
        assert result is None
    
    # * Test theme selection w/ current theme not in available themes
    @patch('src.ui.theming.theme_selector.THEMES', {"theme1": {}, "theme2": {}})
    @patch('src.ui.theming.theme_selector.settings_manager')
    @patch('src.ui.theming.theme_selector.TerminalMenu')
    def test_interactive_selector_theme_not_found(self, mock_menu_class, mock_settings):
        # setup mocks
        mock_settings.get.return_value = "unknown_theme"  # not in THEMES
        mock_menu = Mock()
        mock_menu.show.return_value = 0
        mock_menu_class.return_value = mock_menu
        
        result = interactive_theme_selector()
        
        # should default to index 0 when current theme not found
        args, kwargs = mock_menu_class.call_args
        assert kwargs["cursor_index"] == 0
        assert result == "theme1"
    
    # * Test fallback when terminal menu fails w/ OSError
    @patch('src.ui.theming.theme_selector.THEMES', {"theme1": {}, "theme2": {}})
    @patch('src.ui.theming.theme_selector.settings_manager')
    @patch('src.ui.theming.theme_selector.TerminalMenu')
    @patch('src.ui.theming.theme_selector._fallback_theme_selector')
    def test_interactive_selector_oserror_fallback(self, mock_fallback, mock_menu_class, mock_settings):
        # setup mocks
        mock_settings.get.return_value = "theme1"
        mock_menu_class.side_effect = OSError("Terminal not available")
        mock_fallback.return_value = "theme2"
        
        result = interactive_theme_selector()
        
        # should call fallback selector
        mock_fallback.assert_called_once_with(["theme1", "theme2"], "theme1")
        assert result == "theme2"
    
    # * Test fallback when terminal menu fails w/ general exception
    @patch('src.ui.theming.theme_selector.THEMES', {"theme1": {}, "theme2": {}})
    @patch('src.ui.theming.theme_selector.settings_manager')
    @patch('src.ui.theming.theme_selector.TerminalMenu')
    @patch('src.ui.theming.theme_selector._fallback_theme_selector')
    def test_interactive_selector_exception_fallback(self, mock_fallback, mock_menu_class, mock_settings):
        # setup mocks
        mock_settings.get.return_value = "theme1"
        mock_menu_class.side_effect = Exception("Menu creation failed")
        mock_fallback.return_value = None
        
        result = interactive_theme_selector()
        
        # should call fallback selector
        mock_fallback.assert_called_once_with(["theme1", "theme2"], "theme1")
        assert result is None


# * Test fallback theme selector for non-TTY environments

class TestFallbackThemeSelector:
    # * Test successful theme selection via numeric input
    @patch('src.ui.theming.theme_selector.console')
    @patch('src.ui.theming.theme_selector.settings_manager')
    @patch('src.ui.theming.theme_selector.refresh_theme')
    @patch('src.ui.theming.theme_selector.show_loom_art')
    @patch('rich.prompt.Confirm')
    def test_fallback_selector_success(self, mock_confirm, mock_show_art, mock_refresh, 
                                     mock_settings, mock_console):
        # setup mocks
        mock_console.input.return_value = "2"  # user selects theme 2
        mock_confirm.ask.return_value = True   # user confirms
        mock_settings.get.return_value = "current_theme"
        
        theme_names = ["theme1", "theme2", "theme3"]
        result = _fallback_theme_selector(theme_names, "current_theme")
        
        # verify display & interaction
        mock_console.clear.assert_called_once()
        mock_console.input.assert_called_once()
        mock_confirm.ask.assert_called_once()
        
        # verify theme preview
        mock_settings.set.assert_any_call("theme", "theme2")
        mock_show_art.assert_called_once()
        
        assert result == "theme2"
    
    # * Test user cancels theme selection
    @patch('src.ui.theming.theme_selector.console')
    def test_fallback_selector_quit(self, mock_console):
        mock_console.input.return_value = "q"
        
        theme_names = ["theme1", "theme2"]
        result = _fallback_theme_selector(theme_names, "theme1")
        
        assert result is None
    
    # * Test user enters empty input
    @patch('src.ui.theming.theme_selector.console')
    def test_fallback_selector_empty_input(self, mock_console):
        mock_console.input.return_value = ""
        
        theme_names = ["theme1", "theme2"]
        result = _fallback_theme_selector(theme_names, "theme1")
        
        assert result is None
    
    # * Test invalid numeric input (out of range)
    @patch('src.ui.theming.theme_selector.console')
    def test_fallback_selector_invalid_number(self, mock_console):
        mock_console.input.return_value = "5"  # > len(theme_names)
        
        theme_names = ["theme1", "theme2"]
        result = _fallback_theme_selector(theme_names, "theme1")
        
        # should print error & return None
        assert result is None
        error_calls = [call for call in mock_console.print.call_args_list 
                      if "Invalid choice" in str(call)]
        assert len(error_calls) > 0
    
    # * Test non-numeric input
    @patch('src.ui.theming.theme_selector.console')
    def test_fallback_selector_non_numeric(self, mock_console):
        mock_console.input.return_value = "abc"
        
        theme_names = ["theme1", "theme2"]
        result = _fallback_theme_selector(theme_names, "theme1")
        
        # should print error & return None
        assert result is None
        error_calls = [call for call in mock_console.print.call_args_list 
                      if "Invalid input" in str(call)]
        assert len(error_calls) > 0
    
    # * Test user declines confirmation after preview
    @patch('src.ui.theming.theme_selector.console')
    @patch('src.ui.theming.theme_selector.settings_manager')
    @patch('src.ui.theming.theme_selector.refresh_theme')
    @patch('src.ui.theming.theme_selector.show_loom_art')
    @patch('rich.prompt.Confirm')
    def test_fallback_selector_decline_confirmation(self, mock_confirm, mock_show_art, 
                                                  mock_refresh, mock_settings, mock_console):
        # setup mocks
        mock_console.input.return_value = "1"
        mock_confirm.ask.return_value = False  # user declines
        
        theme_names = ["theme1", "theme2"]
        result = _fallback_theme_selector(theme_names, "current")
        
        # should preview theme but return None after declining
        mock_show_art.assert_called_once()
        assert result is None
    
    # * Test EOFError handling (Ctrl+D)
    @patch('src.ui.theming.theme_selector.console')
    def test_fallback_selector_eof_error(self, mock_console):
        mock_console.input.side_effect = EOFError()
        
        theme_names = ["theme1", "theme2"]
        result = _fallback_theme_selector(theme_names, "theme1")
        
        # should handle EOFError gracefully
        assert result is None
    
    # * Test KeyboardInterrupt handling (Ctrl+C)
    @patch('src.ui.theming.theme_selector.console')
    def test_fallback_selector_keyboard_interrupt(self, mock_console):
        mock_console.input.side_effect = KeyboardInterrupt()
        
        theme_names = ["theme1", "theme2"]
        result = _fallback_theme_selector(theme_names, "theme1")
        
        # should handle KeyboardInterrupt gracefully
        assert result is None