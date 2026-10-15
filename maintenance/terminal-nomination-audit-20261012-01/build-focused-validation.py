"""Synthesize only explicitly selected final, pinned JUnit reports; run no tests."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path, PurePosixPath
import xml.etree.ElementTree as ET

EVIDENCE = Path(__file__).absolute().parent
CHECKOUT = Path("/home/barberb/lift_coding/maintenance/terminal-token-reduction-20261007-01/checkout")
HELPER_REPORTS = ("audit-helper-validation-02.xml", "audit-live-regression-01.xml")
HELPER_SOURCE_PATHS = frozenset({
    "ipfs_accelerate_py/agent_supervisor/runtime/reviewed_source_nomination_context.py",
    "ipfs_accelerate_py/agent_supervisor/runtime/reviewed_source_nomination_audit.py",
    "test/api/test_reviewed_source_nomination_audit.py",
})
AUDITOR_SOURCE_PATH = "benchmarks/agent_supervisor/container_coding/terminal_context_audit.py"
DRIVER_SOURCE_PATH = "benchmarks/agent_supervisor/container_coding/terminal_container_supervisor.py"
AUDITOR_TEST_SOURCE_PATH = "benchmarks/agent_supervisor/container_coding/test_terminal_nomination_context_audit.py"
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_XML_BYTES = 16 * 1024 * 1024


def wire(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def bounded_read(path, maximum):
    if path.is_symlink() or not path.is_file():
        raise ValueError("explicit input must be a regular non-symlink file")
    with path.open("rb") as stream:
        raw = stream.read(maximum + 1)
    if len(raw) > maximum:
        raise ValueError("explicit input exceeds synthesis bound")
    return raw


def evidence_path(value):
    path = Path(value)
    if not path.is_absolute():
        path = EVIDENCE / path
    if path.parent != EVIDENCE or path.resolve(strict=True) != path:
        raise ValueError("selected report/receipt must be an explicit evidence-root file")
    return path


def source_path(value):
    path = PurePosixPath(value)
    if not path.parts or path.is_absolute() or str(path) != value or any(part in {".", ".."} for part in path.parts):
        raise ValueError("source pin must be canonical checkout-relative")
    actual = CHECKOUT / value
    if actual.resolve(strict=True) != actual:
        raise ValueError("source pin crosses a symlink")
    return actual


def load_receipt(path):
    raw = bounded_read(path, MAX_JSON_BYTES)
    value = json.loads(raw)
    if type(value) is not dict or value.get("all_latest_passed") is not True:
        raise ValueError("final validation receipt is absent or not passing")
    if type(value.get("selected_reports")) is not list or type(value.get("sources")) is not list:
        raise ValueError("final validation receipt must explicitly pin selected_reports and sources")
    return value, {"path": str(path), "bytes": len(raw), "sha256": sha(raw)}


def check_pin(raw, record):
    if type(record.get("bytes")) is not int or record["bytes"] != len(raw):
        raise ValueError("explicit pin byte count differs")
    if type(record.get("sha256")) is not str or record["sha256"] != sha(raw):
        raise ValueError("explicit pin digest differs")


def parse_report(raw):
    root = ET.fromstring(raw)
    rows = []
    for case in root.iter("testcase"):
        classname, name = case.get("classname", ""), case.get("name")
        if not name:
            raise ValueError("JUnit testcase lacks an identity")
        outcome = "errors" if case.find("error") is not None else "failed" if case.find("failure") is not None else "skipped" if case.find("skipped") is not None else "passed"
        rows.append(((classname, name), outcome))
    if not rows:
        raise ValueError("selected JUnit report has no cases")
    return rows


def main(args):
    helper, helper_pin = load_receipt(evidence_path("audit-helper-validation.json"))
    auditor, auditor_pin = load_receipt(evidence_path(args.audit_validation))
    report_groups = [("helper", helper, [EVIDENCE / name for name in HELPER_REPORTS])]
    auditor_reports = ([evidence_path(path) for path in args.audit_report] if args.audit_report else
        [evidence_path(record["path"]) for record in auditor["selected_reports"]])
    if not auditor_reports or len(auditor_reports) != len(set(auditor_reports)):
        raise ValueError("auditor final selected report inventory is empty or duplicated")
    report_groups.append(("auditor", auditor, auditor_reports))
    reports, occurrences = [], defaultdict(list)
    for owner, receipt, selected in report_groups:
        pins = {str(evidence_path(record["path"])): record for record in receipt["selected_reports"]}
        if len(pins) != len(receipt["selected_reports"]):
            raise ValueError("validation receipt has duplicate report pins")
        for path in selected:
            record = pins.get(str(path))
            if record is None:
                raise ValueError("final report is not independently pinned by its owner receipt")
            raw = bounded_read(path, MAX_XML_BYTES)
            check_pin(raw, record)
            cases = parse_report(raw)
            census = dict(Counter(outcome for _, outcome in cases))
            distinct_cases = len({key for key, _ in cases})
            if type(record.get("distinct_cases")) is not int or record["distinct_cases"] != distinct_cases:
                raise ValueError("JUnit census differs from owner final distinct-case count")
            declared = record.get("outcomes", {})
            for outcome in ("passed", "errors", "skipped"):
                if type(declared.get(outcome)) is not int or declared[outcome] != census.get(outcome, 0):
                    raise ValueError("JUnit outcomes differ from owner final report census")
            declared_failures = declared.get("failed", declared.get("failures"))
            if type(declared_failures) is not int or declared_failures != census.get("failed", 0):
                raise ValueError("JUnit failures differ from owner final report census")
            for key, outcome in cases:
                occurrences[key].append({"report": str(path), "owner": owner, "outcome": outcome})
            reports.append({"path": str(path), "owner": owner, "bytes": len(raw), "sha256": sha(raw),
                "case_occurrences": len(cases), "distinct_cases": distinct_cases,
                "class_counts": dict(sorted(Counter(key[0] for key, _ in cases).items())),
                "outcomes": {key: census.get(key, 0) for key in ("passed", "failed", "errors", "skipped")}})
    # The selected reports are final. Conflicting duplicate outcomes fail closed;
    # synthesis never silently overrides a selected failure with an older pass.
    conflicts = [key for key, values in occurrences.items() if len({entry["outcome"] for entry in values}) != 1]
    if conflicts:
        raise ValueError("selected final reports contain conflicting duplicate outcomes")
    unique_census = Counter(values[-1]["outcome"] for values in occurrences.values())
    source_records = defaultdict(list)
    for owner, receipt in (("helper", helper), ("auditor", auditor)):
        if len({record["path"] for record in receipt["sources"]}) != len(receipt["sources"]):
            raise ValueError("owner final source inventory has duplicate paths")
        for record in receipt["sources"]:
            source_records[record["path"]].append((owner, record))
    if set(record["path"] for record in helper["sources"]) != HELPER_SOURCE_PATHS:
        raise ValueError("helper final three-source inventory changed")
    expected_sources = HELPER_SOURCE_PATHS | {AUDITOR_SOURCE_PATH, DRIVER_SOURCE_PATH, AUDITOR_TEST_SOURCE_PATH}
    if set(source_records) != expected_sources:
        raise ValueError("expected six final production/test sources are not explicitly pinned")
    checks = []
    for relative, owners in sorted(source_records.items()):
        path = source_path(relative)
        raw = bounded_read(path, 4 * 1024 * 1024)
        for owner, record in owners:
            check_pin(raw, record)
        checks.append({"path": relative, "absolute_path": str(path), "bytes": len(raw), "sha256": sha(raw),
            "independently_joined_owner_receipts": [owner for owner, _ in owners], "matches_final_pins": True})
    duplicate_cases = [{"classname": key[0], "name": key[1], "occurrences": values}
        for key, values in sorted(occurrences.items()) if len(values) > 1]
    outcomes = {key: unique_census.get(key, 0) for key in ("passed", "failed", "errors", "skipped")}
    summary = {
        "schema": "reviewed-source-nomination-final-focused-validation@1",
        "owner_validation_receipts": [helper_pin, auditor_pin], "selected_reports": reports,
        "auditor_report_selection": "explicit_final_paths" if args.audit_report else "owner_final_selected_reports",
        "deduplication_identity": ["classname", "name"], "classname_aliases_applied": False,
        "case_occurrences": sum(report["case_occurrences"] for report in reports),
        "unique_cases": len(occurrences), "duplicate_distinct_cases": len(duplicate_cases),
        "duplicate_occurrences": sum(len(values) - 1 for values in occurrences.values()),
        "duplicate_case_provenance": duplicate_cases, "outcomes": outcomes,
        "all_selected_cases_passed": outcomes["passed"] == len(occurrences),
        "current_source_checks": checks, "all_six_source_pins_match": True,
        "bounded_limits_from_pinned_auditor_receipt": auditor.get("bounded_limits", {}),
        "superseded_reports_excluded": {
            "helper": [record for record in helper["selected_reports"] if Path(record["path"]).name not in HELPER_REPORTS],
            "auditor": auditor.get("historical_reports", []),
        },
        "meaningful_boundaries": {
            "helper": helper.get("validated_boundaries", []),
            "auditor": auditor.get("validated_boundaries", []),
        },
        "limitations": [
            "Only explicitly selected final reports are counted; superseded failed or partial reports are not selected.",
            "JUnit identities are exact classname/name pairs. Any different classnames remain distinct and are disclosed; no speculative aliasing is applied.",
            "Historical inclusion@1 catalog replay requires the same trusted pinned interpreter, import roots and original repository path; cross-runtime replay fails closed.",
            "Historical reconstruction checks captured original source and model-input bytes; it establishes no current owner revision, current dispatch or current source freshness.",
            "Unit fixtures and regression cases do not establish live provider behavior, total-session token savings, task satisfaction, semantic equivalence, source authentication or convergence.",
        ],
        "tests_rerun_by_synthesis": 0, "provider_calls_by_synthesis": 0,
        "production_or_test_edits_by_synthesis": 0,
        "private_or_hidden_artifacts_read": False,
    }
    if not summary["all_selected_cases_passed"]:
        raise ValueError("selected final JUnit reports are not all passing")
    output = evidence_path(args.output) if (EVIDENCE / args.output).exists() else EVIDENCE / args.output
    if output.parent != EVIDENCE or output.name != "final-focused-validation.json":
        raise ValueError("output must be the new final-focused-validation.json evidence-root file")
    raw = wire(summary)
    with output.open("xb") as stream:
        stream.write(raw)
    print(json.dumps({"path": str(output), "bytes": len(raw), "sha256": sha(raw),
        "unique_cases": summary["unique_cases"], "duplicate_occurrences": summary["duplicate_occurrences"],
        "outcomes": outcomes, "source_checks": len(checks)}, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-validation", required=True)
    parser.add_argument("--audit-report", action="append", help="Exact final auditor JUnit path; repeat for each selected report")
    parser.add_argument("--output", default="final-focused-validation.json")
    main(parser.parse_args())
