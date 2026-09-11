#!/usr/bin/env python3
"""Read native per-attempt worker projections; never mutate task authority."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import time


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


def observe_lane(lane, *, now=None, stale_seconds=1800):
    """Return bounded observations, keeping stale projections distinct from work.

    A worker heartbeat is activity evidence, not proof of useful task progress.
    Completed historical attempt files do not raise stale-worker notices.
    """
    lane = Path(lane).resolve()
    clock = time.time() if now is None else float(now)
    records, notices = [], []
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
                "active_phase_started_at", "implementation_in_progress",
                "last_implementation_task_id", "last_implementation_returncode",
                "last_validation_returncode", "last_merge_returncode", "last_merge_commit")}
            record["projection"] = str(path)
            record["heartbeat_age_seconds"] = _age(state.get("heartbeat_at"), clock)
            record["progress_age_seconds"] = _age(state.get("last_progress_at"), clock)
            active = bool(state.get("active_task_id"))
            record["active_projection"] = active
            log_path = Path(str(state.get("last_implementation_log_path") or ""))
            if log_path.is_absolute() and log_path.resolve().is_relative_to(lane) and log_path.is_file():
                info = log_path.stat()
                record.update(log_path=str(log_path), log_bytes=info.st_size,
                              log_age_seconds=round(max(0.0, clock - info.st_mtime), 1))
            heartbeat_age = record["heartbeat_age_seconds"]
            if active and (heartbeat_age is None or heartbeat_age > stale_seconds):
                notices.append({"task": state["active_task_id"], "reason": "active_projection_heartbeat_missing_or_stale",
                                "projection": str(path), "heartbeat_age_seconds": heartbeat_age})
            records.append(record)
        except (OSError, ValueError, TypeError) as exc:
            notices.append({"reason": "worker_projection_unreadable", "projection": str(path), "error_type": type(exc).__name__})
    return {"observed_at": datetime.fromtimestamp(clock, timezone.utc).isoformat(),
            "authoritative": False, "attempts": records, "notices": notices,
            "projection_count": len(paths), "projection_limit": 100}
