import base64
import os
import sys
import types
from pathlib import Path
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

from handsfree.api import app

client = TestClient(app)


def test_dev_audio_upload_saves_file(tmp_path, test_user_id):
    audio_bytes = b"RIFFxxxxWAVEfmt "  # not a real WAV; fine for upload smoke test
    payload = {
        "data_base64": base64.b64encode(audio_bytes).decode("ascii"),
        "format": "wav",
    }

    # Use patch.dict style like the existing suite
    with patch.dict(
        os.environ,
        {
            "HANDSFREE_AUTH_MODE": "dev",
            "HANDSFREE_DEV_AUDIO_DIR": str(tmp_path),
            "HANDSFREE_DEV_AUDIO_MAX_BYTES": "1048576",
        },
    ):
        resp = client.post(
            "/v1/dev/audio",
            headers={"X-User-Id": test_user_id},
            json=payload,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["format"] == "wav"
        assert body["bytes"] == len(audio_bytes)
        assert body["uri"].startswith("file://")

        # Verify the saved file exists under tmp_path
        saved_path = Path(body["uri"].removeprefix("file://"))
        assert saved_path.exists()
        assert saved_path.read_bytes() == audio_bytes


def test_dev_audio_upload_forbidden_outside_dev_mode(test_user_id):
    payload = {
        "data_base64": base64.b64encode(b"hello").decode("ascii"),
        "format": "m4a",
    }

    with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "jwt"}):
        resp = client.post(
            "/v1/dev/audio",
            headers={"X-User-Id": test_user_id},
            json=payload,
        )
        assert resp.status_code in (401, 403)


def test_dev_audio_upload_accepts_audio_base64_alias(tmp_path, test_user_id):
    """Test that audio_base64 is accepted as a backwards-compatible alias for data_base64."""
    audio_bytes = b"RIFFxxxxWAVEfmt "
    payload = {
        "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),  # Using alias
        "format": "wav",
    }

    with patch.dict(
        os.environ,
        {
            "HANDSFREE_AUTH_MODE": "dev",
            "HANDSFREE_DEV_AUDIO_DIR": str(tmp_path),
            "HANDSFREE_DEV_AUDIO_MAX_BYTES": "1048576",
        },
    ):
        resp = client.post(
            "/v1/dev/audio",
            headers={"X-User-Id": test_user_id},
            json=payload,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["format"] == "wav"
        assert body["bytes"] == len(audio_bytes)
        assert body["uri"].startswith("file://")

        # Verify the saved file exists
        saved_path = Path(body["uri"].removeprefix("file://"))
        assert saved_path.exists()
        assert saved_path.read_bytes() == audio_bytes
