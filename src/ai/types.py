# src/ai/types.py
# Shared types for AI clients & functionality

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


# * Result object for AI generation operations
@dataclass(slots=True)
class GenerateResult:
    success: bool  # indicates if generation was successful
    data: Optional[Dict[str, Any]] = None  # parsed JSON payload on success
    raw_text: str = ""  # provider raw text (for debugging)
    json_text: str = ""  # extracted JSON text (after any stripping)
    error: str = ""  # error message on failure


# * Status object for Ollama server availability & model discovery
@dataclass(slots=True)
class OllamaStatus:
    available: bool  # whether Ollama server is accessible
    models: List[str]  # list of available model names
    error: str  # error message if unavailable (empty if success)
