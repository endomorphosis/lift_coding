#!/usr/bin/env python3
"""Validate NS-007 published context qualification artifacts.

Stdlib plus the sealed producer/consumer sources. Re-checks structural
invariants and performs a live smoke of cold/incremental roots, packing,
and patch rejection. Does not claim a live A–D experiment.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import runpy
import sys


ROOT = Path(__file__).resolve().parents[6]
PAPER = ROOT / "papers/completion/neurosymbolic_supervision"
QUAL = PAPER / "qualification"
SNAP = PAPER / "receipts/snapshots/NS-007"
SNAP_QUAL = SNAP / "qualification"
RUNNER = SNAP / "run_context_qualification.py"

MANDATORY_FAMILIES = {
    "unchanged",
    "localized",
    "renamed",
    "deleted",
    "configuration",
    "dependency",
    "fixture",
    "dynamic",
    "native",
    "stale_map",
    "repair",
    "context_core",
}
CRITERIA = (
    "All retained context cases preserve mandatory acceptance material and expose unknown/opaque frontiers.",
    "Cold/incremental roots and selected/full validation agree within the declared profile; mismatches receive failures and cause fixes or explicit limitations.",
    "Valid source-bound patches apply and stale/out-of-scope preimages reject.",
    "Context reduction is measured with the same actual tokenizer for both modes, with fallback rates retained.",
)


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def fail(message: str) -> None:
    raise SystemExit(f"NS-007 validation failed: {message}")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    cases_path = QUAL / "context_cases.json"
    results_path = QUAL / "context_results.jsonl"
    report_path = QUAL / "context_report.md"
    for path in (cases_path, results_path, report_path, RUNNER):
        if not path.is_file():
            fail(f"missing {path}")

    cases = load_json(cases_path)
    rows = load_jsonl(results_path)
    report = report_path.read_text(encoding="utf-8")

    if cases.get("schema") != "neurosymbolic-supervision/context-qualification-cases@1":
        fail("unexpected cases schema")
    if cases.get("task_id") != "NS-007":
        fail("cases task_id mismatch")
    if not rows:
        fail("empty results")
    if any(row.get("schema") != "neurosymbolic-supervision/context-qualification-result@1" for row in rows):
        fail("result schema mismatch")

    families = {row["family"] for row in rows if row.get("retained")}
    missing_families = MANDATORY_FAMILIES - families
    if missing_families:
        fail(f"missing retained families: {sorted(missing_families)}")

    retained = [row for row in rows if row.get("retained")]
    if not retained:
        fail("no retained cases")
    for row in retained:
        if row.get("status") != "pass":
            fail(f"retained case failed: {row['case_id']}")
        if not row.get("mandatory_acceptance_preserved"):
            fail(f"mandatory acceptance not preserved: {row['case_id']}")
        if not row.get("opaque_or_unknown_exposed"):
            fail(f"unknown/opaque frontier not exposed: {row['case_id']}")

    producer_rows = [row for row in retained if row.get("producer")]
    if not producer_rows:
        fail("no producer results")
    for row in producer_rows:
        agree = row["producer"].get("cold_incremental_agree")
        if agree is False and "cold_incremental_root_mismatch" not in (row.get("limitations") or []):
            fail(f"cold/incremental mismatch without limitation: {row['case_id']}")
        pytest_cmp = row.get("pytest")
        if pytest_cmp and pytest_cmp.get("selected_full_agree") is False and "selected_full_validation_mismatch" not in (row.get("limitations") or []):
            fail(f"selected/full mismatch without limitation: {row['case_id']}")

    valid = next((row for row in rows if row["case_id"] == "repair_valid_source_bound"), None)
    stale = next((row for row in rows if row["case_id"] == "repair_stale_preimage"), None)
    oos = next((row for row in rows if row["case_id"] == "repair_out_of_scope"), None)
    if not valid or not valid.get("repair", {}).get("applied"):
        fail("valid source-bound patch did not apply")
    if not valid["repair"].get("caller_root_unchanged"):
        fail("valid apply mutated the caller root")
    if not stale or stale.get("repair", {}).get("accepted") is not False:
        fail("stale preimage was not rejected")
    if not oos or oos.get("repair", {}).get("accepted") is not False:
        fail("out-of-scope patch was not rejected")

    tokenizer = cases.get("tokenizer") or {}
    if tokenizer.get("same_estimator_for_raw_and_semantic") is not True:
        fail("tokenizer was not shared across modes")
    if tokenizer.get("fallback_rate") is None:
        fail("tokenizer fallback rate missing")
    packing = [row for row in rows if row.get("context")]
    if not packing:
        fail("no context packing measurements")
    if any(not row["context"].get("same_estimator_object") for row in packing):
        fail("packing did not use the same estimator object")
    if any(row["context"].get("token_reduction_fraction") is None for row in packing):
        fail("context reduction was not measured")
    if "calibrated_utf8" not in report or "Fallback rate" not in report:
        fail("report omitted tokenizer fallback")
    if "IsolatedPatchWorktree" not in report:
        fail("report omitted source-linked edit path")
    if "CST/AST" not in report:
        fail("report omitted CST/AST limitation")

    by_id = {row["case_id"]: row for row in rows}
    for required in (
        "unchanged",
        "local_body",
        "rename",
        "delete",
        "config",
        "lock",
        "fixture",
        "dynamic",
        "native",
        "repair_valid_source_bound",
        "repair_stale_preimage",
        "repair_out_of_scope",
        "stale_capsule_map",
        "context_core_nontruncatable",
    ):
        if required not in by_id:
            fail(f"missing required case {required}")

    for name in ("context_cases.json", "context_results.jsonl", "context_report.md"):
        current = QUAL / name
        snapshot = SNAP_QUAL / name
        if not snapshot.is_file():
            fail(f"missing snapshot {snapshot}")
        if digest(current) != digest(snapshot):
            fail(f"current output differs from snapshot: {name}")

    # Live smoke using the same runner bootstrap.
    sys.path.insert(0, str(SNAP))
    runner = runpy.run_path(str(RUNNER))
    capability = runner["prepare_sealed_imports"]()
    api = runner["load_surfaces"](capability)
    if capability.get("anyio") or capability.get("multiformats") or capability.get("tiktoken"):
        # Presence is allowed; absence was the recorded profile. Do not fail closed on extra tools.
        pass
    if not capability["public_semantic_state_import"]["error"] and not capability.get("anyio"):
        fail("public semantic_state import unexpectedly succeeded without anyio")

    import tempfile, shutil
    tmp = Path(tempfile.mkdtemp(prefix="ns007-validate-", dir="/tmp"))
    try:
        repo = tmp / "baseline"
        api["materialize_baseline"](repo)
        runner["init_repo"](repo)
        first_index, first_bundle, _ = runner["scan_and_build"](api, repo)
        second_index, second_bundle, _ = runner["scan_and_build"](
            api, repo, previous_index=first_index, previous_bundle=first_bundle
        )
        if first_index.state_cid != second_index.state_cid or first_bundle.root.root_cid != second_bundle.root.root_cid:
            fail("live smoke: cold/incremental roots disagreed")
        estimator = api["CalibratedTokenEstimator"]()
        target_cid = api["cid_for_bytes"]((repo / "pkg/core.py").read_bytes())
        surrounding_cid = api["cid_for_bytes"]((repo / "pkg/callers.py").read_bytes())
        test_cid = api["cid_for_bytes"]((repo / "tests/test_core.py").read_bytes())
        packing = runner["pack_modes"](
            api,
            estimator=estimator,
            target_cid=target_cid,
            surrounding_cid=surrounding_cid,
            test_cid=test_cid,
            delta_cid=first_index.state_cid,
            obligation_cids=[first_bundle.root.root_cid],
            interface_cids=[],
            admissions=[],
            assumptions=["validate-smoke"],
        )
        if not packing["mandatory_cids_match"] or not packing["same_estimator_object"]:
            fail("live smoke: packing did not preserve mandatory CIDs on one estimator")
        patch = "not a patch"
        rejected = api["validate_patch"](patch, api["PatchScope"].from_dict({"allowed_paths": ["pkg/"], "effect_paths": ["pkg/core.py"], "task_owned_paths": ["pkg/"]}), run_apply_check=False)
        if rejected.accepted:
            fail("live smoke: malformed patch was accepted")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("NS-007 context qualification: OK")
    print(f"rows={len(rows)} retained={len(retained)} families={len(families)}")
    print("cold_incremental=agree_or_limited; valid_apply=pass; stale_oos=reject; tokenizer_fallback_retained")
    print("live_smoke=cold_incremental_agree,pack_mandatory,malformed_patch_reject")


if __name__ == "__main__":
    main()
