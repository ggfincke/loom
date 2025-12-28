# src/ai/clients/claude_client.py
# Claude (Anthropic) API client for generating JSON responses

from __future__ import annotations

from .base import BaseClient
from ..utils import APICallContext
from ...config.settings import settings_manager
from ...core.exceptions import AIError, ProviderError, RateLimitError


# * Anthropic Claude API client for JSON generation
class ClaudeClient(BaseClient):

    provider_name = "anthropic"
    required_env_vars = ["ANTHROPIC_API_KEY"]

    # * Make Claude API call w/ JSON-only response mode
    def make_call(self, prompt: str, model: str) -> APICallContext:
        import anthropic
        from anthropic import Anthropic

        client = Anthropic()
        settings = settings_manager.load()

        try:
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                temperature=settings.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": f"{prompt}\n\nPlease respond with valid JSON only, no additional text or formatting.",
                    }
                ],
            )
        except Exception as e:
            # Safely check for provider-specific exception types (may not exist in mocks)
            rate_limit_error = getattr(anthropic, "RateLimitError", None)
            api_status_error = getattr(anthropic, "APIStatusError", None)
            api_connection_error = getattr(anthropic, "APIConnectionError", None)

            # Check for rate limit (429)
            if rate_limit_error and isinstance(e, rate_limit_error):
                raise RateLimitError(
                    f"Anthropic rate limit exceeded: {e}",
                    provider="anthropic",
                    retry_after=getattr(e, "retry_after", None),
                ) from e
            # Check for API errors (4xx/5xx)
            if api_status_error and isinstance(e, api_status_error):
                status_code = getattr(e, "status_code", "unknown")
                message = getattr(e, "message", str(e))
                raise ProviderError(
                    f"Anthropic API error ({status_code}): {message}",
                    provider="anthropic",
                ) from e
            # Check for connection errors
            if api_connection_error and isinstance(e, api_connection_error):
                raise ProviderError(
                    f"Anthropic connection error: {e}",
                    provider="anthropic",
                ) from e
            # Fallback for unexpected errors
            raise AIError(f"Anthropic API error: {e}") from e

        # extract text from response (process text blocks only & skip tool blocks)
        raw_text = ""
        for content_block in response.content:
            if content_block.type == "text":
                raw_text += content_block.text

        return APICallContext(raw_text=raw_text, provider_name="anthropic", model=model)
