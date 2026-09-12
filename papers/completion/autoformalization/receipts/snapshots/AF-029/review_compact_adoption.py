#!/usr/bin/env python3
"""Sealed-PATH source/artifact review of the AF-029 compact adoption bundle.

Does not rerun training, regenerate feedback, reload multi-gigabyte checkpoint
payloads, or replace the retained-byte check_outputs.py verifier. That verifier
already PASSed against the original output tree; this script checks the
committed compact references and live/snapshot identity.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[6]
PAPER = ROOT / "papers" / "completion" / "autoformalization"
SNAPSHOT = Path(__file__).resolve().parent / "operator-adoption-v1"
TEMPLATE = PAPER / "qualification" / "operator_inputs" / "AF-029" / "pending_receipt.template.json"
TEMPLATE_SHA256 = "964c8c17ab3d172e25c5d8096b67b3bc65a02d5740871c8a65dc81fb761e30f6"
INPUTS_SHA256 = "6177c6e0957502d22012aef4555a35bb30d137f64a185e41546cae0a5dcb964a"
TEACHER_RAW_SHA256 = "97cf9da4711c4ae45431425f2b1b668df294e4c3fde6119f7aa9e97630607470"
SEEDS = {104729, 130363, 155921}
T2_IDS = {
    "00b940fcd4a96a67fdccde88310b5956e790e3a5d66055984d19cd1b3c61a8d8",
    "095147ede126c6a6f4f9f2817c208ce78e6662c3ce9d8ec6979a42aceac0ebf0",
    "cb766e9e811216a00f47ca8d96263c1d7dce4ec8c458f417ae36b11db8304c2b",
}
T3_IDS = {
    "def483e87bb57d27a8f24a3939a063d1039af95c111ec6d5733b452f612b5cbc",
    "c90b4b9e7fd0120a7507b5e98bf7130e6c1e63091c14200afd3c2ee137ca5faf",
    "a4e7a375e63e8a62c13691673342560596418095a0b1f0835ad6929d66d18be8",
}
E_REFUSE = "if arm_id == \"E\" or not capability.get(\"runnable\"):"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> int:
    errors: list[str] = []
    if sha256_file(TEMPLATE) != TEMPLATE_SHA256:
        errors.append("pending receipt template digest drifted")
    template = load_json(TEMPLATE)
    artifacts = template.get("artifacts") or {}
    outputs = template.get("outputs") or {}
    if len(artifacts) != 91 or len(outputs) != 91:
        errors.append(f"template mapping counts artifacts={len(artifacts)} outputs={len(outputs)}")

    for name, expected in artifacts.items():
        path = ROOT / name
        if not path.is_file():
            errors.append(f"missing snapshot {name}")
            continue
        digest = sha256_file(path)
        if digest != expected:
            errors.append(f"snapshot digest mismatch {name}")
        rel = path.relative_to(SNAPSHOT)
        live = PAPER / rel
        if not live.is_file():
            errors.append(f"missing live output {live.relative_to(ROOT)}")
        elif sha256_file(live) != expected:
            errors.append(f"live output differs from snapshot {live.relative_to(ROOT)}")

    for live_name, snapshot_name in outputs.items():
        if snapshot_name not in artifacts:
            errors.append(f"output maps to unhashed snapshot {live_name}")
        if live_name == snapshot_name:
            errors.append(f"output is its own snapshot {live_name}")

    evidence_files = {str(p.relative_to(ROOT)) for p in (PAPER / "evidence" / "native_training").rglob("*") if p.is_file()}
    expected_evidence = {name for name in outputs if name.startswith("papers/completion/autoformalization/evidence/native_training/")}
    extra = sorted(evidence_files - expected_evidence)
    missing = sorted(expected_evidence - evidence_files)
    if extra:
        errors.append("unaccounted evidence files: " + ", ".join(extra[:8]))
    if missing:
        errors.append("missing mapped evidence files: " + ", ".join(missing[:8]))

    inputs = load_json(PAPER / "data" / "native_training_inputs.json")
    if sha256_file(PAPER / "data" / "native_training_inputs.json") != INPUTS_SHA256:
        errors.append("native_training_inputs.json digest drifted")
    if inputs.get("scope") != "train_and_selection_only" or inputs.get("final_test_access") is not False:
        errors.append("encoder inputs are not train/selection-only")
    rows = inputs.get("rows") or []
    if len(rows) != 84:
        errors.append(f"expected 84 encoder rows, got {len(rows)}")
    if any(str(row.get("embedding_model") or "").startswith("mock") for row in rows):
        errors.append("mock embeddings present")
    splits = {row.get("split") for row in rows}
    if splits != {"train", "selection"}:
        errors.append(f"encoder splits {splits}")
    if sum(1 for row in rows if row.get("split") == "train") != 69:
        errors.append("encoder train population is not 69")
    if sum(1 for row in rows if row.get("split") == "selection") != 15:
        errors.append("encoder selection population is not 15")

    teacher = load_json(PAPER / "data" / "native_training_teacher_manifest.json")
    if teacher.get("schema") != "af029-native-delivered-artifact-reference/v1":
        errors.append("teacher manifest is not the compact delivered reference")
    if (teacher.get("raw_member") or {}).get("sha256") != TEACHER_RAW_SHA256:
        errors.append("teacher raw-member digest is not the nonempty 84-target artifact")
    if teacher.get("scientific_completion_admitted") is not False:
        errors.append("teacher compact reference admitted scientific completion")
    if teacher.get("e_locked") is not True:
        errors.append("teacher compact reference did not lock E")

    qualification = load_json(PAPER / "evidence" / "native_training" / "preparation" / "qualification.json")
    if qualification.get("real_offline_encoder_execution") is not True:
        errors.append("encoder qualification is not a real offline MiniLM execution")
    if qualification.get("grouping_vectors_reused") is not False:
        errors.append("encoder qualification reused grouping vectors")
    if qualification.get("final_sources_or_labels_accessed") is not False:
        errors.append("encoder qualification accessed final sources or labels")
    positive = qualification.get("positive") or {}
    if positive.get("rows") != 84 or (positive.get("splits") or {}) != {"train": 69, "selection": 15}:
        errors.append("encoder qualification population drifted")
    if qualification.get("input_artifact_sha256") != INPUTS_SHA256:
        errors.append("encoder qualification bound a different input digest")

    run = load_json(PAPER / "runs" / "native_training" / "manifest.json")
    env = run.get("environment") or {}
    if env.get("projection_update_backend") != "packed_cpu":
        errors.append("run manifest did not record packed_cpu")
    if env.get("stripped_profile_is_error") is not True:
        errors.append("stripped-profile error contract missing")
    if not env.get("torch", {}).get("ok") or not env.get("numpy", {}).get("ok"):
        errors.append("run manifest missing CPU Torch/NumPy origins")
    if not env.get("research_toolchain_sha256"):
        errors.append("research toolchain identity missing")
    if run.get("final_test_locked") is not True:
        errors.append("final test is not locked")
    promotion = run.get("promotion") or {}
    if promotion.get("e_locked") is not True:
        errors.append("E promotion is not locked")
    if promotion.get("generic_file_existence_insufficient") is not True:
        errors.append("generic file existence can activate E")
    if promotion.get("requires_af013_identity_bound_canary") is not True:
        errors.append("AF-013 identity-bound canary requirement missing")
    packed = (run.get("arms") or {}).get("T2", {}).get("packed_cpu") or []
    if {item.get("seed") for item in packed} != SEEDS or len(packed) != 3:
        errors.append("T2 packed reports missing a frozen seed")
    for item in packed:
        if item.get("backend") != "packed_cpu" or item.get("parameter_changed") is not True:
            errors.append(f"T2 seed {item.get('seed')} lacks committed packed update")
        shared = item.get("shared_parameter_change") or {}
        if (
            type(shared.get("changed_numeric_parameter_count")) is not int
            or shared["changed_numeric_parameter_count"] <= 0
            or shared.get("before_sha256") == shared.get("after_sha256")
        ):
            errors.append(f"T2 seed {item.get('seed')} has no shared-weight change")
        norms = item.get("gradient_norms") or []
        if not any(isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0 for v in norms):
            errors.append(f"T2 seed {item.get('seed')} has no nonzero shared gradient")
        if item.get("full_family_search") is not True:
            errors.append(f"T2 seed {item.get('seed')} did not search all shared families")
    memory = run.get("t2_live_memory_checks") or []
    if {row.get("seed") for row in memory} != SEEDS:
        errors.append("T2 live memory checks missing a seed")
    if any(
        row.get("trainer_sample_memory_used") is not False
        or row.get("sample_memory_entry_count") != 0
        or row.get("decoded_embeddings_unchanged") is not True
        for row in memory
    ):
        errors.append("T2 sample memory was not disabled")

    results = load_jsonl(PAPER / "runs" / "native_training" / "results.jsonl")
    costs = load_jsonl(PAPER / "runs" / "native_training" / "costs.jsonl")
    measured = {}
    for row in results:
        if row.get("split") == "final_test":
            if row.get("execution_status") != "unrun" or row.get("bodies_opened") or row.get("ids_inspected"):
                errors.append(f"final test opened {row.get('record_id')}")
        if row.get("execution_status") == "measured":
            measured.setdefault(row.get("arm_id"), []).append(row)
        if row.get("record_kind") == "aggregate" and (row.get("metrics") or {}).get("source_fidelity") is not None:
            errors.append(f"fabricated source fidelity {row.get('record_id')}")
    for arm in ("T0", "T1", "T2"):
        if not measured.get(arm):
            errors.append(f"no measured results for {arm}")
        aggregate_rows = [r for r in measured.get(arm, []) if r.get("record_kind") == "aggregate"]
        expected_ids = {1, 2, 3} if arm == "T0" else SEEDS
        field = "replay" if arm == "T0" else "seed"
        if {(r.get(field), r.get("split")) for r in aggregate_rows} != {
            (value, split) for value in expected_ids for split in ("train", "selection")
        }:
            errors.append(f"{arm} lacks complete matched train/selection evaluations")
    t3_rows = [row for row in results if row.get("arm_id") == "T3" and row.get("record_kind") == "t3_attempt"]
    if {row.get("seed") for row in t3_rows} != SEEDS:
        errors.append("T3 did not run all three seeds")
    for row in t3_rows:
        checkpoint = row.get("checkpoint") or {}
        detail = row.get("detail") or {}
        if not checkpoint.get("matched_t2") or checkpoint.get("matched_t2") != checkpoint.get("initial"):
            errors.append(f"T3 seed {row.get('seed')} missing matched T2 checkpoint")
        if int(row.get("update_count") or 0) <= 0 and int(detail.get("applied_count") or 0) <= 0:
            errors.append(f"T3 seed {row.get('seed')} did not train on admitted feedback")
        if detail.get("protected_parameters_unchanged") is not True:
            errors.append(f"T3 seed {row.get('seed')} did not protect primary representation")
        if detail.get("feedback_scope") != "native_compiler_structural_contracts_only":
            errors.append(f"T3 seed {row.get('seed')} used an unsupported feedback scope")
        if checkpoint.get("final") not in T3_IDS:
            errors.append(f"T3 seed {row.get('seed')} final identity is not bound")
    if not any(row.get("record_id") == "AF-029:preparation:encoder" for row in costs):
        errors.append("preparation costs were not carried forward")
    if not any(row.get("experiment_arm") == "T2" for row in costs):
        errors.append("T2 training costs missing")
    if not any(row.get("experiment_arm") == "T3-feedback" for row in costs):
        errors.append("checker costs missing")

    receipts = load_jsonl(PAPER / "evidence" / "native_training" / "native_checker_receipts.jsonl")
    if len(receipts) != 69:
        errors.append(f"expected 69 native checker receipts, got {len(receipts)}")
    if any(row.get("scope") != "native_compiler_structural_contracts_only" for row in receipts):
        errors.append("checker receipt left the pinned structural-contract scope")
    if any(row.get("semantic_fidelity_measured") is not False for row in receipts):
        errors.append("checker receipt claimed semantic fidelity")
    if any(
        not row.get("source_sha256")
        or not row.get("receipt_sha256")
        or not row.get("lean_source_sha256")
        or not row.get("binary_sha256")
        for row in receipts
    ):
        errors.append("a native checker receipt lacks source/goal/checker identity bindings")
    statuses = {row.get("status") for row in receipts}
    if not statuses <= {"checked", "timeout", "unsupported_fragment"}:
        errors.append(f"unexpected checker receipt statuses {statuses}")
    checked = sum(1 for row in receipts if row.get("status") == "checked" and row.get("exit_code") == 0)
    if checked != 61:
        errors.append(f"expected 61 successful checked receipts, got {checked}")
    if sum(1 for row in receipts if row.get("status") == "timeout") != 6:
        errors.append("original checker timeouts were rewritten")
    if sum(1 for row in receipts if row.get("status") == "unsupported_fragment") != 2:
        errors.append("unsupported-fragment receipts were rewritten")

    binding = load_json(PAPER / "evidence" / "native_training" / "eligible_checkpoint_binding.json")
    if set(binding.get("t2_identities") or []) != T2_IDS or set(binding.get("t3_identities") or []) != T3_IDS:
        errors.append("eligible-checkpoint identities drifted")
    if binding.get("e_locked") is not True:
        errors.append("eligible-checkpoint binding unlocked E")
    if binding.get("teacher_manifest_sha256") != TEACHER_RAW_SHA256:
        errors.append("eligible-checkpoint binding lost the nonmock teacher digest")

    checkpoints = load_json(PAPER / "checkpoints" / "native_training" / "manifest.json")
    if checkpoints.get("schema") != "af029-native-delivered-artifact-reference/v1":
        errors.append("checkpoint manifest is not the compact delivered reference")
    if checkpoints.get("e_locked") is not True:
        errors.append("checkpoint manifest unlocked E")
    nested = checkpoints.get("eligible_checkpoint_identities") or {}
    if set(nested.get("t2_identities") or []) != T2_IDS or set(nested.get("t3_identities") or []) != T3_IDS:
        errors.append("checkpoint manifest identities drifted")
    if checkpoints.get("scientific_completion_admitted") is not False:
        errors.append("checkpoint compact reference admitted scientific completion")

    recovered = (PAPER / "evidence" / "native_training" / "recovered_checker.stdout.log").read_text(encoding="utf-8")
    if "\nPASS\n" not in recovered and not recovered.startswith("PASS\n"):
        if "PASS" not in recovered.splitlines():
            errors.append("recovered checker log does not contain PASS")
    if '"admitted_feedback": 2606' not in recovered or '"e_locked": true' not in recovered:
        errors.append("recovered checker PASS did not bind admitted feedback and E lock")

    arms_source = (PAPER / "evaluation" / "pipeline_arms.py").read_text(encoding="utf-8")
    if E_REFUSE not in arms_source:
        errors.append("pipeline_arms.py no longer unconditionally refuses E")
    if "unavailable_pending_AF-011_AF-013" not in arms_source:
        errors.append("pipeline_arms.py lost the AF-013 promotion gate")

    config = load_json(PAPER / "config" / "pipeline_arms.json")
    arm_e = (config.get("arms") or {}).get("E") or {}
    if arm_e.get("development_route") != "unavailable_pending_AF-011_AF-013":
        errors.append("pipeline_arms.json activated E")

    for task_id in ("AF-011", "AF-012", "AF-020", "AF-028"):
        path = PAPER / "receipts" / f"{task_id}.json"
        if not path.is_file():
            errors.append(f"{task_id} receipt missing")
            continue
        prior = load_json(path)
        if prior.get("status") != "complete" or prior.get("task_id") != task_id:
            errors.append(f"{task_id} receipt is not a preserved complete receipt")

    scope = load_json(PAPER / "evidence" / "native_training" / "reconstruction_metric_scope.json")
    if "target-assisted" not in str(scope.get("finding") or ""):
        errors.append("reconstruction metric scope lost the target-assisted finding")
    if scope.get("scientific_training_calls") != 0:
        errors.append("metric-scope review mutated training")

    handoff = load_json(PAPER / "evidence" / "native_training" / "adoption_handoff.json")
    if handoff.get("native_mutation_available") is not False:
        errors.append("handoff claims a native mutation is available")
    if (handoff.get("promotion") or {}).get("e_locked") is not True:
        errors.append("handoff unlocked E")
    if "original checker OOM" not in str(handoff.get("original_container_outcome") or ""):
        errors.append("original checker OOM was not preserved")

    check_source = (PAPER / "evidence" / "native_training" / "check_outputs.py").read_text(encoding="utf-8")
    if "No Torch import" not in check_source.splitlines()[0] and "No Torch import" not in check_source:
        errors.append("authoritative validator is no longer the stdlib check_outputs.py")
    try:
        compile(check_source, "check_outputs.py", "exec")
    except (SyntaxError, ValueError, TypeError):
        errors.append("check_outputs.py is not valid Python")

    if errors:
        print("FAIL")
        for item in errors:
            print(item)
        return 1
    print("PASS")
    print(json.dumps({
        "admitted_feedback": 2606,
        "checker_receipts": 69,
        "e_locked": True,
        "encoder_rows": 84,
        "live_outputs_match_snapshots": True,
        "recovered_checker_pass_retained": True,
        "snapshot_artifacts": 91,
        "t2_identities": sorted(T2_IDS),
        "t3_identities": sorted(T3_IDS),
        "teacher_raw_sha256": TEACHER_RAW_SHA256,
        "template_sha256": TEMPLATE_SHA256,
        "whole_data_checking_rerun": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
