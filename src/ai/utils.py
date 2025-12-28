# src/ai/utils.py
# Shared utility functions for AI response processing w/ JSON parsing & key normalization

import json
import re
from dataclasses import dataclass
from typing import Any, Optional

from .types import GenerateResult


# * Short key aliases for token-efficient AI responses
OP_KEY_ALIASES: dict[str, str] = {
    "l": "line",
    "t": "text",
    "s": "start",
    "e": "end",
    "cur": "current_snippet",
    "w": "why",
}

# * Section key aliases for sectionizer responses
SECTION_KEY_ALIASES: dict[str, str] = {
    "k": "kind",
    "h": "heading_text",
    "s": "start_line",
    "e": "end_line",
    "c": "confidence",
    "sub": "subsections",
}


def normalize_op_keys(op: dict[str, Any]) -> dict[str, Any]:
    return {OP_KEY_ALIASES.get(k, k): v for k, v in op.items()}

def normalize_edits_response(edits: dict[str, Any]) -> dict[str, Any]:
    if "ops" in edits and isinstance(edits["ops"], list):
        edits["ops"] = [normalize_op_keys(op) for op in edits["ops"]]
    return edits

def _normalize_subsection(sub: Any) -> dict[str, Any]:
    if isinstance(sub, list) and len(sub) >= 3:
        # array format: [name, start_line, end_line, optional_meta]
        result: dict[str, Any] = {
            "name": sub[0],
            "start_line": sub[1],
            "end_line": sub[2],
        }
        if len(sub) > 3 and isinstance(sub[3], dict):
            result["meta"] = sub[3]
        return result
    elif isinstance(sub, dict):
        # dict format - expand short keys if present
        normalized: dict[str, Any] = {}
        for k, v in sub.items():
            key = SECTION_KEY_ALIASES.get(k, k) if isinstance(k, str) else k
            normalized[key] = v
        return normalized
    # pass through unchanged if unknown format (cast to satisfy type checker)
    return dict(sub) if isinstance(sub, dict) else {"_raw": sub}


def normalize_section_keys(section: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for k, v in section.items():
        key = SECTION_KEY_ALIASES.get(k, k) if isinstance(k, str) else str(k)
        normalized[key] = v
    # also normalize subsections if present
    if "subsections" in normalized and isinstance(normalized["subsections"], list):
        normalized["subsections"] = [
            _normalize_subsection(sub) for sub in normalized["subsections"]
        ]
    return normalized

def normalize_sections_response(data: dict[str, Any]) -> dict[str, Any]:
    if "sections" in data and isinstance(data["sections"], list):
        data["sections"] = [normalize_section_keys(s) for s in data["sections"]]
    return data


# * Context object for API call results (used by BaseClient._process_response)
@dataclass(slots=True)
class APICallContext:
    raw_text: str  # raw response text from provider
    provider_name: str  # provider ID: "openai", "anthropic", "ollama"
    model: str  # model used for the call


# strip markdown code blocks & thinking tokens from AI responses
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


# * Parse JSON from text after stripping markdown (returns data, json_text, error_message)
def parse_json(text: str) -> tuple[Optional[dict[str, Any]], str, str]:
    json_text = strip_markdown_code_blocks(text)

    try:
        data = json.loads(json_text)
        return data, json_text, ""
    except json.JSONDecodeError as e:
        truncated = json_text[:200] + ("..." if len(json_text) > 200 else "")
        error_msg = f"JSON parsing failed: {e}. Stripped text: {truncated}"
        return None, json_text, error_msg


# * Validate AI response structure & extract normalized data (raises JSONParsingError or AIError)
def validate_and_extract(
    data: Any,
    raw_text: str,
    json_text: str,
    parse_error: str,
    model: str,
    context: str,
    *,
    require_ops: bool = True,
    require_single_op: bool = False,
    log_version_debug: bool = False,
    log_structure: bool = False,
) -> dict[str, Any]:
    # ! import here to avoid circular dependency w/ core module
    from ..core.exceptions import JSONParsingError, AIError
    from ..core.debug import debug_ai

    context_hint = f" during {context}" if context else ""

    # handle parse failure
    if data is None:
        from ..core.debug import debug_error

        debug_error(Exception(parse_error), f"AI {context} failed for model {model}")

        # distinguish API errors (no response) from parsing errors (got response)
        has_raw = isinstance(raw_text, str) and len(raw_text) > 0
        has_json = isinstance(json_text, str) and len(json_text) > 0
        has_response = has_raw or has_json

        if has_response:
            # got a response but couldn't parse it - JSONParsingError
            lines = json_text.split("\n") if json_text else []
            snippet = "\n".join(lines[:5]) + "\n..." if len(lines) > 5 else json_text
            error_msg = f"AI generated invalid JSON{context_hint} using model '{model}':\n{snippet}\nError: {parse_error}"
            if raw_text and raw_text != json_text:
                error_msg += f"\nFull raw response: {raw_text[:300]}{'...' if len(raw_text) > 300 else ''}"
            raise JSONParsingError(error_msg)
        else:
            # API call failed w/ no response - AIError
            raise AIError(f"AI failed to process {context}: {parse_error}")

    # validate structure
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

    # normalize short keys & return
    return normalize_edits_response(data)


# * High-level helper: GenerateResult -> validated dict w/ structure validation
def process_ai_response(
    result: GenerateResult,
    model: str,
    context: str,
    *,
    require_ops: bool = True,
    require_single_op: bool = False,
    log_version_debug: bool = False,
    log_structure: bool = False,
) -> dict[str, Any]:
    # if result already failed, extract error info
    if not result.success:
        # parse_json was already called, pass through the error
        return validate_and_extract(
            data=None,
            raw_text=result.raw_text,
            json_text=result.json_text,
            parse_error=result.error,
            model=model,
            context=context,
            require_ops=require_ops,
            require_single_op=require_single_op,
            log_version_debug=log_version_debug,
            log_structure=log_structure,
        )

    # result.success means we have parsed data
    return validate_and_extract(
        data=result.data,
        raw_text=result.raw_text,
        json_text=result.json_text,
        parse_error="",
        model=model,
        context=context,
        require_ops=require_ops,
        require_single_op=require_single_op,
        log_version_debug=log_version_debug,
        log_structure=log_structure,
    )
