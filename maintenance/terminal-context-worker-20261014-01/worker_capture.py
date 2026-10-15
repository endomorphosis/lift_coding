"""Launch a distinct offline capture worker through the native process boundary.

The caller owns current-head observations before/after this separately admitted
dispatch and publishes returned data only after its final observation succeeds.
This is not full supervisor/Portal admission or an existing provider receipt.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import stat
import sys

ROOT = Path(__file__).resolve().parent
CHILD = ROOT / "context_worker.py"
RUNTIME_SOURCE = ROOT.parent / "terminal-dispatch-evidence-20261014-01" / "checkout" / "ipfs_accelerate_py" / "agent_supervisor" / "todo_daemon" / "supervisor_runtime.py"
REQUEST_SCHEMA = "terminal-complete-context-worker-request@1"
OBSERVATION_SCHEMA = "terminal-complete-context-worker-observation@1"
SCHEMA = "terminal-complete-context-worker-launch@1"
MAX_REQUEST_BYTES = 1_048_576
MAX_REPORT_BYTES = 2_000_000
MAX_STDERR_BYTES = 65_536
MAX_TEXT_BYTES = 500_000
FALSE = {name: False for name in (
    "native_full_supervisor_invoked", "official_terminal_bench_harness_executed",
    "proof_authority", "execution_authority", "completion_authority", "task_satisfaction",
    "model_interpretation_equivalence_proved",
)}
REQUEST_FIELDS = {"schema", "request_id", "session_id", "expected_head", "original_rendered", "packed_wire",
    "messages", "context_message_id", "max_input_tokens", "tokenizer_descriptor", "history_required_ids",
    "delivery_mode", "previous_message_manifest"}
OBSERVATION_FIELDS = {"schema", "request_id", "session_id", "expected_head", "request_sha256", "selection",
    "consumer", "selected_message_manifest", "provider_usage", "actual_external_provider_invocations", *FALSE}
CONSUMER_FIELDS = {"schema", "provider", "model", "consumer_calls", "input_sha256", "input_bytes",
    "input_local_tokens", "tokenizer_descriptor_sha256", "planning_renderer_identity_verified",
    "native_router_invoked", "ack", "provider_usage", "allocation_store", "claims"}
CONSUMER_CLAIMS = {"local_consumer_observed": True, "network_provider_invoked": False,
    "native_cli_invocation_receipt": False, "full_supervisor_invoked": False,
    "task_satisfaction": False, "formal_proof": False, "provider_token_savings": False}


class WorkerCaptureError(ValueError):
    """The owned dispatch, exact request or observational receipt differs."""


def _need(value, message):
    if not value:
        raise WorkerCaptureError(message)


def _wire(value):
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                         allow_nan=False).encode("ascii")
    except (TypeError, ValueError, UnicodeError, RecursionError) as error:
        raise WorkerCaptureError("bounded finite plain JSON required") from error
    _need(len(raw) <= MAX_REPORT_BYTES, "complete request/report exceeds declared byte bound")
    return raw


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _text(value, name, maximum=MAX_TEXT_BYTES, nonempty=False):
    _need(type(value) is str, name + " must be exact text")
    try:
        raw = value.encode("utf-8", errors="strict")
    except UnicodeError as error:
        raise WorkerCaptureError(name + " must be strict UTF-8") from error
    _need(len(raw) <= maximum and (not nonempty or bool(raw)), name + " exceeds declared byte bound")
    return raw


def _read(path, maximum, *, empty=False):
    path = Path(path)
    _need(path.is_absolute() and path.resolve(strict=True) == path, "canonical named owned file required")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        _need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
              and (empty or before.st_size > 0) and before.st_size <= maximum,
              "bounded single-link regular owned file required")
        raw = stream.read(maximum + 1)
        after = os.fstat(stream.fileno())
    identity = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_ctime_ns)
    _need(len(raw) == before.st_size and len(raw) <= maximum
          and identity(before) == identity(after) == identity(path.lstat()), "owned file changed during read")
    return raw


def _shared_state_path():
    # Deliberately ignore optional scheduler environment overrides. A different
    # pool cannot stand in for this experiment's original shared authority.
    return Path("/tmp") / ("ipfs-datasets-resource-scheduler-" + str(os.getuid()) + ".json")


def _lease_check(lease):
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceLease
    _need(type(lease) is ResourceLease, "original native datasets ResourceLease required")
    _need(lease._scheduler.state_path == _shared_state_path()
          and lease._scheduler.config.proof_safety_enabled is True
          and lease._scheduler.config.proof_recovery_enabled is False,
          "original shared proof-safe resource pool required")
    _need(lease.owner_pid == os.getpid() and not lease.released and not lease.cancelled,
          "original resource lease is cancelled, released or owned by another process")


def _request(request):
    _need(type(request) is dict and set(request) == REQUEST_FIELDS and request.get("schema") == REQUEST_SCHEMA,
          "closed generic complete-context worker request required")
    for key in ("request_id", "session_id", "context_message_id"):
        _text(request[key], key, 128, True)
    _need(type(request["delivery_mode"]) is str and request["delivery_mode"] in {
        "adaptive", "expanded", "packed", "decode_before_model"}, "closed delivery mode required")
    _text(request["original_rendered"], "complete original context", MAX_TEXT_BYTES, True)
    _text(request["packed_wire"], "complete packed wire", MAX_TEXT_BYTES, True)
    _need(type(request["max_input_tokens"]) is int and 1 <= request["max_input_tokens"] <= 100_000,
          "bounded exact input token ceiling required")
    _need(type(request["tokenizer_descriptor"]) is dict, "exact offline tokenizer descriptor required")
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    _need(type(request["expected_head"]) is dict and
          CodebaseHead.from_dict(request["expected_head"]).to_dict() == request["expected_head"],
          "complete exact typed current head required")
    messages = request["messages"]
    _need(type(messages) is list and 1 <= len(messages) <= 32, "bounded complete messages required")
    identities = set()
    for message in messages:
        _need(type(message) is dict and set(message) == {"message_id", "role", "content"},
              "closed complete message row required")
        _text(message["message_id"], "message identity", 128, True)
        _need(message["message_id"] not in identities, "duplicate message identity")
        identities.add(message["message_id"])
        _need(type(message["role"]) is str and message["role"] in {
            "system", "developer", "user", "assistant", "tool"}, "explicit message role required")
        _text(message["content"], "complete message content")
    _need(request["context_message_id"] in identities, "required context message is absent")
    nominated = next(row for row in messages if row["message_id"] == request["context_message_id"])
    _need(nominated["content"] == request["original_rendered"], "nominated context is not the exact original")
    history = request["history_required_ids"]
    _need(type(history) is list and all(type(name) is str for name in history)
          and len(history) == len(set(history)) and set(history) <= identities,
          "complete required historical message inventory required")
    previous = request["previous_message_manifest"]
    _need(type(previous) is list and len(previous) <= 32, "bounded previous message manifest required")
    previous_ids = set()
    for row in previous:
        _need(type(row) is dict and set(row) == {"message_id", "role", "content_sha256"},
              "closed previous message provenance required")
        _need(type(row["message_id"]) is str and row["message_id"] not in previous_ids,
              "unique previous message identity required")
        previous_ids.add(row["message_id"])
        _need(type(row["content_sha256"]) is str and len(row["content_sha256"]) == 64
              and all(char in "0123456789abcdef" for char in row["content_sha256"]),
              "exact previous message SHA required")
        current = next((message for message in messages if message["message_id"] == row["message_id"]), None)
        _need(current is not None and current["role"] == row["role"]
              and (row["message_id"] == request["context_message_id"]
                   or _sha(current["content"].encode()) == row["content_sha256"]),
              "historical message was omitted or rewritten")
    raw = _wire(request)
    _need(len(raw) <= MAX_REQUEST_BYTES, "complete request exceeds child parser byte bound")
    return raw


def _selected_payload(observation, request, output_dir):
    from copy import deepcopy
    import token_cost_review as ledger
    source = ROOT.parent / "terminal-source-capsules-20261014-01" / "token_cost_review.py"
    _need(Path(ledger.__file__).resolve() == source and _sha(_read(source, 65_536)) ==
          "ea806dbaa99d1c1ee241c6acb0fa0097f2de172f4921bf10fc16e0b8fb020041",
          "exact retained complete-message offline ledger required")
    tokenizer, descriptor = ledger.load_tokenizer(request["tokenizer_descriptor"])
    selection = observation["selection"]
    _need(type(selection) is dict and selection.get("schema") == "terminal-complete-message-adaptive-delivery@1",
          "typed complete-message selection report required")
    selected = selection.get("selected_messages")
    _need(type(selected) is list and len(selected) == len(request["messages"]),
          "selected complete message inventory differs")
    position = next(index for index, row in enumerate(request["messages"])
                    if row["message_id"] == request["context_message_id"])
    form = selection.get("selected_form")
    _need(form in {"expanded", "packed"}, "closed selected model representation required")
    expected = deepcopy(request["messages"])
    if form == "packed":
        expected[position]["content"] = request["packed_wire"]
    _need(selected == expected, "selected input omits or rewrites non-nominated message bytes")
    _need(selection.get("context_message_id") == request["context_message_id"]
          and selection.get("context_message_index") == position,
          "selected context identity/index differs")
    expanded_payload = ledger.serialize_messages(request["messages"])["payload"]
    packed = deepcopy(request["messages"])
    packed[position]["content"] = request["packed_wire"]
    packed_payload = ledger.serialize_messages(packed)["payload"]
    expanded_tokens, packed_tokens = len(tokenizer.encode(expanded_payload)), len(tokenizer.encode(packed_payload))
    mode = request["delivery_mode"]
    expected_form = ("packed" if packed_tokens < expanded_tokens else "expanded") if mode == "adaptive" else (
        "expanded" if mode == "decode_before_model" else mode)
    _need(form == expected_form, "complete-message delivery mode selection differs")
    for name, payload, tokens in [("expanded_full_message_cost", expanded_payload, expanded_tokens),
                                  ("packed_full_message_cost", packed_payload, packed_tokens)]:
        measured = selection.get(name)
        _need(type(measured) is dict and measured.get("serialized_payload") == payload
              and measured.get("payload_sha256") == _sha(payload.encode())
              and measured.get("payload_bytes") == len(payload.encode())
              and type(measured.get("input_tokens")) is int and measured["input_tokens"] == tokens,
              "counterfactual full-message BPE/bytes differ")
    payload = packed_payload if form == "packed" else expanded_payload
    tokens = packed_tokens if form == "packed" else expanded_tokens
    _need(selection.get("serialized_payload") == payload and selection.get("payload_sha256") == _sha(payload.encode())
          and selection.get("payload_bytes") == len(payload.encode())
          and type(selection.get("input_tokens")) is int and selection["input_tokens"] == tokens
          and selection.get("max_input_tokens") == request["max_input_tokens"]
          and tokens <= request["max_input_tokens"], "actual selected full input differs or exceeds budget")
    manifest = [{"message_id": row["message_id"], "role": row["role"],
                 "content_sha256": _sha(row["content"].encode())} for row in expected]
    _need(observation["selected_message_manifest"] == manifest, "selected actual message provenance differs")
    _need(selection.get("tokenizer") == descriptor and selection.get("provider_usage") is None
          and type(selection.get("provider_invocations")) is int and selection["provider_invocations"] == 0,
          "selection promotes unknown provider usage")
    consumer = observation["consumer"]
    _need(type(consumer) is dict and set(consumer) == CONSUMER_FIELDS
          and consumer.get("schema") == "terminal-native-router-local-consumer-capture@1",
          "closed native-router local consumer report required")
    _need(consumer["provider"] == "experimental-local-capture" and consumer["model"] == "context-capture-v1"
          and type(consumer["consumer_calls"]) is int and consumer["consumer_calls"] == 1
          and consumer["planning_renderer_identity_verified"] is True and consumer["native_router_invoked"] is True
          and consumer["ack"] == "TERMINAL_CONTEXT_CAPTURE_ACK_V1", "distinct actual local consumer identity required")
    _need(consumer["input_sha256"] == _sha(payload.encode()) and consumer["input_bytes"] == len(payload.encode())
          and type(consumer["input_local_tokens"]) is int and consumer["input_local_tokens"] == tokens
          and consumer["tokenizer_descriptor_sha256"] == _sha(_wire(descriptor)),
          "actual router-consumer bytes/BPE differ from selected full input")
    _need(consumer["provider_usage"] is None and consumer["claims"] == CONSUMER_CLAIMS,
          "local capture cannot promote provider, supervisor or proof authority")
    store = consumer["allocation_store"]
    _need(type(store) is dict and store.get("path") == str(output_dir / "router-allocation.duckdb")
          and store.get("profile") == "fresh-owned-empty-native-allocation-schema"
          and all(type(store.get(key)) is int and store[key] == 0 for key in (
              "slots_before", "slots_after", "mutable_rows_before", "mutable_rows_after")),
          "local consumer allocation store scope or occupancy differs")


def _observation(raw, request, request_raw, output_dir, expected_selection=None, expected_manifest=None):
    try:
        observation = json.loads(raw)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise WorkerCaptureError("one canonical child observation required") from error
    _need(type(observation) is dict and set(observation) == OBSERVATION_FIELDS
          and observation.get("schema") == OBSERVATION_SCHEMA and _wire(observation) == raw,
          "closed canonical child observation required")
    for key in ("request_id", "session_id", "expected_head"):
        _need(observation[key] == request[key], "child observation has another request/session/head")
    _need(observation["request_sha256"] == _sha(request_raw), "child observed another complete request")
    _need(all(observation[key] is False for key in FALSE) and observation["provider_usage"] is None
          and type(observation["actual_external_provider_invocations"]) is int
          and observation["actual_external_provider_invocations"] == 0,
          "offline observation cannot promote provider or execution authority")
    _selected_payload(observation, request, output_dir)
    if expected_selection is not None:
        _need(observation["selection"] == expected_selection
              and observation["selected_message_manifest"] == expected_manifest,
              "child selection differs from genuine prelaunch complete-context validation")
    return observation


def launch_capture(*, request: dict, repository: Path, lease, output_dir: Path,
                   timeout_seconds=30) -> dict:
    """Perform one admitted native process launch; return unpromoted local data.

    Current-source entry/exit observations belong to the caller. This function
    never treats serialized head data as a live catalog or dispatch authority.
    """
    _need(type(timeout_seconds) in {int, float} and math.isfinite(timeout_seconds)
          and 0 < timeout_seconds <= 60, "bounded finite worker deadline required")
    request_raw = _request(request)
    _lease_check(lease)
    repository, output_dir = Path(repository), Path(output_dir)
    _need(repository.is_absolute() and repository.resolve(strict=True) == repository and repository.is_dir(),
          "canonical existing source repository required")
    _need(output_dir.is_absolute() and output_dir.resolve() == output_dir and ROOT in output_dir.parents
          and output_dir != repository and repository not in output_dir.parents and not output_dir.exists(),
          "exclusive new owned output outside source repository required")
    child_raw = _read(CHILD, 128_000)
    import context_worker
    _need(Path(context_worker.__file__).resolve() == CHILD, "exact owned worker preflight module required")
    expected_selection, expected_manifest = context_worker.prepare_request(request)
    _need(expected_manifest[:len(request["previous_message_manifest"])] == request["previous_message_manifest"],
          "previously delivered history must remain an ordered prefix")
    from ipfs_accelerate_py.agent_supervisor.todo_daemon import supervisor_runtime as native
    _need(Path(native.__file__).resolve() == RUNTIME_SOURCE, "exact pinned native supervisor launcher required")
    native_raw = _read(RUNTIME_SOURCE, 256_000)
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceLane
    command = [sys.executable, "-I", "-B", str(CHILD)]
    birth = {}
    output_dir.mkdir(mode=0o700)
    environment = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "PYTHONUTF8": "1",
        "PYTHONDONTWRITEBYTECODE": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1", "CUDA_VISIBLE_DEVICES": "", "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1", "IPFS_ACCELERATE_LLM_OBSERVE": "0",
        "IPFS_ACCELERATE_LLM_ALLOCATE": "0",
        "IPFS_ACCELERATE_LLM_RESPONSE_CACHE": "0",
        "IPFS_ACCELERATE_PY_ROUTER_RESPONSE_CACHE": "0",
        "IPFS_ACCELERATE_LLM_ALLOCATION_DB": str(output_dir / "router-allocation.duckdb")}
    with (output_dir / "request.json").open("xb") as stream:
        stream.write(request_raw)
    with lease.acquire_child(lane=ResourceLane.VALIDATION, cpu_slots=1, memory_mb=256,
            child_process_slots=1, timeout=min(20, timeout_seconds),
            request_id="terminal-context-worker:" + request["request_id"]) as child_lease:
        _lease_check(child_lease)
        def cancellation():
            return lease.released or lease.cancelled or child_lease.released or child_lease.cancelled

        def started(process):
            _lease_check(lease); _lease_check(child_lease)
            identity = native.read_process_birth(process.pid)
            _need(identity is not None and identity.pid == process.pid, "actual worker birth identity unavailable")
            birth.update(pid=process.pid, start_time_ticks=identity.start_time_ticks)

        with (output_dir / "stdout.json").open("xb") as stdout, (output_dir / "stderr.log").open("xb") as stderr:
            completed = native.run_process_group_stream(command, cwd=repository,
                stdout=stdout, stderr=stderr, input_text=request_raw.decode("ascii"),
                env=environment, inherit_environment=False, timeout_seconds=timeout_seconds,
                max_timeout_seconds=timeout_seconds, progress_poll_seconds=0.05,
                cancel_requested=cancellation, on_started=started, text=False)
        _lease_check(lease); _lease_check(child_lease)
        _need(completed.returncode == 0 and bool(birth), "offline worker process failed")
        stderr_raw = _read(output_dir / "stderr.log", MAX_STDERR_BYTES, empty=True)
        _need(stderr_raw == b"", "offline worker produced unexpected stderr")
        report_raw = _read(output_dir / "stdout.json", MAX_REPORT_BYTES)
        observation = _observation(report_raw, request, request_raw, output_dir, expected_selection, expected_manifest)
    _lease_check(lease)
    _need(_read(CHILD, 128_000) == child_raw and _read(RUNTIME_SOURCE, 256_000) == native_raw,
          "child or native launcher producer changed during dispatch")
    files = [{"relative_path": name, "bytes": len(raw), "sha256": _sha(raw)} for name, raw in [
        ("request.json", request_raw), ("stdout.json", report_raw), ("stderr.log", stderr_raw)]]
    return {"schema": SCHEMA, "request_sha256": _sha(request_raw), "request_bytes": len(request_raw),
        "native_dispatch": {"module": native.__name__, "method": "run_process_group_stream",
            "path": str(RUNTIME_SOURCE), "sha256": _sha(native_raw), "actual_child_birth": birth,
            "actual_process_invoked": True, "native_shared_parent_lease_used": True,
            "native_child_lease": {"cpu_slots": 1, "memory_mb": 256, "child_process_slots": 1},
            "inherited_environment": False, "shell": False},
        "observation": observation, "output_artifacts": files,
        "current_head_observation_owned_by_caller": True, "provider_usage": None,
        "actual_external_provider_invocations": 0, **FALSE}
