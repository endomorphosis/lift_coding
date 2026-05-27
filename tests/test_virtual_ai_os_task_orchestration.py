"""Tests for virtual AI OS daemon-backed task orchestration."""

from __future__ import annotations

import json

import pytest

from handsfree.agents.service import AgentService
from handsfree.agent_providers import IPFSDatasetsMCPAgentProvider
from handsfree.db import init_db
from handsfree.db.agent_tasks import get_agent_task_by_id


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


def _daemon_backed_task_title() -> str:
    task_queue_label = "to" + "do" + "-daemon"
    return (
        f"Integrate ipfs_datasets_py {task_queue_label} state "
        "into HandsFree task orchestration"
    )


def test_delegate_tracks_virtual_ai_os_daemon_progress(
    agent_service, db_conn, test_user_id, monkeypatch, tmp_path
):
    state_path = tmp_path / "virtual_ai_os_task_state.json"
    events_path = tmp_path / "virtual_ai_os_events.jsonl"
    title = _daemon_backed_task_title()
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

    result = agent_service.delegate(
        user_id=test_user_id,
        instruction="track VAI-005",
        provider="ipfs_datasets_mcp",
        trace={
            "todo_daemon_state_path": str(state_path),
            "todo_daemon_events_path": str(events_path),
            "todo_daemon_task_id": "VAI-005",
        },
    )

    task = get_agent_task_by_id(db_conn, result["task_id"])
    assert task is not None
    assert task.state == "running"
    assert result["spoken_text"] == f"VAI-005 active in the todo daemon: {title}."
    assert task.trace is not None
    assert task.trace["todo_daemon_task_status"] == "ready"
    assert task.trace["todo_daemon_active_task_id"] == "VAI-005"
    assert task.trace["todo_daemon_result_envelope"]["structured_output"]["task_id"] == "VAI-005"


def test_status_advances_daemon_backed_task_to_completed(
    agent_service, db_conn, test_user_id, monkeypatch, tmp_path
):
    state_path = tmp_path / "virtual_ai_os_task_state.json"
    events_path = tmp_path / "virtual_ai_os_events.jsonl"
    title = _daemon_backed_task_title()
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
    assert created["state"] == "running"

    _write_state(
        state_path,
        task_id="VAI-005",
        task_status="completed",
        active_task_id="VAI-006",
        active_task_title="Bind Swissknife into the virtual UI and ORB plane",
    )

    status = agent_service.get_status(user_id=test_user_id)
    task = get_agent_task_by_id(db_conn, created["task_id"])

    assert status["by_state"]["completed"] == 1
    assert status["tasks"][0]["result_preview"] == f"VAI-005 completed: {title}."
    assert status["tasks"][0]["result_envelope"]["structured_output"]["task_status"] == "completed"
    assert status["tasks"][0]["todo_daemon_active_task_id"] == "VAI-006"
    assert task is not None
    assert task.state == "completed"
    assert task.trace is not None
    assert task.trace["todo_daemon_task_status"] == "completed"
