"""Shared helpers for discovering persisted AI history artifacts."""

from __future__ import annotations

from typing import Any

import duckdb

from handsfree.db.action_logs import get_action_logs
from handsfree.db.ai_history_index import get_ai_history_records


def discover_failure_history_cids(
    conn: duckdb.DuckDBPyConnection | None,
    *,
    user_id: str | None,
    repo: str | None,
    pr_number: int | None,
    workflow_name: str | None = None,
    check_name: str | None = None,
    failure_target: str | None = None,
    failure_target_type: str | None = None,
    limit: int = 50,
) -> list[str]:
    """Discover recent persisted failure-analysis outputs to reuse as history."""
    if conn is None or not user_id or not repo:
        return []

    derived_failure_target = failure_target
    derived_failure_target_type = failure_target_type
    if workflow_name:
        derived_failure_target = workflow_name
        derived_failure_target_type = "workflow"
    elif check_name:
        derived_failure_target = check_name
        derived_failure_target_type = "check"

    indexed = get_ai_history_records(
        conn,
        user_id=user_id,
        capability_id="github.check.failure_rag_explain",
        repo=repo,
        failure_target=derived_failure_target,
        failure_target_type=derived_failure_target_type,
        exclude_pr_number=pr_number,
        limit=limit,
    )
    if indexed:
        return [record.ipfs_cid for record in indexed]

    logs = get_action_logs(conn, user_id=user_id, limit=limit)
    discovered: list[str] = []
    seen: set[str] = set()

    for log in logs:
        if log.action_type != "ai.execute.github.check.failure_rag_explain" or not log.ok:
            continue
        if not isinstance(log.result, dict):
            continue

        output_payload = _as_dict(log.result.get("output"))
        typed_payload = _as_dict(log.result.get("typed_output"))
        cid = output_payload.get("ipfs_cid") or typed_payload.get("ipfs_cid")
        if not isinstance(cid, str) or not cid.strip() or cid in seen:
            continue

        logged_repo = output_payload.get("repo") or typed_payload.get("repo")
        if logged_repo != repo:
            continue

        logged_pr = output_payload.get("pr_number") or typed_payload.get("pr_number")
        if pr_number is not None and logged_pr == pr_number:
            continue

        logged_target = output_payload.get("failure_target") or typed_payload.get("failure_target")
        logged_target_type = output_payload.get("failure_target_type") or typed_payload.get(
            "failure_target_type"
        )
        if derived_failure_target and logged_target != derived_failure_target:
            continue
        if derived_failure_target_type and logged_target_type != derived_failure_target_type:
            continue

        discovered.append(cid)
        seen.add(cid)

    return discovered


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
