#!/usr/bin/python3.12 -S
"""Targeted, assertion-heavy PGIR-211 orphan-candidate adoption.

The candidate path is deliberately embedded here rather than accepted on the
command line so the supervisor's broad worktree scanner cannot mistake this
bounded recovery process for a live provider invocation.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from ipfs_accelerate_py.agent_supervisor.runtime.configured_board_scheduler import (
    configured_board_common_args,
    load_configured_board,
)
from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (
    PortalTaskState,
    utc_now,
)
from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor import (
    TodoImplementationSupervisor,
    parse_args as parse_supervisor_args,
    supervisor_config_from_args,
)
from ipfs_accelerate_py.agent_supervisor.validation.validation_runtime import (
    VALIDATION_PYTHON_LAUNCHER_MODE_ENV,
    VALIDATION_PYTHON_PROFILE_ENV,
    build_validation_environment,
    validation_environment_for_runner,
)


ROOT = Path(
    "/home/barberb/lift_coding/.worktrees/pgir-successor-current-supervisor"
)
CONFIG = ROOT / (
    "config/agent_supervisor_proof_grounded_ir_learning_successor_scheduler.json"
)
RUNTIME = ROOT / (
    "data/agent_supervisor/proof_grounded_ir_learning/successor-v1/runtime"
)
STATE_DIR = RUNTIME / "state/lane-1"
STATE_PATH = STATE_DIR / "pgir_lane_1_task_state.json"
PROTECTED_ACTIVE_PATH = STATE_DIR / "implementation-protected-path-active.json"
WORKTREE = RUNTIME / (
    "worktrees/workspace_5b226adc52ae_05747af60262"
)
TASK_ID = "PGIR-211"
TASK_CID = "baguqeeraeothuxy6rl24wz2pwrcskbc5ed7exy2vsp6exxbyziohw72jgrpa"
TASK_KEY = (
    "task/v1/23a67a5f1e8af5cb674fb44525045d20fe4be35593fc4bdc38ca1c7b7f49345e"
)
BRANCH = "implementation/pgir-211-23a67a5f1e8a-attempt-1-1787685173"
CANDIDATE = "59cdab5572cac092fb42398fe908a424e54d9c4e"
CANDIDATE_TREE = "8e44a1024b9152cc988be0a9dad0fada2f0eecf4"
BASELINE = "10c38f56803442c224d379cedf6b0e5ca1e35147"
TARGET = "agent/pgir-successor-current-supervisor-20260825"
EXPECTED_TARGET_BEFORE = "8cbb26404298a6f0b34e65c363444beb075e3dbe"
EXPECTED_LIFECYCLE_REASON = "controlled_restart_dead_owner"
EXPECTED_LIFECYCLE_FENCE = 5
EXPECTED_LIFECYCLE_RECORD_ID = (
    "baguqeeram4gbgsquvl5g4vuhwadtamecafuse75plrjlboyjbsnyozst4sxq"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def git(*args: str, cwd: Path = ROOT) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(
        completed.returncode == 0,
        f"git {' '.join(args)} failed: {completed.stderr[-1000:]}",
    )
    return completed.stdout.strip()


def build_objects() -> tuple[Any, Any, Any]:
    board = load_configured_board(CONFIG, repo_root=ROOT)
    require(board.max_lanes == 2, "configured lane count drifted")
    argv = [
        *configured_board_common_args(board, implement=False),
        "--state-dir",
        str(STATE_DIR),
        "--state-prefix",
        "pgir_lane_1",
        "--task-shard-count",
        str(board.max_lanes),
        "--task-shard-index",
        "1",
        "--reconciliation-only",
    ]
    args = parse_supervisor_args(argv)
    supervisor = TodoImplementationSupervisor(
        supervisor_config_from_args(args, repo_root=ROOT)
    )
    daemon = supervisor._build_worktree_reconciliation_daemon()
    require(supervisor.config.reconciliation_only is True, "not reconciliation-only")
    require(supervisor.config.implement is False, "provider implementation enabled")
    require(daemon.implement is False, "daemon provider implementation enabled")
    require(daemon.resolved_merge_target_branch == TARGET, "merge target drifted")
    require(daemon.state_path == STATE_PATH, "lane state path drifted")
    return board, supervisor, daemon


def load_exact_task(daemon: Any) -> Any:
    matches = [task for task in daemon._load_tasks() if task.task_id == TASK_ID]
    require(len(matches) == 1, "PGIR-211 task cardinality drifted")
    task = matches[0]
    identity = daemon._identity_for_task(task)
    # Markdown task records use ``todo``; dependency-derived readiness lives
    # in the lane projection and was asserted by require_stale_state().
    require(task.status == "todo", f"PGIR-211 board status drifted: {task.status!r}")
    require(task.canonical_task_key == TASK_KEY, "task key drifted")
    require(task.canonical_task_cid == TASK_CID, "task CID field drifted")
    require(identity.canonical_task_key == TASK_KEY, "derived task key drifted")
    require(identity.canonical_task_cid == TASK_CID, "derived task CID drifted")
    return task


def require_candidate_and_target(supervisor: Any) -> tuple[str, str, dict[str, Any]]:
    require(WORKTREE.is_dir(), "candidate worktree is absent")
    require(git("branch", "--show-current", cwd=WORKTREE) == BRANCH, "branch drifted")
    require(git("rev-parse", "HEAD^{commit}", cwd=WORKTREE) == CANDIDATE, "candidate drifted")
    require(git("rev-parse", "HEAD^{tree}", cwd=WORKTREE) == CANDIDATE_TREE, "tree drifted")
    require(git("status", "--porcelain", cwd=WORKTREE) == "", "candidate is dirty")
    require(git("status", "--porcelain", cwd=ROOT) == "", "merge target is dirty")
    target_commit = supervisor._git_ref_commit(ROOT, TARGET)
    require(target_commit == EXPECTED_TARGET_BEFORE, "merge target head drifted")
    baseline = supervisor._git_merge_base(ROOT, TARGET, CANDIDATE)
    require(baseline == BASELINE, "candidate merge base drifted")
    preflight = supervisor._preflight_worktree_reconciliation_merge(
        ROOT,
        target_ref=TARGET,
        branch=BRANCH,
    )
    require(preflight.get("attempted") is True, "merge preflight did not run")
    require(preflight.get("mergeable") is True, f"candidate conflicts: {preflight}")
    require(int(preflight.get("returncode", -1)) == 0, "merge preflight failed")
    require(bool(str(preflight.get("tree") or "")), "merge preflight tree absent")
    return baseline, target_commit, preflight


def require_stale_state() -> PortalTaskState:
    state = PortalTaskState.load(STATE_PATH)
    require(state.implementation_in_progress is True, "stale execution flag is absent")
    require(state.active_task_id == TASK_ID, "active task drifted")
    require(state.active_task_key == TASK_KEY, "active task key drifted")
    require(state.active_task_cid == TASK_CID, "active task CID drifted")
    require(state.active_attempt == 1, "active attempt drifted")
    require(state.active_phase == "validating", "active phase drifted")
    require(Path(state.active_worktree_path) == WORKTREE, "active worktree drifted")
    require(state.active_branch == BRANCH, "active branch drifted")
    require(state.implementation_attempts.get(TASK_ID) == 1, "display attempt drifted")
    require(
        state.implementation_attempts_by_cid.get(TASK_CID) == 1,
        "CID attempt drifted",
    )
    require(state.task_statuses.get(TASK_ID) == "ready", "state task status drifted")
    require(PROTECTED_ACTIVE_PATH.is_file(), "protected snapshot is absent")
    return state


def require_exact_dead_lifecycle(daemon: Any) -> tuple[Any, Path, Path]:
    store = daemon.worktree_lifecycle
    record = store.load_workspace(WORKTREE)
    require(record is not None, "workspace lifecycle record is absent or malformed")
    require(record.record_id == EXPECTED_LIFECYCLE_RECORD_ID, "lifecycle record ID drifted")
    require(record.fence == EXPECTED_LIFECYCLE_FENCE, "lifecycle fence drifted")
    require(record.task_id == TASK_ID, "lifecycle task drifted")
    require(record.canonical_task_cid == TASK_CID, "lifecycle CID drifted")
    require(record.attempt == 1, "lifecycle attempt drifted")
    require(record.workspace_path == str(WORKTREE), "lifecycle workspace drifted")
    require(record.branch == BRANCH, "lifecycle branch drifted")
    require(record.merge_target == TARGET, "lifecycle target drifted")
    require(record.repo_root == str(ROOT), "lifecycle repository drifted")
    require(record.state_dir == str(STATE_DIR), "lifecycle state directory drifted")
    require(record.state.value == "terminal", "lifecycle is not terminal")
    require(record.terminal_reason == EXPECTED_LIFECYCLE_REASON, "terminal reason drifted")
    checked = store.require_exact_dead_owner(
        WORKTREE,
        expected_record_id=record.record_id,
        expected_fence=record.fence,
        expected_lease_id=record.lease_id,
        expected_task_id=TASK_ID,
        expected_canonical_task_cid=TASK_CID,
        expected_attempt=1,
        expected_branch=BRANCH,
        expected_merge_target=TARGET,
        expected_repo_root=str(ROOT),
        expected_state_dir=str(STATE_DIR),
        allow_terminal=True,
    )
    require(checked == record, "dead-owner lifecycle proof changed authority")
    record_path = store.workspace_path_for(WORKTREE)
    index_path = store.task_index_path_for(
        canonical_task_cid=TASK_CID,
        task_id=TASK_ID,
        attempt=1,
    )
    require(record_path.is_file(), "lifecycle workspace authority is absent")
    require(index_path.is_file(), "lifecycle task authority is absent")
    return record, record_path, index_path


def require_raw_no_site(daemon: Any) -> dict[str, str]:
    require(
        os.environ.get(VALIDATION_PYTHON_PROFILE_ENV) == "raw-no-site",
        "raw-no-site profile is not selected",
    )
    require(
        not os.environ.get(
            "IPFS_ACCELERATE_AGENT_IMPLEMENTATION_EXTERNAL_ISOLATION_JSON", ""
        ),
        "external validation isolation conflicts with raw-no-site",
    )
    environment = validation_environment_for_runner(
        build_validation_environment(),
        daemon._validation_command_runner,
    )
    mode = environment.get(VALIDATION_PYTHON_LAUNCHER_MODE_ENV, "")
    require(environment.get(VALIDATION_PYTHON_PROFILE_ENV) == "raw-no-site", "profile lost")
    require(":site-policy=no-site:" in mode, "no-site launcher policy absent")
    require(mode.endswith(":sealed-memfd"), "launcher is not sealed")
    return {
        "python": environment.get("IPFS_ACCELERATE_VALIDATION_PYTHON_EXECUTABLE", ""),
        "pythonpath": environment.get("PYTHONPATH", ""),
        "profile": environment.get(VALIDATION_PYTHON_PROFILE_ENV, ""),
        "launcher_mode": mode,
    }


def require_validation_receipts(result: dict[str, Any]) -> list[dict[str, Any]]:
    validation = result.get("validation_result")
    require(isinstance(validation, dict), "validation result is absent")
    require(validation.get("attempted") is True, "validation did not run")
    require(validation.get("passed") is True, f"validation failed: {validation}")
    results = validation.get("results")
    require(isinstance(results, list) and results, "validation command results are absent")
    receipts: list[dict[str, Any]] = []
    for index, command_result in enumerate(results):
        require(isinstance(command_result, dict), f"validation result {index} is malformed")
        require(int(command_result.get("returncode", -1)) == 0, f"validation {index} failed")
        launcher = command_result.get("validation_python_launcher")
        boundary = command_result.get("validation_filesystem_boundary")
        require(isinstance(launcher, dict), f"validation {index} launcher receipt absent")
        require(isinstance(boundary, dict), f"validation {index} filesystem receipt absent")
        mode = str(launcher.get("mode") or "")
        require(launcher.get("sealed") is True, f"validation {index} launcher unsealed")
        require(":site-policy=no-site:" in mode, f"validation {index} site policy drifted")
        require(mode.endswith(":sealed-memfd"), f"validation {index} launcher mode drifted")
        require(boundary.get("applied") is True, f"validation {index} boundary unapplied")
        require(
            boundary.get("python_site_policy") == "raw-no-site",
            f"validation {index} boundary site policy drifted",
        )
        receipts.append(
            {
                "command": str(command_result.get("command") or ""),
                "returncode": int(command_result.get("returncode", -1)),
                "launcher_mode": mode,
                "launcher_sealed": launcher.get("sealed"),
                "filesystem_schema": str(boundary.get("schema") or ""),
                "filesystem_applied": boundary.get("applied"),
                "python_site_policy": boundary.get("python_site_policy"),
            }
        )
    return receipts


def preflight() -> dict[str, Any]:
    _, supervisor, daemon = build_objects()
    state = require_stale_state()
    task = load_exact_task(daemon)
    record, record_path, index_path = require_exact_dead_lifecycle(daemon)
    baseline, target_commit, merge_preflight = require_candidate_and_target(supervisor)
    validation_environment = require_raw_no_site(daemon)
    return {
        "mode": "preflight",
        "approved": True,
        "task_id": task.task_id,
        "task_cid": task.canonical_task_cid,
        "attempt": state.active_attempt,
        "candidate": CANDIDATE,
        "candidate_tree": CANDIDATE_TREE,
        "baseline": baseline,
        "target": TARGET,
        "target_commit": target_commit,
        "merge_preflight_tree": merge_preflight.get("tree"),
        "lifecycle_record_id": record.record_id,
        "lifecycle_fence": record.fence,
        "lifecycle_terminal_reason": record.terminal_reason,
        "lifecycle_record_path": str(record_path),
        "lifecycle_index_path": str(index_path),
        "validation_environment": validation_environment,
    }


def adopt() -> dict[str, Any]:
    _, supervisor, daemon = build_objects()
    stale_state = require_stale_state()
    task = load_exact_task(daemon)
    record, record_path, index_path = require_exact_dead_lifecycle(daemon)
    baseline, target_commit, merge_preflight = require_candidate_and_target(supervisor)
    validation_environment = require_raw_no_site(daemon)
    attempts_before = dict(stale_state.implementation_attempts)
    cid_attempts_before = dict(stale_state.implementation_attempts_by_cid)

    protected = daemon._reconcile_implementation_protected_path_fence()
    require(protected.get("blocked") is False, f"protected fence blocked: {protected}")
    require(not PROTECTED_ACTIVE_PATH.exists(), "protected snapshot was not cleared")

    lifecycle_finalization = daemon._reconcile_exact_quiesced_worktree_lifecycle(
        worktree_path=WORKTREE,
        task_id=TASK_ID,
        canonical_task_cid=TASK_CID,
        branch_name=BRANCH,
        expected_attempt=1,
        reason="pgir_211_interrupted_candidate_terminal_predecessor_finalized",
        action="finalize",
        expected_lifecycle_record=record,
    )
    require(lifecycle_finalization.get("finalized") is True, "lifecycle not finalized")
    require(lifecycle_finalization.get("blocked") is False, "lifecycle finalization blocked")
    require(not record_path.exists(), "workspace lifecycle authority remains")
    require(not index_path.exists(), "task lifecycle authority remains")

    state = PortalTaskState.load(STATE_PATH)
    require(state.active_task_id == TASK_ID, "active state changed before clearing")
    require(state.active_attempt == 1, "attempt changed before clearing")
    daemon._mark_implementation_finished(state, finished_at=utc_now())
    state.save(STATE_PATH)
    cleared = PortalTaskState.load(STATE_PATH)
    require(cleared.implementation_in_progress is False, "execution state remains active")
    require(cleared.active_task_id == "", "active task was not cleared")
    require(cleared.active_attempt == 0, "active attempt was not cleared")
    require(cleared.active_worktree_path == "", "active worktree was not cleared")
    require(cleared.active_branch == "", "active branch was not cleared")
    require(cleared.implementation_attempts == attempts_before, "attempt map changed")
    require(cleared.implementation_attempts_by_cid == cid_attempts_before, "CID attempt map changed")
    require(cleared.task_statuses.get(TASK_ID) == "ready", "task status changed early")

    task = load_exact_task(daemon)
    require_candidate_and_target(supervisor)
    recovery_key = supervisor._worktree_reconciliation_recovery_key(
        task_cid=TASK_CID,
        baseline_ref=baseline,
        candidate_commit=CANDIDATE,
        target_commit=target_commit,
        mode="pre_merge",
    )
    require(len(recovery_key) == 40, "recovery key is malformed")
    result = daemon.reconcile_validated_worktree_candidate(
        worktree_path=WORKTREE,
        branch_name=BRANCH,
        task=task,
        baseline_ref=baseline,
        candidate_commit=CANDIDATE,
        recovery_key=recovery_key,
    )
    require(result.get("provider_dispatched") is False, "provider was dispatched")
    require(result.get("attempt_consumed") is False, "attempt was consumed")
    require(int(result.get("returncode", -1)) == 0, f"reconciliation failed: {result}")
    receipts = require_validation_receipts(result)
    merge_result = result.get("merge_result")
    require(isinstance(merge_result, dict), "merge result is absent")
    merged = merge_result.get("merged") is True
    queued = merge_result.get("queued") is True
    require(merged or queued, f"candidate was neither merged nor queued: {merge_result}")
    require(not (merged and queued), "candidate is both merged and queued")

    final_state = PortalTaskState.load(STATE_PATH)
    require(final_state.implementation_in_progress is False, "reconciliation state remains active")
    require(final_state.active_task_id == "", "reconciliation active task remains")
    require(final_state.implementation_attempts == attempts_before, "reconciliation consumed attempt")
    require(
        final_state.implementation_attempts_by_cid == cid_attempts_before,
        "reconciliation consumed CID attempt",
    )
    require(daemon.worktree_lifecycle.load_workspace(WORKTREE) is None, "lifecycle record remains")
    require(not index_path.exists(), "lifecycle task index remains")

    target_after = supervisor._git_ref_commit(ROOT, TARGET)
    board_task = [item for item in daemon._load_tasks() if item.task_id == TASK_ID]
    require(len(board_task) == 1, "post-reconciliation PGIR-211 cardinality drifted")
    if merged:
        require(target_after != target_commit, "merged result did not advance target")
        require(
            subprocess.run(
                ["git", "merge-base", "--is-ancestor", CANDIDATE, target_after],
                cwd=ROOT,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            ).returncode
            == 0,
            "candidate is not an ancestor of the advanced target",
        )
        require(board_task[0].status == "completed", "board completion callback did not land")
    else:
        require(bool(str(merge_result.get("request_id") or "")), "queued request ID absent")

    return {
        "mode": "adopt",
        "approved": True,
        "task_id": TASK_ID,
        "task_cid": TASK_CID,
        "candidate": CANDIDATE,
        "candidate_tree": CANDIDATE_TREE,
        "baseline": baseline,
        "target": TARGET,
        "target_before": target_commit,
        "target_after": target_after,
        "merge_preflight_tree": merge_preflight.get("tree"),
        "recovery_key": recovery_key,
        "protected_reconciliation": protected,
        "lifecycle_finalization": lifecycle_finalization,
        "validation_environment": validation_environment,
        "validation_receipts": receipts,
        "provider_dispatched": result.get("provider_dispatched"),
        "attempt_consumed": result.get("attempt_consumed"),
        "returncode": result.get("returncode"),
        "merge": {
            "merged": merged,
            "queued": queued,
            "reason": merge_result.get("reason"),
            "request_id": merge_result.get("request_id"),
            "implementation_commit": merge_result.get("implementation_commit"),
            "merge_commit": merge_result.get("merge_commit"),
            "completion_commit": merge_result.get("completion_commit"),
            "train_result": merge_result.get("train_result"),
            "worktree_lifecycle_handoff": merge_result.get("worktree_lifecycle_handoff"),
            "worktree_pool_handoff": merge_result.get("worktree_pool_handoff"),
        },
        "board_status": board_task[0].status,
        "attempts": final_state.implementation_attempts.get(TASK_ID),
        "cid_attempts": final_state.implementation_attempts_by_cid.get(TASK_CID),
    }


def require_clean_retry_state() -> PortalTaskState:
    state = PortalTaskState.load(STATE_PATH)
    require(state.implementation_in_progress is False, "execution state is active")
    require(state.active_task_id == "", "active task remains")
    require(state.active_task_key == "", "active task key remains")
    require(state.active_task_cid == "", "active task CID remains")
    require(state.active_attempt == 0, "active attempt remains")
    require(state.active_phase == "", "active phase remains")
    require(state.active_worktree_path == "", "active worktree remains")
    require(state.active_branch == "", "active branch remains")
    require(state.implementation_attempts.get(TASK_ID) == 1, "display attempt drifted")
    require(
        state.implementation_attempts_by_cid.get(TASK_CID) == 1,
        "CID attempt drifted",
    )
    require(state.task_statuses.get(TASK_ID) == "ready", "task is not ready")
    require(not PROTECTED_ACTIVE_PATH.exists(), "protected snapshot reappeared")
    return state


def require_lifecycle_absence(daemon: Any) -> dict[str, Any]:
    absence = daemon._reconcile_exact_quiesced_worktree_lifecycle(
        worktree_path=WORKTREE,
        task_id=TASK_ID,
        canonical_task_cid=TASK_CID,
        branch_name=BRANCH,
        expected_attempt=1,
        reason="pgir_211_retry_absence_verified",
        action="adopt",
    )
    require(absence.get("attempted") is False, f"lifecycle was attempted: {absence}")
    require(absence.get("blocked") is False, f"lifecycle absence blocked: {absence}")
    require(absence.get("reason") == "no_lifecycle_record", f"lifecycle remains: {absence}")
    require(absence.get("attempt") == 1, f"lifecycle attempt drifted: {absence}")
    require(absence.get("record_absence_verified") is True, "workspace absence unverified")
    require(absence.get("task_index_absence_verified") is True, "index absence unverified")
    return absence


def retry_preflight() -> dict[str, Any]:
    _, supervisor, daemon = build_objects()
    state = require_clean_retry_state()
    task = load_exact_task(daemon)
    baseline, target_commit, merge_preflight = require_candidate_and_target(supervisor)
    lifecycle_absence = require_lifecycle_absence(daemon)
    validation_environment = require_raw_no_site(daemon)
    envelope = json.loads(task.metadata["proposal artifact envelope"])
    require(envelope.get("schema", "").endswith("task-artifact-envelope@1"), "envelope absent")
    return {
        "mode": "retry-preflight",
        "approved": True,
        "task_id": task.task_id,
        "task_cid": task.canonical_task_cid,
        "attempt": state.implementation_attempts.get(TASK_ID),
        "candidate": CANDIDATE,
        "candidate_tree": CANDIDATE_TREE,
        "baseline": baseline,
        "target": TARGET,
        "target_commit": target_commit,
        "merge_preflight_tree": merge_preflight.get("tree"),
        "lifecycle_absence": lifecycle_absence,
        "artifact_envelope": envelope,
        "validation_environment": validation_environment,
    }


def retry_adopt() -> dict[str, Any]:
    _, supervisor, daemon = build_objects()
    initial_state = require_clean_retry_state()
    task = load_exact_task(daemon)
    baseline, target_commit, merge_preflight = require_candidate_and_target(supervisor)
    lifecycle_absence = require_lifecycle_absence(daemon)
    validation_environment = require_raw_no_site(daemon)
    attempts_before = dict(initial_state.implementation_attempts)
    cid_attempts_before = dict(initial_state.implementation_attempts_by_cid)

    recovery_key = supervisor._worktree_reconciliation_recovery_key(
        task_cid=TASK_CID,
        baseline_ref=baseline,
        candidate_commit=CANDIDATE,
        target_commit=target_commit,
        mode="pre_merge",
    )
    require(len(recovery_key) == 40, "recovery key is malformed")
    result = daemon.reconcile_validated_worktree_candidate(
        worktree_path=WORKTREE,
        branch_name=BRANCH,
        task=task,
        baseline_ref=baseline,
        candidate_commit=CANDIDATE,
        recovery_key=recovery_key,
    )
    require(result.get("provider_dispatched") is False, "provider was dispatched")
    require(result.get("attempt_consumed") is False, "attempt was consumed")
    validation = result.get("validation_result")
    require(isinstance(validation, dict), "validation result is absent")
    proposal_gate = validation.get("proposal_gate")
    require(isinstance(proposal_gate, dict), "proposal gate result is absent")
    require(proposal_gate.get("accepted") is True, f"proposal gate failed: {proposal_gate}")
    receipts = require_validation_receipts(result)
    merge_result = result.get("merge_result")
    require(isinstance(merge_result, dict), "merge result is absent")
    merged = merge_result.get("merged") is True
    queued = merge_result.get("queued") is True
    require(merged != queued, f"candidate merge disposition is invalid: {merge_result}")
    if merged:
        require(int(result.get("returncode", -1)) == 0, f"merged reconciliation failed: {result}")
    else:
        require(int(result.get("returncode", -1)) == 1, f"queued return code drifted: {result}")
        require(
            merge_result.get("reason") == "reconciled_candidate_queued_pending_merge",
            f"queued reason drifted: {merge_result}",
        )
        require(bool(str(merge_result.get("request_id") or "")), "queued request ID absent")

    final_state = PortalTaskState.load(STATE_PATH)
    require(final_state.implementation_in_progress is False, "reconciliation state is active")
    require(final_state.active_task_id == "", "reconciliation active task remains")
    require(final_state.implementation_attempts == attempts_before, "reconciliation consumed attempt")
    require(
        final_state.implementation_attempts_by_cid == cid_attempts_before,
        "reconciliation consumed CID attempt",
    )
    require(daemon.worktree_lifecycle.load_workspace(WORKTREE) is None, "lifecycle record remains")

    target_after = supervisor._git_ref_commit(ROOT, TARGET)
    board_task = [item for item in daemon._load_tasks() if item.task_id == TASK_ID]
    require(len(board_task) == 1, "post-reconciliation task cardinality drifted")
    if merged:
        require(target_after != target_commit, "merged result did not advance target")
        require(
            subprocess.run(
                ["git", "merge-base", "--is-ancestor", CANDIDATE, target_after],
                cwd=ROOT,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            ).returncode == 0,
            "candidate is not an ancestor of the advanced target",
        )
        require(board_task[0].status == "completed", "board completion did not land")
    else:
        require(target_after == target_commit, "queued handoff unexpectedly advanced target")

    return {
        "mode": "retry-adopt",
        "approved": True,
        "task_id": TASK_ID,
        "task_cid": TASK_CID,
        "candidate": CANDIDATE,
        "candidate_tree": CANDIDATE_TREE,
        "baseline": baseline,
        "target": TARGET,
        "target_before": target_commit,
        "target_after": target_after,
        "merge_preflight_tree": merge_preflight.get("tree"),
        "recovery_key": recovery_key,
        "lifecycle_absence": lifecycle_absence,
        "validation_environment": validation_environment,
        "validation_receipts": receipts,
        "provider_dispatched": result.get("provider_dispatched"),
        "attempt_consumed": result.get("attempt_consumed"),
        "returncode": result.get("returncode"),
        "proposal_gate": proposal_gate,
        "merge": {
            "merged": merged,
            "queued": queued,
            "reason": merge_result.get("reason"),
            "request_id": merge_result.get("request_id"),
            "implementation_commit": merge_result.get("implementation_commit"),
            "merge_commit": merge_result.get("merge_commit"),
            "completion_commit": merge_result.get("completion_commit"),
            "train_result": merge_result.get("train_result"),
            "worktree_lifecycle_handoff": merge_result.get("worktree_lifecycle_handoff"),
            "worktree_pool_handoff": merge_result.get("worktree_pool_handoff"),
        },
        "board_status": board_task[0].status,
        "attempts": final_state.implementation_attempts.get(TASK_ID),
        "cid_attempts": final_state.implementation_attempts_by_cid.get(TASK_CID),
    }


def main() -> int:
    require(
        len(sys.argv) == 2,
        "usage: pgir211_targeted_adopt.py preflight|adopt|retry-preflight|retry-adopt",
    )
    mode = sys.argv[1]
    require(mode in {"preflight", "adopt", "retry-preflight", "retry-adopt"}, "unknown mode")
    if mode == "preflight":
        result = preflight()
    elif mode == "adopt":
        result = adopt()
    elif mode == "retry-preflight":
        result = retry_preflight()
    else:
        result = retry_adopt()
    print(json.dumps(result, sort_keys=True, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
