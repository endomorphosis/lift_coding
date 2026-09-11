"""Publish verified source checkpoints and repair exact undispatched route failures.

Exclusive maintenance of this campaign only. Failed attempt history remains
failed; source checkpoints are separately validated agent-assisted work.
"""
from collections import Counter
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import paper_supervisor_campaign as C
import materialize_paper_database as M
import repair_paper_launch_validation as R

AUDIT = Path(__file__).with_name("third_launch.json")
AUDIT_SHA = "75bf1e65adc9b2c53f39b8b1758a6a35e97c831ed6aa0c9e41dcc3750fca776c"
STATE = R.STATE


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def lane_work(paper, audit):
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import DatabaseImplementationDaemon
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.database_portal_bridge import DatabasePortalBridgeError
    lane, repo = STATE / paper, ROOT / ".worktrees" / ("vericodegen-" + paper + "-2026")
    expected = {t["task_alias"]: t for t in audit["control.duckdb"]["tasks"]}
    prefix = {"autoformalization": "AF", "law_to_action": "LA", "neurosymbolic_supervision": "NS"}[paper]
    first = prefix + "-001"
    report_path = lane / "source-checkpoint-maintenance.json"
    R.require(not report_path.exists(), "this one-shot lane maintenance already has a report; inspect before resuming")
    report = {"schema": "paper-source-checkpoint-maintenance/v1", "paper": paper,
              "started_at": C.now(), "audit_sha256": AUDIT_SHA,
              "provider_invoked": False, "mutations": [], "success": False}
    C.write(report_path, report)
    owner_dir = lane / "source-checkpoint-maintenance-owner"
    owner_dir.mkdir(mode=0o700, exist_ok=True)
    ready_path = owner_dir / "paper-owner.ready.json"
    C.prepare_owner_start(ready_path, paper)
    process, record = C.launch([str(C.PYTHON), str(ROOT / "scripts/paper_state_owner.py"),
        "--database", str(lane / "control.duckdb"), "--state-dir", str(owner_dir),
        "--store-id", "vericodegen-2026-" + paper,
        "--secret-handle", "handle:vericodegen-2026:" + paper + ":source-checkpoint-maintenance"],
        ROOT, C.environment(ROOT), owner_dir / "owner.log")
    report["maintenance_owner_process"] = record
    C.write(report_path, report)
    try:
        ready = C.wait_owner_ready(process, record, ready_path, paper=paper, database=lane / "control.duckdb")
        vault = owner_dir / (ready["endpoint_secret_handle"].replace(":", "_").replace("/", "_") + ".quack-token")
        R.require(vault.stat().st_mode & 0o077 == 0, "credential is not private")
        os.environ["IPFS_ACCELERATE_AGENT_QUACK_TOKEN"] = vault.read_text().strip()
        os.environ["IPFS_ACCELERATE_AGENT_STATE_SCHEMA_REVISION"] = "1"
        report["owner_identity"] = ready["identity"]
        owner = audit["control.execution.duckdb"]["database_task_attempts"][0]["owner_session_id"]
        with DatabaseImplementationDaemon(database_path=lane / "control.duckdb", quack_uri=ready["quack_endpoint"], owner_session_id=owner, task_prefix=prefix + "-") as daemon:
            source = daemon.task_source
            records = source.intent.list_tasks(limit=1000)
            R.require(len(records) == 25, "unexpected task population")
            for task in records:
                original = expected[task["task_alias"]]
                for key in ("task_cid", "status", "revision"):
                    R.require(task[key] == original[key], "task changed since audited stop")
            # AF-003 was interrupted before even starting a provider. Record
            # that maintenance finding without claiming an observed ImportError.
            for attempt in daemon.list_running_attempts():
                R.require(paper == "autoformalization" and attempt.task_alias == "AF-003", "unrecognized running attempt")
                original = next(a for a in audit["control.execution.duckdb"]["database_task_attempts"] if a["attempt_id"] == attempt.attempt_id)
                R.require(attempt.committed_phase == "context" and attempt.revision == original["revision"], "interrupted attempt advanced")
                projections = [p for p in audit["portal_projections"] if any(e.get("task_id") == "AF-003" for e in p["events"])]
                R.require(len(projections) == 1 and [e["type"] for e in projections[0]["events"]] == ["task_selected"], "AF-003 setup evidence differs")
                projection = Path(projections[0]["path"])
                R.require(R.sha(projection) == projections[0]["sha256"], "AF-003 event evidence changed")
                state = C.read(projection.with_name("portal-task-state.json"))
                R.require(state.get("implementation_in_progress") is False and not state.get("active_log_path") and not state.get("last_implementation_log_path"), "AF-003 provider progress exists")
                # Context compilation happens before dispatch and writes JSON
                # alongside implementation logs. Preserve and authenticate it.
                context_files = list(projection.parent.glob("implementation-logs/*"))
                allowed_context_names = {"af-003-attempt-1-context-receipt.json", "af-003-base-context-receipt.json", "af-003-base-context-capsule.json"}
                for path in context_files:
                    R.require(path.is_file() and path.name in allowed_context_names, "AF-003 implementation output exists")
                    backup_path = Path(C.read(AUDIT)["backup_root"]) / paper / "state" / path.relative_to(lane / "state")
                    R.require(R.sha(path) == R.sha(backup_path), "AF-003 context changed since stopped backup")
                report["retained_pre_dispatch_context"] = [{"path": str(p), "sha256": R.sha(p)} for p in context_files]
                R.require(daemon.provider_invocation_recorded(attempt.attempt_id, idempotency_key="provider:" + attempt.attempt_id) is None, "AF-003 provider receipt exists")
                retired = daemon._block_portal_failed_attempt(attempt, DatabasePortalBridgeError(
                    "campaign_stopped_during_pre_provider_setup", result={"implementation": {
                        "failure_kind": "lifecycle_setup", "attempt_consumed": False,
                        "provider_dispatched": False, "provider_call_allowed": False,
                        "infrastructure_failure": True}}))
                report["mutations"].append({"kind": "record_interrupted_setup", "attempt": retired.to_dict(),
                    "evidence_basis": "stopped process tree, context-only durable phase, only task_selected event, no implementation log/provider receipt", "native_import_failure_observed_for_this_attempt": False})
                C.write(report_path, report)
            R.require(not daemon.list_running_attempts(), "running attempt remains")
            # Authenticate every blocked status against its original exact
            # failed claim and the retained native no-dispatch failure event.
            blocked = [t for t in source.intent.list_tasks(limit=1000) if t["status"] == "blocked"]
            for task in blocked:
                receipt = task["body"].get("completion_receipt", {})
                R.require(receipt.get("operation") == "database_portal_attempt_failure" and receipt.get("provider_dispatched") is False,
                          "blocked task is not an exact undispatched Portal failure")
                R.require(receipt.get("control_result_revision") == task["revision"], "blocked failure revision differs")
                attempt = daemon.get_attempt(receipt["attempt_id"])
                R.require(attempt and attempt.status in {"failed", "blocked"}, "failure attempt is not retired")
                for key in ("claim_id", "attempt_id", "attempt_number", "task_cid", "owner_session_id", "fencing_token", "fence_epoch", "lease_id"):
                    R.require(receipt.get(key) == getattr(attempt, key), "failure attempt binding differs")
                claim = daemon.coordinator.get_task_claim(attempt.claim_id)
                R.require(str(getattr(claim.state, "value", claim.state)) == "released", "failed lease is not released")
                if task["task_alias"] != "AF-003":
                    events = [e for e in audit["portal_failures"] if e.get("task_id") == task["task_alias"]]
                    R.require(len(events) == 1 and events[0].get("provider_dispatched") is False, "no exact provider failure event")
                    error = events[0].get("exception_result", {})
                    R.require(error.get("exception_type") == "ImportError" and "ROUTER_OWNED_COMPATIBILITY_LEGACY_AUTO" in error.get("message", ""), "different route failure")
                if task["task_alias"] == first:
                    receipt_rel = Path("papers/completion") / paper / "receipts" / (first + ".json")
                    argv = ["python3", "scripts/paper_supervisors.py", "verify-task", "--paper", paper, "--task", first]
                    R.require(len(task["validations"]) == 1 and task["validations"][0]["argv"] == argv, "native validation command differs")
                    logfile = owner_dir / (first + "-verify-task.json")
                    with logfile.open("w") as log:
                        result = subprocess.run(argv, cwd=repo, env=C.environment(repo), stdout=log, stderr=subprocess.STDOUT)
                    R.require(result.returncode == 0, "source checkpoint validation failed")
                    paper_receipt = C.read(repo / receipt_rel)
                    R.require([a["criterion"] for a in task["acceptance"]] == [a["criterion"] for a in paper_receipt["criteria"]], "native criteria differ from source receipt")
                    evidence = "sha256:" + R.sha(repo / receipt_rel)
                    validation = source.record_validation_result(task_cid=task["task_cid"], outcome="passed", evidence_digest=evidence, argv=argv,
                        body={"execution_kind": "agent_assisted_checkpoint_validation", "receipt_path": str(receipt_rel),
                              "exit_code": 0, "validation_log": str(logfile), "validation_log_sha256": R.sha(logfile),
                              "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(),
                              "provider_attempt_success_claimed": False, "acceptance_criteria": paper_receipt["criteria"]})
                    completion = {"operation": "paper_agent_assisted_checkpoint_complete", "task_id": first,
                                  "paper_receipt": str(receipt_rel), "evidence_digest": evidence,
                                  "prior_failure_receipt_sha256": digest(receipt), "prior_failure_attempt_id": attempt.attempt_id,
                                  "validation_event": validation.to_dict(), "audit_sha256": AUDIT_SHA,
                                  "provider_invoked": False, "benchmark_result_claimed": False,
                                  "completed_at": C.now(), "scope": "source recovery and explicitly reconciled reconstruction only"}
                    changed = source.compare_and_set_status(task["task_cid"], task["revision"], "completed", receipt=completion, evidence_digests=[evidence])
                    report["mutations"].append({"kind": "verified_source_checkpoint", "task_id": first, "status": changed.task.status,
                                                "revision": changed.revision, "completion": completion})
                else:
                    repair = {"operation": "paper_explicit_provider_pin_repair", "audit_sha256": AUDIT_SHA,
                              "prior_failure_receipt_sha256": digest(receipt), "prior_attempt_id": attempt.attempt_id,
                              "provider": "grok", "configuration_sha256": R.sha(ROOT / "scripts/paper_supervisor_campaign.py"),
                              "reason": "supported_explicit_grok_route_qualified_without_provider_call", "requeued_at": C.now(),
                              "old_attempt_history_preserved": True, "provider_invoked": False}
                    changed = source.compare_and_set_status(task["task_cid"], task["revision"], "ready", receipt=repair)
                    report["mutations"].append({"kind": "requeue_after_route_repair", "task_id": task["task_alias"], "revision": changed.revision, "receipt": repair})
                R.require(changed.changed, "expected native CAS did not change status")
                C.write(report_path, report)
            final = source.intent.list_tasks(limit=1000)
            R.require(Counter(t["status"] for t in final) == {"completed": 1, "ready": 24}, "unexpected final task counts")
            report["final_tasks"] = [{k: t[k] for k in ("task_alias", "task_cid", "status", "revision")} for t in final]
            report["next_eligible_tasks"] = [t.task_alias for t in source.ready_tasks(limit=100).tasks]
        report.update(success=True, finished_at=C.now())
        C.write(report_path, report)
        print(paper, "source checkpoint completed; 24 tasks remain open", flush=True)
        return report
    finally:
        os.environ.pop("IPFS_ACCELERATE_AGENT_QUACK_TOKEN", None)
        report["cleanup_errors"] = C.cleanup_children([("owner", process, record)])
        C.write(report_path, report)
        R.require(not report["cleanup_errors"], "maintenance owner cleanup failed")


def main():
    M._native(ROOT)
    R.require(R.sha(AUDIT) == AUDIT_SHA, "third-launch audit changed")
    audit = C.read(AUDIT)
    with (STATE / "campaign.lock").open("a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        campaign = C.read(STATE / "campaign.json")
        R.require(campaign == audit["campaign"] and campaign.get("stopped_at") and not campaign.get("cleanup_errors"), "campaign changed since stopped audit")
        R.require(not C.alive(campaign["controller"]), "controller is live")
        for lane in campaign["lanes"].values():
            R.require(not C.alive(lane["owner"]) and not C.alive(lane["supervisor"]), "campaign child is live")
        resume_path = Path(__file__).with_name("third_launch_maintenance_preflight_resume.json")
        resumed_files = C.read(resume_path)["current_files"] if resume_path.exists() else audit["files"]
        for original, entry in audit["files"].items():
            R.require(R.sha(Path(entry["backup"])) == entry["sha256"], "original backup changed")
        for original, entry in resumed_files.items():
            R.require(R.sha(Path(original)) == entry["sha256"] and R.sha(Path(entry["backup"])) == entry["sha256"], "saved database/backup changed")
        for paper in C.PAPERS:
            repo = ROOT / ".worktrees" / ("vericodegen-" + paper + "-2026")
            R.require(not subprocess.check_output(["git", "status", "--porcelain"], cwd=repo, text=True).strip(), "source checkout is dirty")
            prefix = {"autoformalization": "AF", "law_to_action": "LA", "neurosymbolic_supervision": "NS"}[paper]
            relative = Path("papers/completion") / paper / "receipts" / (prefix + "-001.json")
            R.require(R.sha(ROOT / relative) == R.sha(repo / relative), "source receipt is not committed in lane")
        reports = [lane_work(p, audit["lanes"][p]) for p in C.PAPERS]
        C.write(Path(__file__).with_name("third_launch_settlement.json"), {"success": all(r["success"] for r in reports), "lanes": reports})


if __name__ == "__main__":
    main()
