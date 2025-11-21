# src/ai/types.py
# Shared types for AI clients & functionality

from dataclasses import dataclass
from typing import Any, Dict, Optional


# * Result object for AI generation operations
@dataclass(slots=True)
class GenerateResult:
    success: bool  # indicates if generation was successful
    data: Optional[Dict[str, Any]] = None  # parsed JSON payload on success
    raw_text: str = ""  # provider raw text (for debugging)
    json_text: str = ""  # extracted JSON text (after any stripping)
    error: str = ""  # error message on failure
