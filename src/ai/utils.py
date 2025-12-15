# src/ai/utils.py
# Shared utility functions for AI clients

import json
import re
from dataclasses import dataclass
from typing import Callable

from .types import GenerateResult


# * Context object for API call results (used by process_json_response)
@dataclass(slots=True)
class APICallContext:
    raw_text: str  # raw response text from provider
    provider_name: str  # provider name (openai, claude, ollama)
    model: str  # model used for the call


# * Process API response into GenerateResult w/ consistent JSON parsing
def process_json_response(
    api_call: Callable[[str, str], APICallContext], prompt: str, model: str
) -> GenerateResult:
    ctx = api_call(prompt, model)
    json_text = strip_markdown_code_blocks(ctx.raw_text)

    try:
        data = json.loads(json_text)
        return GenerateResult(
            success=True, data=data, raw_text=ctx.raw_text, json_text=json_text
        )
    except json.JSONDecodeError as e:
        truncated = json_text[:200] + ("..." if len(json_text) > 200 else "")
        msg = f"JSON parsing failed: {e}. Model: {ctx.model}. Stripped text: {truncated}"
        return GenerateResult(
            success=False, raw_text=ctx.raw_text, json_text=json_text, error=msg
        )


# * Strip markdown code blocks & thinking tokens from AI responses
def strip_markdown_code_blocks(text: str) -> str:
    # first strip thinking tokens if present
    thinking_pattern = r"<think>.*?</think>\s*(.*)"
    thinking_match = re.match(thinking_pattern, text.strip(), re.DOTALL)
    if thinking_match:
        text = thinking_match.group(1).strip()

    # then strip markdown code blocks
    code_block_pattern = r"^```(?:json)?\s*\n(.*?)\n```\s*$"
    match = re.match(code_block_pattern, text.strip(), re.DOTALL)

    if match:
        return match.group(1)
    else:
        return text.strip()
