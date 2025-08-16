# src/ai/clients/factory.py
# AI client factory for routing to appropriate provider based on model

from ..models import validate_model, get_model_error_message, resolve_model_alias
from ..types import GenerateResult
from .openai_client import run_generate as openai_generate
from .claude_client import run_generate as claude_generate
from .ollama_client import run_generate as ollama_generate

# * Generate JSON response using appropriate AI client based on model
def run_generate(prompt: str, model: str) -> GenerateResult:
    # use comprehensive validation for better error messages
    valid, provider = validate_model(model)
    
    if not valid:
        error_msg = get_model_error_message(model)
        return GenerateResult(success=False, error=error_msg)
    
    # resolve model alias first
    validated_model = resolve_model_alias(model)
    
    # route to appropriate client based on detected provider
    if provider == "openai":
        return openai_generate(prompt, validated_model)
    elif provider == "claude":
        return claude_generate(prompt, validated_model)
    elif provider == "ollama":
        return ollama_generate(prompt, validated_model)
    else:
        # this should never happen due to validation above
        error_msg = f"Unknown model provider for model: {validated_model}"
        return GenerateResult(success=False, error=error_msg)