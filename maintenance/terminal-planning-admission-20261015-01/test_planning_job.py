"""Authored fixtures exercise real native admission, never benchmark solutions."""
import copy
import hashlib
import json
from pathlib import Path
import stat
import subprocess
import sys

import pytest

import planning_job as jobs


def binding():
    instruction = "Preserve this whole instruction: λ.\n  trailing spaces  \n"
    source = "def authored_fixture(x):\n    return x + 1\n"
    return {
        "native_head": {"namespace": "authored-fixture", "root_uri": "file:///authored-fixture",
                        "snapshot_cid": "fixture-snapshot", "manifest_cid": "fixture-manifest", "revision": 1},
        "instructions": [{"task_id": "authored-task", "instruction_text": instruction,
                          "instruction_sha256": hashlib.sha256(instruction.encode()).hexdigest()}],
        "source_records": [{"path": "fixture.py", "source_text": source,
                           "sha256": hashlib.sha256(source.encode()).hexdigest()}],
        "max_input_tokens": 1024,
        "planning_request_binding": {"request_sha256": "a"*64, "session_id": "authored-session"},
        "original_residuals": [{"required": True, "resolved": False, "text": instruction}],
    }


@pytest.fixture
def live_job(tmp_path):
    root = tmp_path
    private = root / "private"
    private.mkdir(mode=0o700)
    with jobs.create_owned_planning_job(job_repository=root/"job", private_root=private,
            public_output=root/"public", input_binding=binding(), task_key="authored-observation") as job:
        yield job


def test_real_native_admission_and_materialization(live_job):
    job = live_job
    report = job.report
    verified = jobs.verify_planning_job(job)
    assert verified == job.job_binding
    assert job.manifest["payload"]["schema"] == "supervisor-local-benchmark-manifest@3"
    assert report["native_formal_compilation"]["status"] == "compiled"
    assert report["native_formal_compilation"]["proof_results"] == []
    assert report["native_plan_validation"]["status"] == "consistent"
    assert report["native_materialization"]["task_cids"] == [job.task_cid]
    assert job.intent.get_task(job.task_cid)["status"] == "ready"
    assert report["profile_capabilities"] == sorted(jobs.profiles.ALLOWED_LOCAL_CAPABILITIES)
    assert len(report["profile_capabilities"]) == 5
    assert report["capability_scope"] == "bounded-local-work"
    assert report["native_lifecycle_witness"]["profile_content_id"] == job.manifest["payload"]["profile_content_id"]
    assert report["acceptance_pending"] is True
    assert set(job.manifest["payload"]["sources"]) == {jobs.INPUT_NAME, jobs.VALIDATOR_NAME}
    assert job.manifest["payload"]["created_outputs"] == [jobs.OUTPUT_NAME]
    assert all(item["required"] is True and item["phase"] == "post_execution"
               for item in job.admission["receipt"]["payload"]["pending_requirements"])


def test_original_full_inputs_remain_opaque_unresolved(live_job):
    assert live_job.input_binding == binding()
    residual = live_job.report["original_instruction_residuals"][0]
    assert residual["instruction_text"] == binding()["instructions"][0]["instruction_text"]
    assert residual["resolved"] is False and residual["required"] is True
    assert all(live_job.report[name] is False for name in jobs.FALSE)
    assert all(live_job.job_binding[name] is False for name in jobs.FALSE)
    assert live_job.graph.unresolved_questions == ()  # metatask, not the original task graph
    original = live_job.input_binding
    original["instructions"][0]["instruction_text"] = "rewritten"
    assert live_job.input_binding == binding()


def test_public_report_cannot_recreate_live_owner(live_job):
    with pytest.raises(ValueError, match="live owned"):
        jobs.verify_planning_job(live_job.report)
    fake = object.__new__(jobs.OwnedPlanningJob)
    fake.__dict__.update(live_job.__dict__)
    with pytest.raises(ValueError, match="live owned"):
        jobs.verify_planning_job(fake)
    with pytest.raises(TypeError, match="context manager"):
        jobs.OwnedPlanningJob(object(), intent=live_job.intent)


@pytest.mark.parametrize("target", [jobs.INPUT_NAME, jobs.VALIDATOR_NAME])
def test_changed_tracked_source_refused(live_job, target):
    path = live_job.job_repository / target
    original = path.read_bytes()
    try:
        path.write_bytes(original+b"\n")
        with pytest.raises(ValueError):
            jobs.verify_planning_job(live_job)
    finally:
        path.write_bytes(original)
    jobs.verify_planning_job(live_job)


def test_rogue_declared_output_cannot_skip_owned_writer(live_job):
    path = live_job.job_repository / jobs.OUTPUT_NAME
    path.write_text("{}")
    try:
        with pytest.raises(ValueError, match="outside owned writer"):
            jobs.verify_planning_job(live_job)
    finally:
        path.unlink()


def test_tampered_native_receipt_fails_signature(live_job):
    original = copy.deepcopy(live_job.admission)
    try:
        live_job.admission["receipt"]["payload"]["completion_authority"] = True
        with pytest.raises(ValueError):
            jobs.verify_planning_job(live_job)
    finally:
        live_job.admission.clear()
        live_job.admission.update(original)
    jobs.verify_planning_job(live_job)


def test_wrong_fixture_registry_refuses_live_job(live_job, tmp_path):
    original = jobs.profiles._LIFECYCLE_REGISTRY_ROOT_OVERRIDE
    try:
        jobs.profiles._LIFECYCLE_REGISTRY_ROOT_OVERRIDE = tmp_path/"not-the-owned-registry"
        with pytest.raises(ValueError, match="registry scope changed"):
            jobs.verify_planning_job(live_job)
    finally:
        jobs.profiles._LIFECYCLE_REGISTRY_ROOT_OVERRIDE = original
    jobs.verify_planning_job(live_job)


@pytest.mark.parametrize("tokens", [True, -1, 1025, 2.5, "37"])
def test_capture_budget_or_type_cannot_create_artifact(live_job, tokens):
    with pytest.raises(ValueError):
        jobs.write_planning_observation(live_job,
            {"observation": {"selection": {"input_tokens": tokens}}})
    assert not (live_job.job_repository/jobs.OUTPUT_NAME).exists()
    jobs.verify_planning_job(live_job)


def test_native_pending_gate_cannot_be_removed_or_completed(live_job):
    task = live_job.intent.get_task(live_job.task_cid)
    kwargs = {"task_cid": live_job.task_cid, "task_alias": task["task_alias"],
              "goal_cid": task["goal_cid"], "plan_cid": task["plan_cid"],
              "objective_id": task["objective_id"], "identity": task["identity"]}
    with pytest.raises(ValueError, match="cannot be removed"):
        live_job.intent.upsert_task(**kwargs, body={"title": "removed"})
    with pytest.raises(ValueError, match="completion requires"):
        live_job.intent.upsert_task(**kwargs, body=task["body"], status="done")
    jobs.verify_planning_job(live_job)


@pytest.mark.parametrize("change", [
    lambda d: d["instructions"][0].update(instruction_text="changed"),
    lambda d: d["instructions"][0].update(instruction_sha256="0"*64),
    lambda d: d["source_records"][0].update(source_text="changed"),
    lambda d: d["source_records"][0].update(sha256="0"*64),
    lambda d: d.update(max_input_tokens=True),
    lambda d: d.update(max_input_tokens=0),
    lambda d: d.update(max_input_tokens=1000001),
    lambda d: d.update(native_head={}),
    lambda d: d.update(instructions=[]),
    lambda d: d.update(source_records=[]),
    lambda d: d["source_records"][0].update(path="../fixture.py"),
    lambda d: d["source_records"][0].update(path="a//fixture.py"),
    lambda d: d["source_records"][0].update(path="."),
    lambda d: d["source_records"][0].update(path="fixture\n.py"),
    lambda d: d["source_records"].append(copy.deepcopy(d["source_records"][0])),
    lambda d: d["instructions"].append(copy.deepcopy(d["instructions"][0])),
    lambda d: d.update(unsupported_float=0.5),
    lambda d: d.update(unsupported_tuple=(1,)),
])
def test_input_binding_integrity_and_bounds(change):
    value = binding()
    change(value)
    with pytest.raises(ValueError):
        jobs.validate_input_binding(value)


def test_cyclic_input_rejected_before_recursion_failure():
    value = binding()
    value["cycle"] = value
    with pytest.raises(ValueError, match="structure bound"):
        jobs.validate_input_binding(value)


def test_cleanup_on_body_failure_and_historical_public_evidence(tmp_path):
    private = tmp_path/"private"
    private.mkdir(mode=0o700)
    previous = jobs.profiles._LIFECYCLE_REGISTRY_ROOT_OVERRIDE
    handle = None
    with pytest.raises(RuntimeError, match="authored interruption"):
        with jobs.create_owned_planning_job(job_repository=tmp_path/"job", private_root=private,
                public_output=tmp_path/"public", input_binding=binding(), task_key="cleanup-observation") as job:
            handle = job
            assert stat.S_IMODE(private.stat().st_mode) == 0o700
            assert jobs.profiles._LIFECYCLE_REGISTRY_ROOT_OVERRIDE == private/"fixture-registry"
            raise RuntimeError("authored interruption")
    assert not private.exists()
    assert handle.intent.is_open is False
    assert jobs.profiles._LIFECYCLE_REGISTRY_ROOT_OVERRIDE == previous
    assert (tmp_path/"public"/"planning-job.json").is_file()
    with pytest.raises(ValueError, match="live owned"):
        jobs.verify_planning_job(handle)


def test_private_state_refuses_evidence_tree_and_insecure_modes(tmp_path):
    with pytest.raises(ValueError, match="outside the evidence stage"):
        with jobs.create_owned_planning_job(job_repository=tmp_path/"job", private_root=jobs.ROOT/"not-created-private",
                public_output=tmp_path/"public", input_binding=binding(), task_key="authored"):
            pytest.fail("must not enter")
    private = tmp_path/"private"
    private.mkdir(mode=0o755)
    with pytest.raises(ValueError, match="0700"):
        with jobs.create_owned_planning_job(job_repository=tmp_path/"job", private_root=private,
                public_output=tmp_path/"public", input_binding=binding(), task_key="authored"):
            pytest.fail("must not enter")
    assert private.exists() and not list(private.iterdir())


def test_write_artifact_preserves_all_inputs_but_never_accepts(live_job):
    # Last test using this live fixture: creation intentionally changes its state.
    capture = {"observation": {"selection": {"input_tokens": 37}}, "authored_capture": True}
    receipt = jobs.write_planning_observation(live_job, capture)
    raw = Path(receipt["path"]).read_bytes()
    artifact = json.loads(raw)
    assert artifact["input_binding"] == binding()
    assert artifact["native_head"] == binding()["native_head"]
    assert artifact["observed_input_tokens"] == 37
    assert receipt["sha256"] == hashlib.sha256(raw).hexdigest()
    assert all(artifact[key] is False for key in jobs.FALSE)
    assert receipt["acceptance_pending"] is True
    assert live_job.intent.get_task(live_job.task_cid)["status"] == "ready"
    subprocess.run([sys.executable, str(live_job.job_repository/jobs.VALIDATOR_NAME)],
                   cwd=live_job.job_repository, check=True, capture_output=True, timeout=10)
    with pytest.raises(ValueError, match="create-only"):
        jobs.write_planning_observation(live_job, capture)
    try:
        Path(receipt["path"]).write_bytes(raw+b"\n")
        with pytest.raises(ValueError, match="observation changed"):
            jobs.verify_planning_job(live_job)
    finally:
        Path(receipt["path"]).write_bytes(raw)
    jobs.verify_planning_job(live_job)


@pytest.fixture(scope="module")
def historical_report(tmp_path_factory):
    root = tmp_path_factory.mktemp("historical-planning-fixture")
    private = root/"private"
    private.mkdir(mode=0o700)
    with jobs.create_owned_planning_job(job_repository=root/"job", private_root=private,
            public_output=root/"public", input_binding=binding(), task_key="historical-observation") as job:
        report = job.report
    assert not private.exists()
    return report


def test_historical_replay_after_private_cleanup_never_opens_former_state(historical_report, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("historical replay attempted a live or filesystem read")
    monkeypatch.setattr(jobs.profiles, "load_local_profile", forbidden)
    monkeypatch.setattr(jobs.native, "verify_local_benchmark_admission", forbidden)
    monkeypatch.setattr(jobs.native, "_manifest", forbidden)
    monkeypatch.setattr(jobs.native, "_repository", forbidden)
    monkeypatch.setattr(jobs.IntentRepository, "__init__", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    replay = jobs.verify_historical_planning_report(historical_report)
    assert replay["consistent"] is True
    assert replay["historical_signature_consistency_only"] is True
    assert replay["current_owner_authority"] is False
    assert replay["private_state_opened"] is False
    assert replay["live_registry_observed"] is False
    assert all(replay[key] is False for key in jobs.FALSE)


@pytest.mark.parametrize("change", [
    lambda r: r.update(completion_authority=True),
    lambda r: r.update(account_registry_authority=True),
    lambda r: r.update(original_task_coverage=0),
    lambda r: r.update(current_owner_authority=True),
    lambda r: r.update(acceptance_pending=False),
    lambda r: r.update(prover_invocations=True),
    lambda r: r["job_binding"].update(task_cid="changed"),
    lambda r: r["job_binding"].update(receipt_cid="changed"),
    lambda r: r["job_binding"].update(native_head={"revision": 2}),
    lambda r: r["job_binding"]["input_binding"]["source_records"][0].update(source_text="changed"),
    lambda r: r["job_binding"]["input_binding"]["instructions"][0].update(instruction_text="changed"),
    lambda r: r["native_admission"]["receipt"]["payload"].update(completion_authority=True),
    lambda r: r["native_admission"]["manifest"]["payload"].update(baseline_commit="0"*40),
    lambda r: r["native_pending_contract"]["payload"].update(intent_owner_id="changed"),
    lambda r: r["native_formal_compilation"].update(proof_results=[{}]),
    lambda r: r["native_plan_validation"].update(status="proved"),
    lambda r: r["native_lifecycle_witness"].update(root_signature="changed"),
    lambda r: r["native_lifecycle_witness"]["profile"].update(capabilities=["network"]),
    lambda r: r["native_profile"].update(revoked=True),
    lambda r: r["native_profile"].update(revoked=0),
    lambda r: r["native_receipt_reference"].update(bytes=0),
    lambda r: r["original_instruction_residuals"][0].update(resolved=True),
    lambda r: r["native_materialization"].update(completion_authority=True),
    lambda r: r["native_materialization"].update(completion_authority=0),
])
def test_historical_report_rejects_mutations(historical_report, change):
    report = copy.deepcopy(historical_report)
    change(report)
    with pytest.raises((ValueError, TypeError)):
        jobs.verify_historical_planning_report(report)

