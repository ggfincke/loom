# src/ai/types.py
# Shared types for AI clients & functionality

from typing import Optional

# result class for AI generation operations
class GenerateResult:
    # indicates if generation was successful
    def __init__(self, success: bool, data: Optional[dict] = None, raw_text: str = "", json_text: str = "", error: str = ""):
        self.success = success
        self.data = data
        self.raw_text = raw_text
        self.json_text = json_text
        self.error = error