# src/ai/clients/ollama_client.py
# Ollama API client functions for generating JSON responses using local models

import json
from typing import List
import ollama
from ...config.settings import settings_manager
from ..types import GenerateResult
from ...core.exceptions import AIError
from ..utils import strip_markdown_code_blocks
from ...core.debug import debug_ai, debug_error, debug_api_call


# * Check if Ollama server is running & accessible
def is_ollama_available() -> bool:
    try:
        ollama.list()
        return True
    except Exception as e:
        return False

# * Check if Ollama server is running & return detailed error if not
def check_ollama_with_error() -> tuple[bool, str]:
    try:
        debug_ai("Checking Ollama server availability...")
        response = ollama.list()
        debug_ai(f"Ollama server is available - found {len(response.models)} models")
        return True, ""
    except Exception as e:
        debug_error(e, "Ollama server check")
        error_msg = f"Ollama server connection failed: {str(e)}. Please ensure Ollama is running locally."
        return False, error_msg

# * Get list of available local models from Ollama
def get_available_models() -> List[str]:
    try:
        models_response = ollama.list()
        models = []
        # ollama.list() returns a ListResponse object with a models attribute
        for model in models_response.models:
            # extract model name from the model attribute
            model_name = model.model
            if model_name:
                models.append(model_name)
        return models
    except Exception as e:
        return []

# * Get list of available local models w/ detailed error reporting
def get_available_models_with_error() -> tuple[List[str], str]:
    try:
        debug_ai("Retrieving available Ollama models...")
        models_response = ollama.list()
        models = []
        # ollama.list() returns a ListResponse object with a models attribute
        for model in models_response.models:
            # extract model name from the model attribute
            model_name = model.model
            if model_name:
                models.append(model_name)
        debug_ai(f"Found {len(models)} available models: {', '.join(models)}")
        return models, ""
    except Exception as e:
        debug_error(e, "Ollama model list")
        error_msg = f"Failed to retrieve Ollama models: {str(e)}. Ensure Ollama is running & models are installed."
        return [], error_msg

# * Generate JSON response using Ollama API w/ model validation
def run_generate(prompt: str, model: str = "llama3.2") -> GenerateResult:
    # check if Ollama server is available first w/ detailed error
    available, error_msg = check_ollama_with_error()
    if not available:
        raise AIError(f"Ollama server error: {error_msg}")
    
    # validate model is available locally w/ detailed error
    available_models, models_error = get_available_models_with_error()
    if models_error:
        raise AIError(f"Ollama model error: {models_error}")
    
    if model not in available_models:
        if not available_models:
            error_msg = f"Model '{model}' not found & no local models available. Run 'ollama pull {model}' to install it."
        else:
            error_msg = f"Model '{model}' not found locally. Available models: {', '.join(available_models)}. Run 'ollama pull {model}' to install it."
        raise AIError(f"Ollama model error: {error_msg}")
    
    try:
        settings = settings_manager.load()
        
        debug_api_call("Ollama", model, len(prompt))
        debug_ai(f"Making Ollama API call with model: {model}, temperature: {settings.temperature}")
        
        # create chat request w/ structured JSON output request
        response = ollama.chat(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant. Always respond with valid JSON only, no additional text or formatting."
                },
                {
                    "role": "user", 
                    "content": f"{prompt}\n\nPlease respond with valid JSON only, no additional text or formatting."
                }
            ],
            options={
                "temperature": settings.temperature
            }
        )
        
        # extract text from response
        raw_text = response.get('message', {}).get('content', '')
        debug_ai(f"Received response from Ollama: {len(raw_text)} characters")
        
        # strip code blocks to extract JSON
        json_text = strip_markdown_code_blocks(raw_text)
        debug_ai(f"Extracted JSON text: {len(json_text)} characters")
        
        # ensure valid JSON
        try:
            data = json.loads(json_text)
            debug_ai("Successfully parsed JSON response")
            return GenerateResult(success=True, data=data, raw_text=raw_text, json_text=json_text)
        except json.JSONDecodeError as e:
            debug_error(e, "JSON parsing")
            # return error result instead of raising
            error_msg = f"JSON parsing failed: {str(e)}. Raw response: {json_text[:200]}{'...' if len(json_text) > 200 else ''}"
            return GenerateResult(success=False, raw_text=raw_text, json_text=json_text, error=error_msg)
            
    except Exception as e:
        debug_error(e, "Ollama API call")
        # normalize provider API errors to AIError for consistent handling
        raise AIError(f"Ollama API error: {str(e)}. Model: {model}. Check if Ollama is running & model is properly installed.")