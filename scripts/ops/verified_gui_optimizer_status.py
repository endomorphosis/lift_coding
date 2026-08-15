#!/usr/bin/env python3
"""Read-only health snapshot for the VerifiedGuiOptimizer supervisor board."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

SCHEMA = "verified-gui-optimizer-supervisor-health@1"
LANE_COUNT = 4
ATTEMPT_LIMIT_IDLE_REASON = "all_selectable_ready_tasks_reached_max_task_attempts"
EMPTY_BACKLOG_IDLE_REASONS = frozenset(
    {
        "no_shard_selectable_ready_tasks",
        "no_tasks_found",
    }
)
POLICY_IDLE_REASONS = frozenset(
    {
        ATTEMPT_LIMIT_IDLE_REASON,
        "all_selectable_ready_tasks_deferred_by_resource_claim",
        "all_selectable_ready_tasks_deprioritized_as_off_mission",
        "no_eligible_ready_tasks_after_selection_filters",
        "provider_capacity_backoff",
    }
)
DISPOSITION_IDLE_VALUES = frozenset(
    {
        "abstain_review",
        "closed_deterministic",
        "defer_capability",
        "residual_llm_authorized",
    }
)
ACTIVE_WRAPPER_STATUSES = frozenset({"running", "starting"})
RECOVERABLE_WRAPPER_STATUSES = frozenset(
    {
        "child_exited",
        "launch_failed",
        "max_restarts_reached",
        "recycling",
        "restarting",
        "agentic_maintenance_started",
        "agentic_maintenance_completed",
        "agentic_maintenance_failed",
    }
)
KNOWN_WRAPPER_STATUSES = (
    ACTIVE_WRAPPER_STATUSES | RECOVERABLE_WRAPPER_STATUSES | {"stopped", "termination_blocked"}
)
RUNNER_TERMINAL_LINE = "all supervisor tracks reached fresh terminal quiescence"
RUNNER_COMPLETED_LINE = "completed after terminal board drain"


def _read_json(path: Path) -> tuple[dict[str, Any], str | None]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {}, f"{type(exc).__name__}: {exc}"
    if not isinstance(value, dict):
        return {}, "JSON root is not an object"
    return value, None


def _read_pid(path: Path) -> int | None:
    try:
        value = int(path.read_text(encoding="utf-8").strip())
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    return value if value > 0 else None


def _positive_pid(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def _pid_alive(pid: int | None) -> bool:
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    try:
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
        closing_parenthesis = stat.rfind(")")
        if closing_parenthesis >= 0:
            state = stat[closing_parenthesis + 2 :].split(" ", 1)[0]
            if state == "Z":
                return False
    except (OSError, UnicodeError):
        pass
    return True


def _pid_identity_matches(
    pid: int | None,
    expected_tokens: tuple[str, ...],
) -> bool | None:
    """Check observable argv identity; None means the platform cannot prove it."""

    if pid is None or sys.platform != "linux":
        return None
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return None
    command = raw.replace(b"\0", b" ").decode("utf-8", errors="replace")
    if not command.strip():
        return None
    return any(token in command for token in expected_tokens)


def _age_seconds(value: Any, *, now: dt.datetime) -> float | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.UTC)
    return max(
        0.0,
        (now - parsed.astimezone(dt.UTC)).total_seconds(),
    )


def _file_age_seconds(path: Path, *, now: dt.datetime) -> float | None:
    try:
        modified_at = path.stat().st_mtime
    except OSError:
        return None
    return max(0.0, now.timestamp() - modified_at)


def _runner_terminal_evidence(path: Path | None) -> bool:
    if path is None:
        return False
    saw_start = False
    saw_terminal = False
    saw_completed = False
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if " starting " in line:
                    saw_start = True
                    saw_terminal = False
                    saw_completed = False
                elif saw_start and RUNNER_TERMINAL_LINE in line:
                    saw_terminal = True
                elif saw_start and saw_terminal and RUNNER_COMPLETED_LINE in line:
                    saw_completed = True
    except (OSError, UnicodeError):
        return False
    return saw_start and saw_terminal and saw_completed


def _task_count(
    task: dict[str, Any],
    field: str,
    issues: list[str],
) -> int | None:
    value = task.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        issues.append(f"invalid_task_field:{field}")
        return None
    return value


def _disposition_idle_reason(reason: str) -> bool:
    prefix = "disposition_idle:"
    return reason.startswith(prefix) and reason[len(prefix) :] in (DISPOSITION_IDLE_VALUES)


def _selection_idle_reason_is_quiescent(reason: str) -> bool:
    if reason in EMPTY_BACKLOG_IDLE_REASONS or reason in POLICY_IDLE_REASONS:
        return True
    if _disposition_idle_reason(reason):
        return True
    resource_prefix = "resource_claim_deferred:"
    if reason.startswith(resource_prefix) and len(reason) > len(resource_prefix):
        return True
    retry_prefix = "implementation_retry_deferred:"
    if not reason.startswith(retry_prefix):
        return False
    nested = reason[len(retry_prefix) :]
    return bool(nested) and (nested in POLICY_IDLE_REASONS or _disposition_idle_reason(nested))


def _task_projection_is_quiescent(
    *,
    active_task_id: str,
    implementation_in_progress: bool,
    selection_idle_reason: str,
    counts: dict[str, int | None],
) -> bool:
    if active_task_id or implementation_in_progress:
        return False
    if not _selection_idle_reason_is_quiescent(selection_idle_reason):
        return False
    required = (
        "ready_count",
        "selectable_ready_count",
        "eligible_ready_count",
        "blocked_count",
    )
    if any(counts[field] is None for field in required):
        return False
    if selection_idle_reason in EMPTY_BACKLOG_IDLE_REASONS:
        return all(
            counts[field] == 0
            for field in (
                "ready_count",
                "selectable_ready_count",
                "eligible_ready_count",
            )
        )
    return True


def _lane_snapshot(
    state_root: Path,
    lane: int,
    *,
    now: dt.datetime,
    stale_seconds: float,
    runner_terminal_evidence: bool,
) -> dict[str, Any]:
    lane_root = state_root / f"lane-{lane}"
    prefix = f"vgo_lane_{lane}"
    status_path = lane_root / f"{prefix}_supervisor_status.json"
    task_path = lane_root / f"{prefix}_task_state.json"
    supervisor_pid_path = lane_root / f"{prefix}_supervisor.pid"
    daemon_pid_path = lane_root / f"{prefix}_managed_daemon.pid"
    status, status_error = _read_json(status_path)
    task, task_error = _read_json(task_path)
    issues: list[str] = []
    blockers: list[str] = []
    warnings: list[str] = []

    if status_error:
        issues.append(f"supervisor_status_unreadable: {status_error}")
    if task_error:
        issues.append(f"task_state_unreadable: {task_error}")

    status_name = status.get("status") if status else None
    if status and (not isinstance(status_name, str) or not status_name):
        issues.append("invalid_supervisor_status")
        status_name = None
    status_updated_at = status.get("updated_at") or status.get("heartbeat_at") if status else None
    status_age = _age_seconds(status_updated_at, now=now)
    status_fresh = status_age is not None and status_age <= stale_seconds
    if status and status_age is None:
        issues.append("invalid_supervisor_status_timestamp")

    supervisor_marker_pid = _read_pid(supervisor_pid_path)
    daemon_marker_pid = _read_pid(daemon_pid_path)
    status_supervisor_pid = _positive_pid(status.get("supervisor_pid"))
    status_daemon_pid = _positive_pid(status.get("daemon_pid"))
    if status and status_supervisor_pid is None:
        issues.append("invalid_supervisor_status_pid")

    candidate_pids = {
        pid
        for pid in (
            supervisor_marker_pid,
            daemon_marker_pid,
            status_supervisor_pid,
            status_daemon_pid,
        )
        if pid is not None
    }
    pid_liveness = {pid: _pid_alive(pid) for pid in candidate_pids}
    supervisor_identity = {
        pid: _pid_identity_matches(
            pid,
            ("implementation_supervisor_entry.py", "implementation_supervisor"),
        )
        for pid in {supervisor_marker_pid, status_supervisor_pid}
        if pid is not None and pid_liveness.get(pid, False)
    }
    daemon_identity = {
        pid: _pid_identity_matches(pid, ("implementation_daemon",))
        for pid in {daemon_marker_pid, status_daemon_pid}
        if pid is not None and pid_liveness.get(pid, False)
    }
    supervisor_live_pids = sorted(
        pid
        for pid in {supervisor_marker_pid, status_supervisor_pid}
        if pid is not None
        and pid_liveness.get(pid, False)
        and supervisor_identity.get(pid) is not False
    )
    daemon_live_pids = sorted(
        pid
        for pid in {daemon_marker_pid, status_daemon_pid}
        if pid is not None
        and pid_liveness.get(pid, False)
        and daemon_identity.get(pid) is not False
    )

    count_fields = (
        "task_count",
        "completed_count",
        "ready_count",
        "selectable_ready_count",
        "eligible_ready_count",
        "external_reserved_count",
        "waiting_count",
        "blocked_count",
    )
    counts: dict[str, int | None] = {field: None for field in count_fields}
    active_task_id = ""
    implementation_in_progress = False
    selection_idle_reason = ""
    if not task_error:
        for field in count_fields:
            counts[field] = _task_count(task, field, issues)
        raw_active_task_id = task.get("active_task_id")
        if not isinstance(raw_active_task_id, str):
            issues.append("invalid_task_field:active_task_id")
        else:
            active_task_id = raw_active_task_id.strip()
        raw_in_progress = task.get("implementation_in_progress")
        if not isinstance(raw_in_progress, bool):
            issues.append("invalid_task_field:implementation_in_progress")
        else:
            implementation_in_progress = raw_in_progress
        raw_idle_reason = task.get("selection_idle_reason")
        if not isinstance(raw_idle_reason, str):
            issues.append("invalid_task_field:selection_idle_reason")
        else:
            selection_idle_reason = raw_idle_reason

    task_mtime_age = _file_age_seconds(task_path, now=now)
    terminal_fields_satisfied = bool(
        counts["task_count"] is not None
        and counts["task_count"] > 0
        and counts["completed_count"] == counts["task_count"]
        and not active_task_id
        and not implementation_in_progress
        and counts["eligible_ready_count"] == 0
        and counts["blocked_count"] == 0
        and counts["external_reserved_count"] == 0
    )
    terminal_quiescent = bool(runner_terminal_evidence and terminal_fields_satisfied)
    projection_quiescent = terminal_quiescent or (
        _task_projection_is_quiescent(
            active_task_id=active_task_id,
            implementation_in_progress=implementation_in_progress,
            selection_idle_reason=selection_idle_reason,
            counts=counts,
        )
    )
    execution_active = bool(active_task_id or implementation_in_progress)
    task_freshness_required = not projection_quiescent
    heartbeat_age = _age_seconds(task.get("heartbeat_at"), now=now)
    progress_age = _age_seconds(task.get("last_progress_at"), now=now)

    blocked_count = counts["blocked_count"] or 0
    if blocked_count > 0:
        blockers.append(f"blocked_tasks_present:{blocked_count}")
    attempt_limited = bool(
        not terminal_fields_satisfied and selection_idle_reason == ATTEMPT_LIMIT_IDLE_REASON
    )
    if attempt_limited:
        blockers.append("all_selectable_ready_tasks_reached_attempt_limit")

    last_implementation_returncode = task.get("last_implementation_returncode")
    if (
        isinstance(last_implementation_returncode, int)
        and not isinstance(last_implementation_returncode, bool)
        and last_implementation_returncode != 0
    ):
        warnings.append("last_implementation_failed")
    last_merge_returncode = task.get("last_merge_returncode")
    if (
        isinstance(last_merge_returncode, int)
        and not isinstance(last_merge_returncode, bool)
        and last_merge_returncode != 0
    ):
        warnings.append("last_merge_failed")

    projected_supervisor_alive = status.get("supervisor_pid_alive")
    projected_daemon_alive = status.get("daemon_pid_alive")
    return {
        "lane": lane,
        "status_path": str(status_path),
        "task_state_path": str(task_path),
        "supervisor_pid_path": str(supervisor_pid_path),
        "daemon_pid_path": str(daemon_pid_path),
        "status": status_name,
        "updated_at": status_updated_at,
        "wrapper_status_age_seconds": status_age,
        "wrapper_status_fresh": status_fresh,
        "supervisor_pid": supervisor_marker_pid,
        "supervisor_pid_alive": bool(
            supervisor_marker_pid and pid_liveness.get(supervisor_marker_pid, False)
        ),
        "status_supervisor_pid": status_supervisor_pid,
        "status_supervisor_pid_alive": bool(
            status_supervisor_pid and pid_liveness.get(status_supervisor_pid, False)
        ),
        "supervisor_pid_identity_matches": supervisor_identity.get(supervisor_marker_pid),
        "status_supervisor_pid_identity_matches": supervisor_identity.get(status_supervisor_pid),
        "supervisor_live_pids": supervisor_live_pids,
        "projected_supervisor_pid_alive": projected_supervisor_alive,
        "daemon_pid": daemon_marker_pid,
        "daemon_pid_alive": bool(daemon_marker_pid and pid_liveness.get(daemon_marker_pid, False)),
        "status_daemon_pid": status_daemon_pid,
        "status_daemon_pid_alive": bool(
            status_daemon_pid and pid_liveness.get(status_daemon_pid, False)
        ),
        "daemon_pid_identity_matches": daemon_identity.get(daemon_marker_pid),
        "status_daemon_pid_identity_matches": daemon_identity.get(status_daemon_pid),
        "daemon_live_pids": daemon_live_pids,
        "projected_daemon_pid_alive": projected_daemon_alive,
        "last_recycle_reason": status.get("last_recycle_reason"),
        "autonomous_unstall": status.get("autonomous_unstall"),
        "stalled_without_active_worker": bool(status.get("stalled_without_active_worker")),
        "heartbeat_at": task.get("heartbeat_at"),
        "heartbeat_age_seconds": heartbeat_age,
        "last_progress_at": task.get("last_progress_at"),
        "progress_age_seconds": progress_age,
        "task_state_mtime_age_seconds": task_mtime_age,
        "task_state_fresh_for_latest_run": runner_terminal_evidence,
        "task_projection_quiescent": projection_quiescent,
        "task_freshness_required": task_freshness_required,
        "terminal_fields_satisfied": terminal_fields_satisfied,
        "terminal_quiescent": terminal_quiescent,
        "implementation_in_progress": implementation_in_progress,
        "execution_active": execution_active,
        "active_task_id": active_task_id,
        "active_task_cid": task.get("active_task_cid"),
        "active_phase": task.get("active_phase"),
        "active_attempt": task.get("active_attempt"),
        "active_worktree_path": task.get("active_worktree_path"),
        **counts,
        "blocked_task_ids": task.get("blocked_task_ids"),
        "selection_idle_reason": selection_idle_reason,
        "attempt_limited": attempt_limited,
        "last_implementation_returncode": last_implementation_returncode,
        "last_implementation_commit": task.get("last_implementation_commit"),
        "last_merge_returncode": last_merge_returncode,
        "last_merge_commit": task.get("last_merge_commit"),
        "last_merge_error": task.get("last_merge_error"),
        "orphaned": False,
        "issues": issues,
        "blockers": blockers,
        "warnings": warnings,
    }


def _assess_lane_runtime(
    lane: dict[str, Any],
    *,
    master_alive: bool,
    runner_terminal_evidence: bool,
    stale_seconds: float,
) -> None:
    issues = lane["issues"]
    warnings = lane["warnings"]
    supervisor_live = bool(lane["supervisor_live_pids"])
    daemon_live = bool(lane["daemon_live_pids"])

    projected_supervisor = lane["projected_supervisor_pid_alive"]
    if isinstance(projected_supervisor, bool) and (
        projected_supervisor != lane["status_supervisor_pid_alive"]
    ):
        warnings.append("projected_supervisor_pid_liveness_disagrees")
    projected_daemon = lane["projected_daemon_pid_alive"]
    if isinstance(projected_daemon, bool) and (projected_daemon != lane["status_daemon_pid_alive"]):
        warnings.append("projected_daemon_pid_liveness_disagrees")

    if lane["status"] not in KNOWN_WRAPPER_STATUSES:
        issues.append(f"unknown_wrapper_status:{lane['status']}")
    if lane["status"] == "termination_blocked":
        issues.append("wrapper_termination_blocked")

    if not master_alive:
        if supervisor_live or daemon_live:
            lane["orphaned"] = True
            issues.append("live_lane_process_without_master")
        if lane["status"] != "stopped":
            issues.append(f"wrapper_not_stopped_after_master_exit:{lane['status']}")
        if Path(lane["supervisor_pid_path"]).exists():
            issues.append("supervisor_pid_marker_not_removed")
        if Path(lane["daemon_pid_path"]).exists():
            issues.append("daemon_pid_marker_not_removed")
        return

    if runner_terminal_evidence and lane["status"] == "stopped":
        warnings.append("terminal_drain_in_progress")
        return

    if lane["supervisor_pid"] is None:
        issues.append("supervisor_pid_marker_missing_or_invalid")
    elif not lane["supervisor_pid_alive"]:
        issues.append("supervisor_pid_not_alive")
    elif lane["supervisor_pid_identity_matches"] is False:
        issues.append("supervisor_pid_identity_mismatch")
    if lane["status_supervisor_pid"] is None:
        issues.append("supervisor_status_pid_missing_or_invalid")
    elif not lane["status_supervisor_pid_alive"]:
        issues.append("supervisor_status_pid_not_alive")
    elif lane["status_supervisor_pid_identity_matches"] is False:
        issues.append("supervisor_status_pid_identity_mismatch")
    if (
        lane["supervisor_pid"] is not None
        and lane["status_supervisor_pid"] is not None
        and lane["supervisor_pid"] != lane["status_supervisor_pid"]
    ):
        issues.append("supervisor_pid_marker_status_mismatch")
    if len(lane["supervisor_live_pids"]) > 1:
        lane["orphaned"] = True
        issues.append("multiple_live_supervisor_pids")

    if lane["wrapper_status_age_seconds"] is None:
        issues.append("wrapper_status_age_unknown")
    elif not lane["wrapper_status_fresh"]:
        issues.append("wrapper_status_stale")
    if lane["status"] == "stopped" and not runner_terminal_evidence:
        issues.append("wrapper_stopped_while_master_running")
    elif lane["status"] in RECOVERABLE_WRAPPER_STATUSES:
        warnings.append(f"wrapper_recovery_in_progress:{lane['status']}")
    if lane["stalled_without_active_worker"]:
        issues.append("wrapper_reports_stalled_without_active_worker")

    daemon_expected = lane["status"] in ACTIVE_WRAPPER_STATUSES
    if daemon_expected:
        if lane["daemon_pid"] is None:
            issues.append("daemon_pid_marker_missing_or_invalid")
        elif not lane["daemon_pid_alive"]:
            issues.append("daemon_pid_not_alive")
        elif lane["daemon_pid_identity_matches"] is False:
            issues.append("daemon_pid_identity_mismatch")
        if lane["status_daemon_pid"] is None:
            issues.append("supervisor_status_daemon_pid_missing_or_invalid")
        elif not lane["status_daemon_pid_alive"]:
            issues.append("supervisor_status_daemon_pid_not_alive")
        elif lane["status_daemon_pid_identity_matches"] is False:
            issues.append("supervisor_status_daemon_pid_identity_mismatch")
        if (
            lane["daemon_pid"] is not None
            and lane["status_daemon_pid"] is not None
            and lane["daemon_pid"] != lane["status_daemon_pid"]
        ):
            issues.append("daemon_pid_marker_status_mismatch")
    if len(lane["daemon_live_pids"]) > 1:
        lane["orphaned"] = True
        issues.append("multiple_live_daemon_pids")
    if daemon_live and not supervisor_live:
        lane["orphaned"] = True
        issues.append("orphaned_daemon_without_live_wrapper")

    enforce_task_freshness = bool(lane["status"] == "running" and lane["task_freshness_required"])
    if enforce_task_freshness:
        # The managed daemon deliberately blocks while an implementation
        # command runs, so its task-state projection may remain byte-stable
        # for the full command timeout.  Fresh wrapper heartbeats, actual PID
        # liveness, and stalled_without_active_worker are the authoritative
        # runtime signals; task timestamps remain diagnostic only.
        heartbeat_age = lane["heartbeat_age_seconds"]
        if heartbeat_age is None:
            warnings.append("task_heartbeat_age_unknown")
        elif heartbeat_age > stale_seconds:
            warnings.append("task_heartbeat_stale_while_wrapper_live")
        if lane["execution_active"]:
            progress_age = lane["progress_age_seconds"]
            if progress_age is None:
                warnings.append("active_progress_age_unknown")
            elif progress_age > stale_seconds:
                warnings.append("active_progress_stale_while_wrapper_live")


def build_report(
    repo_root: Path,
    runtime_relative: str,
    stale_seconds: float,
) -> dict[str, Any]:
    now = dt.datetime.now(dt.UTC)
    runtime_root = (repo_root / runtime_relative).resolve()
    state_root = runtime_root / "state"
    master_pid_path = state_root / "configured-board-master.pid"
    master_pid = _read_pid(master_pid_path)
    master_pid_alive = _pid_alive(master_pid)
    master_pid_identity_matches = (
        _pid_identity_matches(
            master_pid,
            ("multi_supervisor_runner",),
        )
        if master_pid_alive
        else None
    )
    master_runtime_alive = bool(master_pid_alive and master_pid_identity_matches is not False)
    logs = sorted((runtime_root / "logs").glob("configured-board-*.log"))
    latest_master_log = logs[-1] if logs else None
    runner_terminal_evidence = _runner_terminal_evidence(latest_master_log)
    lanes = [
        _lane_snapshot(
            state_root,
            lane,
            now=now,
            stale_seconds=stale_seconds,
            runner_terminal_evidence=runner_terminal_evidence,
        )
        for lane in range(LANE_COUNT)
    ]
    for lane in lanes:
        _assess_lane_runtime(
            lane,
            master_alive=master_runtime_alive,
            runner_terminal_evidence=runner_terminal_evidence,
            stale_seconds=stale_seconds,
        )

    all_lanes_terminal = bool(lanes) and all(lane["terminal_quiescent"] for lane in lanes)
    any_lane_process_alive = any(
        lane["supervisor_live_pids"] or lane["daemon_live_pids"] for lane in lanes
    )
    terminal_drained = bool(
        all_lanes_terminal
        and not master_runtime_alive
        and not any_lane_process_alive
        and not master_pid_path.exists()
        and all(lane["status"] == "stopped" for lane in lanes)
        and all(
            not Path(lane["supervisor_pid_path"]).exists()
            and not Path(lane["daemon_pid_path"]).exists()
            for lane in lanes
        )
    )

    issues = [f"lane_{lane['lane']}:{issue}" for lane in lanes for issue in lane["issues"]]
    blockers = [f"lane_{lane['lane']}:{blocker}" for lane in lanes for blocker in lane["blockers"]]
    warnings = [f"lane_{lane['lane']}:{warning}" for lane in lanes for warning in lane["warnings"]]
    if master_pid_alive and master_pid_identity_matches is False:
        issues.append("configured_board_master_pid_identity_mismatch")
    if not master_runtime_alive and not terminal_drained:
        issues.append("configured_board_master_not_alive")
    terminal_fields_without_runner_evidence = (
        bool(lanes)
        and all(lane["terminal_fields_satisfied"] for lane in lanes)
        and not runner_terminal_evidence
    )
    if not master_runtime_alive and terminal_fields_without_runner_evidence:
        issues.append("terminal_projection_lacks_runner_freshness_evidence")

    if terminal_drained and not issues:
        lifecycle = "completed"
    elif issues:
        lifecycle = "unhealthy"
    elif blockers:
        lifecycle = "blocked"
    elif master_runtime_alive:
        lifecycle = "running"
    else:
        lifecycle = "unhealthy"
        issues.append("indeterminate_supervisor_lifecycle")
    healthy = lifecycle in {"running", "completed"}
    return {
        "schema": SCHEMA,
        "observed_at": now.isoformat().replace("+00:00", "Z"),
        "repo_root": str(repo_root),
        "runtime_root": str(runtime_root),
        "lifecycle": lifecycle,
        "healthy": healthy,
        "master_pid_path": str(master_pid_path),
        "master_pid": master_pid,
        "master_pid_alive": master_pid_alive,
        "master_pid_identity_matches": master_pid_identity_matches,
        "master_runtime_alive": master_runtime_alive,
        "latest_master_log": (str(latest_master_log) if latest_master_log else None),
        "runner_terminal_evidence": runner_terminal_evidence,
        "stale_seconds": stale_seconds,
        "terminal_lane_count": sum(1 for lane in lanes if lane["terminal_quiescent"]),
        "all_lanes_terminal": all_lanes_terminal,
        "terminal_drained": terminal_drained,
        "blocked_lane_count": sum(1 for lane in lanes if lane["blockers"]),
        "orphaned_lane_count": sum(1 for lane in lanes if lane["orphaned"]),
        "issues": issues,
        "blockers": blockers,
        "warnings": warnings,
        "lanes": lanes,
    }


def _report_exit_code(report: dict[str, Any]) -> int:
    return 0 if report.get("lifecycle") in {"running", "completed"} else 1


def _run_self_test() -> int:
    import tempfile
    from unittest import mock

    scenario_count = 0

    def check(condition: bool, message: str) -> None:
        nonlocal scenario_count
        scenario_count += 1
        if not condition:
            raise AssertionError(message)

    with tempfile.TemporaryDirectory(prefix="vgo-status-self-test-") as raw:
        repo_root = Path(raw)
        runtime_relative = "data/agent_supervisor/verified_gui_optimizer"
        runtime_root = repo_root / runtime_relative
        state_root = runtime_root / "state"
        log_root = runtime_root / "logs"
        log_root.mkdir(parents=True)
        now = dt.datetime.now(dt.UTC)
        stamp = now.strftime("%Y%m%dT%H%M%SZ")
        (log_root / f"configured-board-{stamp}.log").write_text(
            f"{now.isoformat()} starting self-test\n",
            encoding="utf-8",
        )
        fresh = now.isoformat().replace("+00:00", "Z")
        stale = (
            (now - dt.timedelta(hours=1))
            .isoformat()
            .replace(
                "+00:00",
                "Z",
            )
        )
        master_pid = 100
        live_pids = {master_pid}
        state_root.mkdir(parents=True)
        (state_root / "configured-board-master.pid").write_text(
            f"{master_pid}\n",
            encoding="utf-8",
        )

        def write_lane(
            lane: int,
            *,
            status_name: str = "running",
            active: bool = True,
            heartbeat: str = fresh,
            progress: str = fresh,
            idle_reason: str = "",
            blocked_count: int = 0,
            completed_count: int = 1,
            with_pid_markers: bool = True,
        ) -> None:
            lane_root = state_root / f"lane-{lane}"
            lane_root.mkdir(parents=True, exist_ok=True)
            prefix = f"vgo_lane_{lane}"
            supervisor_pid = 200 + lane
            daemon_pid = 300 + lane
            daemon_expected = status_name in ACTIVE_WRAPPER_STATUSES
            status_payload = {
                "status": status_name,
                "updated_at": fresh,
                "supervisor_pid": supervisor_pid,
                "daemon_pid": daemon_pid if daemon_expected else None,
                "supervisor_pid_alive": status_name != "stopped",
                "daemon_pid_alive": daemon_expected,
            }
            task_payload = {
                "task_count": 42,
                "completed_count": completed_count,
                "ready_count": 1 if active else 0,
                "selectable_ready_count": 1 if active else 0,
                "eligible_ready_count": 1 if active else 0,
                "external_reserved_count": 0,
                "waiting_count": 40 if active else 42 - completed_count,
                "blocked_count": blocked_count,
                "blocked_task_ids": (["VGO-BLOCKED"] if blocked_count else []),
                "active_task_id": f"VGO-{lane + 1:03d}" if active else "",
                "active_task_cid": f"cid-{lane}",
                "implementation_in_progress": active,
                "selection_idle_reason": idle_reason,
                "heartbeat_at": heartbeat,
                "last_progress_at": progress,
                "last_implementation_returncode": 0,
                "last_merge_returncode": 0,
            }
            (lane_root / f"{prefix}_supervisor_status.json").write_text(
                json.dumps(status_payload),
                encoding="utf-8",
            )
            (lane_root / f"{prefix}_task_state.json").write_text(
                json.dumps(task_payload),
                encoding="utf-8",
            )
            for path in (
                lane_root / f"{prefix}_supervisor.pid",
                lane_root / f"{prefix}_managed_daemon.pid",
            ):
                path.unlink(missing_ok=True)
            if with_pid_markers:
                (lane_root / f"{prefix}_supervisor.pid").write_text(
                    f"{supervisor_pid}\n",
                    encoding="utf-8",
                )
                if daemon_expected:
                    (lane_root / f"{prefix}_managed_daemon.pid").write_text(
                        f"{daemon_pid}\n",
                        encoding="utf-8",
                    )

        for lane in range(LANE_COUNT):
            live_pids.update({200 + lane, 300 + lane})
            write_lane(lane)

        module = sys.modules[__name__]
        with (
            mock.patch.object(
                module,
                "_pid_alive",
                side_effect=lambda pid: bool(pid in live_pids),
            ),
            mock.patch.object(
                module,
                "_pid_identity_matches",
                return_value=None,
            ),
        ):
            report = build_report(repo_root, runtime_relative, 60.0)
            check(report["lifecycle"] == "running", "running lifecycle")
            check(_report_exit_code(report) == 0, "running exit code")

            for lane in range(LANE_COUNT):
                write_lane(lane, heartbeat=stale, progress=stale)
            report = build_report(repo_root, runtime_relative, 60.0)
            check(report["lifecycle"] == "running", "active stable lifecycle")
            check(
                any(
                    "task_heartbeat_stale_while_wrapper_live" in item for item in report["warnings"]
                ),
                "active stable task projection is diagnostic",
            )

            for lane in range(LANE_COUNT):
                write_lane(
                    lane,
                    active=False,
                    heartbeat=stale,
                    progress=stale,
                    idle_reason="no_shard_selectable_ready_tasks",
                )
            report = build_report(repo_root, runtime_relative, 60.0)
            check(report["lifecycle"] == "running", "quiescent lifecycle")
            check(
                not any("task_heartbeat_stale" in item for item in report["issues"]),
                "quiescent task heartbeat is not a failure",
            )

            write_lane(
                0,
                active=False,
                idle_reason="no_eligible_ready_tasks_after_selection_filters",
                blocked_count=1,
            )
            report = build_report(repo_root, runtime_relative, 60.0)
            check(report["lifecycle"] == "blocked", "blocked lifecycle")

            write_lane(
                0,
                active=False,
                idle_reason=ATTEMPT_LIMIT_IDLE_REASON,
            )
            report = build_report(repo_root, runtime_relative, 60.0)
            check(report["lifecycle"] == "blocked", "attempt-limit lifecycle")

            write_lane(0)
            status_path = state_root / "lane-0" / "vgo_lane_0_supervisor_status.json"
            stale_status = json.loads(status_path.read_text(encoding="utf-8"))
            stale_status["updated_at"] = stale
            status_path.write_text(json.dumps(stale_status), encoding="utf-8")
            report = build_report(repo_root, runtime_relative, 60.0)
            check(report["lifecycle"] == "unhealthy", "stale wrapper lifecycle")

            write_lane(0)
            live_pids.remove(200)
            report = build_report(repo_root, runtime_relative, 60.0)
            check(report["lifecycle"] == "unhealthy", "actual dead PID detected")
            live_pids.add(200)

            write_lane(
                0,
                status_name="max_restarts_reached",
                active=False,
                idle_reason="no_shard_selectable_ready_tasks",
            )
            live_pids.discard(300)
            report = build_report(repo_root, runtime_relative, 60.0)
            check(report["lifecycle"] == "running", "recoverable wrapper state")

            write_lane(
                0,
                status_name="unknown_state",
                active=False,
                idle_reason="no_shard_selectable_ready_tasks",
            )
            report = build_report(repo_root, runtime_relative, 60.0)
            check(report["lifecycle"] == "unhealthy", "unknown wrapper state")
            write_lane(0)
            live_pids.add(300)

            (state_root / "configured-board-master.pid").unlink()
            live_pids.remove(master_pid)
            report = build_report(repo_root, runtime_relative, 60.0)
            check(report["lifecycle"] == "unhealthy", "orphan lifecycle")
            check(report["orphaned_lane_count"] == 4, "all orphan lanes found")

            live_pids.clear()
            for lane in range(LANE_COUNT):
                write_lane(
                    lane,
                    status_name="stopped",
                    active=False,
                    heartbeat=stale,
                    progress=stale,
                    idle_reason="no_tasks_found",
                    completed_count=42,
                    with_pid_markers=False,
                )
            report = build_report(repo_root, runtime_relative, 60.0)
            check(
                report["lifecycle"] == "unhealthy",
                "terminal fields alone lack runner freshness evidence",
            )
            with (log_root / f"configured-board-{stamp}.log").open(
                "a",
                encoding="utf-8",
            ) as handle:
                handle.write((f"{fresh} heartbeat\n") * 10_000)
                handle.write(f"{fresh} {RUNNER_TERMINAL_LINE}\n")
                handle.write(f"{fresh} {RUNNER_COMPLETED_LINE}\n")
            report = build_report(repo_root, runtime_relative, 60.0)
            check(report["lifecycle"] == "completed", "completed lifecycle")
            check(report["terminal_drained"] is True, "terminal drain detected")
            check(_report_exit_code(report) == 0, "completed exit code")

            with (log_root / f"configured-board-{stamp}.log").open(
                "a",
                encoding="utf-8",
            ) as handle:
                handle.write(f"{fresh} starting same-second rerun\n")
            report = build_report(repo_root, runtime_relative, 60.0)
            check(
                report["lifecycle"] == "unhealthy",
                "prior same-second terminal evidence is not reused",
            )

    print(
        json.dumps(
            {
                "schema": "verified-gui-optimizer-status-self-test@1",
                "passed": True,
                "assertion_count": scenario_count,
            },
            sort_keys=True,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--runtime-root",
        default="data/agent_supervisor/verified_gui_optimizer",
        help="Repository-relative configured-board runtime root.",
    )
    parser.add_argument("--stale-seconds", type=float, default=900.0)
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run deterministic stdlib-only lifecycle tests and exit.",
    )
    args = parser.parse_args(argv)
    if args.self_test:
        return _run_self_test()
    if not math.isfinite(args.stale_seconds) or args.stale_seconds <= 0:
        parser.error("--stale-seconds must be finite and positive")
    repo_root = args.repo_root.resolve()
    report = build_report(repo_root, args.runtime_root, args.stale_seconds)
    print(json.dumps(report, sort_keys=True, indent=2))
    return _report_exit_code(report)


if __name__ == "__main__":
    raise SystemExit(main())
