"""Hardware-free display widget backend harness tests."""

from __future__ import annotations

import sys
import types
from types import SimpleNamespace
from typing import Any

if "handsfree.secrets" not in sys.modules:
    secrets_module = types.ModuleType("handsfree.secrets")
    secrets_module.get_default_secret_manager = lambda: None
    secrets_module.get_secret_manager = lambda *args, **kwargs: None
    secrets_module.reset_secret_manager = lambda: None
    sys.modules["handsfree.secrets"] = secrets_module

from handsfree.agent_providers import (  # noqa: E402
    _display_widget_action_items_from_context,
)
from handsfree.models import MetaGlassesDisplayWidgetMobileActionPayload  # noqa: E402


def _envelope() -> SimpleNamespace:
    return SimpleNamespace(
        artifact_refs=SimpleNamespace(receipt_ref="sha256:receipt-artifact"),
        trace=SimpleNamespace(request_id="corr-render"),
    )


def _orb_receipt(
    *,
    operation: str,
    mobile_action: dict[str, Any],
    receipt_cid: str,
    correlation_id: str,
) -> dict[str, Any]:
    return {
        "receipt_cid": receipt_cid,
        "correlation_id": correlation_id,
        "interface_cid": "sha256:descriptor",
        "source_interface_cid": "sha256:descriptor",
        "operation": operation,
        "widget_id": "task-progress-active",
        "widget_cid": "sha256:widget",
        "policy_decision": {
            "outcome": "permit",
            "reasons": ["Required capabilities granted."],
            "decision_cid": "sha256:policy",
        },
        "mobile_action": mobile_action,
        "manifest": mobile_action.get("manifest"),
        "patch": mobile_action.get("patch"),
        "focus": mobile_action.get("focus"),
        "fallback": mobile_action.get("fallback"),
    }


def _mobile_action(
    *,
    action_type: str,
    operation: str,
    correlation_id: str,
    receipt_cid: str,
    manifest: dict[str, Any] | None = None,
    patch: dict[str, Any] | None = None,
) -> dict[str, Any]:
    action: dict[str, Any] = {
        "type": action_type,
        "operation": operation,
        "correlation_id": correlation_id,
        "request_id": f"{operation}-1",
        "interface_cid": "sha256:descriptor",
        "widget_id": "task-progress-active",
        "widget_cid": "sha256:widget",
        "orb_receipt_cid": receipt_cid,
        "fallback": {
            "render_path": "mobile-card",
            "message": "Display unavailable. Showing task progress on phone.",
        },
        "issued_at": "2026-05-22T12:00:00Z",
    }
    if manifest is not None:
        action["manifest"] = manifest
        action["state"] = manifest["state"]["values"]
    if patch is not None:
        action["patch"] = patch
    return action


def _backend_payload_for(receipt: dict[str, Any], action_id: str) -> dict[str, Any]:
    actions = _display_widget_action_items_from_context({}, receipt, _envelope())
    assert [action["id"] for action in actions] == [
        "mobile_render_display_widget",
        "mobile_update_display_widget",
        "mobile_clear_display_widget",
        "mobile_focus_display_widget",
        "mobile_activate_display_widget_action",
        "mobile_reset_display_widget_session",
        "mobile_play_display_widget_video",
        "mobile_subscribe_display_widget_updates",
    ]
    return next(action["mobile_payload"] for action in actions if action["id"] == action_id)


def test_backend_serializes_orb_receipts_into_mobile_widget_actions() -> None:
    manifest = {
        "schema": "handsfree.meta-glasses/widget-manifest",
        "schema_version": "0.1.0",
        "widget_id": "task-progress-active",
        "widget_cid": "sha256:widget",
        "interface_cid": "sha256:descriptor",
        "operation": "render_widget",
        "state": {
            "values": {
                "title": "Sync dataset",
                "progress": 0.42,
                "progress_label": "42% complete",
                "status": "running",
            },
        },
        "fallback": {
            "render_path": "mobile-card",
            "message": "Display unavailable. Showing task progress on phone.",
        },
    }
    render_receipt = _orb_receipt(
        operation="render_widget",
        receipt_cid="sha256:render-receipt",
        correlation_id="corr-render",
        mobile_action=_mobile_action(
            action_type="mobile_render_display_widget",
            operation="render_widget",
            correlation_id="corr-render",
            receipt_cid="sha256:render-receipt",
            manifest=manifest,
        ),
    )
    update_receipt = _orb_receipt(
        operation="update_widget",
        receipt_cid="sha256:update-receipt",
        correlation_id="corr-update",
        mobile_action=_mobile_action(
            action_type="mobile_update_display_widget",
            operation="update_widget",
            correlation_id="corr-update",
            receipt_cid="sha256:update-receipt",
            patch={"progress": 0.43, "progress_label": "43% complete"},
        ),
    )
    clear_receipt = _orb_receipt(
        operation="clear_widget",
        receipt_cid="sha256:clear-receipt",
        correlation_id="corr-clear",
        mobile_action=_mobile_action(
            action_type="mobile_clear_display_widget",
            operation="clear_widget",
            correlation_id="corr-clear",
            receipt_cid="sha256:clear-receipt",
        ),
    )

    render_payload = _backend_payload_for(render_receipt, "mobile_render_display_widget")
    update_payload = _backend_payload_for(update_receipt, "mobile_update_display_widget")
    clear_payload = _backend_payload_for(clear_receipt, "mobile_clear_display_widget")

    render_model = MetaGlassesDisplayWidgetMobileActionPayload(**render_payload)
    update_model = MetaGlassesDisplayWidgetMobileActionPayload(**update_payload)
    clear_model = MetaGlassesDisplayWidgetMobileActionPayload(**clear_payload)

    assert render_model.type == "mobile_render_display_widget"
    assert render_model.operation == "render_widget"
    assert render_model.descriptor_cid == "sha256:descriptor"
    assert render_model.interface_cid == "sha256:descriptor"
    assert render_model.widget_cid == "sha256:widget"
    assert render_model.orb_receipt_cid == "sha256:render-receipt"
    assert render_model.policy_decision.outcome == "permit"
    assert render_model.manifest == manifest
    assert render_model.state == manifest["state"]["values"]
    assert render_model.fallback == manifest["fallback"]

    assert update_model.type == "mobile_update_display_widget"
    assert update_model.operation == "update_widget"
    assert update_model.orb_receipt_cid == "sha256:update-receipt"
    assert update_model.patch == {
        "progress": 0.43,
        "progress_label": "43% complete",
    }

    assert clear_model.type == "mobile_clear_display_widget"
    assert clear_model.operation == "clear_widget"
    assert clear_model.orb_receipt_cid == "sha256:clear-receipt"
    assert clear_model.widget_id == "task-progress-active"
