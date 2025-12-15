# src/ai/clients/ollama_client.py
# Ollama API client functions for generating JSON responses using local models

from typing import List, Optional

import ollama  # type: ignore

from ...config.settings import settings_manager
from ..types import GenerateResult, OllamaStatus
from ...core.exceptions import AIError
from ..utils import APICallContext, process_json_response
from ...core.debug import debug_ai, debug_error, debug_api_call


# * Per-invocation cache for Ollama status (cleared by reset_cache)
_cached_status: Optional[OllamaStatus] = None


# * Reset the cached Ollama status (call at start of each CLI invocation)
def reset_cache() -> None:
    global _cached_status
    _cached_status = None


# * Single core function to check Ollama server & retrieve models (cached)
def check_ollama_status(*, with_debug: bool = False) -> OllamaStatus:
    global _cached_status
    if _cached_status is not None:
        return _cached_status

    try:
        if with_debug:
            debug_ai("Checking Ollama server availability...")
        response = ollama.list()
        models = [m.model for m in response.models if m.model]
        if with_debug:
            debug_ai(f"Ollama server available - found {len(models)} models: {', '.join(models)}")
        _cached_status = OllamaStatus(available=True, models=models, error="")
    except Exception as e:
        if with_debug:
            debug_error(e, "Ollama server check")
        error_msg = f"Ollama server connection failed: {str(e)}. Please ensure Ollama is running locally."
        _cached_status = OllamaStatus(available=False, models=[], error=error_msg)

    return _cached_status


# * Check if Ollama server is running & accessible (backward-compat wrapper)
def is_ollama_available() -> bool:
    return check_ollama_status().available


# * Check if Ollama server is running & return detailed error if not (backward-compat wrapper)
def check_ollama_with_error() -> tuple[bool, str]:
    status = check_ollama_status(with_debug=True)
    return status.available, status.error


# * Get list of available local models from Ollama (backward-compat wrapper)
def get_available_models() -> List[str]:
    return check_ollama_status().models


# * Get list of available local models w/ detailed error reporting (backward-compat wrapper)
def get_available_models_with_error() -> tuple[List[str], str]:
    status = check_ollama_status(with_debug=True)
    return status.models, status.error


# * Internal helper to make Ollama API call & return raw context
def _make_ollama_call(prompt: str, model: str) -> APICallContext:
    settings = settings_manager.load()

    debug_api_call("Ollama", model, len(prompt))
    debug_ai(f"Making Ollama API call with model: {model}, temperature: {settings.temperature}")

    try:
        response = ollama.chat(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant. Always respond with valid JSON only, no additional text or formatting.",
                },
                {
                    "role": "user",
                    "content": f"{prompt}\n\nPlease respond with valid JSON only, no additional text or formatting.",
                },
            ],
            options={"temperature": settings.temperature},
        )

        raw_text = response.get("message", {}).get("content", "")
        debug_ai(f"Received response from Ollama: {len(raw_text)} characters")

        return APICallContext(raw_text=raw_text, provider_name="ollama", model=model)

    except Exception as e:
        debug_error(e, "Ollama API call")
        raise AIError(
            f"Ollama API error: {str(e)}. Model: {model}. Check if Ollama is running & model is properly installed."
        )


# * Generate JSON response using Ollama API w/ model validation
def run_generate(prompt: str, model: str = "llama3.2") -> GenerateResult:
    # single call to check server & get models (cached)
    status = check_ollama_status(with_debug=True)

    if not status.available:
        raise AIError(f"Ollama server error: {status.error}")

    if model not in status.models:
        if not status.models:
            error_msg = f"Model '{model}' not found & no local models available. Run 'ollama pull {model}' to install it."
        else:
            error_msg = f"Model '{model}' not found locally. Available models: {', '.join(status.models)}. Run 'ollama pull {model}' to install it."
        raise AIError(f"Ollama model error: {error_msg}")

    return process_json_response(_make_ollama_call, prompt, model)
