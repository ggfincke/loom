# src/ai/clients/ollama_client.py
# Ollama API client for generating JSON responses using local models

from __future__ import annotations

from functools import lru_cache

from .base import BaseClient
from ..cache import AICache
from ..models import get_default_model
from ..types import GenerateResult, OllamaStatus
from ..utils import APICallContext
from ...config.settings import settings_manager
from ...core.exceptions import AIError, ProviderError
from ...core.output import get_output_manager


# * Ollama API client for local model inference
class OllamaClient(BaseClient):

    provider_name = "ollama"

    # * Check Ollama server status before making API call
    def preflight(self) -> None:
        status = self._check_ollama_status(with_debug=True)
        if not status.available:
            raise AIError(f"Ollama server error: {status.error}")

    # Ollama doesn't require API key - validation handled by preflight
    def validate_credentials(self) -> None:
        pass

    # * Validate model exists in Ollama's local model list
    def validate_model(self, model: str) -> str:
        status = self._check_ollama_status()

        if model not in status.models:
            if not status.models:
                error_msg = f"Model '{model}' not found & no local models available. Run 'ollama pull {model}' to install it."
            else:
                error_msg = f"Model '{model}' not found locally. Available models: {', '.join(status.models)}. Run 'ollama pull {model}' to install it."
            raise AIError(f"Ollama model error: {error_msg}")

        return model

    # * Make Ollama API call w/ JSON-only response mode
    def make_call(self, prompt: str, model: str) -> APICallContext:
        import ollama  # type: ignore

        settings = settings_manager.load()
        output = get_output_manager()

        output.debug(
            f"Ollama API call - Model: {model}, Prompt: {len(prompt)} chars", "API"
        )
        output.debug(
            f"Making Ollama API call with model: {model}, temperature: {settings.temperature}",
            "AI",
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
            output.debug(
                f"Received response from Ollama: {len(raw_text)} characters", "AI"
            )

            return APICallContext(
                raw_text=raw_text, provider_name="ollama", model=model
            )

        except Exception as e:
            output.debug(
                f"Ollama API call - Exception: {type(e).__name__}: {str(e)}", "ERROR"
            )
            # Check for ResponseError (Ollama's main error type)
            if hasattr(ollama, "ResponseError") and isinstance(e, ollama.ResponseError):
                raise ProviderError(
                    f"Ollama API error: {e}",
                    provider="ollama",
                ) from e
            # Check for connection errors
            if isinstance(e, (ConnectionError, OSError)):
                raise ProviderError(
                    f"Ollama connection failed: {e}. Check if Ollama is running.",
                    provider="ollama",
                ) from e
            # Fallback for unexpected errors
            raise AIError(
                f"Ollama API error: {e}. Model: {model}. Check if Ollama is running & model is installed."
            ) from e

    # check & cache Ollama server status (returns available models & error)
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

            output = get_output_manager()
            if with_debug:
                output.debug("Checking Ollama server availability...", "AI")

            response = ollama.list()
            models = [m.model for m in response.models if m.model]

            if with_debug:
                output.debug(
                    f"Ollama server available - found {len(models)} models: {', '.join(models)}",
                    "AI",
                )

            AICache.set_ollama_status(models)
            return OllamaStatus(available=True, models=models, error="")

        except Exception as e:
            if with_debug:
                output = get_output_manager()
                output.debug(
                    f"Ollama server check - Exception: {type(e).__name__}: {str(e)}",
                    "ERROR",
                )

            error_msg = f"Ollama server connection failed: {str(e)}. Please ensure Ollama is running locally."
            AICache.set_ollama_status(None, error_msg)
            return OllamaStatus(available=False, models=[], error=error_msg)


# get lazily-initialized singleton client
@lru_cache(maxsize=1)
def _get_client() -> OllamaClient:
    return OllamaClient()


# * Generate JSON response using Ollama API
def run_generate(prompt: str, model: str | None = None) -> GenerateResult:
    resolved_model = model or get_default_model("ollama")
    return _get_client().run_generate(prompt, resolved_model)


# check Ollama server status (cached)
def check_ollama_status(*, with_debug: bool = False) -> OllamaStatus:
    return _get_client()._check_ollama_status(with_debug=with_debug)


# check if Ollama server is running & return detailed error if not
def check_ollama_with_error() -> tuple[bool, str]:
    status = check_ollama_status(with_debug=True)
    return status.available, status.error


# get list of available local models w/ detailed error reporting
def get_available_models_with_error() -> tuple[list[str], str]:
    status = check_ollama_status(with_debug=True)
    return status.models, status.error
