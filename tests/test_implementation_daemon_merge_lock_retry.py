from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"


def _daemon_class():
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (
        PortalImplementationDaemon,
    )

    return PortalImplementationDaemon


def test_transient_merge_lock_is_retryable_but_not_a_real_merge_conflict():
    daemon = _daemon_class()
    transient_merge_lock = {"merged": False, "attempted": False, "reason": "lock_exists"}
    real_conflict = {"merged": False, "attempted": True, "reason": "merge_conflict"}

    assert daemon._merge_result_needs_reconciliation(transient_merge_lock)
    assert daemon._merge_result_is_transient_lock_deferral(transient_merge_lock)
    assert daemon._merge_result_needs_reconciliation(real_conflict)
    assert not daemon._merge_result_is_transient_lock_deferral(real_conflict)


def test_merge_lock_retry_queue_runs_one_transient_retry_when_generic_reconciliation_is_disabled():
    daemon = _daemon_class()
    conflict_event = {
        "task_id": "VAI-010",
        "merge_result": {"merged": False, "attempted": True, "reason": "merge_conflict"},
    }
    transient_event = {
        "task_id": "VAI-011",
        "timestamp": "2026-06-23T15:00:00+00:00",
        "merge_result": {"merged": False, "attempted": False, "reason": "lock_unavailable"},
    }
    now_ts = datetime(2026, 6, 23, 15, 5, tzinfo=timezone.utc).timestamp()

    selected = daemon._select_failed_merge_candidates_for_reconciliation(
        [conflict_event, transient_event],
        max_merges=0,
        now_ts=now_ts,
    )

    assert selected == [transient_event]


def test_stale_transient_merge_lock_is_not_retried_when_reconciliation_is_disabled():
    daemon = _daemon_class()
    transient_event = {
        "task_id": "VAI-214",
        "timestamp": "2026-06-09T09:07:16+00:00",
        "merge_result": {"merged": False, "attempted": False, "reason": "lock_exists"},
    }
    now_ts = datetime(2026, 6, 23, 15, 20, tzinfo=timezone.utc).timestamp()

    selected = daemon._select_failed_merge_candidates_for_reconciliation(
        [transient_event],
        max_merges=0,
        now_ts=now_ts,
    )

    assert selected == []


def test_prior_attempted_merge_failure_abandons_reconciliation_candidate(tmp_path):
    Daemon = _daemon_class()
    events_path = tmp_path / "events.jsonl"
    implementation_commit = "aafd833a5c426c1add54af5d4b689522c4ebbc1b"
    events = [
        {
            "timestamp": "2026-06-09T09:07:16+00:00",
            "type": "implementation_finished",
            "task_id": "VAI-214",
            "attempt": 1,
            "branch": "implementation/vai-214-attempt-1",
            "implementation_commit": implementation_commit,
            "merge_result": {"merged": False, "attempted": False, "reason": "lock_exists"},
            "validation_result": {"attempted": True, "passed": True},
        },
        {
            "timestamp": "2026-06-09T09:20:00+00:00",
            "type": "merge_reconciled",
            "task_id": "VAI-214",
            "attempt": 1,
            "branch": "implementation/vai-214-attempt-1",
            "implementation_commit": implementation_commit,
            "resolved": False,
            "merge_result": {"merged": False, "attempted": True, "reason": "main_checkout_dirty_conflict"},
        },
    ]
    events_path.write_text("\n".join(json.dumps(event) for event in events), encoding="utf-8")
    daemon = Daemon(
        todo_path=tmp_path / "todo.md",
        state_path=tmp_path / "state.json",
        strategy_path=tmp_path / "strategy.json",
        events_path=events_path,
        repo_root=tmp_path,
    )
    daemon._git_ref_is_ancestor = lambda _commit, _target: False

    assert daemon._failed_merge_candidates() == []


def test_failed_merge_reconciliation_ignores_removed_todo_tasks(tmp_path):
    Daemon = _daemon_class()
    todo_path = tmp_path / "todo.md"
    events_path = tmp_path / "events.jsonl"
    todo_path.write_text(
        """# Todos

## ACCEL-001 Current task

- Status: todo
- Priority: P1
- Track: runtime
- Depends on:
- Outputs: src/runtime.py
- Validation: test -f src/runtime.py
- Acceptance: Keep valid reconciliation candidates.

## ACCEL-888 Blocked stale task

- Status: blocked
- Priority: P2
- Track: ops
- Depends on:
- Outputs: cleanup-archive/stale.py
- Validation: true
- Acceptance: Blocked tasks should not be resurrected by merge reconciliation.
""",
        encoding="utf-8",
    )
    live_event = {
        "type": "implementation_finished",
        "task_id": "ACCEL-001",
        "attempt": 1,
        "branch": "implementation/accel-001-attempt-1",
        "implementation_commit": "1111111111111111111111111111111111111111",
        "validation_result": {"attempted": True, "passed": True},
        "merge_result": {"merged": False, "attempted": True, "reason": "merge_conflict"},
    }
    removed_event = {
        "type": "implementation_finished",
        "task_id": "ACCEL-999",
        "attempt": 1,
        "branch": "implementation/accel-999-attempt-1",
        "implementation_commit": "9999999999999999999999999999999999999999",
        "validation_result": {"attempted": True, "passed": True},
        "merge_result": {"merged": False, "attempted": True, "reason": "merge_conflict"},
    }
    blocked_event = {
        "type": "implementation_finished",
        "task_id": "ACCEL-888",
        "attempt": 1,
        "branch": "implementation/accel-888-attempt-1",
        "implementation_commit": "8888888888888888888888888888888888888888",
        "validation_result": {"attempted": True, "passed": True},
        "merge_result": {"merged": False, "attempted": True, "reason": "merge_conflict"},
    }
    events_path.write_text(
        "\n".join(json.dumps(event) for event in [removed_event, blocked_event, live_event]),
        encoding="utf-8",
    )
    daemon = Daemon(
        todo_path=todo_path,
        state_path=tmp_path / "state.json",
        strategy_path=tmp_path / "strategy.json",
        events_path=events_path,
        repo_root=tmp_path,
        task_header_prefix="## ACCEL-",
    )
    daemon._main_branch_name = lambda: "main"
    daemon._git_ref_is_ancestor = lambda _commit, _target: False

    assert daemon._failed_merge_candidates() == [live_event]


def test_duplicate_attempt_suppression_prioritizes_transient_locks_before_new_conflict_work():
    daemon = _daemon_class()
    conflict_event = {
        "task_id": "VAI-010",
        "merge_result": {"merged": False, "attempted": True, "reason": "merge_conflict"},
    }
    transient_event = {
        "task_id": "VAI-011",
        "merge_result": {"merged": False, "attempted": False, "reason": "lock_cleanup_failed"},
    }

    selected = daemon._select_failed_merge_candidates_for_reconciliation(
        [conflict_event, transient_event],
        max_merges=2,
    )

    assert selected == [transient_event, conflict_event]
