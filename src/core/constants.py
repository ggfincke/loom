# src/core/constants.py
# Constants & enums for validation policies, risk levels & edit operations

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional

# * Risk level constants for validation strictness
class RiskLevel(Enum):
    LOW = "low"
    MED = "med"
    HIGH = "high"
    STRICT = "strict"

# * Validation policy constants for error handling
class ValidationPolicy(Enum):
    ASK = "ask"
    RETRY = "retry"
    MANUAL = "manual"
    FAIL_SOFT = "fail_soft"
    FAIL_HARD = "fail_hard"

# * Diff operation status constants for interactive review
class DiffOp(Enum):
    APPROVE = "approve"
    REJECT = "reject"
    SKIP = "skip"
    # todo add modify & prompt operations
    # MODIFY = "modify"
    # PROMPT = "prompt"

# * Edit operation data structure for diff review workflow
@dataclass
class EditOperation:
    operation: str                                              # "replace_line", "replace_range", "insert_after", "delete_range" 
    line_number: int
    content: str = ""
    start_line: Optional[int] = None                            # for replace_range, delete_range
    end_line: Optional[int] = None                              # for replace_range, delete_range
    reasoning: str = ""
    confidence: float = 0.0
    status: DiffOp = DiffOp.SKIP                                # user decision status
    before_context: List[str] = field(default_factory=list)     # surrounding lines for display
    after_context: List[str] = field(default_factory=list)
    original_content: str = ""                                  # original content for replace operations
