"""Display widget backend action contract tests."""

import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

if "handsfree.secrets" not in sys.modules:
    secrets_module = types.ModuleType("handsfree.secrets")
    secrets_module.get_default_secret_manager = lambda: None
    secrets_module.get_secret_manager = lambda *args, **kwargs: None
    secrets_module.reset_secret_manager = lambda: None
    sys.modules["handsfree.secrets"] = secrets_module

from handsfree.agent_providers import (  # noqa: E402
    IPFSAccelerateMCPAgentProvider,
    build_meta_glasses_display_widget_action_items,
)
from handsfree.api import app  # noqa: E402
from handsfree.models import MetaGlassesDisplayWidgetMobileActionPayload  # noqa: E402
from test_mcp_ipfs_provider import _FakeMCPClient  # noqa: E402


client = TestClient(app)

DISPLAY_WIDGET_ACTION_IDS = [
    "mobile_render_display_widget",
    "mobile_update_display_widget",
    "mobile_clear_display_widget",
    "mobile_focus_display_widget",
    "mobile_activate_display_widget_action",
    "mobile_reset_display_widget_session",
]


def _contract_kwargs() -> dict[str, object]:
    return {
        "descriptor_cid": "bafybeidescriptor",
        "widget_cid": "bafybeiwidget",
        "orb_receipt_cid": "bafybeiorbreceipt",
        "policy_decision": {
            "outcome": "permit",
            "reasons": ["trusted descriptor"],
            "policy_id": "display-widget-default",
        },
        "widget_id": "handsfree.task-progress-widget",
        "correlation_id": "corr-widget",
        "request_id": "render-1",
        "state": {"status": "running", "progress": 0.42},
        "patch": {"progress": 0.43},
        "fallback": {"render_path": "mobile-card", "message": "Display unavailable."},
    }


def test_display_widget_payload_model_requires_receipt_and_policy_fields() -> None:
    payload = MetaGlassesDisplayWidgetMobileActionPayload(
        type="mobile_render_display_widget",
        action="render",
        operation="render_widget",
        descriptor_cid="bafybeidescriptor",
        widget_id="handsfree.task-progress-widget",
        widget_cid="bafybeiwidget",
        orb_receipt_cid="bafybeiorbreceipt",
        policy_decision={"outcome": "permit", "reasons": ["trusted descriptor"]},
        correlation_id="corr-widget-render",
    )

    assert payload.interface_cid == "bafybeidescriptor"
    assert payload.policy_decision.outcome == "permit"

    with pytest.raises(ValidationError):
        MetaGlassesDisplayWidgetMobileActionPayload(
            type="mobile_render_display_widget",
            action="render",
            operation="render_widget",
            descriptor_cid="bafybeidescriptor",
            widget_id="handsfree.task-progress-widget",
            widget_cid="bafybeiwidget",
            policy_decision={"outcome": "permit"},
            correlation_id="corr-widget-render",
        )


def test_provider_helper_builds_all_widget_mobile_actions() -> None:
    actions = build_meta_glasses_display_widget_action_items(**_contract_kwargs())

    assert [action["id"] for action in actions] == DISPLAY_WIDGET_ACTION_IDS
    for action in actions:
        payload = MetaGlassesDisplayWidgetMobileActionPayload(**action["mobile_payload"])
        assert action["params"]["display_widget_action"] == action["mobile_payload"]
        assert action["params"]["descriptor_cid"] == "bafybeidescriptor"
        assert action["params"]["widget_cid"] == "bafybeiwidget"
        assert action["params"]["orb_receipt_cid"] == "bafybeiorbreceipt"
        assert payload.descriptor_cid == "bafybeidescriptor"
        assert payload.widget_cid == "bafybeiwidget"
        assert payload.orb_receipt_cid == "bafybeiorbreceipt"
        assert payload.policy_decision.outcome == "permit"

    focus_payload = actions[3]["mobile_payload"]
    assert focus_payload["action"] == "focus"
    assert focus_payload["operation"] == "focus_next"
    assert focus_payload["focus"] == {"direction": "next"}


def test_wearables_provider_envelope_adds_widget_action_contract(monkeypatch) -> None:
    monkeypatch.setenv("HANDSFREE_AGENT_ENABLE_IPFS_ACCELERATE_MCP", "true")
    provider = IPFSAccelerateMCPAgentProvider(client=_FakeMCPClient())
    task = SimpleNamespace(
        id="task-widget-1",
        instruction="render a task progress widget",
        target_type=None,
        target_ref=None,
        trace={
            "wearables_bridge_requested_workflow": "wearables_bridge_connectivity",
            "mcp_capability": "workflow",
            "client_context": {
                "device_id": "AA:BB",
                "device_name": "Ray-Ban Meta",
                "target_connection_state": "connected",
                "display_capable": True,
                "display_connection_state": "connected",
                "display_widget_descriptor_cid": "bafybeidescriptor",
                "display_widget_id": "handsfree.task-progress-widget",
                "display_widget_cid": "bafybeiwidget",
                "display_widget_orb_receipt_cid": "bafybeiorbreceipt",
                "display_widget_correlation_id": "corr-widget",
                "display_widget_policy_decision": {
                    "outcome": "permit",
                    "reasons": ["trusted descriptor"],
                },
            },
        },
    )

    result = provider.start_task(task)
    envelope = result["trace"]["mcp_result_envelope"]
    widget_actions = [
        action for action in envelope["follow_up_actions"] if action["id"] in DISPLAY_WIDGET_ACTION_IDS
    ]

    assert result["ok"] is True
    assert [action["id"] for action in widget_actions] == DISPLAY_WIDGET_ACTION_IDS
    assert widget_actions[0]["mobile_payload"]["descriptor_cid"] == "bafybeidescriptor"
    assert widget_actions[0]["mobile_payload"]["widget_cid"] == "bafybeiwidget"
    assert widget_actions[0]["mobile_payload"]["orb_receipt_cid"] == "bafybeiorbreceipt"
    assert widget_actions[0]["mobile_payload"]["policy_decision"]["outcome"] == "permit"


def test_openapi_exposes_display_widget_action_contract() -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schemas = response.json()["components"]["schemas"]
    assert "MetaGlassesDisplayWidgetMobileActionPayload" in schemas
    payload_schema = schemas["MetaGlassesDisplayWidgetMobileActionPayload"]
    assert {
        "type",
        "action",
        "operation",
        "descriptor_cid",
        "widget_id",
        "widget_cid",
        "orb_receipt_cid",
        "policy_decision",
        "correlation_id",
    }.issubset(set(payload_schema["required"]))
    assert "mobile_payload" in schemas["ActionItem"]["properties"]

    schema_json = json.dumps(schemas)
    examples_json = json.dumps(schemas["CommandResponse"].get("examples", []))
    for action_id in DISPLAY_WIDGET_ACTION_IDS:
        assert action_id in schema_json
        assert action_id in examples_json
    for contract_field in ("descriptor_cid", "widget_cid", "orb_receipt_cid", "policy_decision"):
        assert contract_field in schema_json
        assert contract_field in examples_json


def test_static_openapi_spec_documents_display_widget_actions() -> None:
    raw_spec = Path("spec/openapi.yaml").read_text()

    for action_id in DISPLAY_WIDGET_ACTION_IDS:
        assert action_id in raw_spec
    for contract_field in ("descriptor_cid", "widget_cid", "orb_receipt_cid", "policy_decision"):
        assert contract_field in raw_spec
