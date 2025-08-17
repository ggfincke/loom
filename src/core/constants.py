# src/core/constants.py
# Constants & enums for validation policies & risk levels

from enum import Enum

# * Constant Enums
# RiskLevel
class RiskLevel(Enum):
    LOW = "low"
    MED = "med"
    HIGH = "high"
    STRICT = "strict"

# ValidationPolicy
class ValidationPolicy(Enum):
    ASK = "ask"
    RETRY = "retry"
    MANUAL = "manual"
    FAIL_SOFT = "fail_soft"
    FAIL_HARD = "fail_hard"