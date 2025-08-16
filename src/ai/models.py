# src/ai/models.py
# OpenAI model validation & allow-list for Loom CLI

from typing import List, Optional
import typer

# supported OpenAI models allow-list
SUPPORTED_MODELS: List[str] = [
    "gpt-5",
    "gpt-5-mini",
    "gpt-5-nano",
    "gpt-4o",
    "gpt-4o-mini"
]

# model categories for user guidance
MODEL_CATEGORIES = {
    "latest": ["gpt-5", "gpt-5-mini", "gpt-5-nano"],
    "cost_effective": ["gpt-5-mini", "gpt-5-nano", "gpt-4o-mini"],
    "high_capability": ["gpt-5", "gpt-4o"]
}

# check if model is in the supported list
def validate_model(model: str) -> bool:
    return model in SUPPORTED_MODELS

# generate friendly error message for unsupported models
def get_model_error_message(invalid_model: str) -> str:
    supported_list = ", ".join(SUPPORTED_MODELS)
    return (
        f"Model '{invalid_model}' is not supported.\n"
        f"Supported models: {supported_list}\n"
        f"Recommended: gpt-5-mini (latest generation, cost-efficient) or gpt-5 (highest capability)"
    )

# * Validate model & show error if invalid; returns None if invalid
def ensure_valid_model(model: Optional[str]) -> Optional[str]:
    if model is None:
        return None
    
    if not validate_model(model):
        typer.echo(get_model_error_message(model), err=True)
        raise typer.Exit(1)
    
    return model

# get the recommended default model
def get_default_model() -> str:
    return "gpt-5-mini"