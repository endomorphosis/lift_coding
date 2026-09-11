#!/usr/bin/env python3
"""Read native per-attempt worker projections; never mutate task authority."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import time


def _object(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError):
            return {}
    return value if isinstance(value, dict) else {}


def _claim(task):
    body = _object(task.get("body_json", task.get("body")))
    receipt = _object(body.get("completion_receipt"))
    if receipt.get("operation") == "database_claim" and all(
            isinstance(receipt.get(key), str) and receipt[key] for key in ("attempt_id", "claim_id")):
        return (task["task_cid"], receipt["attempt_id"], receipt["claim_id"])
    return None


def _binding_match(path, tasks):
    """Missing evidence remains unconfirmed; aliases never establish a claim."""
    binding_path = path.with_name("database-attempt-binding.json")
    try:
        if binding_path.resolve().parent != path.resolve().parent or binding_path.stat().st_size > 64 * 1024:
            raise ValueError("binding outside attempt or oversized")
        binding = _object(json.loads(binding_path.read_text()))
        keys = ("task_cid", "attempt_id", "claim_id")
        if not all(isinstance(binding.get(key), str) and binding[key] for key in keys):
            raise ValueError("binding identity incomplete")
    except (OSError, ValueError, TypeError):
        return {"authority_match": "unconfirmed", "authority_match_reason": "binding_missing_or_invalid"}
    record = {key: binding[key] for key in keys}
    record["binding_projection"] = str(binding_path)
    task = tasks.get(binding["task_cid"]) if tasks is not None else None
    if task is None:
        return dict(record, authority_match="unconfirmed", authority_match_reason="owner_task_unavailable")
    record["authoritative_task_status"] = task.get("status")
    if task.get("status") in {"ready", "open", "todo", "blocked", "done", "completed", "cancelled", "canceled", "failed"}:
        return dict(record, authority_match="historical", authority_match_reason="owner_task_not_in_progress")
    current = _claim(task) if task.get("status") == "in_progress" else None
    if current is None:
        return dict(record, authority_match="unconfirmed", authority_match_reason="owner_claim_unavailable")
    if tuple(binding[key] for key in keys) != current:
        return dict(record, authority_match="historical", authority_match_reason="owner_claim_superseded")
    return dict(record, authority_match="current", authority_match_reason="owner_claim_matched")


def _age(value, clock):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return None
        return round(max(0.0, clock - parsed.timestamp()), 1)
    except (TypeError, ValueError):
        return None


def observe_lane(lane, *, now=None, stale_seconds=1800, authoritative_tasks=None):
    """Return bounded observations, keeping stale projections distinct from work.

    A worker heartbeat is activity evidence, not proof of useful task progress.
    Completed historical attempt files do not raise stale-worker notices.
    """
    lane = Path(lane).resolve()
    clock = time.time() if now is None else float(now)
    records, notices, supervisors = [], [], []
    tasks = None
    if authoritative_tasks is not None:
        tasks = {}
        for task in authoritative_tasks:
            if isinstance(task, dict) and isinstance(task.get("task_cid"), str) and task["task_cid"]:
                # Duplicate owner rows are ambiguous, never proof of a historical claim.
                cid = task["task_cid"]
                tasks[cid] = task if cid not in tasks else None
    matched_current = set()
    for path in (lane / "state").glob("*_supervisor_status.json"):
        try:
            status = json.loads(path.read_text())
            record = {key: status.get(key) for key in (
                "status", "updated_at", "restart_count", "last_exit_code", "daemon_pid",
                "daemon_pid_alive", "active_worker_count", "log_path")}
            record["projection"] = str(path)
            supervisors.append(record)
            if status.get("status") in {"restarting", "failed", "error", "stalled"}:
                notices.append({"reason": "native_supervisor_requires_attention", **record})
        except (OSError, ValueError, TypeError):
            notices.append({"reason": "supervisor_projection_unreadable", "projection": str(path)})
    paths = list((lane / "state").glob("*_database_portal_attempts/*/portal-task-state.json"))
    dated = []
    for path in paths:
        try:
            if path.resolve().is_relative_to(lane):
                dated.append((path.stat().st_mtime, path))
        except OSError:
            continue  # Native attempt cleanup can remove a historical projection.
    for _, path in sorted(dated, reverse=True)[:100]:
        try:
            if path.stat().st_size > 4 * 1024 * 1024:
                raise ValueError("worker state projection exceeds observation bound")
            state = json.loads(path.read_text())
            if not isinstance(state, dict):
                raise ValueError("worker state projection is not an object")
            record = {key: state.get(key) for key in (
                "active_task_id", "active_phase", "heartbeat_at", "last_progress_at",
                "active_phase_started_at", "active_worktree_path", "active_branch", "implementation_in_progress",
                "last_implementation_task_id", "last_implementation_returncode",
                "last_validation_returncode", "last_merge_returncode", "last_merge_commit")}
            record["projection"] = str(path)
            record["heartbeat_age_seconds"] = _age(state.get("heartbeat_at"), clock)
            record["progress_age_seconds"] = _age(state.get("last_progress_at"), clock)
            active = bool(state.get("active_task_id"))
            record["active_projection"] = active
            record.update(_binding_match(path, tasks))
            if record["authority_match"] == "current":
                matched_current.add(record["task_cid"])
                if not active:
                    notices.append({"reason": "current_owner_claim_projection_inactive",
                                    "task_cid": record["task_cid"], "projection": str(path)})
            log_path = Path(str(state.get("active_log_path") or state.get("last_implementation_log_path") or ""))
            if log_path.is_absolute() and log_path.resolve().is_relative_to(lane) and log_path.is_file():
                info = log_path.stat()
                record.update(log_path=str(log_path), log_bytes=info.st_size,
                              log_age_seconds=round(max(0.0, clock - info.st_mtime), 1))
            heartbeat_age = record["heartbeat_age_seconds"]
            if active and record["authority_match"] != "historical" and (heartbeat_age is None or heartbeat_age > stale_seconds):
                notices.append({"task": state["active_task_id"], "reason": "active_projection_heartbeat_missing_or_stale",
                                "projection": str(path), "heartbeat_age_seconds": heartbeat_age,
                                "authority_match": record["authority_match"]})
            records.append(record)
        except (OSError, ValueError, TypeError) as exc:
            notices.append({"reason": "worker_projection_unreadable", "projection": str(path), "error_type": type(exc).__name__})
    for cid, task in (tasks or {}).items():
        if task is not None and task.get("status") == "in_progress" and cid not in matched_current:
            notices.append({"reason": "current_owner_claim_projection_unconfirmed",
                            "task": task.get("task_alias"), "task_cid": cid})
    return {"observed_at": datetime.fromtimestamp(clock, timezone.utc).isoformat(),
            "authoritative": False, "supervisors": supervisors, "attempts": records, "notices": notices,
            "owner_tasks_supplied": authoritative_tasks is not None,
            "projection_count": len(paths), "projection_limit": 100}
