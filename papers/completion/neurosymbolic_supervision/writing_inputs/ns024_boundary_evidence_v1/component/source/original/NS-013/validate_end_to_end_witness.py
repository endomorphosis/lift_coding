#!/usr/bin/env python3
"""Validate NS-013 published end-to-end witness artifacts.

Re-checks structural invariants and performs a live smoke of routing change,
denied-write observation, incomplete-manifest rejection, and simulated-unit
non-publication. This is qualification evidence, not a matched A–D experiment.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile


SNAP = Path(__file__).resolve().parent
ROOT = SNAP.parents[5]
PAPER = ROOT / "papers/completion/neurosymbolic_supervision"
QUAL = PAPER / "qualification"
SNAP_QUAL = SNAP / "qualification"
RUNNER = SNAP / "run_end_to_end_witness.py"

CRITERIA = (
    "A genuine task progresses from authorized input to independently accepted patch and matching published post-root.",
    "Every step links current source/task/plan/obligation/evidence IDs; relevant symbolic/context evidence visibly changes the route or admission decision.",
    "The valid permitted action still works while the specified denied-effect violation is repaired/rejected.",
    "A rejected or incomplete path cannot report completion, and simulation-only runs remain labeled qualification rather than live success.",
)

REQUIRED_STEPS = (
    "capture_state",
    "state_obligation",
    "obtain_counterexample",
    "plan_bounded_repair",
    "choose_reasoning_route",
    "validate_candidate",
    "reuse_narrowly",
    "seal_and_publish",
    "learn_without_self_approval",
    "invalid_denied_effect_rejected",
    "incomplete_cannot_complete",
    "simulation_labeled_qualification",
)


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def fail(message: str) -> None:
    raise SystemExit(f"NS-013 validation failed: {message}")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def live_smoke() -> None:
    sys.path.insert(0, str(SNAP))
    import run_end_to_end_witness as runner

    api_bundle = runner.prepare_imports()
    api = api_bundle["api"]
    routing = api["route_model"]
    RoutingInputs = api["RoutingInputs"]
    before = routing(
        RoutingInputs.from_dict(
            {
                "context_tokens": 800,
                "lowest_confidence": "heuristic",
                "risk": "medium",
                "dependency_cone_size": 4,
                "unresolved_obligations": 1,
                "prior_repair_failures": 0,
                "available_proofs": 0,
                "prior_route_failed": False,
            }
        )
    )
    after = routing(
        RoutingInputs.from_dict(
            {
                "context_tokens": 800,
                "lowest_confidence": "exact",
                "risk": "low",
                "dependency_cone_size": 2,
                "unresolved_obligations": 1,
                "prior_repair_failures": 0,
                "available_proofs": 1,
                "prior_route_failed": False,
            }
        )
    )
    if runner.enum_val(after.route) != "deterministic_only":
        fail(f"live route after evidence was {after.route}")
    if runner.enum_val(before.route) == runner.enum_val(after.route):
        fail("live smoke route did not change when symbolic/context evidence was bound")

    with tempfile.TemporaryDirectory(prefix="ns013-smoke-") as tmp:
        root = Path(tmp) / "fixture"
        root.mkdir()
        runner.materialize_fixture(root, records=runner.BUGGY_RECORDS)
        buggy = runner.observe_denied_write(root / "pkg/records.py")
        if not buggy["denied_write_persisted"]:
            fail("buggy fixture did not persist a denied write")
        if not buggy["permitted_write_works"]:
            fail("buggy fixture broke permitted writes")
        (root / "pkg/records.py").write_text(runner.FIXED_RECORDS, encoding="utf-8")
        fixed = runner.observe_denied_write(root / "pkg/records.py")
        if fixed["denied_write_persisted"]:
            fail("repaired fixture still persisted a denied write")
        if not fixed["permitted_write_works"]:
            fail("repaired fixture lost permitted writes")

    empty = api["create_full_checkpoint"](
        runner._state(api, revision="rev-empty"),
        runner._policy(api),
        units=(),
        expected_unit_ids=("unit/test-denied-no-write",),
        parent_seal_cid=api["GENESIS_PARENT_SEAL"],
        fallback_reasons=("first_state",),
    )
    simulated = api["create_full_checkpoint"](
        runner._state(api, revision="rev-sim"),
        runner._policy(api),
        units=(
            runner._unit(
                api,
                "unit/sim",
                proof_mode=api["ProofMode"].SIMULATED.value,
                terminal_status=api["ProofTerminalStatus"].SIMULATED.value,
            ),
        ),
        expected_unit_ids=("unit/sim",),
    )
    if empty.sealed or simulated.sealed:
        fail("live smoke sealed an incomplete or simulated required unit")


def main() -> None:
    witness_path = QUAL / "end_to_end_witness.json"
    trace_path = QUAL / "end_to_end_trace.jsonl"
    study_path = QUAL / "end_to_end_case_study.md"
    for path in (witness_path, trace_path, study_path, RUNNER, SNAP / "compat_shims.py"):
        if not path.is_file():
            fail(f"missing {path}")
    if digest(witness_path) != digest(SNAP_QUAL / "end_to_end_witness.json"):
        fail("current witness differs from snapshot")
    if digest(trace_path) != digest(SNAP_QUAL / "end_to_end_trace.jsonl"):
        fail("current trace differs from snapshot")
    if digest(study_path) != digest(SNAP_QUAL / "end_to_end_case_study.md"):
        fail("current case study differs from snapshot")

    witness = load_json(witness_path)
    rows = load_jsonl(trace_path)
    study = study_path.read_text(encoding="utf-8")
    if witness.get("schema") != "neurosymbolic-supervision/end-to-end-witness@1":
        fail("witness schema mismatch")
    if witness.get("task_id") != "NS-013":
        fail("witness task_id mismatch")
    if witness.get("live_ad_experiment") is not False:
        fail("witness claimed a live A-D experiment")
    if witness.get("simulation_counted_as_success") is not False:
        fail("simulation was counted as success")
    if witness.get("qualification_not_live_ad") is not True:
        fail("qualification label missing")
    if witness.get("table6_labels_replaced") is not True:
        fail("schematic Table 6 labels were not replaced")

    ids = witness.get("ids") or {}
    for key in (
        "task_cid",
        "source_id",
        "pre_tree",
        "post_tree",
        "policy_cid",
        "obligation_id",
        "plan_cid",
        "counterexample_id",
        "patch_digest",
        "evidence_ids",
    ):
        if not ids.get(key):
            fail(f"missing identity {key}")
    if ids["pre_tree"] == ids["post_tree"]:
        fail("post-root tree matches the unrepaired pre-tree")
    schematic = ("R0", "P0", "T0", "O0", "S0", "F0", "E0")
    blob = json.dumps(ids)
    if any(token in blob.split('"') for token in schematic):
        fail("schematic Table 6 labels remain in identities")

    valid = witness.get("valid_path") or {}
    if not valid.get("applied") or valid.get("pytest_exit") != 0:
        fail("valid path was not independently accepted")
    if valid.get("denied_write_persisted") is not False:
        fail("valid path still persisted a denied write")
    if valid.get("permitted_write_works") is not True:
        fail("valid path lost the permitted write")
    if valid.get("caller_root_unchanged") is not True:
        fail("valid path mutated the caller root")

    invalid = witness.get("invalid_path") or {}
    if invalid.get("denied_write_persisted") is not True:
        fail("invalid path did not retain the denied-effect violation")
    if invalid.get("reported_completion") is not False:
        fail("invalid path reported completion")
    if invalid.get("incomplete_completion_reported") is not False:
        fail("incomplete path reported completion")
    if invalid.get("simulated_counted_as_success") is not False:
        fail("simulated unit counted as success")

    pub = witness.get("publication") or {}
    if not pub.get("published") or not pub.get("seal_cid"):
        fail("complete path did not publish a parent-bound seal")
    if pub.get("pointer_seal_cid") and pub["pointer_seal_cid"] != pub["seal_cid"]:
        fail("published pointer does not match the accepted seal")

    route = witness.get("route_change") or {}
    if (route.get("before") or {}).get("route") == (route.get("after") or {}).get("route"):
        fail("symbolic/context evidence did not change the route")
    if (route.get("after") or {}).get("route") != "deterministic_only":
        fail("bound evidence did not admit deterministic_only")

    if [row.get("step") for row in rows] != list(REQUIRED_STEPS):
        fail("trace steps missing or reordered")
    for row, step in zip(rows, REQUIRED_STEPS):
        if row.get("schema") != "neurosymbolic-supervision/end-to-end-trace@1":
            fail(f"{step} has the wrong trace schema")
        for field in ("source_id", "task_cid", "plan_cid", "obligation_id"):
            if not row.get(field):
                fail(f"{step} missing {field}")
        if not row.get("evidence_ids"):
            fail(f"{step} missing evidence_ids")
        if row.get("live_ad_experiment") is not False:
            fail(f"{step} claimed live A-D success")
    if rows[4].get("evidence_changed_route_or_admission") is not True:
        fail("choose_reasoning_route did not record an evidence-driven route change")
    if rows[7].get("completion_reported") is not True:
        fail("published path did not record operational completion")
    if rows[9].get("completion_reported") is not False:
        fail("invalid path recorded completion")
    if rows[10].get("completion_reported") is not False:
        fail("incomplete path recorded completion")
    if rows[11].get("completion_reported") is not False:
        fail("simulation path recorded completion")

    for token in (
        "qualification",
        ids["task_cid"],
        ids["obligation_id"],
        ids["pre_tree"],
        ids["post_tree"],
        pub["seal_cid"],
        "deterministic_only",
    ):
        if token not in study:
            fail(f"case study missing {token}")
    if "live A–D experiment" not in study and "live A-D experiment" not in study:
        fail("case study does not label the run as not a live A-D experiment")

    live_smoke()
    print("NS-013 end-to-end witness validation passed")


if __name__ == "__main__":
    main()
