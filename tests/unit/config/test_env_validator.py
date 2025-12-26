# tests/unit/config/test_env_validator.py
# Unit tests for environment variable validation

import os
import pytest
from unittest.mock import patch

from src.config.env_validator import (
    REQUIRED_ENV_VARS,
    get_required_env_var,
    validate_provider_env,
    get_missing_env_message,
)


class TestRequiredEnvVars:
    """Test REQUIRED_ENV_VARS registry."""

    def test_openai_requires_api_key(self):
        assert REQUIRED_ENV_VARS["openai"] == "OPENAI_API_KEY"

    def test_anthropic_requires_api_key(self):
        assert REQUIRED_ENV_VARS["anthropic"] == "ANTHROPIC_API_KEY"

    def test_ollama_has_no_requirement(self):
        assert "ollama" not in REQUIRED_ENV_VARS


class TestGetRequiredEnvVar:
    """Test get_required_env_var function."""

    def test_returns_openai_var_name(self):
        assert get_required_env_var("openai") == "OPENAI_API_KEY"

    def test_returns_anthropic_var_name(self):
        assert get_required_env_var("anthropic") == "ANTHROPIC_API_KEY"

    def test_returns_none_for_unknown_provider(self):
        assert get_required_env_var("ollama") is None
        assert get_required_env_var("unknown") is None


class TestValidateProviderEnv:
    """Test validate_provider_env function."""

    def test_openai_valid_when_key_set(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            assert validate_provider_env("openai") is True

    def test_openai_invalid_when_key_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            assert validate_provider_env("openai") is False

    def test_openai_invalid_when_key_empty(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=True):
            assert validate_provider_env("openai") is False

    def test_anthropic_valid_when_key_set(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            assert validate_provider_env("anthropic") is True

    def test_anthropic_invalid_when_key_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            assert validate_provider_env("anthropic") is False

    def test_ollama_always_valid(self):
        # Ollama has no env requirement
        with patch.dict(os.environ, {}, clear=True):
            assert validate_provider_env("ollama") is True

    def test_unknown_provider_always_valid(self):
        # Unknown providers have no requirement
        with patch.dict(os.environ, {}, clear=True):
            assert validate_provider_env("unknown_provider") is True


class TestGetMissingEnvMessage:
    """Test get_missing_env_message function."""

    def test_openai_message(self):
        msg = get_missing_env_message("openai")
        assert "OPENAI_API_KEY" in msg
        assert "Missing" in msg

    def test_anthropic_message(self):
        msg = get_missing_env_message("anthropic")
        assert "ANTHROPIC_API_KEY" in msg
        assert "Missing" in msg

    def test_ollama_message(self):
        msg = get_missing_env_message("ollama")
        assert "does not require" in msg

    def test_unknown_provider_message(self):
        msg = get_missing_env_message("unknown")
        assert "does not require" in msg
