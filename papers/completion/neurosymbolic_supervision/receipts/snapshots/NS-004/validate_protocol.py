"""Validate the frozen NS-004 specification; this runs no repair experiment."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import jsonschema

ROOT = Path.cwd()
FOLDER = ROOT / "papers/completion/neurosymbolic_supervision/protocol"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check():
    manifest = json.loads((FOLDER / "experiment_manifest.json").read_text())
    schema = json.loads((FOLDER / "measurement_schema.json").read_text())
    document = (FOLDER / "preregistered_protocol.md").read_text()
    assert sha(FOLDER / "preregistered_protocol.md") == manifest["protocol_sha256"]
    assert sha(FOLDER / "measurement_schema.json") == manifest["measurement_schema_sha256"]
    payload = {k: v for k, v in manifest.items() if k != "protocol_bundle_sha256"}
    assert hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == manifest["protocol_bundle_sha256"]
    assert manifest["final_execution_ready"] is False and manifest["scope_change_authorized"] is False
    assert manifest["population"]["actual_recruited_count"] is None
    assert manifest["population"]["total_families"] == sum(manifest["population"][k] for k in
        ("development_families", "pilot_families", "final_families")) == 24
    schedule, arms = manifest["schedule"], manifest["arms"]
    n = manifest["population"]["final_families"]
    assert n == 16 and len(schedule["final_repetitions"]) == len(schedule["cache_profiles"]) == 2
    assert schedule["final_main_units"] == n * 4 * 2 * 2 == 256
    assert schedule["final_additional_ablation_units"] == n * 2 * 2 * 2 == 128
    assert schedule["final_total_units"] == n * len(arms) * 2 * 2 == 384
    assert schedule["total_comparison_units"] == 384 + schedule["development_units"] + schedule["pilot_units"] == 448
    assert {k for k in arms["A"] if arms["A"][k] != arms["B"][k]} == {"context"}
    assert {k for k in arms["C"] if arms["C"][k] != arms["C-no-route"][k]} == {"routing"}
    # Disabling reuse entails full execution; this is one mechanism with its
    # explicitly declared validation-mode consequence, not a weaker oracle.
    assert {k for k in arms["C"] if arms["C"][k] != arms["C-no-reuse"][k]} == {"reuse", "validation"}
    assert {k for k in arms["C"] if arms["C"][k] != arms["D"][k]} == {"governed_lifecycle"}
    limits = manifest["budgets"]
    assert limits["campaign_provider_effects_max"] == 448 + limits["pre_final_boundary_provider_effects_reserved"] == 512
    assert limits["proposal_effects_per_unit"] == limits["reserved_cpu_cores"] == limits["concurrent_ns_scientific_containers"] == 1
    assert limits["limits_enforced_and_reserved"] is False
    assert limits["unknown_paid_effect_replay_allowed"] is False
    assert manifest["inference"]["noninferiority_margin_absolute"] == 0.05
    assert manifest["inference"]["minimum_robust_useful_completion"] == 0.25
    assert manifest["inference"]["power_guarantee"] is False
    assert 0.1707 < 1 - 0.05 ** (1 / n) < 0.1708
    assert manifest["amortization"]["horizons"] == [1, 10, 100, 1000]
    assert manifest["boundary_qualification"]["planned_cases"] == 16 * 4 * 2 == 128
    assert manifest["boundary_qualification"]["counts_as_live_repair"] is False
    assert manifest["boundary_qualification"]["unsafe_controls_can_publish"] is False
    assert all(t in manifest["core_obligations_retained"] for t in ["NS-005", "NS-006", "NS-016", "NS-017", "NS-018", "NS-019", "NS-020"])
    assert not any(marker in document.lower() for marker in ["[tbd]", "[to be filled]", "[todo]"])
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema)
    # This deliberately missing schema fixture is not an attempt, oracle or
    # live result. Its only purpose is to test record-admission constraints.
    sample = {
        "schema": "paper-ns-attempt-measurement/v1", "record_kind": "schema_validation_fixture",
        "identity": {"protocol_bundle_sha256": manifest["protocol_bundle_sha256"], "final_freeze_sha256": None,
            "task_id": "schema-fixture", "family_id": "schema-fixture", "source_preimage_id": "schema-fixture",
            "runner_source_id": "schema-fixture", "oracle_manifest_id": "schema-fixture", "schedule_unit_id": "schema-fixture",
            "arm": "A", "cache": "local_cold", "repetition": 0},
        "terminal_state": "missing", "terminal_reason": "Schema validation fixture only; no actual run",
        "scheduled": True, "started_at": None, "finished_at": "schema-fixture-not-a-time",
        "provider": {"dispatched": False, "logical_effect_id": None, "served_provider": None, "served_model": None,
            "served_revision": None, "revision_availability_reason": "No provider in schema fixture", "reasoning_effort": None,
            "runtime_receipt_id": None, "usage_receipt_id": None, "possibly_charged": False,
            "sampling_seed_supported": False, "temperature_supported": False, "proposal_effect_count": 0,
            "provider_cache_observed": None},
        "oracle": {"status": "not_run", "independent_scorer_id": None, "receipt_id": None,
            "cold_full_validation": False, "candidate_valid": None, "hidden_access_incident": False, "reason": "schema fixture"},
        "admission": {"attempted": False, "admitted": None, "mandatory_evidence_current": False, "scope_preserved": False,
            "publication_required": False, "publication_admitted": None, "publication_receipt_id": None,
            "current_parent_id": None, "candidate_kind": "none", "candidate_artifact_id": None, "target_patch_exposed": False},
        "measurements": {k: {"status": "unavailable", "value": None, "unit": "schema-fixture-unit", "source": None,
                              "reason": "No measurement: schema fixture only"} for k in manifest["metrics"]["schema_measurements"]},
        "stages": [], "budget": {"serialized_request_bytes": None, "patch_bytes": None, "limit_triggered": None,
                                  "observed_overshoot": {}, "reconciliation_required": False},
        "control": {"consumed_evidence_ids": [], "next_action": None, "fallback_count": 0, "replan_count": 0,
                    "manual_intervention_count": 0, "reuse_cold_disagreement": None},
        "deviation_ids": [], "interpretation_limits": ["Structural schema fixture; no empirical data"]}
    validator.validate(sample)
    negatives = []
    for name, mutate in [
        ("unscored_solved", lambda v: v.update(terminal_state="solved")),
        ("unfrozen_final", lambda v: v.update(record_kind="final")),
        ("unavailable_zero", lambda v: v["measurements"]["provider_charge"].update(value=0)),
        ("actual_null", lambda v: v["measurements"]["provider_charge"].update(status="actual")),
        ("second_proposal", lambda v: v["provider"].update(proposal_effect_count=2)),
        ("unidentified_dispatch", lambda v: v["provider"].update(dispatched=True)),
        ("D_without_publication_requirement", lambda v: v["identity"].update(arm="D")),
    ]:
        value = deepcopy(sample)
        mutate(value)
        assert list(validator.iter_errors(value)), name
        negatives.append(name)
    return {"protocol_contract_valid": True, "protocol_bundle_sha256": manifest["protocol_bundle_sha256"],
            "final_execution_ready": False, "planned_comparison_units": 448, "observed_live_repair_results": 0,
            "structural_negative_cases_rejected": negatives,
            "scope": "Static protocol/hash/arithmetic/schema checks only; no provider invocation or research result"}


if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
