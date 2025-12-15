# tests/unit/ai/test_models.py
# Unit tests for AI model validation, alias resolution & provider detection

from unittest.mock import Mock, patch
import pytest
import sys
import typer

from src.ai.models import (
    resolve_model_alias,
    validate_model,
    get_model_error_message,
    ensure_valid_model,
    check_openai_api_key,
    check_claude_api_key,
    get_ollama_models,
    is_ollama_available,
    get_models_by_provider,
    get_model_provider,
    get_default_model,
    _is_test_model,
    _get_test_model_provider,
    reset_model_cache,
    OPENAI_MODELS,
    CLAUDE_MODELS,
    SUPPORTED_MODELS,
    MODEL_ALIASES,
    MODEL_CATEGORIES,
)


@pytest.fixture(autouse=True)
def reset_caches():
    # reset model cache before each test to avoid stale data
    reset_model_cache()
    yield
    reset_model_cache()


# * Test model alias resolution


class TestResolveModelAlias:
    # * Test resolving supported full model names (no change)
    def test_resolve_full_model_name(self):
        assert resolve_model_alias("gpt-5") == "gpt-5"
        assert (
            resolve_model_alias("claude-opus-4-1-20250805")
            == "claude-opus-4-1-20250805"
        )
        assert resolve_model_alias("gpt-4o-mini") == "gpt-4o-mini"

    # * Test resolving known aliases to full names
    def test_resolve_known_aliases(self):
        assert resolve_model_alias("claude-opus-4.1") == "claude-opus-4-1-20250805"
        assert resolve_model_alias("gpt4o") == "gpt-4o"
        assert resolve_model_alias("gpt5") == "gpt-5"
        assert resolve_model_alias("claude-haiku-3") == "claude-3-haiku-20240307"

    # * Test unknown aliases return original value
    def test_resolve_unknown_alias(self):
        assert resolve_model_alias("unknown-model") == "unknown-model"
        assert resolve_model_alias("gpt-9000") == "gpt-9000"
        assert resolve_model_alias("claude-future") == "claude-future"


# * Test model validation logic


class TestValidateModel:
    # * Test validation w/ test models in testing environment
    @patch("src.ai.models._is_test_model")
    @patch("src.ai.models._get_test_model_provider")
    def test_validate_test_model(self, mock_get_provider, mock_is_test):
        mock_is_test.return_value = True
        mock_get_provider.return_value = "openai"

        valid, provider = validate_model("test-model")

        assert valid is True
        assert provider == "openai"
        mock_is_test.assert_called_once_with("test-model")
        mock_get_provider.assert_called_once_with("test-model")

    # * Test OpenAI model validation w/ API key available
    @patch("src.ai.models.check_openai_api_key")
    def test_validate_openai_model_with_key(self, mock_check_key):
        mock_check_key.return_value = True

        valid, provider = validate_model("gpt-5")

        assert valid is True
        assert provider == "openai"

    # * Test OpenAI model validation w/o API key
    @patch("src.ai.models.check_openai_api_key")
    def test_validate_openai_model_without_key(self, mock_check_key):
        mock_check_key.return_value = False

        valid, provider = validate_model("gpt-5")

        assert valid is False
        assert provider == "openai_key_missing"

    # * Test Claude model validation w/ API key available
    @patch("src.ai.models.check_claude_api_key")
    def test_validate_claude_model_with_key(self, mock_check_key):
        mock_check_key.return_value = True

        valid, provider = validate_model("claude-opus-4-1-20250805")

        assert valid is True
        assert provider == "claude"

    # * Test Claude model validation w/o API key
    @patch("src.ai.models.check_claude_api_key")
    def test_validate_claude_model_without_key(self, mock_check_key):
        mock_check_key.return_value = False

        valid, provider = validate_model("claude-opus-4-1-20250805")

        assert valid is False
        assert provider == "claude_key_missing"

    # * Test Ollama model validation when available
    @patch("src.ai.models.get_ollama_models")
    @patch("src.ai.models.is_ollama_available")
    def test_validate_ollama_model_available(self, mock_is_available, mock_get_models):
        mock_get_models.return_value = ["llama3", "mistral", "codellama"]
        mock_is_available.return_value = True

        valid, provider = validate_model("llama3")

        assert valid is True
        assert provider == "ollama"

    # * Test Ollama model validation when Ollama available but model missing
    @patch("src.ai.models.get_ollama_models")
    @patch("src.ai.models.is_ollama_available")
    def test_validate_ollama_model_missing(self, mock_is_available, mock_get_models):
        mock_get_models.return_value = ["llama3", "mistral"]
        mock_is_available.return_value = True

        valid, provider = validate_model("nonexistent-model")

        assert valid is False
        assert provider == "ollama_model_missing"

    # * Test model validation when not found anywhere
    @patch("src.ai.models.get_ollama_models")
    @patch("src.ai.models.is_ollama_available")
    def test_validate_model_not_found(self, mock_is_available, mock_get_models):
        mock_get_models.return_value = []
        mock_is_available.return_value = False

        valid, provider = validate_model("unknown-model")

        assert valid is False
        assert provider == "model_not_found"


# * Test model error message generation


class TestGetModelErrorMessage:
    # * Test error message for missing OpenAI API key
    @patch("src.ai.models.validate_model")
    def test_error_message_openai_key_missing(self, mock_validate):
        mock_validate.return_value = (False, "openai_key_missing")

        message = get_model_error_message("gpt-5")

        assert "requires OPENAI_API_KEY environment variable" in message
        assert "gpt-5" in message

    # * Test error message for missing Claude API key
    @patch("src.ai.models.validate_model")
    def test_error_message_claude_key_missing(self, mock_validate):
        mock_validate.return_value = (False, "claude_key_missing")

        message = get_model_error_message("claude-opus-4")

        assert "requires ANTHROPIC_API_KEY environment variable" in message
        assert "claude-opus-4" in message

    # * Test error message for missing Ollama model w/ available models
    @patch("src.ai.models.validate_model")
    @patch("src.ai.models.get_ollama_models")
    def test_error_message_ollama_model_missing_with_available(
        self, mock_get_models, mock_validate
    ):
        mock_validate.return_value = (False, "ollama_model_missing")
        mock_get_models.return_value = ["llama3", "mistral"]

        message = get_model_error_message("nonexistent")

        assert "not found in Ollama" in message
        assert "Available local models: llama3, mistral" in message

    # * Test error message for missing Ollama model w/ no available models
    @patch("src.ai.models.validate_model")
    @patch("src.ai.models.get_ollama_models")
    def test_error_message_ollama_model_missing_no_available(
        self, mock_get_models, mock_validate
    ):
        mock_validate.return_value = (False, "ollama_model_missing")
        mock_get_models.return_value = []

        message = get_model_error_message("nonexistent")

        assert "not found in Ollama" in message
        assert "No local models available" in message

    # * Test comprehensive error message for general model not found
    @patch("src.ai.models.validate_model")
    @patch("src.ai.models.get_models_by_provider")
    @patch("src.ai.models.is_ollama_available")
    @patch("src.ai.models.check_claude_api_key")
    @patch("src.ai.models.check_openai_api_key")
    def test_error_message_comprehensive(
        self,
        mock_openai_key,
        mock_claude_key,
        mock_ollama_avail,
        mock_providers,
        mock_validate,
    ):
        mock_validate.return_value = (False, "model_not_found")
        mock_providers.return_value = {
            "openai": {
                "models": ["gpt-5"],
                "available": True,
                "requirement": "API key",
            },
            "claude": {
                "models": ["claude-opus-4"],
                "available": False,
                "requirement": "API key",
            },
            "ollama": {
                "models": [],
                "available": False,
                "requirement": "Ollama server",
            },
        }
        mock_openai_key.return_value = True
        mock_claude_key.return_value = False
        mock_ollama_avail.return_value = False

        message = get_model_error_message("unknown-model")

        assert "Model 'unknown-model' is not available" in message
        assert "Available OPENAI models: gpt-5" in message
        assert "Popular aliases:" in message
        assert "Recommended: gpt-5-mini" in message


# * Test ensure_valid_model functionality


class TestEnsureValidModel:
    # * Test successful validation returns resolved model
    @patch("src.ai.models.resolve_model_alias")
    @patch("src.ai.models.validate_model")
    def test_ensure_valid_model_success(self, mock_validate, mock_resolve):
        mock_resolve.return_value = "gpt-5"
        mock_validate.return_value = (True, "openai")

        result = ensure_valid_model("gpt5")

        assert result == "gpt-5"
        mock_resolve.assert_called_once_with("gpt5")
        mock_validate.assert_called_once_with("gpt-5")

    # * Test None input returns None
    def test_ensure_valid_model_none(self):
        result = ensure_valid_model(None)
        assert result is None

    # * Test invalid model raises typer.Exit
    @patch("src.ai.models.resolve_model_alias")
    @patch("src.ai.models.validate_model")
    @patch("src.ai.models.get_model_error_message")
    @patch("typer.echo")
    def test_ensure_valid_model_invalid(
        self, mock_echo, mock_error_msg, mock_validate, mock_resolve
    ):
        mock_resolve.return_value = "invalid-model"
        mock_validate.return_value = (False, "model_not_found")
        mock_error_msg.return_value = "Error message"

        with pytest.raises(typer.Exit) as exc_info:
            ensure_valid_model("invalid-model")

        assert exc_info.value.exit_code == 1
        mock_echo.assert_called_once_with("Error message", err=True)


# * Test API key checking functions


class TestAPIKeyChecking:
    # * Test OpenAI API key detection
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_check_openai_api_key_present(self):
        assert check_openai_api_key() is True

    @patch.dict("os.environ", {}, clear=True)
    def test_check_openai_api_key_absent(self):
        assert check_openai_api_key() is False

    # * Test Claude API key detection
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_check_claude_api_key_present(self):
        assert check_claude_api_key() is True

    @patch.dict("os.environ", {}, clear=True)
    def test_check_claude_api_key_absent(self):
        assert check_claude_api_key() is False


# * Test Ollama integration functions


class TestOllamaIntegration:
    # * Test get_ollama_models success (via check_ollama_status)
    @patch("src.ai.clients.ollama_client.check_ollama_status")
    def test_get_ollama_models_success(self, mock_check_status):
        from src.ai.types import OllamaStatus

        mock_check_status.return_value = OllamaStatus(
            available=True, models=["llama3", "mistral"], error=""
        )

        result = get_ollama_models()

        assert result == ["llama3", "mistral"]

    # * Test get_ollama_models exception handling
    @patch("src.ai.clients.ollama_client.check_ollama_status")
    def test_get_ollama_models_exception(self, mock_check_status):
        mock_check_status.side_effect = Exception("Connection failed")

        result = get_ollama_models()

        assert result == []

    # * Test is_ollama_available success (via check_ollama_status)
    @patch("src.ai.clients.ollama_client.check_ollama_status")
    def test_is_ollama_available_success(self, mock_check_status):
        from src.ai.types import OllamaStatus

        mock_check_status.return_value = OllamaStatus(
            available=True, models=["llama3"], error=""
        )

        result = is_ollama_available()

        assert result is True

    # * Test is_ollama_available exception handling
    @patch("src.ai.clients.ollama_client.check_ollama_status")
    def test_is_ollama_available_exception(self, mock_check_status):
        mock_check_status.side_effect = Exception("Import failed")

        result = is_ollama_available()

        assert result is False


# * Test provider information gathering


class TestGetModelsByProvider:
    # * Test complete provider information gathering
    @patch("src.ai.models.check_openai_api_key")
    @patch("src.ai.models.check_claude_api_key")
    @patch("src.ai.models.get_ollama_models")
    @patch("src.ai.models.is_ollama_available")
    def test_get_models_by_provider_complete(
        self, mock_ollama_avail, mock_ollama_models, mock_claude_key, mock_openai_key
    ):
        mock_openai_key.return_value = True
        mock_claude_key.return_value = False
        mock_ollama_models.return_value = ["llama3"]
        mock_ollama_avail.return_value = True

        result = get_models_by_provider()

        assert "openai" in result
        assert "claude" in result
        assert "ollama" in result

        assert result["openai"]["available"] is True
        assert result["claude"]["available"] is False
        assert result["ollama"]["available"] is True

        assert result["openai"]["models"] == OPENAI_MODELS
        assert result["claude"]["models"] == CLAUDE_MODELS
        assert result["ollama"]["models"] == ["llama3"]


# * Test utility functions


class TestUtilityFunctions:
    # * Test get_model_provider wrapper
    @patch("src.ai.models.validate_model")
    def test_get_model_provider_success(self, mock_validate):
        mock_validate.return_value = (True, "openai")

        result = get_model_provider("gpt-5")

        assert result == "openai"

    @patch("src.ai.models.validate_model")
    def test_get_model_provider_invalid(self, mock_validate):
        mock_validate.return_value = (False, "model_not_found")

        result = get_model_provider("invalid-model")

        assert result is None

    # * Test default model selection
    def test_get_default_model(self):
        result = get_default_model()
        assert result == "gpt-5-mini"


# * Test model detection functions


class TestTestModelDetection:
    # * Test test model detection in testing environment
    def test_is_test_model_in_testing(self):
        # pytest is in sys.modules during testing
        assert _is_test_model("test-model") is True
        assert _is_test_model("mock-openai") is True
        assert _is_test_model("gpt-4o") is True

    # * Test non-test model detection
    def test_is_not_test_model(self):
        assert _is_test_model("regular-model") is False
        assert _is_test_model("unknown-model") is False

    # * Test provider detection for test models
    def test_get_test_model_provider_openai(self):
        assert _get_test_model_provider("gpt-4o") == "openai"
        assert _get_test_model_provider("mock-openai") == "openai"
        assert _get_test_model_provider("test-model") == "openai"  # default

    def test_get_test_model_provider_claude(self):
        assert _get_test_model_provider("claude-opus-4") == "claude"
        assert _get_test_model_provider("mock-claude") == "claude"

    def test_get_test_model_provider_ollama(self):
        assert _get_test_model_provider("mock-ollama") == "ollama"


# * Test model constants integrity


class TestModelConstants:
    # * Test model list integrity
    def test_supported_models_completeness(self):
        expected_total = len(OPENAI_MODELS) + len(CLAUDE_MODELS)
        assert len(SUPPORTED_MODELS) == expected_total

        for model in OPENAI_MODELS:
            assert model in SUPPORTED_MODELS

        for model in CLAUDE_MODELS:
            assert model in SUPPORTED_MODELS

    # * Test alias targets are valid
    def test_model_aliases_validity(self):
        for alias, target in MODEL_ALIASES.items():
            assert (
                target in SUPPORTED_MODELS
            ), f"Alias '{alias}' points to unsupported model '{target}'"

    # * Test category models are valid
    def test_model_categories_validity(self):
        for category, models in MODEL_CATEGORIES.items():
            for model in models:
                assert (
                    model in SUPPORTED_MODELS
                ), f"Category '{category}' contains unsupported model '{model}'"
