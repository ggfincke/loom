# src/core/constants.py
# Constants & enums for validation policies, risk levels & edit operations

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional


# * Operation type constants for edit operations
OP_REPLACE_LINE = "replace_line"
OP_REPLACE_RANGE = "replace_range"
OP_INSERT_AFTER = "insert_after"
OP_DELETE_RANGE = "delete_range"


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
    MODIFY = "modify"
    PROMPT = "prompt"


# * Edit operation data structure for diff review workflow
@dataclass
class EditOperation:
    # operation type: "replace_line", "replace_range", "insert_after", "delete_range"
    operation: str
    line_number: int
    content: str = ""
    # for replace_range & delete_range operations
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    reasoning: str = ""
    confidence: float = 0.0
    # user decision status
    status: DiffOp = DiffOp.SKIP
    # surrounding lines for display
    before_context: List[str] = field(default_factory=list)
    after_context: List[str] = field(default_factory=list)
    # original content for replace operations
    original_content: str = ""
    # user prompt for PROMPT operations
    prompt_instruction: Optional[str] = None
