# src/ai/clients/openai_client.py
# OpenAI API client functions for generating JSON responses using the Responses API

import os
import json
from openai import OpenAI
from ...config.settings import settings_manager
from ..types import GenerateResult
from ..models import ensure_valid_model
from ...core.exceptions import AIError, ConfigurationError
from ..utils import strip_markdown_code_blocks

# * Generate JSON response using OpenAI API w/ model validation
def run_generate(prompt: str, model: str = "gpt-5-mini") -> GenerateResult:
    if not os.getenv("OPENAI_API_KEY"):
        raise ConfigurationError("Missing OPENAI_API_KEY in environment or .env")
    
    # validate model before making API call
    validated_model = ensure_valid_model(model)
    if validated_model is None:
        # ensure_valid_model already showed error & exited, this should not happen
        raise RuntimeError("Model validation failed")
    
    client = OpenAI()
    
    try:
        # GPT-5 models don't support temperature parameter
        if validated_model.startswith("gpt-5"):
            resp = client.responses.create(model=validated_model, input=prompt)
        else:
            settings = settings_manager.load()
            resp = client.responses.create(model=validated_model, input=prompt, temperature=settings.temperature)
    except Exception as e:
        # normalize provider API errors to AIError for consistent handling
        raise AIError(f"OpenAI API error: {str(e)}")
    
    # raw response text
    raw_text = resp.output_text
    
    # strip code blocks to extract JSON
    json_text = strip_markdown_code_blocks(raw_text)
    
    # ensure valid JSON (model should already be constrained by prompt)
    try:
        data = json.loads(json_text)
        return GenerateResult(success=True, data=data, raw_text=raw_text, json_text=json_text)
    except json.JSONDecodeError as e:
        # return error result instead of raising
        error_msg = f"JSON parsing failed: {str(e)}"
        return GenerateResult(success=False, raw_text=raw_text, json_text=json_text, error=error_msg)