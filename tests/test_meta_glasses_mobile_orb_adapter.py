"""Unit tests for Meta glasses mobile ORB response helpers."""

from __future__ import annotations

from handsfree.meta_glasses_mobile_orb_adapter import (
    build_mobile_orb_dispatch_response,
    build_mobile_orb_invoke_service_response,
)
from handsfree.models import (
    MetaGlassesMobileOrbDispatchResponseRequest,
    MetaGlassesMobileOrbInvokeServiceRequest,
)


def test_build_mobile_orb_invoke_service_response_normalizes_optional_fields() -> None:
    request = MetaGlassesMobileOrbInvokeServiceRequest(
        binding_handle="sha256:binding",
        operation="get_task_status",
        arguments={
            "task_id": "task-123",
            "display_widget_action": {"type": "mobile_render_display_widget"},
            "follow_up_actions": [{"id": "open_result"}, "ignored"],
            "spoken_text": "Task is running.",
        },
        correlation_id="corr-task-status",
        parent_receipt_cids=["sha256:event-receipt"],
    )

    response = build_mobile_orb_invoke_service_response(
        binding={"service_interface_cid": "sha256:task-service"},
        request=request,
        receipt_cid="sha256:invoke-receipt",
    )

    assert response.ok is True
    assert response.service_result["service_interface_cid"] == "sha256:task-service"
    assert response.output_refs == ["sha256:invoke-receipt"]
    assert response.provenance_refs == ["sha256:task-service", "sha256:event-receipt"]
    assert response.follow_up_actions[0] == {"id": "open_result"}
    assert response.follow_up_actions[1]["id"] == "mobile_render_display_widget"
    assert response.follow_up_actions[1]["params"]["display_widget_action"] == (
        response.display_widget_action
    )
    assert response.display_widget_action["contract"] == (
        "handsfree.meta-glasses/display-widget-action@0.1.0"
    )
    assert response.display_widget_action["type"] == "mobile_render_display_widget"
    assert response.display_widget_action["action"] == "render"
    assert response.display_widget_action["operation"] == "render_widget"
    assert response.display_widget_action["orb_receipt_cid"] == "sha256:invoke-receipt"
    assert response.display_widget_action["correlation_id"] == "corr-task-status"
    assert response.display_widget_action["policy_decision"]["outcome"] == "permit"
    assert response.spoken_text == "Task is running."


def test_build_mobile_orb_dispatch_response_filters_invalid_fields() -> None:
    request = MetaGlassesMobileOrbDispatchResponseRequest(
        edge_session_id="sha256:edge-session",
        result={
            "follow_up_actions": [{"id": "open_result"}, "ignored"],
            "display_widget_action": "invalid",
            "spoken_text": ["invalid"],
        },
        render_targets=["display_widget", "audio"],
        correlation_id="corr-task-status",
        parent_receipt_cids=["sha256:event-receipt", "sha256:invoke-receipt"],
    )

    response = build_mobile_orb_dispatch_response(
        request=request,
        receipt_cid="sha256:dispatch-receipt",
    )

    assert response.dispatched_actions == [{"id": "open_result"}]
    assert response.display_widget_action is None
    assert response.spoken_text is None
    assert response.receipt_cid == "sha256:dispatch-receipt"
