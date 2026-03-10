"""Tests for dev peer chat history endpoint."""

import base64
import os
import sys
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
from handsfree.transport.libp2p_bluetooth import (
    CHAT_PROTOCOL_ID,
    PeerEnvelope,
    encode_chat_message_payload,
    encode_transport_envelope,
    encode_transport_message,
)


client = TestClient(app)


def test_dev_peer_chat_history_returns_normalized_messages(test_user_id):
    conversation_id = "chat:test-history"
    task_snapshot = {
        "task_id": "task-history-1",
        "provider_label": "IPFS Accelerate",
        "summary": "IPFS Accelerate agentic fetch running.",
    }
    envelope = PeerEnvelope(
        kind="message",
        peer_id="12D3KooWpeerChat",
        session_id="session-chat-history",
        payload_b64=encode_transport_message(
            CHAT_PROTOCOL_ID,
            encode_chat_message_payload(
                "history hello",
                sender_peer_id="12D3KooWpeerChat",
                conversation_id=conversation_id,
                priority="urgent",
                timestamp_ms=222222,
                        task_snapshot=task_snapshot,
            ),
        ),
    )

    dev_peer_chat_service._messages.clear()  # test reset for in-memory dev store
    get_db().execute("DELETE FROM peer_chat_messages")

    with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "dev"}):
        ingest = client.post(
            "/v1/dev/peer-envelope",
            json={
                "peer_ref": "peer://chat-a",
                "frame_base64": base64.b64encode(encode_transport_envelope(envelope)).decode("ascii"),
            },
            headers={"X-User-Id": test_user_id},
        )
        assert ingest.status_code == 200

        response = client.get(
            f"/v1/dev/peer-chat/{conversation_id}",
            headers={"X-User-Id": test_user_id},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["conversation_id"] == conversation_id
    assert body["messages"] == [
        {
            "conversation_id": conversation_id,
            "peer_id": "12D3KooWpeerChat",
            "sender_peer_id": "12D3KooWpeerChat",
            "text": "history hello",
            "priority": "urgent",
            "timestamp_ms": 222222,
            "task_snapshot": {
                "task_id": "task-history-1",
                "state": None,
                "provider": None,
                "provider_label": "IPFS Accelerate",
                "capability": None,
                "summary": "IPFS Accelerate agentic fetch running.",
                "mcp_execution_mode": None,
                "mcp_preferred_execution_mode": None,
                "result_preview": None,
            },
        }
    ]


def test_dev_peer_chat_recent_conversations_returns_latest_summary(test_user_id):
    dev_peer_chat_service._messages.clear()  # test reset for in-memory fallback state
    get_db().execute("DELETE FROM peer_chat_messages")

    messages = [
        ("chat:test-a", "first message", 1000),
        ("chat:test-b", "second message", 2000),
    ]

    with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "dev"}):
        for conversation_id, text, timestamp_ms in messages:
            envelope = PeerEnvelope(
                kind="message",
                peer_id="12D3KooWpeerChat",
                session_id=f"session-{conversation_id}",
                payload_b64=encode_transport_message(
                    CHAT_PROTOCOL_ID,
                    encode_chat_message_payload(
                        text,
                        sender_peer_id="12D3KooWpeerChat",
                        conversation_id=conversation_id,
                        priority="normal",
                        timestamp_ms=timestamp_ms,
                    ),
                ),
            )
            ingest = client.post(
                "/v1/dev/peer-envelope",
                json={
                    "peer_ref": "peer://chat-a",
                    "frame_base64": base64.b64encode(encode_transport_envelope(envelope)).decode("ascii"),
                },
                headers={"X-User-Id": test_user_id},
            )
            assert ingest.status_code == 200

        response = client.get(
            "/v1/dev/peer-chat?limit=10",
            headers={"X-User-Id": test_user_id},
        )

    assert response.status_code == 200
    body = response.json()
    assert [item["conversation_id"] for item in body["conversations"]] == [
        "chat:test-b",
        "chat:test-a",
    ]
    assert body["conversations"][0]["last_text"] == "second message"
    assert body["conversations"][0]["priority"] == "normal"
