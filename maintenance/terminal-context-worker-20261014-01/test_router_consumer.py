"""Actual native-router local capture, exact delivery and isolated-store controls.

Native function substitutions below are adversarial unit controls only. The
positive control uses the genuine native renderer/router/allocation code.
"""
import hashlib
import json
from pathlib import Path
import tempfile

import pytest

import router_consumer as subject
from token_cost_review import load_tokenizer


PAYLOAD = '{"messages":[{"role":"user","content":"雪 café $0 <|endoftext|>\\nexact bytes"}]}'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture
def local(monkeypatch):
    from ipfs_accelerate_py.llm_allocation import duckdb_store
    # Each unit control owns a genuinely fresh public DB. This reset is confined
    # to tests; the production adapter refuses any already initialized store.
    monkeypatch.setattr(duckdb_store, "_DEFAULT_STORE", None)
    for key in subject._RESPONSE_CACHE_VARIABLES:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("IPFS_ACCELERATE_PY_ROUTER_RESPONSE_CACHE", "0")
    monkeypatch.setenv("IPFS_ACCELERATE_LLM_OBSERVE", "0")
    monkeypatch.setenv("IPFS_ACCELERATE_LLM_ALLOCATE", "0")
    with tempfile.TemporaryDirectory(prefix="router-consumer-unit-", dir=subject.ROOT) as directory:
        path = Path(directory) / "router-allocation.duckdb"
        monkeypatch.setenv("IPFS_ACCELERATE_LLM_ALLOCATION_DB", str(path))
        tokenizer, descriptor = load_tokenizer()
        yield path, tokenizer, descriptor


def capture(local, *, payload=PAYLOAD, **changes):
    arguments = {"payload": payload, "expected_sha256": sha(payload.encode()),
        "expected_bytes": len(payload.encode()), "tokenizer_descriptor": local[2]}
    arguments.update(changes)
    return subject.capture_with_native_router(**arguments)


def test_genuine_native_router_calls_actual_local_consumer_once_and_reports_no_provider_authority(local):
    report = capture(local)
    assert set(report) == {"schema", "provider", "model", "consumer_calls", "input_sha256", "input_bytes",
        "input_local_tokens", "tokenizer_descriptor_sha256", "planning_renderer_identity_verified",
        "native_router_invoked", "ack", "provider_usage", "allocation_store", "claims"}
    assert report["schema"] == subject.SCHEMA
    assert report["provider"] == subject.PROVIDER and report["model"] == subject.MODEL
    assert report["consumer_calls"] == 1
    assert report["input_sha256"] == sha(PAYLOAD.encode())
    assert report["input_bytes"] == len(PAYLOAD.encode())
    assert report["input_local_tokens"] == len(local[1].encode(PAYLOAD))
    assert report["tokenizer_descriptor_sha256"] == sha(json.dumps(local[2], sort_keys=True,
        separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii"))
    assert report["planning_renderer_identity_verified"] is True and report["native_router_invoked"] is True
    assert report["ack"] == "TERMINAL_CONTEXT_CAPTURE_ACK_V1" and report["provider_usage"] is None
    assert report["allocation_store"] == {"path": str(local[0]),
        "profile": "fresh-owned-empty-native-allocation-schema", "slots_before": 0, "slots_after": 0,
        "mutable_rows_before": 0, "mutable_rows_after": 0}
    assert report["claims"] == {"local_consumer_observed": True, "network_provider_invoked": False,
        "native_cli_invocation_receipt": False, "full_supervisor_invoked": False,
        "task_satisfaction": False, "formal_proof": False, "provider_token_savings": False}
    assert local[0].is_file()


@pytest.mark.parametrize("changes", [
    {"expected_sha256": "0" * 64}, {"expected_sha256": "F" * 64}, {"expected_sha256": None},
    {"expected_bytes": 0}, {"expected_bytes": True}, {"expected_bytes": 1.0},
    {"tokenizer_descriptor": []},
])
def test_wrong_predeclared_bindings_refuse_before_any_owned_db_creation(local, changes):
    with pytest.raises(subject.RouterConsumerError):
        capture(local, **changes)
    assert not local[0].exists()


@pytest.mark.parametrize("payload", ["", "x" * (subject.MAX_PAYLOAD_BYTES + 1), "\ud800"])
def test_whole_input_bounds_and_strict_unicode_before_db(local, payload):
    with pytest.raises(subject.RouterConsumerError):
        subject.capture_with_native_router(payload=payload, expected_sha256="0" * 64,
            expected_bytes=1, tokenizer_descriptor=local[2])
    assert not local[0].exists()


@pytest.mark.parametrize("variable", ["IPFS_ACCELERATE_LLM_OBSERVE", "IPFS_ACCELERATE_LLM_ALLOCATE",
    "IPFS_ACCELERATE_PY_ROUTER_RESPONSE_CACHE"])
def test_native_side_effect_and_cache_controls_must_be_explicit_zero(local, monkeypatch, variable):
    monkeypatch.setenv(variable, "1")
    with pytest.raises(subject.RouterConsumerError):
        capture(local)
    assert not local[0].exists()


def test_lowercase_cache_precedence_cannot_override_zero(local, monkeypatch):
    monkeypatch.setenv("ipfs_accelerate_py_ROUTER_RESPONSE_CACHE", "1")
    with pytest.raises(subject.RouterConsumerError, match="response cache"):
        capture(local)
    assert not local[0].exists()


def test_missing_owned_db_override_refuses_private_default(local, monkeypatch):
    monkeypatch.delenv("IPFS_ACCELERATE_LLM_ALLOCATION_DB")
    with pytest.raises(subject.RouterConsumerError, match="owned native allocation"):
        capture(local)
    assert not local[0].exists()


def test_existing_db_or_symlink_is_not_a_fresh_allocation_profile(local):
    local[0].write_bytes(b"unit-owned sentinel")
    with pytest.raises(subject.RouterConsumerError, match="fresh canonical allocation"):
        capture(local)
    assert local[0].read_bytes() == b"unit-owned sentinel"


def test_dangling_symlink_override_is_refused_without_following(local):
    local[0].symlink_to(local[0].parent / "not-created")
    with pytest.raises(subject.RouterConsumerError, match="fresh canonical allocation"):
        capture(local)
    assert not (local[0].parent / "not-created").exists()


def test_dangling_wal_sidecar_is_refused_without_following(local):
    sidecar = Path(str(local[0]) + ".wal")
    sidecar.symlink_to(local[0].parent / "not-created")
    with pytest.raises(subject.RouterConsumerError, match="sidecar already exists"):
        capture(local)
    assert not local[0].exists() and not (local[0].parent / "not-created").exists()


def test_store_outside_owned_stage_is_refused_without_opening(local, monkeypatch, tmp_path):
    outside = tmp_path / "router-allocation.duckdb"
    monkeypatch.setenv("IPFS_ACCELERATE_LLM_ALLOCATION_DB", str(outside))
    with pytest.raises(subject.RouterConsumerError, match="fresh canonical allocation"):
        capture(local)
    assert not outside.exists()


def test_prior_initialized_native_store_is_refused_without_replacing_it(local):
    from ipfs_accelerate_py.llm_allocation import duckdb_store
    prior = duckdb_store.get_allocation_store()
    with pytest.raises(subject.RouterConsumerError, match="fresh process-local"):
        capture(local)
    assert duckdb_store.get_allocation_store() is prior and not local[0].exists()


def test_native_planning_renderer_payload_change_is_refused_before_consumer(local, monkeypatch):
    from ipfs_accelerate_py.agent_supervisor.runtime import router_implementation_runner
    monkeypatch.setattr(router_implementation_runner, "render_model_prompt", lambda **kw: (kw["prompt"] + " ", ""))
    with pytest.raises(subject.RouterConsumerError, match="renderer modified"):
        capture(local)
    assert not local[0].exists()


def test_native_renderer_unrequested_advisory_is_refused(local, monkeypatch):
    from ipfs_accelerate_py.agent_supervisor.runtime import router_implementation_runner
    monkeypatch.setattr(router_implementation_runner, "render_model_prompt", lambda **kw: (kw["prompt"], "extra"))
    with pytest.raises(subject.RouterConsumerError, match="renderer modified"):
        capture(local)
    assert not local[0].exists()


def test_returning_ack_without_calling_consumer_is_not_receipt(local, monkeypatch):
    from ipfs_accelerate_py import llm_router
    monkeypatch.setattr(llm_router, "generate_text", lambda *args, **kw: subject.ACK)
    with pytest.raises(subject.RouterConsumerError, match="one exact acknowledged"):
        capture(local)


def test_capture_occurs_inside_endpoint_not_before_native_router(local, monkeypatch):
    from ipfs_accelerate_py import llm_router
    original = llm_router.generate_text
    endpoint = subject._LocalCapture.generate
    states = []
    def inside(self, prompt, **kwargs):
        states.append(("endpoint", self.calls, self.observed))
        return endpoint(self, prompt, **kwargs)
    def outside(*args, **kwargs):
        consumer = kwargs["provider_instance"]
        states.append(("router-entry", consumer.calls, consumer.observed))
        result = original(*args, **kwargs)
        states.append(("router-exit", consumer.calls, dict(consumer.observed)))
        return result
    monkeypatch.setattr(subject._LocalCapture, "generate", inside)
    monkeypatch.setattr(llm_router, "generate_text", outside)
    capture(local)
    assert states[:2] == [("router-entry", 0, None), ("endpoint", 0, None)]
    assert states[2][0:2] == ("router-exit", 1)
    assert states[2][2]["input_sha256"] == sha(PAYLOAD.encode())


def test_native_router_mutated_input_refuses_and_never_falls_back_or_retries(local, monkeypatch):
    from ipfs_accelerate_py import llm_router
    original = subject._LocalCapture.generate
    calls = []
    def mutated(self, prompt, **kwargs):
        calls.append(kwargs.get("model_name"))
        return original(self, prompt + " ", **kwargs)
    def forbid(*args, **kwargs):
        raise AssertionError("provider or local fallback must never be consulted")
    monkeypatch.setattr(subject._LocalCapture, "generate", mutated)
    monkeypatch.setattr(llm_router, "_iter_unpinned_optional_providers", forbid)
    monkeypatch.setattr(llm_router, "_get_local_hf_provider", forbid)
    with pytest.raises(subject.RouterConsumerError, match="received modified"):
        capture(local)
    assert calls == [subject.MODEL]


def test_endpoint_wrong_model_or_provider_kwargs_and_second_call_refuse(local):
    consumer = subject._LocalCapture(payload=PAYLOAD, expected_sha256=sha(PAYLOAD.encode()),
        expected_bytes=len(PAYLOAD.encode()), tokenizer=local[1])
    with pytest.raises(subject.RouterConsumerError, match="exact local model"):
        consumer.generate(PAYLOAD, model_name="wrong")
    with pytest.raises(subject.RouterConsumerError, match="exactly once"):
        consumer.generate(PAYLOAD, model_name=subject.MODEL)


def test_native_mutable_allocation_row_after_endpoint_is_refused(local, monkeypatch):
    from ipfs_accelerate_py.llm_allocation import duckdb_store
    original = subject._LocalCapture.generate
    def write_owned_row(self, prompt, **kwargs):
        result = original(self, prompt, **kwargs)
        connection = duckdb_store.get_allocation_store()._connect()
        try:
            connection.execute("INSERT INTO provider_health(provider) VALUES ('unit-control')")
        finally:
            connection.close()
        return result
    monkeypatch.setattr(subject._LocalCapture, "generate", write_owned_row)
    with pytest.raises(subject.RouterConsumerError, match="table is not empty"):
        capture(local)


def test_exact_native_source_pin_failure_prevents_import_or_db_use(local, monkeypatch):
    monkeypatch.setitem(subject._NATIVE_PINS, "llm_router.py", "0" * 64)
    with pytest.raises(subject.RouterConsumerError, match="pinned native source changed"):
        capture(local)
    assert not local[0].exists()
