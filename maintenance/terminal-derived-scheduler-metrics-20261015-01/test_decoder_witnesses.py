"""Meaningful byte/row/case binding and scope tests for the pure inventory."""
import builtins
import copy
import hashlib
import json
import os
from pathlib import Path

import pytest

import decoder_witnesses as dw


@pytest.fixture(scope="module")
def filecases():
    # Named, sealed, public predecessor evidence; no private stores or inputs.
    path = Path(__file__).resolve().parent.parent / "terminal-jsonl-model-20261015-01" / "experiment-01" / "file-case-report.json"
    return json.loads(path.read_bytes())


@pytest.fixture(scope="module")
def inventory(filecases):
    return dw.build_decoder_witnesses(filecases=filecases)


def test_complete_deduplicated_inventory_and_all_observation_origins(inventory, filecases):
    assert inventory["summary"] == dw.EXPECTED_SUMMARY
    assert dw.validate_decoder_witnesses(inventory, filecases=filecases) == inventory
    witnesses = inventory["witnesses"]
    assert len({(row["kind"], row["raw_hex"]) for row in witnesses}) == 70
    assert len({row["witness_id"] for row in witnesses}) == 70
    origins = [origin for row in witnesses for origin in row["origins"]]
    source = [row for row in origins if row["category"] == "file_case"]
    assert len(source) == 240
    assert len({(row["case_index"], row["phase"], row["path"]) for row in source}) == 240
    assert {row["case_index"] for row in source} == set(range(30))
    assert len([row for row in origins if row["category"] == "authored_grammar_probe"]) == 26


def test_exact_all_derived_case_joins_and_separate_custody_controls(inventory, filecases):
    assert inventory["derived_cases"] == filecases["derived_cases"]
    table = {row["witness_id"]: row for row in inventory["witnesses"]}
    indices = []
    for binding in inventory["case_bindings"]:
        index = binding["derived_case_index"]
        if index is None:
            if binding["category"] == "custody_refusal":
                assert binding["parse_refusal_witness_ids"] == []
            else:
                assert binding["category"] == "parser_refusal"
                assert binding["parse_refusal_witness_ids"]
            continue
        indices.append(index)
        case = inventory["derived_cases"][index]["case"]
        for bucket in case["buckets"]:
            number = bucket["bucket_id"]
            for kind, path in dw.BUCKET_PATHS[number].items():
                witness = table[binding["files"]["after"][path]]
                assert witness["expected_parse_success"] is True
                assert witness["expected_rows"] == [dw._typed_row(row, kind) for row in bucket[kind]]
                for phase in ("before", "after"):
                    assert binding["files"][phase][path] == binding["files"]["after"][path]
    assert indices == list(range(16))


@pytest.mark.parametrize("kind", ["requests", "plan"])
def test_scalar_control_and_supplementary_ids_are_numbers_not_lean_string_literals(inventory, kind):
    def probe(name):
        return next(row for row in inventory["witnesses"] if row["kind"] == kind and
                    {"category": "authored_grammar_probe", "probe_id": kind + "-" + name} in row["origins"])
    controls = probe("escaped-controls")
    assert controls["expected_rows"][0]["request_id"] == [8, 12, 1, 9, 10, 13]
    supplementary = probe("escaped-supplementary")
    assert supplementary["expected_rows"][0]["request_id"] == [0x1F9E0, 0x10FFFF]
    if kind == "plan":
        assert controls["expected_rows"][0]["batch_id"] == [8, 12, 1, 9, 10, 13]
    for row in inventory["witnesses"]:
        for value in row["expected_rows"] or []:
            for key in ("request_id", "batch_id"):
                for scalar in value.get(key, []):
                    assert 0 <= scalar <= 0x10FFFF and not 0xD800 <= scalar <= 0xDFFF


def test_negative_grammar_probes_preserve_actual_invalid_bytes(inventory):
    extra = [row for row in inventory["witnesses"] if any(origin["category"] == "authored_grammar_probe" for origin in row["origins"])]
    assert sum(row["expected_parse_success"] for row in extra) == 10
    assert sum(not row["expected_parse_success"] for row in extra) == 16
    invalid = [row for row in extra if any(origin.get("probe_id", "").endswith("invalid-utf8") for origin in row["origins"])]
    assert len(invalid) == 2
    for row in invalid:
        raw = bytes.fromhex(row["raw_hex"])
        assert b"\xc0\xaf" in raw
        assert row["expected_rows"] is None and row["expected_parse_success"] is False
        with pytest.raises(UnicodeError):
            raw.decode("utf-8")


def _report_mutations():
    return [
        ("drop_witness", lambda r: r["witnesses"].pop()),
        ("reorder_witness", lambda r: r["witnesses"].reverse()),
        ("duplicate_witness", lambda r: r["witnesses"].append(copy.deepcopy(r["witnesses"][0]))),
        ("raw_bytes", lambda r: r["witnesses"][0].update(raw_bytes=0)),
        ("raw_hex", lambda r: r["witnesses"][0].update(raw_hex="ff")),
        ("raw_hash", lambda r: r["witnesses"][0].update(raw_sha256="0" * 64)),
        ("kind", lambda r: r["witnesses"][0].update(kind="plan")),
        ("accept", lambda r: r["witnesses"][0].update(expected_parse_success=False)),
        ("rows", lambda r: r["witnesses"][0]["expected_rows"][0].update(prompt_len=65)),
        ("identifier", lambda r: r["witnesses"][0]["expected_rows"][0].update(request_id=[0xD800])),
        ("drop_origin", lambda r: r["witnesses"][0]["origins"].pop()),
        ("origin_case", lambda r: r["witnesses"][0]["origins"][0].update(case_index=29)),
        ("origin_phase", lambda r: r["witnesses"][0]["origins"][0].update(phase="after")),
        ("origin_path", lambda r: r["witnesses"][0]["origins"][0].update(path="other.jsonl")),
        ("drop_case", lambda r: r["case_bindings"].pop()),
        ("reorder_case", lambda r: r["case_bindings"].reverse()),
        ("derived_index", lambda r: r["case_bindings"][0].update(derived_case_index=1)),
        ("model_hash", lambda r: r["case_bindings"][0].update(source_model_sha256="0" * 64)),
        ("case_witness_join", lambda r: r["case_bindings"][0]["files"]["after"].update({dw.FILE_PATHS[0]: "unknown"})),
        ("derived_drop", lambda r: r["derived_cases"].pop()),
        ("derived_reorder", lambda r: r["derived_cases"].reverse()),
        ("summary", lambda r: r["summary"].update(accepted_witnesses=44)),
        ("boolean_integer", lambda r: r["summary"].update(derived_cases=True)),
        ("limit", lambda r: r["limits"].update(max_integer=10**18 + 1)),
        ("claim", lambda r: r["claims"].update(source_model_equivalence_proved=True)),
        ("scope", lambda r: r["scope"].update(decoder_checks="universal_parser_equivalence")),
        ("unknown", lambda r: r.update(unchecked_extra=True)),
    ]


@pytest.mark.parametrize("name,mutate", _report_mutations(), ids=lambda value: value if isinstance(value, str) else None)
def test_any_retained_projection_binding_or_scope_tamper_is_rejected(inventory, filecases, name, mutate):
    forged = copy.deepcopy(inventory)
    mutate(forged)
    with pytest.raises(ValueError):
        dw.validate_decoder_witnesses(forged, filecases=filecases)


def _input_mutations():
    return [
        ("missing_entry", lambda r: r["entries"].pop()),
        ("reorder_entry", lambda r: r["entries"].reverse()),
        ("case_recipe", lambda r: r["entries"][0]["spec"].update(case_id="other")),
        ("head", lambda r: r["head"].update(generation=2)),
        ("contract", lambda r: r.update(contract_sha256="0" * 64)),
        ("model_row", lambda r: r["entries"][0]["model"]["case"]["buckets"][0]["requests"][0].update(prompt_len=65)),
        ("model_projection", lambda r: r["entries"][0]["model"]["projections"]["after"][dw.FILE_PATHS[0]]["records"][0]["record_span"].update(end_byte=2)),
        ("model_projection_domain", lambda r: r["entries"][0]["model"]["projections"].update(after=None)),
        ("drop_derived", lambda r: r["derived_cases"].pop()),
        ("derived_row", lambda r: r["derived_cases"][0]["case"]["buckets"][0]["plan"][0]["shape"].update(seq_align=128)),
        ("metrics", lambda r: r["entries"][0]["model"]["supplied_metrics"]["1"]["cost"].update(numerator=1)),
        ("current_authority", lambda r: r["claims"].update(historical_reports_are_live_authority=True)),
        ("summary", lambda r: r["counts"].update(accepted=8)),
        ("wrong_model_outcome", lambda r: r["entries"][0].update(outcome="model_refusal")),
        ("missing_refusal", lambda r: r["entries"][-1].update(error=None)),
        ("drop_observed_leaf", lambda r: r["entries"][0]["after"]["files"].pop(dw.FILE_PATHS[0])),
    ]


@pytest.mark.parametrize("name,mutate", _input_mutations(), ids=lambda value: value if isinstance(value, str) else None)
def test_source_report_row_and_model_join_tamper_is_rejected(filecases, name, mutate):
    forged = copy.deepcopy(filecases)
    mutate(forged)
    with pytest.raises(ValueError):
        dw.build_decoder_witnesses(filecases=forged)


def test_consistently_rehashed_observed_payload_still_cannot_replace_authored_recipe(filecases):
    import base64
    forged = copy.deepcopy(filecases)
    leaf = forged["entries"][0]["after"]["files"][dw.FILE_PATHS[0]]
    raw = base64.b64decode(leaf["payload_b64"]).replace(b"64", b"65")
    leaf.update(payload_b64=base64.b64encode(raw).decode("ascii"), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    with pytest.raises(ValueError):
        dw.build_decoder_witnesses(filecases=forged)


@pytest.mark.parametrize("invalid", [None, True, 1.0, float("nan"), (), {"bad": -1},
                                      {"bad": 10**20 + 1}, {"bad": "\ud800"},
                                      {"bad": list(range(32769))}])
def test_input_plain_json_and_domain_bounds(invalid):
    with pytest.raises(ValueError):
        dw.build_decoder_witnesses(filecases=invalid)


def test_report_depth_and_byte_limits_are_checked_before_replay(inventory, filecases):
    nested = None
    for _ in range(34):
        nested = {"nested": nested}
    for invalid in (nested, {"oversized": "x" * (dw.MAX_REPORT_BYTES + 1)}):
        with pytest.raises(ValueError):
            dw.validate_decoder_witnesses(invalid, filecases=filecases)


def test_rebuild_and_validation_never_open_or_reobserve_files(inventory, filecases, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("pure supplied-byte witness projection attempted filesystem I/O")
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(os, "open", forbidden)
    monkeypatch.setattr(os, "stat", forbidden)
    assert dw.build_decoder_witnesses(filecases=filecases) == inventory
    assert dw.validate_decoder_witnesses(inventory, filecases=filecases) == inventory
