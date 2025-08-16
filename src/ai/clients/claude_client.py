# src/ai/clients/claude_client.py
# Claude API client functions for generating JSON responses using the Messages API

import os
import json
import re
from dotenv import load_dotenv
from anthropic import Anthropic
from ...config.settings import settings_manager
from ..types import GenerateResult
from ..models import ensure_valid_model

# strip markdown code blocks
def strip_markdown_code_blocks(text: str) -> str:
    code_block_pattern = r'^```(?:json)?\s*\n(.*?)\n```\s*$'
    match = re.match(code_block_pattern, text.strip(), re.DOTALL)
    
    if match:
        return match.group(1)
    else:
        return text.strip()

# * Generate JSON response using Claude API w/ model validation
def run_generate(prompt: str, model: str = "claude-sonnet-4-20250514") -> GenerateResult:
    load_dotenv()
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("Missing ANTHROPIC_API_KEY in environment or .env")
    
    # validate model before making API call
    validated_model = ensure_valid_model(model)
    if validated_model is None:
        # ensure_valid_model already showed error & exited, this should not happen
        raise RuntimeError("Model validation failed")
    
    client = Anthropic()
    
    settings = settings_manager.load()
    
    # create message w/ structured JSON output request
    response = client.messages.create(
        model=validated_model,
        max_tokens=4096,
        temperature=settings.temperature,
        messages=[
            {
                "role": "user", 
                "content": f"{prompt}\n\nPlease respond with valid JSON only, no additional text or formatting."
            }
        ]
    )
    
    # extract text from response
    raw_text = ""
    for content_block in response.content:
        # only process text blocks, skip other types like tool use blocks
        if content_block.type == "text":
            raw_text += content_block.text
    
    # strip code blocks to extract JSON
    json_text = strip_markdown_code_blocks(raw_text)
    
    # ensure valid JSON
    try:
        data = json.loads(json_text)
        return GenerateResult(success=True, data=data, raw_text=raw_text, json_text=json_text)
    except json.JSONDecodeError as e:
        # return error result instead of raising
        error_msg = f"JSON parsing failed: {str(e)}"
        return GenerateResult(success=False, raw_text=raw_text, json_text=json_text, error=error_msg)