"""Owner-memory planning permits over genuine native task-claim fences.

The permit authorizes one local observation worker only. Its public report is
historical evidence, never a transferable capability, coding admission or proof.
Source-owner entry/exit observations remain separate responsibilities of root.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import secrets
import stat
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parent
SCHEMA = "terminal-owner-planning-observation-permit-evidence@1"
BINDING_SCHEMA = "terminal-planning-request-binding@1"
_KEY = object()
CLAIMS = {name: False for name in (
    "serialized_capability", "native_full_supervisor_invoked", "typed_daemon_dispatch_admitted",
    "original_task_coverage", "original_requirements_resolved", "original_coding_task_admitted",
    "proof_authority", "execution_authority", "completion_authority", "task_satisfaction",
    "model_interpretation_equivalence_proved", "durable_permit_resume_supported",
)}


class PlanningPermitError(ValueError):
    """Original owner, scope, request, process or native fence differs."""


def _need(condition, message):
    if not condition:
        raise PlanningPermitError(message)


def _wire(value):
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                         allow_nan=False).encode("ascii")
    except (TypeError, ValueError, UnicodeError, RecursionError) as error:
        raise PlanningPermitError("bounded exact finite JSON required") from error
    _need(len(raw) <= 2_000_000, "permit binding exceeds byte bound")
    return raw


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _module(name):
    import importlib
    module = importlib.import_module(name)
    _need(Path(module.__file__).resolve(strict=True) == ROOT / (name + ".py"),
          "exact owned planning module required")
    return module


def planning_request_binding(request: dict) -> dict:
    """Replay a body-free binding without a job, coordinator or live permit."""
    worker = _module("worker_capture")
    raw = worker._request(request)
    selection, manifest = _module("context_worker").prepare_request(request)
    core = json.loads(request["original_rendered"])
    instruction = json.loads(core["goal"]["instruction_json"])["instruction"].encode("utf-8")
    sources = []
    for row in core["evidence"]:
        if row["kind"] == "source-view":
            view = json.loads(row["summary"])
            sources.append({key: view[key] for key in (
                "path", "source_cid", "source_sha256", "full_source_bytes")})
    return {"schema": BINDING_SCHEMA, "request_sha256": _sha(raw), "request_bytes": len(raw),
        "request_id": request["request_id"], "session_id": request["session_id"],
        "original_task_id": core["objective_id"],
        "native_head": json.loads(_wire(request["expected_head"])),
        "original_rendered_sha256": _sha(request["original_rendered"].encode("utf-8")),
        "original_rendered_bytes": len(request["original_rendered"].encode("utf-8")),
        "packed_wire_sha256": _sha(request["packed_wire"].encode("utf-8")),
        "full_instruction_sha256": _sha(instruction), "full_instruction_bytes": len(instruction),
        "source_bindings": sorted(sources, key=lambda row: row["path"]),
        "unresolved_residual_spans_utf8": core["acceptance"]["requirement_residual_spans"],
        "tokenizer_descriptor_sha256": _sha(_wire(request["tokenizer_descriptor"])),
        "delivery_mode": request["delivery_mode"], "selected_form": selection["selected_form"],
        "context_message_id": request["context_message_id"],
        "selected_payload_sha256": selection["payload_sha256"],
        "selected_payload_bytes": selection["payload_bytes"], "selected_input_tokens": selection["input_tokens"],
        "max_input_tokens": request["max_input_tokens"], "selected_message_manifest_sha256": _sha(_wire(manifest)),
        "original_task_coverage": False, "original_requirements_resolved": False}


def _job_check(job, job_binding, request_binding):
    module = _module("planning_job")
    verified = module.verify_planning_job(job)
    _need(type(job_binding) is dict and _wire(verified) == _wire(job_binding),
          "exact original live native planning job required")
    _need(verified.get("schema") == "terminal-owned-planning-job-binding@1"
          and all(verified.get(key) is False for key in (
              "original_task_coverage", "original_requirements_resolved", "completion_authority")),
          "planning observation job cannot cover original coding obligations")
    inputs = job.input_binding
    _need(type(inputs) is dict and inputs.get("planning_request_binding") == request_binding,
          "signed native job does not authorize this exact complete request")
    _need(verified.get("input_binding_sha256") == _sha(_wire(inputs))
          and verified.get("native_head") == request_binding["native_head"],
          "signed native input/head scope differs")
    _need(inputs.get("native_head") == request_binding["native_head"]
          and type(inputs.get("max_input_tokens")) is int
          and inputs["max_input_tokens"] == request_binding["max_input_tokens"],
          "signed full-input head or input-token budget differs")
    instructions = inputs.get("instructions", [])
    candidates = [row for row in instructions if row.get("task_id") == request_binding["original_task_id"]]
    _need(len(candidates) == 1 and candidates[0].get("instruction_sha256") == request_binding["full_instruction_sha256"]
          and _sha(candidates[0]["instruction_text"].encode("utf-8")) == request_binding["full_instruction_sha256"]
          and len(candidates[0]["instruction_text"].encode("utf-8")) == request_binding["full_instruction_bytes"],
          "signed full original instruction differs from actual request")
    residuals = inputs.get("original_requirement_residuals")
    _need(type(residuals) is list and len(residuals) == len(instructions),
          "complete original instruction residual inventory required")
    for instruction in instructions:
        matches = [row for row in residuals if type(row) is dict and row.get("task_id") == instruction["task_id"]]
        length = len(instruction["instruction_text"].encode("utf-8"))
        _need(len(matches) == 1 and matches[0].get("instruction_sha256") == instruction["instruction_sha256"]
              and matches[0].get("unresolved_spans") == [[0, length]]
              and matches[0].get("span_unit") == "utf8_bytes"
              and matches[0].get("full_instruction_retained") is True
              and matches[0].get("all_requirements_unresolved") is True
              and matches[0].get("full_task_coverage_qualified") is False,
              "signed full instruction residual was omitted or weakened")
    sources = inputs.get("source_records", [])
    from ipfs_datasets_py.logic.software_contracts.content import cid_for_bytes
    for source in request_binding["source_bindings"]:
        matches = [row for row in sources if row.get("path") == source["path"]]
        _need(len(matches) == 1, "requested source absent from signed complete original inputs")
        raw = matches[0]["source_text"].encode("utf-8")
        _need(matches[0].get("sha256") == source["source_sha256"] == _sha(raw)
              and len(raw) == source["full_source_bytes"] and cid_for_bytes(raw) == source["source_cid"],
              "signed original source bytes/CID differ from actual request")
    _need(inputs.get("original_benchmark_task_admitted") is False
          and inputs.get("original_task_satisfaction") is False,
          "original coding admission or satisfaction cannot be promoted")
    return verified


def _claim_material(claim):
    return {name: getattr(claim, name) for name in (
        "task_cid", "claim_id", "attempt_id", "attempt_number", "owner_session_id",
        "lease_id", "fencing_token", "fence_epoch", "claimed_at_ms", "expires_at_ms", "worktree_id")}


def _coordinator_check(coordinator, claim, job_binding):
    from ipfs_accelerate_py.agent_supervisor.merge.database_coordination import DatabaseCoordinator, TaskClaim
    _need(type(coordinator) is DatabaseCoordinator and coordinator.is_open and type(claim) is TaskClaim,
          "original live native coordinator and TaskClaim required")
    _need(not coordinator._require_existing_authority, "existing account authority is outside planning fixture scope")
    path = coordinator.database_path
    _need(type(path) is type(Path()) and path.is_absolute() and path.resolve(strict=True) == path,
          "canonical original owned coordinator database required")
    metadata = path.lstat()
    _need(stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1 and metadata.st_uid == os.geteuid(),
          "single-link owned native coordinator database required")
    _need(claim.task_cid == job_binding["task_cid"]
          and claim.owner_session_id == job_binding["intent_session_id"], "native claim belongs to another planning job")
    # Only the explicitly selected fresh registry is inspected; no account
    # database or private owner records are discovered/opened here.
    connection = coordinator._require()
    _need(connection.execute("SELECT COUNT(*) FROM coordination_tasks").fetchone()[0] == 1,
          "planning coordinator must contain only this explicit fixture task")
    row = connection.execute("SELECT task_id FROM coordination_tasks WHERE task_cid = ?", [claim.task_cid]).fetchone()
    _need(row is not None and row[0] == job_binding["task_key"], "native coordinator task identity differs")
    return {"path": str(path), "device": metadata.st_dev, "inode": metadata.st_ino}


def _launch_binding(*, parent_lease, request, repository, command, environment, producer_pins,
                    timeout_seconds, job, job_binding):
    _need(type(timeout_seconds) in {int, float} and math.isfinite(timeout_seconds)
          and 0 < timeout_seconds <= 60, "bounded planning worker timeout required")
    worker = _module("worker_capture")
    worker._lease_check(parent_lease)
    repository = Path(repository)
    _need(repository.is_absolute() and repository.resolve(strict=True) == repository and repository.is_dir(),
          "canonical current source repository required")
    _need(type(environment) is dict and type(environment.get("IPFS_ACCELERATE_LLM_ALLOCATION_DB")) is str,
          "explicit owned local-capture environment required")
    output = Path(environment["IPFS_ACCELERATE_LLM_ALLOCATION_DB"]).parent
    _need(output.is_absolute() and ROOT in output.parents and output.resolve() == output
          and output != repository and repository not in output.parents, "owned capture output scope differs")
    actual = worker.capture_launch_binding(output)
    supplied = {"command": command, "environment": environment, "producer_pins": producer_pins}
    _need(_wire(supplied) == _wire(actual), "exact native command, environment and producer pins required")
    request_binding = planning_request_binding(request)
    _job_check(job, job_binding, request_binding)
    return {"request": request_binding, "repository": str(repository), "launch": supplied,
        "job_binding_sha256": _sha(_wire(job_binding)), "timeout_seconds": timeout_seconds,
        "local_provider": "experimental-local-capture", "local_model": "context-capture-v1"}


def _owner_birth():
    from ipfs_accelerate_py.agent_supervisor.merge.worktree_lifecycle import read_process_birth
    birth = read_process_birth(os.getpid())
    _need(birth is not None, "actual owner process birth unavailable")
    return birth.to_dict()


class PlanningPermit:
    """One process-local, sealed, noncopyable planning-worker capability."""
    __slots__ = ("_coordinator", "_claim", "_parent", "_job", "_job_binding", "_binding", "_registry",
        "_owner", "_lock", "_phase", "_thread", "_guard", "_birth", "_ack_attempts", "_failed", "_secret", "_seal")

    def __init_subclass__(cls, **kwargs):
        raise PlanningPermitError("planning permits cannot be subclassed")

    def __init__(self, *, _key=None, coordinator=None, claim=None, parent=None, job=None,
                 job_binding=None, binding=None, registry=None):
        _need(_key is _KEY, "use the original planning permit issuer")
        self._coordinator, self._claim, self._parent, self._job = coordinator, claim, parent, job
        self._job_binding, self._binding, self._registry = _wire(job_binding), _wire(binding), _wire(registry)
        self._owner, self._lock = _owner_birth(), threading.RLock()
        self._phase, self._thread, self._guard, self._birth = "issued", None, None, None
        self._ack_attempts, self._failed = 0, False
        self._secret = secrets.token_bytes(32)
        self._reseal()

    def _state(self):
        return _wire({"object": id(self), "coordinator": id(self._coordinator), "claim": id(self._claim),
            "parent": id(self._parent), "job": id(self._job), "job_binding": self._job_binding.decode(),
            "binding": self._binding.decode(), "registry": self._registry.decode(), "owner": self._owner,
            "lock": id(self._lock), "phase": self._phase, "thread": self._thread,
            "guard": id(self._guard), "birth": self._birth, "ack_attempts": self._ack_attempts,
            "failed": self._failed, "claim_binding": _claim_material(self._claim)})

    def _reseal(self):
        self._seal = hmac.new(self._secret, self._state(), hashlib.sha256).digest()

    def _identity(self):
        _need(type(self) is PlanningPermit and _owner_birth() == self._owner,
              "original owner process and exact permit required")
        _need(hmac.compare_digest(self._seal, hmac.new(self._secret, self._state(), hashlib.sha256).digest()),
              "sealed planning permit state changed")

    def __copy__(self):
        raise PlanningPermitError("planning permit cannot be copied")

    def __deepcopy__(self, memo):
        raise PlanningPermitError("planning permit cannot be copied")

    def __reduce_ex__(self, protocol):
        raise PlanningPermitError("planning permit cannot be serialized")

    def _started(self, process):
        assert_running_planning_callback(self, self._guard)
        with self._lock:
            self._ack_attempts += 1
            self._reseal()
            try:
                _need(self._ack_attempts == 1 and self._birth is None and type(process) is subprocess.Popen,
                      "one original native Popen acknowledgement required")
                binding = json.loads(self._binding)
                from ipfs_accelerate_py.agent_supervisor.merge.worktree_lifecycle import read_process_birth
                birth = read_process_birth(process.pid)
                _need(birth is not None and birth.parent_pid == os.getpid()
                      and os.stat(f"/proc/{process.pid}").st_uid == os.geteuid()
                      and os.getpgid(process.pid) == process.pid, "foreign worker process ownership refused")
                with Path(f"/proc/{process.pid}/cmdline").open("rb") as stream:
                    raw = stream.read(8193)
                _need(len(raw) <= 8192 and raw.rstrip(b"\0").split(b"\0") == [part.encode() for part in binding["launch"]["command"]]
                      and list(process.args) == binding["launch"]["command"], "actual worker command differs")
                _need(Path(os.readlink(f"/proc/{process.pid}/cwd")) == Path(binding["repository"]),
                      "actual worker source workspace differs")
                _need(time.time_ns() // 1_000_000 < self._claim.expires_at_ms, "planning permit expired before worker ACK")
                self._birth = {**birth.to_dict(), "uid": os.geteuid()}
                self._reseal()
            except BaseException:
                self._failed = True
                self._reseal()
                raise


def issue_planning_permit(*, coordinator, claim, parent_lease, job, job_binding, request,
                         repository, command, environment, producer_pins, timeout_seconds=30):
    """Bind one original native job/claim to one complete local capture request."""
    binding = _launch_binding(parent_lease=parent_lease, request=request, repository=repository,
        command=command, environment=environment, producer_pins=producer_pins,
        timeout_seconds=timeout_seconds, job=job, job_binding=job_binding)
    registry = _coordinator_check(coordinator, claim, job_binding)
    coordinator.protect_task_claim(claim, expected_task_cid=job_binding["task_cid"],
        expected_owner_session_id=job_binding["intent_session_id"])
    return PlanningPermit(_key=_KEY, coordinator=coordinator, claim=claim, parent=parent_lease,
        job=job, job_binding=job_binding, binding=binding, registry=registry)


def assert_running_planning_callback(permit, guard):
    """Require the original guard while its real native fence callback is live."""
    _need(type(permit) is PlanningPermit, "original planning permit required")
    with permit._lock:
        permit._identity()
        _need(permit._phase == "running" and permit._thread == threading.get_ident()
              and guard is permit._guard and guard is not None,
              "original active native planning callback required")
        _module("worker_capture")._lease_check(permit._parent)


def execute_planning_capture(permit, *, parent_lease, request, repository, command, environment,
                             producer_pins, timeout_seconds=30, launch):
    """Burn once before dispatch; preserve native coordinator pre/post fencing."""
    _need(type(permit) is PlanningPermit, "original planning permit required")
    with permit._lock:
        permit._identity()
        _need(permit._phase == "issued", "planning permit already consumed or burned")
        permit._phase = "burned"
        permit._reseal()
    binding = _launch_binding(parent_lease=parent_lease, request=request, repository=repository,
        command=command, environment=environment, producer_pins=producer_pins,
        timeout_seconds=timeout_seconds, job=permit._job, job_binding=json.loads(permit._job_binding))
    _need(parent_lease is permit._parent and _wire(binding) == permit._binding,
          "planning permit belongs to different request, resource owner or launch")
    registry = _coordinator_check(permit._coordinator, permit._claim, json.loads(permit._job_binding))
    _need(_wire(registry) == permit._registry and callable(launch), "original native coordinator or callback differs")

    def protected(_native_lease):
        with permit._lock:
            permit._identity()
            permit._phase, permit._thread = "running", threading.get_ident()
            permit._guard = permit._started
            permit._reseal()
        try:
            result = launch(on_started=permit._guard)
            with permit._lock:
                permit._identity()
                _need(permit._birth is not None and permit._ack_attempts == 1 and not permit._failed,
                      "actual native worker birth ACK absent, repeated or refused")
            return result
        finally:
            with permit._lock:
                permit._phase, permit._thread, permit._guard = "burned", None, None
                permit._reseal()

    capture = permit._coordinator.execute_with_task_claim_fence(permit._claim, protected,
        minimum_remaining_ms=math.ceil((float(timeout_seconds) + 25) * 1000))
    after = _launch_binding(parent_lease=parent_lease, request=request, repository=repository,
        command=command, environment=environment, producer_pins=producer_pins,
        timeout_seconds=timeout_seconds, job=permit._job, job_binding=json.loads(permit._job_binding))
    _need(_wire(after) == permit._binding, "planning job or launch inputs changed during capture")
    with permit._lock:
        permit._identity()
        permit._phase = "completed"
        permit._reseal()
    public = {"schema": SCHEMA, "scope": "planning-observation-only", "worker_mode": "localcapture",
        "native_coordinator_claim_fenced_before_after": True, "single_use_owner_permit_consumed": True,
        "worker_birth_acknowledged_before_stdin": True, "native_job_binding": json.loads(permit._job_binding),
        "request_binding": binding["request"], "claim_binding_sha256": _sha(_wire(_claim_material(permit._claim))),
        "launch_binding_sha256": _sha(_wire(binding["launch"])), "actual_worker_birth": json.loads(_wire(permit._birth)),
        "provider_usage": None, "actual_external_provider_invocations": 0, **CLAIMS}
    return {"capture": capture, "planning_admission": public}
