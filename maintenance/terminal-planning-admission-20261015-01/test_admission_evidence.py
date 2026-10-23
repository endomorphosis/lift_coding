"""Pure corruption controls for historical evidence, never dispatch authority.

All capture/birth/job data here is explicitly synthetic. No process, provider,
native owner, signing profile or database is created by these fixtures. Their
positive results test data joins only and are never actual worker receipts.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile

import pytest

import admission_verify as subject
import context_worker
import planning_permit
import router_consumer
import worker_capture
from admission_io import FALSE, wire, sha
from test_admitted_worker import authored_request
from test_worker_capture import fixture_observation


def declared_result(head):
    return {"schema": "terminal-planning-admission-experiment@1", "completed": True,
        "policy": deepcopy(subject.POLICY), "native_head": deepcopy(head), "source_count": 5,
        "task_count": 4, "native_local_metatasks_admitted": 8, "worker_child_invocations": 8,
        "local_consumer_calls": 8, "actual_external_provider_invocations": 0,
        "new_optimizer_updates": 0, "new_prover_invocations": 0, "source_body_execution": False,
        "metadata_original_record_counts": {"source_files": 5},
        "native_capsule_inventory": {"source_entries": 5}, "artifact_pins": [],
        "seconds": 0.0, "peak_rss_kib": 1, **FALSE}


@pytest.fixture
def inventory(authored_request):
    with tempfile.TemporaryDirectory(prefix=".authored-public-evidence-", dir=subject.ROOT) as directory:
        output = Path(directory)
        files = {name: ("authored core " + name).encode() for name in subject.FILES}
        for task in subject.TASKS:
            for mode in subject.MODES:
                for leaf in subject.WORKER_LEAVES - {"router-allocation.duckdb.wal"}:
                    name = f"workers/{task}/{mode}/{leaf}"
                    files[name] = b"" if leaf == "stderr.log" else ("authored public " + name).encode()
                for leaf in ("input-binding.json", "validate-planning-observation.py", "planning-observation.json"):
                    name = f"jobs/{task}-{mode}/repository/{leaf}"
                    files[name] = ("authored public " + name).encode()
                name = f"jobs/{task}-{mode}/admission/planning-job.json"
                files[name] = ("authored public " + name).encode()
        result = declared_result(authored_request["expected_head"])
        for name, raw in files.items():
            path = output / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            result["artifact_pins"].append({"relative_path": name, "bytes": len(raw), "sha256": sha(raw)})
        result["artifact_pins"].sort(key=lambda row: row["relative_path"])
        yield output, result, files


def test_closed_evidence_inventory_acquires_all_declared_public_bytes(inventory):
    output, result, files = inventory
    assert subject.validate_result(result) is None
    assert subject.artifact_check(output, result) == files
    assert len(files) == 74


@pytest.mark.parametrize("damage", ["extra", "missing_flag", "worker_bool", "worker_count", "local_count",
    "admission_count", "provider", "provider_bool", "optimizer", "prover", "source_body", "authority_zero",
    "policy_zero", "head_bool", "seconds_nan", "seconds_negative", "rss_float", "empty_metadata"])
def test_result_cannot_promote_work_authority_or_accept_nonfinite_diagnostics(inventory, damage):
    _, result, _ = inventory
    if damage == "extra": result["invented_coverage_receipt"] = True
    elif damage == "missing_flag": result.pop("proof_authority")
    elif damage == "worker_bool": result["worker_child_invocations"] = True
    elif damage == "worker_count": result["worker_child_invocations"] = 7
    elif damage == "local_count": result["local_consumer_calls"] = 9
    elif damage == "admission_count": result["native_local_metatasks_admitted"] = 0
    elif damage == "provider": result["actual_external_provider_invocations"] = 1
    elif damage == "provider_bool": result["actual_external_provider_invocations"] = False
    elif damage == "optimizer": result["new_optimizer_updates"] = 1
    elif damage == "prover": result["new_prover_invocations"] = 1
    elif damage == "source_body": result["source_body_execution"] = True
    elif damage == "authority_zero": result["proof_authority"] = 0
    elif damage == "policy_zero": result["policy"]["proof_authority"] = 0
    elif damage == "head_bool": result["native_head"]["generation"] = True
    elif damage == "seconds_nan": result["seconds"] = float("nan")
    elif damage == "seconds_negative": result["seconds"] = -1
    elif damage == "rss_float": result["peak_rss_kib"] = 1.0
    elif damage == "empty_metadata": result["metadata_original_record_counts"] = {}
    with pytest.raises(ValueError):
        subject.validate_result(result)


@pytest.mark.parametrize("damage", ["duplicate", "missing_worker", "missing_job", "traversal", "backslash",
    "unknown_task", "unknown_mode", "unknown_worker_leaf", "private_key_leaf", "extra_job_depth",
    "bool_bytes", "negative_bytes", "wrong_hash", "unsorted", "actual_extra", "symlink", "hardlink", "changed"])
def test_public_artifact_scope_refuses_omission_aliasing_and_private_leaf_names(inventory, damage):
    output, result, _ = inventory
    rows = result["artifact_pins"]
    worker = next(row for row in rows if row["relative_path"].endswith("/request.json"))
    path = output / worker["relative_path"]
    if damage == "duplicate": rows.append(deepcopy(rows[-1])); rows.sort(key=lambda row: row["relative_path"])
    elif damage == "missing_worker": rows.remove(worker); path.unlink()
    elif damage == "missing_job":
        row = next(row for row in rows if row["relative_path"].endswith("/input-binding.json"))
        rows.remove(row); (output / row["relative_path"]).unlink()
    elif damage == "traversal": worker["relative_path"] = "workers/../private/key"
    elif damage == "backslash": worker["relative_path"] = worker["relative_path"].replace("/", "\\")
    elif damage == "unknown_task": worker["relative_path"] = "workers/private-task/adaptive/request.json"
    elif damage == "unknown_mode": worker["relative_path"] = worker["relative_path"].replace("/adaptive/", "/external/").replace("/expanded/", "/external/")
    elif damage == "unknown_worker_leaf": worker["relative_path"] = str(Path(worker["relative_path"]).with_name("unreviewed.json"))
    elif damage in {"private_key_leaf", "extra_job_depth"}:
        row = next(row for row in rows if row["relative_path"].endswith("/input-binding.json"))
        parent = Path(row["relative_path"]).parent
        row["relative_path"] = str(parent / "local_dev_profile.key" if damage == "private_key_leaf" else parent / "extra" / "input.json")
    elif damage == "bool_bytes": worker["bytes"] = False
    elif damage == "negative_bytes": worker["bytes"] = -1
    elif damage == "wrong_hash": worker["sha256"] = "0" * 64
    elif damage == "unsorted": rows.reverse()
    elif damage == "actual_extra": (path.parent / "unreviewed.json").write_bytes(b"authored extra")
    elif damage == "symlink":
        raw = path.read_bytes(); path.unlink(); target = output / "authored-target"; target.write_bytes(raw); path.symlink_to(target)
    elif damage == "hardlink": os.link(path, output / "authored-hardlink")
    elif damage == "changed": path.write_bytes(b"changed authored public data")
    with pytest.raises(ValueError):
        subject.artifact_check(output, result)


@pytest.fixture
def retained_capture(authored_request):
    request = deepcopy(authored_request)
    with tempfile.TemporaryDirectory(prefix=".authored-retained-evidence-", dir=subject.ROOT) as directory:
        output = Path(directory) / "capture"
        observation = fixture_observation(request, output)
        observation["consumer"]["schema"] = router_consumer.SCHEMA
        request_binding = planning_permit.planning_request_binding(request)
        inputs = {"planning_request_binding": request_binding}
        # Deliberately unsigned descriptive unit data. Full native report
        # signature verification belongs to validate_deliveries separately.
        job = {"schema": "authored-descriptive-job-binding@1", "input_binding": inputs,
            "native_head": deepcopy(request["expected_head"]), "input_binding_sha256": sha(wire(inputs))}
        proof = {"schema": planning_permit.SCHEMA, "scope": "planning-observation-only", "worker_mode": "localcapture",
            "native_coordinator_claim_fenced_before_after": True, "single_use_owner_permit_consumed": True,
            "worker_birth_acknowledged_before_stdin": True, "native_job_binding": job, "request_binding": request_binding,
            "claim_binding_sha256": "a" * 64, "launch_binding_sha256": sha(wire(worker_capture.capture_launch_binding(output))),
            "actual_worker_birth": {"pid": 123, "start_time_ticks": 456, "uid": os.geteuid(),
                "parent_pid": 12, "boot_id": "authored-not-a-live-process"},
            "provider_usage": None, "actual_external_provider_invocations": 0, **planning_permit.CLAIMS}
        artifacts = {"request.json": worker_capture._request(request), "stdout.json": wire(observation),
            "stderr.log": b""}
        capture = {"schema": worker_capture.SCHEMA, "request_sha256": sha(artifacts["request.json"]),
            "request_bytes": len(artifacts["request.json"]),
            "native_dispatch": {"module": "ipfs_accelerate_py.agent_supervisor.todo_daemon.supervisor_runtime",
                "method": "run_process_group_stream", "path": str(worker_capture.RUNTIME_SOURCE),
                "sha256": sha(worker_capture._read(worker_capture.RUNTIME_SOURCE, 256_000)),
                "actual_child_birth": {"pid": 123, "start_time_ticks": 456}, "actual_process_invoked": True,
                "native_shared_parent_lease_used": True, "native_child_lease": {"cpu_slots": 1, "memory_mb": 256,
                    "child_process_slots": 1}, "inherited_environment": False, "shell": False},
            "observation": observation, "output_artifacts": [{"relative_path": name, "bytes": len(artifacts[name]),
                "sha256": sha(artifacts[name])} for name in ("request.json", "stdout.json", "stderr.log")],
            "current_head_observation_owned_by_caller": True, "provider_usage": None,
            "actual_external_provider_invocations": 0, "planning_admission": proof, **worker_capture.FALSE}
        yield {"output_dir": output, "request": request, "capture": capture, "artifacts": artifacts}


def test_historical_data_join_never_recreates_job_permit_or_consumer(retained_capture, monkeypatch):
    import planning_job
    def forbidden(*args, **kwargs):
        pytest.fail("historical data replay must not acquire live authority or invoke a consumer")
    monkeypatch.setattr(worker_capture, "launch_admitted_capture", forbidden)
    monkeypatch.setattr(context_worker, "execute_request", forbidden)
    monkeypatch.setattr(router_consumer, "capture_with_native_router", forbidden)
    monkeypatch.setattr(planning_permit, "issue_planning_permit", forbidden)
    monkeypatch.setattr(planning_job, "verify_planning_job", forbidden)
    observation, birth = subject.validate_capture(**retained_capture)
    assert observation == retained_capture["capture"]["observation"] and birth == (123, 456)


@pytest.mark.parametrize("damage", ["extra", "serialized_capability", "coverage", "resume", "provider",
    "provider_bool", "usage", "scope", "worker_mode", "consumed", "fenced", "ack", "request_sha",
    "input_hash", "job_head", "job_request", "birth_pid", "birth_pid_float", "birth_start", "birth_start_float", "birth_uid_float",
    "birth_no_parent", "birth_no_boot", "birth_extra",
    "launch_hash", "claim_hash"])
def test_planning_evidence_is_exact_historical_data_not_transferable_authority(retained_capture, damage):
    proof = retained_capture["capture"]["planning_admission"]
    if damage == "extra": proof["unsigned_dispatch_grant"] = True
    elif damage == "serialized_capability": proof["serialized_capability"] = True
    elif damage == "coverage": proof["original_task_coverage"] = True
    elif damage == "resume": proof["durable_permit_resume_supported"] = True
    elif damage == "provider": proof["actual_external_provider_invocations"] = 1
    elif damage == "provider_bool": proof["actual_external_provider_invocations"] = False
    elif damage == "usage": proof["provider_usage"] = {"tokens": 1}
    elif damage == "scope": proof["scope"] = "original-benchmark-completion"
    elif damage == "worker_mode": proof["worker_mode"] = "external-model"
    elif damage == "consumed": proof["single_use_owner_permit_consumed"] = False
    elif damage == "fenced": proof["native_coordinator_claim_fenced_before_after"] = 1
    elif damage == "ack": proof["worker_birth_acknowledged_before_stdin"] = False
    elif damage == "request_sha": proof["request_binding"]["selected_payload_sha256"] = "0" * 64
    elif damage == "input_hash": proof["native_job_binding"]["input_binding_sha256"] = "0" * 64
    elif damage == "job_head": proof["native_job_binding"]["native_head"]["generation"] += 1
    elif damage == "job_request": proof["native_job_binding"]["input_binding"]["planning_request_binding"] = {}
    elif damage == "birth_pid": proof["actual_worker_birth"]["pid"] += 1
    elif damage == "birth_pid_float": proof["actual_worker_birth"]["pid"] = 123.0
    elif damage == "birth_start": proof["actual_worker_birth"]["start_time_ticks"] += 1
    elif damage == "birth_start_float": proof["actual_worker_birth"]["start_time_ticks"] = 456.0
    elif damage == "birth_uid_float": proof["actual_worker_birth"]["uid"] = float(os.geteuid())
    elif damage == "birth_no_parent": proof["actual_worker_birth"]["parent_pid"] = 0
    elif damage == "birth_no_boot": proof["actual_worker_birth"]["boot_id"] = ""
    elif damage == "birth_extra": proof["actual_worker_birth"]["transferable_dispatch_grant"] = True
    elif damage == "launch_hash": proof["launch_binding_sha256"] = "0" * 64
    elif damage == "claim_hash": proof["claim_binding_sha256"] = "g" * 64
    with pytest.raises(ValueError):
        subject.validate_capture(**retained_capture)


@pytest.mark.parametrize("damage", ["request_file", "stderr", "stdout", "birth_bool", "runtime_hash",
    "shell", "lease_float", "consumer_flag", "consumer_bytes_float", "extra_capture", "output_hash"])
def test_capture_parentage_consumer_bytes_and_retained_file_custody_refuse(retained_capture, damage):
    capture = retained_capture["capture"]
    if damage == "request_file": retained_capture["artifacts"]["request.json"] += b" "
    elif damage == "stderr": retained_capture["artifacts"]["stderr.log"] = b"authored unexpected stderr"
    elif damage == "stdout": retained_capture["artifacts"]["stdout.json"] += b"\n"
    elif damage == "birth_bool": capture["native_dispatch"]["actual_child_birth"]["pid"] = True
    elif damage == "runtime_hash": capture["native_dispatch"]["sha256"] = "0" * 64
    elif damage == "shell": capture["native_dispatch"]["shell"] = True
    elif damage == "lease_float": capture["native_dispatch"]["native_child_lease"]["memory_mb"] = 256.0
    elif damage in {"consumer_flag", "consumer_bytes_float"}:
        consumer = capture["observation"]["consumer"]
        if damage == "consumer_flag": consumer["claims"]["network_provider_invoked"] = 0
        else: consumer["input_bytes"] = float(consumer["input_bytes"])
        retained_capture["artifacts"]["stdout.json"] = wire(capture["observation"])
        row = capture["output_artifacts"][1]
        row.update(bytes=len(retained_capture["artifacts"]["stdout.json"]), sha256=sha(retained_capture["artifacts"]["stdout.json"]))
    elif damage == "extra_capture": capture["invented_native_receipt"] = True
    elif damage == "output_hash": capture["output_artifacts"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError):
        subject.validate_capture(**retained_capture)
