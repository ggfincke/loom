# tests/unit/test_constants.py
# Unit tests for enum constants & their behavior

import pytest
from src.core.constants import RiskLevel, ValidationPolicy


# * Test RiskLevel enum


class TestRiskLevel:

    # * Test all RiskLevel enum values exist & have correct string values
    def test_risk_level_values(self):
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MED.value == "med"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.STRICT.value == "strict"

    # * Test enum membership & iteration
    def test_risk_level_enum_membership(self):
        all_levels = list(RiskLevel)
        assert len(all_levels) == 4
        assert RiskLevel.LOW in all_levels
        assert RiskLevel.MED in all_levels
        assert RiskLevel.HIGH in all_levels
        assert RiskLevel.STRICT in all_levels

    # * Test enum equality comparisons
    def test_risk_level_equality(self):
        assert RiskLevel.LOW == RiskLevel.LOW
        assert RiskLevel.MED != RiskLevel.HIGH
        assert RiskLevel.STRICT != RiskLevel.LOW

    # * Test string representations
    def test_risk_level_string_representation(self):
        assert str(RiskLevel.LOW) == "RiskLevel.LOW"
        assert str(RiskLevel.MED) == "RiskLevel.MED"
        assert str(RiskLevel.HIGH) == "RiskLevel.HIGH"
        assert str(RiskLevel.STRICT) == "RiskLevel.STRICT"

    # * Test repr format
    def test_risk_level_repr(self):
        assert repr(RiskLevel.LOW) == "<RiskLevel.LOW: 'low'>"
        assert repr(RiskLevel.MED) == "<RiskLevel.MED: 'med'>"
        assert repr(RiskLevel.HIGH) == "<RiskLevel.HIGH: 'high'>"
        assert repr(RiskLevel.STRICT) == "<RiskLevel.STRICT: 'strict'>"

    @pytest.mark.parametrize(
        "level,expected_value",
        [
            (RiskLevel.LOW, "low"),
            (RiskLevel.MED, "med"),
            (RiskLevel.HIGH, "high"),
            (RiskLevel.STRICT, "strict"),
        ],
    )
    # * Test accessing enum values via .value attribute
    def test_risk_level_value_access(self, level, expected_value):
        assert level.value == expected_value

    # * Test that enum values cannot be compared for ordering (expected behavior)
    def test_risk_level_comparison_ordering(self):
        with pytest.raises(TypeError):
            _ = RiskLevel.LOW < RiskLevel.HIGH

        with pytest.raises(TypeError):
            _ = RiskLevel.STRICT > RiskLevel.MED

    # * Test enum values are hashable & can be used as dict keys
    def test_risk_level_hashable(self):
        risk_settings = {
            RiskLevel.LOW: "permissive",
            RiskLevel.MED: "balanced",
            RiskLevel.HIGH: "strict",
            RiskLevel.STRICT: "very_strict",
        }

        assert risk_settings[RiskLevel.LOW] == "permissive"
        assert risk_settings[RiskLevel.STRICT] == "very_strict"
        assert len(risk_settings) == 4


# * Test ValidationPolicy enum


class TestValidationPolicy:

    # * Test all ValidationPolicy enum values exist & have correct string values
    def test_validation_policy_values(self):
        assert ValidationPolicy.ASK.value == "ask"
        assert ValidationPolicy.RETRY.value == "retry"
        assert ValidationPolicy.MANUAL.value == "manual"
        assert ValidationPolicy.FAIL_SOFT.value == "fail_soft"
        assert ValidationPolicy.FAIL_HARD.value == "fail_hard"

    # * Test enum membership & iteration
    def test_validation_policy_enum_membership(self):
        all_policies = list(ValidationPolicy)
        assert len(all_policies) == 5
        assert ValidationPolicy.ASK in all_policies
        assert ValidationPolicy.RETRY in all_policies
        assert ValidationPolicy.MANUAL in all_policies
        assert ValidationPolicy.FAIL_SOFT in all_policies
        assert ValidationPolicy.FAIL_HARD in all_policies

    # * Test enum equality comparisons
    def test_validation_policy_equality(self):
        assert ValidationPolicy.ASK == ValidationPolicy.ASK
        assert ValidationPolicy.RETRY != ValidationPolicy.MANUAL
        assert ValidationPolicy.FAIL_SOFT != ValidationPolicy.FAIL_HARD

    # * Test string representations
    def test_validation_policy_string_representation(self):
        assert str(ValidationPolicy.ASK) == "ValidationPolicy.ASK"
        assert str(ValidationPolicy.RETRY) == "ValidationPolicy.RETRY"
        assert str(ValidationPolicy.MANUAL) == "ValidationPolicy.MANUAL"
        assert str(ValidationPolicy.FAIL_SOFT) == "ValidationPolicy.FAIL_SOFT"
        assert str(ValidationPolicy.FAIL_HARD) == "ValidationPolicy.FAIL_HARD"

    # * Test repr format
    def test_validation_policy_repr(self):
        assert repr(ValidationPolicy.ASK) == "<ValidationPolicy.ASK: 'ask'>"
        assert repr(ValidationPolicy.RETRY) == "<ValidationPolicy.RETRY: 'retry'>"
        assert repr(ValidationPolicy.MANUAL) == "<ValidationPolicy.MANUAL: 'manual'>"
        assert (
            repr(ValidationPolicy.FAIL_SOFT)
            == "<ValidationPolicy.FAIL_SOFT: 'fail_soft'>"
        )
        assert (
            repr(ValidationPolicy.FAIL_HARD)
            == "<ValidationPolicy.FAIL_HARD: 'fail_hard'>"
        )

    @pytest.mark.parametrize(
        "policy,expected_value",
        [
            (ValidationPolicy.ASK, "ask"),
            (ValidationPolicy.RETRY, "retry"),
            (ValidationPolicy.MANUAL, "manual"),
            (ValidationPolicy.FAIL_SOFT, "fail_soft"),
            (ValidationPolicy.FAIL_HARD, "fail_hard"),
        ],
    )
    # * Test accessing enum values via .value attribute
    def test_validation_policy_value_access(self, policy, expected_value):
        assert policy.value == expected_value

    # * Test enum values are hashable & can be used as dict keys
    def test_validation_policy_hashable(self):
        policy_handlers = {
            ValidationPolicy.ASK: "interactive",
            ValidationPolicy.RETRY: "automatic_retry",
            ValidationPolicy.MANUAL: "user_intervention",
            ValidationPolicy.FAIL_SOFT: "graceful_exit",
            ValidationPolicy.FAIL_HARD: "cleanup_exit",
        }

        assert policy_handlers[ValidationPolicy.ASK] == "interactive"
        assert policy_handlers[ValidationPolicy.FAIL_HARD] == "cleanup_exit"
        assert len(policy_handlers) == 5


# * Test enum interaction & cross-references


class TestEnumInteractions:

    # * Test RiskLevel & ValidationPolicy are distinct enum types
    def test_enums_are_distinct_types(self):
        assert type(RiskLevel.LOW) != type(ValidationPolicy.ASK)
        assert RiskLevel.LOW != ValidationPolicy.ASK

    # * Test enums can be used as function parameters
    def test_enum_values_as_function_parameters(self):
        def process_validation(risk: RiskLevel, policy: ValidationPolicy) -> str:
            return f"Risk: {risk.value}, Policy: {policy.value}"

        result = process_validation(RiskLevel.HIGH, ValidationPolicy.RETRY)
        assert result == "Risk: high, Policy: retry"

    # * Test enums work together in complex data structures
    def test_enum_combinations_in_data_structures(self):
        validation_matrix = {
            (RiskLevel.LOW, ValidationPolicy.ASK): "prompt_user_low_risk",
            (RiskLevel.HIGH, ValidationPolicy.FAIL_HARD): "strict_validation",
            (RiskLevel.MED, ValidationPolicy.RETRY): "auto_retry_medium",
        }

        assert (
            validation_matrix[(RiskLevel.LOW, ValidationPolicy.ASK)]
            == "prompt_user_low_risk"
        )
        assert (
            validation_matrix[(RiskLevel.HIGH, ValidationPolicy.FAIL_HARD)]
            == "strict_validation"
        )

    # * Test enum values work w/ set operations
    def test_enum_set_operations(self):
        risk_set = {RiskLevel.LOW, RiskLevel.HIGH}
        policy_set = {ValidationPolicy.ASK, ValidationPolicy.MANUAL}

        assert RiskLevel.LOW in risk_set
        assert RiskLevel.MED not in risk_set
        assert ValidationPolicy.ASK in policy_set
        assert ValidationPolicy.RETRY not in policy_set

        # test set intersection, union, etc.
        all_risks = set(RiskLevel)
        selected_risks = {RiskLevel.LOW, RiskLevel.STRICT}
        intersection = all_risks.intersection(selected_risks)
        assert intersection == selected_risks


# * Test enum edge cases & error conditions


class TestEnumEdgeCases:

    # * Test enum values cannot be modified
    def test_enum_immutability(self):
        original_value = RiskLevel.LOW.value

        # attempting to modify should not work (or raise AttributeError)
        with pytest.raises(AttributeError):
            RiskLevel.LOW.value = "modified"  # type: ignore[misc]

        assert RiskLevel.LOW.value == original_value

    # * Test .name attribute works correctly
    def test_enum_name_attribute(self):
        assert RiskLevel.LOW.name == "LOW"
        assert RiskLevel.MED.name == "MED"
        assert ValidationPolicy.FAIL_SOFT.name == "FAIL_SOFT"
        assert ValidationPolicy.ASK.name == "ASK"

    # * Test accessing enum members by name
    def test_enum_by_name_lookup(self):
        assert RiskLevel["LOW"] == RiskLevel.LOW
        assert RiskLevel["STRICT"] == RiskLevel.STRICT
        assert ValidationPolicy["ASK"] == ValidationPolicy.ASK
        assert ValidationPolicy["FAIL_HARD"] == ValidationPolicy.FAIL_HARD

    # * Test accessing non-existent enum members raises KeyError
    def test_enum_invalid_name_lookup(self):
        with pytest.raises(KeyError):
            RiskLevel["INVALID"]

        with pytest.raises(KeyError):
            ValidationPolicy["NONEXISTENT"]

    # * Test enum iteration maintains definition order
    def test_enum_iteration_order(self):
        risk_levels = list(RiskLevel)
        expected_order = [
            RiskLevel.LOW,
            RiskLevel.MED,
            RiskLevel.HIGH,
            RiskLevel.STRICT,
        ]
        assert risk_levels == expected_order

        policies = list(ValidationPolicy)
        expected_policy_order = [
            ValidationPolicy.ASK,
            ValidationPolicy.RETRY,
            ValidationPolicy.MANUAL,
            ValidationPolicy.FAIL_SOFT,
            ValidationPolicy.FAIL_HARD,
        ]
        assert policies == expected_policy_order

    # * Test enum values are always truthy
    def test_enum_boolean_context(self):
        assert bool(RiskLevel.LOW) is True
        assert bool(ValidationPolicy.ASK) is True

        # test in conditional contexts
        if RiskLevel.HIGH:
            high_risk_detected = True
        else:
            high_risk_detected = False

        assert high_risk_detected is True
