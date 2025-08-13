# src/ai/clients/openai_client.py
# OpenAI API client functions for generating JSON responses using the Responses API

import os
import json
import re
from dotenv import load_dotenv
from openai import OpenAI
from ...config.settings import settings_manager
from ..types import GenerateResult

# strip markdown code blocks
def strip_markdown_code_blocks(text: str) -> str:
    code_block_pattern = r'^```(?:json)?\s*\n(.*?)\n```\s*$'
    match = re.match(code_block_pattern, text.strip(), re.DOTALL)
    
    if match:
        return match.group(1)
    else:
        return text.strip()

# generate JSON response using OpenAI API
def run_generate(prompt: str, model: str = "gpt-5-mini") -> GenerateResult:
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Missing OPENAI_API_KEY in environment or .env")
    client = OpenAI()
    
    # GPT-5 models don't support temperature parameter
    if model.startswith("gpt-5"):
        resp = client.responses.create(model=model, input=prompt)
    else:
        settings = settings_manager.load()
        resp = client.responses.create(model=model, input=prompt, temperature=settings.temperature)
    
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