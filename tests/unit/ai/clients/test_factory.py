# tests/unit/ai/clients/test_factory.py
# Unit tests for AI client routing, response parsing & error handling

import pytest
from unittest.mock import patch, Mock
import json

from src.ai.clients.factory import run_generate, CLIENT_REGISTRY
from src.ai.types import GenerateResult
from tests.test_support.mock_ai import DeterministicMockAI


# * Test AI client factory routing & provider selection
class TestAIClientRouting:

    # * Test OpenAI models route to OpenAI client
    def test_openai_model_routing(self):
        mock_result = GenerateResult(
            success=True,
            data={"result": "success"},
            raw_text='{"result": "success"}',
            json_text='{"result": "success"}',
        )

        # create a mock client class
        mock_client_instance = Mock()
        mock_client_instance.run_generate.return_value = mock_result

        mock_client_class = Mock(return_value=mock_client_instance)

        # patch the registry to return our mock
        with (
            patch.dict(CLIENT_REGISTRY, {"openai": lambda: mock_client_class}),
            patch(
                "src.ai.clients.factory.validate_model", return_value=(True, "openai")
            ),
            patch(
                "src.ai.clients.factory.ModelRegistry.resolve_alias",
                return_value="gpt-5-mini",
            ),
        ):
            result = run_generate("Test prompt", "gpt-5-mini")

            assert result.success
            assert result.data == {"result": "success"}
            mock_client_instance.run_generate.assert_called_once_with(
                "Test prompt", "gpt-5-mini"
            )

    # * Test Claude models route to Claude client
    def test_claude_model_routing(self):
        mock_result = GenerateResult(
            success=True,
            data={"version": 1, "ops": []},
            raw_text='{"version": 1, "ops": []}',
            json_text='{"version": 1, "ops": []}',
        )

        mock_client_instance = Mock()
        mock_client_instance.run_generate.return_value = mock_result

        mock_client_class = Mock(return_value=mock_client_instance)

        with (
            patch.dict(CLIENT_REGISTRY, {"anthropic": lambda: mock_client_class}),
            patch(
                "src.ai.clients.factory.validate_model",
                return_value=(True, "anthropic"),
            ),
            patch(
                "src.ai.clients.factory.ModelRegistry.resolve_alias",
                return_value="claude-sonnet-4-20250514",
            ),
        ):
            result = run_generate("Test prompt", "claude-sonnet-4-20250514")

            assert result.success
            mock_client_instance.run_generate.assert_called_once()

    # * Test Ollama models route to Ollama client
    def test_ollama_model_routing(self):
        mock_result = GenerateResult(
            success=True,
            data={"sections": []},
            raw_text='{"sections": []}',
            json_text='{"sections": []}',
        )

        mock_client_instance = Mock()
        mock_client_instance.run_generate.return_value = mock_result

        mock_client_class = Mock(return_value=mock_client_instance)

        with (
            patch.dict(CLIENT_REGISTRY, {"ollama": lambda: mock_client_class}),
            patch(
                "src.ai.clients.factory.validate_model",
                return_value=(True, "ollama"),
            ),
            patch(
                "src.ai.clients.factory.ModelRegistry.resolve_alias",
                return_value="llama3.2",
            ),
        ):
            result = run_generate("Test prompt", "llama3.2")

            assert result.success
            mock_client_instance.run_generate.assert_called_once()

    # * Test invalid models are rejected before client calls
    def test_invalid_model_rejection(self):
        with patch("src.ai.clients.factory.validate_model", return_value=(False, None)):
            result = run_generate("Test prompt", "nonexistent-model")

            assert not result.success
            assert (
                "not available" in result.error.lower()
                or "not found" in result.error.lower()
                or "error" in result.error.lower()
            )

    # * Test model aliases are resolved before routing
    def test_model_alias_resolution(self):
        mock_result = GenerateResult(
            success=True,
            data={"result": "success"},
            raw_text='{"result": "success"}',
            json_text='{"result": "success"}',
        )

        mock_client_instance = Mock()
        mock_client_instance.run_generate.return_value = mock_result

        mock_client_class = Mock(return_value=mock_client_instance)

        with (
            patch.dict(CLIENT_REGISTRY, {"openai": lambda: mock_client_class}),
            patch(
                "src.ai.clients.factory.validate_model", return_value=(True, "openai")
            ),
            patch(
                "src.ai.clients.factory.ModelRegistry.resolve_alias",
                return_value="gpt-5",
            ) as resolve_mock,
        ):
            result = run_generate("Test prompt", "gpt5")

            assert result.success
            # verify alias was resolved
            resolve_mock.assert_called_once_with("gpt5")
            # verify client was called w/ resolved model
            mock_client_instance.run_generate.assert_called_once_with(
                "Test prompt", "gpt-5"
            )


# * Test response parsing for all providers
class TestResponseParsing:

    @pytest.fixture
    def mock_ai(self):
        return DeterministicMockAI()

    # * Test successful OpenAI response parsing
    def test_openai_successful_parsing(self, mock_ai):
        result = mock_ai.generate(
            prompt="You are a resume section parser. Analyze this resume.",
            model="gpt-5-mini",
            scenario="success",
        )

        assert result.success
        assert result.data is not None
        assert isinstance(result.data, dict)
        assert "sections" in result.data
        assert result.raw_text is not None
        assert result.json_text is not None

    # * Test successful Anthropic response parsing
    def test_anthropic_successful_parsing(self, mock_ai):
        result = mock_ai.generate(
            prompt="You are a resume editor. Generate tailored edits.",
            model="claude-sonnet-4-20250514",
            scenario="success",
        )

        assert result.success
        assert result.data is not None
        assert isinstance(result.data, dict)
        assert "version" in result.data
        assert "ops" in result.data
        assert result.raw_text is not None
        assert result.json_text is not None

    # * Test successful Ollama response parsing
    def test_ollama_successful_parsing(self, mock_ai):
        result = mock_ai.generate(
            prompt="You are a resume section parser. Parse sections.",
            model="llama3.2",
            scenario="success",
        )

        assert result.success
        assert result.data is not None
        assert isinstance(result.data, dict)
        assert "sections" in result.data
        assert result.raw_text is not None
        assert result.json_text is not None

    # * Test malformed JSON responses handled gracefully
    def test_malformed_json_handling(self, mock_ai):
        providers_models = [
            ("gpt-5-mini", "openai"),
            ("claude-sonnet-4-20250514", "anthropic"),
            ("llama3.2", "ollama"),
        ]

        for model, provider in providers_models:
            result = mock_ai.generate(
                prompt="Test prompt", model=model, scenario="malformed_json"
            )

            assert not result.success, f"Expected failure for {provider} malformed JSON"
            assert "JSON parsing failed" in result.error
            assert result.raw_text is not None
            assert result.json_text is not None
            assert result.data is None

    # * Test markdown code blocks stripped correctly
    def test_markdown_code_block_stripping(self, mock_ai):
        result = mock_ai.generate(
            prompt="Test prompt",
            model="claude-sonnet-4-20250514",
            scenario="malformed_json",
        )

        # even though parsing fails, code blocks should be stripped
        assert "```" not in result.json_text

    # * Verify ollama thinking token stripping
    def test_ollama_thinking_token_stripping(self, mock_ai):
        # Test Ollama thinking tokens are stripped correctly
        result = mock_ai.generate(
            prompt="You are a resume section parser.",
            model="llama3.2",
            scenario="success",
        )

        # thinking tokens should be stripped from json_text
        assert "<think>" not in result.json_text
        assert "</think>" not in result.json_text
        # but preserved in raw_text
        assert "<think>" in result.raw_text


# * Test error handling scenarios across providers
class TestErrorHandling:

    @pytest.fixture
    def mock_ai(self):
        return DeterministicMockAI()

    # * Test OpenAI rate limit errors handled properly
    def test_openai_rate_limit_handling(self, mock_ai):
        result = mock_ai.generate(
            prompt="Test prompt", model="gpt-4o-mini", scenario="rate_limit_error"
        )

        assert not result.success
        assert "rate limit" in result.error.lower()
        assert result.data is None

    # * Test OpenAI timeout errors handled properly
    def test_openai_timeout_handling(self, mock_ai):
        result = mock_ai.generate(
            prompt="Test prompt", model="gpt-4o-mini", scenario="timeout_error"
        )

        assert not result.success
        assert "timeout" in result.error.lower() or "timed out" in result.error.lower()
        assert result.data is None

    # * Test Anthropic API errors handled properly
    def test_anthropic_api_error_handling(self, mock_ai):
        result = mock_ai.generate(
            prompt="Test prompt", model="claude-sonnet-4-20250514", scenario="api_error"
        )

        assert not result.success
        assert (
            "overloaded" in result.error.lower() or "anthropic" in result.error.lower()
        )
        assert result.data is None

    # * Test Ollama connection errors handled properly
    def test_ollama_connection_error_handling(self, mock_ai):
        result = mock_ai.generate(
            prompt="Test prompt", model="llama3.2", scenario="connection_error"
        )

        assert not result.success
        assert "connect" in result.error.lower() or "ollama" in result.error.lower()
        assert result.data is None

    # * Test Ollama model-not-found errors handled properly
    def test_ollama_model_not_found_handling(self, mock_ai):
        result = mock_ai.generate(
            prompt="Test prompt",
            model="nonexistent-model",
            scenario="model_not_found",
        )

        assert not result.success
        assert "not found" in result.error.lower()
        assert "available models" in result.error.lower()
        assert result.data is None


# * Test prompt kind detection for fixture selection
class TestPromptKindDetection:

    @pytest.fixture
    def mock_ai(self):
        return DeterministicMockAI()

    # * Test sectionizer prompts detected correctly
    def test_sectionizer_prompt_detection(self, mock_ai):
        prompts = [
            "You are a resume section parser. Analyze this resume.",
            "Parse the following resume and analyze its sections.",
            "Resume section detection task for the following content.",
        ]

        for prompt in prompts:
            result = mock_ai.generate(prompt, "gpt-5-mini", "success")
            assert result.success
            assert "sections" in result.data

    # * Test tailor prompts detected correctly
    def test_tailor_prompt_detection(self, mock_ai):
        prompts = [
            "You are a resume editor tasked with tailoring a resume.",
            "Generate resume edits to tailor content for this job.",
            "Resume tailoring task for the following job description.",
        ]

        for prompt in prompts:
            result = mock_ai.generate(prompt, "gpt-5-mini", "success")
            assert result.success
            assert "ops" in result.data
            assert "version" in result.data

    # * Test unknown prompts fall back to sectionizer
    def test_unknown_prompt_fallback(self, mock_ai):
        result = mock_ai.generate(
            "Some random prompt that doesn't match patterns.", "gpt-5-mini", "success"
        )

        assert result.success
        assert "sections" in result.data


# * Test integration w/ client functions
class TestClientIntegration:

    # * Test factory preserves model validation logic
    def test_factory_preserves_model_validation(self):
        result = run_generate("Test prompt", "definitely-not-a-real-model-9999")

        assert not result.success
        assert (
            "not available" in result.error.lower()
            or "not found" in result.error.lower()
            or "unknown" in result.error.lower()
        )

    # * Test factory provides helpful error messages
    def test_factory_error_message_quality(self):
        result = run_generate("Test prompt", "invalid-model")

        assert not result.success
        assert len(result.error) > 20  # should be descriptive
        assert any(
            word in result.error.lower()
            for word in ["available", "models", "api", "key", "install", "requires"]
        )


# * Test GenerateResult object construction
class TestGenerateResultValidation:

    # * Test successful results have expected structure
    def test_successful_result_structure(self):
        mock_ai = DeterministicMockAI()
        result = mock_ai.generate("Test prompt", "gpt-5-mini", "success")

        assert result.success is True
        assert result.data is not None
        assert isinstance(result.data, dict)
        assert result.raw_text is not None
        assert isinstance(result.raw_text, str)
        assert result.json_text is not None
        assert isinstance(result.json_text, str)
        assert result.error == ""

    # * Test failed results have expected structure
    def test_failed_result_structure(self):
        mock_ai = DeterministicMockAI()
        result = mock_ai.generate("Test prompt", "gpt-5-mini", "malformed_json")

        assert result.success is False
        assert result.data is None
        assert result.raw_text is not None
        assert result.json_text is not None
        assert result.error != ""
        assert isinstance(result.error, str)

    # * Test error results have expected structure
    def test_error_result_structure(self):
        mock_ai = DeterministicMockAI()
        result = mock_ai.generate("Test prompt", "gpt-5-mini", "rate_limit_error")

        assert result.success is False
        assert result.data is None
        assert result.error != ""
        assert isinstance(result.error, str)
        assert result.raw_text == ""
        assert result.json_text == ""


# * Test provider-specific response handling behavior
class TestProviderSpecificBehavior:

    @pytest.fixture
    def mock_ai(self):
        return DeterministicMockAI()

    # * Test OpenAI Responses API format handling
    def test_openai_responses_api_format(self, mock_ai):
        result = mock_ai.generate(
            "You are a resume section parser.", "gpt-5-mini", "success"
        )

        assert result.success
        # OpenAI fixture should have output_text directly
        assert result.raw_text == result.json_text

    # * Test Anthropic Messages API format handling
    def test_anthropic_messages_api_format(self, mock_ai):
        result = mock_ai.generate(
            "You are a resume editor.", "claude-sonnet-4-20250514", "success"
        )

        assert result.success
        assert isinstance(result.raw_text, str)
        assert len(result.raw_text) > 0

    # * Test Ollama chat API format handling
    def test_ollama_chat_api_format(self, mock_ai):
        result = mock_ai.generate(
            "You are a resume section parser.", "llama3.2", "success"
        )

        assert result.success
        assert isinstance(result.raw_text, str)
        assert len(result.raw_text) > 0

    # * Test all providers produce compatible GenerateResult objects
    def test_all_providers_produce_compatible_results(self, mock_ai):
        models = ["gpt-5-mini", "claude-sonnet-4-20250514", "llama3.2"]

        for model in models:
            result = mock_ai.generate(
                "You are a resume section parser.", model, "success"
            )

            assert result.success
            assert isinstance(result.data, dict)
            assert "sections" in result.data
            assert isinstance(result.raw_text, str)
            assert isinstance(result.json_text, str)
            assert result.error == ""
