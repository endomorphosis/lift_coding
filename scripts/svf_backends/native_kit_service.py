#!/usr/bin/env python3
"""Campaign-owned native Python IPFS Kit MCP endpoint; no cache or fallback.

All domain operations invoke the pinned ipfs_kit_py LivePinnedIpfsAdapter
against the configured real Kubo HTTP API. No daemon installation, automatic
daemon start, artifact-store cache, injected transport or simulated success.
The existing MCP++ facade may forward domain requests to this endpoint.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import sys
import threading
import time
from urllib.parse import urlsplit
import uuid

ROOT = Path(__file__).resolve().parents[2]
SDK_CLASS = "ipfs_kit_py.assurance.pinned_ipfs.LivePinnedIpfsAdapter"
SDK_PATH = "external/ipfs_kit/ipfs_kit_py/assurance/pinned_ipfs.py"
MAX_ADD_BYTES = 65536
MAX_CAT_BYTES = 1048576
MAX_REQUEST_BYTES = 100000
OPERATION_SECONDS = 10
CONTEXT_ARGS = {"dry_run", "correlation_id", "fixture_scope", "scope", "limit", "cursor"}
TOOLS = [
    {"name": "node_id", "description": "Read this real Kubo node's public identity via native Python IPFS Kit; not the facade's protocol DID.",
     "inputSchema": {"type": "object", "properties": {"dry_run": {"type": "boolean"}, "correlation_id": {"type": "string"}}, "additionalProperties": True}},
    {"name": "swarm_peers", "description": "Read actual connected Kubo swarm peers via native Python IPFS Kit; a genuinely empty swarm remains empty.",
     "inputSchema": {"type": "object", "properties": {"dry_run": {"type": "boolean"}, "correlation_id": {"type": "string"}}, "additionalProperties": True}},
    {"name": "ipfs_cat", "description": "Read exact raw-CID bytes via actual native Python IPFS Kit and real Kubo; no cache fallback.",
     "inputSchema": {"type": "object", "properties": {"cid": {"type": "string"}, "dry_run": {"type": "boolean"}, "correlation_id": {"type": "string"}}, "required": ["cid"], "additionalProperties": True}},
    {"name": "ipfs_add", "description": "Store bounded controlled bytes via actual native Python IPFS Kit block/put and return their raw CID.",
     "inputSchema": {"type": "object", "properties": {"content": {"type": "string"}, "data": {"type": "string"}, "bytes_base64": {"type": "string"}, "pin": {"type": "boolean"}, "dry_run": {"type": "boolean"}, "correlation_id": {"type": "string"}}, "additionalProperties": True}},
    {"name": "ipfs_pubsub_publish", "description": "Publish one bounded UTF-8 notification through the owned two-peer Kubo pubsub exchange. HTTP acceptance is not delivery or durable storage.",
     "inputSchema": {"type": "object", "properties": {"fixture_scope": {"type": "string"}, "topic": {"type": "string"}, "message_id": {"type": "string"}, "message": {"type": "string"}, "dry_run": {"type": "boolean"}, "correlation_id": {"type": "string"}}, "required": ["fixture_scope", "topic", "message_id", "message", "dry_run", "correlation_id"], "additionalProperties": True}},
]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def origin(value: str) -> str:
    parsed = urlsplit(value)
    if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.port is None
            or not 1024 <= parsed.port <= 65535 or parsed.path not in {"", "/"}
            or parsed.username or parsed.password or parsed.query or parsed.fragment):
        raise ValueError("Kubo API must be a credential-free loopback HTTP origin")
    return f"http://127.0.0.1:{parsed.port}"


def cid_for(data: bytes) -> str:
    return "b" + base64.b32encode(bytes([1, 85, 18, 32]) + hashlib.sha256(data).digest()).decode().lower().rstrip("=")


class NativeKit:
    def __init__(self, kubo_api: str, *, root: Path = ROOT):
        self.root, self.kubo_api = root, origin(kubo_api)
        sys.path.insert(0, str(root / "external/ipfs_kit"))
        import ipfs_kit_py.assurance.pinned_ipfs as sdk
        if Path(sdk.__file__).resolve() != root / SDK_PATH:
            raise RuntimeError("native IPFS Kit SDK is not the pinned owner checkout")
        self.sdk = sdk
        self.client = sdk.LivePinnedIpfsAdapter(api_url=self.kubo_api, timeout=OPERATION_SECONDS)
        if self.client.simulated or self.client._transport is not None or not self.client.live_provider:
            raise RuntimeError("injected or simulated IPFS Kit transports are forbidden")
        self.sdk_sha256 = digest((root / SDK_PATH).read_bytes())
        backend_dir = str(Path(__file__).resolve().parent)
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
        import native_pubsub_backend as pubsub_backend
        pubsub_backend.bind(root)
        self.pubsub = pubsub_backend

    def health(self) -> dict:
        result = self.client.health(deadline=time.monotonic() + OPERATION_SECONDS)
        if result.success is not True:
            raise RuntimeError("native IPFS Kit dependency is unavailable")
        return {"status": "ok", "owner": "ipfs_kit_py", "server": "swissknife-native-ipfs-kit",
            "native_python_backend": True, "sdk_class": SDK_CLASS, "sdk_source_sha256": self.sdk_sha256,
            "kubo_api": self.kubo_api, "kubo_version": result.metadata.get("version"),
            "simulated": False, "cache_fallback": False, "work_complete": False, "completion_authority": False}

    def call(self, tool: str, args: dict) -> dict:
        if type(args) is not dict:
            raise ValueError("tool arguments must be a JSON object")
        correlation = args.get("correlation_id")
        if correlation is not None and (type(correlation) is not str or len(correlation) > 256):
            raise ValueError("invalid correlation identifier")
        if "dry_run" in args and type(args["dry_run"]) is not bool:
            raise ValueError("dry_run must be boolean")
        deadline = time.monotonic() + OPERATION_SECONDS
        observation = None
        if tool in {"node_id", "swarm_peers"}:
            if set(args) - CONTEXT_ARGS:
                raise ValueError("unsupported native observation arguments; remote nodes and arbitrary endpoints are forbidden")
            result = getattr(self.client, tool)(deadline=deadline)
            observation = dict(result.metadata)
            if tool == "swarm_peers":
                raw = observation.get("raw_observation")
                if (not isinstance(raw, dict) or "Peers" not in raw or raw.get("error") or raw.get("Error") or raw.get("success") is False
                        or type(observation.get("peers_reported_null")) is not bool
                        or (raw["Peers"] is None) != observation["peers_reported_null"]
                        or (raw["Peers"] is not None and type(raw["Peers"]) is not list)
                        or observation.get("Peers") != (raw["Peers"] if raw["Peers"] is not None else [])
                        or type(observation.get("peer_count")) is not int or observation["peer_count"] != len(observation["Peers"])):
                    raise RuntimeError("native SDK peer normalization lacks its actual raw observation")
                raw_bytes = json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
                if digest(raw_bytes) != observation.get("raw_observation_canonical_sha256"):
                    raise RuntimeError("native SDK raw peer observation canonical hash differs")
            data = json.dumps(observation, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
            method = tool
        elif tool == "ipfs_cat":
            if set(args) - (CONTEXT_ARGS | {"cid", "expected_sha256"}):
                raise ValueError("unsupported native cat arguments")
            cid = args.get("cid")
            if type(cid) is not str or re.fullmatch(r"bafkrei[a-z2-7]{52}", cid) is None:
                raise ValueError("native cat requires a raw CIDv1 SHA-256 identifier")
            expected = args.get("expected_sha256")
            if expected is not None and (type(expected) is not str or re.fullmatch(r"[0-9a-f]{64}", expected) is None):
                raise ValueError("invalid expected SHA-256")
            # Ask the same actual SDK for the raw block's size before its
            # byte-preserving public cat operation. No artifact cache is read.
            stat = self.client._request("/api/v0/block/stat", query={"arg": cid}, deadline=deadline)
            size = stat.get("Size")
            if type(size) is not int or not 0 < size <= MAX_CAT_BYTES:
                raise ValueError("native IPFS block exceeds the bounded cat size")
            result = self.client.cat(cid, expected_sha256=expected, deadline=deadline)
            data = result.data
            if len(data) != size or cid_for(data) != cid:
                raise RuntimeError("native SDK returned bytes inconsistent with the requested block")
            method = "cat"
        elif tool == "ipfs_add":
            if set(args) - (CONTEXT_ARGS | {"content", "data", "bytes_base64", "pin"}):
                raise ValueError("unsupported native add arguments; arbitrary file reads are forbidden")
            if args.get("dry_run") is True:
                raise ValueError("a preview is not native execution; dry_run add is unsupported")
            fields = [key for key in ("content", "data", "bytes_base64") if key in args]
            if len(fields) != 1 or type(args[fields[0]]) is not str:
                raise ValueError("add requires exactly one content/data string or bytes_base64")
            data = base64.b64decode(args[fields[0]], validate=True) if fields[0] == "bytes_base64" else args[fields[0]].encode("utf-8")
            if not 0 < len(data) <= MAX_ADD_BYTES or type(args.get("pin", True)) is not bool:
                raise ValueError("invalid bounded native add payload")
            result = self.client.add(data, pin=args.get("pin", True), deadline=deadline)
            cid = result.resulting_content_cid
            if cid != cid_for(data):
                raise RuntimeError("native SDK storage CID differs from independently hashed bytes")
            method = "add"
        elif tool == "ipfs_pubsub_publish":
            payload = self.pubsub.publish_exchange(args)
            provenance = payload["native_provenance"]
            return {"isError": False, "content": [{"type": "json", "json": payload}],
                "receipt": {"adapter": "swissknife-native-ipfs-kit", "owner": "ipfs_kit_py", "tool": tool,
                            "status": "ok", "native_provenance": provenance}}
        else:
            raise ValueError("unsupported native IPFS Kit operation")
        if result.success is not True:
            raise RuntimeError("native SDK operation did not succeed")
        provenance = {"schema": "swissknife.native-kit-execution.v1", "owner": "ipfs_kit_py", "sdk_class": SDK_CLASS,
            "sdk_method": method, "sdk_source_path": SDK_PATH, "sdk_source_sha256": self.sdk_sha256,
            "service_source_sha256": digest(Path(__file__).read_bytes()),
            "sdk_request_id": result.canonical_result.request_id, "sdk_operation_id": result.canonical_result.operation_id,
            "kubo_api": self.kubo_api, "transport": self.client.transport_kind, "simulated": self.client.simulated,
            "cache_fallback": False, "observed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "correlation_id": correlation, "payload_sha256": digest(data), "payload_bytes": len(data),
            "work_complete": False, "completion_authority": False}
        if observation is not None:
            payload = {**observation, "success": True, "tool": tool, "observation": observation,
                "backend": "ipfs_kit_py.assurance.pinned_ipfs:live-kubo-http", "native_provenance": provenance}
        else:
            payload = {"success": True, "cid": cid, "bytes_base64": base64.b64encode(data).decode(), "size": len(data),
                "sha256": digest(data), "backend": "ipfs_kit_py.assurance.pinned_ipfs:live-kubo-http", "native_provenance": provenance}
            if tool == "ipfs_add":payload.update(stored=True, pinned=args.get("pin", True))
        return {"isError": False, "content": [{"type": "json", "json": payload}],
            "receipt": {"adapter": "swissknife-native-ipfs-kit", "owner": "ipfs_kit_py", "tool": tool,
                        "status": "ok", "native_provenance": provenance}}


def dispatch(backend, request: dict) -> dict | None:
    if type(request) is not dict or request.get("jsonrpc") != "2.0":
        raise ValueError("JSON-RPC 2.0 object required")
    method = request.get("method"); params = request.get("params", {})
    if type(params) is not dict:raise ValueError("JSON-RPC params must be an object")
    if method == "notifications/initialized":return None
    if method == "initialize":
        result = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
            "serverInfo": {"name": "swissknife-native-ipfs-kit", "version": "1.0.0"}}
    elif method == "tools/list":result = {"tools": TOOLS}
    elif method == "tools/call":result = backend.call(params.get("name"), params.get("arguments", {}))
    elif method == "ping":result = {}
    else:raise ValueError("unsupported native MCP method")
    return {"jsonrpc": "2.0", "id": request.get("id"), "result": result}


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False
    request_queue_size = 16
    def __init__(self, address, backend):
        self.backend = backend
        self.slots = threading.BoundedSemaphore(4)
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    server_version = "SwissKnifeNativeKit/1.0"
    def log_message(self, *_args):pass
    def setup(self):
        super().setup();self.connection.settimeout(15)
    def send(self, code, value):
        data = json.dumps(value, ensure_ascii=False, allow_nan=False).encode()
        self.send_response(code);self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)));self.end_headers();self.wfile.write(data)
    def do_GET(self):
        if self.path not in {"/health", "/mcp/health"}:return self.send(404, {"error": "not_found"})
        try:self.send(200, self.server.backend.health())
        except Exception as exc:self.send(503, {"status": "unavailable", "native_python_backend": True, "error_type": type(exc).__name__, "success": False})
    def do_POST(self):
        if self.path != "/mcp":return self.send(404, {"error": "not_found"})
        if not self.server.slots.acquire(blocking=False):return self.send(503, {"error": "bounded_concurrency_exhausted"})
        request = None
        try:
            length = self.headers.get("Content-Length", "")
            if not length.isdigit() or not 0 < int(length) <= MAX_REQUEST_BYTES:
                raise ValueError("bounded Content-Length is required")
            request = json.loads(self.rfile.read(int(length)))
            response = dispatch(self.server.backend, request)
            if response is None:
                self.send_response(204);self.end_headers()
            else:self.send(200, response)
        except Exception as exc:
            if isinstance(request, dict) and request.get("method") == "tools/call":
                tool = request.get("params", {}).get("name") if isinstance(request.get("params"), dict) else None
                self.send(200, {"jsonrpc": "2.0", "id": request.get("id"), "result": {"isError": True,
                    "content": [{"type": "json", "json": {"success": False, "error": str(exc)[:700], "error_type": type(exc).__name__}}],
                    "receipt": {"adapter": "swissknife-native-ipfs-kit", "owner": "ipfs_kit_py", "tool": tool, "status": "error"}}})
            else:self.send(400, {"jsonrpc": "2.0", "id": request.get("id") if isinstance(request, dict) else None,
                "error": {"code": -32600, "message": str(exc)[:700]}})
        finally:self.server.slots.release()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", choices=["127.0.0.1"], default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18314)
    parser.add_argument("--kubo-api", default="http://127.0.0.1:5021")
    args = parser.parse_args(argv)
    if not 1024 <= args.port <= 65535:raise ValueError("invalid loopback service port")
    backend = NativeKit(args.kubo_api)
    backend.health()  # Fail before binding if the actual native dependency fails.
    server = Server((args.host, args.port), backend)
    print(json.dumps({"service": "swissknife-native-ipfs-kit", "endpoint": f"http://{args.host}:{args.port}/mcp",
        "sdk_class": SDK_CLASS, "simulated": False, "cache_fallback": False}), flush=True)
    try:server.serve_forever(poll_interval=0.2)
    finally:server.server_close();backend.client.close()
    return 0


if __name__ == "__main__":raise SystemExit(main())
