"""Offline byte-stream and immutable release checks; no network or ML calls."""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

DIRECTORY = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("bounded_release_download", DIRECTORY / "download_published_release.py")
subject = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(subject)
RELEASE = DIRECTORY.parent / "huggingface" / "source-reconstruction-aes-v1"


class Response(io.BytesIO):
    def __init__(self, data, url):
        super().__init__(data)
        self.headers = {"Content-Length": str(len(data))}
        self.url = url

    def geturl(self):
        return self.url


class OfflineOpener:
    def __init__(self, payload=None):
        self.payload = payload
        self.requests = []

    def open(self, request, timeout):
        self.requests.append((request.full_url, timeout))
        relative = urllib.parse.unquote(request.full_url.split(subject.PREFIX + "/", 1)[1])
        return Response(self.payload if self.payload is not None else (RELEASE / relative).read_bytes(), request.full_url)


@pytest.mark.parametrize("path", ["/absolute", "../outside", "folder/../file", "folder//file", "folder/./file", "back\\slash", "", "bad\x00file"])
def test_release_path_rejects_noncanonical_or_escaping_destinations(path):
    with pytest.raises(ValueError):
        subject.safe_relative(path)


def test_manifest_requires_external_selected_whole_file_hash():
    selected = (RELEASE / "release_manifest.json").read_bytes()
    assert len(subject.checked_manifest(selected)["arms"]) == 9
    with pytest.raises(ValueError, match="immutable manifest"):
        subject.checked_manifest(selected.replace(b"native768", b"native769", 1))


@pytest.mark.parametrize("payload", [b"wrong", b"correctextra", b"correcx"])
def test_byte_stream_truncation_oversize_and_corruption_never_install_target(payload, tmp_path):
    item = {"path": "file", "bytes": 7, "sha256": hashlib.sha256(b"correct").hexdigest()}
    with pytest.raises(ValueError):
        subject.fetch(OfflineOpener(payload), tmp_path, item, time.monotonic() + 5)
    assert not (tmp_path / "file").exists()


def test_existing_download_output_is_never_reused_or_modified(tmp_path):
    output = tmp_path / "existing"
    output.mkdir()
    marker = output / "marker"
    marker.write_bytes(b"untouched")
    with pytest.raises(ValueError, match="fresh absolute"):
        subject.run(output, OfflineOpener())
    assert marker.read_bytes() == b"untouched"


def test_https_redirect_rejects_transport_downgrade_and_url_credentials():
    handler = subject.HTTPSRedirects()
    request = urllib.request.Request("https://huggingface.co/start")
    for target in ("http://cdn.example/payload", "https://user:password@cdn.example/payload"):
        with pytest.raises(ValueError, match="HTTPS redirects"):
            handler.redirect_request(request, None, 302, "redirect", {}, target)
    selected = handler.redirect_request(request, None, 302, "redirect", {}, "https://cdn.example/payload")
    assert selected.full_url == "https://cdn.example/payload"


def test_complete_offline_release_download_runs_only_frozen_stdlib_checker(tmp_path):
    opener = OfflineOpener()
    output = tmp_path / "download"
    reference = subject.run(output, opener)
    receipt = json.loads(Path(reference["path"]).read_text())
    assert receipt["status"] == "downloaded_and_stdlib_verified"
    assert receipt["files_downloaded"] == len(opener.requests) == 45
    assert receipt["bytes_downloaded"] == 12020484
    assert receipt["integrity_check"]["selected_checkpoints_verified"] == 9
    assert receipt["model_loads"] == receipt["model_calls"] == receipt["optimizer_updates"] == 0
    assert receipt["numerical_runtime_restore_executed"] is False
    assert all("/resolve/" + subject.REVISION + "/" in url for url, _ in opener.requests)
    assert all(timeout == 30 for _, timeout in opener.requests)
    assert len(list((output / "release").rglob("*.download-partial"))) == 0
    assert len([path for path in (output / "release").rglob("*") if path.is_file()]) == 45


def test_failure_receipt_keeps_partial_work_and_truthful_zero_model_scope(tmp_path):
    class FailingOpener:
        def open(self, request, timeout):
            raise urllib.error.URLError("offline fixture")
    output = tmp_path / "failure"
    with pytest.raises(urllib.error.URLError):
        subject.run(output, FailingOpener())
    receipt = json.loads((output / "download-receipt.json").read_text())
    assert receipt["status"] == "failed_closed" and receipt["all_selected_file_pins_verified"] is False
    assert receipt["downloaded_files"] == []
    assert receipt["model_loads"] == receipt["model_calls"] == receipt["optimizer_updates"] == 0
