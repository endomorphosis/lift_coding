"""Run authored four-file fixtures and replay their byte-bound finite results.

The files already contain candidate plans before the first observation.  This
brackets validation, not a supervisor task's complete input lifetime.  Current
native codebase-head observation remains the caller's responsibility.
"""
from __future__ import annotations

import copy
from pathlib import Path

from file_model_bridge import FileModelError, build_file_model, validate_file_model
from jsonl_cases import (FILE_PATHS, create_bundle, fixture_payloads,
                         mutate_between_observations, specs)
from jsonl_io import ROOT, sha
from observed_files import ObservationError, decode_file, observe_bundle, reobserve_bundle, validate_bundle
from strict_jsonl import StrictJSONLError
import scheduler_constraints as sc


SCHEMA = "terminal-authored-jsonl-file-case-run@1"
CLAIMS = {
    "real_benchmark_input_used": False,
    "source_body_execution": False,
    "metrics_are_runtime_observations": False,
    "native_codebase_head_observed_by_helper": False,
    "complete_task_input_lifetime_observed": False,
    "historical_reports_are_live_authority": False,
    "file_parser_equivalence_proved": False,
    "checker_model_equivalence_proved": False,
    "full_task_satisfaction_proved": False,
    "source_model_equivalence_proved": False,
    "convergence_proved": False,
    "planning_or_dispatch_authority": False,
}


class FileCaseRunError(ValueError):
    """Authored fixture evidence does not replay against its retained files."""


def _canonical(value):
    try:
        return sc.canonical_bytes(value)
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise FileCaseRunError("case run evidence must be bounded plain JSON") from exc


def _location(output, *, fresh):
    if (not isinstance(output, Path) or output.resolve() != output
            or ROOT not in output.parents or output == ROOT):
        raise FileCaseRunError("a canonical owned case-run output is required")
    if fresh and output.exists():
        raise FileCaseRunError("case-run output must be fresh")
    if not fresh and not output.is_dir():
        raise FileCaseRunError("retained case-run output is missing")


def _contract(contract):
    _canonical(contract)
    try:
        sc.validate_scheduler_contract(
            contract, instruction=contract["instruction"]["source_text"].encode("utf-8"),
            head=contract["head"], source_records=contract["sources"])
    except (KeyError, TypeError, AttributeError, ValueError) as exc:
        raise FileCaseRunError("the complete scheduler contract must replay before file cases") from exc


def _fixture_report(destination, spec, payloads):
    return {
        "schema": "terminal-authored-jsonl-file-fixture@1", "case_id": spec["case_id"],
        "root": str(destination),
        "initial_payloads": {name: {"bytes": len(raw), "sha256": sha(raw)}
                             for name, raw in sorted(payloads.items())},
        "real_benchmark_input_used": False, "source_body_execution": False,
    }


def _after_payloads(spec, payloads):
    result = dict(payloads)
    if spec["fault"] in ("changed_input_bytes", "changed_plan_bytes"):
        name = FILE_PATHS[2] if spec["fault"] == "changed_plan_bytes" else FILE_PATHS[0]
        result[name] = result[name].rstrip(b"\n") + b" \n"
    return result


def _check_recipe(entry, *, destination, spec):
    initial = fixture_payloads(spec)
    expected_fixture = _fixture_report(destination, spec, initial)
    if _canonical(entry["fixture"]) != _canonical(expected_fixture):
        raise FileCaseRunError("fixture provenance differs from the authored byte recipe")
    expected_after = _after_payloads(spec, initial)
    for phase, expected in (("before", initial), ("after", expected_after)):
        bundle = entry[phase]
        validate_bundle(bundle)
        if bundle["root"] != str(destination):
            raise FileCaseRunError("a fixture observation moved to another owned root")
        for name in FILE_PATHS:
            if decode_file(bundle, name) != expected[name]:
                raise FileCaseRunError("observation bytes differ from the independent fixture recipe")


def _evaluate(*, contract, before, after, spec):
    try:
        model = build_file_model(contract=contract, before=before, after=after,
                                 metrics=spec["metrics"], case_id=spec["case_id"])
        validate_file_model(model, contract=contract, before=before, after=after,
                            metrics=spec["metrics"], case_id=spec["case_id"])
    except (FileModelError, StrictJSONLError, ObservationError) as error:
        return None, "file_refusal", {"class": type(error).__name__, "message": str(error)}
    outcome = "accepted" if model["evaluation"]["evaluation_passed"] else "model_refusal"
    observed_ids = {row["requirement_id"] for row in model["evaluation"]["violations"]}
    if not set(spec["intended_violation_ids"]) <= observed_ids:
        raise FileCaseRunError("finite evaluation omitted an independently expected clause violation")
    return model, outcome, None


def _summary(entries):
    counts = {"total": len(entries), "accepted": 0, "model_refusal": 0,
              "file_refusal": 0, "derived_cases": 0}
    derived = []
    for entry in entries:
        counts[entry["outcome"]] += 1
        if entry["model"] is not None:
            counts["derived_cases"] += 1
            derived.append({"case": copy.deepcopy(entry["model"]["case"]),
                            "expected_pass": entry["spec"]["expected_outcome"] == "accepted",
                            "intended_violation_ids": list(entry["spec"]["intended_violation_ids"])})
    return counts, derived


def _inventory(output, selected):
    if {path.name for path in output.iterdir()} != {spec["case_id"] for spec in selected}:
        raise FileCaseRunError("retained fixture inventory has a missing or unknown case")


def run_file_cases(*, output: Path, contract: dict) -> dict:
    """Create exact authored artifacts, then observe, project, check and reobserve."""
    _location(output, fresh=True)
    _contract(contract)
    selected = specs()
    _canonical(selected)
    output.mkdir(mode=0o700)
    entries = []
    for spec in selected:
        destination = output / spec["case_id"]
        fixture = create_bundle(destination=destination, spec=spec)
        before = observe_bundle(root=destination)
        mutate_between_observations(destination=destination, spec=spec)
        after = observe_bundle(root=destination)
        model, outcome, error = _evaluate(contract=contract, before=before, after=after, spec=spec)
        if outcome != spec["expected_outcome"]:
            raise FileCaseRunError("observed file-case outcome differs from its independent expectation")
        entry = {"spec": copy.deepcopy(spec), "fixture": fixture, "before": before,
                 "after": after, "model": model, "outcome": outcome, "error": error}
        _check_recipe(entry, destination=destination, spec=spec)
        reobserve_bundle(after, root=destination)
        entries.append(entry)
    _inventory(output, selected)
    counts, derived = _summary(entries)
    return {"schema": SCHEMA, "contract_sha256": sha(_canonical(contract)),
            "head": copy.deepcopy(contract["head"]), "output": str(output),
            "entries": entries, "derived_cases": derived, "counts": counts,
            "all_expected_outcomes_matched": True, "all_after_observations_reobserved": True,
            "claims": dict(CLAIMS)}


def validate_file_case_run(report, *, output: Path, contract: dict) -> dict:
    """Replay retained evidence and currently reobserve only the final artifacts.

    This creates no files, reruns no mutation recipe, and grants no authority to
    historical observations.  The first observation remains historical data.
    """
    _location(output, fresh=False)
    _contract(contract)
    _canonical(report)
    selected = specs()
    _inventory(output, selected)
    fields = {"schema", "contract_sha256", "head", "output", "entries", "derived_cases", "counts",
              "all_expected_outcomes_matched", "all_after_observations_reobserved", "claims"}
    if (type(report) is not dict or set(report) != fields
            or type(report["entries"]) is not list or len(report["entries"]) != len(selected)):
        raise FileCaseRunError("file case run has an incomplete or unknown report schema")
    rebuilt_entries = []
    for entry, spec in zip(report["entries"], selected):
        if type(entry) is not dict or set(entry) != {"spec", "fixture", "before", "after", "model", "outcome", "error"}:
            raise FileCaseRunError("file case entry has unknown or missing evidence")
        if _canonical(entry["spec"]) != _canonical(spec):
            raise FileCaseRunError("file case specification differs from its independent authored recipe")
        destination = output / spec["case_id"]
        _check_recipe(entry, destination=destination, spec=spec)
        model, outcome, error = _evaluate(contract=contract, before=entry["before"], after=entry["after"], spec=spec)
        if outcome != spec["expected_outcome"]:
            raise FileCaseRunError("retained file case does not reproduce its independently expected outcome")
        rebuilt = {"spec": copy.deepcopy(spec), "fixture": copy.deepcopy(entry["fixture"]),
                   "before": copy.deepcopy(entry["before"]), "after": copy.deepcopy(entry["after"]),
                   "model": model, "outcome": outcome, "error": error}
        if _canonical(entry) != _canonical(rebuilt):
            raise FileCaseRunError("file case evidence or derived model differs from byte replay")
        reobserve_bundle(entry["after"], root=destination)
        rebuilt_entries.append(rebuilt)
    counts, derived = _summary(rebuilt_entries)
    expected = {"schema": SCHEMA, "contract_sha256": sha(_canonical(contract)),
                "head": copy.deepcopy(contract["head"]), "output": str(output),
                "entries": rebuilt_entries, "derived_cases": derived, "counts": counts,
                "all_expected_outcomes_matched": True, "all_after_observations_reobserved": True,
                "claims": dict(CLAIMS)}
    if _canonical(report) != _canonical(expected):
        raise FileCaseRunError("file case run totals or source bindings differ from exact replay")
    return expected
