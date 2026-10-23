"""Consume native T3 obligation priors by ordering unchanged structural checks.

This versioned overlay applies learned advice only to check scheduling. Every
required check still runs on the exact candidate, including after a failure.
It cannot edit IR, weaken a checker, fabricate premises, or admit a proof. The
historical proposed canonical-field mutation adapter remains unimplemented.
"""
from __future__ import annotations
import copy
import hashlib
import json
import math
from pathlib import Path
import time
from typing import Any, Callable, Mapping

SCHEMA = "autoformalization-learned-obligation-priority/v1"
REQUIRED_CHECKS = ("modal_well_formedness", "provenance_preservation")
CONTEXT = "frame_logic"
POLICY = {
    "native_head": "obligation_family",
    "context": CONTEXT,
    "interpretation": "learned obligation-frequency prior, not probability of correctness",
    "baseline_order": list(REQUIRED_CHECKS),
    "selection_rule": "descending probability; ties preserve baseline order",
    "early_stopping": False,
    "canonical_mutation_allowed": False,
    "checker_mutation_allowed": False,
    "proof_admission": "not performed by this structural-check scheduler",
    "rollback": "disable guidance and replay exact baseline check order",
}

class GuidanceBoundaryError(ValueError):
    """Malformed, unbound, or changed guidance is never silently admitted."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hash(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise GuidanceBoundaryError(f"{name} must be a lowercase SHA-256 digest")
    return value


def implementation_identity() -> dict[str, Any]:
    return {"overlay_sha256": file_digest(Path(__file__)), "policy": POLICY}


def validate_qualification(qualification: Mapping[str, Any], prediction: Mapping[str, Any]) -> None:
    from ipfs_datasets_py.utils.cid_utils import cid_for_dag_json
    if qualification.get("schema") != "autoformalization-learned-route-qualification/v1" or qualification.get("qualified") is not True:
        raise GuidanceBoundaryError("Learned obligation scheduling is not qualified")
    if qualification.get("implementation") != implementation_identity():
        raise GuidanceBoundaryError("Qualified overlay/policy changed")
    review = qualification.get("independent_engineering_review")
    evidence = qualification.get("qualification_evidence")
    if not isinstance(review, dict) or not isinstance(evidence, dict):
        raise GuidanceBoundaryError("Qualification must include independent engineering review and executed evidence")
    if cid_for_dag_json(review) != qualification.get("independent_review_cid"):
        raise GuidanceBoundaryError("Independent engineering review CID mismatch")
    if review.get("approved") is not True or review.get("overlay_sha256") != file_digest(Path(__file__)):
        raise GuidanceBoundaryError("Engineering review did not approve these exact overlay bytes")
    if digest(evidence) != qualification.get("qualification_evidence_sha256"):
        raise GuidanceBoundaryError("Qualification evidence digest mismatch")
    required = ("real_checkpoint_predictions_consumed", "paired_on_off_effect_observed", "checker_preserved", "rollback_passed", "final_examples_opened_is_false")
    if not all(evidence.get(k) is True for k in required):
        raise GuidanceBoundaryError("Required executed qualification conditions are absent")
    payload = {k: v for k, v in qualification.items() if k != "qualification_cid"}
    if cid_for_dag_json(payload) != qualification.get("qualification_cid"):
        raise GuidanceBoundaryError("Qualification CID mismatch")
    allowed = qualification.get("allowed_model_bindings") or []
    observed = {k: prediction.get(k) for k in ("arm_id", "seed", "checkpoint_sha256", "compact_sha256")}
    if observed not in allowed:
        raise GuidanceBoundaryError("Prediction does not match a qualified actual checkpoint export")


def choose_check_order(
    prediction: Mapping[str, Any], canonical_record: Mapping[str, Any], *,
    enabled: bool = True, expected_prediction_sha256: str | None = None,
    qualification: Mapping[str, Any] | None = None, qualification_required: bool = False,
) -> dict[str, Any]:
    required = {"record_id", "text_sha256", "canonical_ir", "checker_contract"}
    if not isinstance(canonical_record, Mapping) or not required <= canonical_record.keys():
        raise GuidanceBoundaryError("Canonical candidate/checker/source binding missing")
    _hash(canonical_record["text_sha256"], "canonical text_sha256")
    if not canonical_record["record_id"] or not canonical_record["checker_contract"]:
        raise GuidanceBoundaryError("Candidate record and checker identities must be nonempty")
    receipt = {
        "schema": SCHEMA, "arm": "E_obligation_priority_v1", "enabled": enabled,
        "record_id": canonical_record["record_id"], "text_sha256": canonical_record["text_sha256"],
        "canonical_sha256": digest(canonical_record["canonical_ir"]),
        "checker_contract_sha256": digest(canonical_record["checker_contract"]),
        "canonical_mutated": False, "checker_mutated": False,
        "learned_parameters_consumed": False, "qualification_applied": False,
        "calibration_measured": False, "proof_truth_predicted": False,
        "check_order": list(REQUIRED_CHECKS), "order_changed": False,
    }
    if not enabled:
        receipt["action"] = "baseline_guidance_off"
        return receipt
    if not isinstance(prediction, Mapping):
        raise GuidanceBoundaryError("Prediction must be a mapping")
    if prediction.get("record_id") != canonical_record["record_id"]:
        raise GuidanceBoundaryError("Prediction/candidate record_id binding mismatch")
    # Model embedding inputs retain the complete source; canonical C parses the
    # frozen prefix. Bind their common parser input without confusing the two.
    if qualification_required and "parser_text_sha256" not in prediction:
        raise GuidanceBoundaryError("Final prediction lacks its exact parser-prefix binding")
    parser_hash = prediction.get("parser_text_sha256", prediction.get("text_sha256"))
    if parser_hash != canonical_record["text_sha256"]:
        raise GuidanceBoundaryError("Prediction/candidate parser source binding mismatch")
    if prediction.get("sample_memory_used") is not False or prediction.get("reference_targets_used") is not False:
        raise GuidanceBoundaryError("Prediction must explicitly exclude sample memory and reference targets")
    prediction_sha256 = digest(prediction)
    if expected_prediction_sha256 is not None and prediction_sha256 != expected_prediction_sha256:
        raise GuidanceBoundaryError("Prediction content differs from the frozen emitted row")
    if qualification_required and (qualification is None or expected_prediction_sha256 is None):
        raise GuidanceBoundaryError("Final routing requires qualification and a frozen prediction row digest")
    if qualification is not None:
        validate_qualification(qualification, prediction)
        if qualification.get("checker_contract") != canonical_record["checker_contract"]:
            raise GuidanceBoundaryError("Candidate checker differs from qualified callbacks/native types")
        receipt["qualification_applied"] = True
    heads = prediction.get("proof_heads_by_family") or {}
    native = heads.get(CONTEXT) or {}
    if native.get("family") != CONTEXT or native.get("schema_version") != "legal-ir-proof-auxiliary-heads-v1":
        raise GuidanceBoundaryError("Actual native fixed-context proof-head export missing")
    head = (native.get("heads") or {}).get("obligation_family") or {}
    probabilities = head.get("probabilities")
    if not isinstance(probabilities, Mapping):
        raise GuidanceBoundaryError("Native obligation-family probabilities missing")
    # Empty heads in a real T0/T2 checkpoint remain an explicit no-learned-head
    # control. They cannot produce a causal effect or earn T3 consumption credit.
    if not probabilities:
        receipt.update(action="baseline_empty_native_head", native_head_empty=True, prediction_sha256=prediction_sha256)
        return receipt
    if set(probabilities) != set(REQUIRED_CHECKS):
        raise GuidanceBoundaryError("Native obligation vocabulary differs from the frozen two-check contract")
    values = {}
    for label, probability in probabilities.items():
        if isinstance(probability, bool) or not isinstance(probability, (int, float)):
            raise GuidanceBoundaryError("Probabilities must be numbers")
        if not math.isfinite(probability) or not 0 <= probability <= 1:
            raise GuidanceBoundaryError("Nonfinite or out-of-range probability")
        values[label] = float(probability)
    if abs(sum(values.values()) - 1.0) > 1e-6:
        raise GuidanceBoundaryError("Probabilities must sum to one")
    _hash(prediction.get("checkpoint_sha256"), "checkpoint_sha256")
    _hash(prediction.get("compact_sha256"), "compact_sha256")
    order = sorted(REQUIRED_CHECKS, key=lambda label: (-values[label], REQUIRED_CHECKS.index(label)))
    receipt.update(
        action="run_all_unchanged_checks_in_learned_order", check_order=order,
        order_changed=order != list(REQUIRED_CHECKS), learned_parameters_consumed=True,
        prediction_sha256=prediction_sha256, checkpoint_sha256=prediction["checkpoint_sha256"],
        prediction_full_source_sha256=prediction.get("text_sha256"),
        compact_sha256=prediction["compact_sha256"], model_arm=prediction.get("arm_id"), seed=prediction.get("seed"),
        native_head={"context": CONTEXT, "name": "obligation_family", "probabilities": values,
                     "proof_feedback_version_fingerprint": native.get("proof_feedback_version_fingerprint"),
                     "schema_version": native["schema_version"]},
        feature_to_action={label: {"feature": "proof_auxiliary_head_logits.obligation_family", "probability": values[label], "executed_priority": order.index(label)} for label in REQUIRED_CHECKS},
    )
    return receipt


def execute_checks(
    prediction: Mapping[str, Any], canonical_record: Mapping[str, Any],
    checks: Mapping[str, Callable[[dict[str, Any]], Mapping[str, Any] | bool]], **kwargs: Any,
) -> dict[str, Any]:
    """Invoke every unchanged check callback on an isolated identical candidate.

    Each callback returns bool or a JSON mapping with ``passed: bool``. Callback
    exceptions are retained failures, and never suppress subsequent checks. This
    function preserves the original candidate even if a callback mutates its copy.
    Such mutation is explicitly reported as an invalid check execution.
    """
    if set(checks) != set(REQUIRED_CHECKS) or not all(callable(v) for v in checks.values()):
        raise GuidanceBoundaryError("Every and only the two required check callbacks must be supplied")
    if kwargs.get("qualification_required"):
        # The publication run must execute the qualified native-schema check
        # functions; caller-supplied success callbacks cannot acquire credit.
        from structural_checks import CHECKS, checker_contract
        qualification = kwargs.get("qualification")
        if qualification is None or qualification.get("checker_contract") != checker_contract():
            raise GuidanceBoundaryError("Final callback source/native contracts differ from qualification")
        if any(checks[name] is not CHECKS[name] for name in REQUIRED_CHECKS):
            raise GuidanceBoundaryError("Final run replaced a qualified check callback")
    original = copy.deepcopy(dict(canonical_record))
    receipt = choose_check_order(prediction, canonical_record, **kwargs)
    started = time.monotonic()
    calls = []
    for name in receipt["check_order"]:
        candidate = copy.deepcopy(original)
        begin = time.monotonic()
        try:
            output = checks[name](candidate)
            if isinstance(output, bool):
                output = {"passed": output}
            if not isinstance(output, Mapping) or type(output.get("passed")) is not bool:
                raise GuidanceBoundaryError("Checker must return an explicit boolean passed field")
            output = copy.deepcopy(dict(output))
            canonical_bytes(output)
            if candidate != original:
                raise GuidanceBoundaryError("Checker mutated its isolated candidate")
            status = "passed" if output["passed"] else "failed"
        except Exception as exc:
            output = {"passed": False, "error_type": type(exc).__name__, "error": str(exc)}
            status = "error"
        calls.append({"check": name, "status": status, "result": output, "result_sha256": digest(output), "wall_seconds": time.monotonic()-begin})
    if canonical_record != original:
        raise GuidanceBoundaryError("Caller candidate changed during check execution")
    receipt.update(
        checks_executed=calls, all_required_checks_executed=len(calls)==len(REQUIRED_CHECKS),
        all_passed=all(r["status"] == "passed" for r in calls),
        first_failure_index=next((i for i,r in enumerate(calls) if r["status"] != "passed"), None),
        wall_seconds=time.monotonic()-started,
    )
    return receipt
