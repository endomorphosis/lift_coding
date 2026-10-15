"""Bounded Stage AA host orchestration; no implicit Docker invocation."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import time

AA = Path(__file__).resolve().parent
CHECKOUT = AA / "checkout"
PINNED = Path("/home/barberb/lift_coding/maintenance/terminal-compact-retrieval-20261011-01/pinned-dependencies-v10")
PREVIOUS = Path("/home/barberb/lift_coding/maintenance/terminal-checked-worker-context-20261013-01")
CONTAINER = "ipfs-admitted-context-budget-aa14"
IMAGE = "ipfs-supervisor-preview-worker:20261005-r3"
LEAN = Path("/home/barberb/.elan/toolchains/leanprover--lean4---v4.34.1")
TOKENIZER = Path("/home/barberb/lift_coding/maintenance/terminal-token-pairing-20261012-01/pinned-host-tokenizer")
CONTAINER_PYTHON = "/opt/ipfs-supervisor/venv/bin/python"
OWNER_ENV = {
    "HOME": "/opt/ipfs-supervisor/home",
    "PYTHONPATH": "/opt/ipfs-supervisor/source:/opt/ipfs-supervisor/datasets:/opt/ipfs-supervisor/kit:/opt/ipfs-supervisor/tokenizer",
    "PYTHONDONTWRITEBYTECODE": "1", "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1", "TOKENIZERS_PARALLELISM": "false",
    "TIKTOKEN_CACHE_DIR": "/opt/ipfs-supervisor/home/tokenizer-cache",
    "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
}


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode()


def signature(info):
    return tuple(getattr(info, name) for name in (
        "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
        "st_size", "st_mtime_ns", "st_ctime_ns"))


def public_bytes(path, limit=8 * 1024 * 1024):
    path = Path(path)
    if not path.is_absolute() or path.resolve(strict=True) != path:
        raise ValueError("exact canonical named public file required")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > limit:
            raise ValueError("bounded regular single-link named public file required")
        chunks, count = [], 0
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            chunks.append(chunk)
            count += len(chunk)
            if count > limit:
                raise ValueError("named public file exceeds bound")
        raw = b"".join(chunks)
        if len(raw) != before.st_size or signature(before) != signature(os.fstat(fd)) or signature(before) != signature(path.lstat()):
            raise ValueError("named public file changed during capture")
        return raw
    finally:
        os.close(fd)


def pin(path, limit=8 * 1024 * 1024):
    raw = public_bytes(path, limit)
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def write_exclusive(path, raw, mode=0o600):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
        os.fchmod(stream.fileno(), mode)


class RuntimeFreeze:
    """Retain the root freeze manifest and its exact declared producer files."""
    def __init__(self, expected_sha256):
        if type(expected_sha256) is not str or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
            raise ValueError("explicit final runtime freeze SHA256 required")
        self._witnesses = []
        self._closed = False
        self.path = AA / "runtime-source-pins-14.json"
        try:
            self.raw = self._retain(self.path)
            self.digest = hashlib.sha256(self.raw).hexdigest()
            if self.digest != expected_sha256:
                raise ValueError("runtime freeze manifest differs from explicit root pin")
            value = json.loads(self.raw)
            if type(value) is not dict or value.get("schema") != "terminal-admitted-context-runtime-freeze@1":
                raise ValueError("exact admitted-context runtime freeze schema required")
            rows = value.get("files")
            if type(rows) is not list or len(rows) != 6:
                raise ValueError("exact six final runtime production files required")
            seen = set()
            for row in rows:
                if type(row) is not dict or set(row) != {"path", "relative_path", "bytes", "sha256"}:
                    raise ValueError("closed runtime producer pin required")
                relative = Path(row["relative_path"])
                if relative.is_absolute() or ".." in relative.parts or relative.as_posix() != row["relative_path"] or relative.suffix != ".py":
                    raise ValueError("exact relative Python producer path required")
                path = CHECKOUT / relative
                if str(path) != row["path"] or str(path) in seen:
                    raise ValueError("freeze producer must be a unique exact AA checkout path")
                seen.add(str(path))
                self._retain(path, row)
            scripts = value.get("scripts", [])
            if type(scripts) is not list:
                raise ValueError("optional script pins must be an explicit list")
            for row in scripts:
                if type(row) is not dict or set(row) not in ({"path", "bytes", "sha256"}, {"path", "relative_path", "bytes", "sha256"}):
                    raise ValueError("closed optional authored script pin required")
                path = Path(row["path"])
                if path.parent != AA or path.suffix != ".py" or str(path) in seen or ("relative_path" in row and row["relative_path"] != path.name):
                    raise ValueError("only unique explicitly named AA-root Python harnesses may be pinned")
                seen.add(str(path))
                self._retain(path, row)
            self.check()
        except BaseException:
            self.close()
            raise

    def _retain(self, path, expected=None):
        if path.resolve(strict=True) != path:
            raise ValueError("canonical source producer required")
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        before = os.fstat(descriptor)
        try:
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_uid not in {0, os.geteuid()} or not 0 <= before.st_size <= 8 * 1024 * 1024:
                raise ValueError("bounded owned/root-readable producer required")
            with os.fdopen(descriptor, "rb", closefd=False) as stream:
                raw = stream.read(8 * 1024 * 1024 + 1)
            if len(raw) != before.st_size or signature(before) != signature(os.fstat(descriptor)) or signature(before) != signature(path.lstat()):
                raise ValueError("original producer custody changed during capture")
            digest = hashlib.sha256(raw).hexdigest()
            if expected is not None and (type(expected["bytes"]) is not int or len(raw) != expected["bytes"] or type(expected["sha256"]) is not str or not re.fullmatch(r"[0-9a-f]{64}", expected["sha256"]) or digest != expected["sha256"]):
                raise ValueError("original producer bytes differ from freeze")
            self._witnesses.append((path, descriptor, before, digest))
            return raw
        except BaseException:
            os.close(descriptor)
            raise

    def check(self):
        if self._closed:
            raise ValueError("closed runtime freeze cannot authorize setup")
        for path, descriptor, before, digest in self._witnesses:
            if path.resolve(strict=True) != path or signature(before) != signature(os.fstat(descriptor)) or signature(before) != signature(path.lstat()):
                raise ValueError("original freeze/producer stat witness changed")
            os.lseek(descriptor, 0, os.SEEK_SET)
            with os.fdopen(descriptor, "rb", closefd=False) as stream:
                raw = stream.read(8 * 1024 * 1024 + 1)
            if len(raw) != before.st_size or hashlib.sha256(raw).hexdigest() != digest or signature(before) != signature(os.fstat(descriptor)):
                raise ValueError("original freeze/producer bytes changed")
            fresh = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                if signature(os.fstat(fresh)) != signature(before):
                    raise ValueError("fresh producer path changed")
                with os.fdopen(fresh, "rb", closefd=False) as stream:
                    fresh_raw = stream.read(8 * 1024 * 1024 + 1)
                if fresh_raw != raw or signature(os.fstat(fresh)) != signature(before) or signature(path.lstat()) != signature(before):
                    raise ValueError("fresh producer bytes/stat changed")
            finally:
                os.close(fresh)

    def close(self):
        if not self._closed:
            for _, descriptor, _, _ in self._witnesses:
                os.close(descriptor)
            self._closed = True

    def to_dict(self):
        return {"path": str(self.path), "bytes": len(self.raw), "sha256": self.digest}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze-sha256", required=True,
                        help="Root's final AA/runtime-source-pins-14.json SHA256; setup remains gated until it exists.")
    return parser.parse_args()


class EvidenceRun:
    def __init__(self, namespace, freeze):
        self.output = AA / namespace
        self.output.mkdir(mode=0o700)
        os.environ["IPFS_ACCELERATE_META_INDEX_DUCKDB"] = str(self.output / "host-meta-index.duckdb")
        os.environ["IPFS_ACCELERATE_PYTEST_SEAL_DUCKDB"] = str(self.output / "host-pytest-seal.duckdb")
        os.environ["IPFS_ACCELERATE_AGENT_ORCHESTRATION_DIR"] = str(self.output / "host-orchestration")
        self.freeze = freeze
        self.calls = 0

    def save(self, name, value):
        write_exclusive(self.output / name, wire(value))

    def command(self, label, argv, *, input_bytes=None, timeout=180, allow_failure=False, cleanup=False):
        freeze_error = None
        try:
            self.freeze.check()
        except BaseException as error:
            if not cleanup:
                raise
            freeze_error = {"type": type(error).__name__, "message": str(error)[:1024]}
        begin = time.monotonic_ns()
        timeout_error = None
        try:
            result = subprocess.run(argv, input=input_bytes, capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired as error:
            timeout_error = error
            result = subprocess.CompletedProcess(argv, None, error.stdout or b"", error.stderr or b"")
        stdout = self.output / (label + ".stdout")
        stderr = self.output / (label + ".stderr")
        write_exclusive(stdout, result.stdout)
        write_exclusive(stderr, result.stderr)
        self.save(label + ".json", {"argv": argv, "returncode": result.returncode,
                  "timed_out": timeout_error is not None,
                  "owned_cleanup_only": cleanup, "freeze_error": freeze_error,
                  "elapsed_milliseconds": (time.monotonic_ns() - begin) // 1_000_000,
                  "stdout": pin(stdout), "stderr": pin(stderr)})
        if not cleanup:
            self.freeze.check()
        if timeout_error is not None:
            raise timeout_error
        if result.returncode and not allow_failure:
            raise RuntimeError("actual setup command failed; retained receipt: " + label)
        return result

    def owner_argv(self, script, *, state_namespace, extra_args=()):
        environment = dict(OWNER_ENV)
        environment.update({
            "IPFS_ACCELERATE_META_INDEX_DUCKDB": "/opt/ipfs-supervisor/state/" + state_namespace + "-meta.duckdb",
            "IPFS_ACCELERATE_PYTEST_SEAL_DUCKDB": "/opt/ipfs-supervisor/state/" + state_namespace + "-seal.duckdb",
            "IPFS_ACCELERATE_AGENT_ORCHESTRATION_DIR": "/opt/ipfs-supervisor/state/" + state_namespace + "-orchestration",
        })
        argv = ["docker", "exec", "--user", "supervisor", "--workdir", "/app"]
        for key, value in sorted(environment.items()):
            argv += ["--env", key + "=" + value]
        return argv + [CONTAINER, CONTAINER_PYTHON, "-B", "-P", script, *extra_args]

    def upload_program(self, local, destination):
        self.command("upload-" + local.stem, ["docker", "cp", str(local), CONTAINER + ":" + destination])
        self.command("protect-" + local.stem, ["docker", "exec", "--user", "root", CONTAINER,
                     CONTAINER_PYTHON, "-I", "-c",
                     "import os,pathlib; p=pathlib.Path(" + repr(destination) + "); os.chown(p,0,0); p.chmod(0o444)"])
