#!/usr/bin/env python3
"""Check AF-014 outputs against the three acceptance criteria."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
PAPER = HERE.parents[2]
REPO = PAPER.parents[2]
RULE_ID = "af014-executable-exception-scoping/v1"
CANARY_SHA256 = "98549048682ea1eb727812a6bb8e9d7a9834c22d43a62fd5373b7b7fad97c207"
PRE_PATCH = {
    "spacy_modal_codec.py": "fd40489c229a8976e50e31d5b9b46184796d7b0cd73e35531dfd0e817833b26f",
    "codec.py": "0f81dad45244ab88d3df5ac8c5d585d80d4ee14c59a5441c1bdd19f5a2cccd86",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> int:
    results = load_jsonl(PAPER / "runs" / "compiler_repair" / "results.jsonl")
    trace = load_json(PAPER / "evidence" / "repair_task_trace.json")
    validation = load_json(PAPER / "evidence" / "repair_validation.json")
    diff = PAPER / "evidence" / "compiler_patch.diff"
    errors: list[str] = []

    by_id = {row.get("record_id"): row for row in results}
    required_ids = {
        "T5-DEV-MP09-EXCEPTION-SCOPE",
        "T5-DEV-MP12-SHARED-LOSS-RETAINED",
        "T5-CANARY-STRUCTURAL",
        "T5-T4-STARTING-ARM",
        "T5-FINAL-TEST",
        "T5-NATIVE-CHECKERS",
        "T5-UNEXECUTED-SYNTHESIS",
        "T5-NO-MEASURED-IMPROVEMENT",
    }
    missing = required_ids - set(by_id)
    if missing:
        errors.append(f"missing result rows {sorted(missing)}")

    stages = [item.get("stage") for item in trace.get("chain", [])]
    if stages != [
        "observed_defect",
        "task_proposal",
        "actual_patch",
        "validation_evidence",
        "activation_configuration",
        "rollback_identity",
    ]:
        errors.append(f"trace stages {stages}")
    if trace.get("rule_id") != RULE_ID:
        errors.append("trace rule_id mismatch")
    if trace.get("starting_arm") != "T4" or trace.get("starting_arm_status") != "unactivated/unavailable":
        errors.append("T4 starting arm not pinned as unactivated/unavailable")
    rollback = next(item for item in trace["chain"] if item["stage"] == "rollback_identity")
    if rollback.get("restore_pre_patch_blobs") != PRE_PATCH:
        errors.append("rollback identity does not restore the frozen pre-patch blobs")
    if rollback.get("applied_learning_rollback_performed") is not False:
        errors.append("rollback must not claim applied-learning rollback")
    activation = next(item for item in trace["chain"] if item["stage"] == "activation_configuration")
    if activation.get("parameter_action") is not False:
        errors.append("activation must distinguish the executable rule from a parameter action")
    if activation.get("t4_learned_guidance") != "unactivated/unavailable":
        errors.append("T4 guidance still looks activated")

    mp09 = by_id.get("T5-DEV-MP09-EXCEPTION-SCOPE") or {}
    observation = (mp09.get("compiler_observation") or {})
    deontic = next((item for item in observation.get("formulas", []) if item.get("family") == "deontic"), None)
    if not deontic or deontic.get("predicate") != "audit":
        errors.append(f"MP09 deontic predicate is {None if deontic is None else deontic.get('predicate')}")
    if deontic and "exempt" in str(deontic.get("predicate", "")).split("_"):
        errors.append("MP09 still folds exempt into the governing predicate")
    if deontic and not any("unless exempt" in item for item in deontic.get("exceptions", [])):
        errors.append("MP09 lost the unless exempt slot")
    unless = next(
        (item for item in observation.get("formulas", []) if str(item.get("cue", "")).lower() == "unless"),
        None,
    )
    if not unless or unless.get("role") != "exception":
        errors.append("unless cue is not role=exception")

    mp12 = by_id.get("T5-DEV-MP12-SHARED-LOSS-RETAINED") or {}
    shared = mp12.get("shared_loss") or validation.get("shared_loss") or {}
    if shared.get("source_meaning_equal") is not False:
        errors.append("MP12 source meaning was equalized; shared source error was removed")
    if shared.get("recompiled_ir_equal") is not True:
        errors.append("MP12 independent IR-equality witness drifted")
    if shared.get("meaning_disagreement_count") != 1:
        errors.append(f"MP12 disagreement count {shared.get('meaning_disagreement_count')}")

    canary = by_id.get("T5-CANARY-STRUCTURAL") or {}
    if canary.get("used_for_patch_selection") is not False:
        errors.append("canary used for patch selection")
    if canary.get("n_records") != 38 or canary.get("canary_sha256") != CANARY_SHA256:
        errors.append("canary identity drifted")
    if (by_id.get("T5-FINAL-TEST") or {}).get("execution_status") != "no_run":
        errors.append("final test is not unrun")
    if (by_id.get("T5-FINAL-TEST") or {}).get("extra", {}).get("used_for_patch_selection"):
        errors.append("final test used for patch selection")
    final_extra = by_id.get("T5-FINAL-TEST") or {}
    if final_extra.get("used_for_patch_selection") is not False:
        errors.append("final-test patch selection flag missing")
    if validation.get("final_test", {}).get("used_for_patch_selection") is not False:
        errors.append("validation final_test used for patch selection")
    if validation.get("final_test", {}).get("opened") is not False:
        errors.append("final test was opened")
    if validation.get("canary", {}).get("used_for_patch_selection") is not False:
        errors.append("validation canary used for patch selection")

    if (by_id.get("T5-NO-MEASURED-IMPROVEMENT") or {}).get("accepted_improvement_is_measured_outcome") is not False:
        errors.append("accepted improvement was reported as a measured outcome")
    if (by_id.get("T5-UNEXECUTED-SYNTHESIS") or {}).get("execution_status") != "no_run":
        errors.append("unexecuted synthesis is not unrun")
    if (by_id.get("T5-T4-STARTING-ARM") or {}).get("outcome") != "t4_unactivated_unavailable":
        errors.append("T4 starting arm row missing")
    if not any(row.get("outcome") == "rejected_patch" for row in results):
        errors.append("rejected patches were not retained")

    if not diff.is_file() or diff.stat().st_size < 100:
        errors.append("compiler_patch.diff missing or empty")
    diff_text = diff.read_text(encoding="utf-8") if diff.is_file() else ""
    if "EXCEPTION_SCOPE_RULE_ID" not in diff_text:
        errors.append("diff does not contain the exception-scope rule")
    if "spacy_modal_codec.py" not in diff_text or "codec.py" not in diff_text:
        errors.append("diff does not name both codec files")

    if validation.get("all_structural_contracts_passed") is not True:
        errors.append("validation did not pass structural contracts")
    if validation.get("activation", {}).get("parameter_action") is not False:
        errors.append("validation treats the patch as a parameter action")
    if not validation.get("claim_limits"):
        errors.append("validation missing claim limits")

    spacy = REPO / "external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/spacy_modal_codec.py"
    codec = REPO / "external/ipfs_datasets/ipfs_datasets_py/logic/modal/codec.py"
    if RULE_ID.encode("utf-8") not in spacy.read_bytes():
        errors.append("live spacy codec missing exception-scope rule")
    if RULE_ID.encode("utf-8") not in codec.read_bytes():
        errors.append("live modal codec missing exception-scope rule")
    if b"_apply_executable_exception_scoping" not in codec.read_bytes():
        errors.append("live modal codec missing executable exception-scoping pass")

    if errors:
        print("AF-014 check FAIL")
        for item in errors:
            print(" -", item)
        return 1
    print(
        json.dumps(
            {
                "task_id": "AF-014",
                "status": "pass",
                "result_rows": len(results),
                "trace_stages": stages,
                "canary_records": 38,
                "final_test": "unrun",
                "t4": "unactivated/unavailable",
                "accepted_improvement_is_measured_outcome": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
