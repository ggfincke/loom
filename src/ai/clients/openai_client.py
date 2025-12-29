# src/ai/clients/openai_client.py
# OpenAI API client for generating JSON responses using the Responses API

from __future__ import annotations

from .base import BaseClient
from ..utils import APICallContext
from ...config.settings import settings_manager
from ...core.exceptions import AIError, ProviderError, RateLimitError


# * OpenAI API client using the Responses API
class OpenAIClient(BaseClient):

    provider_name = "openai"
    required_env_vars = ["OPENAI_API_KEY"]

    # * Make OpenAI API call using Responses API
    def make_call(self, prompt: str, model: str) -> APICallContext:
        import openai
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
            # Safely check for provider-specific exception types (may not exist in mocks)
            rate_limit_error = getattr(openai, "RateLimitError", None)
            api_status_error = getattr(openai, "APIStatusError", None)
            api_connection_error = getattr(openai, "APIConnectionError", None)

            # Check for rate limit (429)
            if rate_limit_error and isinstance(e, rate_limit_error):
                raise RateLimitError(
                    f"OpenAI rate limit exceeded: {e}",
                    provider="openai",
                    retry_after=getattr(e, "retry_after", None),
                ) from e
            # Check for API errors (4xx/5xx)
            if api_status_error and isinstance(e, api_status_error):
                status_code = getattr(e, "status_code", "unknown")
                message = getattr(e, "message", str(e))
                raise ProviderError(
                    f"OpenAI API error ({status_code}): {message}",
                    provider="openai",
                ) from e
            # Check for connection errors
            if api_connection_error and isinstance(e, api_connection_error):
                raise ProviderError(
                    f"OpenAI connection error: {e}",
                    provider="openai",
                ) from e
            # Fallback for unexpected errors
            raise AIError(f"OpenAI API error: {e}") from e

        return APICallContext(
            raw_text=resp.output_text, provider_name="openai", model=model
        )
