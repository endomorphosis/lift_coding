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


def test_dev_media_upload_saves_image_file(tmp_path, test_user_id):
    image_bytes = b"\x89PNG\r\n\x1a\nfakepng"
    payload = {
        "data_base64": base64.b64encode(image_bytes).decode("ascii"),
        "media_kind": "image",
        "format": "png",
        "mime_type": "image/png",
    }

    with patch.dict(
        os.environ,
        {
            "HANDSFREE_AUTH_MODE": "dev",
            "HANDSFREE_DEV_MEDIA_DIR": str(tmp_path),
            "HANDSFREE_DEV_MEDIA_MAX_BYTES": "1048576",
        },
    ):
        resp = client.post(
            "/v1/dev/media",
            headers={"X-User-Id": test_user_id},
            json=payload,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["format"] == "png"
        assert body["media_kind"] == "image"
        assert body["mime_type"] == "image/png"
        assert body["bytes"] == len(image_bytes)
        saved_path = Path(body["uri"].removeprefix("file://"))
        assert saved_path.exists()
        assert saved_path.read_bytes() == image_bytes


def test_dev_media_upload_rejects_invalid_media_kind(test_user_id):
    payload = {
        "data_base64": base64.b64encode(b"fake").decode("ascii"),
        "media_kind": "document",
        "format": "pdf",
    }

    with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "dev"}):
        resp = client.post(
            "/v1/dev/media",
            headers={"X-User-Id": test_user_id},
            json=payload,
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["message"] == "media_kind must be one of: image, video"


def test_dev_media_upload_forbidden_outside_dev_mode(test_user_id):
    payload = {
        "data_base64": base64.b64encode(b"fake").decode("ascii"),
        "media_kind": "image",
        "format": "jpg",
    }

    with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "jwt"}):
        resp = client.post(
            "/v1/dev/media",
            headers={"X-User-Id": test_user_id},
            json=payload,
        )
        assert resp.status_code in (401, 403)


def test_dev_media_upload_normalizes_media_kind_case(tmp_path, test_user_id):
    image_bytes = b"\x89PNG\r\n\x1a\ncasekind"
    payload = {
        "data_base64": base64.b64encode(image_bytes).decode("ascii"),
        "media_kind": "ImAgE",
        "format": "png",
    }

    with patch.dict(
        os.environ,
        {
            "HANDSFREE_AUTH_MODE": "dev",
            "HANDSFREE_DEV_MEDIA_DIR": str(tmp_path),
            "HANDSFREE_DEV_MEDIA_MAX_BYTES": "1048576",
        },
    ):
        resp = client.post(
            "/v1/dev/media",
            headers={"X-User-Id": test_user_id},
            json=payload,
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["media_kind"] == "image"
    saved_path = Path(body["uri"].removeprefix("file://"))
    assert saved_path.exists()
    assert saved_path.read_bytes() == image_bytes


def test_dev_media_upload_uses_default_video_format(tmp_path, test_user_id):
    video_bytes = b"\x00\x00\x00\x20ftypisomvideodata"
    payload = {
        "data_base64": base64.b64encode(video_bytes).decode("ascii"),
        "media_kind": "video",
    }

    with patch.dict(
        os.environ,
        {
            "HANDSFREE_AUTH_MODE": "dev",
            "HANDSFREE_DEV_MEDIA_DIR": str(tmp_path),
            "HANDSFREE_DEV_MEDIA_MAX_BYTES": "1048576",
        },
    ):
        resp = client.post(
            "/v1/dev/media",
            headers={"X-User-Id": test_user_id},
            json=payload,
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["media_kind"] == "video"
    assert body["format"] == "mp4"
    saved_path = Path(body["uri"].removeprefix("file://"))
    assert saved_path.suffix == ".mp4"
    assert saved_path.exists()
    assert saved_path.read_bytes() == video_bytes