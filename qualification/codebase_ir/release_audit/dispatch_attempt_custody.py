"""Receive a closed historical dispatch attempt ledger without executing producers."""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import stat
import time
import xml.etree.ElementTree as ET
from collections import Counter
from hashlib import sha256
from pathlib import Path

INPUT_SCHEMA = "codebase-ir-dispatch-attempt-custody-input@1"
SCHEMA = "codebase-ir-dispatch-attempt-custody@1"
PROFILE = "recorded-dispatch-attempts@1"
ROLES = ("machine_review", "attempt_ledger", "postledger_supplement")
PUBLIC_ANCHORS = {
    "machine_review": "fb04941c382a3c9f842d60b514c0b7af3ea303772926a11924fe4bf7fb5aa4b8",
    "attempt_ledger": "7203e8e5fabc7a8ff1af2dc0db5c035753e72b30cf625276ab0f37e508036caf",
    "postledger_supplement": "0c4861fa0c24702ed3feeb846d766b93032353b0ac39a7d363b222bba9944815",
}
HOSTS = tuple("host-run-" + n for n in ("01", "02", "03", "04", "05", "07", "09", "10", "11", "12", "13"))
DOCKERS = ("docker-run-01", *("docker-positive-" + str(n).zfill(2) for n in range(2, 8)),
           "docker-child-proof-02", "docker-child-epoch-02")
STREAMS = ("stream-before-generation-run-01", "stream-fixed-generation-run-01")
TRUE_FLAGS = (
    "dispatch_attempt_custody_inventory_produced", "recorded_attempt_population_reconciled",
    "recorded_test_phase_populations_reconciled", "recorded_costs_reconciled",
    "original_outcomes_and_generations_preserved", "input_files_unchanged",
)
FALSE_FLAGS = (
    "native_execution_performed", "training_executed", "current_authority_claimed",
    "owner_sources_imported", "owner_database_opened", "profile_keys_read", "git_executable_invoked",
    "network_access_performed", "signature_authentication_performed", "producer_authentication_verified",
    "native_publication_reconstructed", "live_attempt_eligibility_verified", "historical_process_origin_authenticated",
    "complete_runtime_generation_custody_qualified", "whole_current_live_runtime_qualified",
    "whole_same_generation_host_suite_qualified", "external_effect_absence_qualified",
    "unique_cpu_time_measured", "total_elapsed_wall_time_measured", "training_absence_certified",
    "complete_os_launch_census_verified", "proof_authority_qualified", "production_acceptance_requalified",
)
MAX_FILE = 2 * 1024 * 1024
MAX_FILES = 192
MAX_BYTES = 32 * 1024 * 1024
MAX_REPORT = 4 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()


def bounded_canonical(value, limit):
    chunks, total = [], 0
    encoder = json.JSONEncoder(sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
    for token in encoder.iterencode(value):
        raw = token.encode("utf-8")
        require(total + len(raw) + 1 <= limit, "main report allocation bound")
        chunks.append(raw)
        total += len(raw)
    return b"".join(chunks) + b"\n"


def document(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, "duplicate JSON key")
            out[key] = value
        return out

    def integer(value):
        require(len(value) <= 20, "integer allocation bound")
        out = int(value)
        require(abs(out) <= 2**63 - 1, "integer magnitude bound")
        return out

    def floating(value):
        require(len(value) <= 64, "float allocation bound")
        out = float(value)
        require(math.isfinite(out), "nonfinite JSON")
        return out

    def constant(_):
        raise ValueError("nonfinite JSON")

    value = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=pairs,
                       parse_int=integer, parse_float=floating, parse_constant=constant)
    require(type(value) is dict, "JSON object required")
    return value


def number(value, *, nullable=False):
    if nullable and value is None:
        return value
    require(type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1e9,
            "bounded nonnegative recorded number required")
    return value


def descriptor(value, *, declared=False):
    keys = {"path", "sha256", "bytes", "present"} if declared else {"path", "sha256", "size_bytes"}
    require(type(value) is dict and set(value) == keys, "closed file descriptor required")
    if declared:
        require(value["present"] is True, "present descriptor required")
    size = value["bytes" if declared else "size_bytes"]
    require(type(size) is int and 0 <= size <= MAX_FILE, "preallocation file bound")
    require(type(value["sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", value["sha256"]) is not None,
            "SHA-256 descriptor required")
    path = Path(value["path"])
    require(path.is_absolute() and ".." not in path.parts, "absolute lexical input path required")
    return {"path": str(path), "sha256": value["sha256"], "size_bytes": size}


class Capture:
    """Bound physical reads; explicit relocation never falls back to an original."""

    def __init__(self, relocated_sources=None):
        self.remap = relocated_sources or {}
        self.files = {}
        self.logical = {}
        self.total = 0
        self.started = time.monotonic()

    @staticmethod
    def raw(path, limit):
        require(path.is_absolute() and path.resolve(strict=True) == path, "canonical nonsymlink file required")
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        try:
            before = os.fstat(fd)
            require(stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= limit, "bounded regular file required")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                raw = stream.read(limit + 1)
            after, current = os.fstat(fd), path.lstat()

            def identity(row):
                return row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns, row.st_ctime_ns

            require(identity(before) == identity(after) == identity(current) and len(raw) == before.st_size,
                    "file changed during bounded read")
            return raw
        finally:
            os.close(fd)

    def read(self, path, pin=None, *, mapped=True, maximum=MAX_FILE):
        require(time.monotonic() - self.started <= 120, "capture deadline")
        logical = Path(path).absolute()
        if self.remap and mapped:
            require(str(logical) in self.remap, "explicit relocated member unavailable")
            physical = Path(self.remap[str(logical)])
        else:
            physical = logical
        limit = maximum if pin is None else min(maximum, descriptor(pin)["size_bytes"])
        if physical not in self.files:
            require(len(self.files) < MAX_FILES and self.total + limit <= MAX_BYTES, "preallocation aggregate bound")
            raw = self.raw(physical, limit)
            self.files[physical] = raw
            self.total += len(raw)
        raw = self.files[physical]
        if pin:
            require(len(raw) == pin["size_bytes"] and sha256(raw).hexdigest() == pin["sha256"], "selected raw pin mismatch")
        self.logical[str(logical)] = physical
        return raw

    def stable(self):
        rows = []
        for path, raw in self.files.items():
            require(time.monotonic() - self.started <= 120, "stability deadline")
            require(self.raw(path, len(raw)) == raw, "previously captured body changed")
            rows.append({"path": str(path), "sha256": sha256(raw).hexdigest(), "size_bytes": len(raw), "unchanged": True})
        return {"unchanged": True, "files": rows}


def selected_inputs(ledger, ledger_path):
    selected, memberships, frontiers = {}, [], []
    base = ledger_path.parent

    def add(pin, role, membership):
        if pin.get("present") is False:
            require(set(pin) == {"path", "present"}, "closed unavailable declaration")
            require(Path(pin["path"]).is_relative_to(base), "missing declaration outside selected root")
            frontiers.append({"membership": membership, "role": role, "path": pin["path"], "disposition": "recorded_body_unavailable"})
            return
        parsed = descriptor(pin, declared=True)
        require(Path(parsed["path"]).is_relative_to(base), "selected child outside ledger root")
        if parsed["path"] in selected:
            require(selected[parsed["path"]] == parsed, "conflicting shared child pins")
        selected[parsed["path"]] = parsed
        memberships.append({**parsed, "role": role, "membership": membership})

    for group, population, names in (("host_attempts", HOSTS, {"invocation.json", "review.json", "reports.jsonl", "tests.xml"}),
                                     ("Docker_attempts", DOCKERS, {"container-execution-final.json"}),
                                     ("isolated_stream_attempts", STREAMS, {"review.json", "reports.jsonl", "tests.xml", "launcher-result.json"})):
        rows = ledger[group]
        require(type(rows) is list and [row["attempt"] for row in rows] == list(population), "complete ordered attempt population required")
        for row in rows:
            pins = row["raw_file_pins"]
            require(type(pins) is list and len(pins) <= 16, "bounded explicit raw roles")
            chosen = {Path(pin["path"]).name: pin for pin in pins if Path(pin["path"]).name in names}
            require(set(chosen) == names and len(chosen) == sum(Path(pin["path"]).name in names for pin in pins), "complete unique raw role declarations")
            for name in sorted(names):
                add(chosen[name], name, row["attempt"])
            for pin in pins:
                if Path(pin["path"]).name not in names:
                    frontiers.append({"membership": row["attempt"], "role": Path(pin["path"]).name,
                                      "path": pin["path"], "disposition": "outside_selected_receiving_profile"})
    for group, field, count in (("retained_metadata_audit_attempts", "pin", 23),
                                ("non_native_preparation_records", "pin", 21),
                                ("preentry_invocation_failures", "metadata_pin", 1),
                                ("progress_observer_failures", "metadata_pin", 1)):
        rows = ledger[group]
        require(type(rows) is list and len(rows) == count, "complete selected auxiliary population required")
        paths = [row[field]["path"] for row in rows]
        require(len(set(paths)) == count, "repeated auxiliary membership")
        for index, row in enumerate(rows):
            add(row[field], group, group + "/" + str(index))
    require(len(selected) == 104, "closed selected unique body population")
    for role in ("additional_isolated_native_Git_gc_control", "isolated_native_Git_marker_control",
                 "historical_available_scope_readback_pins", "historical_failure_cause_audit_pins"):
        frontiers.append({"role": role, "disposition": "ledger_declaration_only_not_replayed"})
    return selected, memberships, frontiers


def phase_rows(raw):
    lines = raw.splitlines()
    require(len(lines) <= 4096 and all(len(line) <= 128 * 1024 for line in lines), "JSONL preallocation bound")
    rows, partial = [], 0
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            row = document(line)
        except json.JSONDecodeError:
            require(index == len(lines) - 1 and not raw.endswith(b"\n"), "malformed complete JSONL record")
            partial += 1
            continue
        require(set(row) in ({"duration_seconds", "nodeid", "outcome", "when"},
                             {"duration_seconds", "nodeid", "outcome", "when", "failure"}), "closed pytest phase record")
        if "failure" in row:
            require(row["outcome"] == "failed" and type(row["failure"]) is str and len(row["failure"]) <= 65536,
                    "bounded recorded failure text")
        require(type(row["nodeid"]) is str and 0 < len(row["nodeid"]) <= 128 * 1024 and "\x00" not in row["nodeid"], "bounded phase identity")
        require(row["when"] in ("setup", "call", "teardown") and row["outcome"] in ("passed", "failed", "skipped"), "typed pytest phase outcome")
        number(row["duration_seconds"])
        rows.append(row)
    require(len({(row["nodeid"], row["when"]) for row in rows}) == len(rows), "duplicate pytest phase identity")
    counters = {phase: dict(sorted(Counter(row["outcome"] for row in rows if row["when"] == phase).items()))
                for phase in ("call", "setup", "teardown")}
    nodes = {phase: {outcome: sorted(row["nodeid"] for row in rows if row["when"] == phase and row["outcome"] == outcome)
                     for outcome in ("failed", "passed", "skipped")} for phase in counters}
    return {"actual_call_cases": sum(counters["call"].values()), "setup_case_records": sum(counters["setup"].values()),
            "partial_JSON_lines_ignored": partial, "phases": counters, "nodes_by_outcome": nodes}, rows


def xml_rows(raw):
    require(b"<!" not in raw and b"\x00" not in raw, "entity-free UTF-8 XML required")
    text = raw.decode("utf-8", errors="strict")
    parser = ET.XMLPullParser(events=("start", "end"))
    nodes, depth = 0, 0
    for index in range(0, len(text), 1024):
        parser.feed(text[index:index + 1024])
        for event, _ in parser.read_events():
            if event == "start":
                nodes += 1
                depth += 1
                require(nodes <= 4096 and depth <= 8, "XML structure allocation bound")
            else:
                depth -= 1
    parser.close()
    root = ET.fromstring(text)
    require(root.tag == "testsuites" and 1 <= len(root) <= 8 and all(s.tag == "testsuite" for s in root), "closed XML suites")
    suites, cases = [], []
    for suite in root:
        counts = {}
        for key in ("tests", "failures", "errors", "skipped"):
            token = suite.attrib[key]
            require(re.fullmatch(r"0|[1-9][0-9]{0,3}", token) is not None and int(token) <= 512, "bounded XML count")
            counts[key] = int(token)
        require(len(suite) == counts["tests"] and all(c.tag == "testcase" for c in suite), "XML case population")
        outcome_counts = Counter(child.tag for case in suite for child in case)
        require(set(outcome_counts) <= {"failure", "error", "skipped"}
                and all(outcome_counts[tag] == counts[key] for tag, key in (("failure", "failures"), ("error", "errors"), ("skipped", "skipped"))), "XML outcome totals")
        for case in suite:
            require(set(case.attrib) <= {"name", "classname", "time"} and "name" in case.attrib, "closed XML testcase")
            cases.append({"name": case.attrib["name"], "classname": case.attrib.get("classname"),
                          "time": case.attrib.get("time"), "outcomes": [child.tag for child in case]})
        suites.append({**counts, "time": suite.attrib.get("time")})
    require(len(cases) <= 512 and len({(c["classname"], c["name"]) for c in cases}) == len(cases), "unique bounded XML cases")
    return suites, cases


def reconcile(ledger, machine, supplement, bodies):
    require(ledger["schema"] == "finite-proof-query-attempt-cost-ledger@3", "ledger schema")
    require(machine["schema"] == "repository-proof-index-codebase-ir-finite-proof-query-dispatch-review@1"
            and supplement["schema"] == "finite-dispatch-postledger-finalization-cost-supplement@1", "selected review/supplement schema")
    host, stream, docker, audit_rows, preparations = [], [], [], [], []
    phase_totals = Counter()

    def raw_role(row, name):
        pins = [pin for pin in row["raw_file_pins"] if Path(pin["path"]).name == name]
        require(len(pins) == 1, "unique role required")
        pin = pins[0]
        return None if pin["present"] is False else bodies[pin["path"]]

    for group, destination in (("host_attempts", host), ("isolated_stream_attempts", stream)):
        for row in ledger[group]:
            review = document(raw_role(row, "review.json"))
            seconds = number(review["elapsed_seconds"])
            require(seconds == number(row["elapsed_seconds"]), "recorded driver cost differs")
            phase_raw = raw_role(row, "reports.jsonl")
            counts, phases = phase_rows(phase_raw) if phase_raw is not None else phase_rows(b"")
            require(canonical(counts) == canonical(row["counts"]), "independent typed phase population differs")
            require(type(review["pytest_exit_code"]) is type(row["pytest_exit_code"]) is int
                    and review["pytest_exit_code"] == row["pytest_exit_code"], "pytest exit identity")
            xml_raw = raw_role(row, "tests.xml")
            suites, cases = xml_rows(xml_raw) if xml_raw is not None else ([], [])
            if "XML_suite_counts" in row:
                declared = [{key: str(value) for key, value in suite.items()} for suite in suites]
                require(declared == row["XML_suite_counts"], "independent XML counts differ")
            setup_ids = {p["nodeid"] for p in phases if p["when"] == "setup"}
            if phases:
                require(len(cases) == len(setup_ids), "XML and actual setup population differ")
                errors = counts["phases"]["setup"].get("failed", 0) + counts["phases"]["teardown"].get("failed", 0)
                require(sum(s["errors"] for s in suites) == errors
                        and sum(s["failures"] for s in suites) == counts["phases"]["call"].get("failed", 0), "phase/XML failure and cleanup counts differ")
            for phase, outcomes in counts["phases"].items():
                for outcome, count in outcomes.items():
                    phase_totals[phase + "/" + outcome] += count
            status = "passed" if review["pytest_exit_code"] == 0 and all(outcomes.get("failed", 0) == 0 for outcomes in counts["phases"].values()) else "failed_or_partial"
            if group == "host_attempts":
                require(review["qualification"] == row["status"] == status, "whole host failure rewritten")
                invocation = document(raw_role(row, "invocation.json"))
                generation = review.get("generation_cid")
                require(invocation.get("generation_cid") == generation == row.get("generation_cid"), "generation identity differs")
                outer_seconds = None
            else:
                require(row["test_qualification"] is (status == "passed"), "stream outcome differs")
                launcher = document(raw_role(row, "launcher-result.json"))
                require(type(launcher["returncode"]) is int and launcher["returncode"] == row["pytest_exit_code"], "stream launcher exit differs")
                outer_seconds = number(launcher["elapsed_seconds"])
                generation = None
            destination.append({"attempt": row["attempt"], "recorded_outcome": status, "generation_cid": generation,
                                "driver_seconds": seconds, "outer_launcher_seconds": outer_seconds, "phase_counts": counts,
                                "XML_suites": suites, "XML_cases": cases,
                                "phase_body_unavailable": phase_raw is None, "XML_body_unavailable": xml_raw is None,
                                "source_generation_reconstructed": False, "execution_authenticated": False})
    require(sum(row["recorded_outcome"] == "failed_or_partial" for row in host) == 10, "historical adverse host population")
    for row, count, outcome in zip(host[-3:], (37, 23, 1), ("failed_or_partial", "failed_or_partial", "passed"), strict=True):
        require(row["phase_counts"]["actual_call_cases"] == count and len(row["XML_cases"]) == count
                and row["recorded_outcome"] == outcome, "whole and targeted host populations differ")
    require(len({row["generation_cid"] for row in host[-3:]}) == 3,
            "separate whole and targeted generations required")
    for row in ledger["Docker_attempts"]:
        raw = document(raw_role(row, "container-execution-final.json"))
        require(type(raw["returncode"]) is type(row["returncode"]) is int and raw["returncode"] == row["returncode"]
                and raw["qualification_status"] == row["status"]
                and number(raw["elapsed_seconds"]) == number(row["elapsed_seconds"]), "raw Docker driver outcome/cost differs")
        expected = "completed" if raw["returncode"] == 0 else "unqualified"
        require(expected == row["status"] and raw.get("fixture_case") == row["fixture_case"], "driver completion interpretation differs")
        docker.append({"attempt": row["attempt"], "fixture_case": raw.get("fixture_case"), "recorded_driver_outcome": expected,
                       "returncode": raw["returncode"], "driver_seconds": raw["elapsed_seconds"],
                       "native_task_completion_inferred": False, "publication_reconstructed": False})
    for row in ledger["retained_metadata_audit_attempts"]:
        raw = document(bodies[row["pin"]["path"]])
        errors = raw.get("errors")
        error_count = len(errors) if isinstance(errors, list) else 0
        require(raw.get("schema") == row["recorded_schema"] and raw.get("status") == row["recorded_status"]
                and type(row["recorded_error_count"]) is int and error_count == row["recorded_error_count"], "recorded metadata status/error count differs")
        case_count = len(raw["cases"]) if type(raw.get("cases")) is list else None
        require(case_count == row["recorded_summary_case_count"]
                and (case_count is None or type(row["recorded_summary_case_count"]) is int), "metadata summary case population differs")
        disposition = "recorded_metadata_outcome_only"
        if Path(row["pin"]["path"]).name == "joint-summary-02.json":
            require(raw["status"] == "passed" and raw["cases"] == [], "original empty passed summary must remain")
            disposition = "failed_empty_three_case_population"
            require(row["derived_qualification"] == disposition, "empty summary upgraded")
        if Path(row["pin"]["path"]).name == "joint-summary-03.json":
            require(raw["status"] == "passed" and [case["case"] for case in raw["cases"]] == ["positive", "child-late-proof", "child-late-epoch"], "final exact three-case population")
            require([case["native_task_status"] for case in raw["cases"]] == ["completed", "in_progress", "in_progress"]
                    and [case["native_settlement"] for case in raw["cases"]] == ["completed-with-native-publication", "unknown-retained", "unknown-retained"], "recorded UNKNOWN settlement promoted")
            require(raw["UNKNOWN_proves_no_external_effects"] is False and raw["independent_live_attempt_lease_checked"] is False
                    and raw["separate_generation11_positive06_qualification_transferred"] is False
                    and raw["test_only_generation13_runtime_transfer_claimed"] is False, "historical scope promoted")
            disposition = "passed_exact_three_case_population"
            require(row["derived_qualification"] == disposition, "exact summary disposition differs")
            summary = raw
        audit_rows.append({"path": row["pin"]["path"], "recorded_schema": raw.get("schema"), "recorded_status": raw.get("status"),
                           "recorded_error_count": error_count, "recorded_summary_case_count": case_count,
                           "receiving_disposition": disposition, "native_qualification_replayed": False})
    for row in ledger["non_native_preparation_records"]:
        raw = document(bodies[row["pin"]["path"]])
        recorded = raw.get("status", raw.get("preparation_status"))
        require(recorded == row["recorded_preparation_status"], "preparation recorded status differs")
        require(type(row["executed_native_test_cases"]) is int and row["executed_native_test_cases"] == 0
                and type(row["native_solver_training_worker_jobs"]) is int and row["native_solver_training_worker_jobs"] == 0, "preparation converted to executed work")
        preparations.append({"path": row["pin"]["path"], "recorded_status": recorded, "executed_cases_inferred": False})
    auxiliary = {}
    for group, schema in (("preentry_invocation_failures", "finite-worker-driver-invocation-failure@1"),
                          ("progress_observer_failures", "finite-worker-progress-observer-failure@1")):
        declared = ledger[group][0]
        raw = document(bodies[declared["metadata_pin"]["path"]])
        require(raw["schema"] == schema and raw["status"] == declared["status"]
                and raw["exception"] == declared["exception"] and raw["all_os_launch_count"] is None,
                "auxiliary raw failure identity differs")
        if group == "preentry_invocation_failures":
            require(raw["failure_stage"] == declared["failure_stage"] and raw["driver_generation"] == declared["driver_generation"]
                    and raw["intended_output_root_exists"] is declared["output_root_existed_at_failed_invocation"] is False
                    and raw["retained_failures_rewritten"] is declared["failure_rewritten"] is False
                    and raw["native_container_created"] is declared["native_container_created"] is False
                    and raw["native_fixture_entry"] is declared["native_fixture_entry"] is False,
                    "preentry failure promoted into fixture entry")
            require(type(declared["recorded_fixture_solver_training_worker_jobs"]) is int
                    and declared["recorded_fixture_solver_training_worker_jobs"] == 0
                    and declared["elapsed_seconds"] is None and declared["all_OS_process_launch_count"] is None,
                    "preentry unmeasured work fabricated")
            stdout = declared["stdout_pin"]
            require(raw["stdout"] == stdout["path"] and raw["stdout_sha256"] == stdout["sha256"]
                    and type(raw["stdout_bytes"]) is int and raw["stdout_bytes"] == stdout["bytes"],
                    "unselected stdout declaration identity differs")
        else:
            fields = ("coding_worker_launched_by_observer", "in_container_progress_process_launched",
                      "native_fixture_requalified_by_observer", "proof_or_training_job_launched_by_observer",
                      "raw_engine_output_retained")
            require(all(raw[key] is declared[key] is False for key in fields)
                    and raw["read_only_engine_queries"] is declared["read_only_engine_queries"] is True
                    and raw["selection"] == [] and raw["elapsed_seconds"] is declared["elapsed_seconds"] is None
                    and declared["all_os_launch_count"] is None
                    and raw["failure_boundary"] == declared["failure_boundary"], "observer failure scope promoted")
            require(raw["subsequent_actual_driver_result"] == declared["subsequent_actual_driver_result"]
                    and raw["subsequent_result_container_removed"] is declared["subsequent_result_container_removed"] is True
                    and type(raw["subsequent_result_returncode"]) is type(declared["subsequent_result_returncode"]) is int
                    and raw["subsequent_result_returncode"] == declared["subsequent_result_returncode"] == 0,
                    "distinct subsequent driver declaration differs")
        auxiliary[group] = {"declaration": declared, "raw_metadata_reconciled": True,
                            "execution_authenticated": False, "unselected_references_followed": False}
    auxiliary["explicit_unexecuted_generation06"] = {"declaration": ledger["explicit_unexecuted_generation06"],
                                                    "receiving_disposition": "ledger_declaration_only_not_replayed"}
    costs = {}
    for group, rows, key in (("host", host, "finished_host_driver_seconds_sum"), ("Docker", docker, "finished_Docker_driver_seconds_sum"),
                             ("stream", stream, "finished_stream_driver_seconds_sum")):
        total = sum(row["driver_seconds"] for row in rows)
        require(number(ledger[key]) == total, "ordered recorded cost sum differs")
        costs[group] = {"ordered_seconds_sum": total, "attempt_count": len(rows),
                        "clock": "recorded internal review clock" if group == "stream" else "recorded driver clock",
                        "unique_cpu_or_calendar_time": False}
    require(ledger["total_elapsed_wall_time"] is None and ledger["all_native_process_launch_count"] is None,
            "unavailable total wall/process census must stay unknown")
    require(summary["immutable_runtime_generation_cid"] == machine["generation"]["generation_cid"]
            and summary["generation_manifest_sha256"] == machine["generation"]["manifest"]["sha256"]
            and summary["native_runtime_profile_generation"] == "12", "matched recorded generation identity differs")
    by_driver = {row["attempt"]: row for row in ledger["Docker_attempts"]}
    require([row["attempt"] for row in machine["selected_native_cases"]] == ["docker-positive-07", "docker-child-proof-02", "docker-child-epoch-02"], "machine exact three-driver population")
    for row, declared in zip(summary["cases"], machine["selected_native_cases"], strict=True):
        driver = by_driver[declared["attempt"]]
        pin = next(pin for pin in driver["raw_file_pins"] if Path(pin["path"]).name == "container-execution-final.json")
        require({key: pin[key] for key in ("path", "sha256", "bytes")} == declared["driver"] == row["container_final_pin"]
                and number(row["driver_elapsed_seconds"]) == driver["elapsed_seconds"] == number(declared["driver_seconds"]), "summary raw driver binding differs")
    require(supplement["original_final_cost_ledger_pin"]["sha256"] == machine["attempt_cost_ledger"]["sha256"], "postledger original commitment differs")
    require(supplement["whole_current_live_runtime_qualified"] is False and machine["whole_current_live_runtime_qualified"] is False,
            "changed live source qualification promoted")
    require(type(supplement["postledger_attempts"]) is list and len(supplement["postledger_attempts"]) == 2
            and all(row["elapsed_seconds"] is None for row in supplement["postledger_attempts"]), "postledger unavailable costs must stay null")
    require(machine["all_32_RPI_production_exits_open"] is True and machine["global_optimizer_convergence_proved"] is False,
            "production or convergence promoted")
    require(machine["broad_host_training_census"] is None and machine["complete_OS_launch_count"] is None,
            "unavailable broad host census must remain null")
    return {"host_attempts": host, "docker_attempts": docker, "stream_attempts": stream, "metadata_audits": audit_rows,
            "non_native_preparations": preparations, "driver_costs": costs, "host_phase_population": dict(phase_totals),
            "matched_generation12_recorded_outcomes": [{"case": row["case"], "native_task_status": row["native_task_status"],
                "native_settlement": row["native_settlement"], "outcome_authenticated": False} for row in summary["cases"]],
            "whole_suite_generation_frontiers": {"host11": "failed whole 37-case generation11 attempt", "host12": "failed whole 23-case generation12 attempt",
                "host13": "separate one-case generation13 retry; no combined 23-case passing run", "generation12_source_capsule_reconstructed": False},
            "null_cost_frontiers": {"total_elapsed_wall_time": None, "complete_OS_launch_count": None,
                "broad_host_training_census": machine["broad_host_training_census"], "postledger_attempts": supplement["postledger_attempts"]},
            "auxiliary_declared_attempts": auxiliary}


def population(root, expected):
    require(root.is_absolute() and root.resolve(strict=True) == root and stat.S_ISDIR(root.lstat().st_mode), "canonical output directory required")
    files, dirs, pending = set(), set(), [root]
    while pending:
        folder = pending.pop()
        with os.scandir(folder) as entries:
            for entry in entries:
                relative = Path(entry.path).relative_to(root).as_posix()
                info = entry.stat(follow_symlinks=False)
                require(len(files) < MAX_FILES and len(dirs) <= 1, "output population bound")
                if stat.S_ISDIR(info.st_mode):
                    require(relative == "retained", "unexpected output directory")
                    dirs.add(relative)
                    pending.append(Path(entry.path))
                else:
                    require(stat.S_ISREG(info.st_mode) and relative in expected, "unexpected nonregular/output file")
                    files.add(relative)
    require(files == expected and dirs == {"retained"} and root.resolve(strict=True) == root,
            "exact final output population required")
    return {"file_count": len(files), "directory_count": len(dirs)}


def audit(manifest_path, output, *, relocated_sources=None):
    manifest_path, output = Path(manifest_path).absolute(), Path(output).absolute()
    capture = Capture(relocated_sources)
    manifest_raw = capture.read(manifest_path, mapped=False, maximum=256 * 1024)
    require(len(manifest_raw) <= 256 * 1024, "input manifest bound")
    spec = document(manifest_raw)
    require(set(spec) == {"schema", "selected_profile", *ROLES} and spec["schema"] == INPUT_SCHEMA
            and spec["selected_profile"] == PROFILE, "closed selected input profile required")
    top, raw_top, docs = {}, {}, {}
    for role in ROLES:
        top[role] = descriptor(spec[role])
        raw_top[role] = capture.read(top[role]["path"], top[role])
        require(sha256(raw_top[role]).hexdigest() == PUBLIC_ANCHORS[role], "independently pinned public selection required")
        docs[role] = document(raw_top[role])
    ledger, machine, supplement = (docs[role] for role in ("attempt_ledger", "machine_review", "postledger_supplement"))
    for role, key in (("attempt_ledger", "attempt_cost_ledger"), ("postledger_supplement", "post_ledger_finalization_cost_supplement")):
        outer = machine[key]
        require(set(outer) == {"bytes", "path", "sha256"} and outer["path"] == top[role]["path"]
                and outer["sha256"] == top[role]["sha256"] and type(outer["bytes"]) is int
                and outer["bytes"] == top[role]["size_bytes"], "independent machine input commitment differs")
    selected, memberships, frontiers = selected_inputs(ledger, Path(top["attempt_ledger"]["path"]))
    selected.update({pin["path"]: pin for pin in top.values()})
    require(len(selected) == 107, "selected top/child population")
    if relocated_sources is not None:
        require(set(relocated_sources) == set(selected), "exact explicit relocation population")
        require(len(set(relocated_sources.values())) == len(selected), "distinct relocated physical bodies required")
    bodies = {path: capture.read(path, pin) for path, pin in selected.items()}
    findings = reconcile(ledger, machine, supplement, bodies)
    forbidden = {manifest_path.parent, *(physical.parent for physical in capture.files)}
    require(not output.exists() and not output.is_symlink() and output.resolve(strict=False) == output
            and not any(output == scope or output.is_relative_to(scope) for scope in forbidden), "fresh output outside input scopes required")
    output.mkdir(parents=True)
    (output / "retained").mkdir()
    retained = Capture()
    files = []

    def retain(relative, raw):
        path = output / relative
        with path.open("xb") as stream:
            stream.write(raw)
        path.chmod(0o444)
        pin = {"path": str(path), "sha256": sha256(raw).hexdigest(), "size_bytes": len(raw)}
        require(retained.read(path, pin) == raw, "written retained copy differs")
        return pin

    inputs = [(str(manifest_path), manifest_raw), *((path, bodies[path]) for path in sorted(selected))]
    for index, (original, raw) in enumerate(inputs):
        relative = "retained/" + str(index).zfill(3) + ".bytes"
        pin = retain(relative, raw)
        files.append({**pin, "relative_path": relative, "original_path": original})
    nested = {"schema": "codebase-ir-dispatch-attempt-selected-custody@1", "status": "passed",
              "input_manifest_sha256": sha256(manifest_raw).hexdigest(), "selected_inputs": top,
              "selected_memberships": memberships, "retained_files": files, "selected_unique_file_count": 107,
              "selected_input_bytes": sum(len(raw) for raw in bodies.values()),
              "scope": "Exact selected public bytes and recorded declaration bindings; no producer or execution authentication",
              **{flag: False for flag in FALSE_FLAGS}}
    nested_pin = retain("selected_custody.json", canonical(nested))
    expected = {row["relative_path"] for row in files} | {"selected_custody.json"}
    before = population(output, expected)
    input_stability, retained_stability = capture.stable(), retained.stable()
    require(input_stability["unchanged"] is True and retained_stability["unchanged"] is True, "final stability refused")
    require(capture.stable()["unchanged"] is True and retained.stable()["unchanged"] is True, "late stability refused")
    after = population(output, expected)
    report = {"schema": SCHEMA, "status": "passed", "selected_profile": PROFILE,
              "manifest_sha256": sha256(manifest_raw).hexdigest(), **{role + "_sha256": top[role]["sha256"] for role in ROLES},
              "selected_file_count": 107, "selected_input_bytes": sum(map(len, bodies.values())),
              "host_attempt_count": 11, "docker_attempt_count": 9, "stream_attempt_count": 2,
              "adverse_host_attempt_count": 10, "unqualified_docker_driver_count": 5,
              "metadata_audit_attempt_count": 23, "non_native_preparation_count": 21,
              "new_native_jobs_launched": 0, "additional_attempted_training_epochs": 0,
              "zero_count_scope": "Work produced by this receiving audit, not a census of historical native/training work",
              **findings, "raw_body_frontiers": frontiers, "selected_memberships": memberships,
              "selected_custody": nested_pin, "retained_files": files, "input_stability": input_stability,
              "retained_copy_stability": retained_stability, "retained_population_before_report": before,
              "retained_population_after_rereads": after, "explicit_relocated_input_map_used": relocated_sources is not None,
              "scope": "Pinned historical attempt/test/cost consistency; signed/runtime/source/publication authority not replayed",
              "bounds": {"file_bytes": MAX_FILE, "main_report_bytes": MAX_REPORT, "read_files": MAX_FILES, "first_capture_bytes": MAX_BYTES,
                         "copy_capture_bytes": MAX_BYTES, "first_plus_copy_bytes": 2 * MAX_BYTES,
                         "deadline_seconds": 120, "XML_cases": 512, "XML_nodes": 4096, "XML_depth": 8,
                         "JSONL_rows": 4096, "JSONL_line_bytes": 128 * 1024},
              **{flag: True for flag in TRUE_FLAGS}, **{flag: False for flag in FALSE_FLAGS}}
    report_raw = bounded_canonical(report, MAX_REPORT)
    report_path = output / "dispatch_attempt_custody.json"
    with report_path.open("xb") as stream:
        stream.write(report_raw)
    require(Capture.raw(report_path, MAX_REPORT) == report_raw, "written main report differs")
    require(capture.stable()["unchanged"] is True and retained.stable()["unchanged"] is True, "post-report referenced body drift")
    population(output, expected | {"dispatch_attempt_custody.json"})
    require(Capture.raw(report_path, MAX_REPORT) == report_raw, "late main report differs")
    population(output, expected | {"dispatch_attempt_custody.json"})
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.manifest, args.output)
    print(json.dumps({key: report[key] for key in ("status", "selected_file_count", "host_attempt_count", "docker_attempt_count", "stream_attempt_count")}))


if __name__ == "__main__":
    main()
