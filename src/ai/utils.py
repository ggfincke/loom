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
        msg = (
            f"JSON parsing failed: {e}. Model: {ctx.model}. Stripped text: {truncated}"
        )
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


# * Convert GenerateResult to dict, raising appropriate error on failure
def convert_result_to_dict(
    result: GenerateResult,
    model: str,
    context: str,
    *,
    include_snippets: bool = True,
) -> dict:
    # ! import here to avoid circular dependency w/ core module
    from ..core.exceptions import JSONParsingError, AIError
    from ..core.debug import debug_error

    if not result.success:
        debug_error(Exception(result.error), f"AI {context} failed for model {model}")

        # distinguish API errors (no response) from parsing errors (got response)
        has_raw = isinstance(result.raw_text, str) and len(result.raw_text) > 0
        has_json = isinstance(result.json_text, str) and len(result.json_text) > 0
        has_response = has_raw or has_json

        if has_response:
            # got a response but couldn't parse it - JSONParsingError
            lines = result.json_text.split("\n") if result.json_text else []
            snippet = (
                "\n".join(lines[:5]) + "\n..." if len(lines) > 5 else result.json_text
            )
            error_msg = f"AI generated invalid JSON during {context} using model '{model}':\n{snippet}\nError: {result.error}"
            if result.raw_text and result.raw_text != result.json_text:
                error_msg += f"\nFull raw response: {result.raw_text[:300]}{'...' if len(result.raw_text) > 300 else ''}"
            raise JSONParsingError(error_msg)
        else:
            # API call failed with no response - AIError
            raise AIError(f"AI failed to process {context}: {result.error}")

    return result.data


# * Validate AI response structure for edit JSON
def validate_edits_structure(
    data: dict,
    model: str,
    context: str,
    *,
    require_ops: bool = True,
    require_single_op: bool = False,
    log_version_debug: bool = False,
    log_structure: bool = False,
) -> dict:
    # ! import here to avoid circular dependency w/ core module
    from ..core.exceptions import AIError
    from ..core.debug import debug_ai

    context_hint = f" during {context}" if context else ""

    if not isinstance(data, dict):
        raise AIError(
            f"AI response is not a valid JSON object (got {type(data).__name__}){context_hint} for model '{model}'"
        )

    if data.get("version") != 1:
        if log_version_debug:
            debug_ai(
                f"Full JSON response: {str(data)[:500]}{'...' if len(str(data)) > 500 else ''}"
            )
        raise AIError(
            f"Invalid or missing version in AI response: {data.get('version')} (expected 1){context_hint} for model '{model}'"
        )

    if require_ops and ("meta" not in data or "ops" not in data):
        missing_fields = []
        if "meta" not in data:
            missing_fields.append("meta")
        if "ops" not in data:
            missing_fields.append("ops")
        raise AIError(
            f"AI response missing required fields: {', '.join(missing_fields)}{context_hint} for model '{model}'"
        )

    if require_single_op:
        if "ops" not in data or not data["ops"]:
            raise AIError(
                "AI response missing 'ops' array or ops array is empty for PROMPT operation"
            )
        if len(data["ops"]) != 1:
            raise AIError(
                f"AI response must contain exactly one operation, got {len(data['ops'])} for PROMPT operation"
            )

    if log_structure:
        debug_ai(
            f"JSON structure: {list(data.keys()) if isinstance(data, dict) else type(data).__name__}"
        )

    return data


# * High-level helper: process GenerateResult to validated dict
def process_ai_response(
    result: GenerateResult,
    model: str,
    context: str,
    *,
    require_ops: bool = True,
    require_single_op: bool = False,
    log_version_debug: bool = False,
    log_structure: bool = False,
) -> dict:
    data = convert_result_to_dict(result, model, context)
    return validate_edits_structure(
        data,
        model,
        context,
        require_ops=require_ops,
        require_single_op=require_single_op,
        log_version_debug=log_version_debug,
        log_structure=log_structure,
    )
