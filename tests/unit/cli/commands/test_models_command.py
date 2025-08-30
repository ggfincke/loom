# tests/unit/cli/commands/test_models_command.py
# Unit tests for models command functionality

import pytest
from unittest.mock import patch, Mock
from typer.testing import CliRunner

from src.cli.app import app
from src.ai.types import GenerateResult


class TestModelsCommand:

    @pytest.fixture
    def runner(self):
        return CliRunner()

    # * Test models command help flag
    def test_models_help_flag(self, runner):
        with patch('src.cli.commands.models.show_command_help') as mock_help:
            result = runner.invoke(app, ["models", "--help"])
            # Help doesn't exit with SystemExit in this implementation
            mock_help.assert_called_once_with("models")

    # * Test models default callback (list models)
    @patch('src.cli.commands.models.get_models_by_provider')
    @patch('src.cli.commands.models.console')
    def test_models_default_callback(self, mock_console, mock_get_models, runner):
        # mock provider data
        mock_get_models.return_value = {
            "openai": {
                "models": ["gpt-4o", "gpt-4o-mini"],
                "available": True,
                "requirement": "OPENAI_API_KEY"
            },
            "claude": {
                "models": ["claude-3-5-sonnet-20241022"],
                "available": False,
                "requirement": "ANTHROPIC_API_KEY"
            },
            "ollama": {
                "models": [],
                "available": False,
                "requirement": "Ollama server"
            }
        }

        result = runner.invoke(app, ["models"])

        assert result.exit_code == 0
        # verify console output was called for providers
        assert mock_console.print.called
        # verify get_models_by_provider was called
        mock_get_models.assert_called_once()

    # * Test models list subcommand
    @patch('src.cli.commands.models.get_models_by_provider')
    @patch('src.cli.commands.models.console')
    def test_models_list_subcommand(self, mock_console, mock_get_models, runner):
        mock_get_models.return_value = {
            "openai": {
                "models": ["gpt-4o"],
                "available": True,
                "requirement": "OPENAI_API_KEY"
            }
        }

        result = runner.invoke(app, ["models", "list"])

        assert result.exit_code == 0
        mock_get_models.assert_called_once()
        assert mock_console.print.called

    # * Test _show_models_list with available OpenAI models
    @patch('src.cli.commands.models.get_models_by_provider')
    @patch('src.cli.commands.models.console')
    def test_show_models_list_openai_available(self, mock_console, mock_get_models, runner):
        mock_get_models.return_value = {
            "openai": {
                "models": ["gpt-4o", "gpt-4o-mini"],
                "available": True,
                "requirement": "OPENAI_API_KEY"
            }
        }

        result = runner.invoke(app, ["models"])

        assert result.exit_code == 0
        
        # verify specific console print calls
        print_calls = [call[0][0] for call in mock_console.print.call_args_list if call[0]]
        
        # should contain provider header
        openai_header_found = any("OPENAI" in str(call) for call in print_calls)
        assert openai_header_found
        
        # should contain availability status
        available_status_found = any("Available" in str(call) for call in print_calls)
        assert available_status_found

    # * Test _show_models_list with unavailable Claude models
    @patch('src.cli.commands.models.get_models_by_provider')
    @patch('src.cli.commands.models.console')
    def test_show_models_list_claude_unavailable(self, mock_console, mock_get_models, runner):
        mock_get_models.return_value = {
            "claude": {
                "models": ["claude-3-5-sonnet-20241022"],
                "available": False,
                "requirement": "ANTHROPIC_API_KEY"
            }
        }

        result = runner.invoke(app, ["models"])

        assert result.exit_code == 0
        
        print_calls = [call[0][0] for call in mock_console.print.call_args_list if call[0]]
        
        # should contain Claude header
        claude_header_found = any("CLAUDE" in str(call) for call in print_calls)
        assert claude_header_found
        
        # should contain requirement information
        requirement_found = any("ANTHROPIC_API_KEY" in str(call) for call in print_calls)
        assert requirement_found

    # * Test _show_models_list with no Ollama models
    @patch('src.cli.commands.models.get_models_by_provider')
    @patch('src.cli.commands.models.console')
    def test_show_models_list_ollama_no_models(self, mock_console, mock_get_models, runner):
        mock_get_models.return_value = {
            "ollama": {
                "models": [],
                "available": False,
                "requirement": "Ollama server"
            }
        }

        result = runner.invoke(app, ["models"])

        assert result.exit_code == 0
        
        print_calls = [call[0][0] for call in mock_console.print.call_args_list if call[0]]
        
        # should contain Ollama-specific message
        ollama_message_found = any("Start Ollama server" in str(call) for call in print_calls)
        assert ollama_message_found

    # * Test _show_models_list with mixed provider availability
    @patch('src.cli.commands.models.get_models_by_provider')
    @patch('src.cli.commands.models.console')
    def test_show_models_list_mixed_availability(self, mock_console, mock_get_models, runner):
        mock_get_models.return_value = {
            "openai": {
                "models": ["gpt-4o"],
                "available": True,
                "requirement": "OPENAI_API_KEY"
            },
            "claude": {
                "models": ["claude-3-5-sonnet-20241022"],
                "available": False,
                "requirement": "ANTHROPIC_API_KEY"
            },
            "ollama": {
                "models": ["deepseek-r1:14b"],
                "available": True,
                "requirement": "Ollama server"
            }
        }

        result = runner.invoke(app, ["models"])

        assert result.exit_code == 0
        
        print_calls = [call[0][0] for call in mock_console.print.call_args_list if call[0]]
        
        # should contain all provider headers
        assert any("OPENAI" in str(call) for call in print_calls)
        assert any("CLAUDE" in str(call) for call in print_calls)
        assert any("OLLAMA" in str(call) for call in print_calls)
        
        # should contain usage notes at the end
        usage_note_found = any("loom tailor --model" in str(call) for call in print_calls)
        assert usage_note_found


class TestModelsTestCommand:

    @pytest.fixture
    def runner(self):
        return CliRunner()

    # * Test models test command success path
    @patch('src.ai.clients.ollama_client.run_generate')
    @patch('src.cli.commands.models.get_available_models_with_error')
    @patch('src.cli.commands.models.check_ollama_with_error')
    @patch('src.cli.commands.models.console')
    def test_models_test_success(
        self, mock_console, mock_check_ollama, mock_get_models, mock_run_generate, runner
    ):
        # setup successful mocks
        mock_check_ollama.return_value = (True, None)
        mock_get_models.return_value = (["deepseek-r1:14b", "llama3.2"], None)
        mock_run_generate.return_value = GenerateResult(
            success=True,
            data={"test": "success"},
            json_text='{"test": "success"}'
        )

        result = runner.invoke(app, ["models", "test", "deepseek-r1:14b"])

        assert result.exit_code == 0
        
        # verify all checks were performed
        mock_check_ollama.assert_called_once()
        mock_get_models.assert_called_once()
        mock_run_generate.assert_called_once()
        
        # verify console output includes success messages
        print_calls = [call[0][0] for call in mock_console.print.call_args_list if call[0]]
        
        # should contain test steps
        connectivity_check = any("Ollama server connectivity" in str(call) for call in print_calls)
        assert connectivity_check
        
        models_check = any("Retrieving available models" in str(call) for call in print_calls)
        assert models_check
        
        api_test = any("Testing basic API call" in str(call) for call in print_calls)
        assert api_test
        
        success_message = any("fully functional" in str(call) for call in print_calls)
        assert success_message

    # * Test models test command with Ollama server not running
    @patch('src.cli.commands.models.check_ollama_with_error')
    @patch('src.cli.commands.models.console')
    def test_models_test_ollama_not_running(self, mock_console, mock_check_ollama, runner):
        mock_check_ollama.return_value = (False, "Connection refused")

        result = runner.invoke(app, ["models", "test", "deepseek-r1:14b"])

        assert result.exit_code == 0  # command doesn't exit with error, just reports failure
        
        mock_check_ollama.assert_called_once()
        
        # should show failure message
        print_calls = [call[0][0] for call in mock_console.print.call_args_list if call[0]]
        failure_message = any("Failed" in str(call) and "Connection refused" in str(call) for call in print_calls)
        assert failure_message

    # * Test models test command with model not available
    @patch('src.cli.commands.models.get_available_models_with_error')
    @patch('src.cli.commands.models.check_ollama_with_error')
    @patch('src.cli.commands.models.console')
    def test_models_test_model_not_available(
        self, mock_console, mock_check_ollama, mock_get_models, runner
    ):
        mock_check_ollama.return_value = (True, None)
        mock_get_models.return_value = (["llama3.2"], None)  # model not in list

        result = runner.invoke(app, ["models", "test", "deepseek-r1:14b"])

        assert result.exit_code == 0
        
        # should show model not found message
        print_calls = [call[0][0] for call in mock_console.print.call_args_list if call[0]]
        not_found_message = any("not found" in str(call) for call in print_calls)
        assert not_found_message
        
        # should show install instructions
        install_message = any("ollama pull" in str(call) for call in print_calls)
        assert install_message

    # * Test models test command with API call failure
    @patch('src.ai.clients.ollama_client.run_generate')
    @patch('src.cli.commands.models.get_available_models_with_error')
    @patch('src.cli.commands.models.check_ollama_with_error')
    @patch('src.cli.commands.models.console')
    def test_models_test_api_call_failure(
        self, mock_console, mock_check_ollama, mock_get_models, mock_run_generate, runner
    ):
        mock_check_ollama.return_value = (True, None)
        mock_get_models.return_value = (["deepseek-r1:14b"], None)
        mock_run_generate.return_value = GenerateResult(
            success=False,
            error="Model not responding"
        )

        result = runner.invoke(app, ["models", "test", "deepseek-r1:14b"])

        assert result.exit_code == 0
        
        # should show API failure message
        print_calls = [call[0][0] for call in mock_console.print.call_args_list if call[0]]
        api_failure = any("API call failed" in str(call) and "Model not responding" in str(call) for call in print_calls)
        assert api_failure

    # * Test models test command with verbose flag
    @patch('src.cli.commands.models.enable_debug')
    @patch('src.ai.clients.ollama_client.run_generate')
    @patch('src.cli.commands.models.get_available_models_with_error')
    @patch('src.cli.commands.models.check_ollama_with_error')
    @patch('src.cli.commands.models.console')
    def test_models_test_verbose_flag(
        self, mock_console, mock_check_ollama, mock_get_models, 
        mock_run_generate, mock_enable_debug, runner
    ):
        mock_check_ollama.return_value = (True, None)
        mock_get_models.return_value = (["deepseek-r1:14b"], None)
        mock_run_generate.return_value = GenerateResult(
            success=True,
            json_text='{"test": "success"}' * 10  # long response
        )

        result = runner.invoke(app, ["models", "test", "deepseek-r1:14b", "--verbose"])

        assert result.exit_code == 0
        
        # verify debug was enabled
        mock_enable_debug.assert_called_once()
        
        # should show response content when verbose
        print_calls = [call[0][0] for call in mock_console.print.call_args_list if call[0]]
        response_shown = any("Response:" in str(call) for call in print_calls)
        assert response_shown

    # * Test models test command with models retrieval error
    @patch('src.cli.commands.models.get_available_models_with_error')
    @patch('src.cli.commands.models.check_ollama_with_error')
    @patch('src.cli.commands.models.console')
    def test_models_test_models_retrieval_error(
        self, mock_console, mock_check_ollama, mock_get_models, runner
    ):
        mock_check_ollama.return_value = (True, None)
        mock_get_models.return_value = (None, "API timeout")

        result = runner.invoke(app, ["models", "test", "deepseek-r1:14b"])

        assert result.exit_code == 0
        
        # should show models retrieval error
        print_calls = [call[0][0] for call in mock_console.print.call_args_list if call[0]]
        error_message = any("Failed" in str(call) and "API timeout" in str(call) for call in print_calls)
        assert error_message

    # * Test models test command argument validation
    def test_models_test_missing_argument(self, runner):
        # test without model argument - should show error
        result = runner.invoke(app, ["models", "test"])
        
        assert result.exit_code != 0
        # typer will show usage/error message for missing argument


class TestModelsIntegration:

    @pytest.fixture
    def runner(self):
        return CliRunner()

    # * Test integration with get_models_by_provider
    @patch('src.cli.commands.models.get_models_by_provider')
    def test_integration_with_get_models_by_provider(self, mock_get_models, runner):
        # test that the function is called correctly
        mock_get_models.return_value = {}
        
        result = runner.invoke(app, ["models"])
        
        assert result.exit_code == 0
        mock_get_models.assert_called_once_with()

    # * Test integration with Ollama client functions
    @patch('src.ai.clients.ollama_client.run_generate')
    @patch('src.cli.commands.models.get_available_models_with_error')
    @patch('src.cli.commands.models.check_ollama_with_error')
    @patch('src.cli.commands.models.console')
    def test_integration_with_ollama_functions(
        self, mock_console, mock_check_ollama, mock_get_models, mock_run_generate, runner
    ):
        # test that Ollama functions are called with correct parameters
        mock_check_ollama.return_value = (True, None)
        mock_get_models.return_value = (["test-model"], None)
        mock_run_generate.return_value = GenerateResult(success=True)

        result = runner.invoke(app, ["models", "test", "test-model"])

        assert result.exit_code == 0
        
        # verify function calls
        mock_check_ollama.assert_called_once()
        mock_get_models.assert_called_once()
        mock_run_generate.assert_called_once()
        
        # verify run_generate was called with correct parameters
        call_args = mock_run_generate.call_args
        assert len(call_args[0]) == 2  # prompt and model
        assert call_args[0][1] == "test-model"  # model name
        assert "JSON" in call_args[0][0]  # prompt should mention JSON

    # * Test theming integration
    @patch('src.cli.commands.models.get_models_by_provider')
    @patch('src.cli.commands.models.styled_checkmark')
    @patch('src.cli.commands.models.accent_gradient')
    @patch('src.cli.commands.models.styled_bullet')
    @patch('src.cli.commands.models.console')
    def test_theming_integration(
        self, mock_console, mock_styled_bullet, mock_accent_gradient, 
        mock_styled_checkmark, mock_get_models, runner
    ):
        # setup theme function mocks
        mock_styled_checkmark.return_value = "✓"
        mock_accent_gradient.return_value = "Available AI Models"
        mock_styled_bullet.return_value = "•"
        
        mock_get_models.return_value = {
            "openai": {
                "models": ["gpt-4o"],
                "available": True,
                "requirement": "OPENAI_API_KEY"
            }
        }

        result = runner.invoke(app, ["models"])

        assert result.exit_code == 0
        
        # verify theming functions were called
        mock_accent_gradient.assert_called()
        mock_styled_checkmark.assert_called()
        mock_styled_bullet.assert_called()


# * Test error handling and edge cases
class TestModelsEdgeCases:

    @pytest.fixture
    def runner(self):
        return CliRunner()

    # * Test empty models response
    @patch('src.cli.commands.models.get_models_by_provider')
    @patch('src.cli.commands.models.console')
    def test_empty_models_response(self, mock_console, mock_get_models, runner):
        mock_get_models.return_value = {}

        result = runner.invoke(app, ["models"])

        assert result.exit_code == 0
        mock_get_models.assert_called_once()

    # * Test get_models_by_provider exception handling
    @patch('src.cli.commands.models.get_models_by_provider')
    def test_get_models_exception(self, mock_get_models, runner):
        mock_get_models.side_effect = Exception("Provider error")

        # should not crash, may exit with error or handle gracefully
        result = runner.invoke(app, ["models"])
        
        # the exact behavior depends on implementation
        # main goal is that it doesn't crash with unhandled exception

    # * Test models test with empty model name
    def test_models_test_empty_model_name(self, runner):
        result = runner.invoke(app, ["models", "test", ""])
        
        # should handle empty string gracefully
        # may show validation error or attempt the test

    # * Test models test with special characters in model name
    @patch('src.cli.commands.models.check_ollama_with_error')
    @patch('src.cli.commands.models.console')
    def test_models_test_special_characters(self, mock_console, mock_check_ollama, runner):
        mock_check_ollama.return_value = (False, "Invalid model name")
        
        result = runner.invoke(app, ["models", "test", "model@#$%"])
        
        assert result.exit_code == 0
        # should handle special characters in model names