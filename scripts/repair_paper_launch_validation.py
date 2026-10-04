#!/usr/bin/env python3
"""Apply the audited second-launch repair during an exclusive campaign stop.

This one-campaign maintenance procedure preserves native failures and migrates
validation argv before requeuing exactly the three undispatched setup attempts.
It never runs providers or imports a replacement task database.
"""
from __future__ import annotations

from collections import Counter
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import sys

import paper_supervisor_campaign as C
import migrate_paper_validation_argv as M

ROOT = C.ROOT
STATE = Path.home() / ".local/state/ipfs_accelerate_py/vericodegen-2026"
AUDIT = ROOT / "papers/completion/runtime_bootstrap/second_launch.json"
AUDIT_SHA = "f0f9f70a6f2bc6f8e968bd18be1fcf46499e2208d846ac9fb0ef5ce606d8358a"
BACKUP = STATE / "backups/20260911T154237Z-validation-argv/receipt.json"


def sha(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def repair_lane(paper, anchor, backup):
    lane = STATE / paper
    receipt_path = lane / "validation-argv-repair.json"
    prior = C.read(receipt_path) if receipt_path.exists() else None
    if prior and prior.get("success"):
        print(json.dumps({"paper": paper, "status": "already_repaired", "receipt": str(receipt_path)}), flush=True)
        return prior
    if not prior:
        for original, item in backup["files"].items():
            if Path(original).parent == lane:
                require(sha(original) == item["sha256"], "saved database changed since stopped backup")
    failure_file = Path(anchor["failure_event_file"]["path"])
    require(sha(failure_file) == anchor["failure_event_file"]["sha256"], "failure evidence changed")
    observed = json.loads(failure_file.read_text().splitlines()[anchor["implementation_finished_event_line"] - 1])
    require(observed["event_id"] == anchor["implementation_finished_event_id"], "wrong failure event")
    require(all(observed.get(k) is False for k in ("provider_dispatched", "provider_call_allowed", "attempt_consumed")), "failure does not exclude dispatch")
    require(observed["reason"] == "validation_project_dependency_preflight_failed", "unexpected failure")
    report = prior or {"schema": "paper-second-launch-validation-repair/v1", "paper": paper,
                      "started_at": C.now(), "audit_sha256": AUDIT_SHA, "backup_receipt_sha256": sha(BACKUP),
                      "failure_event_file": anchor["failure_event_file"], "provider_invoked": False,
                      "success": False}
    C.write(receipt_path, report)
    owner_dir = lane / "validation-argv-maintenance-owner"
    owner_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    ready_path = owner_dir / "paper-owner.ready.json"
    C.prepare_owner_start(ready_path, paper)
    process, record = C.launch([str(C.PYTHON), str(ROOT / "scripts/paper_state_owner.py"),
        "--database", str(lane / "control.duckdb"), "--state-dir", str(owner_dir),
        "--store-id", "vericodegen-2026-" + paper,
        "--secret-handle", "handle:vericodegen-2026:" + paper + ":validation-argv-maintenance"],
        ROOT, C.environment(ROOT), owner_dir / "owner.log")
    report["maintenance_owner_process"] = record
    C.write(receipt_path, report)
    try:
        ready = C.wait_owner_ready(process, record, ready_path, paper=paper, database=lane / "control.duckdb")
        vault = owner_dir / (ready["endpoint_secret_handle"].replace(":", "_").replace("/", "_") + ".quack-token")
        require(vault.stat().st_mode & 0o077 == 0, "credential permissions are not private")
        os.environ[M.TOKEN_ENV] = vault.read_text().strip()
        os.environ["IPFS_ACCELERATE_AGENT_STATE_SCHEMA_REVISION"] = str(ready["schema_revision"])
        report["maintenance_owner_identity"] = ready["identity"]
        from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import DatabaseImplementationDaemon
        from ipfs_accelerate_py.agent_supervisor.todo_daemon.database_portal_bridge import DatabasePortalBridgeError
        kwargs = dict(database_path=lane / "control.duckdb", quack_uri=ready["quack_endpoint"],
                      owner_session_id=anchor["execution_attempt"]["owner_session_id"], authority_mode="quack",
                      task_prefix=anchor["task_alias"].split("-")[0] + "-")
        with DatabaseImplementationDaemon(**kwargs) as daemon:
            attempt = daemon.get_attempt(anchor["execution_attempt"]["attempt_id"])
            require(attempt is not None, "original attempt missing")
            for key in ("attempt_id", "claim_id", "task_cid", "task_alias", "attempt_number", "owner_session_id", "fencing_token", "fence_epoch", "lease_id"):
                require(getattr(attempt, key) == anchor["execution_attempt"][key], "original attempt identity changed: " + key)
            require(daemon.provider_invocation_recorded(attempt.attempt_id, idempotency_key="provider:" + attempt.attempt_id) is None, "provider receipt exists")
            task = daemon.task_source.get(attempt.task_cid)
            if task.status == "in_progress":
                require(task.revision == anchor["expected_revision"], "original task revision changed")
                require(task.body.get("completion_receipt") == anchor["exact_database_claim_receipt"], "original claim receipt changed")
                detail = {k: observed[k] for k in ("failure_kind", "attempt_consumed", "provider_dispatched", "provider_call_allowed", "infrastructure_failure")}
                detail["backoff_seconds"] = observed.get("backoff_seconds", observed["exception_result"].get("backoff_seconds"))
                attempt = daemon._block_portal_failed_attempt(attempt, DatabasePortalBridgeError(observed["reason"], result={"implementation": detail}))
            elif task.status == "blocked" and attempt.status == "running":
                daemon.reconcile_portal_failure_attempts()
                attempt = daemon.get_attempt(attempt.attempt_id)
            require(attempt.status == "blocked", "attempt was not retired as a nonconsuming setup failure")
            require(not daemon.list_running_attempts(), "another attempt is running")
            task = daemon.task_source.get(attempt.task_cid)
            if task.status == "ready":
                # Only a crash after this procedure's final CAS is resumable.
                current_receipt = task.body.get("completion_receipt", {})
                require(current_receipt.get("operation") == "paper_validation_argv_repair" and current_receipt.get("audit_sha256") == AUDIT_SHA,
                        "unrecognized ready task on maintenance resume")
                require(report.get("migration", {}).get("success") is True, "ready repair has no durable migration receipt")
                report["requeue"] = dict(current_receipt)
            else:
                require(task.status == "blocked", "failed task changed status")
                report["failure_receipt"] = M.plain(task.body["completion_receipt"])
            report["retired_attempt"] = attempt.to_dict()
            claim = daemon.coordinator.get_task_claim(attempt.claim_id)
            require(str(getattr(claim.state, "value", claim.state)) == "released", "exact lease was not released")
            report["released_claim"] = claim.to_dict()
        C.write(receipt_path, report)
        if "requeue" not in report:
            report["migration_dry_run"] = M.migrate(paper, ready["quack_endpoint"], ROOT, dry_run=True)
            C.write(receipt_path, report)
            report["migration"] = M.migrate(paper, ready["quack_endpoint"], ROOT)
            C.write(receipt_path, report)
            with DatabaseImplementationDaemon(**kwargs) as daemon:
                task = daemon.task_source.get(anchor["authoritative_task_cid"])
                require(task.status == "blocked" and task.body.get("completion_receipt") == report["failure_receipt"], "failure changed before requeue")
                require(not daemon.list_running_attempts(), "running attempt before requeue")
                migrated = next(t for t in report["migration"]["tasks"] if t["task_cid"] == task.task_cid)
                require(task.revision == migrated["after_revision"], "migration revision changed before requeue")
                requeue = {"operation": "paper_validation_argv_repair", "audit_sha256": AUDIT_SHA,
                           "migration_sha256": M.digest(report["migration"]),
                           "failure_receipt_sha256": M.digest(report["failure_receipt"]),
                           "original_attempt_id": anchor["execution_attempt"]["attempt_id"],
                           "control_expected_revision": task.revision, "control_result_revision": task.revision + 1,
                           "reason": "reviewed_direct_validation_argv_installed", "provider_invoked": False,
                           "requeued_at": C.now()}
                result = daemon.task_source.compare_and_set_status(task.task_cid, task.revision, "ready", receipt=requeue)
                require(result.changed and result.task.status == "ready", "requeue CAS did not apply")
                report["requeue"] = requeue
                C.write(receipt_path, report)
        with DatabaseImplementationDaemon(**kwargs) as daemon:
            records = [M.plain(t) for t in daemon.task_source.intent.list_tasks(limit=1000)]
            require(len(records) == 25 and Counter(t["status"] for t in records) == {"ready": 25}, "unexpected final statuses")
            require(not daemon.list_running_attempts(), "running attempt at maintenance completion")
            population, _ = M.MAT.build_population(paper, ROOT)
            expected = {t["task_id"]: t for t in population["taskboard"]}
            require({t["task_alias"] for t in records} == set(expected), "final task population differs")
            for task in records:
                M.plan_record(task, expected[task["task_alias"]])
                require(task["validations"][0]["argv"] == expected[task["task_alias"]]["validation_commands"][0]["argv"], "final argv differs")
            report["final_tasks"] = [{k: t[k] for k in ("task_alias", "task_cid", "status", "revision")} for t in records]
            report["final_snapshot_sha256"] = M.digest(records)
        report.update(success=True, finished_at=C.now())
        C.write(receipt_path, report)
        print(json.dumps({"paper": paper, "success": True, "tasks_ready": 25, "receipt": str(receipt_path)}), flush=True)
        return report
    finally:
        os.environ.pop(M.TOKEN_ENV, None)
        errors = C.cleanup_children([("owner", process, record)])
        report["cleanup_errors"] = errors
        report["maintenance_owner_stopped_at"] = C.now()
        C.write(receipt_path, report)
        require(not errors, "maintenance owner cleanup failed")


def main():
    # Import canonical repaired native modules, never an older lane snapshot.
    M.MAT._native(ROOT)
    require(sha(AUDIT) == AUDIT_SHA, "audited second launch changed")
    audit, backup = C.read(AUDIT), C.read(BACKUP)
    for item in backup["files"].values():
        require(sha(item["backup"]) == item["sha256"], "backup file changed")
    with (STATE / "campaign.lock").open("a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        campaign = C.read(STATE / "campaign.json")
        require(campaign.get("stopped_at") and not campaign.get("cleanup_errors"), "campaign has no clean stop")
        require(not C.alive(campaign.get("controller")), "campaign controller is running")
        for lane in campaign["lanes"].values():
            require(not C.alive(lane.get("owner")) and not C.alive(lane.get("supervisor")), "campaign child is running")
        reports = [repair_lane(p, audit["exact_maintenance_anchors"][p], backup) for p in C.PAPERS]
        C.write(ROOT / "papers/completion/runtime_bootstrap/validation_argv_live_repair.json",
                {"schema": "paper-validation-live-repair/v1", "finished_at": C.now(), "lanes": reports,
                 "success": all(r["success"] for r in reports), "provider_invoked": False})


if __name__ == "__main__":
    main()
