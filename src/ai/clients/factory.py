# src/ai/clients/factory.py
# AI client factory for routing to appropriate provider based on model

from typing import Optional
from ..models import is_openai_model, is_claude_model, ensure_valid_model
from ..types import GenerateResult

# * Generate JSON response using appropriate AI client based on model
def run_generate(prompt: str, model: str) -> GenerateResult:
    # validate model first
    validated_model = ensure_valid_model(model)
    if validated_model is None:
        raise RuntimeError("Model validation failed")
    
    # route to appropriate client based on model
    if is_openai_model(validated_model):
        from .openai_client import run_generate as openai_generate
        return openai_generate(prompt, validated_model)
    elif is_claude_model(validated_model):
        from .claude_client import run_generate as claude_generate
        return claude_generate(prompt, validated_model)
    else:
        # this should never happen due to validation above
        raise RuntimeError(f"Unknown model provider for model: {validated_model}")