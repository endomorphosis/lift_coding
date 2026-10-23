"""Authored native signed jobs, task claims and fixture-only resource samples."""
from contextlib import contextmanager
from copy import copy, deepcopy
from dataclasses import replace
import json
import os
from pathlib import Path
import pickle
import subprocess
import sys

import pytest

import planning_permit as subject
import worker_capture as worker
from planning_job import create_owned_planning_job
from test_admitted_worker import authored_request, authored_lease, owned_output
from ipfs_accelerate_py.agent_supervisor.merge.database_coordination import (
    DatabaseCoordinator, DatabaseCoordinationError,
)


def signed_inputs(request):
    core = json.loads(request["original_rendered"])
    text = json.loads(core["goal"]["instruction_json"])["instruction"]
    task = core["objective_id"]
    sources = []
    for row in core["evidence"]:
        if row["kind"] == "source-view":
            view = json.loads(row["summary"])
            sources.append({"path": view["path"], "sha256": view["source_sha256"], "source_text": view["view_text"]})
    return {"native_head": request["expected_head"], "max_input_tokens": request["max_input_tokens"],
        "instructions": [{"task_id": task, "instruction_text": text, "instruction_sha256": subject._sha(text.encode())}],
        "source_records": sources, "planning_request_binding": subject.planning_request_binding(request),
        "original_requirement_residuals": [{"task_id": task, "instruction_sha256": subject._sha(text.encode()),
            "unresolved_spans": [[0, len(text.encode())]], "span_unit": "utf8_bytes", "full_instruction_retained": True,
            "all_requirements_unresolved": True, "full_task_coverage_qualified": False}],
        "original_benchmark_task_admitted": False, "original_task_satisfaction": False}


@contextmanager
def native_case(request, lease, output, tmp_path, *, mutate=None):
    inputs = signed_inputs(request)
    if mutate is not None:
        mutate(inputs)
    source = output.parent / "authored-source"
    source.mkdir()
    for row in signed_inputs(request)["source_records"]:
        path = source / row["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(row["source_text"])
    with create_owned_planning_job(job_repository=output.parent / "job", private_root=tmp_path / "private-job",
            public_output=output.parent / "public-job", input_binding=inputs, task_key="authored-planning-permit") as job:
        with DatabaseCoordinator(tmp_path / "authored-coordinator.duckdb") as coordinator:
            coordinator.register_task(task_cid=job.task_cid, task_id=job.job_binding["task_key"],
                worktree_id=str(source), body=job.job_binding)
            claim = coordinator.claim_task(task_cid=job.task_cid,
                owner_session_id=job.job_binding["intent_session_id"], worktree_id=str(source), lease_ms=120000,
                body=job.job_binding)
            launch_binding = worker.capture_launch_binding(output)
            arguments = dict(coordinator=coordinator, claim=claim, parent_lease=lease, job=job,
                job_binding=job.job_binding, request=request, repository=source, **launch_binding)
            yield arguments, output


def execute(permit, arguments, launch, **changes):
    actual = {key: value for key, value in arguments.items() if key not in {"coordinator", "claim", "job", "job_binding"}}
    actual.update(changes)
    return subject.execute_planning_capture(permit, **actual, launch=launch)


def actual_capture(permit, arguments, output):
    return worker.launch_admitted_capture(request=arguments["request"], repository=arguments["repository"],
        lease=arguments["parent_lease"], output_dir=output, permit=permit)


def test_public_request_binding_replays_full_bounded_content_without_authority(authored_request):
    result = subject.planning_request_binding(authored_request)
    assert result == subject.planning_request_binding(deepcopy(authored_request))
    assert result["request_sha256"] == subject._sha(worker._request(authored_request))
    assert result["native_head"] == authored_request["expected_head"]
    assert result["selected_input_tokens"] <= result["max_input_tokens"]
    assert result["unresolved_residual_spans_utf8"] == [[0, result["full_instruction_bytes"]]]
    assert result["original_task_coverage"] is False
    assert "source_text" not in subject._wire(result).decode()


def test_genuine_native_fenced_capture_and_historical_report_cannot_replay(
        authored_request, authored_lease, owned_output, tmp_path):
    with native_case(authored_request, authored_lease, owned_output, tmp_path) as (arguments, output):
        permit = subject.issue_planning_permit(**arguments)
        result = actual_capture(permit, arguments, output)
        proof = result["planning_admission"]
        assert proof["native_coordinator_claim_fenced_before_after"] is True
        assert proof["single_use_owner_permit_consumed"] is True
        assert proof["worker_birth_acknowledged_before_stdin"] is True
        assert proof["actual_worker_birth"]["pid"] == result["native_dispatch"]["actual_child_birth"]["pid"]
        assert proof["request_binding"] == subject.planning_request_binding(authored_request)
        assert all(proof[key] is False for key in subject.CLAIMS)
        assert proof["provider_usage"] is None
        assert "lease_key" not in subject._wire(proof).decode()
        assert arguments["job"].intent.get_task(arguments["job"].task_cid)["status"] not in {"done", "completed"}
        with pytest.raises(subject.PlanningPermitError, match="consumed"):
            execute(permit, arguments, lambda **unused: None)
        with pytest.raises(subject.PlanningPermitError, match="original"):
            execute(proof, arguments, lambda **unused: None)


def test_permit_construction_copy_pickle_and_subclass_refused(authored_request, authored_lease, owned_output, tmp_path):
    with pytest.raises(subject.PlanningPermitError): subject.PlanningPermit()
    with pytest.raises(subject.PlanningPermitError):
        type("AuthoredPermitSubclass", (subject.PlanningPermit,), {})
    with native_case(authored_request, authored_lease, owned_output, tmp_path) as (arguments, _):
        permit = subject.issue_planning_permit(**arguments)
        for operation in (copy, deepcopy, pickle.dumps):
            with pytest.raises(subject.PlanningPermitError): operation(permit)
        with pytest.raises(subject.PlanningPermitError): subject.assert_running_planning_callback(permit, lambda process: None)


@pytest.mark.parametrize("damage", ["request", "head", "budget", "command", "environment", "producer", "repository", "timeout"])
def test_changed_scope_burns_permit_before_callback(authored_request, authored_lease, owned_output, tmp_path, damage):
    with native_case(authored_request, authored_lease, owned_output, tmp_path) as (arguments, output):
        permit = subject.issue_planning_permit(**arguments)
        altered = {}
        if damage in {"request", "head", "budget"}:
            changed = deepcopy(arguments["request"])
            if damage == "request": changed["request_id"] += "-foreign"
            elif damage == "head": changed["expected_head"]["generation"] += 1
            else: changed["max_input_tokens"] += 1
            altered["request"] = changed
        elif damage == "command": altered["command"] = arguments["command"] + ["--foreign"]
        elif damage == "environment": altered["environment"] = {**arguments["environment"], "PYTHONPATH": "/foreign"}
        elif damage == "producer":
            pins = deepcopy(arguments["producer_pins"]); pins[0]["sha256"] = "0" * 64
            altered["producer_pins"] = pins
        elif damage == "repository":
            other = tmp_path / "foreign-source"; other.mkdir(); altered["repository"] = other
        else: altered["timeout_seconds"] = 31
        entered = []
        with pytest.raises(ValueError): execute(permit, arguments, lambda **unused: entered.append(True), **altered)
        assert entered == [] and not output.exists()
        with pytest.raises(subject.PlanningPermitError, match="consumed"):
            execute(permit, arguments, lambda **unused: None)


@pytest.mark.parametrize("damage", ["instruction", "source", "source_path", "residual", "budget", "coverage"])
def test_genuine_signed_job_with_wrong_original_content_cannot_authorize_context(
        authored_request, authored_lease, owned_output, tmp_path, damage):
    def alter(inputs):
        if damage == "instruction":
            row = inputs["instructions"][0]; row["instruction_text"] += "changed"
            row["instruction_sha256"] = subject._sha(row["instruction_text"].encode())
            residual = inputs["original_requirement_residuals"][0]
            residual["instruction_sha256"] = row["instruction_sha256"]
            residual["unresolved_spans"] = [[0, len(row["instruction_text"].encode())]]
        elif damage == "source":
            row = inputs["source_records"][0]; row["source_text"] += "\n# different original source\n"
            row["sha256"] = subject._sha(row["source_text"].encode())
        elif damage == "source_path": inputs["source_records"][0]["path"] = "foreign/source.py"
        elif damage == "residual": inputs["original_requirement_residuals"][0]["unresolved_spans"][0][1] -= 1
        elif damage == "budget": inputs["max_input_tokens"] += 1
        else: inputs["original_benchmark_task_admitted"] = True
    with native_case(authored_request, authored_lease, owned_output, tmp_path, mutate=alter) as (arguments, output):
        with pytest.raises(subject.PlanningPermitError): subject.issue_planning_permit(**arguments)
        assert not output.exists()


def test_foreign_native_claim_tuple_and_copied_job_refused(authored_request, authored_lease, owned_output, tmp_path):
    with native_case(authored_request, authored_lease, owned_output, tmp_path) as (arguments, _):
        foreign = replace(arguments["claim"], attempt_id="authored-foreign-attempt")
        with pytest.raises(DatabaseCoordinationError): subject.issue_planning_permit(**{**arguments, "claim": foreign})
        with pytest.raises(ValueError): subject.issue_planning_permit(**{**arguments, "job": copy(arguments["job"])})


@pytest.mark.parametrize("fault", ["released", "expired", "short_ack_budget"])
def test_actual_native_claim_refusal_burns_before_external_callback(
        authored_request, authored_lease, owned_output, tmp_path, fault):
    with native_case(authored_request, authored_lease, owned_output, tmp_path) as (arguments, output):
        permit = subject.issue_planning_permit(**arguments)
        coordinator, claim = arguments["coordinator"], arguments["claim"]
        if fault == "released": coordinator.release(claim.as_fenced_lease())
        else:
            # The native clock seam is modified only in this authored fixture.
            coordinator._clock_ms = lambda: claim.expires_at_ms + 1 if fault == "expired" else claim.expires_at_ms - 1000
        entered = []
        with pytest.raises(DatabaseCoordinationError): execute(permit, arguments, lambda **unused: entered.append(True))
        assert entered == [] and not output.exists()
        with pytest.raises(subject.PlanningPermitError, match="consumed"): execute(permit, arguments, lambda **unused: None)


@pytest.mark.parametrize("fault", ["exception", "missing_ack", "coordinator_reentry"])
def test_failed_external_callback_never_restores_capability(authored_request, authored_lease, owned_output, tmp_path, fault):
    with native_case(authored_request, authored_lease, owned_output, tmp_path) as (arguments, _):
        permit = subject.issue_planning_permit(**arguments)
        def callback(*, on_started):
            subject.assert_running_planning_callback(permit, on_started)
            if fault == "exception": raise RuntimeError("authored callback failure")
            if fault == "coordinator_reentry": arguments["coordinator"].protect_task_claim(arguments["claim"])
            return {"authored_unacknowledged": True}
        with pytest.raises((ValueError, RuntimeError, DatabaseCoordinationError)): execute(permit, arguments, callback)
        with pytest.raises(subject.PlanningPermitError, match="consumed"): execute(permit, arguments, callback)


def test_foreign_actual_child_is_fenced_by_native_launcher_before_stdin(authored_request, authored_lease, owned_output, tmp_path):
    from ipfs_accelerate_py.agent_supervisor.todo_daemon import supervisor_runtime as native
    with native_case(authored_request, authored_lease, owned_output, tmp_path) as (arguments, _):
        permit = subject.issue_planning_permit(**arguments); born = []
        def callback(*, on_started):
            def started(process):
                born.append(process.pid)
                on_started(process)
            with (tmp_path / "foreign.log").open("xb") as stream:
                return native.run_process_group_stream([sys.executable, "-I", "-c", "import time; time.sleep(30)"],
                    cwd=arguments["repository"], stdout=stream, input_text="never delivered", env={},
                    inherit_environment=False, timeout_seconds=2, on_started=started)
        with pytest.raises(subject.PlanningPermitError, match="command"): execute(permit, arguments, callback)
        assert born
        with pytest.raises(ProcessLookupError): os.kill(born[0], 0)


def test_original_permit_rejects_forked_owner_before_any_authority_use(authored_request, authored_lease, owned_output, tmp_path):
    with native_case(authored_request, authored_lease, owned_output, tmp_path) as (arguments, _):
        permit = subject.issue_planning_permit(**arguments)
        reader, writer = os.pipe(); pid = os.fork()
        if pid == 0:
            os.close(reader)
            try:
                execute(permit, arguments, lambda **unused: None)
            except subject.PlanningPermitError:
                os.write(writer, b"refused")
            finally:
                os.close(writer); os._exit(0)
        os.close(writer)
        with os.fdopen(reader, "rb") as stream: assert stream.read(16) == b"refused"
        assert os.waitpid(pid, 0)[1] == 0


def test_caught_bad_second_ack_cannot_promote_first_capture(authored_request, authored_lease, owned_output, tmp_path):
    with native_case(authored_request, authored_lease, owned_output, tmp_path) as (arguments, output):
        permit = subject.issue_planning_permit(**arguments)
        binding = worker.capture_launch_binding(output)
        def callback(*, on_started):
            capture = worker._launch_capture(request=arguments["request"], repository=arguments["repository"],
                lease=arguments["parent_lease"], output_dir=output, timeout_seconds=30,
                on_started=on_started, binding=binding, permit=permit)
            with pytest.raises(subject.PlanningPermitError): on_started(object())
            return capture
        with pytest.raises(subject.PlanningPermitError, match="ACK"): execute(permit, arguments, callback)
        assert (output / "stdout.json").exists()
        with pytest.raises(subject.PlanningPermitError, match="consumed"): execute(permit, arguments, callback)
