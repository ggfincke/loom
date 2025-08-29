# src/ai/utils.py
# Shared utility functions for AI clients

import re


def strip_markdown_code_blocks(text: str) -> str:
    """
    Strip markdown code blocks & thinking tokens from AI responses.
    
    First strips thinking tokens (e.g., <think>...</think>), then strips
    markdown code blocks (e.g., ```json ... ```).
    
    Args:
        text: Raw AI response text
        
    Returns:
        Cleaned text content
    """
    # first strip thinking tokens if present
    thinking_pattern = r'<think>.*?</think>\s*(.*)'
    thinking_match = re.match(thinking_pattern, text.strip(), re.DOTALL)
    if thinking_match:
        text = thinking_match.group(1).strip()
    
    # then strip markdown code blocks
    code_block_pattern = r'^```(?:json)?\s*\n(.*?)\n```\s*$'
    match = re.match(code_block_pattern, text.strip(), re.DOTALL)
    
    if match:
        return match.group(1)
    else:
        return text.strip()