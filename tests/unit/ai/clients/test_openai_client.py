# tests/unit/ai/clients/test_openai_client.py
# Unit tests for OpenAI client functionality

import pytest
import json
import os
from unittest.mock import patch, Mock

from src.ai.clients.openai_client import OpenAIClient
from src.ai.types import GenerateResult
from src.core.exceptions import AIError, ConfigurationError


# * Helper function to run generate using client directly (no more module-level API)
def _run_generate(prompt: str, model: str) -> GenerateResult:
    client = OpenAIClient()
    return client.run_generate(prompt, model)


class TestOpenAIClient:

    # * Test successful API call w/ valid JSON response
    @patch("openai.OpenAI")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    # * Verify run generate success
    def test_run_generate_success(self, mock_openai_class):
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.output_text = (
            '{"edits": [{"op": "replace_line", "line": 1, "text": "Updated content"}]}'
        )
        mock_client.responses.create.return_value = mock_response

        result = _run_generate("Test prompt", "gpt-4o")

        assert result.success is True
        assert result.data == {
            "edits": [{"op": "replace_line", "line": 1, "text": "Updated content"}]
        }
        assert result.raw_text == mock_response.output_text
        assert result.json_text == mock_response.output_text
        assert result.error == ""

        # Verify API call was made
        mock_client.responses.create.assert_called_once()

    # * Test successful API call w/ GPT-5 model (no temperature)
    @patch("openai.OpenAI")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    # * Verify run generate gpt5 no temperature
    def test_run_generate_gpt5_no_temperature(self, mock_openai_class):
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.output_text = '{"result": "success"}'
        mock_client.responses.create.return_value = mock_response

        result = _run_generate("Test prompt", "gpt-5-mini")

        assert result.success is True

        # Verify GPT-5 call doesn't include temperature
        mock_client.responses.create.assert_called_once_with(
            model="gpt-5-mini",
            input="Test prompt",
            # No temperature parameter for gpt-5
        )

    # * Test missing API key error
    @patch.dict(os.environ, {}, clear=True)
    # * Verify run generate missing api key
    def test_run_generate_missing_api_key(self):
        # When no API key, run_generate returns error result (base class catches exception)
        result = _run_generate("Test prompt", "gpt-4o")

        assert result.success is False
        assert "OPENAI_API_KEY" in result.error or "openai" in result.error.lower()

    # * Test OpenAI API error handling
    @patch("openai.OpenAI")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    # * Verify run generate api error
    def test_run_generate_api_error(self, mock_openai_class):
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        # Simulate API error
        mock_client.responses.create.side_effect = Exception("API rate limit exceeded")

        result = _run_generate("Test prompt", "gpt-4o")

        assert result.success is False
        assert "OpenAI API error" in result.error
        assert "API rate limit exceeded" in result.error

    # * Test JSON parsing failure
    @patch("openai.OpenAI")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    # * Verify run generate json parsing error
    def test_run_generate_json_parsing_error(self, mock_openai_class):
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.output_text = "Invalid JSON content { not valid }"
        mock_client.responses.create.return_value = mock_response

        result = _run_generate("Test prompt", "gpt-4o")

        assert result.success is False
        assert result.data is None
        assert result.raw_text == "Invalid JSON content { not valid }"
        assert result.json_text == "Invalid JSON content { not valid }"
        assert "JSON parsing failed" in result.error

    # * Test markdown code block stripping
    @patch("openai.OpenAI")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    # * Verify run generate strips markdown
    def test_run_generate_strips_markdown(self, mock_openai_class):
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        markdown_response = """```json
{"edits": [{"op": "replace_line", "line": 1, "text": "Content"}]}
```"""

        mock_response = Mock()
        mock_response.output_text = markdown_response
        mock_client.responses.create.return_value = mock_response

        result = _run_generate("Test prompt", "gpt-4o")

        assert result.success is True
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
    @patch("openai.OpenAI")
    @patch("src.ai.clients.openai_client.settings_manager")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    # * Verify run generate custom temperature
    def test_run_generate_custom_temperature(
        self, mock_settings_manager, mock_openai_class
    ):
        mock_settings = Mock()
        mock_settings.temperature = 0.7
        mock_settings_manager.load.return_value = mock_settings

        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.output_text = '{"result": "test"}'
        mock_client.responses.create.return_value = mock_response

        result = _run_generate("Test prompt", "gpt-4o")

        assert result.success is True

        # Verify custom temperature is used
        mock_client.responses.create.assert_called_once_with(
            model="gpt-4o", input="Test prompt", temperature=0.7
        )

    # * Test default model parameter
    @patch("openai.OpenAI")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    # * Verify run generate default model
    def test_run_generate_default_model(self, mock_openai_class):
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.output_text = '{"result": "test"}'
        mock_client.responses.create.return_value = mock_response

        # Call w/ explicit model (no more module-level default model)
        result = _run_generate("Test prompt", "gpt-4o")

        assert result.success is True
        # Verify API was called
        mock_client.responses.create.assert_called_once()

    # * Test empty response handling
    @patch("openai.OpenAI")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    # * Verify run generate empty response
    def test_run_generate_empty_response(self, mock_openai_class):
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.output_text = ""  # Empty response
        mock_client.responses.create.return_value = mock_response

        result = _run_generate("Test prompt", "gpt-4o")

        # Empty string is not valid JSON
        assert result.success is False
        assert result.raw_text == ""
        assert result.json_text == ""
        assert "JSON parsing failed" in result.error

    # * Test complex JSON response handling
    @patch("openai.OpenAI")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    # * Verify run generate complex json
    def test_run_generate_complex_json(self, mock_openai_class):
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

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

        result = _run_generate("Test prompt", "gpt-4o")

        assert result.success is True
        assert result.data == complex_json
        assert result.data is not None
        assert len(result.data["ops"]) == 2
        assert result.data["meta"]["model"] == "gpt-4o"
        assert result.data["ops"][0]["confidence"] == 0.9


# * Test OpenAIClient class directly
class TestOpenAIClientClass:

    # * Test validate_credentials raises ConfigurationError when key missing
    @patch.dict(os.environ, {}, clear=True)
    # * Verify validate credentials missing key
    def test_validate_credentials_missing_key(self):
        client = OpenAIClient()
        with pytest.raises(ConfigurationError):
            client.validate_credentials()

    # * Test validate_credentials succeeds when key present
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    # * Verify validate credentials w/ key
    def test_validate_credentials_with_key(self):
        client = OpenAIClient()
        # Should not raise
        client.validate_credentials()

    # * Test provider_name is correct
    def test_provider_name(self):
        client = OpenAIClient()
        assert client.provider_name == "openai"
