"""AI backend policy observability helpers."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
import os

import duckdb

from handsfree.db.action_logs import get_action_logs
from handsfree.db.ai_backend_policy_snapshots import get_latest_ai_backend_policy_snapshot
from handsfree.github.auth import _is_live_mode_requested, resolve_github_auth_source
from handsfree.models import (
    AICapabilityUsageCount,
    AILatestSnapshotInfo,
    AIRemapCount,
    AIBackendPolicyBucketReport,
    AIBackendPolicyConfig,
    AIBackendPolicyHistoryBucket,
    AIBackendPolicyHistoryReport,
    AIBackendPolicyReport,
    AISnapshotHealth,
    AISnapshotPolicyConfig,
    AISnapshotSummary,
    AITopCapabilities,
    AIBackendPolicyWindow,
)

from .policy import get_ai_backend_policy


def _get_optional_non_negative_int_env(name: str) -> int | None:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return None
    try:
        parsed = int(raw_value)
    except ValueError:
        return None
    if parsed < 0:
        return None
    return parsed


def build_ai_backend_policy_config() -> AIBackendPolicyConfig:
    policy = get_ai_backend_policy()
    return AIBackendPolicyConfig(
        summary_backend=policy.summary_backend,
        failure_backend=policy.failure_backend,
        github_auth_source=resolve_github_auth_source(),
        github_live_mode_requested=_is_live_mode_requested(),
        snapshot_retention_days=_get_optional_non_negative_int_env(
            "HANDSFREE_AI_POLICY_SNAPSHOT_RETENTION_DAYS"
        ),
        snapshot_max_records_per_user=_get_optional_non_negative_int_env(
            "HANDSFREE_AI_POLICY_SNAPSHOT_MAX_RECORDS_PER_USER"
        ),
        snapshot_min_interval_seconds=_get_optional_non_negative_int_env(
            "HANDSFREE_AI_POLICY_SNAPSHOT_MIN_INTERVAL_SECONDS"
        ),
    )


def build_latest_snapshot_info(
    conn: duckdb.DuckDBPyConnection,
    *,
    user_id: str,
) -> AILatestSnapshotInfo | None:
    snapshot = get_latest_ai_backend_policy_snapshot(conn, user_id=user_id)
    if snapshot is None:
        return None
    created_at = snapshot.created_at
    if created_at.tzinfo is None:
        local_tz = datetime.now().astimezone().tzinfo or UTC
        created_at = created_at.replace(tzinfo=local_tz).astimezone(UTC)
    age_seconds = max(
        0,
        int((datetime.now(UTC) - created_at.astimezone(UTC)).total_seconds()),
    )
    freshness_threshold = _get_optional_non_negative_int_env(
        "HANDSFREE_AI_POLICY_SNAPSHOT_MIN_INTERVAL_SECONDS"
    )
    if freshness_threshold is None:
        freshness_threshold = 3600
    return AILatestSnapshotInfo(
        id=snapshot.id,
        created_at=created_at,
        age_seconds=age_seconds,
        freshness_threshold_seconds=freshness_threshold,
        freshness="fresh" if age_seconds <= freshness_threshold else "stale",
    )


def build_snapshot_health(latest_snapshot: AILatestSnapshotInfo | None) -> AISnapshotHealth:
    if latest_snapshot is None:
        return AISnapshotHealth(status="missing")
    if latest_snapshot.freshness == "fresh":
        return AISnapshotHealth(status="healthy")
    return AISnapshotHealth(status="stale")


def build_snapshot_policy_config(policy: AIBackendPolicyConfig) -> AISnapshotPolicyConfig:
    return AISnapshotPolicyConfig(
        retention_days=policy.snapshot_retention_days,
        max_records_per_user=policy.snapshot_max_records_per_user,
        min_interval_seconds=policy.snapshot_min_interval_seconds,
    )


def build_snapshot_summary(
    *,
    policy: AIBackendPolicyConfig,
    latest_snapshot: AILatestSnapshotInfo | None,
    snapshot_capture: dict[str, object] | None = None,
    next_capture: dict[str, object] | None = None,
) -> AISnapshotSummary:
    return AISnapshotSummary(
        latest_snapshot=latest_snapshot,
        snapshot_health=build_snapshot_health(latest_snapshot),
        policy=build_snapshot_policy_config(policy),
        snapshot_capture=snapshot_capture,
        next_capture=next_capture,
    )


def build_ai_backend_policy_history_report(
    conn: duckdb.DuckDBPyConnection,
    *,
    user_id: str,
    window_hours: int = 24,
    bucket_hours: int = 1,
    limit: int = 1000,
) -> AIBackendPolicyHistoryReport:
    """Return bucketed historical backend-policy activity from action logs."""
    logs = get_action_logs(conn, user_id=user_id, limit=limit)
    now = datetime.now(UTC)
    window_start = now - timedelta(hours=window_hours)

    buckets: list[AIBackendPolicyHistoryBucket] = []
    current_start = window_start
    while current_start < now:
        current_end = min(current_start + timedelta(hours=bucket_hours), now)
        ai_execute_logs = 0
        policy_applied_count = 0
        remap_counter: Counter[str] = Counter()

        for log in logs:
            if not log.action_type.startswith("ai.execute."):
                continue
            log_time = log.created_at.astimezone(UTC)
            if not (current_start <= log_time < current_end):
                continue
            ai_execute_logs += 1
            result = log.result if isinstance(log.result, dict) else {}
            policy_resolution = result.get("policy_resolution")
            if not isinstance(policy_resolution, dict):
                continue
            if not policy_resolution.get("policy_applied"):
                continue
            policy_applied_count += 1
            requested = policy_resolution.get("requested_workflow") or "unknown"
            resolved = policy_resolution.get("resolved_workflow") or "unknown"
            remap_counter[f"{requested}->{resolved}"] += 1

        buckets.append(
            AIBackendPolicyHistoryBucket(
                started_at=current_start,
                ended_at=current_end,
                ai_execute_logs=ai_execute_logs,
                policy_applied_count=policy_applied_count,
                remap_counts=dict(sorted(remap_counter.items())),
            )
        )
        current_start = current_end

    policy = build_ai_backend_policy_config()
    latest_snapshot = build_latest_snapshot_info(conn, user_id=user_id)
    return AIBackendPolicyHistoryReport(
        report_generated_at=now,
        policy=policy,
        window_hours=window_hours,
        bucket_hours=bucket_hours,
        buckets=buckets,
        snapshot_summary=build_snapshot_summary(policy=policy, latest_snapshot=latest_snapshot),
        latest_snapshot=latest_snapshot,
        snapshot_health=build_snapshot_health(latest_snapshot),
    )


def build_ai_backend_policy_report(
    conn: duckdb.DuckDBPyConnection,
    *,
    user_id: str,
    limit: int = 200,
) -> AIBackendPolicyReport:
    """Return current backend policy plus recent remap counts from action logs."""
    logs = get_action_logs(conn, user_id=user_id, limit=limit)
    now = datetime.now(UTC)

    remap_counter: Counter[str] = Counter()
    remapped_capability_counter: Counter[str] = Counter()
    direct_capability_counter: Counter[str] = Counter()
    requested_workflow_counter: Counter[str] = Counter()
    resolved_workflow_counter: Counter[str] = Counter()
    action_counter: Counter[str] = Counter()
    applied_count = 0
    bucket_counters: dict[str, dict[str, Counter[str] | int]] = {
        "last_hour": {
            "action_counter": Counter(),
            "remap_counter": Counter(),
            "remapped_capability_counter": Counter(),
            "direct_capability_counter": Counter(),
            "requested_workflow_counter": Counter(),
            "resolved_workflow_counter": Counter(),
            "applied_count": 0,
        },
        "last_24_hours": {
            "action_counter": Counter(),
            "remap_counter": Counter(),
            "remapped_capability_counter": Counter(),
            "direct_capability_counter": Counter(),
            "requested_workflow_counter": Counter(),
            "resolved_workflow_counter": Counter(),
            "applied_count": 0,
        },
    }

    for log in logs:
        if not log.action_type.startswith("ai.execute."):
            continue
        action_counter[log.action_type] += 1
        age = now - log.created_at.astimezone(UTC)
        matching_buckets = []
        if age <= timedelta(hours=1):
            matching_buckets.append("last_hour")
        if age <= timedelta(hours=24):
            matching_buckets.append("last_24_hours")
        for bucket_name in matching_buckets:
            bucket_counters[bucket_name]["action_counter"][log.action_type] += 1
        result = log.result if isinstance(log.result, dict) else {}
        policy_resolution = result.get("policy_resolution")
        capability_id = None
        if isinstance(result, dict):
            raw_capability_id = result.get("capability_id")
            if isinstance(raw_capability_id, str) and raw_capability_id:
                capability_id = raw_capability_id
        if capability_id is None:
            capability_id = log.action_type.removeprefix("ai.execute.")
        if not isinstance(policy_resolution, dict):
            direct_capability_counter[capability_id] += 1
            for bucket_name in matching_buckets:
                bucket_counters[bucket_name]["direct_capability_counter"][capability_id] += 1
            continue
        if not policy_resolution.get("policy_applied"):
            direct_capability_counter[capability_id] += 1
            for bucket_name in matching_buckets:
                bucket_counters[bucket_name]["direct_capability_counter"][capability_id] += 1
            continue
        applied_count += 1
        remapped_capability_counter[capability_id] += 1
        requested = policy_resolution.get("requested_workflow") or "unknown"
        resolved = policy_resolution.get("resolved_workflow") or "unknown"
        remap_key = f"{requested}->{resolved}"
        remap_counter[remap_key] += 1
        requested_workflow_counter[requested] += 1
        resolved_workflow_counter[resolved] += 1
        for bucket_name in matching_buckets:
            bucket_counters[bucket_name]["applied_count"] += 1
            bucket_counters[bucket_name]["remap_counter"][remap_key] += 1
            bucket_counters[bucket_name]["remapped_capability_counter"][capability_id] += 1
            bucket_counters[bucket_name]["requested_workflow_counter"][requested] += 1
            bucket_counters[bucket_name]["resolved_workflow_counter"][resolved] += 1

    def _top_entries(counter: Counter[str], max_items: int = 5) -> list[AICapabilityUsageCount]:
        return [
            AICapabilityUsageCount(capability_id=capability_id, count=count)
            for capability_id, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))[
                :max_items
            ]
        ]

    def _top_remaps(counter: Counter[str], max_items: int = 5) -> list[AIRemapCount]:
        return [
            AIRemapCount(remap_key=remap_key, count=count)
            for remap_key, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))[
                :max_items
            ]
        ]

    policy = build_ai_backend_policy_config()
    latest_snapshot = build_latest_snapshot_info(conn, user_id=user_id)
    return AIBackendPolicyReport(
        report_generated_at=now,
        policy=policy,
        recent_window=AIBackendPolicyWindow(
            log_limit=limit,
            ai_execute_logs=sum(action_counter.values()),
            policy_applied_count=applied_count,
        ),
        time_buckets={
            bucket_name: AIBackendPolicyBucketReport(
                ai_execute_logs=sum(bucket_data["action_counter"].values()),
                policy_applied_count=int(bucket_data["applied_count"]),
                remapped_capability_counts=dict(
                    sorted(bucket_data["remapped_capability_counter"].items())
                ),
                direct_capability_counts=dict(
                    sorted(bucket_data["direct_capability_counter"].items())
                ),
                requested_workflow_counts=dict(
                    sorted(bucket_data["requested_workflow_counter"].items())
                ),
                resolved_workflow_counts=dict(
                    sorted(bucket_data["resolved_workflow_counter"].items())
                ),
                remap_counts=dict(sorted(bucket_data["remap_counter"].items())),
                action_counts=dict(sorted(bucket_data["action_counter"].items())),
            )
            for bucket_name, bucket_data in bucket_counters.items()
        },
        top_capabilities=AITopCapabilities(
            overall=_top_entries(
                Counter(remapped_capability_counter) + Counter(direct_capability_counter)
            ),
            remapped=_top_entries(remapped_capability_counter),
            direct=_top_entries(direct_capability_counter),
        ),
        top_remaps=_top_remaps(remap_counter),
        remapped_capability_counts=dict(sorted(remapped_capability_counter.items())),
        direct_capability_counts=dict(sorted(direct_capability_counter.items())),
        requested_workflow_counts=dict(sorted(requested_workflow_counter.items())),
        resolved_workflow_counts=dict(sorted(resolved_workflow_counter.items())),
        remap_counts=dict(sorted(remap_counter.items())),
        action_counts=dict(sorted(action_counter.items())),
        snapshot_summary=build_snapshot_summary(policy=policy, latest_snapshot=latest_snapshot),
        latest_snapshot=latest_snapshot,
        snapshot_health=build_snapshot_health(latest_snapshot),
    )
