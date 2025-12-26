# src/ai/clients/claude_client.py
# Claude API client functions for generating JSON responses

import os
from anthropic import Anthropic
from ...config.settings import settings_manager
from ..types import GenerateResult
from ..models import ensure_valid_model
from ...core.exceptions import AIError, ConfigurationError
from ..utils import APICallContext, process_json_response


# * Internal helper to make Claude API call & return raw context
def _make_claude_call(prompt: str, model: str) -> APICallContext:
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

    return APICallContext(raw_text=raw_text, provider_name="claude", model=model)


# * Generate JSON response via Claude API w/ model validation
def run_generate(
    prompt: str, model: str = "claude-sonnet-4-20250514"
) -> GenerateResult:
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise ConfigurationError("Missing ANTHROPIC_API_KEY in environment or .env")

    # validate model before API call
    validated_model = ensure_valid_model(model)
    assert validated_model is not None, "Model validation returned None unexpectedly"
    return process_json_response(_make_claude_call, prompt, validated_model)
