#!/usr/bin/env python3
"""Correct reviewed paper validation argv through native Quack CAS updates.

The campaign coordinator must stop workers and own the maintenance window.
This script never starts/stops processes, opens a database file, requeues a
blocked task, or accepts a credential on the command line.
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("paper_validation_migration_materializer", ROOT / "scripts/materialize_paper_database.py")
MAT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MAT)
TOKEN_ENV = "IPFS_ACCELERATE_AGENT_QUACK_TOKEN"


class MigrationError(ValueError):
    def __init__(self, message, receipt=None):
        super().__init__(message)
        self.receipt = receipt


def plain(value):
    if isinstance(value, Mapping):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    return value


def digest(value):
    return hashlib.sha256(json.dumps(plain(value), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def preserved_contract(record):
    return {k: v for k, v in plain(record).items() if k not in {"revision", "updated_at", "validations"}}


def known_blocked_failure(record, *, already_correct):
    receipt = record["body"].get("completion_receipt")
    fixed = {"operation": "database_portal_attempt_failure", "reason": "validation_project_dependency_preflight_failed",
             "deferred": True, "attempt_consumed": False,
             "failure_kind": "lifecycle_setup", "repair_required": True, "task_cid": record["task_cid"]}
    if not isinstance(receipt, dict) or any(type(receipt.get(k)) is not type(v) or receipt.get(k) != v for k, v in fixed.items()):
        raise MigrationError(f"{record['task_alias']}: unrecognized blocked failure receipt")
    if not (receipt.get("provider_dispatched") is False or
            (receipt.get("provider_dispatched") is None and receipt.get("provider_call_allowed") is False)):
        raise MigrationError(f"{record['task_alias']}: blocked failure does not exclude provider dispatch")
    for key in ("claim_id", "attempt_id", "owner_session_id", "lease_id"):
        if not isinstance(receipt.get(key), str) or not receipt[key]:
            raise MigrationError(f"{record['task_alias']}: incomplete blocked failure binding")
    for key in ("fencing_token", "fence_epoch", "control_expected_revision", "control_result_revision"):
        if type(receipt.get(key)) is not int or receipt[key] < 1:
            raise MigrationError(f"{record['task_alias']}: invalid blocked failure revision/fence")
    result_revision = receipt["control_result_revision"]
    if result_revision != receipt["control_expected_revision"] + 1 or (
        result_revision != record["revision"] and not (already_correct and result_revision < record["revision"])
    ):
        raise MigrationError(f"{record['task_alias']}: stale blocked failure revision")
    return receipt


def plan_record(record, expected):
    alias = record["task_alias"]
    for key in ("task_cid", "goal_cid", "plan_cid", "objective_id", "ordinal", "priority"):
        if record[key] != expected[key]:
            raise MigrationError(f"{alias}: reviewed {key} binding differs")
    if set(record["dependencies"]) != set(expected["depends_on"]):
        raise MigrationError(f"{alias}: reviewed dependencies differ")
    if [v["path"] for v in record["outputs"]] != [v["path"] for v in expected["outputs"]]:
        raise MigrationError(f"{alias}: reviewed outputs differ")
    if [v["criterion"] for v in record["acceptance"]] != expected["acceptance_criteria"]:
        raise MigrationError(f"{alias}: reviewed acceptance differs")
    if len(record["validations"]) != 1 or len(expected["validation_commands"]) != 1:
        raise MigrationError(f"{alias}: validation count differs")
    planned = expected["validation_commands"][0]
    command, corrected = planned["source_command"], planned["argv"]
    validation = record["validations"][0]
    policy = validation["policy"]
    if record["body"].get("validation") != command or policy.get("source_command") != command:
        raise MigrationError(f"{alias}: validation source command differs")
    if any(key in policy for key in ("argv", "validation_commands", "command")):
        raise MigrationError(f"{alias}: validation policy shadows argv")
    old = ["bash", "-lc", command]
    if validation["argv"] not in (old, corrected):
        raise MigrationError(f"{alias}: unexpected validation argv")
    already_correct = validation["argv"] == corrected
    failure = None
    if record["status"] == "blocked":
        failure = known_blocked_failure(record, already_correct=already_correct)
    elif record["status"] != "ready":
        raise MigrationError(f"{alias}: task must be ready or an exact known blocked preflight failure")
    return {"record": record, "change": not already_correct,
            "validation": {"argv": corrected, **policy}, "failure_receipt": failure}


def migrate(paper, quack_endpoint, repo_root=ROOT, *, dry_run=False):
    repo_root = Path(repo_root).resolve()
    if not os.environ.get(TOKEN_ENV, "").strip():
        raise MigrationError("trusted Quack token environment is required")
    population, provenance = MAT.build_population(paper, repo_root)
    _, _, _, DatabaseTaskSource, _ = MAT._native(repo_root)
    from ipfs_accelerate_py.agent_supervisor.task_sources.duckdb_state import open_quack_transport_connection, is_quack_transport_target
    if not is_quack_transport_target(quack_endpoint):
        raise MigrationError("an explicit loopback Quack endpoint is required")
    expected = {r["task_id"]: r for r in population["taskboard"]}
    if len(expected) != 25:
        raise MigrationError("expected exactly 25 reviewed tasks")
    report = {"schema": "paper-validation-argv-migration/v1", "paper": paper,
              "started_at": datetime.now(timezone.utc).isoformat(), "dry_run": dry_run,
              "native_mutation_api": "IntentRepository.upsert_task(expected_revision)",
              "blocked_tasks_requeued": 0, "provider_invoked": False,
              "source_artifact_sha256": provenance["source_sha256"],
              "migration_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "materializer_sha256": hashlib.sha256(Path(MAT.__file__).read_bytes()).hexdigest(),
              "tasks": [], "changed": 0, "unchanged": 0, "success": False}
    remote = open_quack_transport_connection(quack_endpoint)
    try:
        # Native start publishes the durable row as 'starting' before setting
        # its public identity to ready; authenticated queries prove liveness.
        # Historical stopped generations remain in the same database.
        store_id = "vericodegen-2026-" + paper
        identity = remote.execute(
            "SELECT server_id, store_id, database_uuid, generation, process_birth_id, listen_uri, status "
            "FROM state_servers WHERE store_id = ? AND listen_uri = ? AND stopped_at IS NULL "
            "AND status IN ('starting', 'ready') "
            "AND generation = (SELECT max(generation) FROM state_servers WHERE store_id = ?)",
            [store_id, quack_endpoint, store_id],
        ).fetchall()
        if len(identity) != 1:
            raise MigrationError("Quack owner is not the expected paper store")
        report["owner"] = dict(zip(("server_id", "store_id", "database_uuid", "generation", "process_birth_id", "listen_uri", "durable_status"),
                                    [identity[0][i] for i in range(7)]))
        database_uuid = remote.execute("SELECT value FROM control_plane_metadata WHERE key = 'database_uuid'").fetchone()
        if database_uuid is None or database_uuid[0] != report["owner"]["database_uuid"]:
            raise MigrationError("Quack owner database identity differs from control metadata")
        report["owner_history_row_count"] = int(remote.execute("SELECT count(*) FROM state_servers WHERE store_id = ?", [store_id]).fetchone()[0])
        with DatabaseTaskSource(quack_endpoint, owner_id="paper-validation-migration:" + paper, install_schema=False) as source:
            records = [plain(r) for r in source.intent.list_tasks(limit=1000)]
            if len(records) != 25 or {r["task_alias"] for r in records} != set(expected):
                raise MigrationError("remote task population differs from reviewed paper")
            if any(r["status"] == "in_progress" for r in records):
                raise MigrationError("refusing migration while any task is in_progress")
            report["before_snapshot_sha256"] = digest(records)
            report["before_event_watermark"] = int(remote.execute("SELECT coalesce(max(global_sequence),0) FROM domain_events").fetchone()[0])
            plans = [plan_record(record, expected[record["task_alias"]]) for record in records]
            # All records pass admission before the first native transaction.
            for plan in plans:
                record = plan["record"]
                item = {"task_id": record["task_alias"], "task_cid": record["task_cid"], "status": record["status"],
                        "before_revision": record["revision"], "before_sha256": digest(record),
                        "preserved_contract_sha256": digest(preserved_contract(record)),
                        "before_validations_sha256": digest(record["validations"]),
                        "planned_action": "update_argv" if plan["change"] else "already_correct",
                        "failure_receipt": plan["failure_receipt"]}
                report["tasks"].append(item)
                if plan["change"] and not dry_run:
                    update = {key: record[key] for key in ("task_cid", "task_alias", "goal_cid", "ordinal", "status",
                                                             "priority", "plan_cid", "objective_id", "body", "identity")}
                    receipt = source.intent.upsert_task(**update, expected_revision=record["revision"], validations=[plan["validation"]])
                    item["event"] = plain(receipt.to_dict())
                    report["changed"] += 1
                elif not plan["change"]:
                    report["unchanged"] += 1
                observed = plain(source.intent.get_task(record["task_cid"]))
                if preserved_contract(observed) != preserved_contract(record):
                    raise MigrationError("preserved task contract changed unexpectedly")
                expected_revision = record["revision"] + int(plan["change"] and not dry_run)
                if observed["revision"] != expected_revision:
                    raise MigrationError("task revision changed concurrently")
                expected_validations = plain(record["validations"])
                if not dry_run:
                    expected_validations[0]["argv"] = plan["validation"]["argv"]
                if observed["validations"] != expected_validations:
                    raise MigrationError("validation argv or preserved policy differs after migration")
                item.update(after_revision=observed["revision"], after_sha256=digest(observed),
                            after_validations_sha256=digest(observed["validations"]))
            after = [plain(r) for r in source.intent.list_tasks(limit=1000)]
            report["after_snapshot_sha256"] = digest(after)
            report["after_event_watermark"] = int(remote.execute("SELECT coalesce(max(global_sequence),0) FROM domain_events").fetchone()[0])
            if report["after_event_watermark"] - report["before_event_watermark"] != report["changed"]:
                raise MigrationError("event watermark changed outside the expected migration updates")
            report["success"] = True
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        report["reason"] = str(exc) if isinstance(exc, MigrationError) else "native migration failed; inspect the partial receipt"
        raise MigrationError(report["reason"], report) from exc
    finally:
        remote.close()
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
    if os.environ[TOKEN_ENV] in json.dumps(report):
        raise MigrationError("refusing to emit a credential-containing receipt")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper", choices=MAT.PAPERS, required=True)
    parser.add_argument("--quack-endpoint", required=True)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        report = migrate(args.paper, args.quack_endpoint, args.repo_root, dry_run=args.dry_run)
    except Exception as exc:
        report = (exc.receipt if isinstance(exc, MigrationError) else None) or {
            "schema": "paper-validation-argv-migration/v1", "success": False, "error_type": type(exc).__name__,
            "reason": str(exc) if isinstance(exc, MigrationError) else "migration setup failed"}
        if os.environ.get(TOKEN_ENV, "") and os.environ[TOKEN_ENV] in json.dumps(report):
            report = {"success": False, "error_type": "ReceiptCredentialRejected"}
        print(json.dumps(report, indent=2))
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
