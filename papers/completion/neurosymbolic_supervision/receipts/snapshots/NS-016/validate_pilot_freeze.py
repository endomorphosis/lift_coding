#!/usr/bin/env python3
"""Sealed-profile structural validation for NS-016.

Stdlib only. Does not import semantic_state (anyio is absent from the sealed
validation environment), does not dispatch a provider, and does not start a
final attempt. Freeze-admission functions are checked in harness.py via AST
and re-implemented here against the frozen JSON.
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
PAPER = ROOT / "papers/completion/neurosymbolic_supervision"
SNAP = PAPER / "receipts/snapshots/NS-016"
HARNESS = ROOT / "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/harness.py"
ARMS = ("A", "B", "C", "D", "C-no-route", "C-no-reuse")
MEASUREMENT_KEYS = (
    "input_tokens",
    "output_tokens",
    "cached_input_tokens",
    "reasoning_tokens",
    "provider_charge",
    "host_cpu_seconds",
    "remote_gpu_seconds",
    "peak_aggregate_memory_bytes",
    "scratch_bytes",
    "retained_storage_bytes",
    "bytes_read",
    "bytes_written",
    "active_elapsed_seconds",
    "queue_wait_seconds",
    "human_wait_seconds",
    "human_active_seconds",
    "independent_scoring_cpu_seconds",
    "independent_scoring_elapsed_seconds",
    "prime_cpu_seconds",
    "prime_elapsed_seconds",
)
IDENTITY_KEYS = (
    "protocol_bundle_sha256",
    "final_freeze_sha256",
    "task_id",
    "family_id",
    "source_preimage_id",
    "runner_source_id",
    "oracle_manifest_id",
    "schedule_unit_id",
    "arm",
    "cache",
    "repetition",
)
TERMINAL = {
    "solved",
    "unsolved",
    "rejected",
    "abstained",
    "timed_out",
    "unavailable",
    "cancelled",
    "missing",
}
PIN_PATHS = (
    "papers/completion/neurosymbolic_supervision/protocol/preregistered_protocol.md",
    "papers/completion/neurosymbolic_supervision/protocol/experiment_manifest.json",
    "papers/completion/neurosymbolic_supervision/protocol/measurement_schema.json",
    "papers/completion/neurosymbolic_supervision/protocol/development_provider_amendment.json",
    "papers/completion/neurosymbolic_supervision/protocol/scope.md",
    "papers/completion/neurosymbolic_supervision/protocol/deadline_plan.md",
    "papers/completion/neurosymbolic_supervision/benchmark/tasks.jsonl",
    "papers/completion/neurosymbolic_supervision/benchmark/splits.json",
    "papers/completion/neurosymbolic_supervision/benchmark/oracle_manifest.json",
    "papers/completion/neurosymbolic_supervision/benchmark/provenance.md",
    "papers/completion/neurosymbolic_supervision/artifacts/source_forest.json",
    "papers/completion/neurosymbolic_supervision/experiments/run_comparison.py",
    "papers/completion/neurosymbolic_supervision/experiments/score_runs.py",
    "papers/completion/neurosymbolic_supervision/experiments/production_gateway.py",
    "papers/completion/neurosymbolic_supervision/experiments/production_profile.json",
    "papers/completion/neurosymbolic_supervision/experiments/receipt_schema.json",
    "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/harness.py",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_dumps(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def fail(message: str) -> None:
    raise SystemExit("NS-016 validation failed: " + message)


def freeze_body_hash(freeze: dict) -> str:
    body = {key: value for key, value in freeze.items() if key != "freeze_sha256"}
    return sha256_bytes(canonical_dumps(body).encode("utf-8"))


def measurement_complete(row: dict) -> list[str]:
    problems: list[str] = []
    fields = row.get("measurements")
    if not isinstance(fields, dict):
        return ["measurements_object"]
    for name in MEASUREMENT_KEYS:
        item = fields.get(name)
        if not isinstance(item, dict):
            problems.append(f"missing:{name}")
            continue
        status = item.get("status")
        value = item.get("value")
        reason = item.get("reason")
        if status not in {"actual", "estimated", "unavailable"}:
            problems.append(f"status:{name}")
        elif status == "unavailable":
            if value is not None or not isinstance(reason, str) or not reason.strip():
                problems.append(f"dishonest:{name}")
        elif not isinstance(value, (int, float)) or value < 0:
            problems.append(f"value:{name}")
    identity = row.get("identity") if isinstance(row.get("identity"), dict) else {}
    record_kind = row.get("record_kind")
    for name in IDENTITY_KEYS:
        value = identity.get(name)
        if name == "final_freeze_sha256":
            if record_kind == "final" and not (isinstance(value, str) and len(value) == 64):
                problems.append("identity:final_freeze_sha256")
            continue
        if name == "repetition":
            if type(value) is not int or value < 0:
                problems.append("identity:repetition")
            continue
        if value in (None, ""):
            problems.append(f"identity:{name}")
    if row.get("terminal_state") not in TERMINAL:
        problems.append("terminal_state")
    return problems


def harness_source_contract(tree: ast.AST, source: str) -> None:
    names = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    required = {
        "admit_final_attempt",
        "pilot_excluded_from_final",
        "developmental_split",
        "table17_cost_receipt_complete",
        "table18_boundary_receipt_complete",
        "arm_useful_path_status",
        "harness_loop_descriptor",
    }
    missing = sorted(required - names)
    if missing:
        fail("harness.py missing freeze functions: " + ",".join(missing))
    for token in (
        "FINAL_EXPERIMENT_FREEZE_SCHEMA",
        "final_attempt_requires_hashed_freeze",
        "developmental_tasks_excluded_from_final",
        "final_dispatch_without_freeze",
        "pilot_task_as_final_holdout",
        "unscored_retained_arm",
        "unavailable_resources_are_null_not_zero",
    ):
        if token not in source:
            fail(f"harness.py missing freeze token {token}")


def admit_final_attempt(freeze: dict, request: dict) -> dict:
    reasons: list[str] = []
    if freeze.get("schema") != "paper-ns-final-experiment-freeze/v1":
        reasons.append("freeze_schema_mismatch")
    if freeze.get("final_dispatch_authorized") is not True:
        reasons.append("final_dispatch_not_authorized")
    freeze_sha = freeze.get("freeze_sha256")
    if not isinstance(freeze_sha, str) or len(freeze_sha) != 64:
        reasons.append("freeze_sha256_missing")
    elif freeze_body_hash(freeze) != freeze_sha:
        reasons.append("freeze_sha256_mismatch")
    pins = freeze.get("immutable_pins")
    if not isinstance(pins, dict) or not pins:
        reasons.append("immutable_pins_missing")
    record_kind = str(request.get("record_kind") or "")
    split = str(request.get("split") or "")
    task_id = str(request.get("task_id") or "")
    family_id = str(request.get("family_id") or "")
    if record_kind == "final" or split == "final":
        if split in {"development", "pilot"}:
            reasons.append("developmental_task_in_final")
        if task_id in set(freeze.get("developmental_task_ids") or ()):
            reasons.append("pilot_or_development_task_in_final")
        if family_id in set(freeze.get("developmental_family_ids") or ()):
            reasons.append("pilot_or_development_family_in_final")
        if freeze.get("first_final_attempt_started") is True:
            reasons.append("freeze_already_consumed")
        served = freeze.get("served_model_identity") if isinstance(freeze.get("served_model_identity"), dict) else {}
        if not served.get("served_model"):
            reasons.append("served_model_identity_unavailable")
        if freeze.get("resource_reservation_obtained") is not True:
            reasons.append("resource_reservation_unavailable")
    retained = list(freeze.get("retained_executable_arms") or ())
    arm_paths = freeze.get("arm_useful_paths") if isinstance(freeze.get("arm_useful_paths"), dict) else {}
    for arm in retained:
        path = arm_paths.get(arm) if isinstance(arm_paths.get(arm), dict) else {}
        if path.get("has_useful_path") is not True or path.get("independently_scored") is not True:
            reasons.append(f"retained_arm_missing_useful_path:{arm}")
    removed = freeze.get("removed_arms") if isinstance(freeze.get("removed_arms"), dict) else {}
    for arm, meta in removed.items():
        if arm in retained:
            reasons.append(f"removed_arm_still_retained:{arm}")
        if not isinstance(meta, dict) or not str(meta.get("claim_update") or "").strip():
            reasons.append(f"removed_arm_missing_claim_update:{arm}")
    return {"admitted": not reasons, "reasons": reasons, "first_final_attempt_started": False}


def main() -> int:
    freeze = load_json(PAPER / "artifacts/final_experiment_freeze.json")
    manifest = load_json(PAPER / "protocol/final_run_manifest.json")
    splits = load_json(PAPER / "benchmark/splits.json")
    report = (PAPER / "pilot/readiness_report.md").read_text(encoding="utf-8")
    results = []
    with (PAPER / "pilot/results.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                results.append(json.loads(line))
    if freeze.get("schema") != "paper-ns-final-experiment-freeze/v1":
        fail("freeze schema")
    if freeze_body_hash(freeze) != freeze.get("freeze_sha256"):
        fail("freeze_sha256 does not match canonical body")
    if freeze.get("first_final_attempt_started") is not False:
        fail("first final attempt already started")
    if freeze.get("final_dispatch_authorized") is not True and freeze.get("final_dispatch_authorized") is not False:
        fail("final_dispatch_authorized must be a boolean")
    if freeze.get("final_dispatch_authorized") is True:
        fail("final dispatch must not be authorized given current readiness")
    if freeze.get("retained_executable_arms") != []:
        fail("executable final arms must be empty")

    dev = set(splits["development_families"])
    pilot = set(splits["pilot_families"])
    final = set(splits["final_families"])
    if dev & final or pilot & final or dev & pilot:
        fail("split families are not disjoint")
    if set(freeze["developmental_family_ids"]) != dev | pilot:
        fail("developmental families mismatch splits")
    if set(freeze["final_family_ids"]) != final:
        fail("final families mismatch splits")
    for task_id in freeze["developmental_task_ids"]:
        if task_id in set(freeze["final_task_ids"]):
            fail(f"developmental task in final: {task_id}")

    pins = freeze.get("immutable_pins") or {}
    for path in PIN_PATHS:
        digest = sha256_file(ROOT / path)
        if pins.get(path) != digest:
            fail(f"pin mismatch {path}")
    if set(PIN_PATHS) - set(pins):
        fail("missing immutable pins")

    source = HARNESS.read_text(encoding="utf-8")
    tree = ast.parse(source)
    harness_source_contract(tree, source)

    for arm in ARMS:
        path = (freeze.get("arm_useful_paths") or {}).get(arm) or {}
        removed = (freeze.get("removed_arms") or {}).get(arm) or {}
        if path.get("independently_scored") is not True or path.get("has_useful_path") is not True:
            fail(f"arm {arm} lacks independently scored useful path")
        if removed.get("removed_from_executable_final") is not True:
            fail(f"arm {arm} not removed from executable final")
        if not str(removed.get("claim_update") or "").strip():
            fail(f"arm {arm} missing claim update")

    fixture_arms = set()
    live_historical = []
    for row in results:
        if row.get("developmental") is not True and row.get("split") in {"development", "pilot"}:
            fail(f"pilot/dev row not labeled developmental: {row.get('task_id')}")
        if row.get("split") == "final":
            fail("results contain a final-split execution")
        if row.get("family_id") in final:
            fail(f"final family appeared in pilot results: {row.get('family_id')}")
        problems = measurement_complete(row)
        if problems:
            fail(f"Table 17 receipt incomplete {row.get('task_id')} {row.get('arm')}: {problems}")
        if row.get("provider", {}).get("simulated") is True and row.get("counts_as_live_repair") is True:
            fail("simulated stub counted as live repair")
        if row.get("fixture"):
            if row.get("terminal_state") != "solved" or row.get("oracle", {}).get("status") != "passed":
                fail(f"fixture arm failed: {row.get('arm')}")
            fixture_arms.add(row.get("arm"))
        if row.get("counts_as_live_repair"):
            live_historical.append(row)
        for name, item in (row.get("measurements") or {}).items():
            if item.get("status") == "unavailable" and item.get("value") == 0:
                fail(f"unavailable field stored as zero: {name}")
    if fixture_arms != set(ARMS):
        fail(f"fixture arms incomplete: {sorted(fixture_arms)}")
    if len(live_historical) != 1:
        fail(f"expected exactly one live historical solved unit, got {len(live_historical)}")
    live = live_historical[0]
    if live.get("task_id") != "ns-hist-01-xmltodict" or live.get("arm") != "A":
        fail("live historical unit is not xmltodict/A")
    if live.get("provider", {}).get("served_model") != "grok-4.6":
        fail("live historical served model mismatch")
    if live.get("provider", {}).get("simulated") is True:
        fail("live historical marked simulated")

    pilot_rows = [row for row in results if row.get("record_kind") == "pilot"]
    if len(pilot_rows) != 48:
        fail(f"expected 48 pilot-split records, got {len(pilot_rows)}")
    if any(row.get("terminal_state") != "unavailable" for row in pilot_rows):
        fail("pilot-split records must be unavailable without grants")
    hist_dev = [row for row in results if row.get("record_kind") == "development" and not row.get("fixture")]
    if len(hist_dev) != 16:
        fail(f"expected 16 development-split A-D/cold records, got {len(hist_dev)}")

    gate = admit_final_attempt(
        freeze,
        {
            "record_kind": "final",
            "split": "final",
            "task_id": "ns-hist-09-tomlkit",
            "family_id": "upstream:sdispater/tomlkit",
            "arm": "A",
            "final_freeze_sha256": freeze["freeze_sha256"],
        },
    )
    if gate["admitted"] is True:
        fail("final attempt was admitted")
    required_reasons = {
        "final_dispatch_not_authorized",
        "served_model_identity_unavailable",
        "resource_reservation_unavailable",
    }
    if not required_reasons <= set(gate["reasons"]):
        fail(f"final admission reasons incomplete: {gate['reasons']}")

    leak = admit_final_attempt(
        freeze,
        {
            "record_kind": "final",
            "split": "pilot",
            "task_id": "ns-hist-05-dnspython",
            "family_id": "upstream:rthalley/dnspython",
            "arm": "A",
            "final_freeze_sha256": freeze["freeze_sha256"],
        },
    )
    if leak["admitted"] is True:
        fail("pilot task admitted as final")
    if "developmental_task_in_final" not in leak["reasons"] and "pilot_or_development_task_in_final" not in leak["reasons"]:
        fail(f"pilot-as-final reasons incomplete: {leak['reasons']}")

    if manifest.get("schema") != "paper-ns-final-run-manifest/v1":
        fail("manifest schema")
    if manifest.get("freeze_sha256") != freeze.get("freeze_sha256"):
        fail("manifest freeze_sha256 mismatch")
    if manifest.get("dispatch_authorized") is not False:
        fail("manifest dispatch_authorized")
    if manifest.get("first_final_attempt_started") is not False:
        fail("manifest first_final_attempt_started")
    body = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    if sha256_bytes(canonical_dumps(body).encode("utf-8")) != manifest.get("manifest_sha256"):
        fail("manifest_sha256 mismatch")
    if len(manifest.get("units") or []) != 192:
        fail("amended final schedule must list 8 families x 6 arms x 2 cache x 2 reps = 192")
    if any(unit.get("record_kind") != "final" for unit in manifest["units"]):
        fail("manifest units must be record_kind=final")
    if any(unit.get("family_id") in (dev | pilot) for unit in manifest["units"]):
        fail("manifest scheduled a developmental family")

    for token in (
        "Excluded from final holdouts",
        "final_dispatch_authorized=false",
        freeze["freeze_sha256"],
        "Table 17",
        "unavailable",
        "ns-016-prefinal",
    ):
        if token not in report:
            fail(f"readiness report missing {token!r}")

    snap_freeze = SNAP / "artifacts/final_experiment_freeze.json"
    snap_manifest = SNAP / "protocol/final_run_manifest.json"
    snap_results = SNAP / "pilot/results.jsonl"
    snap_report = SNAP / "pilot/readiness_report.md"
    snap_harness = SNAP / "harness.py"
    for current, snapshot in (
        (PAPER / "artifacts/final_experiment_freeze.json", snap_freeze),
        (PAPER / "protocol/final_run_manifest.json", snap_manifest),
        (PAPER / "pilot/results.jsonl", snap_results),
        (PAPER / "pilot/readiness_report.md", snap_report),
        (HARNESS, snap_harness),
    ):
        if sha256_file(current) != sha256_file(snapshot):
            fail(f"snapshot drift: {current}")

    print(
        json.dumps(
            {
                "ok": True,
                "results": len(results),
                "fixture_arms": sorted(fixture_arms),
                "live_historical": 1,
                "pilot_unavailable": len(pilot_rows),
                "freeze_sha256": freeze["freeze_sha256"],
                "manifest_sha256": manifest["manifest_sha256"],
                "final_admitted": False,
                "first_final_attempt_started": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
