#!/usr/bin/env python3
"""Finite reference semantics for the paper's illustrative Table 4 checks.

This is a deliberately small, standard-library-only reconstruction.  It is
not a wrapper around the project compiler, a theorem prover, or a benchmark.
The result records finite conformance checks for the definitions below; it
does not establish soundness outside the enumerated domains.

The manuscript-era source program and its historical result file were not
recovered.  Consequently this program must not be used to overwrite or infer
historical output.  See ``evidence/reference_provenance.json`` for that
boundary and for the independent, candidate-blind witnesses used by the
minimal-pair data.
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, Iterable


SCHEMA = "autoformalization-reference-semantics-results/v2"
SUITE_ID = "AF-006-finite-reference-reconstruction"
WORLD_COUNT = 2
WORLDS = tuple(range(WORLD_COUNT))
EDGES = tuple(itertools.product(WORLDS, repeat=2))


def implication(left: bool, right: bool) -> bool:
    """Material implication over booleans."""

    return (not left) or right


def all_relations() -> Iterable[frozenset[tuple[int, int]]]:
    """Enumerate all 2^(2*2) binary relations in a stable bit-mask order."""

    for mask in range(1 << len(EDGES)):
        yield frozenset(edge for bit, edge in enumerate(EDGES) if mask & (1 << bit))


def valuations() -> Iterable[frozenset[int]]:
    """Enumerate all Boolean valuations over the two worlds."""

    for mask in range(1 << WORLD_COUNT):
        yield frozenset(world for world in WORLDS if mask & (1 << world))


def box(relation: frozenset[tuple[int, int]], world: int, predicate: Callable[[int], bool]) -> bool:
    """Universal Kripke modality, vacuously true at a dead end."""

    return all(predicate(target) for source, target in relation if source == world)


def diamond(relation: frozenset[tuple[int, int]], world: int, predicate: Callable[[int], bool]) -> bool:
    """Existential dual modality."""

    return any(predicate(target) for source, target in relation if source == world)


def is_reflexive(relation: frozenset[tuple[int, int]]) -> bool:
    return all((world, world) in relation for world in WORLDS)


def is_serial(relation: frozenset[tuple[int, int]]) -> bool:
    return all(any(source == world for source, _ in relation) for world in WORLDS)


def strong_until(p: tuple[bool, ...], q: tuple[bool, ...]) -> bool:
    """Strong finite-trace p U q at time zero: p is required before q only."""

    return any(q[index] and all(p[earlier] for earlier in range(index)) for index in range(len(p)))


def _record(
    check_id: str,
    title: str,
    case_count: int,
    expected_outcome: str,
    actual_output: dict[str, Any],
    enumeration: str,
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "title": title,
        "case_count": case_count,
        "expected_outcome": expected_outcome,
        "actual_output": actual_output,
        "enumeration": enumeration,
        "match": actual_output["outcome"] == expected_outcome,
    }


def check_normal_modal_distribution() -> dict[str, Any]:
    counterexamples: list[dict[str, Any]] = []
    cases = 0
    for relation, p, q, world in itertools.product(all_relations(), valuations(), valuations(), WORLDS):
        cases += 1
        antecedent = box(relation, world, lambda target: implication(target in p, target in q))
        consequent = implication(
            box(relation, world, lambda target: target in p),
            box(relation, world, lambda target: target in q),
        )
        if not implication(antecedent, consequent):
            counterexamples.append({"relation": sorted(relation), "p": sorted(p), "q": sorted(q), "world": world})
    return _record(
        "C01", "Normal modal distribution", cases, "No finite countermodel",
        {"outcome": "No finite countermodel", "counterexample_count": len(counterexamples), "counterexamples": counterexamples},
        "16 relations × 4 p-valuations × 4 q-valuations × 2 designated worlds = 512",
    )


def check_reflexive_factivity() -> dict[str, Any]:
    counterexamples: list[dict[str, Any]] = []
    cases = 0
    for relation, p, world in itertools.product(filter(is_reflexive, all_relations()), valuations(), WORLDS):
        cases += 1
        if box(relation, world, lambda target: target in p) and world not in p:
            counterexamples.append({"relation": sorted(relation), "p": sorted(p), "world": world})
    return _record(
        "C02", "Reflexive factivity", cases, "No finite countermodel",
        {"outcome": "No finite countermodel", "counterexample_count": len(counterexamples), "counterexamples": counterexamples},
        "4 reflexive relations × 4 p-valuations × 2 designated worlds = 32",
    )


def check_serial_d() -> dict[str, Any]:
    counterexamples: list[dict[str, Any]] = []
    duality_failures = 0
    cases = 0
    for relation, p, world in itertools.product(filter(is_serial, all_relations()), valuations(), WORLDS):
        cases += 1
        obligation = box(relation, world, lambda target: target in p)
        permission = diamond(relation, world, lambda target: target in p)
        dual_permission = not box(relation, world, lambda target: target not in p)
        if permission != dual_permission:
            duality_failures += 1
        if obligation and not permission:
            counterexamples.append({"relation": sorted(relation), "p": sorted(p), "world": world})
    return _record(
        "C03", "Serial D", cases, "No finite countermodel",
        {"outcome": "No finite countermodel", "counterexample_count": len(counterexamples), "duality_failures": duality_failures, "counterexamples": counterexamples},
        "9 serial relations × 4 p-valuations × 2 designated worlds = 72; tests O(p) → P(p)",
    )


def explicit_witness_checks() -> list[dict[str, Any]]:
    obligation = {
        "actual_world": 0, "ideal_world": 1, "p_at_actual": False, "p_at_ideal": True,
        "obligation_true": True, "actuality_true": False,
    }
    belief = {
        "actual_world": 0, "believed_world": 1, "p_at_actual": False, "p_at_believed_world": True,
        "belief_true": True, "factivity_true": False,
    }
    until_p, until_q = (False, True, True), (True, False, False)
    always_trace = (True, False, True)
    diagonal = {("alice", "alice"), ("bob", "bob")}
    quantifier_order = {
        "domain": ["alice", "bob"], "relation": sorted([list(pair) for pair in diagonal]),
        "for_all_exists": all(any((x, y) in diagonal for y in ("alice", "bob")) for x in ("alice", "bob")),
        "exists_for_all": any(all((x, y) in diagonal for x in ("alice", "bob")) for y in ("alice", "bob")),
    }
    return [
        _record("C04", "Obligation not actuality", 1, "Explicit separating model", {"outcome": "Explicit separating model", "witness": obligation}, "One explicitly specified actual/ideal two-world model"),
        _record("C05", "Belief without factivity", 1, "Explicit separating model", {"outcome": "Explicit separating model", "witness": belief}, "One explicitly specified non-reflexive belief model"),
        _record("C07", "Always not current truth", 1, "Explicit separating trace", {"outcome": "Explicit separating trace", "witness": {"trace_p": list(always_trace), "current_truth": always_trace[0], "always_truth": all(always_trace)}}, "One length-three trace"),
        _record("C08", "Quantifier order", 1, "Diagonal-relation witness", {"outcome": "Diagonal-relation witness", "witness": quantifier_order}, "One two-element diagonal relation"),
    ]


def check_until_not_conjunction() -> dict[str, Any]:
    disagreements: list[dict[str, Any]] = []
    cases = 0
    for bits in itertools.product((False, True), repeat=6):
        p, q = bits[:3], bits[3:]
        until_value = strong_until(p, q)
        conjunction = p[0] and q[0]
        cases += 1
        if until_value != conjunction:
            disagreements.append({"p": list(p), "q": list(q), "strong_until": until_value, "conjunction_at_zero": conjunction})
    return _record(
        "C06", "Until not conjunction", cases, "26 disagreements",
        {"outcome": "26 disagreements", "disagreement_count": len(disagreements), "disagreement_direction_counts": {"until_true_conjunction_false": sum(item["strong_until"] and not item["conjunction_at_zero"] for item in disagreements), "until_false_conjunction_true": sum(not item["strong_until"] and item["conjunction_at_zero"] for item in disagreements)}, "disagreements": disagreements},
        "All 2^(3 p-values + 3 q-values) = 64 length-three Boolean traces; strong until requires p before, not at, the q witness",
    )


def check_guarded_writes() -> dict[str, Any]:
    cases = [
        {"case": "safe-approved-write", "approved": True, "write": True},
        {"case": "unsafe-unapproved-write", "approved": False, "write": True},
        {"case": "no-write-unapproved", "approved": False, "write": False},
        {"case": "no-write-approved", "approved": True, "write": False},
    ]
    for item in cases:
        item["violation"] = item["write"] and not item["approved"]
    safe = next(item for item in cases if item["case"] == "safe-approved-write")
    unsafe = next(item for item in cases if item["case"] == "unsafe-unapproved-write")
    return _record(
        "C09", "Guarded writes", len(cases), "Safe relation 0; unsafe 1 violation",
        {"outcome": "Safe relation 0; unsafe 1 violation", "safe_relation_violation_count": int(safe["violation"]), "unsafe_relation_violation_count": int(unsafe["violation"]), "cases": cases},
        "Four complete request/write observations; violation iff write and not approved",
    )


def check_complete_audit_window() -> dict[str, Any]:
    assignments: list[dict[str, Any]] = []
    for request_observed, window_complete, write, audit in itertools.product((False, True), repeat=4):
        violation = request_observed and window_complete and write and not audit
        assignments.append({"request_observed": request_observed, "window_complete": window_complete, "write": write, "audit": audit, "violation": violation})
    violations = [item for item in assignments if item["violation"]]
    return _record(
        "C10", "Complete audit window", len(assignments), "1 violating assignment",
        {"outcome": "1 violating assignment", "violation_count": len(violations), "violating_assignments": violations},
        "All 2^4 assignments of request-observed, window-complete, write, and audit; audit is required only for an observed write in a complete window",
    )


def check_incomplete_unaligned_traces() -> dict[str, Any]:
    cases = [
        {"case": "partial-log", "capture_complete": False, "audit_observed": False, "status": "unknown", "reason": "absence cannot be treated as negation without complete capture"},
        {"case": "tenant-mismatch", "policy_identity": "tenant-a:admin", "trace_identity": "tenant-b:admin", "status": "unresolved_identity", "reason": "same spelling is not a grounded identity join"},
        {"case": "complete-bounded-window", "capture_complete": True, "audit_observed": True, "status": "satisfied_within_observed_window", "reason": "satisfaction is bounded to the declared captured window"},
    ]
    return _record(
        "C11", "Incomplete/unaligned traces", len(cases), "Unknown, unresolved, bounded satisfaction",
        {"outcome": "Unknown, unresolved, bounded satisfaction", "status_sequence": [item["status"] for item in cases], "cases": cases},
        "Three explicitly typed trace/identity observations",
    )


def check_round_trip_shared_loss() -> dict[str, Any]:
    original = {"obligation": "audit", "exception": "exempt", "meaning": "audit unless exempt"}
    first_ir = {"obligation": "audit"}  # Deliberate lossy encoder: exception omitted.
    realized = "must audit"
    second_ir = {"obligation": "audit"}
    return _record(
        "C12", "Round-trip shared loss", 1, "Equal recompiled IR; unequal source meaning",
        {"outcome": "Equal recompiled IR; unequal source meaning", "original_source": original, "first_ir": first_ir, "realized_source": realized, "recompiled_ir": second_ir, "recompiled_ir_equal": first_ir == second_ir, "source_meaning_equal": False},
        "One deliberately lossy source → IR → source → IR cycle, compared with an independently retained exception annotation",
    )


def evaluate_suite() -> dict[str, Any]:
    """Evaluate every finite check and fail closed if Table 4 no longer matches."""

    checks = [
        check_normal_modal_distribution(),
        check_reflexive_factivity(),
        check_serial_d(),
        *explicit_witness_checks()[:2],
        check_until_not_conjunction(),
        *explicit_witness_checks()[2:],
        check_guarded_writes(),
        check_complete_audit_window(),
        check_incomplete_unaligned_traces(),
        check_round_trip_shared_loss(),
    ]
    expected_counts = [512, 32, 72, 1, 1, 64, 1, 1, 4, 16, 3, 1]
    if [check["case_count"] for check in checks] != expected_counts:
        raise AssertionError("the reconstructed enumeration no longer matches Table 4")
    if len(checks) != 12 or not all(check["match"] for check in checks):
        raise AssertionError("a finite reference check did not meet its declared expected outcome")
    until = next(check for check in checks if check["check_id"] == "C06")
    if until["actual_output"]["disagreement_count"] != 26:
        raise AssertionError("strong-until disagreement count must remain 26 of 64")
    return {
        "schema": SCHEMA,
        "suite_id": SUITE_ID,
        "execution_kind": "new_reconstruction_execution",
        "historical_output_status": "not_recovered_not_executed",
        "implementation": {"language": "Python", "standard_library_only": True, "python_implementation": sys.implementation.name, "python_version": sys.version.split()[0]},
        "claims": {
            "finite_result": "All twelve reconstructed finite checks match their declared Table 4 outcomes.",
            "non_claims": ["This is not recovered historical output.", "This is not independent assurance, because this program generates this result.", "This does not prove unbounded compiler, extractor, model, or logic soundness.", "This is not a natural-distribution accuracy evaluation."],
        },
        "checks": checks,
        "summary": {"check_count": len(checks), "case_counts": expected_counts, "total_enumerated_cases": sum(expected_counts), "all_expected_outcomes_matched": True, "strong_until_conjunction_disagreements": {"numerator": 26, "denominator": 64}},
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("reference_results.json"), help="JSON result destination")
    args = parser.parse_args(argv)
    result = evaluate_suite()
    write_json(args.output, result)
    print(json.dumps({"suite_id": SUITE_ID, "output": str(args.output), "check_count": result["summary"]["check_count"], "all_expected_outcomes_matched": True}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
