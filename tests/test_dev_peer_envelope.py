"""Tests for dev peer envelope ingress."""

import asyncio
import base64
import os
import sys
import types
from unittest.mock import patch

from fastapi import HTTPException

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

from handsfree.api import dev_ingest_peer_envelope
from handsfree.models import DevPeerEnvelopeRequest
from handsfree.transport.libp2p_bluetooth import (
    CHAT_PROTOCOL_ID,
    PeerEnvelope,
    decode_transport_envelope,
    encode_chat_message_payload,
    encode_transport_message,
    encode_transport_envelope,
)


async def _call_endpoint(test_user_id: str, payload: dict):
    request = DevPeerEnvelopeRequest(**payload)
    with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "dev"}):
        return await dev_ingest_peer_envelope(request, test_user_id)


def test_dev_peer_envelope_accepts_handshake(test_user_id):
    envelope = PeerEnvelope(
        kind="handshake",
        peer_id="12D3KooWpeerA",
        session_id="session1234",
        capabilities=["bluetooth-driver-bridge", "handshake-v1"],
    )
    payload = {
        "peer_ref": "peer://demo-a",
        "frame_base64": base64.b64encode(encode_transport_envelope(envelope)).decode("ascii"),
    }

    response = asyncio.run(_call_endpoint(test_user_id, payload))

    assert response.accepted is True
    assert response.kind == "handshake"
    assert response.peer_id == "12D3KooWpeerA"
    assert response.session_id == "session1234"
    assert response.ack_frame_base64 is None


def test_dev_peer_envelope_returns_ack_for_message(test_user_id):
    message_payload = base64.b64encode(b'{"type":"ping"}').decode("ascii")
    envelope = PeerEnvelope(
        kind="message",
        peer_id="12D3KooWpeerB",
        session_id="session5678",
        payload_b64=message_payload,
    )
    payload = {
        "peer_ref": "peer://demo-b",
        "frame_base64": base64.b64encode(encode_transport_envelope(envelope)).decode("ascii"),
    }

    response = asyncio.run(_call_endpoint(test_user_id, payload))

    assert response.accepted is True
    assert response.kind == "message"
    assert response.payload_text == '{"type":"ping"}'
    assert response.ack_frame_base64

    ack_frame = base64.b64decode(response.ack_frame_base64, validate=True)
    ack = decode_transport_envelope(ack_frame)
    assert ack.kind == "ack"
    assert ack.peer_id == "12D3KooWpeerB"
    assert ack.session_id == "session5678"
    assert ack.acked_message_id == envelope.message_id


def test_dev_peer_envelope_decodes_chat_protocol_message(test_user_id):
    envelope = PeerEnvelope(
        kind="message",
        peer_id="12D3KooWpeerChat",
        session_id="session-chat-1",
        payload_b64=encode_transport_message(
            CHAT_PROTOCOL_ID,
            encode_chat_message_payload("hello from glasses", sender_peer_id="12D3KooWpeerChat"),
        ),
    )
    payload = {
        "peer_ref": "peer://chat-a",
        "frame_base64": base64.b64encode(encode_transport_envelope(envelope)).decode("ascii"),
    }

    response = asyncio.run(_call_endpoint(test_user_id, payload))

    assert response.accepted is True
    assert response.protocol == CHAT_PROTOCOL_ID
    assert response.payload_json == {
        "type": "chat",
        "text": "hello from glasses",
        "sender_peer_id": "12D3KooWpeerChat",
    }


def test_dev_peer_envelope_rejects_invalid_base64(test_user_id):
    try:
        asyncio.run(_call_endpoint(test_user_id, {"peer_ref": "peer://bad", "frame_base64": "!!!"}))
    except HTTPException as exc:
        detail = exc.detail
        assert exc.status_code == 400
        assert detail["error"] == "invalid_request"
    else:
        raise AssertionError("Expected HTTPException for invalid base64")
