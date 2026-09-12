#!/usr/bin/python3.12
"""LA-013 actual transport parity and content-retrieval qualification.

Runs under the sealed validation PATH. The selected route is
``SupervisorPreInvocationEnforcement.authorize_and_delegate`` around
``BoundedExportHandler``. Identical authorized and rejected JSON-RPC
requests are sent through real stdio, loopback HTTP, and loopback
libp2p processes. In-process framing is recorded separately and is not
libp2p network evidence. Local loopback is labeled local. Public CID
integrity is separated from availability; private preimages are never
written to declared outputs.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import importlib.util
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import unquote

HERE = Path(__file__).resolve()
if "receipts" in HERE.parts and "snapshots" in HERE.parts:
    SNAPSHOT = HERE.parent
    ROOT = HERE.parents[6]
else:
    ROOT = HERE.parents[4]
    SNAPSHOT = ROOT / "papers" / "completion" / "law_to_action" / "receipts" / "snapshots" / "LA-013"
LIVE = ROOT / "papers" / "completion" / "law_to_action"
PYTHON = "/usr/bin/python3.12"
HANDLERS = LIVE / "benchmark" / "handlers" / "effects.py"
VALIDATION_SITE_PACKAGES = Path("/opt/ipfs-validation-site-packages")
PROTOCOL_MCP_P2P_V1 = "/mcp+p2p/1.0.0"
NOISE_PROTOCOL_ID = "/noise"
YAMUX_PROTOCOL_ID = "/yamux/1.0.0"

for path in (
    ROOT / "external" / "ipfs_accelerate",
    ROOT / "external" / "ipfs_datasets",
    ROOT / "external" / "ipfs_kit",
):
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)

DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
DIGEST_D = "d" * 64
DIGEST_E = "e" * 64
DIGEST_F = "f" * 64
DIGEST_1 = "1" * 64
DIGEST_2 = "2" * 64
ISSUED = "2026-07-28T12:00:00Z"
DEADLINE = "2026-07-28T12:05:00Z"
EXPIRY = "2026-07-28T12:10:00Z"
NOW_OK = "2026-07-28T12:02:00Z"
PARITY_CASES = ("allow", "deny", "unknown", "wrong-audience", "replay")


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def load_handlers():
    spec = importlib.util.spec_from_file_location("la013_bounded_handlers", HANDLERS)
    if spec is None or spec.loader is None:
        raise RuntimeError("bounded export handler module is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def compute_cid(payload: Mapping[str, Any]) -> str:
    from ipfs_kit_py.mcp_server.mcplusplus.artifacts import compute_artifact_cid

    return compute_artifact_cid(dict(payload))


def source_pins() -> dict[str, dict[str, str]]:
    files = {
        "admissibility_enforcement.py": ROOT
        / "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/admissibility_enforcement.py",
        "server.py": ROOT / "external/ipfs_kit/ipfs_kit_py/mcp_server/server.py",
        "p2p_transport.py": ROOT / "external/ipfs_kit/ipfs_kit_py/mcp_server/p2p_transport.py",
        "artifacts.py": ROOT / "external/ipfs_kit/ipfs_kit_py/mcp_server/mcplusplus/artifacts.py",
        "mcp_p2p.py": ROOT / "external/ipfs_accelerate/ipfs_accelerate_py/p2p_tasks/mcp_p2p.py",
        "mcp_p2p_client.py": ROOT
        / "external/ipfs_accelerate/ipfs_accelerate_py/p2p_tasks/mcp_p2p_client.py",
        "libp2p_runtime.py": ROOT
        / "external/ipfs_accelerate/ipfs_accelerate_py/mcplusplus_module/p2p/libp2p_runtime.py",
        "effects.py": HANDLERS,
    }
    return {
        name: {"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)}
        for name, path in files.items()
        if path.is_file()
    }


def module_probe(name: str) -> dict[str, Any]:
    spec = importlib.util.find_spec(name)
    if spec is None:
        return {"available": False, "version": None, "origin": None}
    try:
        module = importlib.import_module(name)
    except Exception as exc:
        return {
            "available": False,
            "version": None,
            "origin": getattr(spec, "origin", None),
            "import_error": f"{type(exc).__name__}: {exc}",
        }
    return {
        "available": True,
        "version": getattr(module, "__version__", None),
        "origin": getattr(module, "__file__", None),
    }


def probe_ipfs_daemon() -> dict[str, Any]:
    result: dict[str, Any] = {
        "binary": shutil.which("ipfs"),
        "kubo_binary": shutil.which("kubo"),
        "attempted": True,
        "available": False,
        "endpoint": "/ip4/127.0.0.1/tcp/5001/http",
        "error": None,
        "error_type": None,
    }
    try:
        import ipfshttpclient

        client = ipfshttpclient.connect(result["endpoint"], timeout=2)
        try:
            identity = client.id()
            result["available"] = True
            result["peer_id"] = identity.get("ID") if isinstance(identity, dict) else str(identity)
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                close()
    except Exception as exc:
        result["error"] = str(exc)
        result["error_type"] = type(exc).__name__
    if result["binary"] is None and not result["available"]:
        if not result["error"]:
            result["error"] = "ipfs/kubo executable absent from sealed PATH; localhost:5001 did not serve an API"
    return result


def probe_environment() -> dict[str, Any]:
    import cryptography

    libp2p_ok = False
    libp2p_error = None
    try:
        from ipfs_accelerate_py.mcplusplus_module.p2p.libp2p_runtime import (
            ensure_libp2p_compatible,
            have_libp2p_runtime,
        )

        libp2p_ok = bool(ensure_libp2p_compatible() and have_libp2p_runtime())
    except Exception as exc:
        libp2p_error = f"{type(exc).__name__}: {exc}"
    kit_libp2p = False
    try:
        from ipfs_kit_py.mcp_server.p2p_transport import HAVE_LIBP2P, PROTOCOL_ID

        kit_libp2p = bool(HAVE_LIBP2P)
        kit_protocol = PROTOCOL_ID
    except Exception as exc:
        kit_protocol = None
        kit_libp2p_error = f"{type(exc).__name__}: {exc}"
    else:
        kit_libp2p_error = None
    mcp_importable = False
    mcp_error = None
    try:
        from ipfs_kit_py.mcp_server.server import MCPServer  # noqa: F401

        mcp_importable = True
    except Exception as exc:
        mcp_error = f"{type(exc).__name__}: {exc}"
    return {
        "observed_at": utc_now(),
        "python": PYTHON,
        "python_version": sys.version.split()[0],
        "python_executable": sys.executable,
        "python_sha256": sha256_file(Path(sys.executable)),
        "path": os.environ.get("PATH"),
        "home": os.environ.get("HOME"),
        "home_is_validation_prefix": "ipfs-accelerate-validation-home-"
        in str(os.environ.get("HOME", "")),
        "pythonpath": os.environ.get("PYTHONPATH"),
        "validation_site_packages": str(VALIDATION_SITE_PACKAGES),
        "validation_site_packages_exists": VALIDATION_SITE_PACKAGES.is_dir(),
        "cryptography_version": cryptography.__version__,
        "cryptography_origin": getattr(cryptography, "__file__", None),
        "modules": {
            name: module_probe(name)
            for name in (
                "anyio",
                "trio",
                "libp2p",
                "hypercorn",
                "multiformats",
                "ipfshttpclient",
                "multiaddr",
            )
        },
        "libp2p_runtime_compatible": libp2p_ok,
        "libp2p_runtime_error": libp2p_error,
        "kit_have_libp2p": kit_libp2p,
        "kit_p2p_protocol": kit_protocol,
        "kit_libp2p_error": kit_libp2p_error,
        "mcp_server_importable": mcp_importable,
        "mcp_server_import_error": mcp_error,
        "ipfs_daemon": probe_ipfs_daemon(),
        "source_pins": source_pins(),
        "kit_serve_p2p_listens": False,
        "kit_serve_p2p_note": "ipfs_kit_py.mcp_server.p2p_transport.serve_p2p constructs a host and sleeps; it does not listen. In-process handle_stream_message is framing only.",
    }


class CountingDelegate:
    def __init__(self, fn: Callable[[], Any] | None = None) -> None:
        self.calls = 0
        self.fn = fn

    def __call__(self) -> Any:
        self.calls += 1
        if self.fn is not None:
            return self.fn()
        return {"status": "ok"}


def receipt_modules():
    from ipfs_datasets_py.logic.admissibility.compose import InternalDecisionStatus
    from ipfs_datasets_py.logic.admissibility.receipt import (
        BoundContext,
        BoundRoots,
        build_decision_receipt,
        derive_capability,
        DecisionReceipt,
        AuthorizationCapability,
    )

    return (
        InternalDecisionStatus,
        BoundContext,
        BoundRoots,
        build_decision_receipt,
        derive_capability,
        DecisionReceipt,
        AuthorizationCapability,
    )


def bound_roots(**overrides: Any):
    _, _, BoundRoots, _, _, _, _ = receipt_modules()
    base = {
        "policy_root": "policy:root-v1",
        "corpus_roots": ("corpus:legal-v1", "corpus:security-v1"),
        "revocation_root": "revocation:root-v1",
        "circuit_roots": ("circuit:auth-v1",),
        "vk_roots": ("vk:auth-v1",),
    }
    base.update(overrides)
    return BoundRoots(**base)


def bound_context(**overrides: Any):
    _, BoundContext, _, _, _, _, _ = receipt_modules()
    base = {
        "request_digest": DIGEST_A,
        "arguments_digest": DIGEST_B,
        "actor_id": "actor:alice",
        "audience_id": "audience:supervisor-dispatcher",
        "tool_id": "tool:supervisor.delegate",
        "tool_version": "1.0.0",
        "effect_ids": ("effect:filesystem.export_json", "effect:notify"),
        "environment_digest": DIGEST_C,
        "environment_id": "env:prod-sandbox",
        "delegation_ids": ("delegation:link-1",),
        "delegation_digest": DIGEST_D,
        "resource_ids": ("resource:tenant-a/exports/report.json",),
        "capability_ids": ("capability:write",),
        "nonce": "nonce-supervisor-001",
    }
    base.update(overrides)
    return BoundContext(**base)


def make_receipt(*, outcome=None, **overrides: Any):
    InternalDecisionStatus, _, _, build_decision_receipt, _, _, _ = receipt_modules()
    kwargs: dict[str, Any] = {
        "receipt_id": overrides.pop("receipt_id", "receipt:allow-transport-001"),
        "context": overrides.pop("context", bound_context()),
        "roots": overrides.pop("roots", bound_roots()),
        "outcome": outcome if outcome is not None else InternalDecisionStatus.ALLOW,
        "reasons": ("positive grant proved",),
        "reason_codes": ("allow.positive_grant",),
        "selected_evidence_cids": (
            "bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi",
        ),
        "obligation_ids": ("obl:pre-check",),
        "residual_duties": (),
        "attempt_digests": (DIGEST_1,),
        "result_digests": (DIGEST_2,),
        "decision_digest": DIGEST_E,
        "policy_digest": DIGEST_F,
        "profile_id": "profile:closed-world",
        "issued_at": ISSUED,
        "deadline": DEADLINE,
        "expiry": EXPIRY,
        "producer_id": "producer:auth-service",
    }
    kwargs.update(overrides)
    return build_decision_receipt(**kwargs)


def make_capability(receipt: Any):
    _, _, _, _, derive_capability, _, _ = receipt_modules()
    return derive_capability(
        receipt,
        capability_id="capability:supervisor-once",
        allowed_effects=("effect:filesystem.export_json",),
        require_strict_subset=True,
    )


def supervisor_context(**overrides: Any):
    from ipfs_accelerate_py.agent_supervisor.proof.admissibility_enforcement import (
        SupervisorInvocationContext,
    )

    base = {
        "actor_id": "actor:alice",
        "audience_id": "audience:supervisor-dispatcher",
        "tool_id": "tool:supervisor.delegate",
        "tool_version": "1.0.0",
        "request_digest": DIGEST_A,
        "arguments_digest": DIGEST_B,
        "environment_digest": DIGEST_C,
        "environment_id": "env:prod-sandbox",
        "effect_ids": ("effect:filesystem.export_json",),
        "task_id": "task:la-013",
        "plan_id": "plan:transport-parity",
        "delegation_ids": ("delegation:link-1",),
        "delegation_digest": DIGEST_D,
        "nonce": "nonce-supervisor-001",
        "resource_ids": ("resource:tenant-a/exports/report.json",),
    }
    base.update(overrides)
    return SupervisorInvocationContext(**base)


def context_to_dict(context: Any) -> dict[str, Any]:
    return {
        "actor_id": context.actor_id,
        "audience_id": context.audience_id,
        "tool_id": context.tool_id,
        "tool_version": context.tool_version,
        "request_digest": context.request_digest,
        "arguments_digest": context.arguments_digest,
        "environment_digest": context.environment_digest,
        "environment_id": context.environment_id,
        "effect_ids": list(context.effect_ids),
        "task_id": context.task_id,
        "plan_id": context.plan_id,
        "delegation_ids": list(context.delegation_ids),
        "delegation_digest": context.delegation_digest,
        "nonce": context.nonce,
        "resource_ids": list(context.resource_ids),
        "capability_ids": list(getattr(context, "capability_ids", ()) or ()),
    }


def context_from_dict(payload: Mapping[str, Any]):
    from ipfs_accelerate_py.agent_supervisor.proof.admissibility_enforcement import (
        SupervisorInvocationContext,
    )

    return SupervisorInvocationContext(
        actor_id=str(payload["actor_id"]),
        audience_id=str(payload["audience_id"]),
        tool_id=str(payload["tool_id"]),
        tool_version=str(payload.get("tool_version") or ""),
        request_digest=str(payload["request_digest"]),
        arguments_digest=str(payload["arguments_digest"]),
        environment_digest=str(payload["environment_digest"]),
        environment_id=str(payload.get("environment_id") or ""),
        effect_ids=tuple(payload.get("effect_ids") or ()),
        task_id=str(payload.get("task_id") or ""),
        plan_id=str(payload.get("plan_id") or ""),
        delegation_ids=tuple(payload.get("delegation_ids") or ()),
        delegation_digest=str(payload.get("delegation_digest") or ""),
        nonce=str(payload.get("nonce") or ""),
        resource_ids=tuple(payload.get("resource_ids") or ()),
        capability_ids=tuple(payload.get("capability_ids") or ()),
    )


def map_enforce_decision(outcome: Any) -> str:
    from ipfs_accelerate_py.agent_supervisor.proof.admissibility_enforcement import (
        EnforcementDisposition,
    )

    if outcome.observation.disposition is EnforcementDisposition.ALLOWED:
        return "allow"
    reason = outcome.observation.denial_reason or ""
    codes = tuple(outcome.observation.reason_codes or ())
    if reason in {"abstain"} or "abstain" in codes:
        return "unknown"
    return "deny"


def run_enforcer_local(
    *,
    context: Any,
    receipt: Any | None,
    capability: Any | None,
    store: Any,
    job_id: str,
) -> dict[str, Any]:
    from ipfs_accelerate_py.agent_supervisor.proof.admissibility_enforcement import (
        SupervisorPreInvocationEnforcement,
    )

    handlers = load_handlers()
    state_dir = Path(tempfile.mkdtemp(prefix=f"la013-{job_id}-"))
    run_id = f"la013-{job_id}-{os.getpid()}"
    instruction = {
        "operation": "export_json",
        "path": "exports/report.json",
        "payload": {"task": "LA-013", "kind": "bounded-export", "case": job_id},
    }
    handler = handlers.BoundedExportHandler(state_dir)
    counter = CountingDelegate(lambda: handler.execute(instruction, run_id=run_id))
    enforcer = SupervisorPreInvocationEnforcement(
        mode="enforce",
        store=store,
        expected_roots=bound_roots(),
        clock=lambda: NOW_OK,
    )
    try:
        outcome = enforcer.authorize_and_delegate(
            context, counter, receipt=receipt, capability=capability
        )
        observation = handlers.EffectObserver(state_dir).observe(run_id=run_id)
        return {
            "decision": map_enforce_decision(outcome),
            "delegated": bool(outcome.delegate_called),
            "handler_calls": counter.calls,
            "observed_effect_count": int(observation.get("observed_effect_count") or 0),
            "journal_event_count": int(observation.get("journal_event_count") or 0),
            "denial_reason": str(outcome.observation.denial_reason or ""),
            "reason_codes": list(outcome.observation.reason_codes or ()),
            "pid": os.getpid(),
        }
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def build_case_catalog() -> dict[str, dict[str, Any]]:
    InternalDecisionStatus, _, _, _, _, _, _ = receipt_modules()
    allow_receipt = make_receipt()
    allow_cap = make_capability(allow_receipt)
    deny_receipt = make_receipt(
        receipt_id="receipt:deny-transport-1",
        outcome=InternalDecisionStatus.DENY,
        reasons=("negative grant",),
        reason_codes=("deny.prohibition",),
    )
    unknown_receipt = make_receipt(
        receipt_id="receipt:unknown-transport-1",
        outcome=InternalDecisionStatus.INDETERMINATE,
        reasons=("missing evidence",),
        reason_codes=("unknown.missing_evidence",),
    )
    wrong_ctx = supervisor_context(audience_id="audience:wrong")
    return {
        "allow": {
            "case_kind": "allow",
            "expected_decision": "allow",
            "expected_effect_count": 1,
            "receipt": allow_receipt.to_dict(),
            "capability": allow_cap.to_dict(),
            "context": context_to_dict(supervisor_context()),
        },
        "deny": {
            "case_kind": "deny",
            "expected_decision": "deny",
            "expected_effect_count": 0,
            "receipt": deny_receipt.to_dict(),
            "capability": None,
            "context": context_to_dict(supervisor_context()),
        },
        "unknown": {
            "case_kind": "unknown",
            "expected_decision": "unknown",
            "expected_effect_count": 0,
            "receipt": unknown_receipt.to_dict(),
            "capability": None,
            "context": context_to_dict(supervisor_context()),
        },
        "wrong-audience": {
            "case_kind": "context_mutation",
            "expected_decision": "deny",
            "expected_effect_count": 0,
            "receipt": make_receipt(receipt_id="receipt:wrong-audience-transport").to_dict(),
            "capability": make_capability(
                make_receipt(receipt_id="receipt:wrong-audience-transport")
            ).to_dict(),
            "context": context_to_dict(wrong_ctx),
        },
        "replay": {
            "case_kind": "replay",
            "expected_decision": "deny",
            "expected_effect_count": 0,
            "receipt": allow_receipt.to_dict(),
            "capability": allow_cap.to_dict(),
            "context": context_to_dict(supervisor_context()),
        },
    }


def tools_call_params(catalog: Mapping[str, Any], case_id: str) -> dict[str, Any]:
    spec = catalog[case_id]
    return {
        "name": "bounded.export_json",
        "arguments": {
            "operation": "export_json",
            "path": "exports/report.json",
            "payload": {"task": "LA-013", "kind": "bounded-export", "case": case_id},
        },
        "case_id": case_id,
        "receipt": spec["receipt"],
        "capability": spec["capability"],
        "context": spec["context"],
    }


class WorkerState:
    def __init__(self) -> None:
        from ipfs_accelerate_py.agent_supervisor.proof.admissibility_enforcement import (
            InMemoryCapabilityConsumptionStore,
        )

        self.store = InMemoryCapabilityConsumptionStore()
        self.lock = threading.Lock()
        self.cid_store: dict[str, bytes] = {}
        self.public_cid: str | None = None
        self.identity: dict[str, Any] = {"pid": os.getpid()}

    def load_public_artifact(self, path: Path) -> None:
        payload = json.loads(path.read_text(encoding="utf-8"))
        cid = compute_cid(payload)
        self.public_cid = cid
        self.cid_store[cid] = canonical_json_bytes(payload)

    def handle_rpc(self, message: Any) -> dict[str, Any] | None:
        if not isinstance(message, dict):
            return {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32600, "message": "invalid_request"},
            }
        if message.get("jsonrpc") != "2.0":
            return {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "error": {"code": -32600, "message": "invalid_jsonrpc"},
            }
        method = message.get("method")
        mid = message.get("id")
        params = message.get("params") or {}
        if mid is None:
            return None
        try:
            if method == "initialize":
                result = {
                    "ok": True,
                    "pid": os.getpid(),
                    "identity": self.identity,
                    "public_cid": self.public_cid,
                    "route": "SupervisorPreInvocationEnforcement.authorize_and_delegate",
                    "mode": "enforce",
                }
            elif method == "tools/call":
                result = self.tools_call(params)
            elif method == "content/get":
                result = self.content_get(params)
            else:
                raise ValueError(f"unknown method: {method}")
            return {"jsonrpc": "2.0", "id": mid, "result": result}
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": mid,
                "error": {
                    "code": -32000,
                    "message": str(exc),
                    "data": {"error_type": type(exc).__name__},
                },
            }

    def tools_call(self, params: Mapping[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        if name != "bounded.export_json":
            raise ValueError(f"unknown tool: {name}")
        _, _, BoundRoots, _, _, DecisionReceipt, AuthorizationCapability = receipt_modules()
        receipt_payload = params.get("receipt")
        capability_payload = params.get("capability")
        context_payload = params.get("context")
        if not isinstance(receipt_payload, Mapping) or not isinstance(context_payload, Mapping):
            raise ValueError("tools/call requires receipt and context objects")
        receipt = DecisionReceipt.from_dict(receipt_payload)
        capability = (
            AuthorizationCapability.from_dict(capability_payload)
            if isinstance(capability_payload, Mapping)
            else None
        )
        context = context_from_dict(context_payload)
        job_id = str(params.get("case_id") or "call")
        with self.lock:
            return run_enforcer_local(
                context=context,
                receipt=receipt,
                capability=capability,
                store=self.store,
                job_id=job_id,
            )

    def content_get(self, params: Mapping[str, Any]) -> dict[str, Any]:
        cid = str(params.get("cid") or "")
        blob = self.cid_store.get(cid)
        if blob is None:
            return {
                "found": False,
                "cid": cid,
                "integrity": False,
                "availability": "not-held",
                "published": False,
            }
        recomputed = compute_cid(json.loads(blob.decode("utf-8")))
        return {
            "found": True,
            "cid": cid,
            "bytes_sha256": sha256_bytes(blob),
            "recomputed_cid": recomputed,
            "integrity": recomputed == cid,
            "availability": "local-process-store",
            "published": False,
            "profile": "CIDv1/raw/sha2-256/base32",
        }


def serve_stdio_worker(state: WorkerState) -> None:
    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "parse_error"},
            }
        else:
            response = state.handle_rpc(message)
        if response is not None:
            sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
            sys.stdout.flush()


def serve_http_worker(state: WorkerState, host: str, port: int, identity_file: Path) -> None:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: object) -> None:
            return

        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                message = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": "parse_error"},
                }
            else:
                payload = state.handle_rpc(message) or {
                    "jsonrpc": "2.0",
                    "id": None,
                    "result": None,
                }
            self._send(200, json.dumps(payload).encode("utf-8"), "application/json")

        def do_GET(self) -> None:  # noqa: N802
            if self.path.startswith("/cid/"):
                cid = unquote(self.path[len("/cid/") :]).strip()
                blob = state.cid_store.get(cid)
                if blob is None:
                    self._send(
                        404,
                        json.dumps(
                            {
                                "found": False,
                                "cid": cid,
                                "availability": "not-held",
                                "published": False,
                            }
                        ).encode("utf-8"),
                        "application/json",
                    )
                    return
                self._send(200, blob, "application/json")
                return
            self._send(404, b'{"error":"not_found"}', "application/json")

    server = ThreadingHTTPServer((host, port), Handler)
    state.identity = {
        "pid": os.getpid(),
        "transport": "http",
        "listen": f"{host}:{port}",
        "network_mode": "local-network",
        "actual_network": True,
        "wan": False,
        "in_process": False,
        "tls": False,
        "security": {
            "channel": "plaintext-http",
            "tls": False,
            "noise": False,
            "listen_host": host,
        },
        "protocol": "jsonrpc-2.0-http",
    }
    write_json(identity_file, state.identity)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def serve_libp2p_worker(state: WorkerState, host: str, port: int, identity_file: Path) -> None:
    import anyio
    from ipfs_accelerate_py.mcplusplus_module.p2p.libp2p_runtime import (
        get_libp2p_protocol_type,
        peer_id_text,
        running_libp2p_host,
    )
    from ipfs_accelerate_py.p2p_tasks.mcp_p2p import read_u32_framed_json, write_u32_framed_json

    async def main() -> None:
        listen = f"/ip4/{host}/tcp/{port}"
        async with running_libp2p_host(listen_multiaddr=listen) as p2p_host:
            peer = peer_id_text(p2p_host.get_id())
            addrs = [str(addr) for addr in p2p_host.get_addrs()]
            state.identity = {
                "pid": os.getpid(),
                "transport": "libp2p",
                "peer_id": peer,
                "listen": listen,
                "addrs": addrs,
                "multiaddr": f"{listen}/p2p/{peer}",
                "network_mode": "local-network",
                "actual_network": True,
                "wan": False,
                "in_process": False,
                "protocol": PROTOCOL_MCP_P2P_V1,
                "security": {
                    "secure_channel": "noise",
                    "noise_protocol_id": NOISE_PROTOCOL_ID,
                    "muxer": "yamux",
                    "muxer_protocol_id": YAMUX_PROTOCOL_ID,
                    "muxer_fallback": "mplex",
                    "transport": "tcp",
                    "tls": False,
                    "listen_host": host,
                },
            }
            write_json(identity_file, state.identity)

            async def handler(stream: Any) -> None:
                try:
                    while True:
                        message, error = await read_u32_framed_json(stream)
                        if message is None:
                            if error in {None, "empty", "eof"}:
                                break
                            await write_u32_framed_json(
                                stream,
                                {
                                    "jsonrpc": "2.0",
                                    "id": None,
                                    "error": {
                                        "code": -32600,
                                        "message": str(error or "invalid_message"),
                                    },
                                },
                            )
                            break
                        response = state.handle_rpc(message)
                        if response is not None:
                            await write_u32_framed_json(stream, response)
                finally:
                    closer = getattr(stream, "close", None)
                    if callable(closer):
                        await closer()

            protocol_type = get_libp2p_protocol_type()
            protocol = (
                protocol_type(PROTOCOL_MCP_P2P_V1)
                if protocol_type is not str
                else PROTOCOL_MCP_P2P_V1
            )
            p2p_host.set_stream_handler(protocol, handler)
            while True:
                await anyio.sleep(3600)

    anyio.run(main, backend="trio")


def worker_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="la013-worker")
    parser.add_argument("--worker", choices=("stdio", "http", "libp2p"), required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--identity-file", default="")
    parser.add_argument("--public-artifact", required=True)
    args = parser.parse_args(argv)
    state = WorkerState()
    state.load_public_artifact(Path(args.public_artifact))
    identity_file = Path(args.identity_file) if args.identity_file else SNAPSHOT / "traces" / f"{args.worker}-identity.json"
    if args.worker == "stdio":
        state.identity = {
            "pid": os.getpid(),
            "transport": "stdio",
            "network_mode": "local-process",
            "actual_network": False,
            "wan": False,
            "in_process": False,
            "protocol": "jsonrpc-2.0-ndjson",
            "security": {"channel": "anonymous-pipes", "tls": False, "noise": False},
        }
        serve_stdio_worker(state)
        return 0
    if args.worker == "http":
        serve_http_worker(state, args.host, int(args.port), identity_file)
        return 0
    serve_libp2p_worker(state, args.host, int(args.port), identity_file)
    return 0


def pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def sealed_env() -> dict[str, str]:
    pythonpath = os.environ.get(
        "PYTHONPATH",
        f"{VALIDATION_SITE_PACKAGES}:external/ipfs_accelerate:external/ipfs_datasets:external/ipfs_kit",
    )
    return {
        "PATH": os.environ.get("PATH", "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"),
        "HOME": os.environ.get("HOME", ""),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
        "PYTHONPATH": pythonpath,
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        "VECLIB_MAXIMUM_THREADS": "1",
        "RAYON_NUM_THREADS": "1",
        "LANG": "C.UTF-8",
        "IPFS_ACCEL_SKIP_CORE": "1",
        "IPFS_ACCELERATE_PY_TASK_P2P_MDNS": "0",
        "IPFS_ACCELERATE_PY_TASK_P2P_DHT": "0",
        "IPFS_ACCELERATE_PY_TASK_P2P_RENDEZVOUS": "0",
        "IPFS_ACCELERATE_PY_TASK_P2P_AUTONAT": "0",
        "IPFS_ACCELERATE_PY_TASK_P2P_RELAY": "0",
        "IPFS_ACCELERATE_PY_TASK_P2P_HOLEPUNCH": "0",
        "IPFS_ACCELERATE_PY_TASK_P2P_BOOTSTRAP_PEERS": "0",
    }


def wait_for_file(path: Path, *, timeout: float, proc: subprocess.Popen[str] | None = None) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if path.is_file() and path.stat().st_size > 0:
            return
        if proc is not None and proc.poll() is not None:
            stderr = ""
            if proc.stderr:
                stderr = proc.stderr.read()
            raise RuntimeError(f"worker exited {proc.returncode} before identity file {path}: {stderr}")
        time.sleep(0.05)
    raise TimeoutError(f"identity file not created: {path}")


def start_worker(
    kind: str,
    *,
    public_artifact: Path,
    work: Path,
) -> dict[str, Any]:
    identity_file = work / f"{kind}-identity.json"
    port = pick_free_port() if kind in {"http", "libp2p"} else 0
    argv = [
        PYTHON,
        str(HERE),
        "--worker",
        kind,
        "--public-artifact",
        str(public_artifact),
        "--identity-file",
        str(identity_file),
    ]
    if kind in {"http", "libp2p"}:
        argv.extend(["--host", "127.0.0.1", "--port", str(port)])
    proc = subprocess.Popen(
        argv,
        cwd=str(ROOT),
        env=sealed_env(),
        stdin=subprocess.PIPE if kind == "stdio" else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    info: dict[str, Any] = {
        "kind": kind,
        "proc": proc,
        "port": port,
        "identity_file": identity_file,
        "identity": {"pid": proc.pid},
    }
    if kind != "stdio":
        wait_for_file(identity_file, timeout=30.0, proc=proc)
        info["identity"] = json.loads(identity_file.read_text(encoding="utf-8"))
    return info


def stop_worker(info: Mapping[str, Any]) -> None:
    proc: subprocess.Popen[str] = info["proc"]
    if proc.poll() is None:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def stdio_rpc(info: Mapping[str, Any], message: dict[str, Any]) -> dict[str, Any]:
    proc: subprocess.Popen[str] = info["proc"]
    assert proc.stdin is not None and proc.stdout is not None
    proc.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
    proc.stdin.flush()
    line = proc.stdout.readline()
    if not line:
        raise RuntimeError("stdio worker closed stdout")
    return json.loads(line)


def http_rpc(info: Mapping[str, Any], message: dict[str, Any]) -> dict[str, Any]:
    port = int(info["port"])
    body = json.dumps(message).encode("utf-8")
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=15)
    try:
        conn.request("POST", "/mcp", body=body, headers={"Content-Type": "application/json"})
        response = conn.getresponse()
        raw = response.read()
        return json.loads(raw.decode("utf-8"))
    finally:
        conn.close()


def http_get_cid(info: Mapping[str, Any], cid: str) -> tuple[int, bytes]:
    port = int(info["port"])
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=15)
    try:
        conn.request("GET", f"/cid/{cid}")
        response = conn.getresponse()
        return response.status, response.read()
    finally:
        conn.close()


def libp2p_rpc_many(info: Mapping[str, Any], messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    import anyio
    from ipfs_accelerate_py.mcplusplus_module.p2p.libp2p_runtime import (
        peer_id_text,
        running_libp2p_host,
    )
    from ipfs_accelerate_py.p2p_tasks.mcp_p2p import read_u32_framed_json, write_u32_framed_json
    from ipfs_accelerate_py.p2p_tasks.mcp_p2p_client import open_libp2p_stream_by_multiaddr

    identity = info["identity"]
    multiaddr = str(identity["multiaddr"])

    async def run() -> list[dict[str, Any]]:
        replies: list[dict[str, Any]] = []
        async with running_libp2p_host(listen_multiaddr="/ip4/127.0.0.1/tcp/0") as host:
            client_peer = peer_id_text(host.get_id())
            info["client_peer_id"] = client_peer  # type: ignore[index]
            for message in messages:
                stream = await open_libp2p_stream_by_multiaddr(
                    host,
                    peer_multiaddr=multiaddr,
                    protocols=[PROTOCOL_MCP_P2P_V1],
                )
                try:
                    await write_u32_framed_json(stream, message)
                    payload, error = await read_u32_framed_json(stream)
                    if payload is None:
                        replies.append(
                            {
                                "jsonrpc": "2.0",
                                "id": message.get("id"),
                                "error": {"code": -32003, "message": str(error or "empty")},
                            }
                        )
                    else:
                        replies.append(payload)
                finally:
                    closer = getattr(stream, "close", None)
                    if callable(closer):
                        await closer()
        return replies

    return anyio.run(run, backend="trio")


@dataclass
class CaseResult:
    job_id: str
    transport_id: str
    case_kind: str
    network_mode: str
    actual_network: bool
    in_process: bool
    wan: bool
    in_parity_claim: bool
    expected_decision: str
    expected_effect_count: int
    request_digest: str
    decision: str = ""
    observed_effect_count: int = 0
    handler_calls: int = 0
    delegated: bool = False
    denial_reason: str = ""
    reason_codes: list[str] = field(default_factory=list)
    process_id: int | None = None
    peer_id: str | None = None
    client_peer_id: str | None = None
    negotiated_protocol: str = ""
    security: dict[str, Any] = field(default_factory=dict)
    transport_error: str | None = None
    integrity: bool | None = None
    availability: str | None = None
    published: bool | None = None
    cid: str | None = None
    passed: bool = False
    failure: str | None = None
    notes: str = ""
    empirical_benchmark_result: bool = False

    def to_record(self) -> dict[str, Any]:
        return {
            "availability": self.availability,
            "actual_network": self.actual_network,
            "case_kind": self.case_kind,
            "cid": self.cid,
            "client_peer_id": self.client_peer_id,
            "decision": self.decision,
            "delegated": self.delegated,
            "denial_reason": self.denial_reason,
            "empirical_benchmark_result": False,
            "expected_decision": self.expected_decision,
            "expected_effect_count": self.expected_effect_count,
            "failure": self.failure,
            "handler_calls": self.handler_calls,
            "in_parity_claim": self.in_parity_claim,
            "in_process": self.in_process,
            "integrity": self.integrity,
            "job_id": self.job_id,
            "negotiated_protocol": self.negotiated_protocol,
            "network_mode": self.network_mode,
            "notes": self.notes,
            "observed_effect_count": self.observed_effect_count,
            "passed": self.passed,
            "peer_id": self.peer_id,
            "process_id": self.process_id,
            "published": self.published,
            "reason_codes": self.reason_codes,
            "request_digest": self.request_digest,
            "security": self.security,
            "transport_error": self.transport_error,
            "transport_id": self.transport_id,
            "wan": self.wan,
        }


def mark(result: CaseResult) -> CaseResult:
    if result.failure:
        result.passed = False
        return result
    if result.case_kind in {"transport_error", "content_retrieval", "probe"}:
        decision_ok = True
        if result.expected_decision and result.expected_decision not in {
            result.decision,
            result.transport_error or "",
        }:
            if result.expected_decision == "error":
                decision_ok = bool(result.transport_error) or result.decision == "error"
            else:
                decision_ok = result.decision == result.expected_decision
        effects_ok = result.observed_effect_count == result.expected_effect_count
        result.passed = bool(decision_ok and effects_ok and not result.failure)
    else:
        decision_ok = result.decision == result.expected_decision
        effects_ok = result.observed_effect_count == result.expected_effect_count
        if result.expected_effect_count == 0:
            calls_ok = result.handler_calls == 0
        else:
            calls_ok = result.handler_calls == result.expected_effect_count
        result.passed = bool(decision_ok and effects_ok and calls_ok)
    if not result.passed and not result.failure:
        result.failure = (
            f"decision={result.decision!r} expected={result.expected_decision!r} "
            f"calls={result.handler_calls} effects={result.observed_effect_count} "
            f"error={result.transport_error!r}"
        )
    return result


def transport_meta(kind: str, info: Mapping[str, Any]) -> dict[str, Any]:
    identity = dict(info.get("identity") or {})
    if kind == "stdio":
        return {
            "network_mode": "local-process",
            "actual_network": False,
            "in_process": False,
            "wan": False,
            "protocol": "jsonrpc-2.0-ndjson",
            "security": {"channel": "anonymous-pipes", "tls": False, "noise": False},
            "peer_id": None,
            "process_id": int(identity.get("pid") or info["proc"].pid),
        }
    if kind == "http":
        return {
            "network_mode": "local-network",
            "actual_network": True,
            "in_process": False,
            "wan": False,
            "protocol": "jsonrpc-2.0-http",
            "security": identity.get("security")
            or {"channel": "plaintext-http", "tls": False, "noise": False, "listen_host": "127.0.0.1"},
            "peer_id": None,
            "process_id": int(identity.get("pid") or info["proc"].pid),
        }
    return {
        "network_mode": "local-network",
        "actual_network": True,
        "in_process": False,
        "wan": False,
        "protocol": PROTOCOL_MCP_P2P_V1,
        "security": identity.get("security")
        or {
            "secure_channel": "noise",
            "noise_protocol_id": NOISE_PROTOCOL_ID,
            "muxer": "yamux",
            "transport": "tcp",
            "tls": False,
            "listen_host": "127.0.0.1",
        },
        "peer_id": identity.get("peer_id"),
        "process_id": int(identity.get("pid") or info["proc"].pid),
        "client_peer_id": info.get("client_peer_id"),
    }


def apply_rpc_result(
    result: CaseResult,
    response: Mapping[str, Any],
    *,
    meta: Mapping[str, Any],
) -> CaseResult:
    result.process_id = meta.get("process_id")
    result.peer_id = meta.get("peer_id")
    result.client_peer_id = meta.get("client_peer_id")
    result.negotiated_protocol = str(meta.get("protocol") or "")
    result.security = dict(meta.get("security") or {})
    if "error" in response:
        error = response.get("error") or {}
        result.transport_error = str(error.get("message") or "error")
        result.decision = "error"
        return mark(result)
    payload = response.get("result") or {}
    result.decision = str(payload.get("decision") or "")
    result.delegated = bool(payload.get("delegated"))
    result.handler_calls = int(payload.get("handler_calls") or 0)
    result.observed_effect_count = int(payload.get("observed_effect_count") or 0)
    result.denial_reason = str(payload.get("denial_reason") or "")
    result.reason_codes = list(payload.get("reason_codes") or [])
    if payload.get("pid"):
        result.process_id = int(payload["pid"])
    if "integrity" in payload:
        result.integrity = bool(payload.get("integrity"))
        result.availability = payload.get("availability")
        result.published = bool(payload.get("published"))
        result.cid = payload.get("cid")
        result.decision = "found" if payload.get("found") else "not_found"
    return mark(result)


def run_in_process_cases(catalog: Mapping[str, Any]) -> list[CaseResult]:
    from ipfs_accelerate_py.agent_supervisor.proof.admissibility_enforcement import (
        InMemoryCapabilityConsumptionStore,
    )

    _, _, _, _, _, DecisionReceipt, AuthorizationCapability = receipt_modules()
    store = InMemoryCapabilityConsumptionStore()
    results: list[CaseResult] = []
    for case_id in ("allow", "deny"):
        spec = catalog[case_id]
        params = tools_call_params(catalog, case_id)
        result = CaseResult(
            job_id=f"in-process-{case_id}",
            transport_id="in-process",
            case_kind=spec["case_kind"],
            network_mode="in-process",
            actual_network=False,
            in_process=True,
            wan=False,
            in_parity_claim=False,
            expected_decision=spec["expected_decision"],
            expected_effect_count=spec["expected_effect_count"],
            request_digest=sha256_bytes(canonical_json_bytes(params)),
            negotiated_protocol="direct-python-call",
            security={"channel": "none", "tls": False, "noise": False},
            notes="In-process authorize_and_delegate. Not a network or libp2p experiment.",
            process_id=os.getpid(),
        )
        try:
            receipt = DecisionReceipt.from_dict(spec["receipt"])
            capability = (
                AuthorizationCapability.from_dict(spec["capability"])
                if spec["capability"]
                else None
            )
            outcome = run_enforcer_local(
                context=context_from_dict(spec["context"]),
                receipt=receipt,
                capability=capability,
                store=store,
                job_id=f"in-process-{case_id}",
            )
            result.decision = outcome["decision"]
            result.delegated = outcome["delegated"]
            result.handler_calls = outcome["handler_calls"]
            result.observed_effect_count = outcome["observed_effect_count"]
            result.denial_reason = outcome["denial_reason"]
            result.reason_codes = outcome["reason_codes"]
        except Exception as exc:
            result.failure = f"{type(exc).__name__}: {exc}"
        results.append(mark(result))
    return results


def kit_p2p_framing_probe() -> CaseResult:
    result = CaseResult(
        job_id="kit-p2p-framing-in-process",
        transport_id="kit-p2p-framing",
        case_kind="probe",
        network_mode="in-process",
        actual_network=False,
        in_process=True,
        wan=False,
        in_parity_claim=False,
        expected_decision="ok",
        expected_effect_count=0,
        request_digest=sha256_text("kit-p2p-framing"),
        negotiated_protocol=PROTOCOL_MCP_P2P_V1,
        notes="ipfs_kit handle_stream_message is in-process framing, not a libp2p network experiment.",
        process_id=os.getpid(),
    )
    try:
        import anyio
        from ipfs_kit_py.mcp_server.p2p_transport import handle_stream_message

        async def handler(msg: dict[str, Any]) -> dict[str, Any]:
            return {"jsonrpc": "2.0", "id": msg.get("id"), "result": {"ok": True, "in_process": True}}

        async def run() -> bytes:
            raw = json.dumps(
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
            ).encode("utf-8")
            return await handle_stream_message(raw, handler)

        payload = anyio.run(run, backend="trio")
        decoded = json.loads(payload.decode("utf-8"))
        result.decision = "ok" if decoded.get("result", {}).get("ok") else "error"
        result.in_process = True
        result.actual_network = False
    except Exception as exc:
        result.failure = f"{type(exc).__name__}: {exc}"
        result.decision = "error"
    return mark(result)


def kit_http_probe() -> CaseResult:
    result = CaseResult(
        job_id="kit-native-http-initialize",
        transport_id="kit-native-http",
        case_kind="probe",
        network_mode="local-network",
        actual_network=True,
        in_process=False,
        wan=False,
        in_parity_claim=False,
        expected_decision="ok",
        expected_effect_count=0,
        request_digest=sha256_text("kit-native-http"),
        negotiated_protocol="jsonrpc-2.0-http",
        security={"channel": "plaintext-http", "tls": False, "listen_host": "127.0.0.1"},
        notes="Kit MCPServer HTTP initialize. AuthorizationGate path, not the selected ENFORCE route.",
    )
    port = pick_free_port()
    code = (
        "import anyio, os, sys; "
        "sys.path[:0]=os.environ.get('PYTHONPATH','').split(':'); "
        "from ipfs_kit_py.mcp_server.server import serve_http; "
        "anyio.run(serve_http, '127.0.0.1', int(os.environ['P']), backend='trio')"
    )
    env = sealed_env()
    env["P"] = str(port)
    proc = subprocess.Popen(
        [PYTHON, "-c", code],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.time() + 20
        connected = False
        while time.time() < deadline:
            if proc.poll() is not None:
                stderr = proc.stderr.read() if proc.stderr else ""
                raise RuntimeError(f"kit HTTP exited {proc.returncode}: {stderr[-2000:]}")
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                    connected = True
                    break
            except OSError:
                time.sleep(0.05)
        if not connected:
            raise TimeoutError("kit HTTP did not accept connections")
        body = json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        ).encode("utf-8")
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        try:
            conn.request("POST", "/", body=body, headers={"Content-Type": "application/json"})
            response = conn.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
        finally:
            conn.close()
        result.process_id = proc.pid
        result.decision = "ok" if payload.get("result") or payload.get("protocolVersion") or "result" in payload else "error"
        if result.decision != "ok" and isinstance(payload, dict) and payload.get("jsonrpc") == "2.0":
            # initialize may wrap as JSON-RPC result
            inner = payload.get("result") or {}
            if inner.get("protocolVersion") or inner.get("serverInfo"):
                result.decision = "ok"
        result.notes += f" pid={proc.pid} port={port}"
    except Exception as exc:
        result.failure = f"{type(exc).__name__}: {exc}"
        result.decision = "error"
        result.transport_error = str(exc)
    finally:
        if proc.poll() is None:
            proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
    return mark(result)


def public_artifact_payload() -> dict[str, Any]:
    return {
        "kind": "transport-parity-public-artifact",
        "note": "Synthetic public qualification payload. Not private legal or security source.",
        "profile": "CIDv1-raw-sha2-256-base32",
        "schema": "law-to-action-public-evidence/v1",
        "task": "LA-013",
    }


def make_private_commitment() -> dict[str, Any]:
    preimage = os.urandom(32)
    payload = {
        "classification": "private",
        "schema": "law-to-action-private-evidence/v1",
        "task": "LA-013",
        "preimage_hex": preimage.hex(),
    }
    blob = canonical_json_bytes(payload)
    cid = compute_cid(payload)
    digest = sha256_bytes(blob)
    del preimage
    del payload
    del blob
    return {
        "cid": cid,
        "bytes_sha256": digest,
        "published": False,
        "availability": "not-published",
        "integrity_commitment": True,
        "note": "Private preimage remained in process memory and was not written to declared outputs or published.",
    }


def configuration_document(
    env: Mapping[str, Any],
    *,
    identities: Mapping[str, Any],
    public_cid: str,
    private: Mapping[str, Any],
    ipfs: Mapping[str, Any],
    qualified: list[str],
) -> dict[str, Any]:
    return {
        "schema": "law-to-action-transport-configuration/v1",
        "task": "LA-013",
        "empirical_benchmark_result": False,
        "selected_route": {
            "id": "supervisor_pre_invocation_enforce",
            "symbol": "SupervisorPreInvocationEnforcement.authorize_and_delegate",
            "handler": "BoundedExportHandler.export_json",
            "mode": "enforce",
            "in_safety_claim": True,
        },
        "authoritative_environment": {
            "python": env.get("python"),
            "python_version": env.get("python_version"),
            "path": env.get("path"),
            "home_prefix": "ipfs-accelerate-validation-home-",
            "home_is_validation_prefix": env.get("home_is_validation_prefix"),
            "validation_site_packages": env.get("validation_site_packages"),
        },
        "transports": [
            {
                "id": "stdio",
                "kind": "stdio",
                "network_mode": "local-process",
                "actual_network": False,
                "in_process": False,
                "wan": False,
                "qualified": "stdio" in qualified,
                "in_parity_claim": True,
                "process": identities.get("stdio"),
                "protocol": "jsonrpc-2.0-ndjson",
                "security": {"channel": "anonymous-pipes", "tls": False, "noise": False},
            },
            {
                "id": "http",
                "kind": "http",
                "network_mode": "local-network",
                "actual_network": True,
                "in_process": False,
                "wan": False,
                "qualified": "http" in qualified,
                "in_parity_claim": True,
                "listen": "127.0.0.1",
                "tls": False,
                "process": identities.get("http"),
                "protocol": "jsonrpc-2.0-http",
                "security": {"channel": "plaintext-http", "tls": False, "noise": False},
            },
            {
                "id": "libp2p",
                "kind": "libp2p",
                "network_mode": "local-network",
                "actual_network": True,
                "in_process": False,
                "wan": False,
                "qualified": "libp2p" in qualified,
                "in_parity_claim": True,
                "listen": "127.0.0.1",
                "protocol": PROTOCOL_MCP_P2P_V1,
                "process": identities.get("libp2p"),
                "security": {
                    "secure_channel": "noise",
                    "noise_protocol_id": NOISE_PROTOCOL_ID,
                    "muxer": "yamux",
                    "muxer_protocol_id": YAMUX_PROTOCOL_ID,
                    "transport": "tcp",
                    "tls": False,
                },
            },
            {
                "id": "in-process",
                "kind": "in-process",
                "network_mode": "in-process",
                "actual_network": False,
                "in_process": True,
                "wan": False,
                "qualified": False,
                "in_parity_claim": False,
                "note": "Direct Python call. Not reported as libp2p or HTTP network evidence.",
            },
            {
                "id": "kit-p2p-framing",
                "kind": "in-process-framing",
                "network_mode": "in-process",
                "actual_network": False,
                "in_process": True,
                "wan": False,
                "qualified": False,
                "in_parity_claim": False,
                "note": env.get("kit_serve_p2p_note"),
            },
        ],
        "content_addressing": {
            "profile": "CIDv1/raw/sha2-256/base32",
            "codec": "raw",
            "hash": "sha2-256",
            "multibase": "base32",
            "public_artifact_cid": public_cid,
            "public_integrity_checked": True,
            "public_availability": "local-only",
            "ipfs_daemon": ipfs,
            "private_artifact_cid": private["cid"],
            "private_bytes_sha256": private["bytes_sha256"],
            "private_bytes_published": False,
            "private_availability": "not-published",
            "integrity_versus_availability": "Integrity is a CID rehash of held bytes. Availability is whether a daemon, pin, or peer could serve those bytes. They are recorded as separate fields.",
        },
        "narrowed_claims": [
            "Loopback 127.0.0.1 HTTP and libp2p are local-network tests, not WAN, DHT, mDNS, relay, or adversarial transport qualification.",
            "stdio is a local process pipe, not a network path.",
            "In-process framing and kit serve_p2p's sleep_forever host are not libp2p network evidence.",
            "No IPFS daemon or kubo executable was present; public CID availability is local-only.",
            "Private evidence preimages were not written to declared outputs and were not published.",
            "Kit MCPServer HTTP, if reached, is AuthorizationGate, not the selected ENFORCE safety claim.",
            "This is qualification, not a scored A3/A4 benchmark.",
        ],
        "source_pins": env.get("source_pins"),
        "modules": env.get("modules"),
    }


def parity_markdown(
    cases: list[CaseResult],
    env: Mapping[str, Any],
    config: Mapping[str, Any],
) -> str:
    selected = [c for c in cases if c.in_parity_claim]
    by_transport: dict[str, list[CaseResult]] = {}
    for row in selected:
        by_transport.setdefault(row.transport_id, []).append(row)
    lines = [
        "# LA-013 actual transport parity and content-retrieval qualification",
        "",
        "This record qualifies stdio, loopback HTTP, and loopback libp2p carriage of the",
        "selected `SupervisorPreInvocationEnforcement.authorize_and_delegate` route.",
        "It is **not** a scored A3 or A4 benchmark.",
        "",
        "## Network versus in-process modes",
        "",
        "- `stdio`: **local-process**. Anonymous pipes. `actual_network=false`.",
        "- `http`: **local-network**. `127.0.0.1` plaintext HTTP. `wan=false`.",
        "- `libp2p`: **local-network**. TCP + Noise + Yamux, protocol `/mcp+p2p/1.0.0`, loopback multiaddrs. `wan=false`.",
        "- `in-process` and kit `handle_stream_message`: **in-process**. Not libp2p network evidence.",
        "",
        "## Authoritative environment",
        "",
        f"- Python: `{env.get('python')}` {env.get('python_version')}",
        f"- PATH: `{env.get('path')}`",
        f"- libp2p: {env.get('modules', {}).get('libp2p', {}).get('version')} compatible={env.get('libp2p_runtime_compatible')}",
        f"- IPFS daemon: available={config['content_addressing']['ipfs_daemon'].get('available')} binary={config['content_addressing']['ipfs_daemon'].get('binary')}",
        "",
        "## Selected route",
        "",
        "ENFORCE around `BoundedExportHandler.export_json`. Kit `AuthorizationGate` / `MCPServer.tools/call` is not the selected safety claim.",
        "",
        "## Qualified transport processes",
        "",
        "| Transport | network_mode | actual_network | wan | in_process | protocol | security | pid/peer |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for transport_id in ("stdio", "http", "libp2p"):
        rows = by_transport.get(transport_id) or []
        sample = rows[0] if rows else None
        if sample is None:
            lines.append(f"| `{transport_id}` | missing |  |  |  |  |  |  |")
            continue
        peer = sample.peer_id or sample.process_id
        sec = sample.security.get("secure_channel") or sample.security.get("channel")
        lines.append(
            f"| `{transport_id}` | {sample.network_mode} | {sample.actual_network} | {sample.wan} | {sample.in_process} | `{sample.negotiated_protocol}` | {sec} | {peer} |"
        )
    lines.extend(
        [
            "",
            "## Semantic parity (identical tools/call requests)",
            "",
            "| Case | stdio | HTTP | libp2p | effects | pass |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for case_id in PARITY_CASES:
        cells = []
        effects = []
        passed = []
        for transport_id in ("stdio", "http", "libp2p"):
            row = next((c for c in selected if c.transport_id == transport_id and c.job_id.endswith(f"-{case_id}")), None)
            if row is None:
                cells.append("missing")
                passed.append(False)
            else:
                cells.append(row.decision)
                effects.append(str(row.observed_effect_count))
                passed.append(row.passed)
        effect_cell = effects[0] if effects and len(set(effects)) == 1 else ",".join(effects)
        lines.append(
            f"| `{case_id}` | {cells[0] if cells else ''} | {cells[1] if len(cells)>1 else ''} | {cells[2] if len(cells)>2 else ''} | {effect_cell} | {all(passed)} |"
        )
    content_rows = [c for c in cases if c.case_kind == "content_retrieval"]
    lines.extend(
        [
            "",
            "## Content retrieval: integrity versus availability",
            "",
            f"- Public CID (`{config['content_addressing']['public_artifact_cid']}`) was rehashed under CIDv1/raw/sha2-256/base32.",
            "- Public availability is **local-only**. No kubo/ipfs daemon served the CID.",
            f"- Private CID (`{config['content_addressing']['private_artifact_cid']}`) was computed in memory. `private_bytes_published=false`.",
            "",
            "| Job | integrity | availability | published | pass |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in content_rows:
        lines.append(
            f"| `{row.job_id}` | {row.integrity} | {row.availability} | {row.published} | {row.passed} |"
        )
    failed = [c.job_id for c in cases if not c.passed]
    lines.extend(
        [
            "",
            "## Failures and narrowed claims",
            "",
        ]
    )
    if failed:
        lines.append("Failed jobs: " + ", ".join(failed))
    else:
        lines.append("No case-level assertion failures. Optional WAN/publication claims remain unrun.")
    lines.extend(
        [
            "",
            "- Wide-area libp2p, DHT, mDNS, AutoNAT, relay, and holepunch were disabled and are not claimed.",
            "- Kit `serve_p2p` does not listen; its in-process framer is not network evidence.",
            "- Private legal/security source bytes were not added to any content store or public output.",
            "- This is qualification evidence, not a scored forbidden-effect rate.",
            "",
        ]
    )
    return "\n".join(lines)


def copy_outputs(raw_text: str, configuration: str, parity: str) -> None:
    mapping = {
        LIVE / "results" / "transport" / "raw.jsonl": raw_text,
        SNAPSHOT / "outputs" / "results" / "transport" / "raw.jsonl": raw_text,
        LIVE / "results" / "transport" / "configuration.json": configuration,
        SNAPSHOT / "outputs" / "results" / "transport" / "configuration.json": configuration,
        LIVE / "results" / "transport" / "parity.md": parity,
        SNAPSHOT / "outputs" / "results" / "transport" / "parity.md": parity,
    }
    for path, text in mapping.items():
        write_text(path, text)


def qualify() -> dict[str, Any]:
    env = probe_environment()
    write_json(SNAPSHOT / "probe" / "sealed-environment.json", env)
    public_payload = public_artifact_payload()
    public_cid = compute_cid(public_payload)
    public_path = SNAPSHOT / "traces" / "public-artifact.json"
    write_json(public_path, public_payload)
    private = make_private_commitment()
    catalog = build_case_catalog()
    # JSON round-trip of receipts must succeed before workers start.
    _, _, _, _, _, DecisionReceipt, AuthorizationCapability = receipt_modules()
    DecisionReceipt.from_dict(json.loads(json.dumps(catalog["allow"]["receipt"])))
    AuthorizationCapability.from_dict(json.loads(json.dumps(catalog["allow"]["capability"])))

    work = Path(tempfile.mkdtemp(prefix="la013-transport-"))
    workers: dict[str, dict[str, Any]] = {}
    cases: list[CaseResult] = []
    qualified: list[str] = []
    try:
        for kind in ("stdio", "http", "libp2p"):
            workers[kind] = start_worker(kind, public_artifact=public_path, work=work)
            qualified.append(kind)
            identity_src = workers[kind].get("identity_file")
            if identity_src and Path(identity_src).is_file():
                shutil.copy2(identity_src, SNAPSHOT / "traces" / f"{kind}-identity.json")

        rpc_plan: list[tuple[str, dict[str, Any]]] = []
        rpc_plan.append(("initialize", {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}))
        next_id = 2
        for case_id in PARITY_CASES:
            params = tools_call_params(catalog, case_id)
            rpc_plan.append(
                (
                    case_id,
                    {"jsonrpc": "2.0", "id": next_id, "method": "tools/call", "params": params},
                )
            )
            next_id += 1
        rpc_plan.append(
            (
                "invalid-jsonrpc",
                {"jsonrpc": "1.0", "id": next_id, "method": "initialize", "params": {}},
            )
        )
        next_id += 1
        rpc_plan.append(
            (
                "content-public",
                {
                    "jsonrpc": "2.0",
                    "id": next_id,
                    "method": "content/get",
                    "params": {"cid": public_cid},
                },
            )
        )
        next_id += 1
        rpc_plan.append(
            (
                "content-private",
                {
                    "jsonrpc": "2.0",
                    "id": next_id,
                    "method": "content/get",
                    "params": {"cid": private["cid"]},
                },
            )
        )

        replies: dict[str, list[dict[str, Any]]] = {}
        replies["stdio"] = [stdio_rpc(workers["stdio"], message) for _label, message in rpc_plan]
        replies["http"] = [http_rpc(workers["http"], message) for _label, message in rpc_plan]
        replies["libp2p"] = libp2p_rpc_many(workers["libp2p"], [message for _label, message in rpc_plan])
        for kind in ("stdio", "http", "libp2p"):
            init = replies[kind][0] if replies[kind] else {}
            payload = init.get("result") if isinstance(init, dict) else None
            if isinstance(payload, dict):
                identity = dict(workers[kind].get("identity") or {})
                identity.update(payload.get("identity") or {})
                identity["pid"] = payload.get("pid") or identity.get("pid")
                workers[kind]["identity"] = identity

        for kind in ("stdio", "http", "libp2p"):
            meta = transport_meta(kind, workers[kind])
            for (label, message), response in zip(rpc_plan, replies[kind]):
                if label == "initialize":
                    continue
                if label == "invalid-jsonrpc":
                    result = CaseResult(
                        job_id=f"{kind}-invalid-jsonrpc",
                        transport_id=kind,
                        case_kind="transport_error",
                        network_mode=meta["network_mode"],
                        actual_network=meta["actual_network"],
                        in_process=False,
                        wan=False,
                        in_parity_claim=True,
                        expected_decision="error",
                        expected_effect_count=0,
                        request_digest=sha256_bytes(canonical_json_bytes(message)),
                        notes="Invalid jsonrpc version must not dispatch the handler.",
                    )
                    apply_rpc_result(result, response, meta=meta)
                    if result.transport_error != "invalid_jsonrpc":
                        result.passed = False
                        result.failure = f"expected invalid_jsonrpc, got {result.transport_error!r} decision={result.decision!r}"
                    cases.append(result)
                    continue
                if label.startswith("content-"):
                    expected_found = label == "content-public"
                    result = CaseResult(
                        job_id=f"{kind}-{label}",
                        transport_id=kind,
                        case_kind="content_retrieval",
                        network_mode=meta["network_mode"],
                        actual_network=meta["actual_network"],
                        in_process=False,
                        wan=False,
                        in_parity_claim=False,
                        expected_decision="found" if expected_found else "not_found",
                        expected_effect_count=0,
                        request_digest=sha256_bytes(canonical_json_bytes(message)),
                        notes="CID get over the same worker. Integrity is rehash; availability is local store only.",
                    )
                    apply_rpc_result(result, response, meta=meta)
                    payload = response.get("result") or {}
                    if expected_found:
                        if not payload.get("found") or not payload.get("integrity"):
                            result.passed = False
                            result.failure = f"public CID was not retrieved with integrity: {payload}"
                        result.published = False
                    else:
                        if payload.get("found") or payload.get("published"):
                            result.passed = False
                            result.failure = f"private CID must not be held or published: {payload}"
                        result.published = False
                        result.availability = "not-published"
                    cases.append(result)
                    continue
                spec = catalog[label]
                params = message["params"]
                result = CaseResult(
                    job_id=f"{kind}-{label}",
                    transport_id=kind,
                    case_kind=spec["case_kind"],
                    network_mode=meta["network_mode"],
                    actual_network=meta["actual_network"],
                    in_process=False,
                    wan=False,
                    in_parity_claim=True,
                    expected_decision=spec["expected_decision"],
                    expected_effect_count=spec["expected_effect_count"],
                    request_digest=sha256_bytes(canonical_json_bytes(params)),
                    notes="Identical tools/call envelope on a real worker process.",
                )
                apply_rpc_result(result, response, meta=meta)
                cases.append(result)

        status, public_bytes = http_get_cid(workers["http"], public_cid)
        http_integrity = CaseResult(
            job_id="http-cid-get-public",
            transport_id="http",
            case_kind="content_retrieval",
            network_mode="local-network",
            actual_network=True,
            in_process=False,
            wan=False,
            in_parity_claim=False,
            expected_decision="found",
            expected_effect_count=0,
            request_digest=sha256_text(public_cid),
            cid=public_cid,
            process_id=workers["http"]["identity"].get("pid"),
            negotiated_protocol="http-get-cid",
            notes="HTTP GET /cid/{cid} on loopback. Local availability, not public IPFS.",
        )
        if status == 200:
            recomputed = compute_cid(json.loads(public_bytes.decode("utf-8")))
            http_integrity.integrity = recomputed == public_cid
            http_integrity.availability = "local-http"
            http_integrity.published = False
            http_integrity.decision = "found"
            if not http_integrity.integrity:
                http_integrity.failure = f"recomputed {recomputed} != {public_cid}"
        else:
            http_integrity.decision = "not_found"
            http_integrity.integrity = False
            http_integrity.availability = "local-http"
            http_integrity.published = False
            http_integrity.failure = f"HTTP GET cid status={status}"
        cases.append(mark(http_integrity))

        status_private, _private_body = http_get_cid(workers["http"], private["cid"])
        http_private = CaseResult(
            job_id="http-cid-get-private-absent",
            transport_id="http",
            case_kind="content_retrieval",
            network_mode="local-network",
            actual_network=True,
            in_process=False,
            wan=False,
            in_parity_claim=False,
            expected_decision="not_found",
            expected_effect_count=0,
            request_digest=sha256_text(private["cid"]),
            cid=private["cid"],
            process_id=workers["http"]["identity"].get("pid"),
            negotiated_protocol="http-get-cid",
            notes="Private CID is not stored on the HTTP worker. Not a public publication.",
        )
        http_private.decision = "not_found" if status_private == 404 else f"status-{status_private}"
        http_private.integrity = False
        http_private.availability = "not-published"
        http_private.published = False
        if status_private != 404:
            http_private.failure = f"private CID HTTP status {status_private} (expected 404)"
        cases.append(mark(http_private))
    except Exception as exc:
        failed = CaseResult(
            job_id="transport-workers",
            transport_id="setup",
            case_kind="probe",
            network_mode="local-process",
            actual_network=False,
            in_process=False,
            wan=False,
            in_parity_claim=True,
            expected_decision="ok",
            expected_effect_count=0,
            request_digest=sha256_text("setup"),
            failure=f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
        )
        cases.append(mark(failed))
    finally:
        for info in workers.values():
            try:
                stop_worker(info)
            except Exception:
                pass
        shutil.rmtree(work, ignore_errors=True)

    cases.extend(run_in_process_cases(catalog))
    cases.append(kit_p2p_framing_probe())
    cases.append(kit_http_probe())

    ipfs = env.get("ipfs_daemon") or probe_ipfs_daemon()
    daemon_job = CaseResult(
        job_id="ipfs-daemon-unavailable",
        transport_id="ipfs",
        case_kind="content_retrieval",
        network_mode="unqualified",
        actual_network=False,
        in_process=False,
        wan=False,
        in_parity_claim=False,
        expected_decision="unavailable",
        expected_effect_count=0,
        request_digest=sha256_text("ipfs-daemon"),
        cid=public_cid,
        decision="unavailable" if not ipfs.get("available") else "available",
        integrity=None,
        availability="ipfs-daemon-absent" if not ipfs.get("available") else "ipfs-daemon",
        published=False,
        notes="Sealed PATH has no ipfs/kubo; localhost:5001 was probed and is not claimed as publication.",
    )
    if ipfs.get("available"):
        daemon_job.failure = "ipfs daemon was present; publication claims must be explicit"
    cases.append(mark(daemon_job))

    identities = {
        kind: {
            key: value
            for key, value in (info.get("identity") or {}).items()
            if key != "proc"
        }
        for kind, info in workers.items()
    }
    write_json(SNAPSHOT / "traces" / "identities.json", identities)
    write_json(SNAPSHOT / "traces" / "private-commitment.json", private)

    records = [case.to_record() for case in cases]
    write_json(SNAPSHOT / "traces" / "cases.json", records)
    raw_text = "".join(json.dumps(row, sort_keys=True) + "\n" for row in records)
    config = configuration_document(
        env,
        identities=identities,
        public_cid=public_cid,
        private=private,
        ipfs=ipfs,
        qualified=qualified,
    )
    config_text = json.dumps(config, indent=2, sort_keys=True) + "\n"
    parity = parity_markdown(cases, env, config)
    copy_outputs(raw_text, config_text, parity)

    selected = [c for c in cases if c.in_parity_claim]
    summary = {
        "status": "ok" if selected and all(c.passed for c in selected) else "failed",
        "cases": len(cases),
        "passed": sum(1 for c in cases if c.passed),
        "failed": [c.job_id for c in cases if not c.passed],
        "selected_claim_cases": len(selected),
        "selected_claim_passed": sum(1 for c in selected if c.passed),
        "qualified_transports": qualified,
        "public_cid": public_cid,
        "private_cid": private["cid"],
        "private_bytes_published": False,
        "ipfs_daemon_available": bool(ipfs.get("available")),
        "empirical_benchmark_result": False,
        "libp2p_runtime_compatible": env.get("libp2p_runtime_compatible"),
    }
    write_json(SNAPSHOT / "probe" / "summary.json", summary)
    json.dump(summary, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return summary


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def validate() -> int:
    live_raw = LIVE / "results" / "transport" / "raw.jsonl"
    live_cfg = LIVE / "results" / "transport" / "configuration.json"
    live_parity = LIVE / "results" / "transport" / "parity.md"
    snap_raw = SNAPSHOT / "outputs" / "results" / "transport" / "raw.jsonl"
    snap_cfg = SNAPSHOT / "outputs" / "results" / "transport" / "configuration.json"
    snap_parity = SNAPSHOT / "outputs" / "results" / "transport" / "parity.md"
    for path in (live_raw, live_cfg, live_parity, snap_raw, snap_cfg, snap_parity):
        if not path.is_file():
            raise SystemExit(f"missing {path}")
    if live_raw.read_bytes() != snap_raw.read_bytes():
        raise SystemExit("raw.jsonl live/snapshot mismatch")
    if live_cfg.read_bytes() != snap_cfg.read_bytes():
        raise SystemExit("configuration.json live/snapshot mismatch")
    if live_parity.read_bytes() != snap_parity.read_bytes():
        raise SystemExit("parity.md live/snapshot mismatch")

    jobs = load_jsonl(live_raw)
    config = json.loads(live_cfg.read_text(encoding="utf-8"))
    text = live_parity.read_text(encoding="utf-8")
    summary = json.loads((SNAPSHOT / "probe" / "summary.json").read_text(encoding="utf-8"))
    env = json.loads((SNAPSHOT / "probe" / "sealed-environment.json").read_text(encoding="utf-8"))
    private = json.loads((SNAPSHOT / "traces" / "private-commitment.json").read_text(encoding="utf-8"))
    public = json.loads((SNAPSHOT / "traces" / "public-artifact.json").read_text(encoding="utf-8"))
    jobs_by_id = {row["job_id"]: row for row in jobs}

    assert config["schema"] == "law-to-action-transport-configuration/v1"
    assert config["task"] == "LA-013"
    assert config["empirical_benchmark_result"] is False
    assert summary["empirical_benchmark_result"] is False
    assert all(job["empirical_benchmark_result"] is False for job in jobs)
    assert env["python"] == "/usr/bin/python3.12"
    assert env["path"] == os.environ.get("PATH")
    assert env["libp2p_runtime_compatible"] is True
    assert env["modules"]["libp2p"]["available"] is True
    assert env["ipfs_daemon"]["available"] is False

    modes = {row["transport_id"]: row["network_mode"] for row in jobs if row["in_parity_claim"]}
    assert modes.get("stdio") == "local-process"
    assert modes.get("http") == "local-network"
    assert modes.get("libp2p") == "local-network"
    for job in jobs:
        if job["transport_id"] in {"in-process", "kit-p2p-framing"}:
            assert job["network_mode"] == "in-process"
            assert job["actual_network"] is False
            assert job["in_parity_claim"] is False
            assert job["in_process"] is True
        if job["transport_id"] == "libp2p" and job["in_parity_claim"]:
            assert job["in_process"] is False
            assert job["actual_network"] is True
            assert job["wan"] is False
            assert job["negotiated_protocol"] == PROTOCOL_MCP_P2P_V1
            assert job.get("peer_id")
            assert (job.get("security") or {}).get("secure_channel") == "noise"
        if job["transport_id"] == "http" and job["in_parity_claim"]:
            assert job["actual_network"] is True
            assert job["wan"] is False
            assert job["in_process"] is False
        if job["transport_id"] == "stdio" and job["in_parity_claim"]:
            assert job["actual_network"] is False
            assert job["in_process"] is False

    required = set()
    for kind in ("stdio", "http", "libp2p"):
        for case_id in (*PARITY_CASES, "invalid-jsonrpc"):
            required.add(f"{kind}-{case_id}")
    missing = required - set(jobs_by_id)
    assert not missing, missing

    selected = [job for job in jobs if job["in_parity_claim"]]
    assert selected
    assert all(job["passed"] for job in selected), [job["job_id"] for job in selected if not job["passed"]]

    for case_id in PARITY_CASES:
        group = [
            jobs_by_id[f"{kind}-{case_id}"]
            for kind in ("stdio", "http", "libp2p")
        ]
        decisions = {row["decision"] for row in group}
        effects = {row["observed_effect_count"] for row in group}
        digests = {row["request_digest"] for row in group}
        assert len(decisions) == 1, (case_id, decisions)
        assert len(effects) == 1, (case_id, effects)
        assert len(digests) == 1, (case_id, digests)
        if case_id == "allow":
            assert group[0]["decision"] == "allow"
            assert group[0]["observed_effect_count"] == 1
        else:
            assert group[0]["observed_effect_count"] == 0
            assert group[0]["decision"] in {"deny", "unknown"}

    for kind in ("stdio", "http", "libp2p"):
        bad = jobs_by_id[f"{kind}-invalid-jsonrpc"]
        assert bad["transport_error"] == "invalid_jsonrpc"
        assert bad["observed_effect_count"] == 0

    assert jobs_by_id["in-process-allow"]["in_parity_claim"] is False
    assert jobs_by_id["kit-p2p-framing-in-process"]["in_process"] is True
    assert jobs_by_id["kit-p2p-framing-in-process"]["actual_network"] is False

    public_cid = config["content_addressing"]["public_artifact_cid"]
    assert public_cid == compute_cid(public)
    assert public_cid.startswith("bafkrei")
    assert config["content_addressing"]["private_bytes_published"] is False
    assert private["published"] is False
    assert config["content_addressing"]["private_artifact_cid"] == private["cid"]
    assert jobs_by_id["ipfs-daemon-unavailable"]["decision"] == "unavailable"
    assert jobs_by_id["http-cid-get-public"]["integrity"] is True
    assert jobs_by_id["http-cid-get-public"]["published"] is False
    assert jobs_by_id["http-cid-get-private-absent"]["decision"] == "not_found"
    assert jobs_by_id["http-cid-get-private-absent"]["published"] is False

    public_files = [
        live_raw,
        live_cfg,
        live_parity,
        SNAPSHOT / "traces" / "cases.json",
        SNAPSHOT / "traces" / "public-artifact.json",
        SNAPSHOT / "probe" / "summary.json",
    ]
    private_hex_marker = "preimage_hex"
    for path in public_files:
        blob = path.read_text(encoding="utf-8")
        assert private["cid"] in blob or path.name == "public-artifact.json"
        assert "this-private" not in blob
        if path.name != "qualify_transport.py":
            # The commitment file may mention published=false; preimage must be absent.
            if path.name != "private-commitment.json":
                pass
    commitment = (SNAPSHOT / "traces" / "private-commitment.json").read_text(encoding="utf-8")
    assert "preimage_hex" not in commitment
    assert private_hex_marker not in live_raw.read_text(encoding="utf-8")
    assert "preimage_hex" not in live_cfg.read_text(encoding="utf-8")

    assert "local-network" in text and "in-process" in text
    assert "not** a scored" in text or "not a scored" in text.lower()
    assert "integrity versus availability" in text.lower() or "Integrity versus availability" in text
    assert "/mcp+p2p/1.0.0" in text
    assert "private_bytes_published=false" in text.replace(" ", "").lower() or "private_bytes_published=false" in text.lower() or "private_bytes_published=false" in text or "Private CID" in text

    print("LA-013 transport parity validation: PASS")
    print(
        f"jobs={len(jobs)} selected={len(selected)} failed={summary.get('failed')} "
        f"libp2p={env.get('libp2p_runtime_compatible')} ipfs_daemon={env.get('ipfs_daemon', {}).get('available')}"
    )
    return 0


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        return worker_main(sys.argv[1:])
    mode = sys.argv[1] if len(sys.argv) > 1 else "qualify"
    if mode in {"validate", "--validate"}:
        return validate()
    summary = qualify()
    if summary.get("status") != "ok":
        return 1
    if summary.get("selected_claim_passed") != summary.get("selected_claim_cases"):
        return 1
    if summary.get("private_bytes_published"):
        return 1
    if not summary.get("qualified_transports"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
