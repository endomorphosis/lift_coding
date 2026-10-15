"""Authored fixtures only; real process dispatch/router, no external provider.

Synthetic observation fixtures exercise pure validators and are never published
as actual worker evidence. Synthetic host samples occur only in these fixtures.
"""
from copy import deepcopy
import os
from pathlib import Path
import tempfile

import pytest

import worker_capture as subject
import context_worker
import capsule_codec
from context_projection import compile_task_context
from nested_context import lift_context_strings
from reference_codec import _envelope, canonical_packet_bytes
from token_cost_review import load_tokenizer
from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
from ipfs_datasets_py.logic.software_contracts.content import cid_for_bytes, cid_for_structured
from ipfs_datasets_py.optimizers.logic_theorem_optimizer.proof_resource_safety import ProofHostResources
from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import (
    GlobalResourceScheduler, ResourceSchedulerConfig, ResourceLane,
)


@pytest.fixture(scope="module")
def authored_request():
    tokenizer, descriptor = load_tokenizer()
    snapshot = cid_for_structured({"schema": "authored-worker-snapshot@1"})
    head = CodebaseHead(repository_id="authored:worker-capture", generation=1,
        manifest_cid=cid_for_structured({"schema": "authored-worker-manifest@1"}), snapshot_cid=snapshot,
        ast_revision_id="rev:authored:worker-capture:snapshot:" + snapshot,
        receipt_cid=cid_for_structured({"schema": "authored-worker-receipt@1"})).to_dict()
    path = "authored-task/environment/unit.py"
    source = b"raise RuntimeError('repository source must never execute')\ndef add(a: int, b: int) -> int:\n    return a + b\n"
    source_cid = cid_for_bytes(source)
    instruction = "  Preserve every source and unresolved instruction. π\n\n".encode()
    task = {"task_id": "authored-task", "sources": [{"path": path, "bytes": len(source), "sha256": subject._sha(source)}],
        "instruction": {"path": "authored-task/instruction.md", "bytes": len(instruction), "sha256": subject._sha(instruction)}}
    codec = {"minified": capsule_codec.build_capsule_codec(source, path, source_cid, head),
        "aliased": capsule_codec.build_capsule_codec(source, path, source_cid, head, aliases=True)}
    projected = compile_task_context(task=task, instruction=instruction, head=head,
        source_rows={path: {"path": path, "source_text": source.decode(), "source_cid": source_cid, "head": head}},
        codec_rows={path: codec}, capsule_summaries=[], tokenizer=tokenizer, arm="raw")
    original = projected["rendered"]
    document = lift_context_strings(original)
    packed = _envelope(document, canonical_packet_bytes(document), [])
    return {"schema": subject.REQUEST_SCHEMA, "request_id": "authored-request", "session_id": "authored-session",
        "expected_head": head, "original_rendered": original, "packed_wire": packed,
        "messages": [{"message_id": "policy", "role": "system", "content": "Plan only; no source execution or proof authority."},
                     {"message_id": "context", "role": "user", "content": original}],
        "context_message_id": "context", "max_input_tokens": 20_000, "tokenizer_descriptor": descriptor,
        "history_required_ids": [], "delivery_mode": "adaptive", "previous_message_manifest": []}


@pytest.fixture
def authored_lease(tmp_path, monkeypatch):
    scheduler = GlobalResourceScheduler(ResourceSchedulerConfig.for_proof_host(
        state_path=tmp_path / "authored-resource-state.json", auto_renew_leases=False,
        proof_resource_sampler=lambda: ProofHostResources(8, 8192, 8192)))
    monkeypatch.setattr(subject, "_shared_state_path", lambda: scheduler.state_path)
    with scheduler.acquire(ResourceLane.ORCHESTRATION, cpu_slots=1, memory_mb=768,
                           child_process_slots=1, timeout=1, request_id="authored-parent") as lease:
        yield lease


@pytest.fixture
def owned_output():
    with tempfile.TemporaryDirectory(prefix=".authored-worker-capture-", dir=subject.ROOT) as directory:
        yield Path(directory) / "capture"


def repository(tmp_path):
    path = tmp_path / "authored-source"
    path.mkdir()
    (path / "unit.py").write_bytes(b"raise RuntimeError('this authored source must not execute')\n")
    return path


def fixture_observation(request, output):
    """Synthetic validator data; never represented as a genuine worker run."""
    selection, manifest = context_worker.prepare_request(deepcopy(request))
    consumer = {"schema": "terminal-native-router-local-consumer-capture@1", "provider": "experimental-local-capture",
        "model": "context-capture-v1", "consumer_calls": 1,
        "input_sha256": selection["payload_sha256"], "input_bytes": selection["payload_bytes"],
        "input_local_tokens": selection["input_tokens"],
        "tokenizer_descriptor_sha256": subject._sha(subject._wire(request["tokenizer_descriptor"])),
        "planning_renderer_identity_verified": True, "native_router_invoked": True,
        "ack": "TERMINAL_CONTEXT_CAPTURE_ACK_V1", "provider_usage": None,
        "allocation_store": {"path": str(output / "router-allocation.duckdb"),
            "profile": "fresh-owned-empty-native-allocation-schema", "slots_before": 0,
            "slots_after": 0, "mutable_rows_before": 0, "mutable_rows_after": 0},
        "claims": deepcopy(subject.CONSUMER_CLAIMS)}
    return {"schema": subject.OBSERVATION_SCHEMA, "request_id": request["request_id"],
        "session_id": request["session_id"], "expected_head": deepcopy(request["expected_head"]),
        "request_sha256": subject._sha(subject._wire(request)), "selection": selection, "consumer": consumer,
        "selected_message_manifest": manifest, "provider_usage": None,
        "actual_external_provider_invocations": 0, **subject.FALSE}


@pytest.mark.parametrize("mode", ["adaptive", "expanded", "packed", "decode_before_model"])
def test_real_native_worker_birth_and_router_capture_preserves_selected_input(
        authored_request, authored_lease, owned_output, tmp_path, mode):
    request = deepcopy(authored_request); request["delivery_mode"] = mode
    result = subject.launch_capture(request=request, repository=repository(tmp_path),
        lease=authored_lease, output_dir=owned_output)
    observation = result["observation"]
    assert result["native_dispatch"]["actual_process_invoked"] is True
    assert result["native_dispatch"]["actual_child_birth"]["pid"] > 0
    assert result["native_dispatch"]["actual_child_birth"]["start_time_ticks"] > 0
    assert result["native_dispatch"]["inherited_environment"] is False
    assert result["native_dispatch"]["shell"] is False
    assert observation["consumer"]["native_router_invoked"] is True
    assert observation["consumer"]["claims"]["network_provider_invoked"] is False
    assert observation["consumer"]["input_sha256"] == observation["selection"]["payload_sha256"]
    assert observation["consumer"]["input_local_tokens"] == observation["selection"]["input_tokens"]
    assert result["provider_usage"] is None and observation["provider_usage"] is None
    assert all(result[key] is False for key in subject.FALSE)
    assert not authored_lease.released and not authored_lease.cancelled
    assert (owned_output / "router-allocation.duckdb").is_file()
    assert (owned_output / "stderr.log").read_bytes() == b""
    assert (owned_output / "stdout.json").read_bytes() == subject._wire(observation)
    if mode == "decode_before_model":
        assert observation["selection"]["selected_form"] == "expanded"
        assert observation["selection"]["signed_local_input_token_difference"] == 0


def test_production_guard_rejects_alternate_pool(authored_request, authored_lease, owned_output, tmp_path, monkeypatch):
    monkeypatch.setattr(subject, "_shared_state_path", lambda: tmp_path / "another-pool.json")
    with pytest.raises(subject.WorkerCaptureError, match="shared proof-safe"):
        subject.launch_capture(request=authored_request, repository=repository(tmp_path),
            lease=authored_lease, output_dir=owned_output)
    assert not owned_output.exists()


def test_cancelled_original_lease_never_launches(authored_request, authored_lease, owned_output, tmp_path):
    authored_lease.cancel()
    with pytest.raises(subject.WorkerCaptureError, match="cancelled"):
        subject.launch_capture(request=authored_request, repository=repository(tmp_path),
            lease=authored_lease, output_dir=owned_output)
    assert not owned_output.exists()


def test_input_budget_denial_occurs_before_process_or_output_creation(authored_request, authored_lease, owned_output, tmp_path):
    request = deepcopy(authored_request); request["max_input_tokens"] = 1
    with pytest.raises(ValueError, match="token budget"):
        subject.launch_capture(request=request, repository=repository(tmp_path), lease=authored_lease, output_dir=owned_output)
    assert not owned_output.exists()


def test_prior_history_cannot_be_reordered_before_spawn(authored_request, authored_lease, owned_output, tmp_path):
    request = deepcopy(authored_request)
    _, manifest = context_worker.prepare_request(request)
    request["previous_message_manifest"] = list(reversed(manifest))
    request["history_required_ids"] = [row["message_id"] for row in manifest]
    with pytest.raises(ValueError, match="ordered prefix"):
        subject.launch_capture(request=request, repository=repository(tmp_path), lease=authored_lease, output_dir=owned_output)
    assert not owned_output.exists()


def test_real_second_packed_turn_preserves_actually_delivered_history(
        authored_request, authored_lease, owned_output, tmp_path):
    source = repository(tmp_path)
    first_request = deepcopy(authored_request); first_request["delivery_mode"] = "packed"
    first = subject.launch_capture(request=first_request, repository=source,
        lease=authored_lease, output_dir=owned_output)
    second_request = deepcopy(first_request); second_request["request_id"] = "authored-second-turn"
    previous = first["observation"]["selected_message_manifest"]
    second_request["previous_message_manifest"] = deepcopy(previous)
    second_request["history_required_ids"] = [row["message_id"] for row in previous]
    second_request["messages"].extend([
        {"message_id": "response:1", "role": "assistant", "content": "TERMINAL_CONTEXT_CAPTURE_ACK_V1"},
        {"message_id": "followup:1", "role": "user", "content": "Keep the same complete context and unresolved obligations."}])
    # The submitted nominated context remains original bytes. Its *selected*
    # historical hash is the actual packed wire, and must stay byte exact.
    assert second_request["messages"][1]["content"] == second_request["original_rendered"]
    assert previous[1]["content_sha256"] == subject._sha(second_request["packed_wire"].encode())
    second = subject.launch_capture(request=second_request, repository=source,
        lease=authored_lease, output_dir=owned_output.with_name("capture-second"))
    assert second["observation"]["selected_message_manifest"][:len(previous)] == previous
    assert second["observation"]["selection"]["input_tokens"] > first["observation"]["selection"]["input_tokens"]
    assert second["observation"]["consumer"]["consumer_calls"] == 1


def test_authored_host_admission_denial_never_starts_process(
        authored_request, authored_lease, owned_output, tmp_path):
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceSchedulerError
    authored_lease._scheduler.config.proof_resource_sampler = lambda: ProofHostResources(8, 8192, 0)
    with pytest.raises(ResourceSchedulerError):
        subject.launch_capture(request=authored_request, repository=repository(tmp_path),
            lease=authored_lease, output_dir=owned_output, timeout_seconds=0.1)
    assert (owned_output / "request.json").is_file()
    assert not (owned_output / "stdout.json").exists()


def test_cancellation_after_actual_birth_fences_worker_before_lease_release(
        authored_request, authored_lease, owned_output, tmp_path, monkeypatch):
    from ipfs_accelerate_py.agent_supervisor.todo_daemon import supervisor_runtime as native
    original_birth = native.read_process_birth
    born = []
    def cancel_at_birth(pid):
        identity = original_birth(pid)
        if identity is not None and not born:
            born.append(pid)
            authored_lease.cancel()
        return identity
    monkeypatch.setattr(native, "read_process_birth", cancel_at_birth)
    with pytest.raises(native.ProcessGroupCancelled):
        subject.launch_capture(request=authored_request, repository=repository(tmp_path),
            lease=authored_lease, output_dir=owned_output)
    assert born
    with pytest.raises(ProcessLookupError): os.kill(born[0], 0)


@pytest.mark.parametrize("damage", ["request", "session", "head", "usage", "provider_count", "authority", "extra",
    "token", "payload_hash", "payload_bytes", "payload", "selection", "manifest", "other_message", "ack",
    "provider", "router", "calls", "store_path", "store_rows", "consumer_claim", "descriptor"])
def test_independently_joined_child_observation_refuses_corruption(authored_request, tmp_path, damage):
    request = deepcopy(authored_request); output = tmp_path / "authored-pure-observation"
    observation = fixture_observation(request, output)
    if damage == "request": observation["request_sha256"] = "0" * 64
    elif damage == "session": observation["session_id"] += "wrong"
    elif damage == "head": observation["expected_head"]["generation"] += 1
    elif damage == "usage": observation["provider_usage"] = {"total": 0}
    elif damage == "provider_count": observation["actual_external_provider_invocations"] = True
    elif damage == "authority": observation["proof_authority"] = True
    elif damage == "extra": observation["provider_receipt"] = "invented"
    elif damage == "token": observation["consumer"]["input_local_tokens"] += 1
    elif damage == "payload_hash": observation["consumer"]["input_sha256"] = "0" * 64
    elif damage == "payload_bytes": observation["consumer"]["input_bytes"] += 1
    elif damage == "payload": observation["selection"]["serialized_payload"] += " "
    elif damage == "selection": observation["selection"]["selected_form"] = "packed"
    elif damage == "manifest": observation["selected_message_manifest"].reverse()
    elif damage == "other_message": observation["selection"]["selected_messages"][0]["content"] += "changed"
    elif damage == "ack": observation["consumer"]["ack"] = "forged"
    elif damage == "provider": observation["consumer"]["provider"] = "codex_cli"
    elif damage == "router": observation["consumer"]["native_router_invoked"] = False
    elif damage == "calls": observation["consumer"]["consumer_calls"] = True
    elif damage == "store_path": observation["consumer"]["allocation_store"]["path"] = "/foreign/private.duckdb"
    elif damage == "store_rows": observation["consumer"]["allocation_store"]["mutable_rows_after"] = 1
    elif damage == "consumer_claim": observation["consumer"]["claims"]["network_provider_invoked"] = True
    elif damage == "descriptor": observation["consumer"]["tokenizer_descriptor_sha256"] = "0" * 64
    with pytest.raises(subject.WorkerCaptureError):
        subject._observation(subject._wire(observation), request, subject._wire(request), output)


def test_valid_authored_pure_observation_and_noncanonical_stdout(authored_request, tmp_path):
    output = tmp_path / "authored-pure-observation"
    observation = fixture_observation(authored_request, output)
    raw = subject._wire(observation)
    assert subject._observation(raw, authored_request, subject._wire(authored_request), output) == observation
    with pytest.raises(subject.WorkerCaptureError, match="canonical"):
        subject._observation(raw + b"\n", authored_request, subject._wire(authored_request), output)


@pytest.mark.parametrize("damage", ["extra", "missing", "omitted_history", "rewritten_history", "duplicate_id",
    "wrong_role", "non_original_context", "huge", "bool_budget"])
def test_closed_bounded_request_and_history_controls(authored_request, damage):
    request = deepcopy(authored_request)
    if damage == "extra": request["private_key"] = "never allowed"
    elif damage == "missing": del request["expected_head"]
    elif damage == "omitted_history": request["history_required_ids"] = ["missing"]
    elif damage == "rewritten_history": request["previous_message_manifest"] = [{"message_id": "policy", "role": "system", "content_sha256": "0" * 64}]
    elif damage == "duplicate_id": request["messages"].append(deepcopy(request["messages"][0]))
    elif damage == "wrong_role": request["messages"][0]["role"] = "unknown"
    elif damage == "non_original_context": request["messages"][1]["content"] += " "
    elif damage == "huge": request["packed_wire"] = "x" * (subject.MAX_TEXT_BYTES + 1)
    elif damage == "bool_budget": request["max_input_tokens"] = True
    with pytest.raises(subject.WorkerCaptureError): subject._request(request)
