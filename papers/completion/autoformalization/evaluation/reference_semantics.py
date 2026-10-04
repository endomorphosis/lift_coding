#!/usr/bin/env python3
"""New, finite Table 4 reconstruction; not historical output or a benchmark.

Expected witnesses are specified separately from actual semantic calculations.
All observations and pass/fail decisions derive from computed values.  The CLI
retains mismatches in its result and exits nonzero; it never changes an oracle
to fit an observation.  The tiny trace/norm languages below are conformance
fixtures, not project compiler/model execution or unbounded soundness proofs.
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
from pathlib import Path
import sys
from typing import Any, Callable, Iterable

SCHEMA = "autoformalization-reference-semantics-results/v3"
SUITE_ID = "AF-006-finite-reference-reconstruction"
WORLDS = (0, 1)
EDGES = tuple(itertools.product(WORLDS, repeat=2))
MODAL_WITNESS_VALUATION = frozenset({1})

# Frozen manuscript expectations; never used as actual calculation inputs.
EXPECTED_COUNTS = (512, 32, 72, 1, 1, 64, 1, 1, 4, 16, 3, 1)
EXPECTED_OUTCOMES = (
    "No finite countermodel", "No finite countermodel", "No finite countermodel",
    "Explicit separating model", "Explicit separating model", "26 disagreements",
    "Explicit separating trace", "Diagonal-relation witness",
    "Safe relation 0; unsafe 1 violation", "1 violating assignment",
    "Unknown, unresolved, bounded satisfaction",
    "Equal recompiled IR; unequal source meaning",
)
EXPECTED_VALUES = {
    "C01": {"counterexample_count": 0},
    "C02": {"counterexample_count": 0},
    "C03": {"counterexample_count": 0, "duality_failure_count": 0},
    "C04": {"modal_truth": True, "actual_truth": False, "separates": True},
    "C05": {"modal_truth": True, "actual_truth": False, "separates": True},
    "C06": {"disagreement_count": 26, "until_true_conjunction_false": 26,
             "until_false_conjunction_true": 0},
    "C07": {"current_truth": True, "always_truth": False, "separates": True},
    "C08": {"for_all_exists": True, "exists_for_all": False, "separates": True},
    "C09": {"violation_flags": [False, True, False, False],
             "safe_relation_violation_count": 0, "unsafe_relation_violation_count": 1},
    "C10": {"violation_count": 1,
             "violating_assignments": [{"request_observed": True, "window_complete": True,
                                         "write": True, "audit": False}]},
    "C11": {"status_sequence": ["unknown", "unresolved_identity",
                                "satisfied_within_observed_window"]},
    "C12": {"recompiled_ir_equal": True, "source_meaning_equal": False,
             "meaning_disagreement_count": 1},
}


def implication(left: bool, right: bool) -> bool:
    return not left or right


def all_relations() -> Iterable[frozenset[tuple[int, int]]]:
    for mask in range(1 << len(EDGES)):
        yield frozenset(edge for bit, edge in enumerate(EDGES) if mask & (1 << bit))


def valuations() -> Iterable[frozenset[int]]:
    for mask in range(1 << len(WORLDS)):
        yield frozenset(world for world in WORLDS if mask & (1 << world))


def box(relation: frozenset[tuple[int, int]], world: int,
        predicate: Callable[[int], bool]) -> bool:
    return all(predicate(target) for source, target in relation if source == world)


def diamond(relation: frozenset[tuple[int, int]], world: int,
            predicate: Callable[[int], bool]) -> bool:
    return any(predicate(target) for source, target in relation if source == world)


def is_reflexive(relation: frozenset[tuple[int, int]]) -> bool:
    return all((world, world) in relation for world in WORLDS)


def is_serial(relation: frozenset[tuple[int, int]]) -> bool:
    return all(any(source == world for source, _ in relation) for world in WORLDS)


def strong_until(p: tuple[bool, ...], q: tuple[bool, ...]) -> bool:
    # Strong finite until at position zero; p holds strictly before a q witness.
    return any(q[index] and all(p[:index]) for index in range(len(p)))


def always(trace: tuple[bool, ...]) -> bool:
    return all(trace)


def quantified_values(domain: tuple[str, ...], relation: set[tuple[str, str]]) -> tuple[bool, bool]:
    return (all(any((x, y) in relation for y in domain) for x in domain),
            any(all((x, y) in relation for x in domain) for y in domain))


def write_violation(approved: bool, write: bool) -> bool:
    return write and not approved


def audit_violation(request_observed: bool, window_complete: bool, write: bool, audit: bool) -> bool:
    return request_observed and window_complete and write and not audit


def trace_status(case: dict[str, Any]) -> str:
    if case["policy_identity"] != case["trace_identity"]:
        return "unresolved_identity"
    if not case["capture_complete"]:
        return "unknown"
    if audit_violation(case["request_observed"], case["capture_complete"], case["write"], case["audit_observed"]):
        return "violated_within_observed_window"
    return "satisfied_within_observed_window"


def encode_norm(source: dict[str, str]) -> dict[str, str]:
    # Intentionally lossy fixture encoder, not the project's compiler.
    return {"obligation": source["obligation"]}


def realize_norm(ir: dict[str, str]) -> str:
    return "must " + ir["obligation"] + (" unless " + ir["exception"] if "exception" in ir else "")


def parse_norm(text: str) -> dict[str, str]:
    # Closed two-template source language for the single shared-loss fixture.
    if text == "must audit":
        return {"obligation": "audit"}
    if text == "must audit unless exempt":
        return {"obligation": "audit", "exception": "exempt"}
    raise ValueError("outside the two-template norm fixture")


def norm_satisfied(norm: dict[str, str], exempt: bool, obligation_holds: bool) -> bool:
    return implication(not exempt, obligation_holds) if "exception" in norm else obligation_holds


def _equal(actual: Any, expected: Any) -> bool:
    # Do not let Python's True == 1 coerce an incorrect observation into a pass.
    return type(actual) is type(expected) and actual == expected


def _record(check_id: str, title: str, actual_cases: list[Any], actual: dict[str, Any],
            enumeration: str) -> dict[str, Any]:
    index = int(check_id[1:]) - 1
    expected = EXPECTED_VALUES[check_id]
    comparisons = {key: _equal(actual.get(key), value) for key, value in expected.items()}
    comparisons["case_count"] = len(actual_cases) == EXPECTED_COUNTS[index]
    return {"check_id": check_id, "title": title, "case_count": len(actual_cases),
            "expected_case_count": EXPECTED_COUNTS[index],
            "expected_outcome": EXPECTED_OUTCOMES[index], "expected_values": expected,
            "actual_output": actual, "enumeration": enumeration,
            "checks": comparisons, "match": all(comparisons.values())}


def check_normal_modal_distribution() -> dict[str, Any]:
    cases, counterexamples = [], []
    for relation, p, q, world in itertools.product(all_relations(), valuations(), valuations(), WORLDS):
        case = {"relation": sorted(relation), "p": sorted(p), "q": sorted(q), "world": world}
        cases.append(case)
        antecedent = box(relation, world, lambda target: implication(target in p, target in q))
        consequent = implication(box(relation, world, lambda target: target in p),
                                  box(relation, world, lambda target: target in q))
        if not implication(antecedent, consequent):
            counterexamples.append(case)
    return _record("C01", "Normal modal distribution", cases,
                   {"counterexample_count": len(counterexamples), "counterexamples": counterexamples},
                   "16 relations × 4 p-valuations × 4 q-valuations × 2 designated worlds")


def check_reflexive_factivity() -> dict[str, Any]:
    cases, counterexamples = [], []
    for relation, p, world in itertools.product(filter(is_reflexive, all_relations()), valuations(), WORLDS):
        case = {"relation": sorted(relation), "p": sorted(p), "world": world}
        cases.append(case)
        if box(relation, world, lambda target: target in p) and world not in p:
            counterexamples.append(case)
    return _record("C02", "Reflexive factivity", cases,
                   {"counterexample_count": len(counterexamples), "counterexamples": counterexamples},
                   "4 reflexive relations × 4 p-valuations × 2 designated worlds")


def check_serial_d() -> dict[str, Any]:
    cases, counterexamples, duality_failures = [], [], []
    for relation, p, world in itertools.product(filter(is_serial, all_relations()), valuations(), WORLDS):
        case = {"relation": sorted(relation), "p": sorted(p), "world": world}
        cases.append(case)
        obligation = box(relation, world, lambda target: target in p)
        permission = diamond(relation, world, lambda target: target in p)
        if permission != (not box(relation, world, lambda target: target not in p)):
            duality_failures.append(case)
        if obligation and not permission:
            counterexamples.append(case)
    return _record("C03", "Serial D", cases,
                   {"counterexample_count": len(counterexamples), "counterexamples": counterexamples,
                    "duality_failure_count": len(duality_failures), "duality_failures": duality_failures},
                   "9 serial relations × 4 p-valuations × 2 designated worlds; O(p) implies P(p)")


def check_modal_separation(check_id: str, title: str) -> dict[str, Any]:
    relation = frozenset({(0, 1), (1, 1)})
    modal_truth = box(relation, 0, lambda target: target in MODAL_WITNESS_VALUATION)
    actual_truth = 0 in MODAL_WITNESS_VALUATION
    witness = {"actual_world": 0, "relation": sorted(relation), "p": sorted(MODAL_WITNESS_VALUATION)}
    return _record(check_id, title, [witness],
                   {"modal_truth": modal_truth, "actual_truth": actual_truth,
                    "separates": modal_truth and not actual_truth, "witness": witness},
                   "One specified non-reflexive actual/accessible-world model")


def check_until_not_conjunction() -> dict[str, Any]:
    cases, disagreements = [], []
    for bits in itertools.product((False, True), repeat=6):
        p, q = bits[:3], bits[3:]
        until_value, conjunction = strong_until(p, q), p[0] and q[0]
        case = {"p": list(p), "q": list(q), "strong_until": until_value, "conjunction_at_zero": conjunction}
        cases.append(case)
        if until_value != conjunction:
            disagreements.append(case)
    return _record("C06", "Until not conjunction", cases,
                   {"disagreement_count": len(disagreements), "disagreements": disagreements,
                    "until_true_conjunction_false": sum(x["strong_until"] and not x["conjunction_at_zero"] for x in disagreements),
                    "until_false_conjunction_true": sum(not x["strong_until"] and x["conjunction_at_zero"] for x in disagreements)},
                   "All 64 length-three Boolean p/q trace pairs; p strictly before q")


def check_always() -> dict[str, Any]:
    trace = (True, False, True)
    now, throughout = trace[0], always(trace)
    return _record("C07", "Always not current truth", [trace],
                   {"current_truth": now, "always_truth": throughout, "separates": now != throughout,
                    "trace_p": list(trace)}, "One length-three separating trace")


def check_quantifier_order() -> dict[str, Any]:
    domain = ("alice", "bob")
    relation = {(x, x) for x in domain}
    forall_exists, exists_forall = quantified_values(domain, relation)
    witness = {"domain": list(domain), "relation": sorted(relation)}
    return _record("C08", "Quantifier order", [witness],
                   {"for_all_exists": forall_exists, "exists_for_all": exists_forall,
                    "separates": forall_exists != exists_forall, "witness": witness},
                   "One two-element diagonal relation")


def check_guarded_writes() -> dict[str, Any]:
    inputs = ((True, True), (False, True), (False, False), (True, False))
    cases = [{"approved": a, "write": w, "violation": write_violation(a, w)} for a, w in inputs]
    return _record("C09", "Guarded writes", cases,
                   {"violation_flags": [x["violation"] for x in cases],
                    "safe_relation_violation_count": int(cases[0]["violation"]),
                    "unsafe_relation_violation_count": int(cases[1]["violation"]), "cases": cases},
                   "All four approved/write valuations; safe approved write and unsafe unapproved write distinguished")


def check_complete_audit_window() -> dict[str, Any]:
    keys = ("request_observed", "window_complete", "write", "audit")
    assignments = [dict(zip(keys, bits)) for bits in itertools.product((False, True), repeat=4)]
    violations = [case for case in assignments if audit_violation(**case)]
    return _record("C10", "Complete audit window", assignments,
                   {"violation_count": len(violations), "violating_assignments": violations},
                   "All sixteen request-observed/window-complete/write/audit assignments")


def check_incomplete_unaligned_traces() -> dict[str, Any]:
    base = {"request_observed": True, "write": True,
            "policy_identity": "tenant-a:admin", "trace_identity": "tenant-a:admin"}
    cases = [{**base, "capture_complete": False, "audit_observed": False},
             {**base, "capture_complete": True, "audit_observed": True, "trace_identity": "tenant-b:admin"},
             {**base, "capture_complete": True, "audit_observed": True}]
    return _record("C11", "Incomplete/unaligned traces", cases,
                   {"status_sequence": [trace_status(case) for case in cases], "cases": cases},
                   "Three specified trace observations; compute completeness and grounded-identity decisions")


def check_round_trip_shared_loss() -> dict[str, Any]:
    original = parse_norm("must audit unless exempt")
    first_ir = encode_norm(original)
    realized = realize_norm(first_ir)
    realized_source = parse_norm(realized)
    second_ir = encode_norm(realized_source)
    differences = []
    for exempt, obligation_holds in itertools.product((False, True), repeat=2):
        before = norm_satisfied(original, exempt, obligation_holds)
        after = norm_satisfied(realized_source, exempt, obligation_holds)
        if before != after:
            differences.append({"exempt": exempt, "obligation_holds": obligation_holds,
                                "source_truth": before, "round_trip_truth": after})
    return _record("C12", "Round-trip shared loss", [original],
                   {"recompiled_ir_equal": first_ir == second_ir,
                    "source_meaning_equal": not differences, "meaning_disagreement_count": len(differences),
                    "original_source": original, "first_ir": first_ir, "realized_source": realized,
                    "recompiled_ir": second_ir, "meaning_counterexamples": differences},
                   "One deliberately lossy two-template round trip; compare meaning on all four exempt/obligation valuations")


def evaluate_suite(*, strict: bool = True) -> dict[str, Any]:
    checks = [check_normal_modal_distribution(), check_reflexive_factivity(), check_serial_d(),
              check_modal_separation("C04", "Obligation not actuality"),
              check_modal_separation("C05", "Belief without factivity"),
              check_until_not_conjunction(), check_always(), check_quantifier_order(),
              check_guarded_writes(), check_complete_audit_window(),
              check_incomplete_unaligned_traces(), check_round_trip_shared_loss()]
    ids = [check["check_id"] for check in checks]
    if ids != [f"C{i:02d}" for i in range(1, 13)]:
        raise AssertionError("reference inventory must contain exactly C01 through C12")
    matched = all(check["match"] for check in checks)
    result = {"schema": SCHEMA, "suite_id": SUITE_ID, "execution_kind": "new_reconstruction_execution",
              "historical_output_status": "not_recovered_not_executed",
              "implementation": {"language": "Python", "standard_library_only": True,
                                 "python_implementation": sys.implementation.name,
                                 "python_version": sys.version.split()[0]},
              "claims": {"finite_result": "All twelve finite expected outcomes matched." if matched else
                         "At least one finite outcome or enumeration differs from the frozen expectation.",
                         "non_claims": ["Not recovered historical output.", "Not independent human annotation.",
                                        "Not project compiler/model/prover execution or unbounded soundness.",
                                        "Not natural-distribution accuracy or benchmark performance."]},
              "checks": checks,
              "summary": {"check_count": len(checks), "case_counts": [c["case_count"] for c in checks],
                          "total_enumerated_cases": sum(c["case_count"] for c in checks),
                          "all_expected_outcomes_matched": matched,
                          "failed_check_ids": [c["check_id"] for c in checks if not c["match"]],
                          "strong_until_conjunction_disagreements": {
                              "numerator": checks[5]["actual_output"]["disagreement_count"],
                              "denominator": checks[5]["case_count"]}}}
    if strict and not matched:
        raise AssertionError("finite reference mismatch: " + ", ".join(result["summary"]["failed_check_ids"]))
    return result


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("reference_results.json"))
    args = parser.parse_args(argv)
    result = evaluate_suite(strict=False)
    write_json(args.output, result)
    print(json.dumps({"suite_id": SUITE_ID, "output": str(args.output), **result["summary"]}, sort_keys=True))
    return 0 if result["summary"]["all_expected_outcomes_matched"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
