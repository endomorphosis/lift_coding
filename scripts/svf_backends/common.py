#!/usr/bin/env python3
"""Real, bounded owner operations. Readiness never grants task/app completion.

An existing listener is used only after its live procfs identity is bound to
the checked-in owner adapter and its declared loopback port. Missing adapters
may be started by --ensure on that vacant port with isolated campaign state.
Foreign listeners and services are never stopped, reconfigured or replaced.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time
from urllib.parse import urlsplit
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[2]
OWNERS = {"ipfs_kit_py": "kit", "ipfs_datasets_py": "datasets", "ipfs_accelerate_py": "accelerate"}
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
TIMEOUT = 30


class ReadinessError(RuntimeError):
    pass


def require(value, message: str) -> None:
    if not value:
        raise ReadinessError(message)


def wire(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def raw_cid(data: bytes) -> str:
    return "b" + base64.b32encode(bytes([1, 0x55, 0x12, 32]) + hashlib.sha256(data).digest()).decode().lower().rstrip("=")


def confined(root: Path, value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    require(path.is_relative_to(root) and ".." not in path.parts, "path is outside campaign repository")
    current = root
    for part in path.relative_to(root).parts:
        current /= part
        require(not current.is_symlink(), "symlink in campaign path")
    require(path.resolve().is_relative_to(root), "resolved path is outside campaign repository")
    return path


def endpoint(value: str) -> str:
    parsed = urlsplit(value)
    require(parsed.scheme == "http" and parsed.hostname == "127.0.0.1" and parsed.port is not None
            and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment
            and parsed.path in {"", "/", "/mcp"}, "endpoint must be a credential-free IPv4 loopback HTTP origin")
    require(1024 <= parsed.port <= 65535, "endpoint port is outside its allowed bound")
    return f"http://127.0.0.1:{parsed.port}"


def atomic_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    with temporary.open("xb") as handle:
        handle.write(wire(value) + b"\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def process_identity(pid: int) -> dict:
    path = Path("/proc") / str(pid)
    value = (path / "stat").read_text().rsplit(")", 1)[1].split()
    return {"pid": pid, "start_ticks": value[19], "uid": path.stat().st_uid,
            "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip()}


def listener_identity(root: Path, origin: str, owner: str) -> dict | None:
    port = urlsplit(endpoint(origin)).port
    inodes = set()
    for table in ("tcp", "tcp6"):
        for row in Path("/proc/net", table).read_text().splitlines()[1:]:
            parts = row.split()
            if parts[3] == "0A" and int(parts[1].rsplit(":", 1)[1], 16) == port:
                inodes.add(parts[9])
    if not inodes:
        return None
    matches = []
    for path in Path("/proc").iterdir():
        if not path.name.isdigit():
            continue
        try:
            if path.stat().st_uid != os.getuid():
                continue
            if not any(fd.readlink().as_posix() in {f"socket:[{i}]" for i in inodes} for fd in (path / "fd").iterdir()):
                continue
            argv = [a.decode() for a in (path / "cmdline").read_bytes().split(b"\0") if a]
            cwd = (path / "cwd").resolve()
            script = root / "swissknife/scripts" / f"start-ipfs-{OWNERS[owner]}-mcp-compat.cjs"
            require(cwd == root / "swissknife" and len(argv) > 1 and Path(argv[0]).name == "node"
                    and (cwd / argv[1]).resolve() == script.resolve()
                    and "--port" in argv and argv[argv.index("--port") + 1] == str(port),
                    "listener is not the declared local owner adapter; preserved")
            matches.append({**process_identity(int(path.name)), "owner": owner, "endpoint": origin,
                "adapter_path": script.relative_to(root).as_posix(), "adapter_sha256": sha(script.read_bytes())})
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
    require(len(matches) == 1, "listener ownership could not be proved; preserved")
    return matches[0]


def reject_errors(value) -> None:
    if isinstance(value, dict):
        require(value.get("isError") is not True and value.get("success") is not False
                and value.get("ok") is not False and not value.get("error")
                and value.get("status") not in {"error", "failed", "failure", "unavailable", "backend_error"},
                "owner returned a semantic error")
        for child in value.values():
            reject_errors(child)
    elif isinstance(value, list):
        for child in value:
            reject_errors(child)


def tool_payload(value: dict, owner: str, tool: str):
    reject_errors(value)
    receipt = value.get("receipt") or {}
    native = (owner == "ipfs_accelerate_py" and receipt.get("adapter") == "swissknife-native-accelerate")
    require((receipt.get("adapter") == f"swissknife-ipfs-{OWNERS[owner]}-compat" or native)
            and receipt.get("tool") == tool and receipt.get("status") == "ok", "owner/tool receipt binding differs")
    require(receipt.get("execution_mode") != "validated_preview", "preview-only result is not execution")
    content = value.get("content")
    require(isinstance(content, list) and len(content) == 1, "owner must return one bounded semantic payload")
    item = content[0]
    result = item.get("json") if item.get("type") == "json" else json.loads(item["text"])
    reject_errors(result)
    if native:
        require(type(result) is dict and receipt.get("owner") == owner, "native receipt owner differs")
        provenance = result.get("native_provenance", {})
        require(provenance == receipt.get("native_provenance") and provenance.get("schema") == "swissknife.native-accelerate-execution.v1"
                and provenance.get("owner") == owner and provenance.get("simulated") is False
                and provenance.get("echo_fallback") is False, "native owner provenance differs")
    return result


class Transport:
    def __init__(self, root: Path, origin: str, owner: str, output: Path):
        self.root, self.origin, self.owner, self.output = root, endpoint(origin), owner, output
        self.identity = listener_identity(root, self.origin, owner)
        require(self.identity is not None, "owner listener is missing")
        self.records = []
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def rpc(self, method: str, params: dict):
        require(listener_identity(self.root, self.origin, self.owner) == self.identity, "owner process changed before request")
        request_id = "svf-readiness:" + uuid.uuid4().hex
        request = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        prefix = f"{len(self.records):02d}-{self.owner}-{method.replace('/', '-')}"
        request_path = self.output / (prefix + ".request.json")
        response_path = self.output / (prefix + ".response.json")
        request_bytes = wire(request)
        request_path.write_bytes(request_bytes)
        req = urllib.request.Request(self.origin + "/mcp", data=request_bytes, headers={"Content-Type": "application/json"})
        try:
            with self.opener.open(req, timeout=TIMEOUT) as response:
                data = response.read(MAX_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as exc:
            response_path.write_bytes(exc.read(MAX_RESPONSE_BYTES + 1))
            raise ReadinessError(f"owner HTTP status {exc.code}") from exc
        require(len(data) <= MAX_RESPONSE_BYTES, "owner response exceeds its byte bound")
        response_path.write_bytes(data)
        record = {"owner": self.owner, "method": method, "tool": params.get("name"), "request_id": request_id,
                  "request_path": request_path.relative_to(self.root).as_posix(), "request_sha256": sha(request_bytes),
                  "response_path": response_path.relative_to(self.root).as_posix(), "response_sha256": sha(data)}
        self.records.append(record)
        value = json.loads(data)
        require(value.get("jsonrpc") == "2.0" and value.get("id") == request_id and "error" not in value,
                "JSON-RPC request/result correlation failed")
        require(listener_identity(self.root, self.origin, self.owner) == self.identity, "owner process changed during request")
        return value["result"]

    def catalog(self, names: list[str]) -> dict[str, dict]:
        tools = self.rpc("tools/list", {}).get("tools")
        require(isinstance(tools, list) and len(tools) <= 2000, "invalid bounded MCP catalog")
        registry = {t.get("name"): t for t in tools if isinstance(t, dict)}
        require(len(registry) == len(tools), "duplicate or malformed tool descriptors")
        for name in names:
            schema = (registry.get(name) or {}).get("inputSchema")
            require(isinstance(schema, dict) and schema.get("type") == "object", "required native tool/schema is unavailable: " + name)
        return registry

    def health(self, origin: str | None = None) -> dict:
        require(listener_identity(self.root, self.origin, self.owner) == self.identity, "owner changed before health request")
        target = endpoint(origin or self.origin)
        with self.opener.open(target + "/mcp/health", timeout=TIMEOUT) as response:
            data = response.read(MAX_RESPONSE_BYTES + 1)
        require(len(data) <= MAX_RESPONSE_BYTES, "owner health response exceeds its byte bound")
        name = self.output / f"{len(self.records):02d}-{self.owner}-health.response.json"
        name.write_bytes(data)
        self.records.append({"owner": self.owner, "method": "GET /mcp/health", "endpoint": target,
            "response_path": name.relative_to(self.root).as_posix(), "response_sha256": sha(data)})
        require(listener_identity(self.root, self.origin, self.owner) == self.identity, "owner changed during health request")
        value = json.loads(data)
        require(type(value) is dict and value.get("status") == "ok", "owner is not ready")
        return value

    def call(self, tool: str, args: dict):
        return tool_payload(self.rpc("tools/call", {"name": tool, "arguments": args}), self.owner, tool)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ReadinessError("owner redirects are forbidden")


def ensure_service(root: Path, origin: str, owner: str, runtime: Path, config: dict, ensure: bool) -> dict:
    identity = listener_identity(root, origin, owner)
    if identity:
        return identity
    require(ensure, "owner listener is missing; --ensure is required to start its isolated adapter")
    service = confined(root, runtime / "services" / owner)
    service.mkdir(parents=True, exist_ok=True)
    port = urlsplit(origin).port
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", port))  # Never replace an occupied listener.
    env = os.environ.copy()
    for name in list(env):
        if "TASK_P2P" in name or "TASK_WORKER_HOOK" in name:
            env.pop(name)
    env.update(MCPPLUSPLUS_ARTIFACT_STORE_DIR=str(service / "artifacts"),
               MCPPLUSPLUS_UCAN_KEY_DIR=str(service / "identity"), MCPPLUSPLUS_EVENT_DAG_DIR=str(service / "dag"),
               MCPPLUSPLUS_HELIA_REPO=str(service / "helia"), MCPPLUSPLUS_HELIA_LIBP2P="0",
               IPFS_ACCELERATE_PY_TASK_P2P_AUTO_DISCOVERY="0", IPFS_ACCELERATE_PY_TASK_P2P_ANNOUNCE_FILE="0",
               IPFS_DATASETS_PY_ROOT=str(root / "external/ipfs_datasets"),
               IPFS_DATASETS_CONTRACT_PYTHON=str(native_python(root, config)))
    if owner == "ipfs_kit_py":
        require(config.get("kuboApi"), "missing native Kubo configuration; no replacement owner is fabricated")
        env["IPFS_KIT_KUBO_API"] = endpoint(config["kuboApi"])
    script = root / "swissknife/scripts" / f"start-ipfs-{OWNERS[owner]}-mcp-compat.cjs"
    with (service / "service.log").open("ab") as log:
        child = subprocess.Popen([shutil.which("node") or "node", str(script), "--host", "127.0.0.1", "--port", str(port)],
            cwd=root / "swissknife", env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline and child.poll() is None:
        identity = listener_identity(root, origin, owner)
        if identity and identity["pid"] == child.pid:
            atomic_json(service / "identity.json", {**identity, "campaign_owned": True, "started_at": dt.datetime.now(dt.timezone.utc).isoformat()})
            return identity
        time.sleep(0.1)
    if child.poll() is None:
        child.terminate()  # Only the exact child created above, never an observed listener.
    raise ReadinessError("campaign-owned adapter failed to bind within its startup deadline")


def native_python(root: Path, config: dict) -> Path:
    # Virtual environments normally symlink their final executable to the
    # system interpreter. Permit that final link, while confining its parent.
    if config.get("python"):
        candidate = Path(config["python"])
        if not candidate.is_absolute():
            candidate = root / candidate
        confined(root, candidate.parent)
        require(candidate.name in {"python", "python3", "python3.12"}, "unexpected native Python executable")
        candidates = [candidate]
    else:
        candidates = [root / "external/ipfs_datasets/.venv/bin/python", root / ".venv/bin/python", Path(sys.executable)]
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    raise ReadinessError("native owner Python runtime is unavailable")


def require_local_queue_routing(env: dict[bytes, bytes]) -> None:
    """Never submit a fixture through ambient remote peer/announce routing."""
    for key, value in env.items():
        if b"TASK_P2P_REMOTE" in key:
            require(not value, "owner has foreign remote task routing; use a campaign-owned endpoint")
    announcement = env.get(b"IPFS_ACCELERATE_PY_TASK_P2P_ANNOUNCE_FILE", env.get(b"ipfs_accelerate_py_TASK_P2P_ANNOUNCE_FILE"))
    if announcement is not None and announcement.strip().lower() in {b"0", b"false", b"no", b"off"}:
        return
    cache = env.get(b"XDG_CACHE_HOME") or os.fsencode(Path(os.fsdecode(env.get(b"HOME", os.fsencode(Path.home())))) / ".cache")
    candidates = [Path(os.fsdecode(cache)) / "ipfs_accelerate_py/task_p2p_announce.json"]
    if announcement:
        candidates.append(Path(os.fsdecode(announcement)))
    require(not any(path.exists() for path in candidates), "owner has ambient peer announcement; use a campaign-owned endpoint")


def store_fixture(client: Transport, path: Path, data: bytes) -> dict:
    client.catalog(["ipfs_add", "ipfs_cat"])
    added = client.call("ipfs_add", {"content": data.decode(), "dry_run": False})
    cid = added.get("cid")
    require(cid == raw_cid(data) and added.get("stored") is True, "native owner did not store the exact raw-CID fixture")
    got = client.call("ipfs_cat", {"cid": cid, "dry_run": False})
    actual = base64.b64decode(got.get("bytes_base64", ""), validate=True)
    require(actual == data and got.get("cid") == cid, "native IPFS retrieval differs from independently hashed fixture bytes")
    return {"cid": cid, "sha256": sha(actual), "size_bytes": len(actual), "real_bytes_verified": True}


def verify_scheduler_result(task, task_id: str, worker_id: str, nonce: str, fixture: bytes) -> dict:
    require(isinstance(task, dict), "actual owner queue returned no record")
    result = task.get("result") or {}
    require(isinstance(result, dict) and task.get("task_id") == task_id and task.get("status") == "completed"
            and task.get("assigned_worker") == worker_id and result.get("operation") == "sha256"
            and result.get("nonce") == nonce and result.get("sha256") == sha(fixture)
            and result.get("size_bytes") == len(fixture) and result.get("output") == sha(fixture),
            "actual owner queue result is missing or unusable")
    return result


def native_accelerate_qualification(client, root: Path, nonce: str) -> dict | None:
    health = client.health()
    if health.get("backend") != "native_python":
        return None  # Preserve the genuine legacy queue path only for legacy owners.
    require(health.get("upstream_available") is True, "native accelerator upstream is unavailable")
    native = client.health(health.get("native_endpoint", ""))
    source_paths = {"sdk_source_sha256": "external/ipfs_accelerate/ipfs_accelerate_py/inference_backend_manager.py",
        "backend_source_sha256": "scripts/svf_backends/native_accelerate_backend.py",
        "service_source_sha256": "scripts/svf_backends/native_accelerate_service.py"}
    expected = {key: sha(confined(root, path).read_bytes()) for key, path in source_paths.items()}
    require(native.get("native_python_backend") is True and native.get("source_contract_current") is True
            and native.get("owner") == "ipfs_accelerate_py" and native.get("device") == "cpu"
            and native.get("offline") is True and native.get("simulated") is False
            and native.get("echo_fallback") is False and all(native.get(k) == v for k, v in expected.items()),
            "native accelerator health is not bound to current actual owner sources")
    client.catalog(["list_models", "run_inference_job", "job_status"])
    models = client.call("list_models", {})
    require(any(row.get("id") == "gpt2" for row in models.get("models", [])), "qualified cached GPT-2 is unavailable")
    prompt = "short test " + nonce[:8]
    result = client.call("run_inference_job", {"model": "gpt2", "model_id": "gpt2", "input": prompt,
        "max_new_tokens": 4, "max_length": 64, "fixture_scope": "svf-native-readiness", "correlation_id": "svf-readiness:" + nonce})
    provenance = result.get("native_provenance", {})
    count = result.get("generated_token_count")
    require(provenance.get("sdk_class") == "ipfs_accelerate_py.inference_backend_manager.InferenceBackendManager"
            and provenance.get("sdk_method") == "execute_task" and all(provenance.get(k) == v for k,v in expected.items())
            and provenance.get("correlation_id") == "svf-readiness:" + nonce
            and provenance.get("offline") is True and provenance.get("external_provider_called") is False
            and type(count) is int and 1 <= count <= 4 and provenance.get("generated_token_count") == count
            and len(result.get("generated_token_ids", [])) == count
            and result.get("inference_executed") is True and result.get("queue_used") is False
            and result.get("execution_semantics") == "synchronous_completed_execution"
            and result.get("status") == "completed" and result.get("model_id") == "gpt2"
            and type(result.get("generated_text")) is str and result["generated_text"].strip()
            and result.get("output") == prompt + result["generated_text"], "native owner returned no genuine bounded generated output")
    job = result.get("job_id")
    require(type(job) is str and str(uuid.UUID(job)) == job and result.get("task_id") == job, "native job identity differs")
    read = client.call("job_status", {"job_id": job})
    read_provenance = read.get("native_provenance", {})
    require(read.get("job_id") == job and read.get("status") == "completed" and read.get("read_from_execution_record") is True
            and read_provenance.get("sdk_method") == "completed_execution_record"
            and all(read_provenance.get(k) == v for k,v in expected.items())
            and read.get("output") == result["output"] and read.get("generated_token_ids") == result["generated_token_ids"],
            "native completed execution readback differs")
    return {"operation": "native_cpu_text_generation", "model": "gpt2", "job_id": job, "generated_token_count": count,
        "output_sha256": sha(result["output"].encode()), "readback_verified": True,
        "inference_executed": True, "queue_used": False, "native_source_sha256": expected}


def qualify(owner: str, root: Path, profile: dict, output: Path, origin: str, ensure: bool) -> dict:
    config = profile.get("backendReadiness", {})
    runtime = confined(root, profile["runtimeRoot"] + "/backends")
    ensure_service(root, origin, owner, runtime, config, ensure)
    client = Transport(root, origin, owner, output)
    nonce = uuid.uuid4().hex
    rows = [{"id": 1, "text": "SVF controlled readiness fixture", "nonce": nonce}, {"id": 2, "text": "Actual backend payload", "nonce": nonce}]
    fixture = wire(rows)
    fixture_path = output / "fixture.json"
    fixture_path.write_bytes(fixture)
    extra_clients = []
    checks = []
    if owner == "ipfs_kit_py":
        checks.append({"operation": "ipfs_add_then_cat", **store_fixture(client, fixture_path, fixture)})
    elif owner == "ipfs_datasets_py":
        client.catalog(["load_dataset", "get_from_ipfs"])
        loaded = client.call("load_dataset", {"source": "json", "format": "json", "options": {"data_files": str(fixture_path), "split": "train"}, "dry_run": True})
        require(loaded.get("summary", {}).get("num_records") == len(rows), "native dataset loader did not load fixture records")
        kit_origin = endpoint(profile["backends"]["ipfs_kit_py"])
        ensure_service(root, kit_origin, "ipfs_kit_py", runtime, config, ensure)
        kit = Transport(root, kit_origin, "ipfs_kit_py", output)
        extra_clients.append(kit)
        stored = store_fixture(kit, fixture_path, fixture)
        gateway = endpoint(config.get("ipfsGateway", "http://127.0.0.1:8091"))
        fetched = client.call("get_from_ipfs", {"cid": stored["cid"], "gateway": gateway, "timeout_seconds": 10, "dry_run": True})
        content = fetched.get("content")
        require(type(content) is str and content.encode() == fixture and json.loads(content) == rows,
                "datasets owner did not return genuine exact fixture rows")
        checks.append({"operation": "load_dataset_and_retrieve_rows", "row_count": len(rows), "row_values_verified": True,
            "fixture_sha256": sha(fixture), "cid": stored["cid"], "gateway": gateway})
    elif (native_check := native_accelerate_qualification(client, root, nonce)) is not None:
        checks.append(native_check)
    else:
        client.catalog(["submit_task", "get_task"])
        # Preserve foreign routing: an adapter carrying remote task hints is not
        # safe for controlled local queue writes. Explicit owned endpoints can
        # be started with routing disabled instead of changing that process.
        pid = client.identity["pid"]
        env = dict(row.split(b"=", 1) for row in Path(f"/proc/{pid}/environ").read_bytes().split(b"\0") if b"=" in row)
        require_local_queue_routing(env)
        queue = output / "fixture-queue.duckdb"
        prompt = json.dumps({"nonce": nonce, "bytes_base64": base64.b64encode(fixture).decode()})
        task_id = client.call("submit_task", {"prompt": prompt, "model_name": "svf-sha256", "task_type": "svf.sha256", "queue_path": str(queue), "dry_run": False})
        require(type(task_id) is str and re.fullmatch(r"[0-9a-f]{32}", task_id) is not None and queue.is_file(),
                "owner did not submit the isolated local scheduler task")
        child_env = os.environ.copy()
        for key in list(child_env):
            if "TASK_P2P" in key or "TASK_WORKER_HOOK" in key:
                child_env.pop(key)
        child_env.update(PYTHONPATH=str(root / "external/ipfs_accelerate"),
            IPFS_ACCELERATE_PY_TASK_P2P_AUTO_DISCOVERY="0", IPFS_ACCELERATE_PY_TASK_P2P_ANNOUNCE_FILE="0",
            IPFS_ACCELERATE_PY_TASK_WORKER_TASK_TYPES="svf.sha256")
        worker_id = "svf-readiness-" + nonce
        command = [str(native_python(root, config)), str(root / "scripts/svf_backends/scheduler_job.py"),
            "--queue", str(queue), "--task-id", task_id, "--worker-id", worker_id]
        with (output / "scheduler.stdout").open("wb") as stdout, (output / "scheduler.stderr").open("wb") as stderr:
            run = subprocess.run(command, cwd=root, env=child_env, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, timeout=120)
        require(run.returncode == 0, "native bounded scheduler failed; inspect retained scheduler logs")
        task = client.call("get_task", {"task_id": task_id, "queue_path": str(queue), "dry_run": True})
        result = verify_scheduler_result(task, task_id, worker_id, nonce, fixture)
        checks.append({"operation": "native_scheduler_job", "task_id": task_id, "task_type": "svf.sha256",
            "worker_id": worker_id, "usable_output_sha256": result["output"], "inference_executed": False,
            "queue_path": queue.relative_to(root).as_posix(), "queue_sha256": sha(queue.read_bytes())})
    return {"checks": checks, "owner_identity": client.identity, "observations": [record for c in [client, *extra_clients] for record in c.records],
            "fixture": {"path": fixture_path.relative_to(root).as_posix(), "sha256": sha(fixture), "size_bytes": len(fixture)}}


def main(owner: str, argv=None, *, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="config/swissknife_visual_functional_supervisor.json")
    parser.add_argument("--endpoint", help="Explicit configured loopback owner endpoint")
    parser.add_argument("--ensure", action="store_true")
    parser.add_argument("--verify", action="store_true", required=True)
    args = parser.parse_args(argv)
    root = root.resolve()
    output = receipt = None
    try:
        profile_path = confined(root, args.profile)
        profile_bytes = profile_path.read_bytes()
        profile = json.loads(profile_bytes)
        require(type(profile) is dict and type(profile.get("backends")) is dict, "invalid readiness profile")
        require(str(profile.get("runtimeRoot", "")).startswith("data/agent_supervisor/"), "runtime must be campaign-owned")
        runtime = confined(root, profile["runtimeRoot"] + "/backends")
        runtime.mkdir(parents=True, exist_ok=True)
        with (runtime / (owner + ".lock")).open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            output = confined(root, runtime / "readiness" / owner / uuid.uuid4().hex)
            output.mkdir(parents=True)
            origin = endpoint(args.endpoint or profile["backends"][owner])
            receipt = {"schema": "swissknife.backend-semantic-readiness.v1", "owner": owner,
                "endpoint": origin, "observed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "profile_sha256": sha(profile_bytes), "passed": False, "semantic_verified": False,
                "work_complete": False, "completion_authority": False, "gui_acceptance": False,
                "limits": {"http_timeout_seconds": TIMEOUT, "max_response_bytes": MAX_RESPONSE_BYTES,
                           "scheduler_timeout_seconds": 120, "fixture_max_bytes": 4096}}
            try:
                receipt.update(qualify(owner, root, profile, output, origin, args.ensure), passed=True, semantic_verified=True)
            except Exception as exc:
                receipt.update(error_type=type(exc).__name__, reason=str(exc)[:1500])
            sources = [Path(__file__), Path(__file__).with_name(owner + ".py"), Path(__file__).with_name("scheduler_job.py")]
            receipt["source_sha256"] = {p.relative_to(root).as_posix(): sha(p.read_bytes()) for p in sources}
            native_sources = {
                "ipfs_kit_py": ["swissknife/scripts/ipfs-kit-kubo-tools.cjs", "swissknife/scripts/ipfs-kit-artifact-cat.cjs"],
                "ipfs_datasets_py": ["external/ipfs_datasets/ipfs_datasets_py/core_operations/dataset_loader.py",
                    "external/ipfs_datasets/ipfs_datasets_py/mcp_server/tools/ipfs_tools/get_from_ipfs.py"],
                "ipfs_accelerate_py": ["external/ipfs_accelerate/ipfs_accelerate_py/p2p_tasks/task_queue.py",
                    "external/ipfs_accelerate/ipfs_accelerate_py/p2p_tasks/worker.py", "external/ipfs_accelerate/ipfs_accelerate_py/llm_router.py"],
            }[owner]
            if owner == "ipfs_accelerate_py" and any(check.get("inference_executed") is True for check in receipt.get("checks", [])):
                native_sources = ["external/ipfs_accelerate/ipfs_accelerate_py/inference_backend_manager.py",
                    "scripts/svf_backends/native_accelerate_backend.py", "scripts/svf_backends/native_accelerate_service.py"]
            receipt["native_source_sha256"] = {p: sha((root / p).read_bytes()) for p in native_sources}
            receipt["artifacts"] = [{"path": p.relative_to(root).as_posix(), "sha256": sha(p.read_bytes()), "size_bytes": p.stat().st_size}
                                    for p in sorted(output.iterdir()) if p.is_file()]
            target = output / "readiness.json"
            atomic_json(target, receipt)
            atomic_json(runtime / (owner + "-readiness.json"), receipt)
            print(json.dumps({"owner": owner, "passed": receipt["passed"], "semantic_verified": receipt["semantic_verified"],
                "receipt_path": target.relative_to(root).as_posix(), "receipt_sha256": sha(target.read_bytes()),
                "reason": receipt.get("reason"), "work_complete": False, "completion_authority": False}))
            return 0 if receipt["passed"] else 1
    except Exception as exc:
        print(json.dumps({"owner": owner, "passed": False, "error_type": type(exc).__name__, "reason": str(exc)[:1500],
                          "work_complete": False, "completion_authority": False}))
        return 1
