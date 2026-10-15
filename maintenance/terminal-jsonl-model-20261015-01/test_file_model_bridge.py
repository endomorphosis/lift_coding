"""Exact authored-file projection, finite semantics, and replay refusal checks."""
import copy
import hashlib
import json
import os
from pathlib import Path

import pytest

import file_model_bridge as bridge
from observed_files import FILE_PATHS, observe_bundle, reobserve_bundle
import scheduler_constraints as sc


I = Path("/home/barberb/lift_coding/maintenance/terminal-typed-constraints-20261015-01")


@pytest.fixture(scope="module")
def contract():
    # Named predecessor public source contract only; no private database reads.
    return json.loads((I / "experiment-01/scheduler-contract.json").read_bytes())


def _row(raw):
    return json.dumps(raw, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _payloads():
    result = {}
    for bucket in (1, 2):
        rid = f"réq-{bucket}-雪"
        request = {"request_id": rid, "prompt_len": 64 * bucket, "gen_len": 3}
        plan = {"request_id": rid, "batch_id": f"batch-δ-{bucket}",
                "shape": {"seq_align": 64 * bucket, "heads_align": 32, "hidden_align": 4096}}
        result[bridge.BUCKET_PATHS[bucket]["requests"]] = _row(request) + b"\n"
        result[bridge.BUCKET_PATHS[bucket]["plan"]] = _row(plan) + b"\n"
    return result


def _metrics():
    return {str(bucket): {name: {"numerator": 0, "denominator": 1}
                          for name in sc.METRIC_NAMES} for bucket in (1, 2)}


def _files(tmp_path, payloads=None, name="artifacts"):
    root = tmp_path / name
    root.mkdir(mode=0o700)
    for directory in ("input_data", "output_data"):
        (root / directory).mkdir(mode=0o700)
    payloads = _payloads() if payloads is None else payloads
    for path in FILE_PATHS:
        (root / path).write_bytes(payloads[path])
    before = observe_bundle(root=root)
    after = observe_bundle(root=root)
    return root, before, after


def _build(contract, before, after, metrics=None, case_id="authored-files"):
    return bridge.build_file_model(contract=contract, before=before, after=after,
                                   metrics=_metrics() if metrics is None else metrics,
                                   case_id=case_id)


def test_exact_unicode_bytes_derive_rows_and_native_evaluation(contract, tmp_path):
    root, before, after = _files(tmp_path)
    report = _build(contract, before, after)
    assert report["evaluation"]["evaluation_passed"] is True
    assert report["head"] == contract["head"]
    assert report["contract_sha256"] == hashlib.sha256(sc.canonical_bytes(contract)).hexdigest()
    assert report["head_sha256"] == contract["head_sha256"]
    assert bridge.validate_file_model(report, contract=contract, before=before, after=after,
                                     metrics=_metrics(), case_id="authored-files")
    assert not any(report["claims"].values())
    for bucket in report["case"]["buckets"]:
        paths = bridge.BUCKET_PATHS[bucket["bucket_id"]]
        raw = (root / paths["requests"]).read_bytes()
        assert bucket["input_before"].encode("utf-8") == raw
        assert bucket["input_after"].encode("utf-8") == raw
        assert bucket["requests"] == report["projections"]["after"][paths["requests"]]["rows"]
        assert bucket["plan"] == report["projections"]["after"][paths["plan"]]["rows"]
    assert reobserve_bundle(after, root=root)["files"] == after["files"]


@pytest.mark.parametrize("ending", [b"\n", b"\r\n", b""])
def test_jsonl_record_endings_remain_bound_without_minification(contract, tmp_path, ending):
    payloads = {path: b" \t" + raw.rstrip(b"\n") + b" \t" + ending
                for path, raw in _payloads().items()}
    root, before, after = _files(tmp_path, payloads)
    report = _build(contract, before, after)
    assert report["evaluation"]["evaluation_passed"]
    for phase in ("before", "after"):
        for path, projection in report["projections"][phase].items():
            raw = (root / path).read_bytes()
            assert projection["raw_sha256"] == hashlib.sha256(raw).hexdigest()
            record = projection["records"][0]
            assert raw[record["line_span"]["start_byte"]:record["line_span"]["end_byte"]] == raw
            span = record["record_span"]
            expected_record = raw[:-len(ending)] if ending else raw
            assert raw[span["start_byte"]:span["end_byte"]] == expected_record
            assert record["line_ending"] == {b"\n": "lf", b"\r\n": "crlf", b"": "none"}[ending]


@pytest.mark.parametrize("path", FILE_PATHS)
def test_any_file_change_inside_verification_bracket_refused(contract, tmp_path, path):
    root, before, _ = _files(tmp_path)
    target = root / path
    target.write_bytes(b" " + target.read_bytes())
    after = observe_bundle(root=root)
    with pytest.raises(bridge.FileModelError):
        _build(contract, before, after)


@pytest.mark.parametrize("path", FILE_PATHS)
def test_same_bytes_with_new_file_generation_refused(contract, tmp_path, path):
    root, before, _ = _files(tmp_path)
    target = root / path
    previous = target.stat()
    os.utime(target, ns=(previous.st_atime_ns, previous.st_mtime_ns + 1000))
    after = observe_bundle(root=root)
    assert before["files"][path]["sha256"] == after["files"][path]["sha256"]
    with pytest.raises(bridge.FileModelError):
        _build(contract, before, after)


@pytest.mark.parametrize("bad", [b"not json\n", b'{"request_id":"a","prompt_len":true,"gen_len":1}\n',
                                 b'{"request_id":"a","prompt_len":1,"gen_len":1,"extra":0}\n',
                                 b'\xff\n', b'{"request_id":"a","prompt_len":1,"gen_len":1}\n\n'])
def test_malformed_request_artifacts_never_define_a_case(contract, tmp_path, bad):
    payloads = _payloads()
    payloads[bridge.BUCKET_PATHS[1]["requests"]] = bad
    _, before, after = _files(tmp_path, payloads)
    with pytest.raises(ValueError):
        _build(contract, before, after)


def test_valid_jsonl_with_invalid_plan_is_rejected_by_native_predicates(contract, tmp_path):
    payloads = _payloads()
    path = bridge.BUCKET_PATHS[1]["plan"]
    row = json.loads(payloads[path])
    row["shape"]["heads_align"] = 31
    payloads[path] = _row(row) + b"\n"
    _, before, after = _files(tmp_path, payloads)
    report = _build(contract, before, after)
    assert report["evaluation"]["evaluation_passed"] is False
    assert "scheduler.shape_alignment" in {v["requirement_id"] for v in report["evaluation"]["violations"]}
    assert report["case"]["buckets"][0]["plan"][0]["shape"]["heads_align"] == 31


def test_swapped_plan_bucket_payloads_cannot_be_relabelled(contract, tmp_path):
    payloads = _payloads()
    first, second = (bridge.BUCKET_PATHS[b]["plan"] for b in (1, 2))
    payloads[first], payloads[second] = payloads[second], payloads[first]
    _, before, after = _files(tmp_path, payloads)
    report = _build(contract, before, after)
    assert report["evaluation"]["evaluation_passed"] is False
    assert "scheduler.exact_once" in {v["requirement_id"] for v in report["evaluation"]["violations"]}


def test_missing_metric_is_not_defaulted_or_silently_proved(contract, tmp_path):
    _, before, after = _files(tmp_path)
    metrics = _metrics()
    metrics["1"].pop("cost")
    report = _build(contract, before, after, metrics)
    assert report["case"]["buckets"][0]["metrics"] == metrics["1"]
    assert report["evaluation"]["evaluation_passed"] is False
    assert "scheduler.thresholds.bucket_1" in {v["requirement_id"] for v in report["evaluation"]["violations"]}


@pytest.mark.parametrize("metric", sc.METRIC_NAMES)
def test_equal_threshold_supplied_rationals_fail_strict_bound(contract, tmp_path, metric):
    _, before, after = _files(tmp_path)
    metrics = _metrics()
    clause = next(c for c in contract["clauses"] if c["requirement_id"] == "scheduler.thresholds.bucket_1")
    limit = clause["parameters"]["metrics"][metric]
    metrics["1"][metric] = {key: limit[key] for key in ("numerator", "denominator")}
    report = _build(contract, before, after, metrics)
    assert report["evaluation"]["evaluation_passed"] is False
    assert any(v["code"] == "not_strictly_below_threshold" for v in report["evaluation"]["violations"])
    assert report["claims"]["supplied_metrics_are_runtime_observations"] is False


@pytest.mark.parametrize("damage", [
    lambda r: r["case"]["buckets"][0]["requests"][0].update(prompt_len=0),
    lambda r: r["case"]["buckets"][0]["plan"][0].update(request_id="invented"),
    lambda r: r["projections"]["after"][FILE_PATHS[0]]["rows"].clear(),
    lambda r: r["evaluation"].update(evaluation_passed=False),
    lambda r: r["head"].update(generation=r["head"]["generation"] + 1),
    lambda r: r["file_bindings"][FILE_PATHS[0]]["after"]["identity"].update(inode=1),
    lambda r: r["claims"].update(planning_or_dispatch_authority=True),
    lambda r: r.update(expected_pass=True),
])
def test_fabricated_rows_or_evidence_fields_do_not_replay(contract, tmp_path, damage):
    _, before, after = _files(tmp_path)
    report = _build(contract, before, after)
    damage(report)
    with pytest.raises(bridge.FileModelError):
        bridge.validate_file_model(report, contract=contract, before=before, after=after,
                                   metrics=_metrics(), case_id="authored-files")


def test_no_caller_substituted_rows_parameter_exists(contract, tmp_path):
    _, before, after = _files(tmp_path)
    with pytest.raises(TypeError):
        bridge.build_file_model(contract=contract, before=before, after=after,
                                metrics=_metrics(), case_id="authored-files", requests=[], plan=[])


@pytest.mark.parametrize("replacement", ["case_id", "metrics", "head", "files"])
def test_report_cannot_move_to_another_input_binding(contract, tmp_path, replacement):
    root, before, after = _files(tmp_path)
    report = _build(contract, before, after)
    args = dict(contract=contract, before=before, after=after, metrics=_metrics(), case_id="authored-files")
    if replacement == "case_id":
        args["case_id"] = "another-case"
    elif replacement == "metrics":
        args["metrics"]["1"]["cost"]["numerator"] = 1
    elif replacement == "head":
        head = copy.deepcopy(contract["head"])
        head["generation"] += 1
        args["contract"] = sc.build_scheduler_contract(
            instruction=contract["instruction"]["source_text"].encode("utf-8"),
            head=head, source_records=contract["sources"])
    else:
        target = root / bridge.BUCKET_PATHS[1]["requests"]
        target.write_bytes(b" " + target.read_bytes())
        args["before"] = observe_bundle(root=root)
        args["after"] = observe_bundle(root=root)
    with pytest.raises(bridge.FileModelError):
        bridge.validate_file_model(report, **args)


@pytest.mark.parametrize("damage", ["root", "inode", "payload", "unknown_file"])
def test_inconsistent_before_after_observations_refused(contract, tmp_path, damage):
    _, before, after = _files(tmp_path)
    after = copy.deepcopy(after)
    if damage == "root":
        after["root"] += "-substituted"
    elif damage == "inode":
        after["files"][FILE_PATHS[0]]["identity"]["inode"] += 1
    elif damage == "payload":
        after["files"][FILE_PATHS[0]]["payload_b64"] = ""
    else:
        after["files"]["input_data/fabricated.jsonl"] = after["files"][FILE_PATHS[0]]
    with pytest.raises(ValueError):
        _build(contract, before, after)


@pytest.mark.parametrize("metrics", [{}, {"1": {}}, {"1": {}, "2": {}, "3": {}},
                                     {"1": [], "2": {}}, {"1": {"cost": 0.0}, "2": {}}])
def test_metrics_require_explicit_plain_two_bucket_binding(contract, tmp_path, metrics):
    _, before, after = _files(tmp_path)
    with pytest.raises(bridge.FileModelError):
        _build(contract, before, after, metrics)
