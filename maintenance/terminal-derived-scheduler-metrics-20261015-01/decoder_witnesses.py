"""Pure exact-byte witnesses for the authored JSONL decoder experiment.

This inventory joins supplied historical observations to typed row values.  It
does not observe files or confer authority on the reports which supply bytes.
The finite Lean decoder checks these witnesses separately; this Python helper
does not prove the implementation of either parser correct.
"""
from __future__ import annotations

import copy
import hashlib
import json

from file_model_bridge import FALSE_CLAIMS as MODEL_CLAIMS, BUCKET_PATHS
from file_case_run import CLAIMS as CASE_CLAIMS, SCHEMA as CASE_SCHEMA
from jsonl_cases import FILE_PATHS, fixture_payloads, specs
from observed_files import compare_bundles, decode_file, validate_bundle
from strict_jsonl import (LIMITS, StrictJSONLError, parse_jsonl,
                          validate_jsonl_report)

SCHEMA = "terminal-jsonl-scalar-decoder-witnesses@1"
MAX_INPUT_BYTES = 16 * 1024 * 1024
MAX_REPORT_BYTES = 4 * 1024 * 1024
MAX_NODES = 400000
CLAIMS = {
    "supplied_bytes_only": True,
    "current_file_custody_verified": False,
    "historical_observations_authenticated": False,
    "formal_python_parser_correctness_proved": False,
    "formal_lean_parser_correctness_proved": False,
    "source_runtime_equivalence_proved": False,
    "source_model_equivalence_proved": False,
    "runtime_metrics_observed": False,
    "full_task_satisfaction_proved": False,
    "convergence_proved": False,
    "planning_or_dispatch_authority": False,
}
SCOPE = {
    "input": "supplied_complete_authored_file_case_observation_bytes",
    "output": "deduplicated_kind_and_raw_bytes_with_unicode_scalar_typed_rows",
    "decoder_checks": "closed_witness_results_not_a_universal_parser_theorem",
    "model_join": "exact_rows_and_input_strings_of_all_16_derived_cases",
    "custody_controls": "three_historical_custody_refusals_are_not_decoder_proofs",
    "metrics": "explicit_supplied_exact_rationals_not_runtime_cost_observations",
}
_ENTRY_FIELDS = {"spec", "fixture", "before", "after", "model", "outcome", "error"}
_CASE_FIELDS = {"schema", "contract_sha256", "head", "output", "entries", "derived_cases",
                "counts", "all_expected_outcomes_matched", "all_after_observations_reobserved", "claims"}
_CUSTODY = {"changed_input_bytes", "changed_plan_bytes", "same_bytes_replacement"}
_MODEL_FIELDS = {"schema", "case_id", "contract_sha256", "head", "head_sha256",
                 "before_observation_sha256", "after_observation_sha256", "metrics_sha256",
                 "supplied_metrics", "file_bindings", "file_comparison", "projections", "case",
                 "evaluation", "claims"}
_EXPECTED_COUNTS = {"total": 30, "accepted": 7, "model_refusal": 9,
                    "file_refusal": 14, "derived_cases": 16}
EXPECTED_SUMMARY = {"source_cases": 30, "source_file_bindings": 240,
                    "derived_cases": 16, "accepted_model_cases": 7, "rejected_model_cases": 9,
                    "parser_refusal_cases": 11, "custody_refusal_cases": 3,
                    "authored_grammar_probes": 26, "positive_grammar_probes": 10,
                    "negative_grammar_probes": 16, "unique_witnesses": 70,
                    "accepted_witnesses": 43, "rejected_witnesses": 27}


class DecoderWitnessError(ValueError):
    """Supplied historical bytes and typed decoder witnesses do not agree."""


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _canonical(value, *, maximum=MAX_INPUT_BYTES):
    nodes = [0]
    def check(item, depth=0):
        nodes[0] += 1
        if depth > 32 or nodes[0] > MAX_NODES:
            raise DecoderWitnessError("plain JSON exceeds the witness structural bound")
        if item is None or type(item) is bool:
            return
        if type(item) is int:
            if not 0 <= item <= 10**20:
                raise DecoderWitnessError("plain JSON integer exceeds the witness bound")
            return
        if type(item) is str:
            try:
                raw = item.encode("utf-8", errors="strict")
            except UnicodeError as exc:
                raise DecoderWitnessError("plain JSON string is not Unicode scalar text") from exc
            if len(raw) > maximum:
                raise DecoderWitnessError("plain JSON string exceeds its witness bound")
            return
        if type(item) is list and len(item) <= 32768:
            for child in item:
                check(child, depth + 1)
            return
        if type(item) is dict and len(item) <= 4096 and all(type(key) is str for key in item):
            for key, child in item.items():
                check(key, depth + 1)
                check(child, depth + 1)
            return
        raise DecoderWitnessError("bounded plain JSON values are required")
    check(value)
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True, allow_nan=False).encode("ascii")
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise DecoderWitnessError("witness material is not bounded plain JSON") from exc
    if len(raw) > maximum:
        raise DecoderWitnessError("serialized witness material exceeds its byte bound")
    return raw


def _same(actual, expected, message):
    if _canonical(actual) != _canonical(expected):
        raise DecoderWitnessError(message)


def _typed_row(row, kind):
    result = copy.deepcopy(row)
    result["request_id"] = [ord(char) for char in row["request_id"]]
    if kind == "plan":
        result["batch_id"] = [ord(char) for char in row["batch_id"]]
    return result


def _parse(raw, kind):
    try:
        parsed = parse_jsonl(raw, kind=kind)
    except StrictJSONLError:
        return False, None, None
    return True, [_typed_row(row, kind) for row in parsed["rows"]], parsed


def _kind(path):
    return "requests" if path.startswith("input_data/") else "plan"


def _extras():
    """Small authored grammar probes, never benchmark workload examples."""
    positives = [
        ("escaped-controls", "\b\f\x01\t\n\r", True),
        ("escaped-supplementary", "\U0001f9e0\U0010ffff", True),
        ("raw-supplementary", "\U0001f9e0\U00010000", False),
        ("escaped-quote-backslash-slash", '"\\/', True),
        ("unicode-scalar-boundaries", "\x1f\x7f\x80\u07ff\u0800\ud7ff\ue000\uffff", True),
    ]
    result = []
    for kind in ("requests", "plan"):
        def row(identifier):
            if kind == "requests":
                return {"request_id": identifier, "prompt_len": 64, "gen_len": 1}
            return {"request_id": identifier, "batch_id": identifier,
                    "shape": {"seq_align": 64, "heads_align": 32, "hidden_align": 4096}}
        for name, identifier, ascii_only in positives:
            raw = json.dumps(row(identifier), sort_keys=True, ensure_ascii=ascii_only,
                             separators=(",", ":")).encode("utf-8") + b"\n"
            if name == "escaped-quote-backslash-slash":
                raw = raw.replace(b"/", b"\\/")
            result.append({"probe_id": kind + "-" + name, "kind": kind,
                           "raw": raw, "expected_accept": True})
        baseline = json.dumps(row("probe"), sort_keys=True,
                              separators=(",", ":")).encode("ascii") + b"\n"
        negatives = [
            ("escaped-nul", baseline.replace(b'"probe"', b'"\\u0000"')),
            ("lone-high-surrogate", baseline.replace(b'"probe"', b'"\\ud800"')),
            ("lone-low-surrogate", baseline.replace(b'"probe"', b'"\\udfff"')),
            ("malformed-unicode-escape", baseline.replace(b'"probe"', b'"\\u12xz"')),
            ("invalid-utf8", baseline.replace(b"probe", b"\xc0\xaf")),
            ("raw-string-control", baseline.replace(b"probe", b"a\x01b")),
            ("noncanonical-natural", baseline.replace(
                b'"prompt_len":64' if kind == "requests" else b'"seq_align":64',
                b'"prompt_len":064' if kind == "requests" else b'"seq_align":064')),
            ("trailing-comma", baseline[:-2] + b",}\n"),
        ]
        for name, raw in negatives:
            result.append({"probe_id": kind + "-" + name, "kind": kind,
                           "raw": raw, "expected_accept": False})
    return result


def _model_join(entry, *, filecases, spec, parsed):
    """Check byte/row joins; the caller separately replays the finite checker."""
    model = entry["model"]
    if type(model) is not dict or set(model) != _MODEL_FIELDS:
        raise DecoderWitnessError("each parsed case needs its exact supplied file model")
    _same(model.get("claims"), MODEL_CLAIMS, "file model claims changed")
    if (model.get("schema") != "terminal-jsonl-file-bound-scheduler-model@1"
            or model.get("case_id") != spec["case_id"]
            or model.get("contract_sha256") != filecases["contract_sha256"]):
        raise DecoderWitnessError("file model provenance differs from its containing case")
    _same(model.get("head"), filecases["head"], "file model head differs")
    for key, value in (("before_observation_sha256", _sha(_canonical(entry["before"]))),
                       ("after_observation_sha256", _sha(_canonical(entry["after"]))),
                       ("head_sha256", _sha(_canonical(filecases["head"]))),
                       ("metrics_sha256", _sha(_canonical(spec["metrics"])))):
        if model.get(key) != value:
            raise DecoderWitnessError("file model byte provenance differs")
    _same(model.get("supplied_metrics"), spec["metrics"], "supplied metric inputs changed")
    _same(model.get("file_comparison"), compare_bundles(entry["before"], entry["after"]),
          "file model observation comparison differs")
    buckets, bindings = [], {}
    for bucket_id in (1, 2):
        paths = BUCKET_PATHS[bucket_id]
        buckets.append({"bucket_id": bucket_id,
                        "requests": copy.deepcopy(parsed["after"][paths["requests"]]["rows"]),
                        "plan": copy.deepcopy(parsed["after"][paths["plan"]]["rows"]),
                        "metrics": copy.deepcopy(spec["metrics"][str(bucket_id)]),
                        "input_before": decode_file(entry["before"], paths["requests"]).decode("utf-8"),
                        "input_after": decode_file(entry["after"], paths["requests"]).decode("utf-8")})
        for kind, path in paths.items():
            bindings[path] = {"bucket_id": bucket_id, "kind": kind,
                              "row_source": "after_raw_utf8_bytes"}
            for phase in ("before", "after"):
                source = entry[phase]["files"][path]
                bindings[path][phase] = {"bytes": source["bytes"], "sha256": source["sha256"],
                                         "identity": copy.deepcopy(source["identity"]),
                                         "payload_b64_sha256": _sha(source["payload_b64"].encode("ascii"))}
    _same(model.get("file_bindings"), bindings, "file model leaf bindings differ")
    expected_case = {"case_id": spec["case_id"], "buckets": buckets}
    _same(model.get("case"), expected_case, "derived model rows differ from the exact file bytes")
    if type(model.get("projections")) is not dict or set(model["projections"]) != {"before", "after"}:
        raise DecoderWitnessError("file model parser projection phases differ")
    for phase in ("before", "after"):
        if type(model["projections"][phase]) is not dict or set(model["projections"][phase]) != set(FILE_PATHS):
            raise DecoderWitnessError("file model parser projection inventory differs")
        for path in FILE_PATHS:
            validate_jsonl_report(model["projections"][phase][path],
                                  raw=decode_file(entry[phase], path), kind=_kind(path))
    evaluation = model.get("evaluation")
    if (type(evaluation) is not dict or evaluation.get("case_id") != spec["case_id"]
            or evaluation.get("case_sha256") != _sha(_canonical(expected_case))
            or evaluation.get("contract_sha256") != filecases["contract_sha256"]
            or evaluation.get("evaluation_passed") is not (entry["outcome"] == "accepted")):
        raise DecoderWitnessError("supplied model evaluation is not joined to its exact case")
    return {"case": expected_case, "expected_pass": entry["outcome"] == "accepted",
            "intended_violation_ids": list(spec["intended_violation_ids"])}


def build_decoder_witnesses(*, filecases: dict) -> dict:
    """Join supplied historical bytes and all typed rows without filesystem I/O."""
    filecases_raw = _canonical(filecases)
    if (type(filecases) is not dict or set(filecases) != _CASE_FIELDS
            or filecases["schema"] != CASE_SCHEMA
            or filecases["all_expected_outcomes_matched"] is not True
            or filecases["all_after_observations_reobserved"] is not True):
        raise DecoderWitnessError("complete historical authored case-run data required")
    _same(filecases["claims"], CASE_CLAIMS, "historical case-run claims changed")
    _same(filecases["counts"], _EXPECTED_COUNTS, "historical case-run counts changed")
    selected = specs()
    if type(filecases["entries"]) is not list or len(filecases["entries"]) != 30 or len(selected) != 30:
        raise DecoderWitnessError("all 30 ordered authored cases are required")
    if type(filecases["output"]) is not str or not filecases["output"].startswith("/") or filecases["output"].endswith("/"):
        raise DecoderWitnessError("an absolute historical output string is required")
    if (type(filecases["contract_sha256"]) is not str or len(filecases["contract_sha256"]) != 64
            or any(char not in "0123456789abcdef" for char in filecases["contract_sha256"])):
        raise DecoderWitnessError("a canonical historical contract hash is required")
    witnesses, lookup, case_bindings, derived = [], {}, [], []
    def add(raw, kind, origin):
        key = (kind, raw)
        if key not in lookup:
            accepted, rows, _ = _parse(raw, kind)
            witness_id = "jsonl-" + kind + "-" + _sha(raw)
            if any(row["witness_id"] == witness_id for row in witnesses):
                raise DecoderWitnessError("distinct witness bytes collide in the inventory")
            lookup[key] = len(witnesses)
            witnesses.append({"witness_id": witness_id, "kind": kind,
                              "raw_hex": raw.hex(), "raw_bytes": len(raw), "raw_sha256": _sha(raw),
                              "expected_parse_success": accepted, "expected_rows": rows, "origins": []})
        witness = witnesses[lookup[key]]
        witness["origins"].append(origin)
        return witness
    for index, (entry, spec) in enumerate(zip(filecases["entries"], selected)):
        if type(entry) is not dict or set(entry) != _ENTRY_FIELDS:
            raise DecoderWitnessError("case entry fields differ from the closed profile")
        _same(entry["spec"], spec, "ordered authored case recipe changed")
        if entry["outcome"] != spec["expected_outcome"]:
            raise DecoderWitnessError("case outcome differs from its authored recipe")
        expected_before = fixture_payloads(spec)
        expected_after = dict(expected_before)
        if spec["fault"] in {"changed_input_bytes", "changed_plan_bytes"}:
            path = FILE_PATHS[2] if spec["fault"] == "changed_plan_bytes" else FILE_PATHS[0]
            expected_after[path] = expected_after[path].rstrip(b"\n") + b" \n"
        root = filecases["output"] + "/" + spec["case_id"]
        fixture = {"schema": "terminal-authored-jsonl-file-fixture@1", "case_id": spec["case_id"],
                   "root": root, "initial_payloads": {path: {"bytes": len(raw), "sha256": _sha(raw)}
                                                         for path, raw in sorted(expected_before.items())},
                   "real_benchmark_input_used": False, "source_body_execution": False}
        _same(entry["fixture"], fixture, "historical fixture differs from its exact byte recipe")
        file_joins, parsed, refusal_ids = {}, {}, []
        for phase, expected in (("before", expected_before), ("after", expected_after)):
            validate_bundle(entry[phase])
            if entry[phase]["root"] != root:
                raise DecoderWitnessError("historical observation root differs from its recipe")
            file_joins[phase], parsed[phase] = {}, {}
            for path in FILE_PATHS:
                raw = decode_file(entry[phase], path)
                if raw != expected[path]:
                    raise DecoderWitnessError("historical observation bytes differ from their recipe")
                witness = add(raw, _kind(path), {"category": "file_case", "case_index": index,
                              "case_id": spec["case_id"], "phase": phase, "path": path,
                              "bucket_id": 1 if path in (FILE_PATHS[0], FILE_PATHS[2]) else 2})
                file_joins[phase][path] = witness["witness_id"]
                accepted, _, projection = _parse(raw, _kind(path))
                if accepted:
                    parsed[phase][path] = projection
                elif witness["witness_id"] not in refusal_ids:
                    refusal_ids.append(witness["witness_id"])
        custody = spec["fault"] in _CUSTODY
        comparison = compare_bundles(entry["before"], entry["after"])
        custody_equal = all(comparison[key] is True for key in (
            "roots_equal", "directory_generations_equal", "inputs_bytes_equal", "unchanged_inputs", "same_file_generations"))
        derived_index = None
        if entry["outcome"] in {"accepted", "model_refusal"}:
            if refusal_ids or not custody_equal or entry["error"] is not None:
                raise DecoderWitnessError("parsed model case has a parser or custody refusal")
            derived_index = len(derived)
            derived.append(_model_join(entry, filecases=filecases, spec=spec, parsed=parsed))
            category = "parsed_model"
        else:
            if entry["model"] is not None or type(entry["error"]) is not dict:
                raise DecoderWitnessError("file refusal must remain separate from a finite model")
            category = "custody_refusal" if custody else "parser_refusal"
            if custody and (refusal_ids or custody_equal):
                raise DecoderWitnessError("custody refusal is not separated from decoder checks")
            if not custody and (not refusal_ids or not custody_equal):
                raise DecoderWitnessError("parser refusal lacks its exact rejected bytes")
        case_bindings.append({"case_index": index, "case_id": spec["case_id"], "category": category,
                              "outcome": entry["outcome"], "source_entry_sha256": _sha(_canonical(entry)),
                              "before_observation_sha256": _sha(_canonical(entry["before"])),
                              "after_observation_sha256": _sha(_canonical(entry["after"])),
                              "files": file_joins, "parse_refusal_witness_ids": refusal_ids,
                              "derived_case_index": derived_index,
                              "source_model_sha256": _sha(_canonical(entry["model"])) if entry["model"] is not None else None})
    _same(filecases["derived_cases"], derived, "all 16 ordered derived cases must join exact observed rows")
    if len(derived) != 16 or sum(case["expected_pass"] for case in derived) != 7:
        raise DecoderWitnessError("derived-case inventory differs from the declared finite profile")
    probes = _extras()
    for probe in probes:
        witness = add(probe["raw"], probe["kind"], {"category": "authored_grammar_probe", "probe_id": probe["probe_id"]})
        if witness["expected_parse_success"] is not probe["expected_accept"]:
            raise DecoderWitnessError("an authored grammar probe differs from its independent expectation")
    summary = {"source_cases": len(case_bindings), "source_file_bindings": 240,
               "derived_cases": len(derived), "accepted_model_cases": 7, "rejected_model_cases": 9,
               "parser_refusal_cases": sum(row["category"] == "parser_refusal" for row in case_bindings),
               "custody_refusal_cases": sum(row["category"] == "custody_refusal" for row in case_bindings),
               "authored_grammar_probes": len(probes), "positive_grammar_probes": 10,
               "negative_grammar_probes": 16, "unique_witnesses": len(witnesses),
               "accepted_witnesses": sum(row["expected_parse_success"] for row in witnesses),
               "rejected_witnesses": sum(not row["expected_parse_success"] for row in witnesses)}
    _same(summary, EXPECTED_SUMMARY, "the decoder witness inventory differs from its fixed authored profile")
    report = {"schema": SCHEMA, "filecases_sha256": _sha(filecases_raw),
              "contract_sha256": filecases["contract_sha256"], "head_sha256": _sha(_canonical(filecases["head"])),
              "limits": dict(LIMITS), "witnesses": witnesses, "case_bindings": case_bindings,
              "derived_cases": derived, "summary": summary, "claims": dict(CLAIMS), "scope": dict(SCOPE)}
    _canonical(report, maximum=MAX_REPORT_BYTES)
    return report


def validate_decoder_witnesses(report, *, filecases):
    """Rebuild complete byte/row joins; never reobserve or open a file."""
    retained = _canonical(report, maximum=MAX_REPORT_BYTES)
    expected = build_decoder_witnesses(filecases=filecases)
    if retained != _canonical(expected, maximum=MAX_REPORT_BYTES):
        raise DecoderWitnessError("decoder witnesses differ from their complete supplied byte inventory")
    return expected
