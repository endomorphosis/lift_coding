"""Observe exact input inside a distinct local backend of the real native router.

This experimental backend acknowledges receipt only. It performs no inference,
source execution, network request or native CLI invocation. The native router
does consult its API-key-slot wrapper even for an injected unknown provider;
that lookup is confined to a fresh, empty, owned native allocation database.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import os
from pathlib import Path
import stat

ROOT = Path(__file__).resolve().parent
NATIVE_ROOT = ROOT.parent / "terminal-dispatch-evidence-20261014-01" / "checkout" / "ipfs_accelerate_py"
SCHEMA = "terminal-planning-admitted-native-router-local-consumer-capture@1"
PROVIDER = "experimental-local-capture"
MODEL = "context-capture-v1"
ACK = "TERMINAL_CONTEXT_CAPTURE_ACK_V1"
MAX_PAYLOAD_BYTES = 500_000
_NATIVE_PINS = {
    "llm_router.py": "4af3f924612b74ff2806293b384f3b5c7da1468c08f5c7dacd6fad7c28bd126d",
    "router_deps.py": "79e400fc5fdb03bad6a9e6f9102721c0080318c26c88f6d914ac9e3ff3a110ab",
    "llm_allocation/duckdb_store.py": "af59a71c8562bab211203efaaf82f210ec071badbf627fc1ef9966f3d5ca44f9",
    "llm_allocation/api_key_slots.py": "0f69974b49684d0fb211ab326150f2c7d8a1fc82c9f634f5108c33885589c43c",
    "agent_supervisor/runtime/router_implementation_runner.py": "9be80225c4ebb4750210fe5d41372066151bc2d20be20570e4091f5020d067ee",
}
_MUTABLE_TABLES = ("allocation_sessions", "api_key_slots", "api_key_stats", "call_observations",
    "cli_session_aliases", "cli_sessions", "provider_health", "session_key_bindings")
_TABLES = frozenset((*_MUTABLE_TABLES, "provider_limits"))
_RESPONSE_CACHE_VARIABLES = ("ipfs_accelerate_py_ROUTER_RESPONSE_CACHE",
    "IPFS_ACCELERATE_PY_ROUTER_RESPONSE_CACHE", "IPFS_DATASETS_PY_ROUTER_RESPONSE_CACHE")
_CLAIMS = {"local_consumer_observed": True, "network_provider_invoked": False,
    "native_cli_invocation_receipt": False, "full_supervisor_invoked": False,
    "task_satisfaction": False, "formal_proof": False, "provider_token_savings": False}


class RouterConsumerError(ValueError):
    """A closed local-consumer boundary or its exact input differs."""


def _need(condition, message):
    if not condition:
        raise RouterConsumerError(message)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def _payload(value):
    _need(type(value) is str, "exact payload text required")
    try:
        raw = value.encode("utf-8", errors="strict")
    except UnicodeError as error:
        raise RouterConsumerError("strict UTF-8 payload required") from error
    _need(0 < len(raw) <= MAX_PAYLOAD_BYTES, "bounded nonempty complete payload required")
    return raw


def _native_witnesses():
    witnesses = {}
    for relative, expected in _NATIVE_PINS.items():
        path = NATIVE_ROOT / relative
        _need(path.resolve(strict=True) == path, "canonical pinned native source required")
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as stream:
            before = os.fstat(stream.fileno())
            _need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                  and 0 < before.st_size <= 2_000_000, "bounded single-link native source required")
            raw = stream.read(2_000_001)
            after = os.fstat(stream.fileno())
        identity = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_ctime_ns)
        _need(len(raw) == before.st_size and _sha(raw) == expected
              and identity(before) == identity(after) == identity(path.lstat()),
              "pinned native source changed")
        witnesses[relative] = (identity(before), expected)
    return witnesses


def _module(name, relative):
    module = importlib.import_module(name)
    _need(Path(module.__file__) == NATIVE_ROOT / relative, "loaded native module is outside its exact pin")
    return module


def _owned_allocation_path():
    for name in ("IPFS_ACCELERATE_LLM_OBSERVE", "IPFS_ACCELERATE_LLM_ALLOCATE"):
        _need(os.environ.get(name) == "0", "native observation and allocation must be explicitly disabled")
    values = [os.environ[name] for name in _RESPONSE_CACHE_VARIABLES if name in os.environ]
    _need(bool(values) and all(value == "0" for value in values), "native response cache must be explicitly disabled")
    raw = os.environ.get("IPFS_ACCELERATE_LLM_ALLOCATION_DB", "")
    _need(bool(raw), "fresh owned native allocation override required")
    path = Path(raw)
    _need(path.is_absolute() and path.name == "router-allocation.duckdb"
          and path.parent != ROOT and ROOT in path.parents
          and path.parent.resolve(strict=True) == path.parent and path.parent.is_dir()
          and path.resolve() == path and not path.exists() and not path.is_symlink(),
          "fresh canonical allocation file under an owned experiment output required")
    sidecar = Path(str(path) + ".wal")
    _need(not sidecar.exists() and not sidecar.is_symlink(), "allocation sidecar already exists")
    return path


def _empty_native_store(store, path):
    _need(store.path == path, "native default store escaped the owned allocation override")
    connection = store._connect()
    _need(connection is not None, "actual native DuckDB allocation schema required")
    try:
        tables = connection.execute("SHOW TABLES").fetchall()
        _need(len(tables) == len(_TABLES) and {row[0] for row in tables} == _TABLES,
              "fresh exact native allocation table population required")
        counts = {}
        for name in _MUTABLE_TABLES:
            # Identifiers are fixed module constants, never source or input data.
            row = connection.execute("SELECT count(*) FROM " + name).fetchone()
            _need(type(row[0]) is int and row[0] == 0, "owned native allocation table is not empty")
            counts[name] = row[0]
    finally:
        connection.close()
    info = path.lstat()
    _need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and path.resolve(strict=True) == path,
          "owned native allocation file must remain a single-link regular file")
    return {"slots": counts["api_key_slots"], "mutable_rows": sum(counts.values())}


class _LocalCapture:
    """The actual injected provider endpoint; capture happens only in generate."""
    router_provider_name = PROVIDER

    def __init__(self, *, payload, expected_sha256, expected_bytes, tokenizer):
        self._payload = payload
        self._expected_sha256 = expected_sha256
        self._expected_bytes = expected_bytes
        self._tokenizer = tokenizer
        self.calls = 0
        self.observed = None

    def generate(self, prompt, *, model_name=None, **kwargs):
        self.calls += 1
        _need(self.calls == 1, "local consumer may be invoked exactly once")
        _need(model_name == MODEL and kwargs == {}, "exact local model and no provider kwargs required")
        raw = _payload(prompt)
        _need(prompt == self._payload and len(raw) == self._expected_bytes
              and _sha(raw) == self._expected_sha256, "native consumer received modified complete payload")
        tokens = self._tokenizer.encode(prompt)
        self.observed = {"input_sha256": _sha(raw), "input_bytes": len(raw), "input_local_tokens": len(tokens)}
        return ACK


def capture_with_native_router(*, payload: str, expected_sha256: str, expected_bytes: int,
                               tokenizer_descriptor: dict) -> dict:
    """Invoke the real native renderer/router once and observe its local endpoint.

    Must run in a fresh worker process with an explicit fresh G-owned allocation
    path. Resource/budget admission and current source observations belong to the
    caller. No serialized data here grants those authorities.
    """
    raw = _payload(payload)
    _need(type(expected_sha256) is str and len(expected_sha256) == 64
          and all(char in "0123456789abcdef" for char in expected_sha256)
          and _sha(raw) == expected_sha256, "complete payload SHA differs")
    _need(type(expected_bytes) is int and expected_bytes == len(raw), "complete payload byte count differs")
    _need(type(tokenizer_descriptor) is dict, "exact pinned offline tokenizer descriptor required")
    path = _owned_allocation_path()
    witnesses = _native_witnesses()
    from token_cost_review import load_tokenizer
    tokenizer, descriptor = load_tokenizer(tokenizer_descriptor)
    native = _module("ipfs_accelerate_py.llm_router", "llm_router.py")
    dependencies = _module("ipfs_accelerate_py.router_deps", "router_deps.py")
    renderer = _module("ipfs_accelerate_py.agent_supervisor.runtime.router_implementation_runner",
                       "agent_supervisor/runtime/router_implementation_runner.py")
    allocation = _module("ipfs_accelerate_py.llm_allocation.duckdb_store", "llm_allocation/duckdb_store.py")
    _module("ipfs_accelerate_py.llm_allocation.api_key_slots", "llm_allocation/api_key_slots.py")
    _need(allocation._DEFAULT_STORE is None, "fresh process-local native allocation store required")
    _need(native._response_cache_enabled() is False, "native response caching is enabled")
    _need(native._effective_llm_provider_name(PROVIDER) == PROVIDER,
          "native provider alias changed experimental local identity")
    rendered, advisory = renderer.render_model_prompt(prompt=payload, purpose="planning", workspace=Path.cwd())
    _need(type(rendered) is str and rendered == payload and advisory == "",
          "native planning renderer modified complete payload")
    store = allocation.get_allocation_store()
    _need(type(store) is allocation.AllocationStore, "original native allocation store required")
    before = _empty_native_store(store, path)
    dependencies_instance = dependencies.RouterDeps()
    _need(dependencies_instance.router_cache == {} and dependencies_instance.accelerate_managers == {}
          and dependencies_instance.remote_cache is None and dependencies_instance.backend_manager is None
          and dependencies_instance.ipfs_backend is None, "fresh neutral native router dependencies required")
    consumer = _LocalCapture(payload=payload, expected_sha256=expected_sha256,
        expected_bytes=expected_bytes, tokenizer=tokenizer)
    response = native.generate_text(rendered, provider=PROVIDER, model_name=MODEL,
        provider_instance=consumer, deps=dependencies_instance,
        allow_local_fallback=False, allow_cross_provider_fallback=False)
    _need(type(response) is str and response == ACK and consumer.calls == 1 and consumer.observed is not None,
          "one exact acknowledged local consumer call required")
    _need(native.get_last_generation_trace() == {"effective_provider_name": PROVIDER, "effective_model_name": MODEL},
          "native router trace differs from explicit local provider/model")
    _need(dependencies_instance.router_cache == {} and dependencies_instance.remote_cache is None,
          "local capture unexpectedly populated or consulted a response cache")
    after = _empty_native_store(store, path)
    _need(_native_witnesses() == witnesses, "native producers changed during local consumer capture")
    return {"schema": SCHEMA, "provider": PROVIDER, "model": MODEL,
        "consumer_calls": consumer.calls, **consumer.observed,
        "tokenizer_descriptor_sha256": _sha(_wire(descriptor)),
        "planning_renderer_identity_verified": True, "native_router_invoked": True,
        "ack": response, "provider_usage": None,
        "allocation_store": {"path": str(path), "profile": "fresh-owned-empty-native-allocation-schema",
            "slots_before": before["slots"], "slots_after": after["slots"],
            "mutable_rows_before": before["mutable_rows"], "mutable_rows_after": after["mutable_rows"]},
        "claims": dict(_CLAIMS)}
