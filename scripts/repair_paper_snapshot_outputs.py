#!/usr/bin/env python3
"""Admit each ready paper task's already-required receipt snapshot directory.

Uses the live paper owner's separately authenticated maintenance API. Active, blocked, and completed
tasks are untouched. No task is requeued, completed, or given provider credit.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("snapshot_output_migration_common", ROOT / "scripts/migrate_paper_validation_argv.py")
COMMON = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COMMON)
plain, digest = COMMON.plain, COMMON.digest


class SnapshotRepairError(ValueError):
    def __init__(self, message, receipt=None):
        super().__init__(message)
        self.receipt = receipt


def preserved(record):
    return {key: value for key, value in plain(record).items()
            if key not in {"outputs", "revision", "updated_at"}}


def plan_record(paper, record, seed):
    alias = seed["id"]
    folder = f"papers/completion/{paper}"
    snapshot = f"{folder}/receipts/snapshots/{alias}/"
    expected = list(dict.fromkeys([*seed["deliverables"], f"{folder}/receipts/{alias}.json"]))
    body = record["body"]
    if (record["task_alias"] != alias or record["identity"].get("task_alias") != alias
            or record["identity"].get("task_cid") != record["task_cid"]
            or body.get("board_namespace") != "vericodegen-2026-" + paper
            or body.get("goal id") != seed["subgoal_id"]
            or body.get("receipt") != f"{folder}/receipts/{alias}.json"):
        raise SnapshotRepairError(f"{alias}: reviewed paper identity differs")
    if [item["criterion"] for item in record["acceptance"]] != seed["acceptance_criteria"]:
        raise SnapshotRepairError(f"{alias}: reviewed acceptance differs")
    predicted = [value.strip() for value in body.get("predicted files", "").split(",") if value.strip()]
    if predicted != [*expected, snapshot]:
        raise SnapshotRepairError(f"{alias}: original bounded snapshot prediction differs")
    observed = [str(Path(item["path"])) for item in record["outputs"]]
    expected = [str(Path(path)) for path in expected]
    normalized_snapshot = str(Path(snapshot))
    if observed not in (expected, [*expected, normalized_snapshot]):
        raise SnapshotRepairError(f"{alias}: current outputs differ from reviewed task")
    effects = [plain(item["effect"]) for item in record["outputs"]]
    if any(str(Path(effect.get("path", ""))) != path for effect, path in zip(effects, observed)):
        raise SnapshotRepairError(f"{alias}: output effect/path identity differs")
    if observed == [*expected, normalized_snapshot]:
        if effects[-1] != {"path": snapshot, "kind": "directory"}:
            raise SnapshotRepairError(f"{alias}: snapshot directory effect differs")
        return {"action": "already_correct", "outputs": effects}
    if record["status"] != "ready":
        return {"action": "skip_" + record["status"], "outputs": effects}
    return {"action": "add_snapshot_directory",
            "outputs": [*effects, {"path": snapshot, "kind": "directory"}]}


def repair(paper, endpoint, repo_root=ROOT, *, dry_run=True, owner_state_dir=None):
    repo_root = Path(repo_root).resolve()
    if paper not in COMMON.MAT.PAPERS:
        raise SnapshotRepairError("unknown paper")
    token = os.environ.get(COMMON.TOKEN_ENV, "").strip()
    if not token:
        raise SnapshotRepairError("trusted Quack token environment is required")
    manifest_path = repo_root / f"papers/completion/{paper}/tasks.json"
    seeds = {task["id"]: task for task in json.loads(manifest_path.read_text())["tasks"]}
    expected_count = {"autoformalization": 25, "law_to_action": 32, "neurosymbolic_supervision": 25, "lean_refactor_arena": 18}[paper]
    if len(seeds) != expected_count:
        raise SnapshotRepairError("reviewed task count differs")
    _, _, _, Source, _ = COMMON.MAT._native(repo_root)
    from ipfs_accelerate_py.agent_supervisor.task_sources.duckdb_state import open_quack_transport_connection, is_quack_transport_target
    if not is_quack_transport_target(endpoint):
        raise SnapshotRepairError("an explicit loopback Quack endpoint is required")
    report = {"schema": "paper-snapshot-output-repair/v1", "paper": paper,
              "started_at": datetime.now(timezone.utc).isoformat(), "dry_run": dry_run,
              "native_mutation_api": "paper-contract-maintenance/v1:snapshot_directory",
              "tasks_requeued": 0, "tasks_completed": 0, "provider_invoked": False,
              "changed": 0, "tasks": [], "success": False}
    remote = open_quack_transport_connection(endpoint)
    try:
        store_id = "vericodegen-2026-" + paper
        latest_generation = remote.execute("SELECT max(generation) FROM state_servers WHERE store_id = ?", [store_id]).fetchone()[0]
        identity = remote.execute(
            "SELECT server_id, database_uuid, generation, process_birth_id FROM state_servers "
            "WHERE store_id = ? AND listen_uri = ? AND stopped_at IS NULL "
            "AND status IN ('starting', 'ready') "
            "AND generation = ?",
            [store_id, endpoint, latest_generation]).fetchall()
        uuid = remote.execute("SELECT value FROM control_plane_metadata WHERE key = 'database_uuid'").fetchone()
        if len(identity) != 1 or uuid is None or identity[0][1] != uuid[0]:
            raise SnapshotRepairError("Quack owner is not the expected paper store")
        owner_birth = identity[0][3]
        report["owner"] = {"store_id": store_id, "server_id": identity[0][0],
                           "database_uuid": identity[0][1], "generation": identity[0][2]}
        with Source(endpoint, owner_id="paper-snapshot-output-repair:" + paper, install_schema=False) as source:
            records = [plain(record) for record in source.intent.list_tasks(limit=1000)]
            if len(records) != expected_count or {record["task_alias"] for record in records} != set(seeds):
                raise SnapshotRepairError("remote task population differs from reviewed paper")
            # Validate all task contracts before the first CAS. The controller
            # may keep running; a concurrent claim makes the exact CAS fail.
            plans = [(record, plan_record(paper, record, seeds[record["task_alias"]])) for record in records]
            report["before_snapshot_sha256"] = digest(records)
            for record, plan in plans:
                item = {"task_id": record["task_alias"], "task_cid": record["task_cid"],
                        "status": record["status"], "action": plan["action"],
                        "before_revision": record["revision"], "before_sha256": digest(record),
                        "preserved_contract_sha256": digest(preserved(record)),
                        "outputs_before": record["outputs"], "outputs_planned": plan["outputs"]}
                report["tasks"].append(item)
                if plan["action"] != "add_snapshot_directory" or dry_run:
                    continue
                event = COMMON.maintenance_submit("snapshot_directory", record, {**report["owner"], "listen_uri": endpoint, "process_birth_id": owner_birth}, owner_state_dir)
                item["event"] = event["event"]
                report["changed"] += 1
                observed = plain(source.intent.get_task(record["task_cid"]))
                if (preserved(observed) != preserved(record)
                        or observed["revision"] != record["revision"] + 1
                        or [output["effect"] for output in observed["outputs"]] != plan["outputs"]):
                    raise SnapshotRepairError("concurrent task mutation or unexpected output repair result")
                item.update(after_revision=observed["revision"], after_sha256=digest(observed))
            report["success"] = True
    except Exception as exc:
        report.update(error_type=type(exc).__name__, reason=str(exc) if isinstance(exc, SnapshotRepairError)
                      else "native CAS repair failed; inspect partial receipt before retrying")
        raise SnapshotRepairError(report["reason"], report) from exc
    finally:
        remote.close()
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
    if token in json.dumps(report):
        raise SnapshotRepairError("refusing to emit a credential-containing receipt")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper", choices=COMMON.MAT.PAPERS, required=True)
    parser.add_argument("--quack-endpoint", required=True)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--apply", action="store_true", help="Apply only admitted ready-task changes; default is read-only")
    parser.add_argument("--owner-state-dir", type=Path, help="Live owner directory containing the separate maintenance credential")
    args = parser.parse_args()
    try:
        result = repair(args.paper, args.quack_endpoint, args.repo_root, dry_run=not args.apply, owner_state_dir=args.owner_state_dir)
    except SnapshotRepairError as exc:
        result = exc.receipt or {"success": False, "reason": str(exc)}
    token = os.environ.get(COMMON.TOKEN_ENV, "").strip()
    if token and token in json.dumps(result):
        result = {"success": False, "reason": "receipt credential rejected"}
    print(json.dumps(result, indent=2))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
