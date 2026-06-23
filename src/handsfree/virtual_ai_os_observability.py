"""Stable observability artifacts for virtual AI OS supervisor reconciliation."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, Mapping

VIRTUAL_AI_OS_OBSERVABILITY_ARTIFACT_CONTRACT_ID = (
    "handsfree.virtual-ai-os/observability-artifacts@0.1.0"
)

VIRTUAL_AI_OS_OBSERVABILITY_ARTIFACT_TYPES: tuple[str, ...] = (
    "policy_decision",
    "placement_change",
    "remote_execution_receipt",
    "validation_failure",
    "rollback_event",
)

VIRTUAL_AI_OS_OBSERVABILITY_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "policy_decision": (
        "artifact_id",
        "task_id",
        "correlation_id",
        "outcome",
        "policy_ref",
        "reason",
        "decided_at",
    ),
    "placement_change": (
        "artifact_id",
        "task_id",
        "correlation_id",
        "from_placement",
        "to_placement",
        "changed_at",
        "reason",
    ),
    "remote_execution_receipt": (
        "artifact_id",
        "task_id",
        "correlation_id",
        "remote_surface",
        "operation",
        "status",
        "receipt_ref",
        "issued_at",
    ),
    "validation_failure": (
        "artifact_id",
        "task_id",
        "correlation_id",
        "validator",
        "failure_code",
        "message",
        "failed_at",
    ),
    "rollback_event": (
        "artifact_id",
        "task_id",
        "correlation_id",
        "rollback_action",
        "reason",
        "triggered_at",
    ),
}


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _artifact_id(artifact_type: str, payload: Mapping[str, Any]) -> str:
    seed = {
        key: value
        for key, value in payload.items()
        if key not in {"artifact_id", "observed_at"}
    }
    digest = hashlib.sha256(_stable_json(seed).encode("utf-8")).hexdigest()
    return f"sha256:vai-observability:{artifact_type}:{digest}"


def _timestamp(value: str | None) -> str:
    return value or datetime.now(UTC).isoformat()


def _base_artifact(
    *,
    artifact_type: str,
    task_id: str,
    correlation_id: str,
    observed_at: str | None,
    parent_artifact_ids: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        "contract_id": VIRTUAL_AI_OS_OBSERVABILITY_ARTIFACT_CONTRACT_ID,
        "artifact_type": artifact_type,
        "task_id": task_id,
        "correlation_id": correlation_id,
        "observed_at": _timestamp(observed_at),
        "parent_artifact_ids": list(parent_artifact_ids),
    }


def _finalize_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    artifact["artifact_id"] = _artifact_id(str(artifact["artifact_type"]), artifact)
    return artifact


def build_virtual_ai_os_policy_decision_artifact(
    *,
    task_id: str,
    correlation_id: str,
    outcome: str,
    policy_ref: str,
    reason: str,
    decided_at: str | None = None,
    actor: str = "handsfree.policy",
    evidence_refs: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Capture a policy decision as a retryable supervisor artifact."""

    artifact = _base_artifact(
        artifact_type="policy_decision",
        task_id=task_id,
        correlation_id=correlation_id,
        observed_at=decided_at,
    )
    artifact.update(
        {
            "outcome": outcome,
            "policy_ref": policy_ref,
            "reason": reason,
            "actor": actor,
            "decided_at": artifact["observed_at"],
            "evidence_refs": dict(evidence_refs or {}),
        }
    )
    return _finalize_artifact(artifact)


def build_virtual_ai_os_placement_change_artifact(
    *,
    task_id: str,
    correlation_id: str,
    from_placement: str,
    to_placement: str,
    reason: str,
    changed_at: str | None = None,
    placement_ref: str | None = None,
    parent_artifact_ids: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Capture a compute/runtime placement transition."""

    artifact = _base_artifact(
        artifact_type="placement_change",
        task_id=task_id,
        correlation_id=correlation_id,
        observed_at=changed_at,
        parent_artifact_ids=parent_artifact_ids,
    )
    artifact.update(
        {
            "from_placement": from_placement,
            "to_placement": to_placement,
            "reason": reason,
            "changed_at": artifact["observed_at"],
            "placement_ref": placement_ref,
        }
    )
    return _finalize_artifact(artifact)


def build_virtual_ai_os_remote_execution_receipt_artifact(
    *,
    task_id: str,
    correlation_id: str,
    remote_surface: str,
    operation: str,
    status: str,
    issued_at: str | None = None,
    receipt_ref: str | None = None,
    stream_refs: tuple[str, ...] = (),
    parent_artifact_ids: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Capture a remote execution receipt and its stream/provenance refs."""

    artifact = _base_artifact(
        artifact_type="remote_execution_receipt",
        task_id=task_id,
        correlation_id=correlation_id,
        observed_at=issued_at,
        parent_artifact_ids=parent_artifact_ids,
    )
    artifact.update(
        {
            "remote_surface": remote_surface,
            "operation": operation,
            "status": status,
            "issued_at": artifact["observed_at"],
            "receipt_ref": receipt_ref,
            "stream_refs": list(stream_refs),
        }
    )
    return _finalize_artifact(artifact)


def build_virtual_ai_os_validation_failure_artifact(
    *,
    task_id: str,
    correlation_id: str,
    validator: str,
    failure_code: str,
    message: str,
    failed_at: str | None = None,
    retryable: bool = True,
    evidence_refs: Mapping[str, str] | None = None,
    parent_artifact_ids: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Capture validation failure details without requiring log archaeology."""

    artifact = _base_artifact(
        artifact_type="validation_failure",
        task_id=task_id,
        correlation_id=correlation_id,
        observed_at=failed_at,
        parent_artifact_ids=parent_artifact_ids,
    )
    artifact.update(
        {
            "validator": validator,
            "failure_code": failure_code,
            "message": message,
            "failed_at": artifact["observed_at"],
            "retryable": retryable,
            "evidence_refs": dict(evidence_refs or {}),
        }
    )
    return _finalize_artifact(artifact)


def build_virtual_ai_os_rollback_event_artifact(
    *,
    task_id: str,
    correlation_id: str,
    rollback_action: str,
    reason: str,
    triggered_at: str | None = None,
    restored_placement: str | None = None,
    restored_ref: str | None = None,
    parent_artifact_ids: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Capture rollback/recovery actions for later reconciliation."""

    artifact = _base_artifact(
        artifact_type="rollback_event",
        task_id=task_id,
        correlation_id=correlation_id,
        observed_at=triggered_at,
        parent_artifact_ids=parent_artifact_ids,
    )
    artifact.update(
        {
            "rollback_action": rollback_action,
            "reason": reason,
            "triggered_at": artifact["observed_at"],
            "restored_placement": restored_placement,
            "restored_ref": restored_ref,
        }
    )
    return _finalize_artifact(artifact)


def build_virtual_ai_os_observability_bundle(
    *,
    task_id: str,
    correlation_id: str,
    artifacts: tuple[Mapping[str, Any], ...],
) -> dict[str, Any]:
    """Bundle ordered artifacts into one supervisor reconciliation record."""

    artifact_ids = [str(artifact["artifact_id"]) for artifact in artifacts]
    bundle_seed = {
        "task_id": task_id,
        "correlation_id": correlation_id,
        "artifact_ids": artifact_ids,
    }
    return {
        "contract_id": VIRTUAL_AI_OS_OBSERVABILITY_ARTIFACT_CONTRACT_ID,
        "bundle_id": _artifact_id("bundle", bundle_seed),
        "task_id": task_id,
        "correlation_id": correlation_id,
        "artifact_ids": artifact_ids,
        "artifacts": [dict(artifact) for artifact in artifacts],
        "supervisor_actions": {
            "retry_from": artifact_ids[-1] if artifact_ids else None,
            "reconcile_by": ["task_id", "correlation_id", "artifact_id"],
            "stable_artifact_types": list(VIRTUAL_AI_OS_OBSERVABILITY_ARTIFACT_TYPES),
        },
    }


def get_virtual_ai_os_observability_artifact_contract() -> dict[str, Any]:
    """Return the stable artifact schema advertised by configuration/docs."""

    return {
        "contract_id": VIRTUAL_AI_OS_OBSERVABILITY_ARTIFACT_CONTRACT_ID,
        "artifact_types": list(VIRTUAL_AI_OS_OBSERVABILITY_ARTIFACT_TYPES),
        "required_fields": {
            key: list(value)
            for key, value in VIRTUAL_AI_OS_OBSERVABILITY_REQUIRED_FIELDS.items()
        },
        "reconcile_keys": ["task_id", "correlation_id", "artifact_id"],
    }


__all__ = [
    "VIRTUAL_AI_OS_OBSERVABILITY_ARTIFACT_CONTRACT_ID",
    "VIRTUAL_AI_OS_OBSERVABILITY_ARTIFACT_TYPES",
    "VIRTUAL_AI_OS_OBSERVABILITY_REQUIRED_FIELDS",
    "build_virtual_ai_os_observability_bundle",
    "build_virtual_ai_os_placement_change_artifact",
    "build_virtual_ai_os_policy_decision_artifact",
    "build_virtual_ai_os_remote_execution_receipt_artifact",
    "build_virtual_ai_os_rollback_event_artifact",
    "build_virtual_ai_os_validation_failure_artifact",
    "get_virtual_ai_os_observability_artifact_contract",
]
