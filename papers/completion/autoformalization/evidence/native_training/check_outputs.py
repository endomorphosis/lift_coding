#!/usr/bin/env python3
"""Stdlib checks of AF-029 native-training artifacts. No Torch import."""
from __future__ import annotations

import argparse
import json
import math
import sys
sys.dont_write_bytecode = True
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPER = HERE.parent.parent
SEEDS = {104729, 130363, 155921}
INPUTS_SHA256 = "6177c6e0957502d22012aef4555a35bb30d137f64a185e41546cae0a5dcb964a"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def sha256_file(path: Path) -> str:
    import hashlib
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


SHARED_COMPONENTS = ('compiler_quality_embedding_weights', 'compiler_quality_family_logits', 'decompiler_plan_embedding_weights', 'decompiler_plan_family_logits', 'decompiler_plan_legal_ir_view_logits', 'family_embedding_weights', 'family_legal_ir_view_embedding_weights', 'family_semantic_slot_embedding_weights', 'family_semantic_slot_legal_ir_view_embedding_weights', 'family_semantic_slot_legal_ir_view_logits', 'feature_embedding_weights', 'feature_family_logits', 'feature_legal_ir_view_logits', 'legal_ir_view_embedding_weights', 'legal_ir_view_family_logits', 'legal_ir_view_logits', 'logic_signature_embedding_weights', 'logic_signature_family_logits', 'logic_signature_legal_ir_view_logits', 'predicate_argument_embedding_weights', 'predicate_argument_family_logits', 'predicate_argument_legal_ir_view_logits', 'round_trip_signal_embedding_weights', 'round_trip_signal_family_logits', 'round_trip_signal_legal_ir_view_logits', 'semantic_slot_embedding_weights', 'semantic_slot_family_logits', 'semantic_slot_legal_ir_view_embedding_weights', 'semantic_slot_legal_ir_view_family_logits', 'semantic_slot_legal_ir_view_logits')

def shared_evidence(before, after):
    import hashlib
    def canonical(value):
        return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    def numbers(value, prefix=()):
        if isinstance(value, dict):
            return {p: v for key, item in value.items() for p, v in numbers(item, (*prefix, str(key))).items()}
        if isinstance(value, (list, tuple)):
            return {p: v for key, item in enumerate(value) for p, v in numbers(item, (*prefix, str(key))).items()}
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError("invalid numeric shared parameter")
        return {prefix: float(value)}
    left = {key: before.get(key, {}) for key in SHARED_COMPONENTS}
    right = {key: after.get(key, {}) for key in SHARED_COMPONENTS}
    changed = {}
    for component in SHARED_COMPONENTS:
        old, new = numbers(left[component]), numbers(right[component])
        count = sum(old.get(key, 0.0) != new.get(key, 0.0) for key in old.keys() | new.keys())
        if count:
            changed[component] = count
    return {"before_sha256": canonical(left), "after_sha256": canonical(right),
            "changed_numeric_parameter_count": sum(changed.values()),
            "changed_components": changed, "components": list(SHARED_COMPONENTS)}

def verify_feedback(root, coverage, receipts, teacher_rows, expected_train_ids):
    import importlib.util
    path = HERE / "verify_feedback_artifacts.py"
    spec = importlib.util.spec_from_file_location("af029_retained_feedback_verifier", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.feedback_artifact_errors(root, coverage, receipts, teacher_rows, expected_train_ids)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper-root", type=Path, default=PAPER)
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    source_root = args.paper_root.resolve()
    run_root = (args.output_root or source_root).resolve()
    evidence_root = run_root / "evidence" / "native_training"
    errors: list[str] = []
    inputs = source_root / "data" / "native_training_inputs.json"
    if sha256_file(inputs) != INPUTS_SHA256:
        errors.append("native_training_inputs.json digest drifted")
    encoder = load_json(inputs)
    if encoder.get("scope") != "train_and_selection_only" or encoder.get("final_test_access") is not False:
        errors.append("encoder inputs are not train/selection-only")
    if any(row.get("embedding_model", "").startswith("mock") for row in encoder.get("rows", [])):
        errors.append("mock embeddings present")
    if len(encoder.get("rows") or []) != 84:
        errors.append("expected 84 encoder rows")

    teacher = load_json(run_root / "data" / "native_training_teacher_manifest.json")
    if teacher.get("targets_produced") != 84 or teacher.get("empty_target_map") is not False:
        errors.append("teacher targets missing or empty")
    if teacher.get("encoder", {}).get("mock") is True:
        errors.append("teacher encoder marked mock")
    if not teacher.get("producer", {}).get("version"):
        errors.append("teacher producer version missing")
    if any(not row.get("artifact_sha256") or not row.get("view_distribution") for row in teacher.get("rows") or []):
        errors.append("a teacher row lacks digest-bound views")

    run = load_json(run_root / "runs" / "native_training" / "manifest.json")
    results = load_jsonl(run_root / "runs" / "native_training" / "results.jsonl")
    costs = load_jsonl(run_root / "runs" / "native_training" / "costs.jsonl")
    checkpoints = load_json(run_root / "checkpoints" / "native_training" / "manifest.json")
    if run.get("environment", {}).get("projection_update_backend") != "packed_cpu":
        errors.append("run manifest did not record packed_cpu")
    if run.get("environment", {}).get("stripped_profile_is_error") is not True:
        errors.append("stripped-profile error contract missing")
    if run.get("final_test_locked") is not True:
        errors.append("final test is not locked")
    if run.get("promotion", {}).get("e_locked") is not True:
        errors.append("E promotion is not locked")
    if checkpoints.get("promotion_unlocked") is not False:
        errors.append("eligible checkpoint manifest unlocked E")
    if checkpoints.get("mock_teacher") is not False:
        errors.append("checkpoint manifest marked mock teacher")
    feedback = teacher.get("native_checker_feedback") or {}
    coverage = feedback.get("coverage") or {}
    if (feedback.get("feedback_scope") != "native_compiler_structural_contracts_only"
            or feedback.get("semantic_fidelity_measured") is not False
            or feedback.get("previous_constant_138_checks_excluded") is not True
            or coverage.get("scope") != "native_compiler_structural_contracts_only"
            or coverage.get("train_rows") != 69 or coverage.get("selection_rows") != 0 or coverage.get("final_rows") != 0
            or coverage.get("semantic_fidelity_measured") is not False
            or (coverage.get("prior_trivial_checks") or {}).get("admissible") is not False):
        errors.append("T3 lacks actual source-contract feedback scope and full training denominator")
    if checkpoints.get("feedback_scope") != "native_compiler_structural_contracts_only" or checkpoints.get("semantic_fidelity_measured") is not False:
        errors.append("checkpoint feedback scope promotes unsupported semantic credit")
    if not checkpoints.get("t2_identities") or not checkpoints.get("t3_identities"):
        errors.append("missing T2/T3 checkpoint identities")
    if checkpoints.get("generic_file_existence_insufficient") is not True:
        errors.append("checkpoint manifest allows generic file existence to activate E")

    measured = {}
    for row in results:
        if row.get("split") == "final_test":
            if row.get("execution_status") != "unrun" or row.get("bodies_opened") or row.get("ids_inspected"):
                errors.append(f"final test opened {row.get('record_id')}")
        if row.get("execution_status") == "measured":
            measured.setdefault(row.get("arm_id"), []).append(row)
        if row.get("record_kind") == "aggregate" and row.get("metrics", {}).get("source_fidelity") is not None:
            errors.append(f"fabricated source fidelity {row.get('record_id')}")
    for arm in ("T0", "T1", "T2"):
        if not measured.get(arm):
            errors.append(f"no measured results for {arm}")
    t2_seeds = {row.get("seed") for row in measured.get("T2", []) if row.get("record_kind") == "aggregate" and row.get("split") == "train"}
    if t2_seeds != SEEDS:
        errors.append(f"T2 seeds {t2_seeds} != {SEEDS}")
    t0_replays = {row.get("replay") for row in measured.get("T0", []) if row.get("record_kind") == "aggregate" and row.get("split") == "train"}
    if t0_replays != {1, 2, 3}:
        errors.append(f"T0 replays {t0_replays}")
    packed_reports = run.get("arms", {}).get("T2", {}).get("packed_cpu") or []
    if len(packed_reports) != 3 or {item.get("seed") for item in packed_reports} != SEEDS:
        errors.append("T2 packed reports must contain exactly one report for each fixed seed")
    for item in packed_reports:
        if item.get("backend") != "packed_cpu":
            errors.append(f"T2 seed {item.get('seed')} backend {item.get('backend')}")
        # An inner executor can report an applied no-op before a later
        # candidate fails and the outer transaction rolls back. Require the
        # committed outer result, not merely an attempted optimizer step.
        norms = item.get("gradient_norms") or []
        if not norms or any(not isinstance(v, (int, float)) or isinstance(v, bool)
                            or not math.isfinite(v) or v < 0 for v in norms):
            errors.append(f"T2 seed {item.get('seed')} has invalid gradient evidence")
        elif not any(v > 0 for v in norms):
            errors.append(f"T2 seed {item.get('seed')} has no nonzero shared gradient")
        if not item.get("applied_packed_updates") or item.get("parameter_changed") is not True:
            errors.append(f"T2 seed {item.get('seed')} has no committed shared parameter change")
        if item.get("full_family_search") is not True or set(item.get("considered_families") or []) != {"legal_ir_view_global_logits", "legal_ir_view_logits", "family_logits", "decoded_embedding", "combined"}:
            errors.append(f"T2 seed {item.get('seed')} did not consider all five shared families")
        shared = item.get("shared_parameter_change") or {}
        if (type(shared.get("changed_numeric_parameter_count")) is not int
                or shared["changed_numeric_parameter_count"] <= 0
                or not shared.get("before_sha256") or not shared.get("after_sha256")
                or shared["before_sha256"] == shared["after_sha256"]):
            errors.append(f"T2 seed {item.get('seed')} has no actual shared-weight change")
        if type(item.get("accepted_epochs")) is not int or item["accepted_epochs"] <= 0:
            errors.append(f"T2 seed {item.get('seed')} has no accepted outer epoch")
    for arm in ("T0", "T1", "T2"):
        aggregate_rows = [r for r in measured.get(arm, []) if r.get("record_kind") == "aggregate"]
        expected_ids = {1, 2, 3} if arm == "T0" else SEEDS
        field = "replay" if arm == "T0" else "seed"
        if len(aggregate_rows) != 6 or {(r.get(field), r.get("split")) for r in aggregate_rows} != {(value, split) for value in expected_ids for split in ("train", "selection")}:
            errors.append(f"{arm} lacks complete matched train/selection evaluations")
        for row in aggregate_rows:
            expected_count = 69 if row.get("split") == "train" else 15
            if (row.get("counts") or {}).get("eligible") != expected_count or (row.get("counts") or {}).get("measured") != expected_count:
                errors.append(f"{arm} evaluation denominator is not the frozen full population")
    for row in measured.get("T2", []):
        if row.get("record_kind") != "aggregate":
            continue
        checkpoint = row.get("checkpoint") or {}
        if row.get("failure") or row.get("termination_reason") == "packed_cpu_update_failure":
            errors.append(f"T2 seed {row.get('seed')} retained a training failure")
        if not checkpoint.get("initial") or not checkpoint.get("final") or checkpoint["initial"] == checkpoint["final"]:
            errors.append(f"T2 seed {row.get('seed')} has unchanged or missing checkpoint identity")
        if type(row.get("accepted_epochs")) is not int or row["accepted_epochs"] <= 0:
            errors.append(f"T2 seed {row.get('seed')} has no accepted epoch in its result")
    # Bind scalar training reports to the retained native outer result and
    # the complete checkpoint bytes that were actually reloaded.
    reloads = checkpoints.get("checkpoint_reload_verification") or []
    expected_finals = {(arm, seed) for arm in ("T2", "T3") for seed in SEEDS}
    final_reloads = [r for r in reloads if Path(r.get("path", "")).name.endswith("-final.json") and r.get("arm_id") in ("T2", "T3")]
    if len(final_reloads) != 6 or {(r.get("arm_id"), r.get("seed")) for r in final_reloads} != expected_finals:
        errors.append("missing exact six complete T2/T3 checkpoint reloads")
    initial_reloads = [r for r in reloads if Path(r.get("path", "")).name.endswith("-initial.json") and r.get("arm_id") == "T2"]
    if len(initial_reloads) != 3 or {r.get("seed") for r in initial_reloads} != SEEDS:
        errors.append("missing three exact initial T2 checkpoint payloads")
    by_checkpoint = {}
    by_state = {}
    for record in [*initial_reloads, *final_reloads]:
        path = (run_root / record["path"]).resolve()
        if not path.is_relative_to(run_root) or not path.is_file() or sha256_file(path) != record.get("file_sha256"):
            errors.append("checkpoint file missing or its bytes changed")
            continue
        payload = load_json(path)
        import hashlib
        identity = hashlib.sha256(json.dumps(payload.get("state"), sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        if (payload.get("schema") != "autoformalization-native-state-checkpoint/v2"
                or not isinstance(payload.get("state"), dict)
                or record.get("all_parameters_equal") is not True
                or record.get("loader") != "ModalAutoencoderTrainingState.from_dict"
                or not identity == payload.get("identity_sha256") == record.get("identity_sha256") == record.get("reloaded_identity_sha256")):
            errors.append("complete native checkpoint payload/reload mismatch")
        phase = "initial" if Path(record["path"]).name.endswith("-initial.json") else "final"
        by_state[(record["arm_id"], record["seed"], phase)] = payload.get("state")
        if phase == "final":
            by_checkpoint[(record["arm_id"], record["seed"])] = identity
    for item in packed_reports:
        path = evidence_root / f"T2-{item['seed']}-outer-result.json"
        if not path.is_file():
            errors.append("missing retained outer training result")
            continue
        outer = load_json(path)
        before = by_state.get(("T2", item["seed"], "initial"))
        after = by_state.get(("T2", item["seed"], "final"))
        if before is None or after is None or shared_evidence(before, after) != item.get("shared_parameter_change"):
            errors.append("reported shared learning differs from retained numeric checkpoint values")
        if (outer.get("failure") or outer.get("parameter_changed") is not True
                or outer.get("gradient_norms") != item.get("gradient_norms")
                or outer.get("shared_parameter_change") != item.get("shared_parameter_change")
                or outer.get("full_family_search") is not True
                or outer.get("considered_families") != item.get("considered_families")
                or outer.get("accepted_epochs") != item.get("accepted_epochs")
                or outer.get("final_checkpoint_sha256") != by_checkpoint.get(("T2", item["seed"]))):
            errors.append("packed report is not bound to committed outer update/checkpoint")
    t3_rows = [row for row in results if row.get("arm_id") == "T3" and row.get("record_kind") == "t3_attempt"]
    if {row.get("seed") for row in t3_rows} != SEEDS:
        errors.append("T3 did not run all three seeds")
    if any(not (row.get("checkpoint") or {}).get("matched_t2") for row in t3_rows):
        errors.append("T3 missing matched T2 checkpoint identity")
    admitted = (teacher.get("native_checker_feedback") or {}).get("admitted_records", 0)
    if admitted <= 0:
        errors.append("no admitted native checker feedback")
    else:
        if any(row.get("update_count", 0) <= 0 for row in t3_rows):
            errors.append("T3 did not train on admitted feedback")
    if not any(row.get("record_id") == "AF-029:preparation:encoder" for row in costs):
        errors.append("preparation costs were not carried forward")
    if not any(row.get("experiment_arm") == "T2" for row in costs):
        errors.append("T2 training costs missing")
    if not any(row.get("experiment_arm") == "T3-feedback" for row in costs):
        errors.append("checker costs missing")
    receipts = evidence_root / "native_checker_receipts.jsonl"
    if not receipts.is_file() or not load_jsonl(receipts):
        errors.append("native checker receipts missing")
    else:
        try:
            errors.extend(verify_feedback(evidence_root / "source_obligation_feedback", coverage,
                load_jsonl(receipts), teacher.get("rows") or [],
                [row["record_id"] for row in encoder["rows"] if row.get("split") == "train"]))
        except (OSError, ValueError, TypeError, KeyError) as exc:
            errors.append("feedback artifact verification failed: " + type(exc).__name__)
    prior = source_root / "receipts" / "AF-011.json"
    if not prior.is_file():
        errors.append("AF-011 receipt missing")
    if errors:
        print("FAIL")
        for item in errors:
            print(item)
        return 1
    print("PASS")
    print(json.dumps({
        "encoder_rows": len(encoder["rows"]),
        "teacher_targets": teacher["targets_produced"],
        "admitted_feedback": admitted,
        "t2_identities": checkpoints["t2_identities"],
        "t3_identities": checkpoints["t3_identities"],
        "e_locked": True,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
