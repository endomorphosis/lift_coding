"""Hardware-free display widget backend harness tests."""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path
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
from handsfree.meta_glasses_display_widget_contract import (  # noqa: E402
    DISPLAY_WIDGET_ACTION_DEFINITIONS,
    DISPLAY_WIDGET_ACTION_IDS,
    DISPLAY_WIDGET_ORB_OPERATIONS,
)
from handsfree.metrics import get_metrics_collector  # noqa: E402
from handsfree.models import MetaGlassesDisplayWidgetMobileActionPayload  # noqa: E402

SPEC_PATH = (
    Path(__file__).resolve().parents[1] / "spec" / "meta_glasses_display_widget_orb_interface.json"
)

MANIFEST = {
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
    policy_decision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "receipt_cid": receipt_cid,
        "correlation_id": correlation_id,
        "interface_cid": "sha256:descriptor",
        "source_interface_cid": "sha256:descriptor",
        "operation": operation,
        "widget_id": "task-progress-active",
        "widget_cid": "sha256:widget",
        "policy_decision": policy_decision
        or {
            "outcome": "permit",
            "reasons": ["Required capabilities granted."],
            "decision_cid": "sha256:policy",
        },
        "mobile_action": mobile_action,
        "manifest": mobile_action.get("manifest"),
        "patch": mobile_action.get("patch"),
        "focus": mobile_action.get("focus"),
        "activated_action_id": mobile_action.get("activated_action_id"),
        "video": mobile_action.get("video"),
        "subscription": mobile_action.get("subscription"),
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
    focus: dict[str, Any] | None = None,
    activated_action_id: str | None = None,
    video: dict[str, Any] | None = None,
    subscription: dict[str, Any] | None = None,
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
    if focus is not None:
        action["focus"] = focus
    if activated_action_id is not None:
        action["activated_action_id"] = activated_action_id
    if video is not None:
        action["video"] = video
    if subscription is not None:
        action["subscription"] = subscription
    return action


def _backend_payload_for(receipt: dict[str, Any], action_id: str) -> dict[str, Any]:
    actions = _display_widget_action_items_from_context({}, receipt, _envelope())
    assert [action["id"] for action in actions] == list(DISPLAY_WIDGET_ACTION_IDS)
    return next(action["mobile_payload"] for action in actions if action["id"] == action_id)


def test_backend_display_widget_contract_matches_descriptor_artifact() -> None:
    descriptor = json.loads(SPEC_PATH.read_text())

    assert descriptor["name"] == "display_widget_bridge"
    assert descriptor["namespace"] == "handsfree.meta_glasses.display"
    assert descriptor["version"] == "0.1.0"
    assert [method["name"] for method in descriptor["methods"]] == list(
        DISPLAY_WIDGET_ORB_OPERATIONS
    )
    assert [definition["id"] for definition in DISPLAY_WIDGET_ACTION_DEFINITIONS] == list(
        DISPLAY_WIDGET_ACTION_IDS
    )


def test_backend_serializes_orb_receipts_into_all_mobile_widget_actions() -> None:
    render_receipt = _orb_receipt(
        operation="render_widget",
        receipt_cid="sha256:render-receipt",
        correlation_id="corr-render",
        mobile_action=_mobile_action(
            action_type="mobile_render_display_widget",
            operation="render_widget",
            correlation_id="corr-render",
            receipt_cid="sha256:render-receipt",
            manifest=MANIFEST,
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
    focus_receipt = _orb_receipt(
        operation="focus_next",
        receipt_cid="sha256:focus-receipt",
        correlation_id="corr-focus",
        mobile_action=_mobile_action(
            action_type="mobile_focus_display_widget",
            operation="focus_next",
            correlation_id="corr-focus",
            receipt_cid="sha256:focus-receipt",
            focus={"direction": "next", "action_id": "dismiss", "focus_index": 1},
        ),
    )
    activate_receipt = _orb_receipt(
        operation="activate",
        receipt_cid="sha256:activate-receipt",
        correlation_id="corr-activate",
        mobile_action=_mobile_action(
            action_type="mobile_activate_display_widget_action",
            operation="activate",
            correlation_id="corr-activate",
            receipt_cid="sha256:activate-receipt",
            activated_action_id="pause",
        ),
    )
    reset_receipt = _orb_receipt(
        operation="reset_session",
        receipt_cid="sha256:reset-receipt",
        correlation_id="corr-reset",
        mobile_action=_mobile_action(
            action_type="mobile_reset_display_widget_session",
            operation="reset_session",
            correlation_id="corr-reset",
            receipt_cid="sha256:reset-receipt",
        ),
    )
    video_receipt = _orb_receipt(
        operation="play_video",
        receipt_cid="sha256:video-receipt",
        correlation_id="corr-video",
        mobile_action=_mobile_action(
            action_type="mobile_play_display_widget_video",
            operation="play_video",
            correlation_id="corr-video",
            receipt_cid="sha256:video-receipt",
            manifest=MANIFEST,
            video={
                "media_id": "preview",
                "uri": "https://example.test/clip.mp4",
                "content_type": "video/mp4",
                "duration_ms": 1200,
            },
        ),
    )
    subscribe_receipt = _orb_receipt(
        operation="subscribe_updates",
        receipt_cid="sha256:subscribe-receipt",
        correlation_id="corr-subscribe",
        mobile_action=_mobile_action(
            action_type="mobile_subscribe_display_widget_updates",
            operation="subscribe_updates",
            correlation_id="corr-subscribe",
            receipt_cid="sha256:subscribe-receipt",
            subscription={"stream": "display_widget_update"},
        ),
    )

    render_payload = _backend_payload_for(render_receipt, "mobile_render_display_widget")
    update_payload = _backend_payload_for(update_receipt, "mobile_update_display_widget")
    clear_payload = _backend_payload_for(clear_receipt, "mobile_clear_display_widget")
    focus_payload = _backend_payload_for(focus_receipt, "mobile_focus_display_widget")
    activate_payload = _backend_payload_for(
        activate_receipt,
        "mobile_activate_display_widget_action",
    )
    reset_payload = _backend_payload_for(reset_receipt, "mobile_reset_display_widget_session")
    video_payload = _backend_payload_for(video_receipt, "mobile_play_display_widget_video")
    subscribe_payload = _backend_payload_for(
        subscribe_receipt,
        "mobile_subscribe_display_widget_updates",
    )

    render_model = MetaGlassesDisplayWidgetMobileActionPayload(**render_payload)
    update_model = MetaGlassesDisplayWidgetMobileActionPayload(**update_payload)
    clear_model = MetaGlassesDisplayWidgetMobileActionPayload(**clear_payload)
    focus_model = MetaGlassesDisplayWidgetMobileActionPayload(**focus_payload)
    activate_model = MetaGlassesDisplayWidgetMobileActionPayload(**activate_payload)
    reset_model = MetaGlassesDisplayWidgetMobileActionPayload(**reset_payload)
    video_model = MetaGlassesDisplayWidgetMobileActionPayload(**video_payload)
    subscribe_model = MetaGlassesDisplayWidgetMobileActionPayload(**subscribe_payload)

    assert render_model.type == "mobile_render_display_widget"
    assert render_model.operation == "render_widget"
    assert render_model.descriptor_cid == "sha256:descriptor"
    assert render_model.interface_cid == "sha256:descriptor"
    assert render_model.widget_cid == "sha256:widget"
    assert render_model.orb_receipt_cid == "sha256:render-receipt"
    assert render_model.policy_decision.outcome == "permit"
    assert render_model.manifest == MANIFEST
    assert render_model.state == MANIFEST["state"]["values"]
    assert render_model.fallback == MANIFEST["fallback"]

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

    assert focus_model.type == "mobile_focus_display_widget"
    assert focus_model.operation == "focus_next"
    assert focus_model.focus is not None
    assert focus_model.focus.direction == "next"
    assert focus_model.focus.action_id == "dismiss"
    assert focus_model.focus.focus_index == 1
    assert focus_model.orb_receipt_cid == "sha256:focus-receipt"

    assert activate_model.type == "mobile_activate_display_widget_action"
    assert activate_model.operation == "activate"
    assert activate_model.activated_action_id == "pause"
    assert activate_model.orb_receipt_cid == "sha256:activate-receipt"

    assert reset_model.type == "mobile_reset_display_widget_session"
    assert reset_model.operation == "reset_session"
    assert reset_model.orb_receipt_cid == "sha256:reset-receipt"

    assert video_model.type == "mobile_play_display_widget_video"
    assert video_model.operation == "play_video"
    assert video_model.video == {
        "media_id": "preview",
        "uri": "https://example.test/clip.mp4",
        "content_type": "video/mp4",
        "duration_ms": 1200,
    }
    assert video_model.manifest == MANIFEST
    assert video_model.state == MANIFEST["state"]["values"]
    assert video_model.orb_receipt_cid == "sha256:video-receipt"

    assert subscribe_model.type == "mobile_subscribe_display_widget_updates"
    assert subscribe_model.operation == "subscribe_updates"
    assert subscribe_model.subscription == {"stream": "display_widget_update"}
    assert subscribe_model.orb_receipt_cid == "sha256:subscribe-receipt"


def test_backend_policy_denial_suppresses_mobile_widget_actions(monkeypatch) -> None:
    monkeypatch.setenv("HANDSFREE_DISPLAY_WIDGETS_ENABLED", "true")
    monkeypatch.setenv("HANDSFREE_DISPLAY_WIDGETS_REQUIRE_TRUSTED_DESCRIPTOR", "true")
    metrics = get_metrics_collector()
    metrics.reset()

    denied_receipt = _orb_receipt(
        operation="render_widget",
        receipt_cid="sha256:denied-receipt",
        correlation_id="corr-denied",
        policy_decision={
            "outcome": "deny",
            "reasons": ["Missing capability: display/widget"],
            "decision_cid": "sha256:policy-denied",
        },
        mobile_action=_mobile_action(
            action_type="mobile_render_display_widget",
            operation="render_widget",
            correlation_id="corr-denied",
            receipt_cid="sha256:denied-receipt",
            manifest=MANIFEST,
        ),
    )

    assert _display_widget_action_items_from_context({}, denied_receipt, _envelope()) == []
    assert metrics.get_snapshot()["display_widget_metrics"]["policy_denial_counts"] == {
        "deny": 1,
    }

    metrics.reset()
