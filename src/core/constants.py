# src/core/constants.py
# Constants and enums for validation policies and risk levels

from enum import Enum


class RiskLevel(Enum):
    LOW = "low"
    MED = "med"
    HIGH = "high"
    STRICT = "strict"


class ValidationPolicy(Enum):
    ASK = "ask"
    RETRY = "retry"
    MANUAL = "manual"
    FAIL_SOFT = "fail_soft"
    FAIL_HARD = "fail_hard"


def normalize_risk(value: str | None) -> RiskLevel:
    if value is None:
        return RiskLevel.MED
    
    value = value.strip().lower()
    
    if value == "low":
        return RiskLevel.LOW
    elif value == "med":
        return RiskLevel.MED
    elif value == "high":
        return RiskLevel.HIGH
    elif value == "strict":
        return RiskLevel.STRICT
    else:
        return RiskLevel.MED


def normalize_validation_policy(value: str | None) -> ValidationPolicy:
    if value is None:
        return ValidationPolicy.ASK
    
    value = value.strip().lower()
    
    if value == "ask":
        return ValidationPolicy.ASK
    elif value == "retry":
        return ValidationPolicy.RETRY
    elif value == "manual":
        return ValidationPolicy.MANUAL
    elif value in ("fail", "fail:soft"):
        return ValidationPolicy.FAIL_SOFT
    elif value == "fail:hard":
        return ValidationPolicy.FAIL_HARD
    else:
        return ValidationPolicy.ASK