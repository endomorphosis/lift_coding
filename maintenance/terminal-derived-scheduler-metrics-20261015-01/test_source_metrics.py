"""Hand-calculated metrics, source-sensitive order, domain and evidence checks."""
import copy
from fractions import Fraction
import json
from pathlib import Path

import pytest

import source_metrics as sm
from source_profile import build_source_profile, EXPECTED_SOURCE_PATH


@pytest.fixture(scope="module")
def profile():
    predecessor = Path(__file__).resolve().parent.parent / "terminal-lean-jsonl-decoder-20261015-01" / "experiment-01"
    head = json.loads((predecessor / "result.json").read_bytes())["native_head"]
    raw = (predecessor / "source-repository" / EXPECTED_SOURCE_PATH).read_bytes()
    return build_source_profile(raw, head=head)


def req(rid="r", prompt=64, gen=1):
    return {"request_id": rid, "prompt_len": prompt, "gen_len": gen}


def plan(rid="r", bid="b", seq=64, heads=32, hidden=4096):
    return {"request_id": rid, "batch_id": bid,
            "shape": {"seq_align": seq, "heads_align": heads, "hidden_align": hidden}}


def derive(profile, requests=None, plans=None):
    return sm.derive_metrics(source_profile=profile,
                             requests=[req()] if requests is None else requests,
                             plan=[plan()] if plans is None else plans)


def val(row):
    return Fraction(row["numerator"], row["denominator"])


def test_single_hand_calculated_example_and_replay(profile):
    r = derive(profile)
    assert r["exact_rational_metrics"] == {
        "cost": {"numerator": 12_977_792, "denominator": 1},
        "pad_ratio": {"numerator": 0, "denominator": 1},
        "p95_latency_ms": {"numerator": 1_294_756, "denominator": 625},
        "sequential_time_ms": {"numerator": 1_294_756, "denominator": 625},
    }
    b = r["batches"][0]
    assert b["sum_sq_arith"] == 4096 and b["sum_lin"] == 64
    assert b["prefill_cost"] == 270336 and b["decode_cost"] == 135168
    assert r["compilation_cost"] == 2572288
    assert b["requests"][0]["shape_compile_latency_applied"] is True
    assert val(r["binary64_metrics"]["cost"]) == 12977792
    assert not any(r["claims"].values())
    assert sm.validate_metric_derivation(r, source_profile=profile, requests=[req()], plan=[plan()]) == r


def test_empty_and_zero_sequence_have_different_latency(profile):
    empty = derive(profile, [], [])
    assert all(val(row) == 0 for row in empty["exact_rational_metrics"].values())
    assert empty["p95_index"] is None and empty["batches"] == []
    zero = derive(profile, [req(prompt=0, gen=0)], [plan(seq=0)])
    assert val(zero["exact_rational_metrics"]["cost"]) == 10_000_000
    assert val(zero["exact_rational_metrics"]["p95_latency_ms"]) == 1508
    assert zero["shape_compilations"][0]["cost_skipped_nonpositive_seq"]
    assert zero["batches"][0]["requests"][0]["shape_compile_latency_applied"]


def test_missing_plan_is_computable_without_claiming_coverage(profile):
    r = derive(profile, [req()], [])
    assert r["input_request_count"] == 1 and r["calculated_request_count"] == 0
    assert val(r["exact_rational_metrics"]["cost"]) == 0


def test_batch_context_uses_prompt_not_declared_shape(profile):
    a = derive(profile)
    b = derive(profile, [req()], [plan(seq=128)])
    assert a["batches"][0]["S_max"] == b["batches"][0]["S_max"] == 64
    assert a["batches"][0]["decode_latency_units_per_request"] == b["batches"][0]["decode_latency_units_per_request"]
    assert a["exact_rational_metrics"]["p95_latency_ms"] == b["exact_rational_metrics"]["p95_latency_ms"]
    assert val(b["exact_rational_metrics"]["cost"]) - val(a["exact_rational_metrics"]["cost"]) == 6_668_288


def test_generation_is_raw_and_batch_padding_is_asymmetric(profile):
    requests = [req("a", 64, 3), req("b", 65, 1)]
    r = derive(profile, requests, [plan("a", seq=128), plan("b", seq=128)])
    b = r["batches"][0]
    assert b["G_max"] == 3 and b["S_max"] == 128
    assert b["sum_sq_arith"] == 128**2 + 129**2 + 130**2
    assert b["sum_lin"] == 128 + 129 + 130
    assert b["pad_prefill"] == 63 and b["pad_decode"] == 2
    assert val(r["exact_rational_metrics"]["pad_ratio"]) == Fraction(65, 133)


def test_compile_latency_uses_lexicographic_batch_and_first_encountered_request(profile):
    requests = [req("r1"), req("r2"), req("r3")]
    r = derive(profile, requests, [plan("r1", "z"), plan("r2", "a"), plan("r3", "a")])
    assert r["batch_order"] == ["z", "a"] and r["sorted_batch_order"] == ["a", "z"]
    assert r["shape_compilations"][0]["compile_latency_batch_id"] == "a"
    assert r["shape_compilations"][0]["compile_latency_request_id"] == "r2"
    assert [x["request_id"] for x in r["latency_concatenation"]] == ["r2", "r3", "r1"]
    compiled = [x["request_id"] for b in r["batches"] for x in b["requests"] if x["shape_compile_latency_applied"]]
    assert compiled == ["r2"]


def test_request_row_order_changes_which_latency_gets_compilation(profile):
    requests = [req("short", 64), req("long", 128)]
    first_short = derive(profile, requests, [plan("short", seq=128), plan("long", seq=128)])
    first_long = derive(profile, requests, [plan("long", seq=128), plan("short", seq=128)])
    assert first_short["shape_compilations"][0]["compile_latency_request_id"] == "short"
    assert first_long["shape_compilations"][0]["compile_latency_request_id"] == "long"
    assert val(first_short["exact_rational_metrics"]["p95_latency_ms"]) < val(first_long["exact_rational_metrics"]["p95_latency_ms"])


def test_source_last_shape_wins_without_waiving_contract_consistency(profile):
    requests = [req("a"), req("b", 128)]
    rows = [plan("a", seq=64), plan("b", seq=128)]
    r = derive(profile, requests, rows)
    assert r["batches"][0]["last_declared_shape"] == [128, 32, 4096]
    assert len(r["shape_compilations"]) == 1
    assert r["shape_compilations"][0]["shape"] == [128, 32, 4096]
    assert not r["claims"]["full_task_satisfaction_proved"]


def test_declared_heads_and_hidden_affect_identity_but_not_cost_formula(profile):
    requests = [req("a"), req("b")]
    same = derive(profile, requests, [plan("a", "a"), plan("b", "b")])
    distinct = derive(profile, requests, [plan("a", "a"), plan("b", "b", heads=31, hidden=4095)])
    assert len(same["shape_compilations"]) == 1 and len(distinct["shape_compilations"]) == 2
    assert val(distinct["exact_rational_metrics"]["cost"]) - val(same["exact_rational_metrics"]["cost"]) == 2572288


@pytest.mark.parametrize("prompt,gen,expected", [(53, 147, Fraction(11, 200)),
                                                (54, 147, Fraction(10, 201)),
                                                (52, 147, Fraction(12, 199)),
                                                (1, 419, Fraction(3, 20))])
def test_padding_thresholds_come_from_rows(profile, prompt, gen, expected):
    r = derive(profile, [req(prompt=prompt, gen=gen)], [plan()])
    assert val(r["exact_rational_metrics"]["pad_ratio"]) == expected
    assert float.fromhex(r["binary64_metrics"]["pad_ratio"]["hex"]) == float(expected)


def test_binary64_padding_ratio_is_retained_outside_finite_rational_bound(profile):
    # Prompt 127 pads by one; generation 873 makes real tokens 1000.
    r = derive(profile, [req(prompt=127, gen=873)], [plan(seq=128)])
    assert r["exact_rational_metrics"]["pad_ratio"] == {"numerator": 1, "denominator": 1000}
    assert r["binary64_metrics"]["pad_ratio"]["denominator"] == 2**60 > 10**18
    assert val(r["binary64_metrics"]["pad_ratio"]) != Fraction(1, 1000)


@pytest.mark.parametrize("count", [1, 2, 19, 20, 21, 40, 60, 100, 255, 256])
def test_percentile_matches_source_rounding_at_bounded_counts(profile, count):
    requests = [req(str(i)) for i in range(count)]
    rows = [plan(str(i)) for i in range(count)]
    r = derive(profile, requests, rows)
    assert r["p95_index"] == (95 * count + 99) // 100 - 1
    assert r["binary64_p95_index"] == r["p95_index"]
    assert val(r["exact_rational_metrics"]["cost"]) <= sm.COST_BOUND


def test_upper_domain_extremes_remain_exact_and_bounded(profile):
    requests = [req(str(i), 4096, 1024) for i in range(256)]
    rows = [plan(str(i), str(i), 8192, i, i) for i in range(256)]
    r = derive(profile, requests, rows)
    assert r["batch_count"] == 256 and len(r["shape_compilations"]) == 256
    cost = val(r["exact_rational_metrics"]["cost"])
    assert cost == val(r["binary64_metrics"]["cost"]) < sm.COST_BOUND < 2**53
    assert all(max(x.values()) <= 10**18 for x in r["exact_rational_metrics"].values())


@pytest.mark.parametrize("change", [
    lambda r,p: r[0].update(prompt_len=4097),
    lambda r,p: r[0].update(prompt_len=-1),
    lambda r,p: r[0].update(gen_len=1025),
    lambda r,p: r[0].update(gen_len=True),
    lambda r,p: r[0].update(notes="unknown"),
    lambda r,p: r.append(copy.deepcopy(r[0])),
    lambda r,p: p[0].update(request_id="unknown"),
    lambda r,p: p[0].update(batch_id="\0"),
    lambda r,p: p[0].update(batch_id="x" * 513),
    lambda r,p: p[0].update(notes="unknown"),
    lambda r,p: p[0]["shape"].update(seq_align=8193),
    lambda r,p: p[0]["shape"].update(heads_align=False),
    lambda r,p: p[0]["shape"].update(hidden_align=10**18+1),
    lambda r,p: p[0]["shape"].pop("heads_align"),
    lambda r,p: p.append(copy.deepcopy(p[0])),
    lambda r,p: r.extend(req(str(i)) for i in range(256)),
    lambda r,p: p.extend(plan(str(i)) for i in range(256)),
])
def test_closed_row_domains_refuse(profile, change):
    requests, rows = [req()], [plan()]
    change(requests, rows)
    with pytest.raises(sm.MetricDerivationError):
        derive(profile, requests, rows)


@pytest.mark.parametrize("field", ["source_profile_sha256", "head", "domain", "request_rows_sha256",
                                  "plan_rows_sha256", "batch_order", "batches", "shape_compilations",
                                  "pad_tokens", "real_tokens", "exact_rational_metrics", "binary64_metrics",
                                  "binary64_machine_profile", "claims", "semantic_scope"])
def test_tampered_report_is_not_accepted_by_outer_hashes(profile, field):
    r = derive(profile)
    r[field] = None
    with pytest.raises(sm.MetricDerivationError):
        sm.validate_metric_derivation(r, source_profile=profile, requests=[req()], plan=[plan()])


def test_forged_profile_is_refused(profile):
    p = copy.deepcopy(profile)
    p["constants"]["Tp_attn"]["binary64_hex"] = float(0.0).hex()
    with pytest.raises(sm.MetricDerivationError, match="profile"):
        derive(p)


def test_replay_detects_changed_rows_and_unknown_outer_fields(profile):
    r = derive(profile)
    for rows, plans in [([req(gen=2)], [plan()]), ([req()], [plan(seq=128)])]:
        with pytest.raises(sm.MetricDerivationError):
            sm.validate_metric_derivation(r, source_profile=profile, requests=rows, plan=plans)
    r["claimed_provider_tokens"] = 0
    with pytest.raises(sm.MetricDerivationError):
        sm.validate_metric_derivation(r, source_profile=profile, requests=[req()], plan=[plan()])
