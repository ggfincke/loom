# src/ai/clients/openai_client.py
# OpenAI API client functions for generating JSON responses using the Responses API

import os
from openai import OpenAI
from ...config.settings import settings_manager
from ..types import GenerateResult
from ..models import ensure_valid_model
from ...core.exceptions import AIError, ConfigurationError
from ..utils import APICallContext, process_json_response


# * Internal helper to make OpenAI API call & return raw context
def _make_openai_call(prompt: str, model: str) -> APICallContext:
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


# * Generate JSON response using OpenAI API w/ model validation
def run_generate(prompt: str, model: str = "gpt-5-mini") -> GenerateResult:
    if not os.getenv("OPENAI_API_KEY"):
        raise ConfigurationError("Missing OPENAI_API_KEY in environment or .env")

    # validate model before making API call
    validated_model = ensure_valid_model(model)
    if validated_model is None:
        raise RuntimeError("Model validation failed")

    return process_json_response(_make_openai_call, prompt, validated_model)
