"""Public artifact custody and scope checks; authored receipts grant no authority."""
from copy import deepcopy
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

import jsonl_verify as evidence
from jsonl_io import FALSE, ROOT, read, sha, wire
from jsonl_run import FILES, POLICY
from jsonl_lean import LEAN_LABELS
from decoder_lean import DECODER_LABELS
from observed_files import FILE_PATHS, observe_bundle


@pytest.fixture
def authored_result():
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    from ipfs_datasets_py.logic.software_contracts.content import cid_for_structured
    cid = cid_for_structured({"schema": "authored-byte-evidence-unit@1"})
    head = CodebaseHead(repository_id="authored-byte-evidence", generation=1,
        manifest_cid=cid, snapshot_cid=cid, ast_revision_id="rev:authored-byte-evidence:snapshot:" + cid,
        receipt_cid=cid).to_dict()
    return {"schema": "terminal-lean-jsonl-decoder-experiment@1", "completed": True,
        "policy": deepcopy(POLICY), "native_head": head, "source_count": 5, "task_count": 4,
        "file_case_count": 30, "outcome_counts": dict(evidence.COUNTS), "all_fixture_expectations_matched": True,
        "new_optimizer_updates": 0, "external_provider_calls": 0, "source_body_execution": False,
        "metadata_original_record_counts": {"ast": 5, "jsonl_file_models": 30},
        "native_capsule_inventory": {"capsules": 57}, "decoder_summary": deepcopy(evidence.DECODER_SUMMARY),
        "artifact_pins": [],
        "seconds": 1.25, "peak_rss_kib": 123, **FALSE}


def _authored_artifacts(output, result):
    """Inert custody bytes only: no fabricated compiler/process claim is checked."""
    output.mkdir()
    (output / "lean").mkdir()
    (output / "decoder-lean").mkdir()
    names = [*FILES, *["lean/" + leaf for leaf in evidence.LEAN_LEAVES],
             *["decoder-lean/" + leaf for leaf in evidence.DECODER_LEAVES]]
    for case in evidence._case_ids():
        directory = output / "file-cases" / case
        (directory / "input_data").mkdir(parents=True)
        (directory / "output_data").mkdir()
        names.extend("file-cases/" + case + "/" + leaf for leaf in FILE_PATHS)
    pins = []
    for name in sorted(names):
        raw = b"" if name.endswith(".jsonl") else wire({"authored_custody_fixture": name})
        (output / name).write_bytes(raw)
        pins.append({"relative_path": name, "bytes": len(raw), "sha256": sha(raw)})
    result["artifact_pins"] = pins


def _authored_fault(result, output, result_raw):
    return {"schema": "terminal-jsonl-model-faults@1", "qualified": True,
        "selected_run": output.name, "selected_result_sha256": sha(result_raw), "native_head": result["native_head"],
        "controls": [{"case": case, "rejected": True,
            "exception_class": "StaleCodebaseError" if case == evidence.FAULT_CASES[-1] else "ValueError",
            "message": "authored schema fixture; no actual fault-process observation claimed"}
            for case in evidence.FAULT_CASES],
        "artifact_pins": [], "source_restored": True, "source_body_execution": False,
        "external_provider_calls": 0, "new_optimizer_updates": 0, **FALSE}


def test_exact_result_scope_and_inventory_constants(authored_result):
    evidence.validate_result(authored_result)
    assert len(FILES) == 14 and len(evidence.LEAN_LEAVES) == 11
    assert len(evidence.DECODER_LEAVES) == 13 and len(DECODER_LABELS) == 6
    assert len(evidence._case_ids()) == 30
    assert LEAN_LABELS == ("finite-scheduler", "false-duplicate-missing-ids", "false-nine-global-shapes",
                           "false-inconsistent-batch", "false-insufficient-alignment")
    assert all(authored_result[key] is False for key in FALSE)


@pytest.mark.parametrize("key", [*FALSE, "source_body_execution"])
def test_unobserved_authority_cannot_be_promoted(authored_result, key):
    authored_result[key] = True
    with pytest.raises(ValueError):
        evidence.validate_result(authored_result)


@pytest.mark.parametrize("key,value", [
    ("source_count", True), ("task_count", 4.0), ("file_case_count", 30.0),
    ("file_case_count", 29), ("new_optimizer_updates", False), ("external_provider_calls", 0.0),
    ("seconds", float("nan")), ("seconds", float("inf")), ("seconds", True),
    ("seconds", -1), ("peak_rss_kib", True), ("all_fixture_expectations_matched", 1),
])
def test_exact_counters_and_finite_diagnostics(authored_result, key, value):
    authored_result[key] = value
    with pytest.raises(ValueError):
        evidence.validate_result(authored_result)


@pytest.mark.parametrize("key,value", [
    ("total", 31), ("accepted", 8), ("model_refusal", 8), ("file_refusal", 13),
    ("derived_cases", 17), ("accepted", True), ("total", 30.0),
])
def test_all_fixture_outcome_counts_must_match(authored_result, key, value):
    authored_result["outcome_counts"][key] = value
    with pytest.raises(ValueError):
        evidence.validate_result(authored_result)


@pytest.mark.parametrize("damage", ["missing_outcome", "unknown_outcome", "unknown_result", "missing_result"])
def test_closed_result_schema(authored_result, damage):
    if damage == "missing_outcome":
        authored_result["outcome_counts"].pop("derived_cases")
    elif damage == "unknown_outcome":
        authored_result["outcome_counts"]["proof_pass"] = 7
    elif damage == "unknown_result":
        authored_result["parser_correctness_proved"] = True
    else:
        authored_result.pop("file_case_count")
    with pytest.raises(ValueError):
        evidence.validate_result(authored_result)


@pytest.mark.parametrize("key,value", [
    ("source_body_execution", 0), ("physical_filesystem_immutability_proved", True),
    ("formal_parser_correctness_proved", 0), ("source_count", 5.0),
    ("general_Python_parser_Lean_equivalence_proved", True),
    ("metrics_source", "runtime measurements"), ("model_rows_source", "caller-supplied rows"),
    ("decoder_scope", "universal Python-parser and source-runtime equivalence"),
    ("original_task_satisfaction", True),
])
def test_policy_interpretation_and_aliases_refused(authored_result, key, value):
    authored_result["policy"][key] = value
    with pytest.raises(ValueError):
        evidence.validate_result(authored_result)


@pytest.mark.parametrize("family,value", [
    ("metadata_original_record_counts", {"ast": True}),
    ("metadata_original_record_counts", {"jsonl_file_models": 30.0}),
    ("native_capsule_inventory", {"capsules": -1}), ("native_capsule_inventory", {}),
])
def test_metadata_diagnostic_maps_are_exact_nonnegative_counts(authored_result, family, value):
    authored_result[family] = value
    with pytest.raises(ValueError):
        evidence.validate_result(authored_result)


@pytest.mark.parametrize("damage", ["missing", "unknown", "bool", "float", "changed"])
def test_decoder_summary_is_closed_and_exact(authored_result, damage):
    summary = authored_result["decoder_summary"]
    key = next(iter(summary))
    if damage == "missing":
        summary.pop(key)
    elif damage == "unknown":
        summary["universal_python_parser_equivalence_proved"] = True
    elif damage == "bool":
        summary[key] = True
    elif damage == "float":
        summary[key] = float(summary[key])
    else:
        summary[key] += 1
    with pytest.raises(ValueError):
        evidence.validate_result(authored_result)


@pytest.mark.parametrize("damage", ["unknown_head", "missing_head", "generation_float", "generation_bool"])
def test_canonical_complete_head_required(authored_result, damage):
    if damage == "unknown_head":
        authored_result["native_head"]["authority"] = True
    elif damage == "missing_head":
        authored_result["native_head"].pop("receipt_cid")
    else:
        authored_result["native_head"]["generation"] = 1.0 if damage == "generation_float" else True
    with pytest.raises((ValueError, TypeError)):
        evidence.validate_result(authored_result)


@pytest.mark.parametrize("damage", ["body", "missing_pin", "unknown_pin", "size_float", "size_bool",
    "duplicate_pin", "wrong_sha", "traversal", "absolute", "noncanonical", "unordered", "sha_type"])
def test_exact158_artifact_pins_refuse_custody_changes(authored_result, tmp_path, monkeypatch, damage):
    monkeypatch.setattr(evidence, "ROOT", tmp_path)
    output = tmp_path / "authored-run"
    _authored_artifacts(output, authored_result)
    assert len(evidence.artifact_check(output, authored_result)) == 158
    if damage == "body":
        (output / FILES[0]).write_bytes(b"changed")
    elif damage == "missing_pin":
        authored_result["artifact_pins"].pop()
    elif damage == "unknown_pin":
        authored_result["artifact_pins"][0]["relative_path"] = "private-authored-not-secret.key"
    elif damage in {"size_float", "size_bool"}:
        authored_result["artifact_pins"][0]["bytes"] = 0.0 if damage == "size_float" else False
    elif damage == "duplicate_pin":
        authored_result["artifact_pins"][-1] = deepcopy(authored_result["artifact_pins"][0])
    elif damage == "wrong_sha":
        authored_result["artifact_pins"][0]["sha256"] = "a" * 64
    elif damage in {"traversal", "absolute", "noncanonical"}:
        authored_result["artifact_pins"][0]["relative_path"] = {
            "traversal": "../policy.json", "absolute": "/policy.json", "noncanonical": "./policy.json"}[damage]
    elif damage == "unordered":
        authored_result["artifact_pins"].reverse()
    else:
        authored_result["artifact_pins"][0]["sha256"] = 0
    with pytest.raises(ValueError):
        evidence.artifact_check(output, authored_result)


@pytest.mark.parametrize("damage", ["extra_case", "missing_case", "extra_bundle_leaf", "missing_bundle_leaf",
    "extra_lean_leaf", "extra_decoder_leaf", "missing_decoder_leaf", "hardlink", "symlink_leaf",
    "symlink_lean", "symlink_decoder", "symlink_case", "symlink_input", "fifo_leaf"])
def test_closed_artifact_directory_profiles(authored_result, tmp_path, monkeypatch, damage):
    monkeypatch.setattr(evidence, "ROOT", tmp_path)
    output = tmp_path / "authored-run"
    _authored_artifacts(output, authored_result)
    first = output / "file-cases" / evidence._case_ids()[0]
    leaf = first / FILE_PATHS[0]
    if damage == "extra_case":
        (output / "file-cases" / "unselected-case").mkdir()
    elif damage == "missing_case":
        first.rename(tmp_path / "detached-case")
    elif damage == "extra_bundle_leaf":
        (first / "input_data" / "unselected.jsonl").write_bytes(b"unread")
    elif damage == "missing_bundle_leaf":
        leaf.unlink()
    elif damage == "extra_lean_leaf":
        (output / "lean" / "private-authored-not-secret.key").write_bytes(b"unread")
    elif damage == "extra_decoder_leaf":
        (output / "decoder-lean" / "private-authored-not-secret.key").write_bytes(b"unread")
    elif damage == "missing_decoder_leaf":
        (output / "decoder-lean" / "report.json").unlink()
    elif damage == "hardlink":
        os.link(leaf, tmp_path / "linked")
    elif damage in {"symlink_leaf", "fifo_leaf"}:
        leaf.unlink()
        if damage == "fifo_leaf":
            os.mkfifo(leaf)
        else:
            leaf.symlink_to(tmp_path / "never-opened")
    else:
        target = {"symlink_lean": output / "lean", "symlink_decoder": output / "decoder-lean", "symlink_case": first,
                  "symlink_input": first / "input_data"}[damage]
        detached = tmp_path / "detached"
        target.rename(detached)
        target.symlink_to(detached, target_is_directory=True)
    with pytest.raises((ValueError, OSError)):
        evidence.artifact_check(output, authored_result)


@pytest.mark.parametrize("directory", ["lean", "decoder-lean"])
def test_unknown_leaf_inventory_refused_before_any_artifact_read(authored_result, tmp_path, monkeypatch, directory):
    import worker_capture
    monkeypatch.setattr(evidence, "ROOT", tmp_path)
    output = tmp_path / "authored-run"
    _authored_artifacts(output, authored_result)
    (output / directory / "unselected-authored-leaf").write_bytes(b"not read")
    monkeypatch.setattr(worker_capture, "_read", lambda *a, **k: pytest.fail("unknown leaf must not be opened"))
    with pytest.raises(ValueError, match="unknown leaf"):
        evidence.artifact_check(output, authored_result)


@pytest.mark.parametrize("damage", ["head", "missing_case", "order", "rejected_alias", "qualified_alias",
    "restored_alias", "counter_alias", "owner_exception", "unknown_field", "result_sha", "run", "control"])
def test_fault_schema_binds_selected_result_exact_controls(authored_result, tmp_path, monkeypatch, damage):
    monkeypatch.setattr(evidence, "ROOT", tmp_path)
    # This test checks only closed report syntax. Real artifact replay has its own controls below.
    monkeypatch.setattr(evidence, "_fault_artifacts", lambda *a, **k: {})
    output = tmp_path / "authored-run"
    result_raw = wire(authored_result)
    report = _authored_fault(authored_result, output, result_raw)
    target = tmp_path / "authored-fault-report.json"
    target.write_bytes(wire(report))
    evidence.fault_precondition(target.name, output=output, result=authored_result, result_raw=result_raw)
    if damage == "head":
        report["native_head"] = {**report["native_head"], "generation": 2}
    elif damage == "missing_case":
        report["controls"].pop()
    elif damage == "order":
        report["controls"].reverse()
    elif damage == "rejected_alias":
        report["controls"][0]["rejected"] = 1
    elif damage == "qualified_alias":
        report["qualified"] = 1
    elif damage == "restored_alias":
        report["source_restored"] = 1
    elif damage == "counter_alias":
        report["external_provider_calls"] = False
    elif damage == "owner_exception":
        report["controls"][-1]["exception_class"] = "ValueError"
    elif damage == "unknown_field":
        report["original_task_satisfaction"] = True
    elif damage == "result_sha":
        report["selected_result_sha256"] = "f" * 64
    elif damage == "run":
        report["selected_run"] = "different-run"
    else:
        report["controls"][0] = None
    target.write_bytes(wire(report))
    with pytest.raises(ValueError):
        evidence.fault_precondition(target.name, output=output, result=authored_result, result_raw=result_raw)


def _actual_authored_fault_artifacts(tmp_path, result):
    """Actual owned file edits and observations, without claiming a native owner run."""
    import jsonl_cases
    from file_model_bridge import build_file_model
    contract = json.loads(read(ROOT.parent / "terminal-typed-constraints-20261015-01"
                               / "experiment-01/scheduler-contract.json", 1024**2))
    result["native_head"] = deepcopy(contract["head"])
    output = tmp_path / "authored-run"
    output.mkdir()
    (output / "base-materials.json").write_bytes(wire({"contract": contract}))
    artifact_root = tmp_path / "authored-artifacts"
    artifact_root.mkdir()
    chosen = next(row for row in jsonl_cases.specs() if row["case_id"] == "valid-minimal")
    for case in evidence.FAULT_CASES[:4]:
        parent = artifact_root / case
        parent.mkdir()
        bundle = parent / "bundle"
        spec = deepcopy(chosen)
        spec["case_id"] = "fault-" + case
        jsonl_cases.create_bundle(destination=bundle, spec=spec)
        before, after = observe_bundle(root=bundle), observe_bundle(root=bundle)
        candidate = build_file_model(contract=contract, before=before, after=after,
            metrics=spec["metrics"], case_id=spec["case_id"])
        if case == "forged_derived_model":
            candidate["case"]["buckets"][0]["requests"][0]["prompt_len"] += 64
        else:
            spec["fault"] = {"file_changed_after_model": "changed_input_bytes",
                "same_bytes_replacement": "same_bytes_replacement",
                "plan_changed_after_model": "changed_plan_bytes"}[case]
            jsonl_cases.mutate_between_observations(destination=bundle, spec=spec)
        current = observe_bundle(root=bundle)
        for leaf, value in {"before": before, "after": after, "candidate": candidate, "current": current}.items():
            (parent / (leaf + ".json")).write_bytes(wire(value))
    pins = []
    for case in evidence.FAULT_CASES[:4]:
        names = [case + "/" + leaf + ".json" for leaf in ("before", "after", "candidate", "current")]
        names += [case + "/bundle/" + leaf for leaf in FILE_PATHS]
        for name in names:
            raw = (artifact_root / name).read_bytes()
            pins.append({"relative_path": name, "bytes": len(raw), "sha256": sha(raw)})
    report = _authored_fault(result, output, wire(result))
    report["artifact_pins"] = sorted(pins, key=lambda row: row["relative_path"])
    return output, artifact_root, report


@pytest.mark.parametrize("damage", [None, "missing_pin", "unknown_leaf", "current_replaced", "stale_current",
    "candidate_repaired", "candidate_changed", "candidate_case_id", "candidate_metrics",
    "wrong_contract_head", "symlink_bundle"])
def test_fault_artifacts_replay_actual_current_custody(authored_result, tmp_path, monkeypatch, damage):
    import jsonl_cases
    monkeypatch.setattr(evidence, "ROOT", tmp_path)
    monkeypatch.setattr(jsonl_cases, "ROOT", tmp_path)
    output, artifact_root, report = _actual_authored_fault_artifacts(tmp_path, authored_result)
    assert len(evidence._fault_artifacts("authored-fault-report.json", report, output)) == 32
    if damage is None:
        return
    if damage == "missing_pin":
        report["artifact_pins"].pop()
    elif damage == "unknown_leaf":
        (artifact_root / evidence.FAULT_CASES[0] / "unknown").write_bytes(b"not read")
    elif damage in {"current_replaced", "stale_current"}:
        case = artifact_root / evidence.FAULT_CASES[0]
        if damage == "current_replaced":
            path = case / "bundle" / FILE_PATHS[0]
            temp = tmp_path / "same-bytes"
            temp.write_bytes(path.read_bytes())
            temp.replace(path)
            pin_name = evidence.FAULT_CASES[0] + "/bundle/" + FILE_PATHS[0]
            for pin in report["artifact_pins"]:
                if pin["relative_path"] == pin_name:
                    raw = path.read_bytes()
                    pin.update(bytes=len(raw), sha256=sha(raw))
        else:
            name = evidence.FAULT_CASES[0] + "/current.json"
            raw = (case / "after.json").read_bytes()
            (case / "current.json").write_bytes(raw)
            for pin in report["artifact_pins"]:
                if pin["relative_path"] == name:
                    pin.update(bytes=len(raw), sha256=sha(raw))
    elif damage in {"candidate_repaired", "candidate_changed", "candidate_case_id", "candidate_metrics"}:
        from file_model_bridge import build_file_model
        case_id = "forged_derived_model" if damage == "candidate_repaired" else evidence.FAULT_CASES[0]
        parent = artifact_root / case_id
        candidate = json.loads((parent / "candidate.json").read_bytes())
        if damage == "candidate_repaired":
            contract = json.loads((output / "base-materials.json").read_bytes())["contract"]
            candidate = build_file_model(contract=contract,
                before=json.loads((parent / "before.json").read_bytes()),
                after=json.loads((parent / "after.json").read_bytes()),
                metrics=candidate["supplied_metrics"], case_id=candidate["case_id"])
        elif damage == "candidate_changed":
            candidate["evaluation"]["evaluation_passed"] = False
        elif damage == "candidate_case_id":
            candidate["case_id"] = "a-different-fault"
        else:
            first_metric = next(iter(candidate["supplied_metrics"]["1"].values()))
            first_metric["numerator"] += 1
        raw = wire(candidate)
        (parent / "candidate.json").write_bytes(raw)
        for pin in report["artifact_pins"]:
            if pin["relative_path"] == case_id + "/candidate.json":
                pin.update(bytes=len(raw), sha256=sha(raw))
    elif damage == "wrong_contract_head":
        base = json.loads((output / "base-materials.json").read_bytes())
        base["contract"]["head"]["generation"] += 1
        (output / "base-materials.json").write_bytes(wire(base))
    else:
        bundle = artifact_root / evidence.FAULT_CASES[0] / "bundle"
        detached = tmp_path / "detached-bundle"
        bundle.rename(detached)
        bundle.symlink_to(detached, target_is_directory=True)
    with pytest.raises((ValueError, OSError)):
        evidence._fault_artifacts("authored-fault-report.json", report, output)


def test_finalizer_rejects_producer_drift_before_publication(authored_result, monkeypatch):
    import finalize_stage
    import run_process
    args = SimpleNamespace(run="authored-run", regression="authored-tests", fault="authored-fault", cold="authored-cold")
    expected = [{"path": "/authored/public-producer.py", "bytes": 12, "sha256": "a" * 64}]
    retained = {args.run + "/result.json": authored_result,
        args.run + "-process-report.json": {}, args.regression + "-process-report.json": {},
        args.fault + "-fault-report.json": {}, args.fault + "-process-report.json": {},
        args.cold + "-cold-report.json": {}, args.cold + "-process-report.json": {"after": expected}}
    monkeypatch.setattr(finalize_stage, "read", lambda path, maximum=0: wire(
        retained[Path(path).relative_to(ROOT).as_posix()]))
    monkeypatch.setattr(evidence, "artifact_check", lambda *a, **k: {})
    monkeypatch.setattr(run_process, "selected", lambda: [{**expected[0], "sha256": "b" * 64}])
    monkeypatch.setattr(finalize_stage, "write", lambda *a, **k: pytest.fail("drift must refuse before publication"))
    with pytest.raises(ValueError, match="current producers differ"):
        finalize_stage.finalize(args)
