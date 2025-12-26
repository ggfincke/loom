# tests/unit/test_openai_client.py
# Unit tests for OpenAI client functionality

import pytest
import json
import os
from unittest.mock import patch, Mock, MagicMock

from src.ai.clients.openai_client import run_generate
from src.ai.types import GenerateResult
from src.core.exceptions import AIError, ConfigurationError


class TestOpenAIClient:

    # * Test successful API call with valid JSON response
    @patch("src.ai.clients.openai_client.OpenAI")
    @patch("src.ai.clients.openai_client.ensure_valid_model")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_run_generate_success(self, mock_ensure_valid, mock_openai_class):
        # setup mocks
        mock_ensure_valid.return_value = "gpt-4o"

        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.output_text = (
            '{"edits": [{"op": "replace_line", "line": 1, "text": "Updated content"}]}'
        )
        mock_client.responses.create.return_value = mock_response

        # test successful generation
        result = run_generate("Test prompt", "gpt-4o")

        # verify result
        assert result.success == True
        assert result.data == {
            "edits": [{"op": "replace_line", "line": 1, "text": "Updated content"}]
        }
        assert result.raw_text == mock_response.output_text
        assert result.json_text == mock_response.output_text
        assert result.error == ""

        # verify API call
        mock_client.responses.create.assert_called_once_with(
            model="gpt-4o", input="Test prompt", temperature=0.2  # default temperature
        )

    # * Test successful API call with GPT-5 model (no temperature)
    @patch("src.ai.clients.openai_client.OpenAI")
    @patch("src.ai.clients.openai_client.ensure_valid_model")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_run_generate_gpt5_no_temperature(
        self, mock_ensure_valid, mock_openai_class
    ):
        # setup mocks for GPT-5 model
        mock_ensure_valid.return_value = "gpt-5-mini"

        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.output_text = '{"result": "success"}'
        mock_client.responses.create.return_value = mock_response

        result = run_generate("Test prompt", "gpt-5-mini")

        assert result.success == True

        # verify GPT-5 call doesn't include temperature
        mock_client.responses.create.assert_called_once_with(
            model="gpt-5-mini",
            input="Test prompt",
            # no temperature parameter
        )

    # * Test missing API key error
    @patch.dict(os.environ, {}, clear=True)
    def test_run_generate_missing_api_key(self):
        with pytest.raises(ConfigurationError, match="Missing OPENAI_API_KEY"):
            run_generate("Test prompt")

    # * Test assertion on unexpected None from model validation
    # Note: This tests a defensive assertion - ensure_valid_model() never returns None
    # with a valid input, but we assert against it as a safety net
    @patch("src.ai.clients.openai_client.ensure_valid_model")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_run_generate_asserts_on_none_model(self, mock_ensure_valid):
        mock_ensure_valid.return_value = None  # simulate unexpected None

        with pytest.raises(AssertionError, match="Model validation returned None"):
            run_generate("Test prompt", "invalid-model")

    # * Test OpenAI API error handling
    @patch("src.ai.clients.openai_client.OpenAI")
    @patch("src.ai.clients.openai_client.ensure_valid_model")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_run_generate_api_error(self, mock_ensure_valid, mock_openai_class):
        mock_ensure_valid.return_value = "gpt-4o"

        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        # simulate API error
        mock_client.responses.create.side_effect = Exception("API rate limit exceeded")

        with pytest.raises(AIError, match="OpenAI API error: API rate limit exceeded"):
            run_generate("Test prompt")

    # * Test JSON parsing failure
    @patch("src.ai.clients.openai_client.OpenAI")
    @patch("src.ai.clients.openai_client.ensure_valid_model")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_run_generate_json_parsing_error(
        self, mock_ensure_valid, mock_openai_class
    ):
        mock_ensure_valid.return_value = "gpt-4o"

        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        # return invalid JSON
        mock_response = Mock()
        mock_response.output_text = "Invalid JSON content { not valid }"
        mock_client.responses.create.return_value = mock_response

        result = run_generate("Test prompt")

        # should return error result instead of raising
        assert result.success == False
        assert result.data is None
        assert result.raw_text == "Invalid JSON content { not valid }"
        assert result.json_text == "Invalid JSON content { not valid }"
        assert "JSON parsing failed" in result.error

    # * Test markdown code block stripping
    @patch("src.ai.clients.openai_client.OpenAI")
    @patch("src.ai.clients.openai_client.ensure_valid_model")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_run_generate_strips_markdown(self, mock_ensure_valid, mock_openai_class):
        mock_ensure_valid.return_value = "gpt-4o"

        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        # response with markdown code blocks
        markdown_response = """```json
{"edits": [{"op": "replace_line", "line": 1, "text": "Content"}]}
```"""

        mock_response = Mock()
        mock_response.output_text = markdown_response
        mock_client.responses.create.return_value = mock_response

        result = run_generate("Test prompt")

        assert result.success == True
        assert result.raw_text == markdown_response
        # json_text should have markdown stripped
        assert (
            result.json_text
            == '{"edits": [{"op": "replace_line", "line": 1, "text": "Content"}]}'
        )
        assert result.data == {
            "edits": [{"op": "replace_line", "line": 1, "text": "Content"}]
        }

    # * Test custom temperature setting
    @patch("src.ai.clients.openai_client.OpenAI")
    @patch("src.ai.clients.openai_client.ensure_valid_model")
    @patch("src.ai.clients.openai_client.settings_manager")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_run_generate_custom_temperature(
        self, mock_settings_manager, mock_ensure_valid, mock_openai_class
    ):
        mock_ensure_valid.return_value = "gpt-4o"

        # mock custom settings with different temperature
        mock_settings = Mock()
        mock_settings.temperature = 0.7
        mock_settings_manager.load.return_value = mock_settings

        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.output_text = '{"result": "test"}'
        mock_client.responses.create.return_value = mock_response

        result = run_generate("Test prompt", "gpt-4o")

        assert result.success == True

        # verify custom temperature is used
        mock_client.responses.create.assert_called_once_with(
            model="gpt-4o", input="Test prompt", temperature=0.7
        )

    # * Test default model parameter
    @patch("src.ai.clients.openai_client.OpenAI")
    @patch("src.ai.clients.openai_client.ensure_valid_model")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_run_generate_default_model(self, mock_ensure_valid, mock_openai_class):
        mock_ensure_valid.return_value = "gpt-5-mini"

        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.output_text = '{"result": "test"}'
        mock_client.responses.create.return_value = mock_response

        # call without specifying model (should use default)
        result = run_generate("Test prompt")

        assert result.success == True

        # verify ensure_valid_model was called with default
        mock_ensure_valid.assert_called_once_with("gpt-5-mini")

    # * Test empty response handling
    @patch("src.ai.clients.openai_client.OpenAI")
    @patch("src.ai.clients.openai_client.ensure_valid_model")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_run_generate_empty_response(self, mock_ensure_valid, mock_openai_class):
        mock_ensure_valid.return_value = "gpt-4o"

        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.output_text = ""  # empty response
        mock_client.responses.create.return_value = mock_response

        result = run_generate("Test prompt")

        # empty string is not valid JSON
        assert result.success == False
        assert result.raw_text == ""
        assert result.json_text == ""
        assert "JSON parsing failed" in result.error

    # * Test complex JSON response handling
    @patch("src.ai.clients.openai_client.OpenAI")
    @patch("src.ai.clients.openai_client.ensure_valid_model")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_run_generate_complex_json(self, mock_ensure_valid, mock_openai_class):
        mock_ensure_valid.return_value = "gpt-4o"

        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        # complex nested JSON response
        complex_json = {
            "version": 1,
            "meta": {"strategy": "targeted", "model": "gpt-4o", "confidence": 0.95},
            "ops": [
                {
                    "op": "replace_line",
                    "line": 5,
                    "text": "Senior Full Stack Developer at Tech Corp (2020-2023)",
                    "reason": "Update job title to match requirements",
                    "confidence": 0.9,
                },
                {
                    "op": "insert_after",
                    "line": 8,
                    "text": "- Built microservices architecture using Docker & Kubernetes",
                    "reason": "Add relevant technical achievement",
                    "confidence": 0.85,
                },
            ],
        }

        mock_response = Mock()
        mock_response.output_text = json.dumps(complex_json, indent=2)
        mock_client.responses.create.return_value = mock_response

        result = run_generate("Test prompt")

        assert result.success == True
        assert result.data == complex_json
        assert result.data is not None
        assert len(result.data["ops"]) == 2
        assert result.data["meta"]["model"] == "gpt-4o"
        assert result.data["ops"][0]["confidence"] == 0.9

    # * Test different API key sources
    @patch("src.ai.clients.openai_client.OpenAI")
    @patch("src.ai.clients.openai_client.ensure_valid_model")
    def test_run_generate_api_key_from_env(self, mock_ensure_valid, mock_openai_class):
        mock_ensure_valid.return_value = "gpt-4o"

        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.output_text = '{"test": true}'
        mock_client.responses.create.return_value = mock_response

        # test with API key in environment
        with patch.dict(os.environ, {"OPENAI_API_KEY": "env-test-key"}):
            result = run_generate("Test prompt")
            assert result.success == True

            # verify OpenAI client was instantiated (implicitly uses env var)
            mock_openai_class.assert_called_once()

        # test without API key - should raise error
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ConfigurationError):
                run_generate("Test prompt")


# * Test integration with other components
class TestOpenAIClientIntegration:

    # * Test ensure_valid_model integration
    @patch("src.ai.clients.openai_client.OpenAI")
    @patch("src.ai.clients.openai_client.ensure_valid_model")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_model_validation_integration(self, mock_ensure_valid, mock_openai_class):
        # test that model validation is called with correct parameters
        mock_ensure_valid.return_value = "validated-model"

        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.output_text = '{"result": "success"}'
        mock_client.responses.create.return_value = mock_response

        result = run_generate("Test prompt", "custom-model")

        # verify ensure_valid_model was called with the provided model
        mock_ensure_valid.assert_called_once_with("custom-model")

        # verify API call uses validated model name
        mock_client.responses.create.assert_called_once()
        call_args = mock_client.responses.create.call_args
        assert call_args[1]["model"] == "validated-model"

    # * Test settings_manager integration
    @patch("src.ai.clients.openai_client.OpenAI")
    @patch("src.ai.clients.openai_client.ensure_valid_model")
    @patch("src.ai.clients.openai_client.settings_manager")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_settings_manager_integration(
        self, mock_settings_manager, mock_ensure_valid, mock_openai_class
    ):
        mock_ensure_valid.return_value = "gpt-4o"

        # create mock settings with specific values
        mock_settings = Mock()
        mock_settings.temperature = 0.3
        mock_settings_manager.load.return_value = mock_settings

        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.output_text = '{"test": "value"}'
        mock_client.responses.create.return_value = mock_response

        result = run_generate("Test prompt", "gpt-4o")

        # verify settings are loaded and used
        mock_settings_manager.load.assert_called_once()

        # verify temperature from settings is used
        call_args = mock_client.responses.create.call_args
        assert call_args[1]["temperature"] == 0.3

    # * Test strip_markdown_code_blocks integration (via process_json_response)
    @patch("src.ai.clients.openai_client.OpenAI")
    @patch("src.ai.clients.openai_client.ensure_valid_model")
    @patch("src.ai.utils.strip_markdown_code_blocks")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_markdown_stripping_integration(
        self, mock_strip_markdown, mock_ensure_valid, mock_openai_class
    ):
        mock_ensure_valid.return_value = "gpt-4o"

        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        raw_response = '```json\n{"result": "test"}\n```'
        cleaned_json = '{"result": "test"}'

        mock_response = Mock()
        mock_response.output_text = raw_response
        mock_client.responses.create.return_value = mock_response

        # mock the markdown stripping function
        mock_strip_markdown.return_value = cleaned_json

        result = run_generate("Test prompt")

        # verify strip_markdown_code_blocks was called
        mock_strip_markdown.assert_called_once_with(raw_response)

        # verify the result uses stripped JSON
        assert result.success == True
        assert result.raw_text == raw_response
        assert result.json_text == cleaned_json
        assert result.data == {"result": "test"}
