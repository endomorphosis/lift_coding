"""AI backend policy observability helpers."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta

import duckdb

from handsfree.db.action_logs import get_action_logs
from handsfree.github.auth import _is_live_mode_requested, resolve_github_auth_source
from handsfree.models import (
    AICapabilityUsageCount,
    AIRemapCount,
    AIBackendPolicyBucketReport,
    AIBackendPolicyConfig,
    AIBackendPolicyHistoryBucket,
    AIBackendPolicyHistoryReport,
    AIBackendPolicyReport,
    AITopCapabilities,
    AIBackendPolicyWindow,
)

from .policy import get_ai_backend_policy


def build_ai_backend_policy_history_report(
    conn: duckdb.DuckDBPyConnection,
    *,
    user_id: str,
    window_hours: int = 24,
    bucket_hours: int = 1,
    limit: int = 1000,
) -> AIBackendPolicyHistoryReport:
    """Return bucketed historical backend-policy activity from action logs."""
    policy = get_ai_backend_policy()
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

    return AIBackendPolicyHistoryReport(
        policy=AIBackendPolicyConfig(
            summary_backend=policy.summary_backend,
            failure_backend=policy.failure_backend,
            github_auth_source=resolve_github_auth_source(),
            github_live_mode_requested=_is_live_mode_requested(),
        ),
        window_hours=window_hours,
        bucket_hours=bucket_hours,
        buckets=buckets,
    )


def build_ai_backend_policy_report(
    conn: duckdb.DuckDBPyConnection,
    *,
    user_id: str,
    limit: int = 200,
) -> AIBackendPolicyReport:
    """Return current backend policy plus recent remap counts from action logs."""
    policy = get_ai_backend_policy()
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

    return AIBackendPolicyReport(
        policy=AIBackendPolicyConfig(
            summary_backend=policy.summary_backend,
            failure_backend=policy.failure_backend,
            github_auth_source=resolve_github_auth_source(),
            github_live_mode_requested=_is_live_mode_requested(),
        ),
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
    )
