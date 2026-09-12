#!/usr/bin/env python3
"""Validate AF-011 training-baseline artifacts against acceptance criteria."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parents[2]
SEEDS = {104729, 130363, 155921}
ARMS = ("T0", "T1", "T2")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> int:
    manifest = load_json(PAPER_ROOT / "runs" / "training_baselines" / "manifest.json")
    results = load_jsonl(PAPER_ROOT / "runs" / "training_baselines" / "results.jsonl")
    checkpoints = load_json(PAPER_ROOT / "checkpoints" / "baselines" / "manifest.json")
    errors: list[str] = []

    if manifest.get("schema") != "autoformalization-training-baselines-manifest/v1":
        errors.append("bad run manifest schema")
    if checkpoints.get("schema") != "autoformalization-baseline-checkpoints/v1":
        errors.append("bad checkpoint manifest schema")
    if manifest.get("config_id") != checkpoints.get("config_id"):
        errors.append("config_id mismatch between run and checkpoint manifests")
    if manifest.get("dataset_id") != checkpoints.get("dataset_id"):
        errors.append("dataset_id mismatch between run and checkpoint manifests")

    executed = defaultdict(list)
    for row in results:
        if row.get("schema") != "autoformalization-training-baseline-result/v1":
            errors.append(f"bad result schema {row.get('record_id')}")
        arm = row.get("arm_id")
        if arm not in ARMS:
            errors.append(f"unknown arm {arm}")
        if row.get("execution_status") == "measured":
            executed[arm].append(row)
            required = ("dataset_id", "config_id", "checkpoint", "termination_reason", "update_count")
            if any(row.get(key) in (None, "") for key in required):
                errors.append(f"executed row missing identities {row.get('record_id')}")
            checkpoint = row.get("checkpoint") or {}
            if "initial" not in checkpoint or "final" not in checkpoint:
                errors.append(f"executed row missing checkpoint hashes {row.get('record_id')}")
            if row.get("claim_admissible") is True:
                errors.append(f"measured row marked claim_admissible {row.get('record_id')}")
            metrics = row.get("metrics") or {}
            if row.get("record_kind") == "aggregate":
                if metrics.get("vector_mse") is None or metrics.get("vector_cosine") is None:
                    errors.append(f"aggregate missing vector diagnostics {row.get('record_id')}")
                if metrics.get("source_fidelity") is not None:
                    errors.append(f"source fidelity fabricated {row.get('record_id')}")
                if metrics.get("native_proof_coverage") is not None:
                    errors.append(f"proof coverage fabricated {row.get('record_id')}")
        if row.get("split") == "final_test":
            if row.get("execution_status") != "unrun" or row.get("bodies_opened") or row.get("ids_inspected"):
                errors.append(f"final test was opened or marked executed {row.get('record_id')}")
            if row.get("result_kind") != "no_run":
                errors.append(f"final test is not no_run {row.get('record_id')}")

    for arm in ARMS:
        if not executed[arm]:
            errors.append(f"no measured results for executed arm {arm}")
        train_n = {
            row["source_record_id"]
            for row in executed[arm]
            if row.get("split") == "train" and row.get("record_kind") == "item"
        }
        sel_n = {
            row["source_record_id"]
            for row in executed[arm]
            if row.get("split") == "selection" and row.get("record_kind") == "item"
        }
        if len(train_n) != 69:
            errors.append(f"{arm} train item coverage {len(train_n)} != 69")
        if len(sel_n) != 15:
            errors.append(f"{arm} selection item coverage {len(sel_n)} != 15")

    t0_replays = {row.get("replay") for row in executed["T0"] if row.get("record_kind") == "aggregate"}
    if t0_replays != {1, 2, 3}:
        errors.append(f"T0 replays {t0_replays}")
    if not manifest["arms"]["T0"].get("deterministic_across_replays"):
        errors.append("T0 replays were not deterministic")

    t1_seeds = {row.get("seed") for row in executed["T1"] if row.get("record_kind") == "aggregate"}
    t2_seeds = {row.get("seed") for row in executed["T2"] if row.get("record_kind") == "aggregate"}
    if t1_seeds != SEEDS:
        errors.append(f"T1 seeds {t1_seeds}")
    if t2_seeds != SEEDS:
        errors.append(f"T2 seeds {t2_seeds}")

    t1_train_mem = [
        row
        for row in executed["T1"]
        if row.get("record_kind") == "aggregate"
        and row.get("split") == "train"
        and row.get("sample_memory_used") is True
        and row.get("split_role") == "seen_training_partition"
    ]
    t1_sel_mem = [
        row
        for row in executed["T1"]
        if row.get("record_kind") == "aggregate"
        and row.get("split") == "selection"
        and row.get("sample_memory_used") is True
    ]
    if not t1_train_mem or not t1_sel_mem:
        errors.append("T1 missing seen/unseen memory diagnostics")
    else:
        if not all(row.get("metrics", {}).get("vector_cosine", 0) > 0.5 for row in t1_train_mem):
            errors.append("T1 seen-source memory diagnostic did not reconstruct")
        if not all(
            row.get("metrics", {}).get("vector_cosine", 1) < t1_train_mem[0]["metrics"]["vector_cosine"]
            for row in t1_sel_mem
        ):
            errors.append("T1 unseen cosine was not separated from seen memory diagnostic")
        if any(row.get("extra", {}).get("generalization_claim") for row in t1_train_mem):
            errors.append("T1 labeled as generalization")

    for row in executed["T2"]:
        if row.get("split") == "train" and row.get("split_role") == "seen_training_partition":
            if row.get("sample_memory_used") is not False:
                errors.append(f"T2 evaluation memory was on {row.get('record_id')}")
        if row.get("sample_memory_entry_count") not in (0, None) and row.get("split_role") != "seen_training_partition_memory_probe":
            if row.get("sample_memory_entry_count") != 0:
                errors.append(f"T2 retained sample memory {row.get('record_id')}")

    if not checkpoints.get("t2_memory_disabled"):
        errors.append("checkpoint manifest did not confirm T2 memory disabled")
    if checkpoints.get("final_test_used_to_select_settings"):
        errors.append("final test selected model settings")
    if manifest["final_test_access"].get("used_to_select_model_settings"):
        errors.append("manifest says final test selected settings")
    if manifest["final_test_access"].get("bodies_opened") or manifest["final_test_access"].get("ids_inspected"):
        errors.append("final test was accessed")
    if not manifest["t2_source_memory_contract"].get("t2_memory_disabled_in_source"):
        errors.append("T2 source contract missing")
    if not all(check.get("trainer_sample_memory_used") is False for check in manifest["arms"]["T2"]["live_memory_checks"]):
        errors.append("live T2 trainer used sample memory")
    if not all(check.get("decoded_embeddings_unchanged") for check in manifest["arms"]["T2"]["live_memory_checks"]):
        errors.append("T2 decoded embeddings changed")

    alternative = manifest.get("budget_constrained_alternative") or {}
    if alternative.get("status") != "narrowed_methods_and_development_diagnostics":
        errors.append("missing narrowed alternative")
    forbidden = " ".join(alternative.get("not_claimed") or []).lower()
    if "training gain" not in alternative.get("reason", "").lower() and "no training gain" not in alternative.get("reason", "").lower():
        if "training gain" not in forbidden:
            errors.append("narrowed alternative does not exclude a fabricated training gain")
    if "Table 11 held-out all-facet source fidelity" not in alternative.get("not_claimed", []):
        errors.append("narrowed alternative still allows Table 11 fidelity")

    ckpt_t0 = [row for row in checkpoints["runs"] if row["arm_id"] == "T0"]
    ckpt_t1 = [row for row in checkpoints["runs"] if row["arm_id"] == "T1"]
    ckpt_t2 = [row for row in checkpoints["runs"] if row["arm_id"] == "T2"]
    if len(ckpt_t0) != 3 or len(ckpt_t1) != 3 or len(ckpt_t2) != 3:
        errors.append(f"checkpoint run counts T0={len(ckpt_t0)} T1={len(ckpt_t1)} T2={len(ckpt_t2)}")
    for row in ckpt_t0 + ckpt_t1 + ckpt_t2:
        if not row.get("initial_checkpoint_sha256") or not row.get("final_checkpoint_sha256"):
            errors.append(f"checkpoint missing identities {row}")
        if "update_count" not in row or not row.get("termination_reason"):
            errors.append(f"checkpoint missing update/termination {row.get('arm_id')} {row.get('seed')}")
        if "config_id" not in row or "dataset_id" not in row:
            errors.append("checkpoint missing dataset/config identity")
    for row in ckpt_t2:
        if row.get("sample_memory_enabled_for_update") or row.get("sample_memory_enabled_for_evaluation"):
            errors.append("T2 checkpoint enables memory")
        if row.get("sample_memory_entry_count") != 0:
            errors.append("T2 checkpoint has sample memory entries")

    print(
        json.dumps(
            {
                "n_results": len(results),
                "n_checkpoints": len(checkpoints["runs"]),
                "t0_deterministic": manifest["arms"]["T0"]["deterministic_across_replays"],
                "t2_memory_disabled": checkpoints["t2_memory_disabled"],
                "final_test_locked": not manifest["final_test_access"]["bodies_opened"],
                "errors": errors,
                "ok": not errors,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
