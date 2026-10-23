"""Observed JSONL rows must determine metrics and every retained model alias.

These fixtures use the selected public cost source and an historical candidate
contract.  They do not execute repository source or claim a current native
owner, compiler invocation, supervised task, or runtime metric observation.
"""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path

import pytest

import jsonl_cases
import source_metric_cases as cases
from file_model_bridge import build_file_model
from jsonl_io import ROOT, read, sha, wire
from observed_files import FILE_PATHS, observe_bundle, reobserve_bundle
from source_metric_bridge import (CLAIMS, SOURCE_PATH, DerivedMetricModelError,
    binary64_threshold_gate, build_derived_file_model, validate_derived_file_model)
from source_profile import build_source_profile
from strict_jsonl import parse_jsonl


def fraction(row):
    return Fraction(row["numerator"], row["denominator"])


@pytest.fixture(scope="module")
def context():
    contract = json.loads(read(ROOT.parent / "terminal-typed-constraints-20261015-01"
                               / "experiment-01/scheduler-contract.json", 1024**2))
    raw = read(ROOT.parent / "terminal-lean-jsonl-decoder-20261015-01"
               / "experiment-01/source-repository" / SOURCE_PATH, 8192)
    profile = build_source_profile(raw, source_path=SOURCE_PATH, head=contract["head"])
    return {"contract": contract, "source_profile": profile, "source_raw": raw}


@pytest.fixture(scope="module", autouse=True)
def owned_temporary_root(tmp_path_factory):
    # All fixtures remain in this process's owned pytest tree.
    root = tmp_path_factory.getbasetemp()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(cases, "ROOT", root)
        patch.setattr(jsonl_cases, "ROOT", root)
        yield root


@pytest.fixture(scope="module")
def complete_report(context, tmp_path_factory):
    output = tmp_path_factory.mktemp("source-metric-complete") / "metric-files"
    report = cases.run_metric_cases(output=output, **context)
    return output, report


@pytest.fixture
def bracket(context, tmp_path):
    spec = deepcopy(next(item for item in cases.metric_specs()
                         if item["case_id"] == "metrics-valid-minimal"))
    output = tmp_path / "bundle"
    jsonl_cases.create_bundle(destination=output, spec=spec)
    before, after = observe_bundle(root=output), observe_bundle(root=output)
    arguments = {**context, "before": before, "after": after, "case_id": spec["case_id"]}
    return output, spec, arguments, build_derived_file_model(**arguments)


def test_actual_bytes_determine_requests_plans_metrics_and_finite_model(bracket):
    output, spec, arguments, report = bracket
    assert validate_derived_file_model(report, **arguments) is report
    assert reobserve_bundle(arguments["after"], root=output)
    for number in (1, 2):
        request_path = f"input_data/requests_bucket_{number}.jsonl"
        plan_path = f"output_data/plan_b{number}.jsonl"
        requests = parse_jsonl((output / request_path).read_bytes(), kind="requests")["rows"]
        plans = parse_jsonl((output / plan_path).read_bytes(), kind="plan")["rows"]
        derived = report["derivations"][str(number)]
        assert derived["request_rows_sha256"] == sha(wire(requests))
        assert derived["plan_rows_sha256"] == sha(wire(plans))
        model = report["file_model"]["case"]["buckets"][number - 1]
        assert model["requests"] == requests and model["plan"] == plans
        assert report["derived_metrics"][str(number)] == derived["exact_rational_metrics"]
        assert report["file_model"]["supplied_metrics"][str(number)] == derived["exact_rational_metrics"]
    assert report["accepted"] is True and report["rational_model_passed"] is True
    assert report["caller_supplied_metrics_accepted"] is False


def test_no_api_path_accepts_caller_supplied_metrics(bracket):
    _, _, arguments, report = bracket
    with pytest.raises(TypeError, match="metrics"):
        build_derived_file_model(**arguments, metrics={"1": {}, "2": {}})
    with pytest.raises(TypeError, match="metrics"):
        validate_derived_file_model(report, **arguments, metrics={"1": {}, "2": {}})


def test_legacy_authored_metric_values_cannot_influence_file_derivation(bracket):
    _, spec, arguments, report = bracket
    original_payloads = jsonl_cases.fixture_payloads(spec)
    for metrics in spec["metrics"].values():
        for metric in metrics.values():
            metric.update(numerator=10**18, denominator=1)
    assert jsonl_cases.fixture_payloads(spec) == original_payloads
    assert build_derived_file_model(**arguments)["derived_metrics"] == report["derived_metrics"]


@pytest.mark.parametrize("damage", ["input_bytes", "plan_bytes", "same_byte_replacement"])
def test_bridge_refuses_actual_changes_inside_validation_bracket(bracket, tmp_path, damage):
    output, _, arguments, _ = bracket
    leaf = output / FILE_PATHS[2 if damage == "plan_bytes" else 0]
    if damage == "same_byte_replacement":
        replacement = tmp_path / "replacement"
        replacement.write_bytes(leaf.read_bytes())
        replacement.replace(leaf)
    else:
        leaf.write_bytes(leaf.read_bytes().rstrip(b"\n") + b" \n")
    arguments = {**arguments, "after": observe_bundle(root=output)}
    with pytest.raises(DerivedMetricModelError, match="stable four-file observation bracket"):
        build_derived_file_model(**arguments)


@pytest.mark.parametrize("bucket,label,expected", [
    (1, "below", Fraction(10, 201)), (1, "equal", Fraction(11, 200)),
    (1, "above", Fraction(12, 199)), (2, "below", Fraction(23, 161)),
    (2, "equal", Fraction(3, 20)), (2, "above", Fraction(25, 159)),
])
def test_actual_padding_threshold_boundary_is_strict(complete_report, bucket, label, expected):
    _, report = complete_report
    entry = next(item for item in report["entries"]
                 if item["case_id"] == f"metrics-bucket{bucket}-padding-{label}")
    bridge = entry["bridge"]
    observed = bridge["derivations"][str(bucket)]
    assert fraction(observed["exact_rational_metrics"]["pad_ratio"]) == expected
    check = next(item for item in bridge["binary64_gate"]["checks"]
                 if item["bucket_id"] == bucket and item["metric"] == "pad_ratio")
    passed = label == "below"
    assert check["rational_threshold_passed"] is passed
    assert check["binary64_threshold_passed"] is passed
    assert check["interpretations_agree"] is True
    assert bridge["accepted"] is passed
    assert entry["outcome"] == ("accepted" if passed else "model_refusal")


def test_binary64_equality_uses_source_threshold_literal(complete_report):
    _, report = complete_report
    entry = next(item for item in report["entries"]
                 if item["case_id"] == "metrics-bucket2-padding-equal")
    bridge = entry["bridge"]
    floating_pad = bridge["derivations"]["2"]["binary64_metrics"]["pad_ratio"]
    # Comparing the runtime-style quotient against an ideal 3/20 would be wrong:
    # both source expressions round to the same binary64 value, so strict < fails.
    assert fraction(floating_pad) < Fraction(3, 20)
    check = next(item for item in bridge["binary64_gate"]["checks"]
                 if item["bucket_id"] == 2 and item["metric"] == "pad_ratio")
    assert fraction(floating_pad) == fraction(check["binary64_threshold_ratio"])
    assert check["binary64_threshold_hex"] == float(0.15).hex()
    assert check["binary64_threshold_passed"] is False


def test_synthetic_gate_probe_keeps_disagreement_separate_from_proof(bracket):
    _, _, arguments, report = bracket
    derivations = deepcopy(report["derivations"])
    item = derivations["2"]
    below = Fraction(3, 20) - Fraction(1, 10**6)
    item["exact_rational_metrics"]["pad_ratio"] = {
        "numerator": below.numerator, "denominator": below.denominator}
    numerator, denominator = float(0.15).as_integer_ratio()
    item["binary64_metrics"]["pad_ratio"] = {
        "numerator": numerator, "denominator": denominator, "hex": float(0.15).hex()}
    gate = binary64_threshold_gate(arguments["contract"], derivations)
    check = next(row for row in gate["checks"] if row["bucket_id"] == 2 and row["metric"] == "pad_ratio")
    assert check["rational_threshold_passed"] is True
    assert check["binary64_threshold_passed"] is False
    assert gate["all_threshold_interpretations_agree"] is False
    assert gate["all_thresholds_passed"] is False
    assert gate["source_execution_or_kernel_proof"] is False
    changed = deepcopy(report)
    changed["derivations"], changed["binary64_gate"] = derivations, gate
    with pytest.raises(ValueError):
        validate_derived_file_model(changed, **arguments)


@pytest.mark.parametrize("damage", ["raw", "profile_constant", "profile_head", "contract_head"])
def test_external_source_profile_and_head_forgery_is_refused(bracket, damage):
    _, _, arguments, _ = bracket
    changed = deepcopy(arguments)
    if damage == "raw":
        raw = changed["source_raw"]
        changed["source_raw"] = raw[:-1] + bytes([raw[-1] ^ 1])
    elif damage == "profile_constant":
        changed["source_profile"]["constants"]["Tp_attn"]["binary64_hex"] = float(0.0).hex()
    elif damage == "profile_head":
        changed["source_profile"]["head"]["generation"] += 1
    else:
        changed["contract"]["head"]["generation"] += 1
    with pytest.raises(ValueError):
        build_derived_file_model(**changed)


@pytest.mark.parametrize("path", [
    ("source_profile_sha256",), ("contract_sha256",), ("before_sha256",), ("after_sha256",),
    ("derivations", "1", "request_rows_sha256"),
    ("derivations", "1", "exact_rational_metrics", "cost", "numerator"),
    ("derivations", "1", "binary64_metrics", "cost", "numerator"),
    ("derivations", "1", "batches", 0, "S_max"),
    ("derived_metrics", "1", "cost", "numerator"),
    ("file_model", "case", "buckets", 0, "metrics", "cost", "numerator"),
    ("file_model", "supplied_metrics", "1", "cost", "numerator"),
])
def test_all_derived_aliases_are_rebuilt_from_exact_file_rows(bracket, path):
    _, _, arguments, report = bracket
    changed = deepcopy(report)
    item = changed
    for key in path[:-1]:
        item = item[key]
    value = item[path[-1]]
    item[path[-1]] = value + 1 if type(value) is int else "0" * 64
    with pytest.raises(ValueError):
        validate_derived_file_model(changed, **arguments)


def test_consistently_injected_zero_metrics_cannot_replace_derived_costs(bracket):
    _, _, arguments, report = bracket
    changed = deepcopy(report)
    zeros = {bucket: {metric: {"numerator": 0, "denominator": 1}
                      for metric in values} for bucket, values in report["derived_metrics"].items()}
    forged_model = build_file_model(contract=arguments["contract"], before=arguments["before"],
        after=arguments["after"], metrics=zeros, case_id=arguments["case_id"])
    assert forged_model["evaluation"]["evaluation_passed"] is True
    changed["derived_metrics"], changed["file_model"] = deepcopy(zeros), forged_model
    for bucket, values in zeros.items():
        changed["derivations"][bucket]["exact_rational_metrics"] = deepcopy(values)
    with pytest.raises(ValueError):
        validate_derived_file_model(changed, **arguments)


def test_binary64_gate_rejects_inconsistent_exact_float_ratio(bracket):
    _, _, arguments, report = bracket
    forged = deepcopy(report["derivations"])
    forged["1"]["binary64_metrics"]["cost"]["numerator"] += 1
    with pytest.raises(DerivedMetricModelError, match="binary64 shadow binding"):
        binary64_threshold_gate(arguments["contract"], forged)


def test_complete_33_case_data_and_actual_current_replay(complete_report, context):
    output, report = complete_report
    assert cases.validate_metric_case_data(report) is report
    assert cases.validate_metric_cases(report, output=output, **context) is report
    assert report["summary"] == cases.METRIC_COUNTS
    assert len(report["entries"]) == 33
    assert sum(entry["model"] is not None for entry in report["entries"]) == 29


@pytest.mark.parametrize("name,needle", [
    ("extra-output", "unknown request_id"),
    ("unsupported-prompt-bound", "prompt_len"),
    ("unsupported-generation-bound", "gen_len"),
    ("unsupported-sequence-bound", "seq_align"),
])
def test_actual_unknown_references_and_profile_bounds_stay_unmodeled(complete_report, name, needle):
    _, report = complete_report
    entry = next(row for row in report["entries"] if row["case_id"] == "metrics-" + name)
    assert entry["outcome"] == "metric_refusal"
    assert entry["error"]["class"] == "MetricDerivationError"
    assert needle in entry["error"]["message"]
    assert entry["bridge"] is None and entry["model"] is None and entry["derived_metrics"] is None


@pytest.mark.parametrize("damage", ["drop", "reorder", "recipe", "summary", "error", "source",
    "profile", "head", "caller_metrics", "claim", "unknown_field", "model"])
def test_complete_metric_report_cannot_be_resigned_with_changed_bindings(complete_report, damage):
    _, original = complete_report
    report = deepcopy(original)
    if damage == "drop":
        report["entries"].pop()
    elif damage == "reorder":
        report["entries"].reverse()
    elif damage == "recipe":
        report["entries"][0]["spec"]["case"]["buckets"][0]["requests"][0]["prompt_len"] += 1
    elif damage == "summary":
        report["summary"]["accepted"] += 1
    elif damage == "error":
        next(entry for entry in report["entries"] if entry["outcome"] == "metric_refusal")["error"]["message"] = "forged"
    elif damage == "source":
        report["source_raw_hex"] = report["source_raw_hex"][:-2] + "00"
    elif damage == "profile":
        report["source_profile"]["defaults"]["granularity"] = 32
        report["source_profile_sha256"] = sha(wire(report["source_profile"]))
    elif damage == "head":
        report["head"]["generation"] += 1
    elif damage == "caller_metrics":
        report["caller_supplied_metrics_accepted"] = True
    elif damage == "claim":
        report["claims"]["source_runtime_equivalence_proved"] = True
    elif damage == "unknown_field":
        report["proof_cache_admission"] = True
    else:
        report["entries"][0]["model"]["evaluation"]["evaluation_passed"] = False
    with pytest.raises((ValueError, TypeError, KeyError)):
        cases.validate_metric_case_data(report)


@pytest.mark.parametrize("case_name", ["extra-output", "unsupported-prompt-bound",
    "unsupported-generation-bound", "unsupported-sequence-bound"])
def test_refused_case_still_requires_stable_before_after_custody(complete_report, context, case_name):
    _, original = complete_report
    report = deepcopy(original)
    entry = next(item for item in report["entries"] if item["case_id"] == "metrics-" + case_name)
    entry["before"]["files"][FILE_PATHS[0]]["identity"]["mtime_ns"] += 1
    # Re-sign the error produced by the unstable bracket.  A refusal receipt is
    # still invalid evidence when its byte-identical file generations disagree.
    rebound = cases._evaluate(spec=entry["spec"], before=entry["before"], after=entry["after"], **context)
    assert rebound["outcome"] == "metric_refusal"
    entry.update(rebound)
    with pytest.raises(ValueError, match="stable|generation|custody"):
        cases.validate_metric_case_data(report)


@pytest.mark.parametrize("damage", ["bytes", "same_byte_replacement", "missing_case",
    "extra_case", "missing_file", "symlink_case"])
def test_current_file_replay_refuses_actual_generation_or_inventory_change(context, tmp_path, damage):
    output = tmp_path / "metric-files"
    report = cases.run_metric_cases(output=output, **context)
    cases.validate_metric_cases(report, output=output, **context)
    entry = report["entries"][0]
    bundle = output / entry["case_id"]
    leaf = bundle / FILE_PATHS[0]
    if damage == "bytes":
        leaf.write_bytes(leaf.read_bytes().rstrip(b"\n") + b" \n")
    elif damage == "same_byte_replacement":
        temporary = tmp_path / "replacement"
        temporary.write_bytes(leaf.read_bytes())
        temporary.replace(leaf)
    elif damage == "missing_case":
        bundle.rename(tmp_path / "detached-case")
    elif damage == "extra_case":
        (output / "unselected").mkdir()
    elif damage == "missing_file":
        leaf.unlink()
    else:
        detached = tmp_path / "detached-case"
        bundle.rename(detached)
        bundle.symlink_to(detached, target_is_directory=True)
    with pytest.raises((ValueError, OSError)):
        cases.validate_metric_cases(report, output=output, **context)


def test_current_replay_never_recreates_files(complete_report, context, monkeypatch):
    output, report = complete_report
    monkeypatch.setattr(cases, "create_bundle", lambda **kwargs: pytest.fail("replay cannot recreate fixtures"))
    monkeypatch.setattr(cases, "observe_bundle", lambda **kwargs: pytest.fail("replay must check retained current generations"))
    assert cases.validate_metric_cases(report, output=output, **context) is report


def test_all_metric_scope_claims_remain_false(complete_report):
    _, report = complete_report
    assert report["caller_supplied_metrics_accepted"] is False
    assert report["claims"] == CLAIMS and all(value is False for value in report["claims"].values())
    assert all(value is False for value in report["source_profile"]["claims"].values())
    for entry in report["entries"]:
        bridge = entry["bridge"]
        if bridge is None:
            continue
        assert bridge["claims"] == CLAIMS
        assert bridge["binary64_gate"]["source_execution_or_kernel_proof"] is False
        for derivation in bridge["derivations"].values():
            assert all(value is False for value in derivation["claims"].values())
