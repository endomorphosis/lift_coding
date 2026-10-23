"""Cold qualification rejects attempts to promote conditional pilot claims."""
from copy import deepcopy
import pytest

from run_successor import POLICY
from verify_successor import validate_result_scope


def result():
    return {"schema": "terminal-typed-ir-proof-experiment@1", "completed": True, "policy": deepcopy(POLICY),
        "native_full_supervisor_invoked": False, "source_to_model_runtime_equivalence_proved": False,
        "training_convergence_proved": False, "full_task_satisfaction_proved": False,
        "provider_token_savings_measured": False,
        "intent_grounding": {"status": "structural_nomination_with_blocked_partial_plan",
            "partial_plan": {"status": "blocked_partial_instruction_coverage",
                "coverage": {"accepted": False, "errors": [{"code": "unsupported_source_units"}]}}}}


def test_unchanged_conditional_result_and_actual_residual_refusal_remain_valid():
    validate_result_scope(result())


@pytest.mark.parametrize("field", ["native_full_supervisor_invoked", "source_to_model_runtime_equivalence_proved",
    "training_convergence_proved", "full_task_satisfaction_proved", "provider_token_savings_measured"])
def test_public_claim_promotion_cannot_acquire_cold_qualification(field):
    value = result()
    value[field] = True
    with pytest.raises(ValueError):
        validate_result_scope(value)


@pytest.mark.parametrize("mutation", ["schema", "policy", "accepted", "missing_residual"])
def test_resealed_policy_or_plan_acceptance_cannot_hide_original_residuals(mutation):
    value = result()
    if mutation == "schema":
        value["schema"] = "other"
    elif mutation == "policy":
        value["policy"]["source_execution"] = True
    elif mutation == "accepted":
        value["intent_grounding"]["partial_plan"]["coverage"]["accepted"] = True
    else:
        value["intent_grounding"]["partial_plan"]["coverage"]["errors"] = []
    with pytest.raises(ValueError):
        validate_result_scope(value)
