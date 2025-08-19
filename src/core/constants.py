# src/core/constants.py
# Constants & enums for validation policies & risk levels

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional

# * Constant Enums
# RiskLevel
class RiskLevel(Enum):
    LOW = "low"
    MED = "med"
    HIGH = "high"
    STRICT = "strict"

# ValidationPolicy (on errors)
class ValidationPolicy(Enum):
    ASK = "ask"
    RETRY = "retry"
    MANUAL = "manual"
    FAIL_SOFT = "fail_soft"
    FAIL_HARD = "fail_hard"

# Diff Operations
class DiffOp(Enum):
    APPROVE = "approve"
    REJECT = "reject"
    SKIP = "skip"
    # todo add modify & prompt operations
    # MODIFY = "modify"
    # PROMPT = "prompt"

# Edit Operation Data Structure
@dataclass
class EditOperation:
    operation: str  # "replace_line", "replace_range", "insert_after", "delete_range"
    line_number: int
    content: str = ""
    start_line: Optional[int] = None  # For replace_range, delete_range
    end_line: Optional[int] = None    # For replace_range, delete_range
    reasoning: str = ""
    confidence: float = 0.0
    status: DiffOp = DiffOp.SKIP  # User decision status
    before_context: List[str] = field(default_factory=list)  # Surrounding lines for display
    after_context: List[str] = field(default_factory=list)
