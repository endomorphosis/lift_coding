#!/usr/bin/env python3
"""Stdlib checks of AF-029 native-training artifacts. No Torch import."""
from __future__ import annotations

import json
import sys
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


def main() -> int:
    errors: list[str] = []
    inputs = PAPER / "data" / "native_training_inputs.json"
    if sha256_file(inputs) != INPUTS_SHA256:
        errors.append("native_training_inputs.json digest drifted")
    encoder = load_json(inputs)
    if encoder.get("scope") != "train_and_selection_only" or encoder.get("final_test_access") is not False:
        errors.append("encoder inputs are not train/selection-only")
    if any(row.get("embedding_model", "").startswith("mock") for row in encoder.get("rows", [])):
        errors.append("mock embeddings present")
    if len(encoder.get("rows") or []) != 84:
        errors.append("expected 84 encoder rows")

    teacher = load_json(PAPER / "data" / "native_training_teacher_manifest.json")
    if teacher.get("targets_produced") != 84 or teacher.get("empty_target_map") is not False:
        errors.append("teacher targets missing or empty")
    if teacher.get("encoder", {}).get("mock") is True:
        errors.append("teacher encoder marked mock")
    if not teacher.get("producer", {}).get("version"):
        errors.append("teacher producer version missing")
    if any(not row.get("artifact_sha256") or not row.get("view_distribution") for row in teacher.get("rows") or []):
        errors.append("a teacher row lacks digest-bound views")

    run = load_json(PAPER / "runs" / "native_training" / "manifest.json")
    results = load_jsonl(PAPER / "runs" / "native_training" / "results.jsonl")
    costs = load_jsonl(PAPER / "runs" / "native_training" / "costs.jsonl")
    checkpoints = load_json(PAPER / "checkpoints" / "native_training" / "manifest.json")
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
    for item in run.get("arms", {}).get("T2", {}).get("packed_cpu") or []:
        if item.get("backend") != "packed_cpu":
            errors.append(f"T2 seed {item.get('seed')} backend {item.get('backend')}")
        if not item.get("applied_packed_updates") and not item.get("parameter_changed"):
            errors.append(f"T2 seed {item.get('seed')} has no packed updates or parameter change")
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
    receipts = HERE / "native_checker_receipts.jsonl"
    if not receipts.is_file() or not load_jsonl(receipts):
        errors.append("native checker receipts missing")
    prior = PAPER / "receipts" / "AF-011.json"
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
