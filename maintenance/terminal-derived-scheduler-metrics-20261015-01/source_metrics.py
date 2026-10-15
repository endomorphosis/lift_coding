"""Derive bounded scheduler metrics from strict rows and a pinned source profile.

The integer/decimal model and the ordered binary64 shadow are independent
calculations. Neither executes the repository source or proves Python/source
equivalence. Supplied metric values are deliberately absent from this API.
"""
from __future__ import annotations

import copy
from fractions import Fraction
import hashlib
import json
import math
import sys


SCHEMA = "terminal-source-derived-scheduler-metrics@1"
METRIC_NAMES = ("cost", "pad_ratio", "p95_latency_ms", "sequential_time_ms")
LATENCY_UNITS_PER_MS = 2500
COST_BOUND = 18_240_065_142_784
MAX_INTEGER = 10**18
DOMAIN = {"max_prompt_len": 4096, "max_gen_len": 1024,
          "max_seq_align": 8192, "max_rows_per_bucket": 256}
FALSE_CLAIMS = {
    "original_source_imported_or_executed": False,
    "source_runtime_equivalence_proved": False,
    "source_model_equivalence_proved": False,
    "binary64_implementation_formally_verified": False,
    "ideal_decimal_metrics_are_runtime_observations": False,
    "full_task_satisfaction_proved": False,
    "formal_proof": False,
    "convergence_proved": False,
    "planning_or_dispatch_authority": False,
    "original_semantic_coverage_complete": False,
}


class MetricDerivationError(ValueError):
    """Rows or source profile are outside the explicit bounded calculation."""


def canonical_bytes(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False).encode("ascii")
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise MetricDerivationError("metric evidence must be finite plain JSON") from exc


def _sha(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _ratio(numerator, denominator=1):
    value = Fraction(numerator, denominator)
    return {"numerator": value.numerator, "denominator": value.denominator}


def _binary(value):
    if type(value) is not float or not math.isfinite(value) or value < 0:
        raise MetricDerivationError("binary64 shadow produced a nonfinite or negative value")
    numerator, denominator = value.as_integer_ratio()
    return {"numerator": numerator, "denominator": denominator, "hex": value.hex()}


def _machine_profile():
    f = sys.float_info
    if (sys.implementation.name != "cpython" or f.radix != 2 or f.mant_dig != 53
            or f.max_exp != 1024 or f.min_exp != -1021 or f.rounds != 1):
        raise MetricDerivationError("binary64 shadow requires the selected CPython IEEE profile")
    return {"implementation": sys.implementation.name,
            "python_version": list(sys.version_info[:3]),
            "radix": f.radix, "mant_dig": f.mant_dig,
            "max_exp": f.max_exp, "min_exp": f.min_exp, "rounds": f.rounds,
            "formal_runtime_semantics_certificate": False}


def _identifier(value, location):
    if type(value) is not str:
        raise MetricDerivationError(location + " must be a UTF-8 string")
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise MetricDerivationError(location + " is not a Unicode scalar string") from exc
    if len(encoded) > 512 or "\0" in value:
        raise MetricDerivationError(location + " exceeds the strict identifier domain")


def _nat(value, maximum, location):
    if type(value) is not int or not 0 <= value <= maximum:
        raise MetricDerivationError(location + " is outside the bounded natural domain")


def _rows(requests, plan):
    if (type(requests) is not list or type(plan) is not list
            or len(requests) > 256 or len(plan) > 256):
        raise MetricDerivationError("request and plan arrays must have at most 256 rows")
    request_map = {}
    for index, row in enumerate(requests):
        if type(row) is not dict or set(row) != {"request_id", "prompt_len", "gen_len"}:
            raise MetricDerivationError("request row has missing or unknown fields")
        _identifier(row["request_id"], "request_id")
        _nat(row["prompt_len"], 4096, "prompt_len")
        _nat(row["gen_len"], 1024, "gen_len")
        if row["request_id"] in request_map:
            raise MetricDerivationError("request IDs must be unique")
        request_map[row["request_id"]] = row
    seen = set()
    for row in plan:
        if type(row) is not dict or set(row) != {"request_id", "batch_id", "shape"}:
            raise MetricDerivationError("plan row has missing or unknown fields")
        _identifier(row["request_id"], "plan request_id")
        _identifier(row["batch_id"], "batch_id")
        if row["request_id"] in seen:
            raise MetricDerivationError("plan request IDs must be unique")
        seen.add(row["request_id"])
        if row["request_id"] not in request_map:
            raise MetricDerivationError("plan references an unknown request_id")
        shape = row["shape"]
        if (type(shape) is not dict
                or set(shape) != {"seq_align", "heads_align", "hidden_align"}):
            raise MetricDerivationError("shape has missing or unknown fields")
        _nat(shape["seq_align"], 8192, "seq_align")
        # The source uses these dimensions for shape identity, not arithmetic.
        # The separate scheduler contract rejects values other than 32/4096.
        _nat(shape["heads_align"], MAX_INTEGER, "heads_align")
        _nat(shape["hidden_align"], MAX_INTEGER, "hidden_align")
    return request_map


def _exact_cost(value, expected, location):
    if (type(value) is not float or not math.isfinite(value)
            or value.as_integer_ratio() != (expected, 1)
            or not 0 <= expected <= COST_BOUND or expected >= 2**53):
        raise MetricDerivationError(location + " failed the exact integral binary64 bound")
    return value


def derive_metrics(*, source_profile: dict, requests: list, plan: list) -> dict:
    """Calculate one bucket, preserving source order and last-row-wins shapes."""
    from source_profile import validate_source_profile_shape
    try:
        validate_source_profile_shape(source_profile)
    except (TypeError, ValueError, KeyError, RecursionError) as exc:
        raise MetricDerivationError("source profile did not replay") from exc
    if (source_profile["domain"] != DOMAIN
            or source_profile["defaults"] != {"HEADS": 32, "HIDDEN": 4096,
                                               "granularity": 64}):
        raise MetricDerivationError("source profile is not the bounded default profile")
    machine = _machine_profile()
    request_map = _rows(requests, plan)
    constants = {name: float.fromhex(row["binary64_hex"])
                 for name, row in source_profile["constants"].items()}
    batches, batch_shapes = {}, {}
    for row in plan:
        bid = row["batch_id"]
        batches.setdefault(bid, []).append(request_map[row["request_id"]])
        shape = row["shape"]
        batch_shapes[bid] = tuple(shape[key] for key in (
            "seq_align", "heads_align", "hidden_align"))

    batch_traces, ordered_traces = {}, []
    cost_total, pad_total, real_total, shadow_cost_total = 0, 0, 0, 0.0
    for bid, rows in batches.items():
        aligned = [((row["prompt_len"] + 63) // 64) * 64 for row in rows]
        smax, gmax = max(aligned), max(row["gen_len"] for row in rows)
        n = gmax
        sum_sq = n * smax * smax + smax * n * (n - 1) + n * (n - 1) * (2 * n - 1) // 6
        sum_lin = n * smax + n * (n - 1) // 2
        shadow_lin = n * smax + n * (n - 1) / 2
        _exact_cost(float(shadow_lin), sum_lin, "decode linear arithmetic")
        decode_cost = sum_sq + 2048 * sum_lin
        shadow_decode_cost = constants["Kd_attn"] * sum_sq + (constants["Kd_mlp"] * 4096) * shadow_lin
        _exact_cost(shadow_decode_cost, decode_cost, "decode cost per request")
        decode_units = 3 * sum_sq + 6144 * sum_lin
        shadow_decode_lat = constants["Td_attn"] * sum_sq + (constants["Td_mlp"] * 4096) * shadow_lin
        prefill_costs, shadow_prefills, request_traces = [], [], []
        for row, aligned_prompt in zip(rows, aligned):
            prefill_cost = 2 * aligned_prompt**2 + aligned_prompt * 4096
            shadow_prefill = (constants["Kp_attn"] * aligned_prompt**2
                              + constants["Kp_mlp"] * (aligned_prompt * 4096))
            _exact_cost(shadow_prefill, prefill_cost, "prefill cost")
            prefill_units = 5 * aligned_prompt**2 + 15360 * aligned_prompt
            shadow_prefill_lat = (constants["Tp_attn"] * aligned_prompt**2
                                  + constants["Tp_mlp"] * (aligned_prompt * 4096))
            shadow_before = shadow_prefill_lat + shadow_decode_lat
            shadow_after = shadow_before + constants["Tbatch_overhead_ms"]
            request_traces.append({
                "request_id": row["request_id"], "prompt_len": row["prompt_len"],
                "gen_len": row["gen_len"], "aligned_prompt": aligned_prompt,
                "prefill_cost": prefill_cost, "prefill_latency_units": prefill_units,
                "prefill_latency_binary64": _binary(shadow_prefill_lat),
                "latency_units_before_overheads": prefill_units + decode_units,
                "latency_units_after_batch_overhead": prefill_units + decode_units + 20_000,
                "latency_units_final": prefill_units + decode_units + 20_000,
                "latency_binary64_before_overheads": _binary(shadow_before),
                "latency_binary64_after_batch_overhead": _binary(shadow_after),
                "latency_binary64_final": _binary(shadow_after),
                "shape_compile_latency_applied": False,
            })
            prefill_costs.append(prefill_cost)
            shadow_prefills.append(shadow_prefill)
        prefill_cost_total = sum(prefill_costs)
        _exact_cost(float(sum(shadow_prefills)), prefill_cost_total, "prefill builtin sum")
        batch_cost = prefill_cost_total + len(rows) * decode_cost
        shadow_batch_cost = sum(shadow_prefills) + len(rows) * shadow_decode_cost
        _exact_cost(shadow_batch_cost, batch_cost, "batch total cost")
        cost_total += batch_cost
        shadow_cost_total += shadow_batch_cost
        _exact_cost(shadow_cost_total, cost_total, "batch cost accumulation")
        pad_prefill = sum(s - row["prompt_len"] for s, row in zip(aligned, rows))
        pad_decode = sum(gmax - row["gen_len"] for row in rows)
        real = sum(row["prompt_len"] + row["gen_len"] for row in rows)
        pad_total += pad_prefill + pad_decode
        real_total += real
        trace = {
            "batch_id": bid, "last_declared_shape": list(batch_shapes[bid]),
            "request_count": len(rows), "S_max": smax, "G_max": gmax,
            "sum_sq_arith": sum_sq, "sum_lin": sum_lin,
            "sum_lin_binary64": _binary(float(shadow_lin)),
            "prefill_cost": prefill_cost_total, "decode_cost_per_request": decode_cost,
            "decode_cost": len(rows) * decode_cost, "cost": batch_cost,
            "cost_binary64": _binary(shadow_batch_cost),
            "decode_latency_units_per_request": decode_units,
            "decode_latency_binary64_per_request": _binary(shadow_decode_lat),
            "pad_prefill": pad_prefill, "pad_decode": pad_decode, "real_tokens": real,
            "requests": request_traces,
        }
        batch_traces[bid] = trace
        ordered_traces.append(trace)

    compile_cost, shadow_compile_cost, shape_traces = 0, 0.0, []
    unique_shapes = sorted(set(batch_shapes.values()))
    for shape in unique_shapes:
        s, h, hidden = shape
        # Source set iteration is immaterial here: every term and partial sum
        # is a nonnegative exactly representable integer under COST_BOUND.
        term = 500 * s**2 + 8192 * s if s > 0 else 0
        shadow_term = (constants["Kshape_attn"] * s**2
                       + constants["Kshape_mlp"] * (s * 4096)) if s > 0 else 0.0
        _exact_cost(shadow_term, term, "shape compile cost")
        compile_cost += term
        shadow_compile_cost += shadow_term
        _exact_cost(shadow_compile_cost, compile_cost, "shape compile accumulation")
        bids = sorted(bid for bid in batch_shapes if batch_shapes[bid] == shape)
        first = batch_traces[bids[0]]["requests"][0]
        first["latency_units_final"] += 3_750_000
        before_shadow = float.fromhex(first["latency_binary64_final"]["hex"])
        first["latency_binary64_final"] = _binary(before_shadow + constants["Tshape_compile_ms"])
        first["shape_compile_latency_applied"] = True
        shape_traces.append({"shape": list(shape), "cost_skipped_nonpositive_seq": s <= 0,
                             "compile_cost": term, "compile_cost_binary64": _binary(shadow_term),
                             "sorted_batch_ids": bids, "compile_latency_batch_id": bids[0],
                             "compile_latency_request_id": first["request_id"],
                             "compile_latency_units": 3_750_000})
    cost_total += compile_cost
    shadow_cost_total += shadow_compile_cost
    _exact_cost(shadow_cost_total, cost_total, "cost with compilation")
    overhead_cost = 10_000_000 * len(batches)
    shadow_overhead = constants["Kbatch_overhead_cost"] * len(batches)
    _exact_cost(shadow_overhead, overhead_cost, "batch overhead cost")
    cost_total += overhead_cost
    shadow_cost_total += shadow_overhead
    _exact_cost(shadow_cost_total, cost_total, "final cost")

    concatenated, units, shadow_lats = [], [], []
    sequential_units, shadow_sequential, sequential_trace = 0, 0.0, []
    for bid in sorted(batch_traces):
        rows = batch_traces[bid]["requests"]
        batch_units = [row["latency_units_final"] for row in rows]
        batch_floats = [float.fromhex(row["latency_binary64_final"]["hex"]) for row in rows]
        slow_units, slow_float = max(batch_units), max(batch_floats)
        sequential_units += slow_units
        shadow_sequential += slow_float
        sequential_trace.append({"batch_id": bid, "max_latency_units": slow_units,
                                 "max_latency_binary64": _binary(slow_float),
                                 "cumulative_units": sequential_units,
                                 "cumulative_binary64": _binary(shadow_sequential)})
        for row, u, v in zip(rows, batch_units, batch_floats):
            concatenated.append({"batch_id": bid, "request_id": row["request_id"],
                                 "latency_units": u, "latency_binary64": _binary(v)})
            units.append(u)
            shadow_lats.append(v)
    count = len(units)
    ideal_index = max(0, (95 * count + 99) // 100 - 1) if count else None
    shadow_index = max(0, min(count - 1, int(math.ceil(0.95 * count) - 1))) if count else None
    if ideal_index != shadow_index:
        raise MetricDerivationError("source percentile index differs inside the selected finite domain")
    p95_units = sorted(units)[ideal_index] if count else 0
    shadow_p95 = sorted(shadow_lats)[shadow_index] if count else 0.0
    shadow_pad = pad_total / max(1, real_total)
    exact = {"cost": _ratio(cost_total), "pad_ratio": _ratio(pad_total, max(1, real_total)),
             "p95_latency_ms": _ratio(p95_units, LATENCY_UNITS_PER_MS),
             "sequential_time_ms": _ratio(sequential_units, LATENCY_UNITS_PER_MS)}
    if any(max(row.values()) > MAX_INTEGER for row in exact.values()):
        raise MetricDerivationError("derived ideal metrics exceed the finite checker rational domain")
    return {
        "schema": SCHEMA, "source_profile_sha256": _sha(source_profile),
        "head": copy.deepcopy(source_profile["head"]), "domain": dict(DOMAIN),
        "request_rows_sha256": _sha(requests), "plan_rows_sha256": _sha(plan),
        "input_request_count": len(requests), "plan_row_count": len(plan),
        "calculated_request_count": count, "batch_count": len(batches),
        "latency_units_per_ms": LATENCY_UNITS_PER_MS,
        "exact_cost_upper_bound": COST_BOUND,
        "cost_order_independence_basis": "all_nonnegative_integral_terms_and_partial_sums_below_2_pow_53",
        "batch_order": list(batches), "sorted_batch_order": sorted(batches),
        "batches": ordered_traces, "shape_compilations": shape_traces,
        "compilation_cost": compile_cost, "batch_overhead_cost": overhead_cost,
        "pad_tokens": pad_total, "real_tokens": real_total,
        "latency_concatenation": concatenated, "sequential_accumulation": sequential_trace,
        "p95_index": ideal_index, "binary64_p95_index": shadow_index,
        "exact_rational_metrics": exact,
        "binary64_metrics": {"cost": _binary(shadow_cost_total), "pad_ratio": _binary(shadow_pad),
                             "p95_latency_ms": _binary(shadow_p95),
                             "sequential_time_ms": _binary(shadow_sequential)},
        "binary64_machine_profile": machine,
        "source_output_field_map": {"sequential_time_ms": "sequential_timecost"},
        "semantic_scope": "bounded_default_decimal_model_and_ordered_host_binary64_shadow_not_source_runtime_equivalence",
        "claims": dict(FALSE_CLAIMS),
    }


def validate_metric_derivation(report, *, source_profile, requests, plan):
    expected = derive_metrics(source_profile=source_profile, requests=requests, plan=plan)
    if canonical_bytes(report) != canonical_bytes(expected):
        raise MetricDerivationError("metric derivation differs from its exact source profile and rows")
    return expected
