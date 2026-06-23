from __future__ import annotations

from handsfree.config import get_virtual_ai_os_observability_contract
from handsfree.virtual_ai_os_observability import (
    VIRTUAL_AI_OS_OBSERVABILITY_ARTIFACT_CONTRACT_ID,
    build_virtual_ai_os_observability_bundle,
    build_virtual_ai_os_placement_change_artifact,
    build_virtual_ai_os_policy_decision_artifact,
    build_virtual_ai_os_remote_execution_receipt_artifact,
    build_virtual_ai_os_rollback_event_artifact,
    build_virtual_ai_os_validation_failure_artifact,
    get_virtual_ai_os_observability_artifact_contract,
)


TASK_ID = "VAI-011"
CORRELATION_ID = "corr-vai-011"
OBSERVED_AT = "2026-06-23T00:00:00Z"


def test_virtual_ai_os_observability_contract_declares_reconcile_artifacts() -> None:
    contract = get_virtual_ai_os_observability_artifact_contract()

    assert contract["contract_id"] == VIRTUAL_AI_OS_OBSERVABILITY_ARTIFACT_CONTRACT_ID
    assert contract["artifact_types"] == [
        "policy_decision",
        "placement_change",
        "remote_execution_receipt",
        "validation_failure",
        "rollback_event",
    ]
    assert contract["reconcile_keys"] == ["task_id", "correlation_id", "artifact_id"]
    assert "policy_ref" in contract["required_fields"]["policy_decision"]
    assert "from_placement" in contract["required_fields"]["placement_change"]
    assert "receipt_ref" in contract["required_fields"]["remote_execution_receipt"]
    assert "failure_code" in contract["required_fields"]["validation_failure"]
    assert "rollback_action" in contract["required_fields"]["rollback_event"]


def test_virtual_ai_os_observability_contract_is_exposed_from_config() -> None:
    contract = get_virtual_ai_os_observability_contract({})

    assert contract["artifact_contract"]["contract_id"] == (
        VIRTUAL_AI_OS_OBSERVABILITY_ARTIFACT_CONTRACT_ID
    )
    assert contract["artifact_contract"]["required_fields"]["rollback_event"] == [
        "artifact_id",
        "task_id",
        "correlation_id",
        "rollback_action",
        "reason",
        "triggered_at",
    ]


def test_virtual_ai_os_observability_bundle_preserves_replay_order_and_links() -> None:
    policy = build_virtual_ai_os_policy_decision_artifact(
        task_id=TASK_ID,
        correlation_id=CORRELATION_ID,
        outcome="permit",
        policy_ref="policy:virtual-ai-os:daemon-supervisor",
        reason="VAI-010 harness permits hardware-free desktop offload.",
        decided_at=OBSERVED_AT,
        evidence_refs={
            "plan": "implementation_plan/docs/19-virtual-ai-os-submodule-integration.md"
        },
    )
    placement = build_virtual_ai_os_placement_change_artifact(
        task_id=TASK_ID,
        correlation_id=CORRELATION_ID,
        from_placement="phone_local",
        to_placement="desktop_peer",
        reason="desktop peer accepted the offload",
        changed_at=OBSERVED_AT,
        placement_ref="sha256:vai011-placement-desktop-peer",
        parent_artifact_ids=(policy["artifact_id"],),
    )
    receipt = build_virtual_ai_os_remote_execution_receipt_artifact(
        task_id=TASK_ID,
        correlation_id=CORRELATION_ID,
        remote_surface="swissknife_orb",
        operation="run_desktop_command",
        status="completed",
        issued_at=OBSERVED_AT,
        receipt_ref="sha256:vai011-remote-receipt",
        stream_refs=("sha256:vai011-stream-events",),
        parent_artifact_ids=(placement["artifact_id"],),
    )
    validation_failure = build_virtual_ai_os_validation_failure_artifact(
        task_id=TASK_ID,
        correlation_id=CORRELATION_ID,
        validator="mobile_orb_display_widget_dispatch",
        failure_code="desktop_peer_disconnected",
        message="Desktop peer disconnected while checking status.",
        failed_at=OBSERVED_AT,
        evidence_refs={"receipt": receipt["artifact_id"]},
        parent_artifact_ids=(receipt["artifact_id"],),
    )
    rollback = build_virtual_ai_os_rollback_event_artifact(
        task_id=TASK_ID,
        correlation_id=CORRELATION_ID,
        rollback_action="fallback_to_phone",
        reason="Recover from desktop peer disconnect.",
        triggered_at=OBSERVED_AT,
        restored_placement="phone_local",
        restored_ref="sha256:vai011-phone-fallback",
        parent_artifact_ids=(validation_failure["artifact_id"],),
    )
    bundle = build_virtual_ai_os_observability_bundle(
        task_id=TASK_ID,
        correlation_id=CORRELATION_ID,
        artifacts=(policy, placement, receipt, validation_failure, rollback),
    )

    assert [artifact["artifact_type"] for artifact in bundle["artifacts"]] == [
        "policy_decision",
        "placement_change",
        "remote_execution_receipt",
        "validation_failure",
        "rollback_event",
    ]
    assert bundle["artifact_ids"] == [
        policy["artifact_id"],
        placement["artifact_id"],
        receipt["artifact_id"],
        validation_failure["artifact_id"],
        rollback["artifact_id"],
    ]
    assert placement["parent_artifact_ids"] == [policy["artifact_id"]]
    assert validation_failure["retryable"] is True
    assert rollback["restored_placement"] == "phone_local"
    assert bundle["supervisor_actions"]["retry_from"] == rollback["artifact_id"]
    assert bundle["supervisor_actions"]["reconcile_by"] == [
        "task_id",
        "correlation_id",
        "artifact_id",
    ]


def test_virtual_ai_os_observability_artifact_ids_are_stable() -> None:
    first = build_virtual_ai_os_remote_execution_receipt_artifact(
        task_id=TASK_ID,
        correlation_id=CORRELATION_ID,
        remote_surface="mobile_glasses",
        operation="dispatch_glasses_response",
        status="error",
        issued_at=OBSERVED_AT,
        receipt_ref="sha256:vai011-dispatch-receipt",
    )
    second = build_virtual_ai_os_remote_execution_receipt_artifact(
        task_id=TASK_ID,
        correlation_id=CORRELATION_ID,
        remote_surface="mobile_glasses",
        operation="dispatch_glasses_response",
        status="error",
        issued_at=OBSERVED_AT,
        receipt_ref="sha256:vai011-dispatch-receipt",
    )

    assert first == second
    assert first["artifact_id"].startswith(
        "sha256:vai-observability:remote_execution_receipt:"
    )
