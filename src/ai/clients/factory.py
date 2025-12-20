# src/ai/clients/factory.py
# AI client factory for routing to appropriate provider based on model

from ..models import validate_model, get_model_error_message, resolve_model_alias
from ..types import GenerateResult

# Placeholders to keep patch targets available for tests without eager SDK imports
# Tests patch these names (e.g., "src.ai.clients.factory.openai_generate")
openai_generate = None  # type: ignore[assignment]
claude_generate = None  # type: ignore[assignment]
ollama_generate = None  # type: ignore[assignment]


# * Generate JSON response using appropriate AI client based on model
def run_generate(prompt: str, model: str) -> GenerateResult:
    # use comprehensive validation for better error messages
    valid, provider = validate_model(model)

    if not valid:
        error_msg = get_model_error_message(model)
        return GenerateResult(success=False, error=error_msg)

    # resolve model alias first
    validated_model = resolve_model_alias(model)

    # route to appropriate client based on detected provider using lazy, patch-friendly resolution
    global openai_generate, claude_generate, ollama_generate

    if provider == "openai":
        if not callable(openai_generate):  # allow tests to patch this name
            from .openai_client import run_generate as _openai_generate

            openai_generate = _openai_generate
        return openai_generate(prompt, validated_model)  # type: ignore[misc]
    elif provider == "claude":
        if not callable(claude_generate):  # allow tests to patch this name
            from .claude_client import run_generate as _claude_generate

            claude_generate = _claude_generate
        return claude_generate(prompt, validated_model)  # type: ignore[misc]
    elif provider == "ollama":
        if not callable(ollama_generate):  # allow tests to patch this name
            from .ollama_client import run_generate as _ollama_generate

            ollama_generate = _ollama_generate
        return ollama_generate(prompt, validated_model)  # type: ignore[misc]
    else:
        # this should never happen due to validation above
        error_msg = f"Unknown model provider for model: {validated_model}"
        return GenerateResult(success=False, error=error_msg)
