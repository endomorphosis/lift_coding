"""Planning-only worker boundaries with authored public, nonexecuted sources.

The integration fixture uses genuine native signing/materialization/claims and
actual subprocess/router delivery. Authored resource samples remain unit-only.
"""
from copy import deepcopy
from contextlib import contextmanager
from io import BytesIO
import json
from pathlib import Path
import tempfile

import pytest

import context_worker
import router_consumer
import worker_capture as subject
from test_worker_capture import authored_request
from ipfs_datasets_py.optimizers.logic_theorem_optimizer.proof_resource_safety import ProofHostResources
from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import (
    GlobalResourceScheduler, ResourceSchedulerConfig, ResourceLane,
)


@pytest.fixture
def authored_lease(tmp_path, monkeypatch):
    scheduler = GlobalResourceScheduler(ResourceSchedulerConfig.for_proof_host(
        state_path=tmp_path / "authored-resource-state.json", auto_renew_leases=False,
        proof_resource_sampler=lambda: ProofHostResources(8, 8192, 8192)))
    monkeypatch.setattr(subject, "_shared_state_path", lambda: scheduler.state_path)
    with scheduler.acquire(ResourceLane.ORCHESTRATION, cpu_slots=1, memory_mb=768,
            child_process_slots=1, timeout=1, request_id="authored-admitted-worker-parent") as lease:
        yield lease


@pytest.fixture
def owned_output():
    with tempfile.TemporaryDirectory(prefix=".authored-admitted-worker-", dir=subject.ROOT) as directory:
        yield Path(directory) / "capture"


def test_distinct_stage_paths_and_schemas_do_not_relabel_sealed_worker():
    assert subject.ROOT.name == "terminal-planning-admission-20261015-01"
    assert subject.CHILD == subject.ROOT / "context_worker.py"
    assert Path(router_consumer.__file__).parent == subject.ROOT
    assert Path(context_worker.__file__).parent == subject.ROOT
    assert subject.REQUEST_SCHEMA == context_worker.SCHEMA == "terminal-planning-admitted-context-worker-request@1"
    assert subject.OBSERVATION_SCHEMA == context_worker.RESPONSE_SCHEMA
    assert subject.SCHEMA == "terminal-planning-admitted-context-worker-launch@1"
    assert router_consumer.SCHEMA == "terminal-planning-admitted-native-router-local-consumer-capture@1"
    assert not hasattr(subject, "launch_capture")


def test_exact_public_future_binding_creates_no_output_and_contains_no_credentials(owned_output):
    binding = subject.capture_launch_binding(owned_output)
    assert set(binding) == {"command", "environment", "producer_pins"}
    assert binding["command"][1:] == ["-I", "-B", str(subject.CHILD)]
    env = binding["environment"]
    assert env["IPFS_ACCELERATE_PY_ROUTER_RESPONSE_CACHE"] == "0"
    assert env["IPFS_ACCELERATE_LLM_OBSERVE"] == env["IPFS_ACCELERATE_LLM_ALLOCATE"] == "0"
    assert env["IPFS_ACCELERATE_LLM_ALLOCATION_DB"] == str(owned_output / "router-allocation.duckdb")
    assert not ({"HOME", "CODEX_HOME", "OPENAI_API_KEY", "AGENT_SUPERVISOR_LOCAL_PROFILE_KEY"} & set(env))
    assert binding["producer_pins"] == sorted(binding["producer_pins"], key=lambda row: row["path"])
    for pin in binding["producer_pins"]:
        assert set(pin) == {"path", "bytes", "sha256"}
        raw = subject._read(Path(pin["path"]), 2_000_000)
        assert len(raw) == pin["bytes"] and subject._sha(raw) == pin["sha256"]
        assert not pin["path"].endswith(".key")
    assert not owned_output.exists()


def test_exact_request_prepares_without_new_authority(authored_request):
    request = deepcopy(authored_request)
    assert request["schema"] == subject.REQUEST_SCHEMA
    raw = subject._request(request)
    assert context_worker.read_request(BytesIO(raw)) == request
    selected, manifest = context_worker.prepare_request(request)
    assert selected["input_tokens"] <= request["max_input_tokens"]
    assert len(manifest) == len(request["messages"])
    assert selected["source_omission_authority"] is False
    assert selected["completion_authority"] is False


def test_old_worker_request_schema_has_no_new_job_admission(authored_request):
    request = deepcopy(authored_request)
    request["schema"] = "terminal-complete-context-worker-request@1"
    with pytest.raises(subject.WorkerCaptureError, match="closed generic"):
        subject._request(request)
    with pytest.raises(context_worker.WorkerInputError, match="closed worker"):
        context_worker.prepare_request(request)


@pytest.mark.parametrize("raw", [b'{"schema":1,"schema":2}', b'{} ', b'{"x":NaN}',
    b'{"x":1.0}', b'[' * 65 + b']' * 65])
def test_owned_child_keeps_strict_bounded_request_parser(raw):
    with pytest.raises(ValueError):
        context_worker.read_request(BytesIO(raw))


def test_unadmitted_public_launch_refuses_before_outputs(authored_request, authored_lease, owned_output, tmp_path):
    source = tmp_path / "nonexecuted-source"
    source.mkdir()
    (source / "unit.py").write_text("raise RuntimeError('must never execute')\n")
    with pytest.raises(ValueError):
        subject.launch_admitted_capture(request=authored_request, repository=source,
            lease=authored_lease, output_dir=owned_output, permit=None)
    assert not owned_output.exists()


def test_private_callback_cannot_replace_original_guard(authored_request, authored_lease, owned_output, tmp_path):
    with pytest.raises(ValueError):
        subject._launch_capture(request=authored_request, repository=tmp_path,
            lease=authored_lease, output_dir=owned_output, permit=None,
            timeout_seconds=30, on_started=lambda process: None,
            binding=subject.capture_launch_binding(owned_output))
    assert not owned_output.exists()


def test_old_stage_allocation_override_cannot_enter_new_consumer(owned_output, monkeypatch):
    monkeypatch.setenv("IPFS_ACCELERATE_LLM_OBSERVE", "0")
    monkeypatch.setenv("IPFS_ACCELERATE_LLM_ALLOCATE", "0")
    monkeypatch.setenv("IPFS_ACCELERATE_PY_ROUTER_RESPONSE_CACHE", "0")
    old = subject.ROOT.parent / "terminal-context-worker-20261014-01" / "authored-no-creation" / "router-allocation.duckdb"
    monkeypatch.setenv("IPFS_ACCELERATE_LLM_ALLOCATION_DB", str(old))
    with pytest.raises(router_consumer.RouterConsumerError):
        router_consumer._owned_allocation_path()
    assert not old.parent.exists() and not owned_output.exists()


@contextmanager
def admitted_case(request, lease, output, tmp_path):
    """One genuine native signed job and live original native task claim."""
    from planning_job import create_owned_planning_job
    from planning_permit import issue_planning_permit, planning_request_binding
    from ipfs_accelerate_py.agent_supervisor.merge.database_coordination import DatabaseCoordinator
    source = output.parent / "source"
    source.mkdir()
    name = "authored-task/environment/unit.py"
    body = b"raise RuntimeError('repository source must never execute')\ndef add(a: int, b: int) -> int:\n    return a + b\n"
    path = source / name
    path.parent.mkdir(parents=True)
    path.write_bytes(body)
    instruction = "  Preserve every source and unresolved instruction. π\n\n"
    binding = {"native_head": request["expected_head"], "max_input_tokens": request["max_input_tokens"],
        "instructions": [{"task_id": "authored-task", "instruction_text": instruction,
            "instruction_sha256": subject._sha(instruction.encode())}],
        "source_records": [{"path": name, "sha256": subject._sha(body), "source_text": body.decode()}],
        "planning_request_binding": planning_request_binding(request),
        "original_requirement_residuals": [{"task_id": "authored-task",
            "instruction_sha256": subject._sha(instruction.encode()), "unresolved_spans": [[0, len(instruction.encode())]],
            "span_unit": "utf8_bytes", "full_instruction_retained": True,
            "all_requirements_unresolved": True, "full_task_coverage_qualified": False}],
        "original_benchmark_task_admitted": False, "original_task_satisfaction": False}
    private = tmp_path / "ephemeral-private-fixture"
    with create_owned_planning_job(job_repository=output.parent / "job-repository",
            private_root=private, public_output=output.parent / "public-job", input_binding=binding,
            task_key="authored-planning-capture") as job:
        with DatabaseCoordinator(output.parent / "coordination.duckdb") as coordinator:
            coordinator.register_task(task_cid=job.task_cid, task_id=job.job_binding["task_key"],
                worktree_id=str(source), body=job.job_binding)
            claim = coordinator.claim_task(task_cid=job.task_cid,
                owner_session_id=job.job_binding["intent_session_id"], worktree_id=str(source),
                lease_ms=120000, body=job.job_binding)
            invocation = subject.capture_launch_binding(output)
            permit = issue_planning_permit(job=job, job_binding=job.job_binding,
                coordinator=coordinator, claim=claim, parent_lease=lease, request=request,
                repository=source, timeout_seconds=30, **invocation)
            yield job, coordinator, claim, permit, source
    assert not private.exists()


@pytest.mark.parametrize("mode", ["expanded", "adaptive"])
def test_genuine_signed_pending_job_claim_and_native_worker_deliver_exact_local_input(
        authored_request, authored_lease, owned_output, tmp_path, mode):
    from planning_job import verify_planning_job
    request = deepcopy(authored_request)
    request["delivery_mode"] = mode
    with admitted_case(request, authored_lease, owned_output, tmp_path) as (job, coordinator, claim, permit, source):
        result = subject.launch_admitted_capture(request=request, repository=source,
            lease=authored_lease, output_dir=owned_output, permit=permit)
        assert result["schema"] == subject.SCHEMA
        assert result["native_dispatch"]["actual_process_invoked"] is True
        assert result["native_dispatch"]["actual_child_birth"]["pid"] > 0
        assert result["native_dispatch"]["actual_child_birth"]["start_time_ticks"] > 0
        consumer = result["observation"]["consumer"]
        assert consumer["schema"] == router_consumer.SCHEMA
        assert consumer["consumer_calls"] == 1 and consumer["native_router_invoked"] is True
        assert consumer["input_sha256"] == result["observation"]["selection"]["payload_sha256"]
        assert consumer["input_local_tokens"] == result["observation"]["selection"]["input_tokens"]
        assert result["provider_usage"] is None
        assert result["planning_admission"] and all(result[key] is False for key in subject.FALSE)
        acknowledged = result["planning_admission"]["actual_worker_birth"]
        for key in ("pid", "start_time_ticks"):
            assert acknowledged[key] == result["native_dispatch"]["actual_child_birth"][key]
        assert verify_planning_job(job) == job.job_binding
        assert job.intent.get_task(job.task_cid)["status"] not in {"completed", "done", "complete"}
        assert not (job.job_repository / "planning-observation.json").exists()
        assert (owned_output / "stdout.json").read_bytes() == subject._wire(result["observation"])
        assert (owned_output / "stderr.log").read_bytes() == b""
        with pytest.raises(ValueError):
            subject.launch_admitted_capture(request=request, repository=source,
                lease=authored_lease, output_dir=owned_output, permit=permit)


def test_existing_output_failure_consumes_original_permit_before_any_child(
        authored_request, authored_lease, owned_output, tmp_path):
    with admitted_case(authored_request, authored_lease, owned_output, tmp_path) as (_, _, _, permit, source):
        owned_output.mkdir()
        with pytest.raises(ValueError):
            subject.launch_admitted_capture(request=authored_request, repository=source,
                lease=authored_lease, output_dir=owned_output, permit=permit)
        assert list(owned_output.iterdir()) == []
        owned_output.rmdir()
        with pytest.raises(ValueError):
            subject.launch_admitted_capture(request=authored_request, repository=source,
                lease=authored_lease, output_dir=owned_output, permit=permit)
        assert not owned_output.exists()


def test_bad_ack_after_genuine_child_cannot_return_candidate_or_restore_permit(
        authored_request, authored_lease, owned_output, tmp_path, monkeypatch):
    from ipfs_accelerate_py.agent_supervisor.todo_daemon import supervisor_runtime as native
    original = native.run_process_group_stream
    births = []
    def corrupted_ack(*args, **kwargs):
        result = original(*args, **kwargs)
        body = json.loads(Path(kwargs["stdout"].name).read_bytes())
        births.append(body["consumer"]["consumer_calls"])
        body["consumer"]["ack"] = "UNIT_AUTHORED_INVALID_ACK"
        stream = kwargs["stdout"]
        stream.seek(0)
        stream.truncate()
        stream.write(subject._wire(body))
        stream.flush()
        return result
    with admitted_case(authored_request, authored_lease, owned_output, tmp_path) as (_, _, _, permit, source):
        monkeypatch.setattr(native, "run_process_group_stream", corrupted_ack)
        with pytest.raises(ValueError):
            subject.launch_admitted_capture(request=authored_request, repository=source,
                lease=authored_lease, output_dir=owned_output, permit=permit)
        assert births == [1]
        monkeypatch.setattr(native, "run_process_group_stream", original)
        with pytest.raises(ValueError):
            subject.launch_admitted_capture(request=authored_request, repository=source,
                lease=authored_lease, output_dir=owned_output, permit=permit)
        assert json.loads((owned_output / "stdout.json").read_bytes())["consumer"]["ack"] == "UNIT_AUTHORED_INVALID_ACK"
