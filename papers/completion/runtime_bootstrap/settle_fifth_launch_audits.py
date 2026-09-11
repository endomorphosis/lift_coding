"""Publish fresh paper evidence while preserving original native attempt history.

Single stopped-campaign maintenance for LA-002/003 or AF-003. Every completion
requires the committed receipt, exact native criteria, and real verify-task CLI.
"""
from __future__ import annotations
import argparse
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
import repair_paper_snapshot_outputs as S

STATE = Path.home() / ".local/state/ipfs_accelerate_py/vericodegen-2026"
AUDIT = Path(__file__).with_name("fifth_launch_stopped.json")
AUDIT_SHA = "7cd570ee159e72fb72cf17ffe5b212eb2504c1ad746c9f8a61c7a56720bdbef4"
LA_ATTEMPT = "attempt:5f135e18aeaf4a9fa3b4b6f11ebb72a6"


def require(value, message):
    if not value:
        raise RuntimeError(message)


def sha(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def git(repo, *args):
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def all_running_attempts(daemon):
    return daemon._require_connection().execute(
        "SELECT attempt_id FROM database_task_attempts WHERE status = 'running'"
    ).fetchall()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper", choices=("law_to_action", "autoformalization"), required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--receipt-sha256", action="append", required=True, help="TASK=SHA256; exact task set is required")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    paper = args.paper
    expected = {"LA-002": ("completed", 7), "LA-003": ("blocked", 4)} if paper == "law_to_action" else {"AF-003": ("completed", 7)}
    hashes = dict(value.split("=", 1) for value in args.receipt_sha256)
    require(set(hashes) == set(expected), "receipt task set differs")
    require(not args.report.exists(), "report exists; inspect partial maintenance before resuming")
    report = {"schema": "paper-fifth-launch-evidence-maintenance/v1", "paper": paper,
              "started_at": C.now(), "apply": args.apply, "provider_invoked": False,
              "source_commit": args.expected_head, "audit_sha256": AUDIT_SHA,
              "validations": {}, "mutations": [], "success": False}
    repo = ROOT / ".worktrees" / f"vericodegen-{paper}-2026"
    lane = STATE / paper
    with (STATE / "campaign.lock").open("a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(sha(AUDIT) == AUDIT_SHA, "stopped audit changed")
        audit = C.read(AUDIT)
        campaign = C.read(STATE / "campaign.json")
        require(campaign == audit["campaign"] and campaign.get("stopped_at") and not campaign.get("cleanup_errors"), "campaign changed")
        require(not C.alive(campaign["controller"]), "controller is live")
        for entry in campaign["lanes"].values():
            require(not C.alive(entry["owner"]) and not C.alive(entry["supervisor"]), "campaign child is live")
        require(git(repo, "rev-parse", "HEAD") == args.expected_head and not git(repo, "status", "--porcelain"), "committed source changed or dirty")
        names = ("control.duckdb", "control.coordination.duckdb", "control.execution.duckdb")
        allowed = {*names, *(name + ".wal" for name in names)}
        present = {str(p) for name in names
                   for p in (lane / name, lane / (name + ".wal")) if p.exists()}
        saved = {path: value for path, value in audit["files"].items()
                 if Path(path).parent == lane and Path(path).name in allowed}
        require(set(saved) == present and all(str(lane / name) in present for name in names), "database/WAL population differs")
        for path, entry in saved.items():
            require(sha(path) == entry["sha256"] == sha(entry["backup"]), "database or saved backup changed")
        seeds = {t["id"]: t for t in C.read(repo / f"papers/completion/{paper}/tasks.json")["tasks"]}
        for task in expected:
            relative = f"papers/completion/{paper}/receipts/{task}.json"
            require(sha(repo / relative) == hashes[task], "paper receipt changed")
            receipt = C.read(repo / relative)
            require([c["criterion"] for c in receipt["criteria"]] == seeds[task]["acceptance_criteria"], "seed acceptance differs")
            argv = ["python3", "scripts/paper_supervisors.py", "verify-task", "--paper", paper, "--task", task]
            log = args.report.with_name(args.report.stem + "-" + task + "-verify.json")
            started = C.now()
            with log.open("w") as handle:
                result = subprocess.run(argv, cwd=repo, env=C.environment(repo), stdout=handle, stderr=subprocess.STDOUT, timeout=120)
            require(result.returncode == 0, "committed verify-task failed: " + task)
            report["validations"][task] = {"argv": argv, "started_at": started, "finished_at": C.now(),
                "exit_code": 0, "validation_log": str(log.resolve()), "validation_log_sha256": sha(log),
                "receipt_path": relative, "receipt_sha256": hashes[task], "acceptance_criteria": receipt["criteria"],
                "source_commit": args.expected_head, "provider_attempt_success_claimed": False,
                "execution_kind": "agent_assisted_postmerge_revalidation" if task != "LA-003" else "agent_assisted_protocol_completion"}
        require(git(repo, "rev-parse", "HEAD") == args.expected_head and not git(repo, "status", "--porcelain"), "source changed during validation")
        if not args.apply:
            report.update(success=True, finished_at=C.now())
            C.write(args.report, report)
            print(json.dumps({"dry_run": True, "success": True, "paper": paper}))
            return
        M._native(ROOT)
        from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import DatabaseImplementationDaemon
        owner_dir = lane / "fifth-evidence-maintenance-owner"
        owner_dir.mkdir(mode=0o700, exist_ok=True)
        ready_path = owner_dir / "paper-owner.ready.json"
        C.prepare_owner_start(ready_path, paper)
        process, process_record = C.launch([str(C.PYTHON), str(ROOT / "scripts/paper_state_owner.py"),
            "--database", str(lane / "control.duckdb"), "--state-dir", str(owner_dir),
            "--store-id", "vericodegen-2026-" + paper,
            "--secret-handle", "handle:vericodegen-2026:" + paper + ":fifth-evidence-maintenance"],
            ROOT, C.environment(ROOT), owner_dir / "owner.log")
        report["maintenance_owner"] = process_record
        try:
            C.write(args.report, report)
            ready = C.wait_owner_ready(process, process_record, ready_path, paper=paper, database=lane / "control.duckdb")
            vault = owner_dir / (ready["endpoint_secret_handle"].replace(":", "_").replace("/", "_") + ".quack-token")
            require(vault.stat().st_mode & 0o077 == 0, "credential permissions differ")
            os.environ["IPFS_ACCELERATE_AGENT_QUACK_TOKEN"] = vault.read_text().strip()
            os.environ["IPFS_ACCELERATE_AGENT_STATE_SCHEMA_REVISION"] = str(ready["schema_revision"])
            report["owner_identity"] = ready["identity"]
            with DatabaseImplementationDaemon(database_path=lane / "control.duckdb", quack_uri=ready["quack_endpoint"],
                authority_mode="quack", owner_session_id="paper-fifth-evidence-maintenance:" + paper,
                task_prefix="LA-" if paper == "law_to_action" else "AF-") as daemon:
                require(not all_running_attempts(daemon), "running attempt remains")
                source = daemon.task_source
                tasks = {t["task_alias"]: S.plain(t) for t in source.intent.list_tasks(limit=1000)}
                require(len(tasks) == 25 and set(tasks) == set(seeds), "native population differs")
                for alias, (status, revision) in expected.items():
                    task = tasks[alias]
                    require((task["status"], task["revision"]) == (status, revision), "native status/revision differs")
                    S.plan_record(paper, task, seeds[alias])
                    require([c["criterion"] for c in task["acceptance"]] == seeds[alias]["acceptance_criteria"], "native acceptance differs")
                    require([v["argv"] for v in task["validations"]] == [report["validations"][alias]["argv"]], "native validation differs")
                if paper == "law_to_action":
                    task = tasks["LA-003"]
                    prior = task["body"].get("completion_receipt", {})
                    require(prior.get("attempt_id") == LA_ATTEMPT and prior.get("provider_dispatched") is True
                        and prior.get("operation") == "database_portal_attempt_failure", "LA-003 failure differs")
                    attempt = daemon.get_attempt(LA_ATTEMPT)
                    require(attempt and attempt.status in {"failed", "blocked"}, "original provider attempt not retired")
                    for key in ("attempt_id", "claim_id", "task_cid", "owner_session_id", "attempt_number", "fencing_token", "fence_epoch", "lease_id"):
                        require(prior[key] == getattr(attempt, key), "failed attempt binding differs")
                    claim = daemon.coordinator.get_task_claim(attempt.claim_id)
                    require(str(getattr(claim.state, "value", claim.state)) == "released", "failed claim not released")
                    report["retained_failed_attempt"] = attempt.to_dict()
                    report["retained_failure_receipt"] = prior
                    outputs = [o["effect"] for o in task["outputs"]]
                    outputs.append({"path": f"papers/completion/{paper}/receipts/snapshots/LA-003/", "kind": "directory"})
                    payload = {k: task[k] for k in ("task_cid", "task_alias", "goal_cid", "ordinal", "status", "priority", "plan_cid", "objective_id", "body", "identity")}
                    event = source.intent.upsert_task(**payload, expected_revision=4, outputs=outputs)
                    changed = S.plain(source.intent.get_task(task["task_cid"]))
                    require(S.preserved(changed) == S.preserved(task) and changed["revision"] == 5, "unexpected scope mutation")
                    report["mutations"].append({"kind": "admit_required_snapshot_directory", "event": event.to_dict()})
                    tasks["LA-003"] = changed
                    C.write(args.report, report)
                for alias in expected:
                    task = tasks[alias]
                    validation_body = report["validations"][alias]
                    digest = "sha256:" + hashes[alias]
                    validation = source.record_validation_result(task_cid=task["task_cid"], outcome="passed",
                        evidence_digest=digest, argv=validation_body["argv"], body=validation_body)
                    correction = {"operation": "paper_agent_assisted_protocol_complete" if alias == "LA-003" else "paper_command_receipt_correction",
                        "task_id": alias, "paper_receipt": validation_body["receipt_path"], "evidence_digest": digest,
                        "source_commit": args.expected_head, "prior_native_receipt_sha256": S.digest(task["body"].get("completion_receipt", {})),
                        "validation_event": validation.to_dict(), "audit_sha256": AUDIT_SHA,
                        "provider_invoked": False, "provider_attempt_success_claimed": False,
                        "benchmark_result_claimed": False, "recorded_at": C.now()}
                    if alias == "LA-003":
                        correction["prior_failure_attempt_id"] = LA_ATTEMPT
                        result = source.compare_and_set_status(task["task_cid"], task["revision"], "completed", receipt=correction, evidence_digests=[digest])
                        require(result.changed and result.task.status == "completed", "protocol completion CAS failed")
                        require(daemon.get_attempt(LA_ATTEMPT).to_dict() == report["retained_failed_attempt"], "historical provider attempt changed")
                        report["mutations"].append({"kind": "agent_assisted_protocol_complete", "revision": result.revision, "receipt": correction})
                    else:
                        evidence = source.record_evidence(task_cid=task["task_cid"], evidence_kind="paper_command_receipt_correction", digest=digest, body=correction)
                        require(S.plain(source.intent.get_task(task["task_cid"])) == task, "completed task history changed")
                        report["mutations"].append({"kind": "append_corrected_evidence", "receipt": correction, "event": evidence.to_dict()})
                    C.write(args.report, report)
                report["final_tasks"] = [{k: t[k] for k in ("task_alias", "task_cid", "status", "revision")} for t in source.intent.list_tasks(limit=1000)]
                require(not all_running_attempts(daemon), "unexpected running attempt at completion")
            report.update(success=True, finished_at=C.now())
        finally:
            os.environ.pop("IPFS_ACCELERATE_AGENT_QUACK_TOKEN", None)
            report["cleanup_errors"] = C.cleanup_children([("owner", process, process_record)])
            if report["cleanup_errors"]:
                report["success"] = False
            C.write(args.report, report)
            require(not report["cleanup_errors"], "owner cleanup failed")
        print(json.dumps({"success": report["success"], "paper": paper, "report": str(args.report)}))


if __name__ == "__main__":
    main()
