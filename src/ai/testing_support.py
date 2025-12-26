# src/ai/testing_support.py
# Test-only model utilities - NOT for production imports
#
# ! This module should ONLY be imported by test code.
# ! Production code should use provider_validator.py for model validation.

import sys


# * Test model names accepted during testing
TEST_MODELS: list[str] = [
    "persistent-test",
    "gpt-4o",
    "gpt-4o-mini",
    "test-model",
    "mock-openai",
    "mock-claude",
    "mock-ollama",
    "mock-anthropic",
]


def is_test_environment() -> bool:
    """Check if we're running in a test environment."""
    return "pytest" in sys.modules or "unittest" in sys.modules


def is_test_model(model: str) -> bool:
    """Check if model is a test model (only valid in test environment)."""
    return is_test_environment() and model in TEST_MODELS


def get_test_model_provider(model: str) -> str:
    """Get provider ID for a test model.

    Returns canonical provider IDs: "openai", "anthropic", "ollama".
    """
    if model.startswith("gpt-") or model == "mock-openai":
        return "openai"
    elif model.startswith("claude-") or model in ("mock-claude", "mock-anthropic"):
        return "anthropic"
    elif model == "mock-ollama":
        return "ollama"
    return "openai"  # default for unknown test models
