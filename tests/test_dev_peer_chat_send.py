"""Tests for dev peer chat send endpoint."""

import os
import sys
import time
import types
from unittest.mock import patch

from fastapi.testclient import TestClient

google_module = types.ModuleType("google")
google_api_core = types.ModuleType("google.api_core")
google_api_core_exceptions = types.ModuleType("google.api_core.exceptions")
google_api_core_exceptions.AlreadyExists = Exception
google_api_core_exceptions.NotFound = Exception
google_api_core_exceptions.GoogleAPIError = Exception
google_cloud = types.ModuleType("google.cloud")
google_secretmanager = types.ModuleType("google.cloud.secretmanager")
google_secretmanager.SecretManagerServiceClient = object
hvac_module = types.ModuleType("hvac")
hvac_module.Client = object
hvac_exceptions_module = types.ModuleType("hvac.exceptions")
hvac_exceptions_module.InvalidPath = Exception
hvac_exceptions_module.VaultError = Exception

sys.modules.setdefault("google", google_module)
sys.modules.setdefault("google.api_core", google_api_core)
sys.modules.setdefault("google.api_core.exceptions", google_api_core_exceptions)
sys.modules.setdefault("google.cloud", google_cloud)
sys.modules.setdefault("google.cloud.secretmanager", google_secretmanager)
sys.modules.setdefault("hvac", hvac_module)
sys.modules.setdefault("hvac.exceptions", hvac_exceptions_module)

from handsfree.api import app, dev_peer_chat_service, get_db
from handsfree.db.agent_tasks import create_agent_task


client = TestClient(app)


class FakeTransport:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str, bytes]] = []

    def send_protocol_message(self, peer_id: str, protocol: str, payload: bytes) -> None:
        self.sent.append((peer_id, protocol, payload))

    def get_local_identity(self):
        return type("Identity", (), {"peer_id": "12D3KooWlocalSend"})()


class FakeTransportWithSessions(FakeTransport):
    def __init__(self) -> None:
        super().__init__()
        self.cleared_peer_ids: list[str] = []
        self._cursors = [
            type(
                "Cursor",
                (),
                {
                    "peer_id": "12D3KooWpeerSession",
                    "peer_ref": "12D3KooWpeerSession",
                    "session_id": "session-1",
                    "resume_token": "resume-1",
                    "capabilities": ("runtime",),
                    "updated_at_ms": 1234567890,
                },
            )()
        ]

    def list_persisted_session_cursors(self):
        return list(self._cursors)

    def clear_persisted_session_cursor(self, peer_id: str) -> bool:
        self.cleared_peer_ids.append(peer_id)
        removed = any(cursor.peer_id == peer_id for cursor in self._cursors)
        self._cursors = [cursor for cursor in self._cursors if cursor.peer_id != peer_id]
        return removed


def test_dev_peer_chat_send_dispatches_transport_and_persists_history(test_user_id):
    fake_transport = FakeTransport()
    dev_peer_chat_service._messages.clear()
    get_db().execute("DELETE FROM peer_chat_messages")

    with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "dev"}):
        with patch("handsfree.api.get_peer_transport", return_value=fake_transport):
            response = client.post(
                "/v1/dev/peer-chat/send",
                json={
                    "peer_id": "12D3KooWpeerRemote",
                    "text": "hello outbound",
                },
                headers={"X-User-Id": test_user_id},
            )

            assert response.status_code == 200
            body = response.json()
            assert body["accepted"] is True
            assert body["peer_id"] == "12D3KooWpeerRemote"
            assert body["sender_peer_id"] == "12D3KooWlocalSend"
            assert body["priority"] == "normal"
            assert body["transport_provider"] == "FakeTransport"
            assert len(fake_transport.sent) == 1

            history = client.get(
                f"/v1/dev/peer-chat/{body['conversation_id']}",
                headers={"X-User-Id": test_user_id},
            )

    assert history.status_code == 200
    history_body = history.json()
    assert history_body["messages"][0]["text"] == "hello outbound"
    assert history_body["messages"][0]["sender_peer_id"] == "12D3KooWlocalSend"
    assert history_body["messages"][0]["priority"] == "normal"


def test_dev_transport_sessions_list_and_clear(test_user_id):
    fake_transport = FakeTransportWithSessions()

    with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "dev"}):
        with patch("handsfree.api.get_peer_transport", return_value=fake_transport):
            list_response = client.get(
                "/v1/dev/transport-sessions",
                headers={"X-User-Id": test_user_id},
            )
            assert list_response.status_code == 200
            assert list_response.json()["sessions"] == [
                {
                    "peer_id": "12D3KooWpeerSession",
                    "peer_ref": "12D3KooWpeerSession",
                    "session_id": "session-1",
                    "resume_token": "resume-1",
                    "capabilities": ["runtime"],
                    "updated_at_ms": 1234567890,
                }
            ]

            clear_response = client.delete(
                "/v1/dev/transport-sessions/12D3KooWpeerSession",
                headers={"X-User-Id": test_user_id},
            )
            assert clear_response.status_code == 200
            assert clear_response.json() == {
                "peer_id": "12D3KooWpeerSession",
                "cleared": True,
            }
            assert fake_transport.cleared_peer_ids == ["12D3KooWpeerSession"]


def test_dev_peer_chat_send_populates_outbox(test_user_id):
    fake_transport = FakeTransport()
    dev_peer_chat_service._messages.clear()
    dev_peer_chat_service._outbox.clear()
    dev_peer_chat_service._now_ms_factory = lambda: 1000
    get_db().execute("DELETE FROM peer_chat_messages")

    try:
        with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "dev"}):
            with patch("handsfree.api.get_peer_transport", return_value=fake_transport):
                send_response = client.post(
                    "/v1/dev/peer-chat/send",
                    json={
                    "peer_id": "12D3KooWpeerOutbox",
                    "text": "queue me",
                    "priority": "urgent",
                },
                    headers={"X-User-Id": test_user_id},
                )
                assert send_response.status_code == 200

                peek = client.get(
                    "/v1/dev/peer-chat/outbox/12D3KooWpeerOutbox",
                    headers={"X-User-Id": test_user_id},
                )
                assert peek.status_code == 200
                assert peek.json()["messages"][0]["text"] == "queue me"
                assert peek.json()["messages"][0]["priority"] == "urgent"
                outbox_message_id = peek.json()["messages"][0]["outbox_message_id"]

                second_peek = client.get(
                    "/v1/dev/peer-chat/outbox/12D3KooWpeerOutbox",
                    headers={"X-User-Id": test_user_id},
                )
                assert second_peek.status_code == 200
                assert second_peek.json()["messages"] == []

                ack = client.post(
                    "/v1/dev/peer-chat/outbox/12D3KooWpeerOutbox/ack",
                    json={"outbox_message_ids": [outbox_message_id]},
                    headers={"X-User-Id": test_user_id},
                )
                assert ack.status_code == 200
                assert ack.json()["acknowledged_message_ids"] == [outbox_message_id]

                empty = client.get(
                    "/v1/dev/peer-chat/outbox/12D3KooWpeerOutbox",
                    headers={"X-User-Id": test_user_id},
                )
    finally:
        dev_peer_chat_service._now_ms_factory = lambda: int(time.time() * 1000)

    assert empty.status_code == 200
    assert empty.json()["messages"] == []


def test_dev_peer_chat_send_includes_task_snapshot_in_send_and_outbox(test_user_id):
    fake_transport = FakeTransport()
    dev_peer_chat_service._messages.clear()
    dev_peer_chat_service._outbox.clear()

    task = create_agent_task(
        get_db(),
        user_id=test_user_id,
        provider="ipfs_accelerate_mcp",
        instruction="inspect wearables bridge",
        trace={
            "provider_label": "IPFS Accelerate",
            "mcp_capability": "agentic_fetch",
            "mcp_execution_mode": "mcp_remote",
            "mcp_preferred_execution_mode": "direct_import",
            "mcp_result_preview": "Connectivity receipt captured",
        },
    )

    with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "dev"}):
        with patch("handsfree.api.get_peer_transport", return_value=fake_transport):
            send_response = client.post(
                "/v1/dev/peer-chat/send",
                json={
                    "peer_id": "12D3KooWpeerTask",
                    "text": "share task snapshot",
                    "priority": "urgent",
                    "task_id": task.id,
                },
                headers={"X-User-Id": test_user_id},
            )

            assert send_response.status_code == 200
            send_body = send_response.json()
            assert send_body["task_snapshot"] == {
                "task_id": task.id,
                "state": "created",
                "provider": "ipfs_accelerate_mcp",
                "provider_label": "IPFS Accelerate",
                "capability": "agentic_fetch",
                "summary": "IPFS Accelerate agentic fetch created.",
                "mcp_execution_mode": "mcp_remote",
                "mcp_preferred_execution_mode": "direct_import",
                "result_preview": "Connectivity receipt captured",
            }

            payload = fake_transport.sent[0][2].decode("utf-8")
            assert '"task_snapshot"' in payload
            assert task.id in payload

            outbox_response = client.get(
                "/v1/dev/peer-chat/outbox/12D3KooWpeerTask/status",
                headers={"X-User-Id": test_user_id},
            )
            history_response = client.get(
                f"/v1/dev/peer-chat/{send_body['conversation_id']}",
                headers={"X-User-Id": test_user_id},
            )
            conversations_response = client.get(
                "/v1/dev/peer-chat?limit=5",
                headers={"X-User-Id": test_user_id},
            )

    assert outbox_response.status_code == 200
    preview = outbox_response.json()["preview_messages"][0]
    assert preview["task_snapshot"]["task_id"] == task.id
    assert preview["task_snapshot"]["mcp_execution_mode"] == "mcp_remote"
    assert history_response.status_code == 200
    history_message = history_response.json()["messages"][0]
    assert history_message["task_snapshot"]["task_id"] == task.id
    assert history_message["task_snapshot"]["result_preview"] == "Connectivity receipt captured"
    assert conversations_response.status_code == 200
    conversation = conversations_response.json()["conversations"][0]
    assert conversation["task_snapshot"]["task_id"] == task.id
    assert conversation["priority"] == "urgent"


def test_dev_peer_chat_outbox_lease_expiry_requeues_message(test_user_id):
    fake_transport = FakeTransport()
    dev_peer_chat_service._messages.clear()
    dev_peer_chat_service._outbox.clear()
    current_time_ms = {"value": 1000}
    dev_peer_chat_service._now_ms_factory = lambda: current_time_ms["value"]
    get_db().execute("DELETE FROM peer_chat_messages")

    try:
        with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "dev"}):
            with patch("handsfree.api.get_peer_transport", return_value=fake_transport):
                send_response = client.post(
                    "/v1/dev/peer-chat/send",
                    json={
                    "peer_id": "12D3KooWpeerLease",
                    "text": "lease me",
                    "priority": "normal",
                },
                    headers={"X-User-Id": test_user_id},
                )
                assert send_response.status_code == 200

                first_fetch = client.get(
                    "/v1/dev/peer-chat/outbox/12D3KooWpeerLease?lease_ms=5000",
                    headers={"X-User-Id": test_user_id},
                )
                assert first_fetch.status_code == 200
                assert len(first_fetch.json()["messages"]) == 1

                second_fetch = client.get(
                    "/v1/dev/peer-chat/outbox/12D3KooWpeerLease?lease_ms=5000",
                    headers={"X-User-Id": test_user_id},
                )
                assert second_fetch.status_code == 200
                assert second_fetch.json()["messages"] == []

                current_time_ms["value"] = 7001
                third_fetch = client.get(
                    "/v1/dev/peer-chat/outbox/12D3KooWpeerLease?lease_ms=5000",
                    headers={"X-User-Id": test_user_id},
                )
    finally:
        dev_peer_chat_service._now_ms_factory = lambda: int(time.time() * 1000)

    assert third_fetch.status_code == 200
    assert len(third_fetch.json()["messages"]) == 1


def test_dev_peer_chat_outbox_offline_only_returns_urgent_messages(test_user_id):
    fake_transport = FakeTransport()
    dev_peer_chat_service._messages.clear()
    dev_peer_chat_service._outbox.clear()
    dev_peer_chat_service._handset_sessions.clear()
    current_time_ms = {"value": 1000}
    dev_peer_chat_service._now_ms_factory = lambda: current_time_ms["value"]
    get_db().execute("DELETE FROM peer_chat_messages")

    try:
        with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "dev"}):
            with patch("handsfree.api.get_peer_transport", return_value=fake_transport):
                client.post(
                    "/v1/dev/peer-chat/send",
                    json={
                        "peer_id": "12D3KooWpeerOffline",
                        "text": "normal queued",
                        "priority": "normal",
                    },
                    headers={"X-User-Id": test_user_id},
                )
                client.post(
                    "/v1/dev/peer-chat/send",
                    json={
                        "peer_id": "12D3KooWpeerOffline",
                        "text": "urgent queued",
                        "priority": "urgent",
                    },
                    headers={"X-User-Id": test_user_id},
                )
                client.post(
                    "/v1/dev/peer-chat/handsets/12D3KooWpeerOffline/heartbeat",
                    json={"display_name": "Offline Handset"},
                    headers={"X-User-Id": test_user_id},
                )

                current_time_ms["value"] = 70000
                response = client.get(
                    "/v1/dev/peer-chat/outbox/12D3KooWpeerOffline",
                    headers={"X-User-Id": test_user_id},
                )
    finally:
        dev_peer_chat_service._now_ms_factory = lambda: int(time.time() * 1000)

    assert response.status_code == 200
    assert response.json()["delivery_mode"] == "hold"
    assert response.json()["queued_total"] == 2
    assert response.json()["queued_urgent"] == 1
    assert response.json()["queued_normal"] == 1
    assert response.json()["deliverable_now"] == 1
    assert response.json()["held_now"] == 1
    assert [item["text"] for item in response.json()["messages"]] == ["urgent queued"]
    assert [item["priority"] for item in response.json()["messages"]] == ["urgent"]


def test_dev_peer_chat_outbox_status_does_not_lease_messages(test_user_id):
    fake_transport = FakeTransport()
    dev_peer_chat_service._messages.clear()
    dev_peer_chat_service._outbox.clear()
    dev_peer_chat_service._handset_sessions.clear()
    current_time_ms = {"value": 1000}
    dev_peer_chat_service._now_ms_factory = lambda: current_time_ms["value"]
    get_db().execute("DELETE FROM peer_chat_messages")

    try:
        with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "dev"}):
            with patch("handsfree.api.get_peer_transport", return_value=fake_transport):
                send_response = client.post(
                    "/v1/dev/peer-chat/send",
                    json={
                        "peer_id": "12D3KooWpeerStatus",
                        "text": "status me",
                        "priority": "normal",
                    },
                    headers={"X-User-Id": test_user_id},
                )
                assert send_response.status_code == 200

                status_response = client.get(
                    "/v1/dev/peer-chat/outbox/12D3KooWpeerStatus/status",
                    headers={"X-User-Id": test_user_id},
                )
                assert status_response.status_code == 200
                assert status_response.json()["queued_total"] == 1
                assert status_response.json()["deliverable_now"] == 1
                assert status_response.json()["messages"] == []
                assert status_response.json()["preview_messages"][0]["state"] == "deliverable"
                assert status_response.json()["preview_messages"][0]["text"] == "status me"

                fetch_response = client.get(
                    "/v1/dev/peer-chat/outbox/12D3KooWpeerStatus",
                    headers={"X-User-Id": test_user_id},
                )
    finally:
        dev_peer_chat_service._now_ms_factory = lambda: int(time.time() * 1000)

    assert fetch_response.status_code == 200
    assert len(fetch_response.json()["messages"]) == 1


def test_dev_peer_chat_outbox_release_clears_message_lease(test_user_id):
    fake_transport = FakeTransport()
    dev_peer_chat_service._messages.clear()
    dev_peer_chat_service._outbox.clear()
    current_time_ms = {"value": 1000}
    dev_peer_chat_service._now_ms_factory = lambda: current_time_ms["value"]
    get_db().execute("DELETE FROM peer_chat_messages")

    try:
        with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "dev"}):
            with patch("handsfree.api.get_peer_transport", return_value=fake_transport):
                send_response = client.post(
                    "/v1/dev/peer-chat/send",
                    json={
                        "peer_id": "12D3KooWpeerRelease",
                        "text": "release me",
                        "priority": "normal",
                    },
                    headers={"X-User-Id": test_user_id},
                )
                assert send_response.status_code == 200

                first_fetch = client.get(
                    "/v1/dev/peer-chat/outbox/12D3KooWpeerRelease?lease_ms=5000",
                    headers={"X-User-Id": test_user_id},
                )
                assert first_fetch.status_code == 200
                outbox_message_id = first_fetch.json()["messages"][0]["outbox_message_id"]

                leased_status = client.get(
                    "/v1/dev/peer-chat/outbox/12D3KooWpeerRelease/status",
                    headers={"X-User-Id": test_user_id},
                )
                assert leased_status.status_code == 200
                assert leased_status.json()["preview_messages"][0]["state"] == "leased"

                release_response = client.post(
                    "/v1/dev/peer-chat/outbox/12D3KooWpeerRelease/release",
                    json={"outbox_message_ids": [outbox_message_id]},
                    headers={"X-User-Id": test_user_id},
                )
                assert release_response.status_code == 200
                assert release_response.json()["released_message_ids"] == [outbox_message_id]

                released_status = client.get(
                    "/v1/dev/peer-chat/outbox/12D3KooWpeerRelease/status",
                    headers={"X-User-Id": test_user_id},
                )
    finally:
        dev_peer_chat_service._now_ms_factory = lambda: int(time.time() * 1000)

    assert released_status.status_code == 200
    assert released_status.json()["preview_messages"][0]["state"] == "deliverable"


def test_dev_peer_chat_outbox_promote_makes_held_message_deliverable(test_user_id):
    fake_transport = FakeTransport()
    dev_peer_chat_service._messages.clear()
    dev_peer_chat_service._outbox.clear()
    dev_peer_chat_service._handset_sessions.clear()
    current_time_ms = {"value": 1000}
    dev_peer_chat_service._now_ms_factory = lambda: current_time_ms["value"]
    get_db().execute("DELETE FROM peer_chat_messages")

    try:
        with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "dev"}):
            with patch("handsfree.api.get_peer_transport", return_value=fake_transport):
                send_response = client.post(
                    "/v1/dev/peer-chat/send",
                    json={
                        "peer_id": "12D3KooWpeerPromote",
                        "text": "promote me",
                        "priority": "normal",
                    },
                    headers={"X-User-Id": test_user_id},
                )
                assert send_response.status_code == 200

                client.post(
                    "/v1/dev/peer-chat/handsets/12D3KooWpeerPromote/heartbeat",
                    json={"display_name": "Offline Promote Handset"},
                    headers={"X-User-Id": test_user_id},
                )
                current_time_ms["value"] = 70000

                held_status = client.get(
                    "/v1/dev/peer-chat/outbox/12D3KooWpeerPromote/status",
                    headers={"X-User-Id": test_user_id},
                )
                assert held_status.status_code == 200
                assert held_status.json()["preview_messages"][0]["state"] == "held_by_policy"
                outbox_message_id = held_status.json()["preview_messages"][0]["outbox_message_id"]

                promote_response = client.post(
                    "/v1/dev/peer-chat/outbox/12D3KooWpeerPromote/promote",
                    json={"outbox_message_ids": [outbox_message_id]},
                    headers={"X-User-Id": test_user_id},
                )
                assert promote_response.status_code == 200
                assert promote_response.json()["promoted_message_ids"] == [outbox_message_id]

                promoted_status = client.get(
                    "/v1/dev/peer-chat/outbox/12D3KooWpeerPromote/status",
                    headers={"X-User-Id": test_user_id},
                )
    finally:
        dev_peer_chat_service._now_ms_factory = lambda: int(time.time() * 1000)

    assert promoted_status.status_code == 200
    assert promoted_status.json()["preview_messages"][0]["priority"] == "urgent"
    assert promoted_status.json()["preview_messages"][0]["state"] == "deliverable"


def test_dev_peer_chat_handset_heartbeat_and_status(test_user_id):
    dev_peer_chat_service._handset_sessions.clear()
    current_time_ms = {"value": 1000}
    dev_peer_chat_service._now_ms_factory = lambda: current_time_ms["value"]

    try:
        with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "dev"}):
            heartbeat = client.post(
                "/v1/dev/peer-chat/handsets/12D3KooWhandset/heartbeat",
                json={"display_name": "Test Handset"},
                headers={"X-User-Id": test_user_id},
            )
            assert heartbeat.status_code == 200
            assert heartbeat.json()["peer_id"] == "12D3KooWhandset"
            assert heartbeat.json()["display_name"] == "Test Handset"
            assert heartbeat.json()["last_seen_ms"] == 1000
            assert heartbeat.json()["status"] == "active"
            assert heartbeat.json()["delivery_mode"] == "short_retry"
            assert heartbeat.json()["recommended_lease_ms"] == 5000
            assert heartbeat.json()["recommended_poll_ms"] == 4000
            assert heartbeat.json()["last_seen_age_ms"] == 0

            current_time_ms["value"] = 2500
            status = client.get(
                "/v1/dev/peer-chat/handsets/12D3KooWhandset",
                headers={"X-User-Id": test_user_id},
            )
    finally:
        dev_peer_chat_service._now_ms_factory = lambda: int(time.time() * 1000)

    assert status.status_code == 200
    assert status.json()["peer_id"] == "12D3KooWhandset"
    assert status.json()["display_name"] == "Test Handset"
    assert status.json()["last_seen_ms"] == 1000
    assert status.json()["status"] == "active"
    assert status.json()["delivery_mode"] == "short_retry"
    assert status.json()["last_seen_age_ms"] == 1500


def test_dev_peer_chat_handset_status_transitions_to_stale_and_offline(test_user_id):
    dev_peer_chat_service._handset_sessions.clear()
    current_time_ms = {"value": 1000}
    dev_peer_chat_service._now_ms_factory = lambda: current_time_ms["value"]

    try:
        with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "dev"}):
            heartbeat = client.post(
                "/v1/dev/peer-chat/handsets/12D3KooWstale/heartbeat",
                json={"display_name": "Stale Handset"},
                headers={"X-User-Id": test_user_id},
            )
            assert heartbeat.status_code == 200

            current_time_ms["value"] = 20000
            stale_status = client.get(
                "/v1/dev/peer-chat/handsets/12D3KooWstale",
                headers={"X-User-Id": test_user_id},
            )

            current_time_ms["value"] = 70000
            offline_status = client.get(
                "/v1/dev/peer-chat/handsets/12D3KooWstale",
                headers={"X-User-Id": test_user_id},
            )
    finally:
        dev_peer_chat_service._now_ms_factory = lambda: int(time.time() * 1000)

    assert stale_status.status_code == 200
    assert stale_status.json()["status"] == "stale"
    assert stale_status.json()["delivery_mode"] == "long_retry"
    assert stale_status.json()["recommended_lease_ms"] == 15000
    assert stale_status.json()["recommended_poll_ms"] == 10000
    assert stale_status.json()["last_seen_age_ms"] == 19000
    assert offline_status.status_code == 200
    assert offline_status.json()["status"] == "offline"
    assert offline_status.json()["delivery_mode"] == "hold"
    assert offline_status.json()["recommended_lease_ms"] == 60000
    assert offline_status.json()["recommended_poll_ms"] == 30000
    assert offline_status.json()["last_seen_age_ms"] == 69000


def test_dev_peer_chat_outbox_fetch_and_ack_update_handset_session(test_user_id):
    fake_transport = FakeTransport()
    dev_peer_chat_service._messages.clear()
    dev_peer_chat_service._outbox.clear()
    dev_peer_chat_service._handset_sessions.clear()
    current_time_ms = {"value": 1000}
    dev_peer_chat_service._now_ms_factory = lambda: current_time_ms["value"]
    get_db().execute("DELETE FROM peer_chat_messages")

    try:
        with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "dev"}):
            with patch("handsfree.api.get_peer_transport", return_value=fake_transport):
                send_response = client.post(
                    "/v1/dev/peer-chat/send",
                    json={
                        "peer_id": "12D3KooWpeerObserved",
                        "text": "observe me",
                    },
                    headers={"X-User-Id": test_user_id},
                )
                assert send_response.status_code == 200

                current_time_ms["value"] = 2000
                fetch_response = client.get(
                    "/v1/dev/peer-chat/outbox/12D3KooWpeerObserved",
                    headers={"X-User-Id": test_user_id},
                )
                assert fetch_response.status_code == 200
                assert fetch_response.json()["delivery_mode"] == "short_retry"
                assert fetch_response.json()["recommended_lease_ms"] == 5000
                assert fetch_response.json()["recommended_poll_ms"] == 4000
                assert fetch_response.json()["queued_total"] == 1
                assert fetch_response.json()["queued_urgent"] == 0
                assert fetch_response.json()["queued_normal"] == 1
                assert fetch_response.json()["deliverable_now"] == 1
                assert fetch_response.json()["held_now"] == 0
                outbox_message_id = fetch_response.json()["messages"][0]["outbox_message_id"]

                current_time_ms["value"] = 3000
                ack_response = client.post(
                    "/v1/dev/peer-chat/outbox/12D3KooWpeerObserved/ack",
                    json={"outbox_message_ids": [outbox_message_id]},
                    headers={"X-User-Id": test_user_id},
                )
                assert ack_response.status_code == 200

                session_response = client.get(
                    "/v1/dev/peer-chat/handsets/12D3KooWpeerObserved",
                    headers={"X-User-Id": test_user_id},
                )
    finally:
        dev_peer_chat_service._now_ms_factory = lambda: int(time.time() * 1000)

    assert session_response.status_code == 200
    assert session_response.json()["last_fetch_ms"] == 2000
    assert session_response.json()["last_ack_ms"] == 3000
