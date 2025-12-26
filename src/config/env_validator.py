# src/config/env_validator.py
# Centralized environment variable registry for provider credentials

import os
from typing import Optional


# * Required environment variables by provider ID
REQUIRED_ENV_VARS: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}


def get_required_env_var(provider: str) -> Optional[str]:
    """Get the required environment variable name for a provider."""
    return REQUIRED_ENV_VARS.get(provider)


def validate_provider_env(provider: str) -> bool:
    """Check if required environment variable is set for provider.

    Returns True if:
    - Provider has no env requirement (e.g., ollama)
    - Provider's required env var is set & non-empty
    """
    var_name = REQUIRED_ENV_VARS.get(provider)
    if var_name is None:
        return True  # no requirement for this provider
    return bool(os.getenv(var_name))


def get_missing_env_message(provider: str) -> str:
    """Generate error message for missing environment variable."""
    var_name = REQUIRED_ENV_VARS.get(provider)
    if var_name is None:
        return f"Provider '{provider}' does not require an API key."
    return f"Missing {var_name} in environment or .env"
