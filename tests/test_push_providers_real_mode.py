"""Tests for APNS/FCM providers in real mode.

These tests use respx to mock outbound HTTP calls so we don't make network
requests during CI.
"""

from __future__ import annotations

import json

import httpx
import respx

from handsfree.notifications.provider import APNSProvider, FCMProvider


def _write_ec_p8_key(tmp_path) -> str:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    key = ec.generate_private_key(ec.SECP256R1())
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    key_path = tmp_path / "apns_key.p8"
    key_path.write_text(pem, encoding="utf-8")
    return str(key_path)


def _write_service_account_json(tmp_path) -> str:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    creds = {
        "type": "service_account",
        "project_id": "my-project",
        "private_key_id": "test-key-id",
        "private_key": pem,
        "client_email": "test-sa@my-project.iam.gserviceaccount.com",
        "client_id": "1234567890",
        "token_uri": "https://oauth2.googleapis.com/token",
    }

    path = tmp_path / "service_account.json"
    path.write_text(json.dumps(creds), encoding="utf-8")
    return str(path)


@respx.mock
def test_apns_provider_real_send_success(tmp_path):
    key_path = _write_ec_p8_key(tmp_path)

    provider = APNSProvider(
        team_id="TESTTEAM123",
        key_id="TESTKEY123",
        key_path=key_path,
        bundle_id="com.example.app",
        use_sandbox=True,
        mode="real",
    )

    url = "https://api.sandbox.push.apple.com/3/device/device-token-abc123"
    route = respx.post(url).mock(return_value=httpx.Response(200, headers={"apns-id": "apns-1"}))

    result = provider.send(
        subscription_endpoint="device-token-abc123",
        notification_data={"id": "n1", "event_type": "test_event", "message": "Hello"},
    )

    assert route.called
    request = route.calls.last.request
    assert request.headers.get("apns-topic") == "com.example.app"
    assert request.headers.get("apns-push-type") == "alert"
    assert request.headers.get("authorization", "").lower().startswith("bearer ")

    assert result["ok"] is True
    assert result["delivery_id"] == "apns-1"


@respx.mock
def test_apns_provider_real_send_failure(tmp_path):
    key_path = _write_ec_p8_key(tmp_path)

    provider = APNSProvider(
        team_id="TESTTEAM123",
        key_id="TESTKEY123",
        key_path=key_path,
        bundle_id="com.example.app",
        use_sandbox=True,
        mode="real",
    )

    url = "https://api.sandbox.push.apple.com/3/device/bad-token"
    respx.post(url).mock(return_value=httpx.Response(400, json={"reason": "BadDeviceToken"}))

    result = provider.send(
        subscription_endpoint="bad-token",
        notification_data={"id": "n1", "event_type": "test_event", "message": "Hello"},
    )

    assert result["ok"] is False
    assert "BadDeviceToken" in result["message"]


@respx.mock
def test_fcm_provider_real_send_success(tmp_path):
    creds_path = _write_service_account_json(tmp_path)

    provider = FCMProvider(project_id="my-project", credentials_path=creds_path, mode="real")

    token_route = respx.post("https://oauth2.googleapis.com/token").mock(
        return_value=httpx.Response(200, json={"access_token": "ya29.test", "expires_in": 3600})
    )
    fcm_route = respx.post("https://fcm.googleapis.com/v1/projects/my-project/messages:send").mock(
        return_value=httpx.Response(200, json={"name": "projects/my-project/messages/123"})
    )

    result = provider.send(
        subscription_endpoint="fcm-token-abc",
        notification_data={"id": "n1", "event_type": "test_event", "message": "Hello"},
    )

    assert token_route.called
    assert fcm_route.called

    request = fcm_route.calls.last.request
    assert request.headers.get("authorization") == "Bearer ya29.test"

    assert result["ok"] is True
    assert result["delivery_id"].endswith("/123")
