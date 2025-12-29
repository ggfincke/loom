# tests/unit/ai/test_models.py
# Unit tests for AI model catalog, alias resolution & defaults

from unittest.mock import Mock, patch
import pytest
import sys
import typer

from src.ai.models import (
    resolve_model_alias,
    get_default_model,
    get_provider_for_model,
    OPENAI_MODELS,
    CLAUDE_MODELS,
    SUPPORTED_MODELS,
    MODEL_ALIASES,
    MODEL_CATEGORIES,
    DEFAULT_MODELS_BY_PROVIDER,
)
from src.ai.provider_validator import (
    validate_model,
    get_model_error_message,
    check_openai_api_key,
    check_anthropic_api_key,
    get_ollama_models,
    is_ollama_available,
    get_models_by_provider,
    get_model_provider,
    reset_model_cache,
)
from src.cli.model_helpers import ensure_valid_model_cli
from src.ai.cache import AICache


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
    # * Test OpenAI model validation w/ API key available
    @patch("src.ai.provider_validator.check_openai_api_key")
    # * Verify validate openai model with key
    def test_validate_openai_model_with_key(self, mock_check_key):
        mock_check_key.return_value = True

        valid, provider = validate_model("gpt-5")

        assert valid is True
        assert provider == "openai"

    # * Test OpenAI model validation w/o API key
    @patch("src.ai.provider_validator.check_openai_api_key")
    # * Verify validate openai model without key
    def test_validate_openai_model_without_key(self, mock_check_key):
        mock_check_key.return_value = False

        valid, provider = validate_model("gpt-5")

        assert valid is False
        assert provider == "openai_key_missing"

    # * Test Claude model validation w/ API key available
    @patch("src.ai.provider_validator.check_anthropic_api_key")
    # * Verify validate claude model with key
    def test_validate_claude_model_with_key(self, mock_check_key):
        mock_check_key.return_value = True

        valid, provider = validate_model("claude-opus-4-1-20250805")

        assert valid is True
        assert provider == "anthropic"

    # * Test Claude model validation w/o API key
    @patch("src.ai.provider_validator.check_anthropic_api_key")
    # * Verify validate claude model without key
    def test_validate_claude_model_without_key(self, mock_check_key):
        mock_check_key.return_value = False

        valid, provider = validate_model("claude-opus-4-1-20250805")

        assert valid is False
        assert provider == "anthropic_key_missing"

    # * Test Ollama model validation when available
    @patch("src.ai.provider_validator.get_ollama_models")
    @patch("src.ai.provider_validator.is_ollama_available")
    # * Verify validate ollama model available
    def test_validate_ollama_model_available(self, mock_is_available, mock_get_models):
        mock_get_models.return_value = ["llama3", "mistral", "codellama"]
        mock_is_available.return_value = True

        valid, provider = validate_model("llama3")

        assert valid is True
        assert provider == "ollama"

    # * Test Ollama model validation when Ollama available but model missing
    @patch("src.ai.provider_validator.get_ollama_models")
    @patch("src.ai.provider_validator.is_ollama_available")
    # * Verify validate ollama model missing
    def test_validate_ollama_model_missing(self, mock_is_available, mock_get_models):
        mock_get_models.return_value = ["llama3", "mistral"]
        mock_is_available.return_value = True

        valid, provider = validate_model("nonexistent-model")

        assert valid is False
        assert provider == "ollama_model_missing"

    # * Test model validation when not found anywhere
    @patch("src.ai.provider_validator.get_ollama_models")
    @patch("src.ai.provider_validator.is_ollama_available")
    # * Verify validate model not found
    def test_validate_model_not_found(self, mock_is_available, mock_get_models):
        mock_get_models.return_value = []
        mock_is_available.return_value = False

        valid, provider = validate_model("unknown-model")

        assert valid is False
        assert provider == "model_not_found"


# * Test model error message generation


class TestGetModelErrorMessage:
    # * Test error message for missing OpenAI API key
    @patch("src.ai.provider_validator.validate_model")
    # * Verify error message openai key missing
    def test_error_message_openai_key_missing(self, mock_validate):
        mock_validate.return_value = (False, "openai_key_missing")

        message = get_model_error_message("gpt-5")

        assert "requires OPENAI_API_KEY environment variable" in message
        assert "gpt-5" in message

    # * Test error message for missing Claude API key
    @patch("src.ai.provider_validator.validate_model")
    # * Verify error message anthropic key missing
    def test_error_message_anthropic_key_missing(self, mock_validate):
        mock_validate.return_value = (False, "anthropic_key_missing")

        message = get_model_error_message("claude-opus-4")

        assert "requires ANTHROPIC_API_KEY environment variable" in message
        assert "claude-opus-4" in message

    # * Test error message for missing Ollama model w/ available models
    @patch("src.ai.provider_validator.validate_model")
    @patch("src.ai.provider_validator.get_ollama_models")
    # * Verify error message ollama model missing with available
    def test_error_message_ollama_model_missing_with_available(
        self, mock_get_models, mock_validate
    ):
        mock_validate.return_value = (False, "ollama_model_missing")
        mock_get_models.return_value = ["llama3", "mistral"]

        message = get_model_error_message("nonexistent")

        assert "not found in Ollama" in message
        assert "Available local models: llama3, mistral" in message


# * Test ensure_valid_model_cli functionality (moved to cli/model_helpers.py)


class TestEnsureValidModelCli:
    # * Test successful validation returns resolved model
    @patch("src.cli.model_helpers.validate_model")
    # * Verify ensure valid model success
    def test_ensure_valid_model_cli_success(self, mock_validate):
        mock_validate.return_value = (True, "openai")

        result = ensure_valid_model_cli("gpt5")

        # gpt5 resolves to gpt-5
        assert result == "gpt-5"

    # * Test None input returns None
    def test_ensure_valid_model_cli_none(self):
        result = ensure_valid_model_cli(None)
        assert result is None

    # * Test invalid model raises typer.Exit
    @patch("src.cli.model_helpers.validate_model")
    @patch("src.cli.model_helpers.get_model_error_message")
    @patch("typer.echo")
    # * Verify ensure valid model invalid
    def test_ensure_valid_model_cli_invalid(
        self, mock_echo, mock_error_msg, mock_validate
    ):
        mock_validate.return_value = (False, "model_not_found")
        mock_error_msg.return_value = "Error message"

        with pytest.raises(typer.Exit) as exc_info:
            ensure_valid_model_cli("invalid-model")

        assert exc_info.value.exit_code == 1
        mock_echo.assert_called_once_with("Error message", err=True)


# * Test API key checking functions


class TestAPIKeyChecking:
    # * Test OpenAI API key detection
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    # * Verify check openai api key present
    def test_check_openai_api_key_present(self):
        AICache.invalidate_all()  # clear cache
        assert check_openai_api_key() is True

    @patch.dict("os.environ", {}, clear=True)
    # * Verify check openai api key absent
    def test_check_openai_api_key_absent(self):
        AICache.invalidate_all()  # clear cache
        assert check_openai_api_key() is False

    # * Test Anthropic API key detection
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    # * Verify check anthropic api key present
    def test_check_anthropic_api_key_present(self):
        AICache.invalidate_all()  # clear cache
        assert check_anthropic_api_key() is True

    @patch.dict("os.environ", {}, clear=True)
    # * Verify check anthropic api key absent
    def test_check_anthropic_api_key_absent(self):
        AICache.invalidate_all()  # clear cache
        assert check_anthropic_api_key() is False


# * Test utility functions


class TestUtilityFunctions:
    # * Test get_model_provider wrapper
    @patch("src.ai.provider_validator.validate_model")
    # * Verify get model provider success
    def test_get_model_provider_success(self, mock_validate):
        mock_validate.return_value = (True, "openai")

        result = get_model_provider("gpt-5")

        assert result == "openai"

    @patch("src.ai.provider_validator.validate_model")
    # * Verify get model provider invalid
    def test_get_model_provider_invalid(self, mock_validate):
        mock_validate.return_value = (False, "model_not_found")

        result = get_model_provider("invalid-model")

        assert result is None

    # * Test default model selection
    def test_get_default_model_global(self):
        result = get_default_model()
        assert result == "gpt-5-mini"

    # * Verify get default model by provider
    def test_get_default_model_by_provider(self):
        assert get_default_model("openai") == "gpt-5-mini"
        assert get_default_model("anthropic") == "claude-sonnet-4-20250514"
        assert get_default_model("ollama") == "llama3.2"

    # * Test get_provider_for_model (static check only)
    def test_get_provider_for_model_openai(self):
        assert get_provider_for_model("gpt-5") == "openai"
        assert get_provider_for_model("gpt-4o") == "openai"

    # * Verify get provider for model anthropic
    def test_get_provider_for_model_anthropic(self):
        assert get_provider_for_model("claude-opus-4-1-20250805") == "anthropic"
        assert get_provider_for_model("claude-sonnet-4-20250514") == "anthropic"

    # * Verify get provider for model unknown
    def test_get_provider_for_model_unknown(self):
        assert get_provider_for_model("llama3") is None  # Ollama is dynamic
        assert get_provider_for_model("unknown") is None


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

    # * Test default models are valid
    def test_default_models_validity(self):
        # OpenAI & Anthropic defaults should be in SUPPORTED_MODELS
        assert DEFAULT_MODELS_BY_PROVIDER["openai"] in SUPPORTED_MODELS
        assert DEFAULT_MODELS_BY_PROVIDER["anthropic"] in SUPPORTED_MODELS
        # Ollama default is dynamic, just check it's a string
        assert isinstance(DEFAULT_MODELS_BY_PROVIDER["ollama"], str)
