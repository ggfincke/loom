# src/openai_client.py
# OpenAI API client functions for generating JSON responses using the Responses API

import os
import json
import re
from dotenv import load_dotenv
from openai import OpenAI
from .settings import settings_manager

# strip markdown code blocks
def strip_markdown_code_blocks(text: str) -> str:
    code_block_pattern = r'^```(?:json)?\s*\n(.*?)\n```\s*$'
    match = re.match(code_block_pattern, text.strip(), re.DOTALL)
    
    if match:
        return match.group(1)
    else:
        return text.strip()

# generate JSON response using OpenAI API
def run_generate(prompt: str, model: str = "gpt-5-mini") -> dict:
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
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        # fail w/ error message
        raise RuntimeError(f"Model did not return valid JSON. Raw response:\n{raw_text}\n\nExtracted JSON:\n{json_text}") from e