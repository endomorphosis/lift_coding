"""Source-bound candidate scheduler predicates and a bounded authored-data checker.

No repository code is imported or executed.  Supplied metrics are inputs to the
candidate contract, not observations from the benchmark cost model.  A passing
finite case neither completes the original intent nor authorizes task dispatch.
"""
from __future__ import annotations

import ast
import copy
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import hashlib
import json
import re

CONTRACT_SCHEMA = "terminal-scheduler-typed-constraint-contract@1"
EVALUATION_SCHEMA = "terminal-scheduler-typed-constraint-evaluation@1"
GRANULARITY, HEADS, HIDDEN, MAX_SHAPES = 64, 32, 4096, 8
MAX_INTEGER, MAX_REQUESTS = 10**18, 256
MAX_INPUT_BYTES, MAX_CASE_BYTES = 65536, 2 * 1024 * 1024
SOURCE_PREFIX = "llm-inference-batching-scheduler/environment/task_file/scripts/"
SOURCE_PATHS = {
    "headless-terminal/environment/base_terminal.py",
    "feal-differential-cryptanalysis/environment/feal.py",
    "break-filter-js-from-html/environment/filter.py",
    SOURCE_PREFIX + "baseline_packer.py", SOURCE_PREFIX + "cost_model.py",
}
SCHEDULER_SOURCE_SHA256 = {
    SOURCE_PREFIX + "baseline_packer.py": "547d230d5e6d93197803480cb81cab0ec6ac63fcfa0a24b246f549523f216c4e",
    SOURCE_PREFIX + "cost_model.py": "0cf417fd5ff0112defcd46970d37a290c0763c5a9092e91cb3ebb86c3f20e6ce",
}
INSTRUCTION_SHA256 = "0817374767533fbf51bb93345ee1bba266263c216c6cc55c096e71b4a1d37dfc"
FALSE_CLAIMS = {
    "original_semantic_coverage_complete": False,
    "full_task_satisfaction_proved": False,
    "source_model_equivalence_proved": False,
    "source_runtime_semantics_verified": False,
    "supplied_metrics_are_runtime_observations": False,
    "cost_model_executed": False,
    "formal_proof": False,
    "convergence_proved": False,
    "planning_or_dispatch_authority": False,
    "physical_input_immutability_proved": False,
}
ASSUMPTIONS = [
    "Candidate lengths and dimensions are exact non-Boolean natural integers bounded by 10^18.",
    "Request identity is the pair (bucket_id, request_id); input IDs are unique within each bucket.",
    "Batch identity is the pair (bucket_id, batch_id); cross-file batch scope remains unresolved.",
    "Strict less-than interprets the prompt word below; original interpretation is not proved.",
    "Metrics are supplied exact rationals; their relationship to Python floating-point cost_model execution is unproved.",
    "Unchanged inputs means equality of the two supplied UTF-8 byte observations, not physical immutability.",
    "The bounded finite checker is experimental and establishes no complete original-task intent coverage.",
]
LIMITS = {"max_integer": MAX_INTEGER, "max_requests_per_bucket": MAX_REQUESTS,
          "max_plan_rows_per_bucket": MAX_REQUESTS, "max_input_bytes": MAX_INPUT_BYTES,
          "max_case_bytes": MAX_CASE_BYTES, "max_identifier_utf8_bytes": 512}
METRIC_NAMES = ("cost", "pad_ratio", "p95_latency_ms", "sequential_time_ms")
THRESHOLD_LEXEMES = {1: ("3.0e11", "0.055", "2.1e6", "2.7e8"),
                     2: ("4.8e10", "0.15", "2.1e5", "3.2e7")}
TEXT = {
    "scheduler.exact_once": "All input requests are included exactly once (no missing/duplicate request_ids)",
    "scheduler.shape_alignment": "Each batch uses shape (seq_align, heads_align=32, hidden_align=4096) where seq_align >= ceil(prompt_len/64)*64. I.e., seq_align is a multiple of 64.",
    "scheduler.global_shape_cap": "Max 8 unique shapes (seq_align, heads_align, hidden_align) across both buckets (MAX_SHAPES=8)",
    "scheduler.batch_shape_equality": "One record per request_id, identical shapes within each batch_id",
    "scheduler.thresholds.bucket_1": "| ``requests_bucket_1.jsonl`` | ``3.0e11`` | ``0.055`` | ``2.1e6`` | ``2.7e8`` |",
    "scheduler.thresholds.bucket_2": "| ``requests_bucket_2.jsonl`` | ``4.8e10`` | ``0.15`` | ``2.1e5`` | ``3.2e7`` |",
    "scheduler.input_unchanged": "The output files must satisfy the performance thresholds above, and you should also keep the input_data files unchanged.",
    "scheduler.input_schema": "a JSON object containing a unique ``request_id``, a ``prompt_len`` and\n``gen_len``:",
}
STRICT_TEXT = "Your goal is to achieve metrics below the thresholds listed below:"


class SchedulerConstraintError(ValueError):
    """A contract binding or closed schema is invalid."""


def _json(value, depth=0):
    if depth > 32:
        raise SchedulerConstraintError("JSON exceeds nesting bound")
    if value is None or type(value) in (bool, int):
        return
    if type(value) is str:
        try:
            if len(value.encode("utf-8")) > MAX_CASE_BYTES:
                raise SchedulerConstraintError("JSON string exceeds byte bound")
        except UnicodeEncodeError as exc:
            raise SchedulerConstraintError("JSON string is not UTF-8") from exc
        return
    if type(value) is list:
        if len(value) > 8192:
            raise SchedulerConstraintError("JSON array exceeds bound")
        for item in value:
            _json(item, depth + 1)
        return
    if type(value) is dict and all(type(key) is str for key in value):
        if len(value) > 1024:
            raise SchedulerConstraintError("JSON object exceeds bound")
        for key, item in value.items():
            _json(key, depth + 1)
            _json(item, depth + 1)
        return
    raise SchedulerConstraintError("only closed plain JSON values are accepted")


def canonical_bytes(value):
    _json(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _span(instruction, text):
    raw = text.encode("utf-8")
    if instruction.count(raw) != 1:
        raise SchedulerConstraintError("candidate clause source is missing or ambiguous")
    start = instruction.index(raw)
    return {"artifact": "instruction", "start_byte": start, "end_byte": start + len(raw),
            "start_line": instruction[:start].count(b"\n") + 1,
            "end_line": instruction[:start + len(raw)].count(b"\n") + 1,
            "text": text, "sha256": _sha(raw)}


def _decimal_rational(lexeme):
    if type(lexeme) is not str or len(lexeme) > 32 or not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?(?:e[+-]?[0-9]{1,2})?", lexeme):
        raise SchedulerConstraintError("threshold lexeme exceeds the decimal grammar")
    try:
        decimal = Decimal(lexeme)
        if not decimal.is_finite() or decimal < 0 or abs(decimal.adjusted()) > 18:
            raise SchedulerConstraintError("threshold decimal is outside the finite model")
        rational = Fraction(decimal)
    except (InvalidOperation, ValueError, OverflowError) as exc:
        raise SchedulerConstraintError("invalid threshold decimal") from exc
    if max(rational.numerator, rational.denominator) > MAX_INTEGER:
        raise SchedulerConstraintError("threshold rational exceeds bounds")
    return {"numerator": rational.numerator, "denominator": rational.denominator,
            "lexeme": lexeme}


def _source_facts(sources):
    facts = []
    wanted = {"cost_model.py": {"align", "_sum_sq_arith", "batch_metrics", "plan_metrics", "pxx_latency"},
              "baseline_packer.py": {"_plan_for_requests", "build_plan"}}
    for source in sources:
        short = source["path"].rsplit("/", 1)[-1]
        if short not in wanted:
            continue
        raw = source["source_text"].encode("utf-8")
        lines = raw.splitlines(keepends=True)
        tree = ast.parse(source["source_text"], filename=source["path"])
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in wanted[short]:
                start = sum(map(len, lines[:node.lineno - 1])) + node.col_offset
                end = sum(map(len, lines[:node.end_lineno - 1])) + node.end_col_offset
                facts.append({"path": source["path"], "source_sha256": source["sha256"],
                              "function": node.name, "start_byte": start, "end_byte": end,
                              "start_line": node.lineno, "end_line": node.end_lineno,
                              "source_text": raw[start:end].decode("utf-8"),
                              "ast_sha256": _sha(ast.dump(node, include_attributes=False).encode("utf-8")),
                              "authority": "syntax_observation_only"})
    return sorted(facts, key=lambda row: (row["path"], row["start_byte"]))


def build_scheduler_contract(*, instruction: bytes, head: dict, source_records: list) -> dict:
    if type(instruction) is not bytes or _sha(instruction) != INSTRUCTION_SHA256:
        raise SchedulerConstraintError("candidate contract requires the complete pinned public scheduler instruction")
    try:
        text = instruction.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SchedulerConstraintError("instruction must be exact UTF-8") from exc
    _json(head)
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    if (type(head) is not dict
            or canonical_bytes(CodebaseHead.from_dict(head).to_dict()) != canonical_bytes(head)):
        raise SchedulerConstraintError("complete canonical native CodebaseHead is required")
    if type(source_records) is not list or len(source_records) != 5:
        raise SchedulerConstraintError("complete five-source inventory is required")
    sources, paths = [], set()
    for row in source_records:
        if type(row) is not dict or set(row) != {"path", "sha256", "source_text"}:
            raise SchedulerConstraintError("source record has unknown or missing fields")
        path, digest, body = row["path"], row["sha256"], row["source_text"]
        if type(path) is not str or path not in SOURCE_PATHS or path in paths:
            raise SchedulerConstraintError("source inventory is not the closed unique five-file profile")
        if type(body) is not str or type(digest) is not str:
            raise SchedulerConstraintError("source body and digest must be strings")
        try:
            raw = body.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise SchedulerConstraintError("source is not UTF-8") from exc
        if len(raw) > 8192 or not re.fullmatch("[0-9a-f]{64}", digest) or _sha(raw) != digest:
            raise SchedulerConstraintError("source body does not match its finite SHA256 binding")
        if path in SCHEDULER_SOURCE_SHA256 and digest != SCHEDULER_SOURCE_SHA256[path]:
            raise SchedulerConstraintError("candidate source projection is outside the audited scheduler revision")
        paths.add(path)
        sources.append(copy.deepcopy(row))
    if paths != SOURCE_PATHS:
        raise SchedulerConstraintError("incomplete source inventory")
    sources.sort(key=lambda row: row["path"])
    parameters = {
        "scheduler.exact_once": {"request_identity": "bucket_qualified", "input_ids_unique": True},
        "scheduler.shape_alignment": {"granularity": GRANULARITY, "heads_align": HEADS, "hidden_align": HIDDEN},
        "scheduler.global_shape_cap": {"max_shapes": MAX_SHAPES, "scope": "both_buckets_union"},
        "scheduler.batch_shape_equality": {"batch_identity": "bucket_qualified"},
        "scheduler.input_unchanged": {"comparison": "observed_utf8_bytes_equal"},
        "scheduler.input_schema": {"domain": "bounded_naturals", "max_integer": MAX_INTEGER,
                                   "max_requests_per_bucket": MAX_REQUESTS},
    }
    for bucket in (1, 2):
        parameters[f"scheduler.thresholds.bucket_{bucket}"] = {
            "bucket_id": bucket, "comparison": "strict_lt",
            "metrics": {name: _decimal_rational(lexeme)
                        for name, lexeme in zip(METRIC_NAMES, THRESHOLD_LEXEMES[bucket])}}
    clauses = []
    for requirement_id in TEXT:
        kind = "thresholds" if requirement_id.startswith("scheduler.thresholds.") else requirement_id.split(".")[-1]
        spans = [_span(instruction, TEXT[requirement_id])]
        if kind == "thresholds":
            spans.insert(0, _span(instruction, STRICT_TEXT))
        clauses.append({"requirement_id": requirement_id, "kind": kind,
                        "source_spans": spans, "parameters": parameters[requirement_id]})
    return {"schema": CONTRACT_SCHEMA, "head": copy.deepcopy(head),
            "head_sha256": _sha(canonical_bytes(head)),
            "instruction": {"source_text": text, "bytes": len(instruction), "sha256": _sha(instruction)},
            "sources": sources, "clauses": clauses,
            "assumptions": list(ASSUMPTIONS), "limits": dict(LIMITS),
            "source_facts": _source_facts(sources), "claims": dict(FALSE_CLAIMS)}


def validate_scheduler_contract(report, *, instruction, head, source_records):
    expected = build_scheduler_contract(instruction=instruction, head=head, source_records=source_records)
    if canonical_bytes(report) != canonical_bytes(expected):
        raise SchedulerConstraintError("contract replay does not match its complete source bindings")
    return True


def _validated_contract(contract):
    if type(contract) is not dict:
        raise SchedulerConstraintError("contract must be a plain object")
    try:
        validate_scheduler_contract(contract, instruction=contract["instruction"]["source_text"].encode("utf-8"),
                                    head=contract["head"], source_records=contract["sources"])
    except (KeyError, TypeError, AttributeError) as exc:
        raise SchedulerConstraintError("contract cannot reconstruct its public source bindings") from exc
    return {row["requirement_id"]: row for row in contract["clauses"]}


def evaluate_case(contract, case) -> dict:
    clauses = _validated_contract(contract)
    violations = []

    def fail(requirement_id, code, path):
        violations.append({"requirement_id": requirement_id,
                           "source_spans": copy.deepcopy(clauses[requirement_id]["source_spans"]),
                           "code": code, "path": path})

    def obj(value, fields, path, requirement_id="scheduler.input_schema"):
        if type(value) is not dict or set(value) != set(fields):
            fail(requirement_id, "closed_schema", path)
            return False
        return True

    def nat(value, path):
        if type(value) is not int or not 0 <= value <= MAX_INTEGER:
            fail("scheduler.input_schema", "bounded_natural_required", path)
            return False
        return True

    def identifier(value, path):
        if type(value) is not str or len(value.encode("utf-8")) > 512:
            fail("scheduler.input_schema", "bounded_string_required", path)
            return False
        return True

    try:
        raw = canonical_bytes(case)
        case_sha = _sha(raw)
        if len(raw) > MAX_CASE_BYTES:
            fail("scheduler.input_schema", "case_byte_bound", "$")
    except (SchedulerConstraintError, UnicodeError, ValueError):
        raw, case_sha = b"", None
        fail("scheduler.input_schema", "plain_finite_json_required", "$")
    case_id = case.get("case_id") if type(case) is dict and type(case.get("case_id")) is str else None
    shapes, counts, seen_buckets = set(), [], set()
    valid_top = obj(case, {"case_id", "buckets"}, "$")
    if valid_top:
        identifier(case["case_id"], "$.case_id")
        buckets = case["buckets"]
        if type(buckets) is not list or len(buckets) != 2:
            fail("scheduler.input_schema", "exactly_two_buckets_required", "$.buckets")
            buckets = []
    else:
        buckets = []
    if violations and case_sha is None:
        buckets = []
    for bi, bucket in enumerate(buckets):
        bp = f"$.buckets[{bi}]"
        if not obj(bucket, {"bucket_id", "requests", "plan", "metrics", "input_before", "input_after"}, bp):
            continue
        bucket_id = bucket["bucket_id"]
        if type(bucket_id) is not int or bucket_id not in (1, 2) or bucket_id in seen_buckets:
            fail("scheduler.input_schema", "unique_bucket_1_or_2_required", bp + ".bucket_id")
            continue
        seen_buckets.add(bucket_id)
        request_map, request_ids, rows = {}, [], []
        requests = bucket["requests"]
        if type(requests) is not list or len(requests) > MAX_REQUESTS:
            fail("scheduler.input_schema", "request_array_bound", bp + ".requests")
            requests = []
        for ri, request in enumerate(requests):
            rp = f"{bp}.requests[{ri}]"
            if not obj(request, {"request_id", "prompt_len", "gen_len"}, rp):
                continue
            good_id = identifier(request["request_id"], rp + ".request_id")
            good_prompt = nat(request["prompt_len"], rp + ".prompt_len")
            good_gen = nat(request["gen_len"], rp + ".gen_len")
            if good_id:
                rid = request["request_id"]
                request_ids.append(rid)
                if rid in request_map:
                    fail("scheduler.exact_once", "duplicate_input_id", rp + ".request_id")
                if good_prompt and good_gen:
                    request_map.setdefault(rid, request)
        plan = bucket["plan"]
        if type(plan) is not list or len(plan) > MAX_REQUESTS:
            fail("scheduler.input_schema", "plan_array_bound", bp + ".plan")
            plan = []
        output_ids, batch_shapes = [], {}
        for pi, row in enumerate(plan):
            pp = f"{bp}.plan[{pi}]"
            if not obj(row, {"request_id", "batch_id", "shape"}, pp):
                continue
            good_id = identifier(row["request_id"], pp + ".request_id")
            good_batch = identifier(row["batch_id"], pp + ".batch_id")
            if good_id:
                output_ids.append(row["request_id"])
            shape = row["shape"]
            if not obj(shape, {"seq_align", "heads_align", "hidden_align"}, pp + ".shape"):
                continue
            good_shape = True
            for name in ("seq_align", "heads_align", "hidden_align"):
                if not nat(shape[name], pp + ".shape." + name):
                    good_shape = False
            if not good_shape:
                continue
            seq, heads, hidden = shape["seq_align"], shape["heads_align"], shape["hidden_align"]
            st = (seq, heads, hidden)
            shapes.add(st)
            if seq % GRANULARITY:
                fail("scheduler.shape_alignment", "sequence_not_multiple_64", pp + ".shape.seq_align")
            if heads != HEADS:
                fail("scheduler.shape_alignment", "heads_not_32", pp + ".shape.heads_align")
            if hidden != HIDDEN:
                fail("scheduler.shape_alignment", "hidden_not_4096", pp + ".shape.hidden_align")
            if good_id and row["request_id"] in request_map:
                prompt = request_map[row["request_id"]]["prompt_len"]
                if seq < ((prompt + GRANULARITY - 1) // GRANULARITY) * GRANULARITY:
                    fail("scheduler.shape_alignment", "sequence_below_rounded_prompt", pp + ".shape.seq_align")
            if good_batch:
                batch = row["batch_id"]
                if batch in batch_shapes and batch_shapes[batch] != st:
                    fail("scheduler.batch_shape_equality", "inconsistent_batch_shape", pp + ".shape")
                batch_shapes.setdefault(batch, st)
            rows.append(row)
        for rid in sorted(set(output_ids)):
            if output_ids.count(rid) > 1:
                fail("scheduler.exact_once", "duplicate_output_id", bp + ".plan")
            if rid not in request_ids:
                fail("scheduler.exact_once", "unexpected_or_wrong_bucket_id", bp + ".plan")
        for rid in sorted(set(request_ids) - set(output_ids)):
            fail("scheduler.exact_once", "missing_output_id", bp + ".plan")
        threshold_id = f"scheduler.thresholds.bucket_{bucket_id}"
        metrics = bucket["metrics"]
        if obj(metrics, METRIC_NAMES, bp + ".metrics", threshold_id):
            for name in METRIC_NAMES:
                mp, metric = bp + ".metrics." + name, metrics[name]
                if not obj(metric, {"numerator", "denominator"}, mp, threshold_id):
                    continue
                numerator, denominator = metric["numerator"], metric["denominator"]
                if (type(numerator) is not int or type(denominator) is not int
                        or not 0 <= numerator <= MAX_INTEGER or not 1 <= denominator <= MAX_INTEGER):
                    fail(threshold_id, "bounded_nonnegative_rational_required", mp)
                    continue
                limit = clauses[threshold_id]["parameters"]["metrics"][name]
                if numerator * limit["denominator"] >= limit["numerator"] * denominator:
                    fail(threshold_id, "not_strictly_below_threshold", mp)
        inputs_good = True
        for name in ("input_before", "input_after"):
            if type(bucket[name]) is not str or len(bucket[name].encode("utf-8")) > MAX_INPUT_BYTES:
                fail("scheduler.input_schema", "input_utf8_byte_bound", bp + "." + name)
                inputs_good = False
        if inputs_good and bucket["input_before"].encode("utf-8") != bucket["input_after"].encode("utf-8"):
            fail("scheduler.input_unchanged", "observed_input_bytes_changed", bp)
        counts.append({"bucket_id": bucket_id, "input_rows": len(requests), "output_rows": len(plan),
                       "distinct_input_ids": len(set(request_ids)), "distinct_output_ids": len(set(output_ids)),
                       "batches": len(batch_shapes)})
    if seen_buckets != {1, 2}:
        fail("scheduler.input_schema", "both_bucket_identities_required", "$.buckets")
    if len(shapes) > MAX_SHAPES:
        fail("scheduler.global_shape_cap", "more_than_eight_global_shapes", "$.buckets")
    return {"schema": EVALUATION_SCHEMA, "contract_sha256": _sha(canonical_bytes(contract)),
            "case_sha256": case_sha, "case_id": case_id, "evaluation_passed": not violations,
            "violations": violations, "counts": sorted(counts, key=lambda row: row["bucket_id"]),
            "global_shape_count": len(shapes), "claims": dict(FALSE_CLAIMS)}


def validate_case_evaluation(report, *, contract, case):
    expected = evaluate_case(contract, case)
    if canonical_bytes(report) != canonical_bytes(expected):
        raise SchedulerConstraintError("case evaluation replay differs from bound inputs")
    return True


def _rational(value):
    value = Fraction(value)
    return {"numerator": value.numerator, "denominator": value.denominator}


def _fixture(bucket_id, sequences):
    requests, plan = [], []
    for index, sequence in enumerate(sequences):
        rid = f"bucket{bucket_id}-request{index}"
        requests.append({"request_id": rid, "prompt_len": sequence, "gen_len": 1})
        plan.append({"request_id": rid, "batch_id": f"batch{index}",
                     "shape": {"seq_align": sequence, "heads_align": HEADS, "hidden_align": HIDDEN}})
    text = "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in requests)
    return {"bucket_id": bucket_id, "requests": requests, "plan": plan,
            "metrics": {name: _rational(0) for name in METRIC_NAMES},
            "input_before": text, "input_after": text}


def authored_cases() -> list[dict]:
    """Explicit fixtures only; no benchmark input, test, solution, or source execution."""
    base = {"case_id": "valid-minimal", "buckets": [_fixture(1, [64]), _fixture(2, [128])]}
    cases = []

    def add(case_id, change=None, expected=False, ids=("scheduler.input_schema",), source=base):
        case = copy.deepcopy(source)
        case["case_id"] = case_id
        if change:
            change(case)
        cases.append({"case": case, "expected_pass": expected,
                      "intended_violation_ids": [] if expected else list(ids)})

    add("valid-minimal", expected=True)
    eight = {"case_id": "valid-eight-global-shapes",
             "buckets": [_fixture(1, [64, 128, 192, 256]), _fixture(2, [320, 384, 448, 512])]}
    add("valid-eight-global-shapes", expected=True, source=eight)
    def below(case):
        for bucket in case["buckets"]:
            for name, lexeme in zip(METRIC_NAMES, THRESHOLD_LEXEMES[bucket["bucket_id"]]):
                threshold = Fraction(Decimal(lexeme))
                bucket["metrics"][name] = _rational(threshold - min(Fraction(1, 1000), threshold / 2))
    add("valid-thresholds-strictly-below", below, expected=True)
    empty = {"case_id": "valid-empty-bounded-model", "buckets": [_fixture(1, []), _fixture(2, [])]}
    add("valid-empty-bounded-model", expected=True, source=empty)
    nine = {"case_id": "invalid-nine-global-shapes",
            "buckets": [_fixture(1, [64, 128, 192, 256]), _fixture(2, [320, 384, 448, 512, 576])]}
    add("invalid-nine-global-shapes", ids=("scheduler.global_shape_cap",), source=nine)
    add("missing-output", lambda c: c["buckets"][0]["plan"].clear(), ids=("scheduler.exact_once",))
    add("duplicate-output", lambda c: c["buckets"][0]["plan"].append(copy.deepcopy(c["buckets"][0]["plan"][0])), ids=("scheduler.exact_once",))
    add("extra-output", lambda c: c["buckets"][0]["plan"][0].update(request_id="invented"), ids=("scheduler.exact_once",))
    add("wrong-bucket-output", lambda c: c["buckets"][0]["plan"][0].update(request_id=c["buckets"][1]["requests"][0]["request_id"]), ids=("scheduler.exact_once",))
    add("duplicate-input", lambda c: c["buckets"][0]["requests"].append(copy.deepcopy(c["buckets"][0]["requests"][0])), ids=("scheduler.exact_once",))
    add("unaligned-sequence", lambda c: c["buckets"][0]["plan"][0]["shape"].update(seq_align=65), ids=("scheduler.shape_alignment",))
    add("below-rounded-prompt", lambda c: c["buckets"][1]["requests"][0].update(prompt_len=129), ids=("scheduler.shape_alignment",))
    add("wrong-heads", lambda c: c["buckets"][0]["plan"][0]["shape"].update(heads_align=31), ids=("scheduler.shape_alignment",))
    add("wrong-hidden", lambda c: c["buckets"][0]["plan"][0]["shape"].update(hidden_align=4095), ids=("scheduler.shape_alignment",))
    inconsistent = {"case_id": "inconsistent-batch-shapes", "buckets": [_fixture(1, [64, 128]), _fixture(2, [128])]}
    add("inconsistent-batch-shapes", lambda c: c["buckets"][0]["plan"][1].update(batch_id="batch0"),
        ids=("scheduler.batch_shape_equality",), source=inconsistent)
    add("mutated-input", lambda c: c["buckets"][0].update(input_after=c["buckets"][0]["input_before"] + " "), ids=("scheduler.input_unchanged",))
    add("negative-prompt", lambda c: c["buckets"][0]["requests"][0].update(prompt_len=-1))
    add("boolean-generation", lambda c: c["buckets"][0]["requests"][0].update(gen_len=True))
    add("oversized-natural", lambda c: c["buckets"][0]["plan"][0]["shape"].update(seq_align=MAX_INTEGER + 1))
    add("unknown-row-field", lambda c: c["buckets"][0]["plan"][0].update(notes="undeclared"))
    add("missing-shape-field", lambda c: c["buckets"][0]["plan"][0]["shape"].pop("hidden_align"))
    add("unknown-bucket", lambda c: c["buckets"][1].update(bucket_id=3))
    add("missing-bucket", lambda c: c["buckets"].pop())
    add("duplicate-bucket", lambda c: c["buckets"][1].update(bucket_id=1))
    add("missing-metric", lambda c: c["buckets"][0]["metrics"].pop("cost"), ids=("scheduler.thresholds.bucket_1",))
    add("unknown-metric", lambda c: c["buckets"][0]["metrics"].update(extra=_rational(0)), ids=("scheduler.thresholds.bucket_1",))
    add("zero-metric-denominator", lambda c: c["buckets"][0]["metrics"]["cost"].update(denominator=0), ids=("scheduler.thresholds.bucket_1",))
    add("boolean-metric-numerator", lambda c: c["buckets"][0]["metrics"]["cost"].update(numerator=False), ids=("scheduler.thresholds.bucket_1",))
    for bucket_id in (1, 2):
        for name, lexeme in zip(METRIC_NAMES, THRESHOLD_LEXEMES[bucket_id]):
            for direction, delta in (("equal", Fraction(0)), ("above", Fraction(1, 1000))):
                def change(c, bi=bucket_id - 1, metric=name, value=Fraction(Decimal(lexeme)) + delta):
                    c["buckets"][bi]["metrics"][metric] = _rational(value)
                add(f"threshold-{bucket_id}-{name}-{direction}", change,
                    ids=(f"scheduler.thresholds.bucket_{bucket_id}",))
    add("too-many-requests", lambda c: c["buckets"][0].update(requests=[copy.deepcopy(c["buckets"][0]["requests"][0]) for _ in range(257)]))
    add("too-many-output-rows", lambda c: c["buckets"][0].update(plan=[copy.deepcopy(c["buckets"][0]["plan"][0]) for _ in range(257)]))
    add("unknown-case-field", lambda c: c.update(expected_pass=True))
    return cases
