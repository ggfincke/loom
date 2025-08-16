# src/ai/models.py
# AI model validation & allow-list for Loom CLI (OpenAI & Claude)

from typing import List, Optional
import typer

# supported OpenAI models
OPENAI_MODELS: List[str] = [
    "gpt-5",
    "gpt-5-mini",
    "gpt-5-nano",
    "gpt-4o",
    "gpt-4o-mini"
]

# supported Claude models
CLAUDE_MODELS: List[str] = [
    "claude-opus-4-1-20250805",
    "claude-opus-4-20250514",
    "claude-sonnet-4-20250514",
    "claude-3-7-sonnet-20250219",
    "claude-3-5-haiku-20241022",
    "claude-3-haiku-20240307"
]

# combined supported models list
SUPPORTED_MODELS: List[str] = OPENAI_MODELS + CLAUDE_MODELS

# model aliases for user-friendly short names
MODEL_ALIASES = {
    # Claude 4 series
    "claude-opus-4.1": "claude-opus-4-1-20250805",
    "claude-opus-4": "claude-opus-4-20250514", 
    "claude-sonnet-4": "claude-sonnet-4-20250514",
    
    # Claude 3 series
    "claude-sonnet-3.7": "claude-3-7-sonnet-20250219",
    "claude-haiku-3.5": "claude-3-5-haiku-20241022",
    "claude-haiku-3": "claude-3-haiku-20240307",
    
    # OpenAI variations (already short, but add common variations)
    "gpt4o": "gpt-4o",
    "gpt4": "gpt-4o",
    "gpt5": "gpt-5",
    "gpt-5m": "gpt-5-mini",
    "gpt-5n": "gpt-5-nano"
}

# model categories for user guidance
MODEL_CATEGORIES = {
    "latest": ["gpt-5", "gpt-5-mini", "gpt-5-nano", "claude-opus-4-1-20250805", "claude-sonnet-4-20250514"],
    "cost_effective": ["gpt-5-mini", "gpt-5-nano", "gpt-4o-mini", "claude-3-5-haiku-20241022", "claude-3-haiku-20240307"],
    "high_capability": ["gpt-5", "gpt-4o", "claude-opus-4-1-20250805", "claude-opus-4-20250514", "claude-sonnet-4-20250514"]
}

# * Resolve model alias to full model name
def resolve_model_alias(model: str) -> str:
    # first check if it's already a valid full model name
    if model in SUPPORTED_MODELS:
        return model
    
    # then check if it's an alias
    if model in MODEL_ALIASES:
        return MODEL_ALIASES[model]
    
    # return original if no alias found
    return model

# check if model is in the supported list
def validate_model(model: str) -> bool:
    return model in SUPPORTED_MODELS

# detect if model is OpenAI or Claude
def is_openai_model(model: str) -> bool:
    return model in OPENAI_MODELS

def is_claude_model(model: str) -> bool:
    return model in CLAUDE_MODELS

# generate friendly error message for unsupported models
def get_model_error_message(invalid_model: str) -> str:
    openai_list = ", ".join(OPENAI_MODELS)
    claude_list = ", ".join(CLAUDE_MODELS)
    
    # show popular aliases for easier discovery
    alias_examples = [
        "claude-sonnet-4", "claude-opus-4", "claude-sonnet-3.7",
        "claude-haiku-3.5", "gpt4o", "gpt5"
    ]
    alias_list = ", ".join(alias_examples)
    
    return (
        f"Model '{invalid_model}' is not supported.\n"
        f"Supported OpenAI models: {openai_list}\n"
        f"Supported Claude models: {claude_list}\n"
        f"Popular aliases: {alias_list}\n"
        f"Recommended: claude-sonnet-4 (Claude, high capability) or gpt-5-mini (OpenAI, cost-efficient)"
    )

# * Validate model & show error if invalid; returns resolved model name if valid
def ensure_valid_model(model: Optional[str]) -> Optional[str]:
    if model is None:
        return None
    
    # resolve alias first
    resolved_model = resolve_model_alias(model)
    
    if not validate_model(resolved_model):
        typer.echo(get_model_error_message(model), err=True)
        raise typer.Exit(1)
    
    return resolved_model

# get the recommended default model
def get_default_model() -> str:
    return "gpt-5-mini"