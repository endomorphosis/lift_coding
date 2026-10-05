"""Download and check one immutable AE release without numerical providers.

This performs public HTTPS reads and stdlib serialized-tensor checks only.
It never imports Torch, executes a model, fits, or opens the private banks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath

REPO = "Publicus/legal-ir-autoencoder"
REVISION = "ce4589fa2a61ac5755af08e2f5a3a345667c2465"
PREFIX = "releases/20261004-source-reconstruction-aes-v1"
MANIFEST_SHA256 = "30e2fe3b112f60fd7f8d9494f88caaba674efdc8424a3c174a0e34570282cbf5"
MANIFEST_BYTES = 46629
CHECKER_SHA256 = "21816a6540b8e02f7dadcdf7efdf04c071f62b9e90e29199e8e878bcb9cc59e2"
CHECKER_BYTES = 9767
TOTAL_FILES = 45
TOTAL_BYTES = 12020484
MAX_FILE_BYTES = 32 * 1024**2
MAX_WALL_SECONDS = 300
SOCKET_TIMEOUT_SECONDS = 30


def require(value, reason):
    if not value:
        raise ValueError(reason)


def raw(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def decode(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result
    return json.loads(data.decode("utf-8", "strict"), object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def seal(value):
    return {**value, "content_sha256": hashlib.sha256(raw(value)).hexdigest()}


def safe_relative(value):
    require(type(value) is str and bool(value) and "\\" not in value and "\x00" not in value,
            "ordinary release path required")
    path = PurePosixPath(value)
    require(not path.is_absolute() and str(path) == value and all(part not in {".", ".."} for part in path.parts),
            "safe canonical relative release path required")
    return value


def selected_url(relative):
    safe_relative(relative)
    return "https://huggingface.co/" + REPO + "/resolve/" + REVISION + "/" + urllib.parse.quote(PREFIX + "/" + relative, safe="/")


def binding(path):
    path = Path(path).absolute()
    require(not any(p.is_symlink() for p in (path, *path.parents)) and path.is_file(), "regular nonsymlink file required")
    before = path.stat()
    require(0 < before.st_size <= MAX_FILE_BYTES, "bounded nonempty file required")
    data = path.read_bytes()
    after = path.stat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), "file changed during read")
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


class HTTPSRedirects(urllib.request.HTTPRedirectHandler):
    max_redirections = 8
    max_repeats = 2

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        address = urllib.parse.urlsplit(newurl)
        require(address.scheme == "https" and bool(address.hostname) and not address.username and not address.password,
                "HTTPS redirects without URL credentials required")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(opener, release, item, deadline):
    require(type(item) is dict and set(item) == {"path", "bytes", "sha256"}, "closed selected release file required")
    relative = safe_relative(item["path"])
    require(type(item["bytes"]) is int and 0 < item["bytes"] <= MAX_FILE_BYTES, "bounded selected file size required")
    require(type(item["sha256"]) is str and len(item["sha256"]) == 64
            and all(c in "0123456789abcdef" for c in item["sha256"]), "selected SHA256 required")
    require(time.monotonic() < deadline, "download wall budget expired")
    target = release / relative
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    require(not any(p.is_symlink() for p in (target, *target.parents)), "nonsymlink destination required")
    require(not target.exists(), "fresh download file required")
    partial = target.with_name(target.name + ".download-partial")
    selected = selected_url(relative)
    request = urllib.request.Request(selected, headers={"User-Agent": "autoformalization-release-check/1", "Accept-Encoding": "identity"})
    count = 0
    digest = hashlib.sha256()
    with opener.open(request, timeout=SOCKET_TIMEOUT_SECONDS) as response, partial.open("xb") as stream:
        os.chmod(partial, 0o600)
        require(urllib.parse.urlsplit(response.geturl()).scheme == "https", "final download transport must be HTTPS")
        length = response.headers.get("Content-Length")
        require(length is None or int(length) == item["bytes"], "HTTP content length differs")
        while True:
            require(time.monotonic() < deadline, "download wall budget expired")
            chunk = response.read(min(64 * 1024, item["bytes"] - count + 1))
            if not chunk:
                break
            count += len(chunk)
            require(count <= item["bytes"], "download exceeds selected size")
            digest.update(chunk)
            stream.write(chunk)
        require(count == item["bytes"] and digest.hexdigest() == item["sha256"], "download byte size or SHA256 differs")
        stream.flush()
        os.fsync(stream.fileno())
    # link is exclusive: a preexisting destination is never overwritten.
    os.link(partial, target, follow_symlinks=False)
    partial.unlink()
    result = binding(target)
    require(result["bytes"] == item["bytes"] and result["sha256"] == item["sha256"], "saved download pin differs")
    return {**result, "relative_path": relative, "selected_url": selected}


def checked_manifest(data):
    require(len(data) == MANIFEST_BYTES and hashlib.sha256(data).hexdigest() == MANIFEST_SHA256,
            "externally selected immutable manifest differs")
    manifest = decode(data)
    require(manifest["schema"] == "source-vector-reconstruction-public-release/v1"
            and manifest["repo_id"] == REPO and manifest["prefix"] == PREFIX, "release identity differs")
    require(manifest["content_sha256"] == hashlib.sha256(raw({k: v for k, v in manifest.items() if k != "content_sha256"})).hexdigest(),
            "manifest seal differs")
    files = manifest["files"]
    require(type(files) is list and len(files) == TOTAL_FILES - 1, "exact44 selected manifest files required")
    names = [safe_relative(item["path"]) for item in files]
    require(len(set(names)) == len(names) and "release_manifest.json" not in names, "duplicate/self-referential release file")
    require(sum(item["bytes"] for item in files) + MANIFEST_BYTES == TOTAL_BYTES, "selected total byte budget differs")
    require([(arm["lane_id"], arm["seed"]) for arm in manifest["arms"]] ==
            [(lane, seed) for lane in ("legacy8", "native384", "native768") for seed in (1729, 1730, 1731)],
            "exact ordered nine arms required")
    require(all(manifest[k] is False for k in ("qualified", "semantic_fit_authorized", "contrastive_fit_authorized",
            "source_fidelity_established", "proof_authority", "semantic_gold_created", "vector_row_tables_or_bank_bodies_included")),
            "release authority or data scope differs")
    return manifest


def verify_frozen_checker(release):
    selected = release / "verify_reconstruction_release.py"
    data = selected.read_bytes()
    require(len(data) == CHECKER_BYTES and hashlib.sha256(data).hexdigest() == CHECKER_SHA256, "externally selected checker source differs")
    namespace = {"__name__": "frozen_release_integrity_checker", "__file__": str(selected)}
    # Execute the already checked bytes, without a second source read or CLI call.
    exec(compile(data, str(selected), "exec"), namespace)
    result = namespace["verify"](release, MANIFEST_SHA256)
    require(result["files_verified"] == TOTAL_FILES - 1 and result["selected_checkpoints_verified"] == 9
            and result["model_loads"] == result["model_calls"] == result["optimizer_updates"] == 0,
            "stdlib checker execution scope differs")
    return result


def write_receipt(output, receipt):
    path = output / "download-receipt.json"
    with path.open("xb") as stream:
        os.chmod(path, 0o600)
        stream.write(json.dumps(seal(receipt), sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False).encode() + b"\n")
        stream.flush()
        os.fsync(stream.fileno())


def run(output, opener=None):
    output = Path(output)
    require(output.is_absolute() and output.parent.is_dir() and not output.exists()
            and not any(p.is_symlink() for p in (output, *output.parents)), "fresh absolute nonsymlink output directory required")
    output.mkdir(mode=0o700)
    release = output / "release"
    release.mkdir(mode=0o700)
    started = time.monotonic()
    receipt = {"schema": "immutable-source-reconstruction-HF-download/v1", "status": "download_started",
               "repo_id": REPO, "revision": REVISION, "prefix": PREFIX,
               "expected_manifest_sha256": MANIFEST_SHA256, "release_directory": str(release),
               "helper_binding": binding(__file__), "downloaded_files": [], "model_loads": 0,
               "model_calls": 0, "optimizer_updates": 0, "private_banks_read": False,
               "numerical_runtime_restore_executed": False, "qualified": False,
               "source_fidelity_established": False, "proof_authority": False,
               "transport": "HTTPS_with_HTTPS_only_redirects", "os_sandbox": False}
    try:
        opener = opener or urllib.request.build_opener(HTTPSRedirects())
        manifest_item = {"path": "release_manifest.json", "bytes": MANIFEST_BYTES, "sha256": MANIFEST_SHA256}
        receipt["downloaded_files"].append(fetch(opener, release, manifest_item, started + MAX_WALL_SECONDS))
        manifest = checked_manifest((release / "release_manifest.json").read_bytes())
        for item in manifest["files"]:
            receipt["downloaded_files"].append(fetch(opener, release, item, started + MAX_WALL_SECONDS))
        receipt["integrity_check"] = verify_frozen_checker(release)
        for item in receipt["downloaded_files"]:
            require(binding(item["path"]) == {k: item[k] for k in ("path", "bytes", "sha256")},
                    "download bytes changed during integrity check")
        require(sum(item["bytes"] for item in receipt["downloaded_files"]) == TOTAL_BYTES, "saved total size differs")
        receipt.update(status="downloaded_and_stdlib_verified", files_downloaded=TOTAL_FILES,
                       bytes_downloaded=TOTAL_BYTES, all_selected_file_pins_verified=True)
    except Exception as error:
        receipt.update(status="failed_closed", error_type=type(error).__name__, error=str(error),
                       all_selected_file_pins_verified=False, wall_seconds=time.monotonic() - started)
        write_receipt(output, receipt)
        raise
    receipt["wall_seconds"] = time.monotonic() - started
    write_receipt(output, receipt)
    return binding(output / "download-receipt.json")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-directory", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.output_directory), sort_keys=True))


if __name__ == "__main__":
    main()
