"""Tests for shared AI history discovery helpers."""

import uuid

from handsfree.ai.history import discover_failure_history_cids
from handsfree.db import init_db
from handsfree.db.action_logs import write_action_log


def test_discover_failure_history_cids_filters_by_repo_and_target() -> None:
    db = init_db(":memory:")
    user_id = str(uuid.uuid4())

    write_action_log(
        db,
        user_id=user_id,
        action_type="ai.execute.github.check.failure_rag_explain",
        ok=True,
        result={
            "output": {
                "repo": "openai/example",
                "pr_number": 101,
                "failure_target": "CI Linux",
                "failure_target_type": "workflow",
                "ipfs_cid": "bafy-keep",
            }
        },
    )
    write_action_log(
        db,
        user_id=user_id,
        action_type="ai.execute.github.check.failure_rag_explain",
        ok=True,
        result={
            "output": {
                "repo": "openai/example",
                "pr_number": 125,
                "failure_target": "CI Linux",
                "failure_target_type": "workflow",
                "ipfs_cid": "bafy-same-pr",
            }
        },
    )
    write_action_log(
        db,
        user_id=user_id,
        action_type="ai.execute.github.check.failure_rag_explain",
        ok=True,
        result={
            "output": {
                "repo": "openai/example",
                "pr_number": 99,
                "failure_target": "unit tests",
                "failure_target_type": "check",
                "ipfs_cid": "bafy-wrong-target",
            }
        },
    )

    discovered = discover_failure_history_cids(
        db,
        user_id=user_id,
        repo="openai/example",
        pr_number=125,
        workflow_name="CI Linux",
    )

    assert discovered == ["bafy-keep"]
    db.close()


def test_discover_failure_history_cids_reads_typed_output_fallback() -> None:
    db = init_db(":memory:")
    user_id = str(uuid.uuid4())

    write_action_log(
        db,
        user_id=user_id,
        action_type="ai.execute.github.check.failure_rag_explain",
        ok=True,
        result={
            "typed_output": {
                "repo": "openai/example",
                "pr_number": 100,
                "failure_target": "unit tests",
                "failure_target_type": "check",
                "ipfs_cid": "bafy-typed",
            }
        },
    )

    discovered = discover_failure_history_cids(
        db,
        user_id=user_id,
        repo="openai/example",
        pr_number=125,
        check_name="unit tests",
    )

    assert discovered == ["bafy-typed"]
    db.close()
