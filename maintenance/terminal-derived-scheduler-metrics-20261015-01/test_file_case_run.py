"""Authored-file run joins, replay, and refusal against forged evidence."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import tempfile

import pytest

import file_case_run as runner
from jsonl_io import ROOT, CONSTRAINT
from observed_files import FILE_PATHS, observe_bundle
import scheduler_constraints as sc


@pytest.fixture(scope="module")
def contract():
    return json.loads((CONSTRAINT / "experiment-01/scheduler-contract.json").read_bytes())


@pytest.fixture(scope="module")
def evidence(contract):
    with tempfile.TemporaryDirectory(prefix="test-file-case-run-", dir=ROOT) as owned:
        output = Path(owned) / "file-cases"
        report = runner.run_file_cases(output=output, contract=contract)
        yield output, report


def _validate(report, output, contract):
    return runner.validate_file_case_run(report, output=output, contract=contract)


def test_all_thirty_authored_outcomes_and_sixteen_derived_cases_replay(contract, evidence):
    output, report = evidence
    assert report["counts"] == {"total": 30, "accepted": 7, "model_refusal": 9,
                                 "file_refusal": 14, "derived_cases": 16}
    assert not any(report["claims"].values())
    assert _validate(report, output, contract) == report
    models = [entry for entry in report["entries"] if entry["model"] is not None]
    assert len(models) == 16
    assert all(entry["outcome"] != "file_refusal" for entry in models)
    assert [item["case"] for item in report["derived_cases"]] == [item["model"]["case"] for item in models]
    for entry in report["entries"]:
        assert entry["outcome"] == entry["spec"]["expected_outcome"]
        if entry["model"] is None:
            assert set(entry["error"]) == {"class", "message"}
        else:
            ids = {v["requirement_id"] for v in entry["model"]["evaluation"]["violations"]}
            assert set(entry["spec"]["intended_violation_ids"]) <= ids


def test_cold_replay_neither_creates_files_nor_repeats_mutation(contract, evidence, monkeypatch):
    output, report = evidence
    leaves = [output / entry["spec"]["case_id"] / path for entry in report["entries"] for path in FILE_PATHS]
    before = [(path.read_bytes(), path.stat().st_ino, path.stat().st_mtime_ns) for path in leaves]
    def refused(*args, **kwargs):
        raise AssertionError("cold replay attempted to create or mutate a fixture")
    monkeypatch.setattr(runner, "create_bundle", refused)
    monkeypatch.setattr(runner, "mutate_between_observations", refused)
    _validate(report, output, contract)
    assert [(path.read_bytes(), path.stat().st_ino, path.stat().st_mtime_ns) for path in leaves] == before


@pytest.mark.parametrize("damage", [
    lambda r: r["entries"].pop(),
    lambda r: r["entries"].append(copy.deepcopy(r["entries"][0])),
    lambda r: r["entries"].reverse(),
    lambda r: r["entries"][0]["spec"].update(expected_outcome="model_refusal"),
    lambda r: r["entries"][0]["spec"]["case"]["buckets"][0]["requests"][0].update(prompt_len=0),
    lambda r: r["entries"][0]["fixture"]["initial_payloads"][FILE_PATHS[0]].update(sha256="0" * 64),
    lambda r: r["entries"][0].update(outcome="file_refusal"),
    lambda r: r["entries"][0]["model"].update(head_sha256="0" * 64),
    lambda r: r["entries"][0]["model"]["evaluation"].update(evaluation_passed=False),
    lambda r: r["derived_cases"][0].update(expected_pass=False),
    lambda r: r["derived_cases"].pop(),
    lambda r: r["counts"].update(accepted=8),
    lambda r: r["claims"].update(metrics_are_runtime_observations=True),
    lambda r: r["head"].update(generation=r["head"]["generation"] + 1),
    lambda r: r.update(unknown=True),
])
def test_forged_report_fields_cannot_be_rehashed_into_evidence(contract, evidence, damage):
    output, original = evidence
    changed = copy.deepcopy(original)
    damage(changed)
    with pytest.raises(ValueError):
        _validate(changed, output, contract)


def test_recomputed_valid_model_and_case_hashes_still_need_original_file_rows(contract, evidence):
    output, original = evidence
    changed = copy.deepcopy(original)
    model = changed["entries"][0]["model"]
    model["case"]["buckets"][0]["requests"][0]["prompt_len"] = 0
    model["evaluation"] = sc.evaluate_case(contract, model["case"])
    assert model["evaluation"]["evaluation_passed"] is True
    changed["derived_cases"][0]["case"] = copy.deepcopy(model["case"])
    with pytest.raises(ValueError):
        _validate(changed, output, contract)


def test_consistently_rehashed_observation_payloads_still_need_authored_recipe(contract, evidence):
    output, original = evidence
    changed = copy.deepcopy(original)
    entry = changed["entries"][0]
    for phase in ("before", "after"):
        record = entry[phase]["files"][FILE_PATHS[0]]
        raw = base64.b64decode(record["payload_b64"])
        raw = raw.replace(b'"prompt_len":64', b'"prompt_len":32')
        record["payload_b64"] = base64.b64encode(raw).decode("ascii")
        record["sha256"] = hashlib.sha256(raw).hexdigest()
        record["bytes"] = len(raw)
        record["identity"]["size"] = len(raw)
    # Matching serialized payload hashes are historical data, not the fixture recipe.
    with pytest.raises(ValueError):
        _validate(changed, output, contract)


def test_rehashed_historical_generation_cannot_replace_current_custody(contract, evidence):
    output, original = evidence
    changed = copy.deepcopy(original)
    entry = changed["entries"][0]
    for phase in ("before", "after"):
        entry[phase]["files"][FILE_PATHS[0]]["identity"]["inode"] += 100
    # Rebuild all pure model hashes; actual final descriptor custody still differs.
    model, outcome, error = runner._evaluate(contract=contract, before=entry["before"],
                                           after=entry["after"], spec=entry["spec"])
    entry.update(model=model, outcome=outcome, error=error)
    changed["derived_cases"][0]["case"] = copy.deepcopy(model["case"])
    with pytest.raises(ValueError):
        _validate(changed, output, contract)


@pytest.mark.parametrize("damage", ["missing_leaf", "same_byte_replace", "changed_leaf", "extra_leaf", "missing_case"])
def test_current_retained_artifacts_must_still_match_final_observations(contract, damage):
    with tempfile.TemporaryDirectory(prefix="test-file-case-fault-", dir=ROOT) as owned:
        output = Path(owned) / "file-cases"
        report = runner.run_file_cases(output=output, contract=contract)
        case_root = output / report["entries"][0]["spec"]["case_id"]
        path = case_root / FILE_PATHS[0]
        if damage == "missing_leaf":
            path.unlink()
        elif damage == "same_byte_replace":
            raw = path.read_bytes()
            temporary = path.with_name("replacement.jsonl")
            temporary.write_bytes(raw)
            temporary.replace(path)
        elif damage == "changed_leaf":
            path.write_bytes(b" " + path.read_bytes())
        elif damage == "extra_leaf":
            (case_root / "input_data/extra.jsonl").write_bytes(b"")
        else:
            case_root.rename(output / "renamed-case")
        with pytest.raises(ValueError):
            _validate(report, output, contract)


def test_invalid_source_contract_refused_before_output_creation(contract):
    with tempfile.TemporaryDirectory(prefix="test-file-case-contract-", dir=ROOT) as owned:
        output = Path(owned) / "file-cases"
        changed = copy.deepcopy(contract)
        changed["instruction"]["source_text"] += " "
        with pytest.raises(ValueError):
            runner.run_file_cases(output=output, contract=changed)
        assert not output.exists()


def test_refusal_error_and_intended_clause_evidence_are_exact(contract, evidence):
    output, original = evidence
    changed = copy.deepcopy(original)
    entry = next(entry for entry in changed["entries"] if entry["outcome"] == "file_refusal")
    entry["error"]["message"] += " changed"
    with pytest.raises(ValueError):
        _validate(changed, output, contract)
    changed = copy.deepcopy(original)
    entry = next(entry for entry in changed["entries"] if entry["outcome"] == "model_refusal")
    entry["model"]["evaluation"]["violations"].clear()
    with pytest.raises(ValueError):
        _validate(changed, output, contract)
