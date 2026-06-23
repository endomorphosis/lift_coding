from __future__ import annotations

import sys
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
        "merge_result": {"merged": False, "attempted": False, "reason": "lock_unavailable"},
    }

    selected = daemon._select_failed_merge_candidates_for_reconciliation(
        [conflict_event, transient_event],
        max_merges=0,
    )

    assert selected == [transient_event]


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
