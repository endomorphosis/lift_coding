"""Tests for persisted AI history index storage."""

from datetime import UTC, datetime, timedelta
import uuid

from handsfree.db import init_db
from handsfree.db.ai_history_index import (
    get_ai_history_records,
    prune_ai_history_records,
    prune_ai_history_records_to_limit,
    store_ai_history_record,
)


def test_store_ai_history_record_is_idempotent_for_same_user_capability_and_cid() -> None:
    db = init_db(":memory:")
    user_id = str(uuid.uuid4())

    first = store_ai_history_record(
        db,
        user_id=user_id,
        capability_id="github.check.failure_rag_explain",
        repo="openai/example",
        pr_number=101,
        failure_target="CI Linux",
        failure_target_type="workflow",
        ipfs_cid="bafy-one",
    )
    second = store_ai_history_record(
        db,
        user_id=user_id,
        capability_id="github.check.failure_rag_explain",
        repo="openai/example",
        pr_number=101,
        failure_target="CI Linux",
        failure_target_type="workflow",
        ipfs_cid="bafy-one",
    )

    records = get_ai_history_records(
        db,
        user_id=user_id,
        capability_id="github.check.failure_rag_explain",
    )

    assert first.id == second.id
    assert [record.ipfs_cid for record in records] == ["bafy-one"]
    db.close()


def test_get_ai_history_records_filters_by_repo_target_and_pr() -> None:
    db = init_db(":memory:")
    user_id = str(uuid.uuid4())

    store_ai_history_record(
        db,
        user_id=user_id,
        capability_id="github.check.failure_rag_explain",
        repo="openai/example",
        pr_number=101,
        failure_target="CI Linux",
        failure_target_type="workflow",
        ipfs_cid="bafy-keep",
    )
    store_ai_history_record(
        db,
        user_id=user_id,
        capability_id="github.check.failure_rag_explain",
        repo="openai/example",
        pr_number=125,
        failure_target="CI Linux",
        failure_target_type="workflow",
        ipfs_cid="bafy-exclude-pr",
    )
    store_ai_history_record(
        db,
        user_id=user_id,
        capability_id="github.check.failure_rag_explain",
        repo="openai/example",
        pr_number=100,
        failure_target="Unit Tests",
        failure_target_type="check",
        ipfs_cid="bafy-wrong-target",
    )

    records = get_ai_history_records(
        db,
        user_id=user_id,
        capability_id="github.check.failure_rag_explain",
        repo="openai/example",
        failure_target="CI Linux",
        failure_target_type="workflow",
        exclude_pr_number=125,
    )

    assert [record.ipfs_cid for record in records] == ["bafy-keep"]
    db.close()


def test_prune_ai_history_records_removes_old_rows() -> None:
    db = init_db(":memory:")
    user_id = str(uuid.uuid4())

    old_record = store_ai_history_record(
        db,
        user_id=user_id,
        capability_id="github.check.failure_rag_explain",
        repo="openai/example",
        pr_number=100,
        failure_target="CI Linux",
        failure_target_type="workflow",
        ipfs_cid="bafy-old",
    )
    store_ai_history_record(
        db,
        user_id=user_id,
        capability_id="github.check.failure_rag_explain",
        repo="openai/example",
        pr_number=101,
        failure_target="CI Linux",
        failure_target_type="workflow",
        ipfs_cid="bafy-new",
    )
    old_time = datetime.now(UTC) - timedelta(days=31)
    db.execute("UPDATE ai_history_index SET created_at = ? WHERE id = ?", [old_time, old_record.id])

    deleted = prune_ai_history_records(db, older_than_days=30)
    records = get_ai_history_records(
        db,
        user_id=user_id,
        capability_id="github.check.failure_rag_explain",
    )

    assert deleted == 1
    assert [record.ipfs_cid for record in records] == ["bafy-new"]
    db.close()


def test_store_ai_history_record_can_prune_via_env(monkeypatch) -> None:
    db = init_db(":memory:")
    user_id = str(uuid.uuid4())

    stale = store_ai_history_record(
        db,
        user_id=user_id,
        capability_id="github.check.failure_rag_explain",
        repo="openai/example",
        pr_number=100,
        failure_target="CI Linux",
        failure_target_type="workflow",
        ipfs_cid="bafy-stale",
    )
    stale_time = datetime.now(UTC) - timedelta(days=8)
    db.execute("UPDATE ai_history_index SET created_at = ? WHERE id = ?", [stale_time, stale.id])

    monkeypatch.setenv("HANDSFREE_AI_HISTORY_RETENTION_DAYS", "7")
    store_ai_history_record(
        db,
        user_id=user_id,
        capability_id="github.check.failure_rag_explain",
        repo="openai/example",
        pr_number=101,
        failure_target="CI Linux",
        failure_target_type="workflow",
        ipfs_cid="bafy-fresh",
    )

    records = get_ai_history_records(
        db,
        user_id=user_id,
        capability_id="github.check.failure_rag_explain",
    )

    assert [record.ipfs_cid for record in records] == ["bafy-fresh"]
    db.close()


def test_prune_ai_history_records_to_limit_keeps_newest_records() -> None:
    db = init_db(":memory:")
    user_id = str(uuid.uuid4())

    first = store_ai_history_record(
        db,
        user_id=user_id,
        capability_id="github.check.failure_rag_explain",
        repo="openai/example",
        pr_number=100,
        failure_target="CI Linux",
        failure_target_type="workflow",
        ipfs_cid="bafy-oldest",
    )
    second = store_ai_history_record(
        db,
        user_id=user_id,
        capability_id="github.check.failure_rag_explain",
        repo="openai/example",
        pr_number=101,
        failure_target="CI Linux",
        failure_target_type="workflow",
        ipfs_cid="bafy-middle",
    )
    third = store_ai_history_record(
        db,
        user_id=user_id,
        capability_id="github.check.failure_rag_explain",
        repo="openai/example",
        pr_number=102,
        failure_target="CI Linux",
        failure_target_type="workflow",
        ipfs_cid="bafy-newest",
    )
    old_time = datetime.now(UTC) - timedelta(days=1)
    older_time = datetime.now(UTC) - timedelta(days=2)
    db.execute("UPDATE ai_history_index SET created_at = ? WHERE id = ?", [older_time, first.id])
    db.execute("UPDATE ai_history_index SET created_at = ? WHERE id = ?", [old_time, second.id])
    db.execute("UPDATE ai_history_index SET created_at = ? WHERE id = ?", [datetime.now(UTC), third.id])

    deleted = prune_ai_history_records_to_limit(
        db,
        user_id=user_id,
        capability_id="github.check.failure_rag_explain",
        max_records=2,
    )
    records = get_ai_history_records(
        db,
        user_id=user_id,
        capability_id="github.check.failure_rag_explain",
    )

    assert deleted == 1
    assert [record.ipfs_cid for record in records] == ["bafy-newest", "bafy-middle"]
    db.close()


def test_store_ai_history_record_can_prune_to_env_max_records(monkeypatch) -> None:
    db = init_db(":memory:")
    user_id = str(uuid.uuid4())
    monkeypatch.setenv("HANDSFREE_AI_HISTORY_MAX_RECORDS_PER_USER", "2")

    store_ai_history_record(
        db,
        user_id=user_id,
        capability_id="github.check.failure_rag_explain",
        repo="openai/example",
        pr_number=100,
        failure_target="CI Linux",
        failure_target_type="workflow",
        ipfs_cid="bafy-one",
    )
    store_ai_history_record(
        db,
        user_id=user_id,
        capability_id="github.check.failure_rag_explain",
        repo="openai/example",
        pr_number=101,
        failure_target="CI Linux",
        failure_target_type="workflow",
        ipfs_cid="bafy-two",
    )
    store_ai_history_record(
        db,
        user_id=user_id,
        capability_id="github.check.failure_rag_explain",
        repo="openai/example",
        pr_number=102,
        failure_target="CI Linux",
        failure_target_type="workflow",
        ipfs_cid="bafy-three",
    )

    records = get_ai_history_records(
        db,
        user_id=user_id,
        capability_id="github.check.failure_rag_explain",
    )

    assert [record.ipfs_cid for record in records] == ["bafy-three", "bafy-two"]
    db.close()
