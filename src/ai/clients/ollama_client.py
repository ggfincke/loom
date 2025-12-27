# src/ai/clients/ollama_client.py
# Ollama API client for generating JSON responses using local models

from functools import lru_cache
from typing import List

from .base import BaseClient
from ..cache import AICache
from ..models import get_default_model
from ..types import GenerateResult, OllamaStatus
from ..utils import APICallContext
from ...config.settings import settings_manager
from ...core.exceptions import AIError
from ...core.debug import debug_ai, debug_error, debug_api_call


# Ollama API client for local model inference
class OllamaClient(BaseClient):

    provider_name = "ollama"

    # check Ollama server status before making API call
    def preflight(self) -> None:
        status = self._check_ollama_status(with_debug=True)
        if not status.available:
            raise AIError(f"Ollama server error: {status.error}")

    # Ollama doesn't require API key - handled by preflight
    def validate_credentials(self) -> None:
        pass

    # validate model exists in Ollama's local model list
    def validate_model(self, model: str) -> str:
        status = self._check_ollama_status()

        if model not in status.models:
            if not status.models:
                error_msg = f"Model '{model}' not found & no local models available. Run 'ollama pull {model}' to install it."
            else:
                error_msg = f"Model '{model}' not found locally. Available models: {', '.join(status.models)}. Run 'ollama pull {model}' to install it."
            raise AIError(f"Ollama model error: {error_msg}")

        return model

    # make Ollama API call
    def make_call(self, prompt: str, model: str) -> APICallContext:
        import ollama  # type: ignore

        settings = settings_manager.load()

        debug_api_call("Ollama", model, len(prompt))
        debug_ai(
            f"Making Ollama API call with model: {model}, temperature: {settings.temperature}"
        )

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

            return APICallContext(
                raw_text=raw_text, provider_name="ollama", model=model
            )

        except Exception as e:
            debug_error(e, "Ollama API call")
            raise AIError(
                f"Ollama API error: {str(e)}. Model: {model}. Check if Ollama is running & model is properly installed."
            )

    # check & cache Ollama server status
    def _check_ollama_status(self, *, with_debug: bool = False) -> OllamaStatus:
        # check cache first
        if AICache.is_ollama_cached():
            cached_models = AICache.get_ollama_models()
            cached_error = AICache.get_ollama_error()
            if cached_models is not None:
                return OllamaStatus(available=True, models=cached_models, error="")
            elif cached_error:
                return OllamaStatus(available=False, models=[], error=cached_error)

        # fetch from server
        try:
            import ollama  # type: ignore

            if with_debug:
                debug_ai("Checking Ollama server availability...")

            response = ollama.list()
            models = [m.model for m in response.models if m.model]

            if with_debug:
                debug_ai(
                    f"Ollama server available - found {len(models)} models: {', '.join(models)}"
                )

            AICache.set_ollama_status(models)
            return OllamaStatus(available=True, models=models, error="")

        except Exception as e:
            if with_debug:
                debug_error(e, "Ollama server check")

            error_msg = f"Ollama server connection failed: {str(e)}. Please ensure Ollama is running locally."
            AICache.set_ollama_status(None, error_msg)
            return OllamaStatus(available=False, models=[], error=error_msg)


# =============================================================================
# Module-level API (backward compatibility + lazy singleton)
# =============================================================================


# get lazily-initialized singleton client
@lru_cache(maxsize=1)
def _get_client() -> OllamaClient:
    return OllamaClient()


# generate JSON response using Ollama API
# returns GenerateResult w/ success/failure status & data
def run_generate(prompt: str, model: str | None = None) -> GenerateResult:
    resolved_model = model or get_default_model("ollama")
    return _get_client().run_generate(prompt, resolved_model)


# =============================================================================
# Backward-compatibility wrappers (used by other modules)
# =============================================================================


# reset the Ollama cache
def reset_cache() -> None:
    AICache.invalidate_provider("ollama")
    _get_client.cache_clear()


# check Ollama server status (cached)
def check_ollama_status(*, with_debug: bool = False) -> OllamaStatus:
    return _get_client()._check_ollama_status(with_debug=with_debug)


# check if Ollama server is running & accessible
def is_ollama_available() -> bool:
    return check_ollama_status().available


# check if Ollama server is running & return detailed error if not
def check_ollama_with_error() -> tuple[bool, str]:
    status = check_ollama_status(with_debug=True)
    return status.available, status.error


# get list of available local models from Ollama
def get_available_models() -> List[str]:
    return check_ollama_status().models


# get list of available local models w/ detailed error reporting
def get_available_models_with_error() -> tuple[List[str], str]:
    status = check_ollama_status(with_debug=True)
    return status.models, status.error
