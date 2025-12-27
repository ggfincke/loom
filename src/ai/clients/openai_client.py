# src/ai/clients/openai_client.py
# OpenAI API client for generating JSON responses using the Responses API

from functools import lru_cache

from .base import BaseClient
from ..models import get_default_model
from ..types import GenerateResult
from ..utils import APICallContext
from ...config.env_validator import validate_provider_env, get_missing_env_message
from ...config.settings import settings_manager
from ...core.exceptions import AIError, ConfigurationError


# OpenAI API client using the Responses API
class OpenAIClient(BaseClient):

    provider_name = "openai"

    # check if OPENAI_API_KEY is available
    def validate_credentials(self) -> None:
        if not validate_provider_env("openai"):
            raise ConfigurationError(get_missing_env_message("openai"))

    # make OpenAI API call
    def make_call(self, prompt: str, model: str) -> APICallContext:
        from openai import OpenAI

        client = OpenAI()

        try:
            # GPT-5 models don't support temperature parameter
            if model.startswith("gpt-5"):
                resp = client.responses.create(model=model, input=prompt)
            else:
                settings = settings_manager.load()
                resp = client.responses.create(
                    model=model, input=prompt, temperature=settings.temperature
                )
        except Exception as e:
            raise AIError(f"OpenAI API error: {str(e)}")

        return APICallContext(
            raw_text=resp.output_text, provider_name="openai", model=model
        )


# =============================================================================
# Module-level API (backward compatibility + lazy singleton)
# =============================================================================


# get lazily-initialized singleton client
@lru_cache(maxsize=1)
def _get_client() -> OpenAIClient:
    return OpenAIClient()


# generate JSON response using OpenAI API
# returns GenerateResult w/ success/failure status & data
def run_generate(prompt: str, model: str | None = None) -> GenerateResult:
    resolved_model = model or get_default_model("openai")
    return _get_client().run_generate(prompt, resolved_model)
