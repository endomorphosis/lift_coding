"""Hardware-free end-to-end harness for the virtual AI OS remote terminal flow."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from handsfree.agent_providers import (
    IPFSDatasetsMCPAgentProvider,
    _display_widget_action_items_from_context,
)
from handsfree.agents.service import AgentService
from handsfree.db import init_db
from handsfree.models import MetaGlassesDisplayWidgetMobileActionPayload


@pytest.fixture
def db_conn():
    conn = init_db(":memory:")
    yield conn
    conn.close()


@pytest.fixture
def agent_service(db_conn):
    return AgentService(db_conn)


def _write_state(path, *, task_id: str, task_status: str, active_task_id: str | None, active_task_title: str | None):
    path.write_text(
        json.dumps(
            {
                "active_task_id": active_task_id or "",
                "active_task_title": active_task_title or "",
                "ready_count": 1,
                "completed_count": 0 if task_status != "completed" else 1,
                "waiting_count": 0,
                "blocked_count": 0,
                "last_progress_at": "2026-05-22T12:00:00+00:00",
                "recommended_task_id": task_id,
                "recommended_actions": ["Implement the task outputs."],
                "task_statuses": {task_id: task_status},
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_events(path, *, task_id: str, title: str):
    path.write_text(
        json.dumps(
            {
                "type": "task_selected",
                "timestamp": "2026-05-22T12:00:00+00:00",
                "task_id": task_id,
                "title": title,
                "track": "backend",
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _task_progress_manifest(*, title: str, summary: str, status: str) -> dict[str, object]:
    return {
        "schema": "handsfree.meta-glasses/widget-manifest",
        "schema_version": "0.1.0",
        "widget_id": "virtual-ai-os-task-progress",
        "widget_cid": "sha256:widget",
        "interface_cid": "sha256:descriptor",
        "operation": "render_widget",
        "state": {
            "values": {
                "title": title,
                "summary": summary,
                "progress": 0.42,
                "progress_label": "42% complete",
                "status": status,
            },
        },
        "fallback": {
            "render_path": "mobile-card",
            "message": "Display unavailable. Showing task progress on phone.",
        },
    }


def test_virtual_ai_os_daemon_progress_emits_mobile_display_widget_payload(
    agent_service, test_user_id, monkeypatch, tmp_path
):
    state_path = tmp_path / "virtual_ai_os_task_state.json"
    events_path = tmp_path / "virtual_ai_os_events.jsonl"
    title = "Integrate ipfs_datasets_py todo-daemon state into HandsFree task orchestration"
    _write_state(
        state_path,
        task_id="VAI-005",
        task_status="ready",
        active_task_id="VAI-005",
        active_task_title=title,
    )
    _write_events(events_path, task_id="VAI-005", title=title)

    provider = IPFSDatasetsMCPAgentProvider(client=None)
    monkeypatch.setattr(
        "handsfree.agents.service.get_provider",
        lambda provider_name: provider if provider_name == "ipfs_datasets_mcp" else None,
    )

    created = agent_service.delegate(
        user_id=test_user_id,
        instruction="track VAI-005",
        provider="ipfs_datasets_mcp",
        trace={
            "todo_daemon_state_path": str(state_path),
            "todo_daemon_events_path": str(events_path),
            "todo_daemon_task_id": "VAI-005",
        },
    )
    status = agent_service.get_status(user_id=test_user_id)

    assert created["state"] == "running"
    assert created["spoken_text"] == f"VAI-005 active in the todo daemon: {title}."
    assert status["tasks"][0]["result_preview"] == f"VAI-005 active in the todo daemon: {title}."
    assert status["tasks"][0]["todo_daemon_task_status"] == "ready"

    manifest = _task_progress_manifest(
        title="Virtual AI OS task progress",
        summary=status["tasks"][0]["result_preview"],
        status=status["tasks"][0]["todo_daemon_task_status"],
    )
    receipt = {
        "receipt_cid": "sha256:render-receipt",
        "correlation_id": "corr-render",
        "interface_cid": "sha256:descriptor",
        "source_interface_cid": "sha256:descriptor",
        "operation": "render_widget",
        "widget_id": manifest["widget_id"],
        "widget_cid": manifest["widget_cid"],
        "policy_decision": {
            "outcome": "permit",
            "reasons": ["Required capabilities granted."],
            "decision_cid": "sha256:policy",
        },
        "mobile_action": {
            "type": "mobile_render_display_widget",
            "operation": "render_widget",
            "correlation_id": "corr-render",
            "request_id": "render-1",
            "interface_cid": "sha256:descriptor",
            "widget_id": manifest["widget_id"],
            "widget_cid": manifest["widget_cid"],
            "orb_receipt_cid": "sha256:render-receipt",
            "manifest": manifest,
            "state": manifest["state"]["values"],
            "fallback": manifest["fallback"],
            "issued_at": "2026-05-22T12:00:00Z",
        },
        "manifest": manifest,
        "fallback": manifest["fallback"],
    }
    envelope = SimpleNamespace(
        artifact_refs=SimpleNamespace(receipt_ref="sha256:receipt-artifact"),
        trace=SimpleNamespace(request_id="corr-render"),
    )

    action_items = _display_widget_action_items_from_context({}, receipt, envelope)
    render_item = next(
        action for action in action_items if action["id"] == "mobile_render_display_widget"
    )
    payload = MetaGlassesDisplayWidgetMobileActionPayload(**render_item["mobile_payload"])

    assert len(action_items) == 8
    assert payload.type == "mobile_render_display_widget"
    assert payload.operation == "render_widget"
    assert payload.widget_id == "virtual-ai-os-task-progress"
    assert payload.manifest == manifest
    assert payload.state == manifest["state"]["values"]
    assert payload.fallback is not None
    assert payload.fallback["render_path"] == "mobile-card"
    assert payload.fallback["message"] == "Display unavailable. Showing task progress on phone."
    assert payload.state["summary"] == f"VAI-005 active in the todo daemon: {title}."