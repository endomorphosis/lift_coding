"""Authored predicate fixtures and source-binding refusal tests."""
import copy
from fractions import Fraction
import hashlib
import json
from pathlib import Path

import pytest

import scheduler_constraints as sc


H = Path("/home/barberb/lift_coding/maintenance/terminal-intent-coverage-20261015-01/experiment-02")


@pytest.fixture(scope="module")
def inputs():
    instruction = (H / "instructions/llm-inference-batching-scheduler/instruction.md").read_bytes()
    head = json.loads((H / "structural-report.json").read_bytes())["head"]
    rows = []
    for path in sorted(sc.SOURCE_PATHS):
        raw = (H / "source-repository" / path).read_bytes()
        rows.append({"path": path, "source_text": raw.decode("utf-8"),
                     "sha256": hashlib.sha256(raw).hexdigest()})
    return instruction, head, rows


@pytest.fixture(scope="module")
def contract(inputs):
    instruction, head, rows = inputs
    return sc.build_scheduler_contract(instruction=instruction, head=head, source_records=rows)


def test_contract_replays_full_exact_inputs(inputs, contract):
    instruction, head, rows = inputs
    assert sc.validate_scheduler_contract(contract, instruction=instruction, head=head, source_records=rows)
    assert contract["instruction"]["source_text"].encode() == instruction
    assert sum(len(row["source_text"].encode()) for row in contract["sources"]) == 15788
    assert contract["head"] == head
    assert not any(contract["claims"].values())


def test_clause_utf8_offsets_and_spans_are_exact(contract):
    instruction = contract["instruction"]["source_text"].encode()
    positions = {
        "scheduler.exact_once": (1588, 1667),
        "scheduler.shape_alignment": (1672, 1820),
        "scheduler.global_shape_cap": (1825, 1918),
        "scheduler.batch_shape_equality": (1923, 1987),
        "scheduler.thresholds.bucket_1": (3631, 3711),
        "scheduler.thresholds.bucket_2": (3712, 3791),
        "scheduler.input_unchanged": (4068, 4188),
    }
    for clause in contract["clauses"]:
        for span in clause["source_spans"]:
            raw = instruction[span["start_byte"]:span["end_byte"]]
            assert raw.decode() == span["text"]
            assert hashlib.sha256(raw).hexdigest() == span["sha256"]
            assert instruction[:span["start_byte"]].count(b"\n") + 1 == span["start_line"]
        if clause["requirement_id"] in positions:
            span = clause["source_spans"][-1]
            assert (span["start_byte"], span["end_byte"]) == positions[clause["requirement_id"]]


def test_thresholds_are_exact_decimal_rationals(contract):
    clauses = {row["requirement_id"]: row for row in contract["clauses"]}
    b1 = clauses["scheduler.thresholds.bucket_1"]["parameters"]
    b2 = clauses["scheduler.thresholds.bucket_2"]["parameters"]
    assert b1["comparison"] == b2["comparison"] == "strict_lt"
    assert b1["metrics"]["pad_ratio"] == {"numerator": 11, "denominator": 200, "lexeme": "0.055"}
    assert b2["metrics"]["pad_ratio"] == {"numerator": 3, "denominator": 20, "lexeme": "0.15"}
    assert b1["metrics"]["cost"]["numerator"] == 300000000000
    assert b2["metrics"]["cost"]["numerator"] == 48000000000


def test_source_ast_spans_are_syntax_only(contract):
    sources = {row["path"]: row for row in contract["sources"]}
    for row in contract["source_facts"]:
        body = sources[row["path"]]["source_text"].encode()
        assert body[row["start_byte"]:row["end_byte"]].decode() == row["source_text"]
        assert row["authority"] == "syntax_observation_only"
    functions = {row["function"]: row for row in contract["source_facts"]}
    assert (functions["align"]["start_byte"], functions["align"]["end_byte"]) == (722, 789)
    assert (functions["_sum_sq_arith"]["start_byte"], functions["_sum_sq_arith"]["end_byte"]) == (2007, 2106)


@pytest.mark.parametrize("descriptor", sc.authored_cases(), ids=lambda d: d["case"]["case_id"])
def test_authored_finite_case_and_replay(contract, descriptor):
    case = descriptor["case"]
    report = sc.evaluate_case(contract, case)
    assert report["evaluation_passed"] is descriptor["expected_pass"]
    ids = {row["requirement_id"] for row in report["violations"]}
    assert set(descriptor["intended_violation_ids"]) <= ids
    assert all(row["source_spans"] for row in report["violations"])
    assert not any(report["claims"].values())
    assert sc.validate_case_evaluation(report, contract=contract, case=case)


@pytest.mark.parametrize("change", [
    lambda r: r.update(extra=True),
    lambda r: r["claims"].update(full_task_satisfaction_proved=True),
    lambda r: r["instruction"].update(source_text=r["instruction"]["source_text"][:-1]),
    lambda r: r["head"].update(generation=r["head"]["generation"] + 1),
    lambda r: r["clauses"][0]["source_spans"][0].update(start_byte=0),
    lambda r: r["clauses"][1]["parameters"].update(granularity=32),
    lambda r: r["sources"][0].update(source_text=r["sources"][0]["source_text"] + "\n"),
    lambda r: r["assumptions"].clear(),
    lambda r: r["source_facts"].clear(),
])
def test_contract_mutation_is_not_authority(inputs, contract, change):
    instruction, head, sources = inputs
    changed = copy.deepcopy(contract)
    change(changed)
    with pytest.raises(ValueError):
        sc.validate_scheduler_contract(changed, instruction=instruction, head=head, source_records=sources)


def test_incomplete_or_modified_instruction_refused(inputs):
    instruction, head, sources = inputs
    for altered in (instruction[:-1], instruction + b" ", instruction.replace(b"0.055", b"0.056")):
        with pytest.raises(ValueError):
            sc.build_scheduler_contract(instruction=altered, head=head, source_records=sources)


@pytest.mark.parametrize("damage", ["bool_generation", "float_generation", "unknown_field", "missing_field"])
def test_native_head_exact_schema_and_numeric_types_required(inputs, damage):
    instruction, head, sources = inputs
    changed = copy.deepcopy(head)
    if damage == "bool_generation":
        changed["generation"] = True
    elif damage == "float_generation":
        changed["generation"] = 1.0
    elif damage == "unknown_field":
        changed["promoted_authority"] = True
    else:
        changed.pop("receipt_cid")
    with pytest.raises(ValueError):
        sc.build_scheduler_contract(instruction=instruction, head=changed, source_records=sources)


def test_source_omission_and_duplicate_refused(inputs):
    instruction, head, sources = inputs
    for altered in (sources[:-1], sources[:-1] + [sources[0]]):
        with pytest.raises(ValueError):
            sc.build_scheduler_contract(instruction=instruction, head=head, source_records=altered)


def test_source_sha_mismatch_refused(inputs):
    instruction, head, sources = inputs
    changed = copy.deepcopy(sources)
    changed[0]["source_text"] += "\n"
    with pytest.raises(ValueError):
        sc.build_scheduler_contract(instruction=instruction, head=head, source_records=changed)


def test_audited_scheduler_revision_cannot_be_silently_changed(inputs):
    instruction, head, sources = inputs
    changed = copy.deepcopy(sources)
    row = next(row for row in changed if row["path"].endswith("cost_model.py"))
    row["source_text"] += "\n"
    row["sha256"] = hashlib.sha256(row["source_text"].encode()).hexdigest()
    with pytest.raises(ValueError):
        sc.build_scheduler_contract(instruction=instruction, head=head, source_records=changed)


def test_report_forgery_rejected(contract):
    case = next(d["case"] for d in sc.authored_cases() if d["case"]["case_id"] == "missing-output")
    report = sc.evaluate_case(contract, case)
    report["evaluation_passed"] = True
    report["violations"] = []
    with pytest.raises(ValueError):
        sc.validate_case_evaluation(report, contract=contract, case=case)


def test_source_or_case_binding_cannot_be_reused(contract):
    case = sc.authored_cases()[0]["case"]
    report = sc.evaluate_case(contract, case)
    changed = copy.deepcopy(case)
    changed["case_id"] += "-different"
    with pytest.raises(ValueError):
        sc.validate_case_evaluation(report, contract=contract, case=changed)


@pytest.mark.parametrize("bad", [1.0, float("inf"), float("nan"), "64", None, True, -1, sc.MAX_INTEGER + 1])
def test_length_domain_is_exact_bounded_nonboolean_nat(contract, bad):
    case = sc.authored_cases()[0]["case"]
    case["buckets"][0]["requests"][0]["prompt_len"] = bad
    assert sc.evaluate_case(contract, case)["evaluation_passed"] is False


def test_unicode_observed_input_bytes_are_not_normalized(contract):
    case = sc.authored_cases()[0]["case"]
    case["buckets"][0]["input_before"] = "é\n"
    case["buckets"][0]["input_after"] = "e\u0301\n"
    report = sc.evaluate_case(contract, case)
    assert any(v["requirement_id"] == "scheduler.input_unchanged" for v in report["violations"])


def test_utf8_input_bound_is_not_character_count(contract):
    case = sc.authored_cases()[0]["case"]
    case["buckets"][0]["input_before"] = case["buckets"][0]["input_after"] = "é" * 40000
    report = sc.evaluate_case(contract, case)
    assert not report["evaluation_passed"]


def test_bucket_qualified_request_and_batch_identifiers_are_explicit(contract):
    case = sc.authored_cases()[0]["case"]
    for bucket in case["buckets"]:
        bucket["requests"][0]["request_id"] = bucket["plan"][0]["request_id"] = "same-id"
        bucket["plan"][0]["batch_id"] = "same-batch"
    assert sc.evaluate_case(contract, case)["evaluation_passed"]
    assert any("bucket_id, request_id" in a for a in contract["assumptions"])
    assert any("bucket_id, batch_id" in a for a in contract["assumptions"])


def test_fraction_cross_multiplication_retains_strict_boundary(contract):
    case = sc.authored_cases()[0]["case"]
    # Non-reduced rationals preserve the same equality, hence still fail strict <.
    case["buckets"][0]["metrics"]["pad_ratio"] = {"numerator": 22, "denominator": 400}
    report = sc.evaluate_case(contract, case)
    assert any(v["code"] == "not_strictly_below_threshold" for v in report["violations"])
    case["buckets"][0]["metrics"]["pad_ratio"] = {"numerator": 54999999, "denominator": 1000000000}
    assert Fraction(54999999, 1000000000) < Fraction(11, 200)
    assert sc.evaluate_case(contract, case)["evaluation_passed"]


@pytest.mark.parametrize("lexeme", ["NaN", "Infinity", "1e99", "1e-99", "-1", "0x10", "1_000", "1." , "1e999999"])
def test_decimal_parser_rejects_unbounded_or_nonfinite_lexemes(lexeme):
    with pytest.raises(ValueError):
        sc._decimal_rational(lexeme)
