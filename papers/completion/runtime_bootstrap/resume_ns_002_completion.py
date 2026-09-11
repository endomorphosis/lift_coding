"""One-shot native NS-002 postmerge revalidation/completion maintenance.

Default: verify the pinned stopped backup and committed corrected artifacts,
run the actual committed CLI validator, and write a preflight report only.
--apply additionally owns a temporary NS Quack owner, refreshes the native
validation checkpoint, and completes the exact saved claim. It never invokes
providers, repeats effects, requeues tasks, or submits the paper.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import paper_supervisor_campaign as C
import materialize_paper_database as M

PAPER = "neurosymbolic_supervision"
STATE = Path.home() / ".local/state/ipfs_accelerate_py/vericodegen-2026"
LANE = STATE / PAPER
REPO = ROOT / ".worktrees/vericodegen-neurosymbolic_supervision-2026"
AUDIT = Path(__file__).with_name("fifth_launch_stopped.json")
AUDIT_SHA = "7cd570ee159e72fb72cf17ffe5b212eb2504c1ad746c9f8a61c7a56720bdbef4"
RECEIPT = Path("papers/completion/neurosymbolic_supervision/receipts/NS-002.json")
OLD_MERGE = "21441b56d03f7381cdd673b1cf7e97a8f36466bb"
OLD_PHASE_SHA = "b27c098260f75f7b4cdd1c9cd6797f2433c971fcd6dd85d6f8995fd22e26757d"
IDENTITY = {
    "task_cid": "baguqeeranfbqnhqrjquvq43qq724eftv2n3omxm2nyib4bc2osbpk4yxidoq",
    "task_alias": "NS-002", "attempt_id": "attempt:694d560c19fd4379b543fbd45c4eb2fb",
    "claim_id": "claim:cff3aa3b15834d97b461111246961c69",
    "lease_id": "lease:412e320fbb494438b7091c271ed88193",
    "owner_session_id": "embedded-store:3aa965b11834111124c5fc19555f67f9",
    "attempt_number": 2, "fencing_token": 2, "fence_epoch": 2,
}
ARGV = ["python3", "scripts/paper_supervisors.py", "verify-task", "--paper", PAPER, "--task", "NS-002"]
TOKEN_ENV = "IPFS_ACCELERATE_AGENT_QUACK_TOKEN"


def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def sha(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def git(*args):
    return subprocess.check_output(["git", "--no-optional-locks", "-C", str(REPO), *args],
                                   text=True, stderr=subprocess.PIPE).strip()


def checked_repository(expected_head, expected_receipt):
    require(git("rev-parse", "HEAD") == expected_head, "NS integration HEAD changed")
    require(git("branch", "--show-current") == "agent/vericodegen-2026-neurosymbolic_supervision",
            "Wrong NS integration branch")
    require(not git("status", "--porcelain", "--untracked-files=normal"), "NS integration checkout is dirty")
    require(subprocess.run(["git", "-C", str(REPO), "merge-base", "--is-ancestor", OLD_MERGE, expected_head],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0,
            "Corrective source is not descended from the original provider merge")
    require(expected_head != OLD_MERGE, "A reviewed corrective commit is required")
    require(sha(REPO / RECEIPT) == expected_receipt, "Corrected receipt hash changed")
    committed = subprocess.check_output(["git", "-C", str(REPO), "show", f"{expected_head}:{RECEIPT}"])
    require(hashlib.sha256(committed).hexdigest() == expected_receipt, "Receipt is not committed at pinned HEAD")
    receipt = json.loads(committed)
    require(receipt.get("schema") == "paper-task-evidence/v1" and receipt.get("task_id") == "NS-002"
            and receipt.get("status") == "complete", "Unexpected corrected task receipt")
    completed = datetime.fromisoformat(receipt["completed_at"].replace("Z", "+00:00"))
    require(completed.tzinfo is not None and completed <= datetime.now(timezone.utc),
            "Corrected receipt must have an actual nonfuture timestamp")
    return receipt


def checked_stopped_files():
    require(sha(AUDIT) == AUDIT_SHA, "Stopped campaign audit changed")
    audit = C.read(AUDIT)
    campaign = C.read(STATE / "campaign.json")
    require(campaign == audit["campaign"] and campaign.get("stopped_at")
            and not campaign.get("cleanup_errors"), "Campaign differs from the clean stopped audit")
    require(not C.alive(campaign["controller"]), "Campaign controller is running")
    for lane in campaign["lanes"].values():
        require(not C.alive(lane["owner"]) and not C.alive(lane["supervisor"]), "Campaign child is running")
    names = {"control.duckdb", "control.coordination.duckdb", "control.execution.duckdb"}
    allowed = names | {name + ".wal" for name in names}
    records = {Path(original).name: item for original, item in audit["files"].items()
               if Path(original).parent == LANE and Path(original).name in allowed}
    require(names <= records.keys(), "Stopped audit lacks an NS database")
    require({name for name in allowed if (LANE / name).exists()} == records.keys(),
            "NS database/WAL population changed since stopped backup")
    for name, item in records.items():
        require(sha(LANE / name) == item["sha256"], "NS database changed since stopped backup: " + name)
        require(sha(item["backup"]) == item["sha256"], "Immutable stopped backup changed: " + name)
    return records


def frozen_execution_rows(daemon):
    connection = daemon._require_connection()
    result = {}
    for table, ordering in (("provider_invocations", "invocation_id"), ("effect_claims", "effect_id")):
        rows = [dict(row.items()) for row in connection.execute(f"SELECT * FROM {table} ORDER BY {ordering}").fetchall()]
        result[table] = {"count": len(rows), "sha256": digest(rows)}
    return result


def forbid_replay(*_args, **_kwargs):
    raise RuntimeError("NS completion maintenance refuses a provider/effect/validation callback replay")


def fresh_validation_body(original_phase, provider, effect, receipt, validation, expected_head, expected_receipt):
    manifest = {
        "schema": "paper-agent-assisted-postmerge-revalidation/v1", "identity": IDENTITY,
        "source_commit": expected_head, "source_tree": git("rev-parse", "HEAD^{tree}"),
        "original_provider_merge": OLD_MERGE, "paper_receipt": str(RECEIPT),
        "paper_receipt_sha256": expected_receipt, "validation": validation,
        "original_provider_receipt_id": provider["receipt_id"],
        "original_provider_evidence_digest": provider["evidence_digest"],
        "original_effect_receipt_sha256": digest(effect),
        "superseded_validation_phase_sha256": digest(original_phase),
        "provider_rerun": False, "benchmark_results_added": False,
    }
    return {
        "outcome": "passed", "evidence_digest": "sha256:" + digest(manifest), "argv": ARGV,
        "validator": "paper_agent_assisted_postmerge_revalidation",
        "execution_kind": "agent_assisted_postmerge_revalidation", "provider_rerun": False,
        "task_cid": IDENTITY["task_cid"], "attempt_id": IDENTITY["attempt_id"],
        "acceptance_criteria": receipt["criteria"], "validation_manifest": manifest,
        "supersedes_validation_phase": original_phase,
        "correction_reason": "Replace future-dated/unreproducible receipt provenance with reviewed committed artifacts and fresh CLI evidence.",
    }


def complete_saved_attempt(daemon, report, report_path, receipt, validation, args):
    attempt = daemon.get_attempt(IDENTITY["attempt_id"])
    require(attempt is not None, "Saved NS attempt is absent")
    for key, value in IDENTITY.items():
        require(getattr(attempt, key) == value, "Saved attempt identity changed: " + key)
    require((attempt.status, attempt.committed_phase, attempt.revision) == ("running", "validation", 5),
            "Saved attempt advanced; inspect durable history before resuming maintenance")
    running = daemon._require_connection().execute(
        "SELECT attempt_id FROM database_task_attempts WHERE status = 'running' ORDER BY attempt_id"
    ).fetchall()
    require([str(row[0]) for row in running] == [attempt.attempt_id],
            "Unexpected additional NS running attempt under any owner")
    task = daemon.task_source.get(attempt.task_cid)
    require(task is not None and task.status == "in_progress" and task.revision == 6,
            "NS control task changed before completion")
    control_claim = task.body.get("completion_receipt", {})
    require(control_claim.get("operation") == "database_claim"
            and control_claim.get("claim_id") == attempt.claim_id
            and control_claim.get("attempt_id") == attempt.attempt_id
            and control_claim.get("owner_session_id") == attempt.owner_session_id
            and control_claim.get("control_claimed_revision") == 6,
            "Control row is not the original exact claimed task")
    require(daemon.coordinator.get_prepared_task_completion(attempt.task_cid) is None,
            "Completion preparation already exists; inspect it before maintenance")
    daemon._protect_attempt_write(attempt)
    current = next(t for t in daemon.task_source.intent.list_tasks(limit=1000) if t["task_cid"] == attempt.task_cid)
    require([a["criterion"] for a in current["acceptance"]] == [a["criterion"] for a in receipt["criteria"]],
            "Corrected paper criteria differ from native control criteria")
    require(len(current["validations"]) == 1 and current["validations"][0]["argv"] == ARGV,
            "Actual CLI does not match native task validation")
    original = [p for p in daemon.phase_history(attempt.attempt_id) if p["phase"] == "validation"]
    require(len(original) == 1 and digest(original[0]) == OLD_PHASE_SHA, "Original validation checkpoint changed")
    provider = daemon.provider_invocation_recorded(attempt.attempt_id, idempotency_key="provider:" + attempt.attempt_id)
    effect = daemon.effect_claim_recorded(attempt.attempt_id, idempotency_key="effect:" + attempt.attempt_id)
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.database_portal_bridge import DatabasePortalExecutionBridge
    require(isinstance(provider, dict) and isinstance(effect, dict), "Saved provider/effect evidence is absent")
    bridge_digest = DatabasePortalExecutionBridge._require_accepted_provider(attempt, provider)
    require(effect.get("status") == "applied" and effect.get("effect") == "portal-supervised-accepted-effect"
            and effect.get("task_cid") == attempt.task_cid and effect.get("attempt_id") == attempt.attempt_id
            and effect.get("portal_receipt_id") == provider["receipt_id"]
            and effect.get("evidence_digest") == bridge_digest, "Saved effect is not bound to the accepted provider")
    before = frozen_execution_rows(daemon)
    archive = report_path.with_name(report_path.stem + ".prior-validation.json")
    with archive.open("x", encoding="utf-8") as handle:
        json.dump(original[0], handle, indent=2)
        handle.write("\n")
    report.update(original_attempt=attempt.to_dict(), original_validation_phase=original[0],
                  original_phase_archive={"path": str(archive), "sha256": sha(archive)},
                  provider_effect_before=before, stage="original_validation_archived")
    C.write(report_path, report)
    checked_repository(args.expected_head, args.receipt_sha256)
    body = fresh_validation_body(original[0], provider, effect, receipt, validation,
                                 args.expected_head, args.receipt_sha256)
    updated = daemon.commit_phase(attempt, "validation", body=body)
    require(updated.revision == 6 and updated.status == "running" and updated.committed_phase == "validation",
            "Native validation refresh returned an unexpected revision")
    readback = [p for p in daemon.phase_history(attempt.attempt_id) if p["phase"] == "validation"]
    require(len(readback) == 1 and readback[0]["body"] == body, "Fresh validation checkpoint readback differs")
    require(frozen_execution_rows(daemon) == before, "Validation refresh changed provider/effect history")
    report.update(fresh_validation=body, refreshed_attempt=updated.to_dict(), stage="fresh_validation_committed")
    C.write(report_path, report)
    checked_repository(args.expected_head, args.receipt_sha256)
    result = daemon.resume_attempt(updated, provider_fn=forbid_replay,
                                   effect_fn=forbid_replay, validation_fn=forbid_replay)
    final = daemon.get_attempt(attempt.attempt_id)
    task = daemon.task_source.get(attempt.task_cid)
    completion = daemon.coordinator.get_prepared_task_completion(attempt.task_cid)
    claim = daemon.coordinator.get_task_claim(attempt.claim_id)
    coordinated = daemon.coordinator.get_task_attempt(attempt.attempt_id)
    require(final.status == "succeeded" and final.committed_phase == "complete", "Execution did not complete")
    require(task.status == "completed" and task.revision == 7, "Control completion CAS did not produce revision 7")
    require(task.body["completion_receipt"]["evidence_digest"] == body["evidence_digest"],
            "Control completion used stale evidence")
    require(completion and completion["status"] == "succeeded"
            and completion["evidence_digest"] == body["evidence_digest"], "Coordination completion evidence differs")
    require(str(getattr(claim.state, "value", claim.state)) == "released"
            and str(getattr(coordinated.status, "value", coordinated.status)) == "succeeded",
            "Exact coordination claim/attempt is not successfully settled")
    require(frozen_execution_rows(daemon) == before, "Completion replayed or changed provider/effect evidence")
    require(daemon._require_connection().execute(
        "SELECT COUNT(*) FROM database_task_attempts WHERE status = 'running'"
    ).fetchone()[0] == 0, "A running NS execution attempt remains under an owner")
    checked_repository(args.expected_head, args.receipt_sha256)
    report.update(stage="native_completion_verified", success=True, final_attempt=final.to_dict(),
                  final_task=task.to_dict(), final_claim=claim.to_dict(), coordination_completion=completion,
                  provider_effect_after=frozen_execution_rows(daemon), native_resume_result=result)
    C.write(report_path, report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--receipt-sha256", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    require(re.fullmatch(r"[0-9a-f]{40}", args.expected_head), "Expected head must be a full Git SHA")
    require(re.fullmatch(r"[0-9a-f]{64}", args.receipt_sha256), "Receipt digest must be bare SHA-256")
    report_path = args.report.resolve()
    require(not report_path.exists(), "Report exists; inspect this one-shot maintenance before retrying")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = {"schema": "paper-ns-002-native-completion-maintenance/v1", "started_at": C.now(),
              "apply": args.apply, "success": False, "provider_invoked": False, "effect_replayed": False,
              "stopped_audit_sha256": AUDIT_SHA, "helper_sha256": sha(__file__), "stage": "preflight"}
    children = []
    with (STATE / "campaign.lock").open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        report["stopped_database_files"] = checked_stopped_files()
        receipt = checked_repository(args.expected_head, args.receipt_sha256)
        logfile = report_path.with_name(report_path.stem + ".validation.log")
        started = C.now()
        with logfile.open("x", encoding="utf-8") as output:
            completed = subprocess.run(ARGV, cwd=REPO, env=C.environment(REPO), stdin=subprocess.DEVNULL,
                                       stdout=output, stderr=subprocess.STDOUT, timeout=600)
        validation = {"argv": ARGV, "cwd": str(REPO), "started_at": started, "finished_at": C.now(),
                      "returncode": completed.returncode, "log": str(logfile), "log_sha256": sha(logfile)}
        report.update(validation=validation, expected_head=args.expected_head,
                      receipt_sha256=args.receipt_sha256, stage="cli_validation_finished")
        C.write(report_path, report)
        require(completed.returncode == 0, "Committed NS-002 CLI validation failed")
        checked_repository(args.expected_head, args.receipt_sha256)
        checked_stopped_files()
        if not args.apply:
            report.update(stage="preflight_complete", preflight_passed=True, finished_at=C.now())
            C.write(report_path, report)
            print(json.dumps({"preflight_passed": True, "database_mutated": False, "report": str(report_path)}))
            return
        M._native(REPO)
        from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import DatabaseImplementationDaemon
        owner_dir = LANE / ("completion-maintenance-owner-" + report_path.stem)
        owner_dir.mkdir(mode=0o700, exist_ok=False)
        ready_path = owner_dir / "paper-owner.ready.json"
        previous = {key: os.environ.get(key) for key in (TOKEN_ENV, "IPFS_ACCELERATE_AGENT_STATE_SCHEMA_REVISION")}
        try:
            process, record = C.launch([str(C.PYTHON), str(ROOT / "scripts/paper_state_owner.py"),
                "--database", str(LANE / "control.duckdb"), "--state-dir", str(owner_dir),
                "--store-id", "vericodegen-2026-" + PAPER,
                "--secret-handle", "handle:vericodegen-2026:" + PAPER + ":ns002-completion"],
                ROOT, C.environment(REPO), owner_dir / "owner.log")
            children.append(("ns-completion-owner", process, record))
            report.update(maintenance_owner_process=record, stage="maintenance_owner_started")
            C.write(report_path, report)
            ready = C.wait_owner_ready(process, record, ready_path, paper=PAPER, database=LANE / "control.duckdb")
            vault = owner_dir / (ready["endpoint_secret_handle"].replace(":", "_").replace("/", "_") + ".quack-token")
            require(vault.stat().st_mode & 0o077 == 0, "Owner credential permissions are not private")
            os.environ[TOKEN_ENV] = vault.read_text().strip()
            os.environ["IPFS_ACCELERATE_AGENT_STATE_SCHEMA_REVISION"] = "1"
            report["maintenance_owner_identity"] = ready["identity"]
            C.write(report_path, report)
            with DatabaseImplementationDaemon(database_path=LANE / "control.duckdb",
                    quack_uri=ready["quack_endpoint"], authority_mode="quack", task_prefix="NS-",
                    owner_session_id=IDENTITY["owner_session_id"], require_real_execution=True,
                    provider_fn=forbid_replay, effect_fn=forbid_replay, validation_fn=forbid_replay) as daemon:
                complete_saved_attempt(daemon, report, report_path, receipt, validation, args)
        except BaseException as exc:
            report.update(success=False, error_type=type(exc).__name__)
            C.write(report_path, report)
            raise
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            report["cleanup_errors"] = C.cleanup_children(children)
            report["finished_at"] = C.now()
            C.write(report_path, report)
            require(not report["cleanup_errors"], "Owned maintenance process cleanup failed")
        print(json.dumps({"success": report["success"], "provider_invoked": False, "report": str(report_path)}))


if __name__ == "__main__":
    main()
