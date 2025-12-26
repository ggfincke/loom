# src/ai/clients/claude_client.py
# Claude (Anthropic) API client for generating JSON responses

from functools import lru_cache

from .base import BaseClient
from ..models import get_default_model
from ..types import GenerateResult
from ..utils import APICallContext
from ...config.env_validator import validate_provider_env, get_missing_env_message
from ...config.settings import settings_manager
from ...core.exceptions import AIError, ConfigurationError


class ClaudeClient(BaseClient):
    """Anthropic Claude API client."""

    provider_name = "anthropic"

    def validate_credentials(self) -> None:
        """Check if ANTHROPIC_API_KEY is available."""
        if not validate_provider_env("anthropic"):
            raise ConfigurationError(get_missing_env_message("anthropic"))

    def make_call(self, prompt: str, model: str) -> APICallContext:
        """Make Claude API call."""
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
            raise AIError(f"Anthropic API error: {str(e)}")

        # extract text from response (process text blocks only & skip tool blocks)
        raw_text = ""
        for content_block in response.content:
            if content_block.type == "text":
                raw_text += content_block.text

        return APICallContext(raw_text=raw_text, provider_name="anthropic", model=model)


# =============================================================================
# Module-level API (backward compatibility + lazy singleton)
# =============================================================================


@lru_cache(maxsize=1)
def _get_client() -> ClaudeClient:
    """Get lazily-initialized singleton client."""
    return ClaudeClient()


def run_generate(prompt: str, model: str | None = None) -> GenerateResult:
    """Generate JSON response using Claude API.

    Args:
        prompt: The prompt to send
        model: Model name (defaults to provider default if None)

    Returns:
        GenerateResult with success/failure status and data
    """
    resolved_model = model or get_default_model("anthropic")
    return _get_client().run_generate(prompt, resolved_model)
