"""Receive only selected frozen failed TLA attempts; execute no captured code."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import stat
from collections import Counter
from pathlib import Path

INPUT_SCHEMA = "codebase-ir-tla-operation-controls-input@1"
REPORT_SCHEMA = "codebase-ir-tla-operation-controls@1"
REPORT_NAME = "tla_operation_controls.json"
IDS = ("initial", "final", "accepted")
ROLES = ("source_freeze", "command_result", "result", "request_audit", "launch_audit",
         "lifecycle_audit", "control_audit", "fixtures", "command", "scheduler_config", "wrapper", "partial")
ANCHORS = {
    "initial": {"result": "f2dc443136560555513760cf2911e97ea5f18780fa9db7b0ab76b3f1fee97bce",
                "command_result": "6277d7aced8ea3cdaf9d603bff5755da092188dc48867bb74f6a5b2449d94782",
                "source_freeze": "02f00eeb9412ac899fb6fd2c81f3ecaa72f0b71bac0c61443f9902d60fe0a6d9"},
    "final": {"result": "2c4ebbed45a5b55612f02b12a1528a1041c85d1cdbe564dcde3a3be7616470c0",
              "command_result": "c6b49485125bed94a68ab08945718fb9d64be2714e96dfb8c13a143431bbd8ae",
              "source_freeze": "e1fa686d41387608ce97b8301c296fc2562fe67d7c774f4e961458b121d5392f"},
    "accepted": {"result": "11ad7523777acb5c073a972019c9dd24a51114c76995a14562606aff77292917",
                 "command_result": "e96d2853754a18c9c6ab979950dd9c3623873724c272c65180b529b7404733a9",
                 "source_freeze": "da5b20029887b9b512087fd694b81a9b156598b0f15ee2c8a72893d380ceb634"},
}
TRUE = ("retained_tla_operation_custody_conformance", "recorded_phase_bindings_reconciled",
        "failed_whole_attempts_preserved", "partial_results_not_promoted", "input_files_unchanged")
FALSE = ("native_execution_performed", "training_executed", "current_authority_claimed",
         "owner_database_opened", "profile_keys_read", "owner_sources_imported", "source_execution_replayed",
         "checker_executions_replayed", "signature_authentication_performed", "process_origin_attested",
         "resource_enforcement_qualified", "original_request_custody_qualified", "aggregate_operation_success_qualified",
         "model_check_authority_qualified", "proof_authority_qualified", "live_eligibility_qualified",
         "production_acceptance_qualified", "native_export_adoption_qualified", "throughput_improvement_qualified")
ZERO = ("runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs")
MAX_FILES, MAX_TOTAL, MAX_FILE = 96, 32 * 1024 * 1024, 2 * 1024 * 1024
MAX_MANIFEST, MAX_REPORT = 128 * 1024, 4 * 1024 * 1024
STOP_KINDS = ("pre_setup_cancel", "live_setup_cancel", "after_setup_cancel", "compile_deadline", "live_model_cancel")
LIFECYCLE_FLAGS = ("cancelled", "output_truncated", "process_tree_terminated", "resource_exhausted",
                   "timed_out", "unavailable", "workspace_cleaned", "workspace_limit_exceeded")
RESULT_FIELDS = {"audit_sha256", "checks", "child_usage", "controls", "elapsed_seconds", "error", "launches",
                 "lifecycles", "native_lifecycles", "phase_counts", "prelaunch_lifecycles", "runs", "runtime", "schema",
                 "scope", "selection_environment", "shared_after", "shared_before", "shared_pool_compatibility",
                 "source_pins_after", "source_pins_before", "status", "tool_files_after", "tool_files_before",
                 "tool_selection", "wrapper_profile"}


class Refusal(ValueError):
    """The selected receiving profile was not satisfied."""


def need(condition, label):
    if not condition:
        raise Refusal(label)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()


def same(left, right):
    return canonical(left) == canonical(right)


def closed(value, fields, label):
    need(type(value) is dict and set(value) == set(fields), label + " closed fields")


def integer(value, low=0, high=2**63 - 1):
    return type(value) is int and low <= value <= high


def number(value, low=0):
    return type(value) in (int, float) and math.isfinite(value) and low <= value <= 1e100


def digest(value):
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def document(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, "duplicate JSON key")
            result[key] = value
        return result

    def parse_integer(token):
        need(len(token) <= 20, "integer allocation bound")
        value = int(token)
        need(abs(value) <= 2**63 - 1, "integer allocation bound")
        return value

    def parse_float(token):
        need(len(token) <= 64 and math.isfinite(float(token)), "finite JSON float")
        return float(token)

    def invalid(_):
        raise Refusal("nonfinite JSON")

    value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_int=parse_integer,
                       parse_float=parse_float, parse_constant=invalid)
    count, pending = 0, [(value, 0)]
    while pending:
        node, depth = pending.pop()
        count += 1
        need(depth <= 40 and count <= 150000, "JSON structural bound")
        if type(node) is str:
            need(len(node) <= 200000 and not any(0xD800 <= ord(c) <= 0xDFFF for c in node), "JSON string bound/surrogate")
        elif type(node) is dict:
            need(len(node) <= 2048, "JSON mapping bound")
            pending.extend((x, depth + 1) for pair in node.items() for x in pair)
        elif type(node) is list:
            need(len(node) <= 4096, "JSON list bound")
            pending.extend((x, depth + 1) for x in node)
    return value


def bounded(path, cap):
    need(path.is_absolute() and path.resolve(strict=True) == path, "canonical input path")
    info = path.stat(follow_symlinks=False)
    need(stat.S_ISREG(info.st_mode) and info.st_size <= cap, "regular preallocation bound")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        def key(s):
            return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns
        need(stat.S_ISREG(before.st_mode) and key(info) == key(before), "descriptor identity")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(cap + 1)
        after, final = os.fstat(fd), path.stat(follow_symlinks=False)
        need(len(raw) == info.st_size and key(before) == key(after) == key(final)
             and path.resolve(strict=True) == path, "stable bounded descriptor")
        return raw
    finally:
        os.close(fd)


class Capture:
    def __init__(self):
        self.raw, self.total = {}, 0

    def take(self, path, pin=None, cap=MAX_FILE):
        path = Path(path).absolute()
        if path not in self.raw:
            need(len(self.raw) < MAX_FILES, "unique input bound")
            available = min(cap, MAX_TOTAL - self.total)
            if pin is not None:
                closed(pin, ("path", "sha256", "size_bytes"), "descriptor")
                need(type(pin["path"]) is str and Path(pin["path"]) == path
                     and digest(pin["sha256"]) and integer(pin["size_bytes"], 0, cap), "descriptor types")
                available = min(available, pin["size_bytes"])
            need(available >= 0, "aggregate allocation bound")
            raw = bounded(path, available)
            self.raw[path], self.total = raw, self.total + len(raw)
        raw = self.raw[path]
        if pin is not None:
            need(len(raw) == pin["size_bytes"] and sha(raw) == pin["sha256"], "exact raw descriptor")
        return raw

    def stable(self):
        for path, raw in self.raw.items():
            need(bounded(path, len(raw)) == raw, "late original/copy/report drift")


def phase(argv):
    need(type(argv) is list and 0 < len(argv) <= 256 and all(type(s) is str and len(s) <= 4096 for s in argv), "native argv")
    return "setup" if "-version" in argv else "help" if "-help" in argv else "model"


def maps(rows, lifecycle=False):
    need(type(rows) is list and len(rows) <= 128, "phase row bound")
    result = {}
    for row in rows:
        need(type(row) is dict and type(row.get("case")) is str, "phase case type")
        argv = row["request"]["argv"] if lifecycle else row["argv"]
        key = row["case"], phase(argv)
        need(key not in result, "duplicate/ambiguous native phase")
        result[key] = row
    return result


def reconcile_attempt(ident, docs):
    """Pure selected-record consistency, with historical population kept explicit."""
    need(ident in IDS, "attempt identity")
    r, freeze, command_result = docs["result"], docs["source_freeze"], docs["command_result"]
    closed(r, RESULT_FIELDS, "native result")
    need(r["schema"] == "tla-operation-control-benchmark@1", "historical native schema")
    closed(freeze, ("independent_review", "native_runner_sha256", "native_sources", "recorded_at_utc", "retained_sources", "selected_sources"), "source freeze")
    closed(command_result, ("after", "argv", "before", "cwd", "env_overrides", "returncode", "seconds"), "command result")
    need(r["status"] == "failed" and type(r["error"]) is str and r["error"], "failed whole attempt")
    need(type(command_result["returncode"]) is int and command_result["returncode"] == 1, "failed command exact returncode")
    need(number(command_result["seconds"]) and number(r["elapsed_seconds"]), "separate elapsed clocks")
    need(same(command_result["before"], command_result["after"]), "command source declarations unchanged")
    need(same(freeze["native_sources"], r["source_pins_before"]) and same(r["source_pins_before"], r["source_pins_after"])
         and len(r["source_pins_before"]) == 79 and all(digest(v) for v in r["source_pins_before"].values()), "79 captured source declarations")
    need(same(freeze["native_sources"], command_result["before"])
         and all(freeze["selected_sources"].get(k) == v for k, v in command_result["before"].items()), "selected source metadata binding")
    command = docs["command"]
    need(command["argv"] == command_result["argv"] and command["cwd"] == command_result["cwd"]
         and command["benchmark_sha256"] == command_result["before"][command["argv"][1]], "recorded command/benchmark binding")
    need(same(r["tool_files_before"], r["tool_files_after"]), "recorded tool declarations unchanged")
    need(all(value is True for value in r["checks"].values()) and set(r["checks"]) == {
        "java_selection_environment_restored", "owned_work_drained", "selected_tool_files_unchanged", "shared_config_unchanged", "sources_stable"}, "recorded cleanup checks")
    need(same(docs["scheduler_config"]["config"], r["shared_before"]["config"])
         and same(r["shared_before"]["config"], r["shared_after"]["config"])
         and all(type(r["shared_after"][k]) is int and r["shared_after"][k] == 0
                 for k in ("owned_active_leases", "owned_waiting_requests")), "recorded configuration and owned drain")
    wrappers = [v for k, v in r["tool_files_before"].items() if Path(k).name == "tlc-memory-aware"]
    need(wrappers == [sha(docs["wrapper"])], "retained wrapper raw binding")
    closed(docs["fixtures"], ("compiler_input", "deadline", "invalid", "valid"), "fixtures")
    for fixture_name in ("deadline", "invalid", "valid"):
        fixture = docs["fixtures"][fixture_name]
        need(sha(fixture["model_text"].encode()) == fixture["model_digest"]
             and sha(fixture["tlc_config_text"].encode()) == fixture["tlc_config_digest"]
             and fixture["bounded"] is True and fixture["unbounded_proof"] is False, "raw fixture model/config bound identities")
    audits = {role: docs[role] for role in ("request_audit", "launch_audit", "lifecycle_audit", "control_audit")}
    need(set(r["audit_sha256"]) == {role.replace("_", "-") + ".json" for role in audits}, "audit hash population")
    # Raw hashes are checked separately by the file receiver, not regenerated from JSON formatting.
    requests, launches, lives = maps(audits["request_audit"]), maps(audits["launch_audit"]), maps(audits["lifecycle_audit"], True)
    need(set(requests) == set(launches) == set(lives), "whole native phase identity join")
    budgets = {}
    for row in audits["control_audit"]["phase_budgets"]:
        closed(row, ("at_monotonic", "case", "deadline", "phase", "remaining_seconds", "request_timeout_seconds"), "phase budget")
        key = row["case"], row["phase"]
        # Constructor request labels carry :constructor; their operation label does not.
        key = (key[0] + ":constructor" if key[1] == "setup" else key[0], key[1])
        need(key not in budgets and key in requests, "budget identity population")
        need(all(number(row[k]) for k in ("at_monotonic", "deadline", "remaining_seconds", "request_timeout_seconds"))
             and row["request_timeout_seconds"] > 0, "recorded cooperative budget types")
        budgets[key] = row
    need(set(budgets) == set(requests), "complete phase budget population")
    phase_rows = []
    for key, req in requests.items():
        launch, life = launches[key], lives[key]
        closed(req, ("argv", "case", "input_bytes", "input_sha256", "limits", "output_paths"), "native request row")
        closed(launch, ("argv", "at_monotonic", "case", "launch_lease_id", "owned_leases", "root_allocations", "thread", "waiting"), "native launch row")
        closed(life, ("case", "request", "result", "shared_backoff_after"), "native lifecycle row")
        lr, out, limits = life["request"], life["result"], req["limits"]
        need(req["argv"] == lr["argv"] == out["command"], "exact request/lifecycle argv")
        cpu = math.ceil(limits["cpu_seconds"])
        file_size = limits["max_file_bytes"] if limits["max_file_bytes"] is not None else limits["max_workspace_bytes"]
        need(integer(file_size, 1) and integer(limits["memory_bytes"], 1) and number(limits["cpu_seconds"])
             and limits["enforce_file_size_limit"] is True, "recorded launch wrapper bounds")
        prefix = ["/usr/bin/prlimit", "--core=0:0", f"--fsize={file_size}:{file_size}",
                  f"--cpu={cpu}:{cpu}", f"--as={limits['memory_bytes']}:{limits['memory_bytes']}", "--"]
        need(launch["argv"] == prefix + req["argv"], "exact recorded launch wrapper")
        need(type(out["returncode"]) is int or out["returncode"] is None, "exact lifecycle returncode type")
        need(all(type(out[k]) is bool for k in LIFECYCLE_FLAGS) and out["workspace_cleaned"] is True, "typed lifecycle and recorded cleanup")
        need(integer(out["pid"], 1) and number(out["elapsed_seconds"]) and all(type(out[k]) is str for k in ("stdout", "stderr", "error", "termination_reason")), "lifecycle scalar types")
        need(lr["stdin_is_empty"] is lr["java_option_environment_absent"] is True
             and integer(lr["input_file_count"]) and lr["input_file_count"] == len(req["input_bytes"])
             and integer(lr["output_path_count"]) and lr["output_path_count"] == len(req["output_paths"]), "recorded native request shape")
        need(set(req["input_bytes"]) == set(req["input_sha256"])
             and all(integer(v) for v in req["input_bytes"].values()) and all(digest(v) for v in req["input_sha256"].values()), "input size/digest declarations")
        for field in ("max_output_bytes", "memory_bytes", "resident_memory_bytes"):
            need(integer(limits[field], 1) and type(lr[field]) is int and limits[field] == lr[field], "request exact integer bound")
        need(number(limits["timeout_seconds"]) and limits["timeout_seconds"] > 0
             and lr["timeout_seconds"] == limits["timeout_seconds"] == budgets[key]["request_timeout_seconds"], "phase timeout custody")
        need(integer(launch["thread"], 1) and integer(launch["waiting"])
             and type(launch["launch_lease_id"]) is str and launch["launch_lease_id"], "recorded launch labels")
        phase_rows.append({"case": key[0], "phase": key[1], "request": req, "launch": launch,
                           "lifecycle": life, "budget": budgets[key], "authentication_verified": False})
    count = Counter(k[1] for k in requests)
    expected = {"setup": 2, "model": 2, "help": 2} if ident == "initial" else {"setup": 17, "model": 14, "help": 13}
    need(dict(count) == expected and set(r["phase_counts"]) == set(expected)
         and all(type(r["phase_counts"][k]) is int and r["phase_counts"][k] == v for k, v in expected.items()), "exact historical phase populations")
    need(all(type(r[k]) is int and r[k] == len(requests) for k in ("launches", "lifecycles", "native_lifecycles"))
         and type(r["prelaunch_lifecycles"]) is int and r["prelaunch_lifecycles"] == 0, "typed total phase population")
    cases = []
    need([x["workers"] for x in r["runs"]] == ([] if ident == "initial" else [1, 2, 4])
         and all(type(x["workers"]) is int and number(x["elapsed_seconds"]) for x in r["runs"]), "ordered complete batch population")
    for batch in r["runs"]:
        expected_cases = [(f"parallel:{batch['workers']}:{route}:{valid}", route, valid) for route in ("engine", "helper") for valid in (True, False)]
        need([(x["case"], x["route"], x["valid"]) for x in batch["cases"]] == expected_cases, "complete ordered native cases")
        for case in batch["cases"]:
            need(type(case["valid"]) is bool and type(case["phase_count"]) is int and case["phase_count"] == 3, "case exact typed phase count")
            outcome = case["result"]
            closed(outcome, ("counterexample_status", "disposition", "evidence", "interface", "outcome", "provider", "request_digest", "request_id", "result", "schema_version"), "wire execution result")
            need(outcome["interface"] == "StateExecutionResult@2" and outcome["schema_version"] == "state-execution-result/v2", "wire schema identity")
            need(outcome["provider"] == "tlc" and outcome["request_id"] == "req:" + case["case"] and digest(outcome["request_digest"]), "case request identity")
            evidence, raw_outcome = outcome["evidence"], outcome["outcome"]
            receipt, artifact = raw_outcome["receipt"], raw_outcome["artifacts"]
            fixture = docs["fixtures"]["valid" if case["valid"] else "invalid"]
            wire_receipt = evidence["receipt"]
            need(same(outcome["result"], raw_outcome["result"])
                 and same({k: v for k, v in receipt.items() if k != "timeout_seconds"},
                          {k: v for k, v in wire_receipt.items() if k != "timeout_seconds"})
                 and number(receipt["timeout_seconds"]) and number(wire_receipt["timeout_seconds"])
                 and receipt["timeout_seconds"] == wire_receipt["timeout_seconds"]
                 and outcome["request_digest"] == evidence["request_digest"] and digest(raw_outcome["request_digest"]), "wire result/receipt/request custody")
            need(artifact["artifact_digest"] == fixture["artifact_digest"] == receipt["artifact_digest"] == evidence["module"]["artifact_digest"]
                 and artifact["model_digest"] == fixture["model_digest"] == receipt["model_digest"]
                 and receipt["configuration_digest"] == fixture["tlc_config_digest"], "captured module/config identities")
            request = requests[(case["case"], "model")]
            need(request["input_bytes"] == {"BoundedCounter.tla": len(fixture["model_text"].encode()),
                                             "BoundedCounter.cfg": len(fixture["tlc_config_text"].encode())}
                 and request["input_sha256"] == {"BoundedCounter.tla": fixture["model_digest"],
                                                 "BoundedCounter.cfg": fixture["tlc_config_digest"]}, "fixture to exact native model inputs")
            life = lives[(case["case"], "model")]["result"]
            need(all(life[k] is False for k in LIFECYCLE_FLAGS if k != "workspace_cleaned")
                 and len(life["stdout"].encode()) + len(life["stderr"].encode()) <= request["limits"]["max_output_bytes"], "completed case requires safe recorded lifecycle")
            need(receipt["stdout"] == life["stdout"] and receipt["stderr"] == life["stderr"]
                 and type(receipt["returncode"]) is int and receipt["returncode"] == life["returncode"]
                 and receipt["command"] == life["command"] and receipt["output_truncated"] is life["output_truncated"] is False, "receipt raw lifecycle binding")
            need(receipt["bounded"] is True and receipt["unbounded_proof"] is False
                 and all(evidence[k] is False for k in ("claim_proof", "claim_theorem", "authorizes_universal_proof", "proof_established", "theorem_established", "is_proved", "is_theorem_authority"))
                 and evidence["authority_ceiling"] == "bounded", "bounded recorded outcome ceiling")
            ce = evidence["counterexample"]
            need(type(ce["state_count"]) is int and ce["state_count"] == len(ce["states"])
                 and ce["replayed"] is (not case["valid"]), "recorded counterexample population/type")
            if case["valid"]:
                need(ce["states"] == [] and receipt["counterexample"] is None and life["returncode"] == 0, "recorded successful case frontier")
            else:
                need(same(ce["states"], receipt["counterexample"]["states"])
                     and all(type(v["index"]) is int for v in ce["states"])
                     and [v["index"] for v in ce["states"]] == [1, 2, 3] and life["returncode"] == 12, "recorded finite trace custody")
            want = "satisfied" if case["valid"] else "counterexample"
            need(outcome["disposition"] == evidence["disposition"] == want, "recorded disposition consistency")
            cases.append({"case": case["case"], "route": case["route"], "valid": case["valid"], "recorded_result": outcome,
                          "original_request_bytes_available": False, "new_model_check_authority": False})
    controls, covered = [], set()
    need([x["kind"] for x in r["controls"]] == ([] if ident == "initial" else list(STOP_KINDS)), "complete retained stop controls")
    for item in r["controls"]:
        need(item["case"] == "control:" + item["kind"] and item["result_published"] is False, "stopped operation has no result")
        stop = item["interruption"]
        need(stop["type"] == ("ProofOperationTimeout" if item["kind"] == "compile_deadline" else "ProofOperationCancelled")
             and stop["kind"] == ("timeout" if item["kind"] == "compile_deadline" else "cancelled")
             and integer(item["operation_timeout_ms"], 1) and type(stop["timeout_ms"]) is int
             and stop["timeout_ms"] == item["operation_timeout_ms"] and integer(stop["elapsed_ms"]), "typed outer interruption/budget")
        keys = {k for k in requests if k[0].removesuffix(":constructor") == item["case"]}
        need(type(item["phase_count"]) is int and item["phase_count"] == len(keys)
             and Counter(item["phases"]) == Counter(k[1] for k in keys), "stopped operation complete phase population")
        covered.update(keys)
        controls.append(copy.deepcopy(item))
    for case in cases:
        covered.update(k for k in requests if k[0].removesuffix(":constructor") == case["case"])
    unassigned = [row for row in phase_rows if (row["case"], row["phase"]) not in covered]
    expected_unassigned = 6 if ident == "initial" else 3
    need(len(unassigned) == expected_unassigned and (ident == "initial" or {x["case"].removesuffix(":constructor") for x in unassigned} == {"control:live_model_deadline"}), "unreturned operation phase frontier")
    if ident == "initial":
        need("tool_version exceeds maximum length of 256" in r["error"] and docs["partial"] is None, "initial metadata failure frontier")
        error_kind = "oversized_tool_version"
    else:
        need("interrupted aggregate operation published a result" in r["error"], "aggregate publication-error frontier")
        partial = docs["partial"]
        need(partial["status"] == "running" and partial["controls"] == [] and partial["checks"] == {}
             and all(same(partial[k], r[k]) for k in partial if k not in ("status", "controls", "checks")), "partial snapshot remains incomplete")
        error_kind = "producer_reported_result_after_expected_interruption"
    return {"id": ident, "recorded_whole_status": "failed", "recorded_command_returncode": 1,
            "failure_kind": error_kind, "recorded_error": r["error"], "recorded_command_seconds": command_result["seconds"],
            "recorded_native_seconds": r["elapsed_seconds"], "phase_counts": expected, "phase_count": len(phase_rows),
            "completed_batch_count": len(r["runs"]), "completed_case_count": len(cases), "recorded_no_result_control_count": len(controls),
            "phases": phase_rows, "completed_cases": cases, "recorded_no_result_controls": controls,
            "unreturned_operation_phases": unassigned, "failed_control_return_value_available": False,
            "partial_status": None if docs["partial"] is None else "running", "partial_promoted": False,
            "recorded_cleanup": r["checks"], "recorded_source_pins": r["source_pins_before"],
            "source_bodies_verified": False, "whole_operation_success_qualified": False,
            "raw_fixture_models": docs["fixtures"], "recorded_control_audit": docs["control_audit"],
            "recorded_source_freeze": freeze, "recorded_tool_pins": r["tool_files_before"],
            "recorded_shared_after": r["shared_after"],
            "unknowns": ["original caller controls and request bytes", "failed control exact returned value",
                         "process origin and enforcement", "source semantics and model-check truth", "current eligibility"]}


def mutation_controls(docs_list):
    """Authored record mutations keep the independent frozen original bytes fixed."""
    base = dict(docs_list)["accepted"]
    controls = []
    faults = (
        ("whole failure promoted", lambda d: d["result"].update(status="passed")),
        ("boolean command exit", lambda d: d["command_result"].update(returncode=True)),
        ("cleanup claim false", lambda d: d["result"]["checks"].update(owned_work_drained=False)),
        ("source declaration rebound", lambda d: d["result"]["source_pins_after"].update({next(iter(d["result"]["source_pins_after"])): "0" * 64})),
        ("retained wrapper altered", lambda d: d.update(wrapper=d["wrapper"] + b"x")),
        ("native phase omitted", lambda d: d["lifecycle_audit"].pop()),
        ("duplicate phase ambiguity", lambda d: d["request_audit"].append(copy.deepcopy(d["request_audit"][0]))),
        ("native argv drift", lambda d: d["request_audit"][0]["argv"].append("unbound")),
        ("launch prefix forged", lambda d: d["launch_audit"][0]["argv"].__setitem__(1, "--core=1:1")),
        ("boolean lifecycle exit", lambda d: d["lifecycle_audit"][0]["result"].update(returncode=False)),
        ("budget omitted", lambda d: d["control_audit"]["phase_budgets"].pop()),
        ("timeout custody drift", lambda d: d["request_audit"][0]["limits"].update(timeout_seconds=999.0)),
        ("boolean phase total", lambda d: d["result"].update(launches=True)),
        ("batch ordering", lambda d: d["result"]["runs"].reverse()),
        ("complete case omitted", lambda d: d["result"]["runs"][0]["cases"].pop()),
        ("front-end request rebound", lambda d: d["result"]["runs"][0]["cases"][0]["result"].update(request_id="req:forged")),
        ("receipt output forged", lambda d: d["result"]["runs"][0]["cases"][0]["result"]["outcome"]["receipt"].update(stdout="forged")),
        ("unbounded proof promoted", lambda d: d["result"]["runs"][0]["cases"][0]["result"]["evidence"].update(claim_proof=True)),
        ("stop result published", lambda d: d["result"]["controls"][0].update(result_published=True)),
        ("typed timeout rebound", lambda d: d["result"]["controls"][3]["interruption"].update(type="ProofOperationCancelled")),
        ("partial promoted", lambda d: d["partial"].update(status="passed")),
        ("unknown native result field", lambda d: d["result"].update(current_authority=True)),
    )
    for label, mutate in faults:
        changed = copy.deepcopy(base)
        mutate(changed)
        # Repairs the container hash labels so each refusal reaches record semantics.
        changed["result"]["audit_sha256"] = {
            role.replace("_", "-") + ".json": sha(canonical(changed[role]))
            for role in ("request_audit", "launch_audit", "lifecycle_audit", "control_audit")}
        try:
            reconcile_attempt("accepted", changed)
        except (Refusal, KeyError, TypeError) as exc:
            controls.append({"control": label, "refused": True, "reason": str(exc),
                             "independent_original_anchors_unchanged": True})
        else:
            raise Refusal("unrefused authored control: " + label)
    return controls


def output_population(root, expected):
    need(root.is_absolute() and root.resolve(strict=True) == root and stat.S_ISDIR(root.stat(follow_symlinks=False).st_mode), "canonical output root")
    files, dirs = set(), set()
    for folder in (root, root / "retained"):
        with os.scandir(folder) as rows:
            for row in rows:
                info = row.stat(follow_symlinks=False)
                relative = Path(row.path).relative_to(root).as_posix()
                if stat.S_ISREG(info.st_mode):
                    need(relative in expected and len(files) < 64, "unexpected output file")
                    files.add(relative)
                else:
                    need(stat.S_ISDIR(info.st_mode) and relative == "retained", "unexpected output directory/alias")
                    dirs.add(relative)
    need(files == set(expected) and dirs == {"retained"} and root.resolve(strict=True) == root, "exact output population")


def final_fence(capture, output, expected):
    capture.stable()
    output_population(output, expected)
    for path, raw in capture.raw.items():
        if path.is_relative_to(output):
            need(bounded(path, len(raw)) == raw, "late retained/report bytes")
    capture.stable()
    output_population(output, expected)


def audit(manifest_path, output):
    manifest_path, output = Path(manifest_path).absolute(), Path(output).absolute()
    cap = Capture()
    manifest_raw = cap.take(manifest_path, cap=MAX_MANIFEST)
    manifest = document(manifest_raw)
    closed(manifest, ("schema", "fixture_origin", "attempts"), "input manifest")
    need(manifest["schema"] == INPUT_SCHEMA and manifest["fixture_origin"] == "retained_failed_tla_operation_attempts", "input profile identity")
    need(type(manifest["attempts"]) is list and [x.get("id") for x in manifest["attempts"]] == list(IDS), "ordered attempt identities")
    protected = {manifest_path.parent}
    docs_list, selected, bindings = [], [], {}
    for item in manifest["attempts"]:
        closed(item, ("id", *ROLES), "attempt input")
        ident, docs = item["id"], {}
        for role in ROLES:
            pin = item[role]
            if role == "partial" and ident == "initial":
                need(pin is None, "initial partial absent")
                docs[role] = None
                continue
            closed(pin, ("path", "sha256", "size_bytes"), "input descriptor")
            need(type(pin["path"]) is str, "input descriptor path type")
            path = Path(pin["path"])
            protected.add(path.parent)
            raw = cap.take(path, pin)
            selected.append((ident, role, path))
            docs[role] = raw if role == "wrapper" else document(raw)
            if role in ANCHORS[ident]:
                need(sha(raw) == ANCHORS[ident][role], "immutable independent attempt anchor " + ident + "/" + role)
                bindings[ident + "_" + role + "_sha256"] = sha(raw)
        for role in ("request_audit", "launch_audit", "lifecycle_audit", "control_audit"):
            name = role.replace("_", "-") + ".json"
            need(docs["result"]["audit_sha256"][name] == item[role]["sha256"], "raw audit binding " + role)
        docs_list.append((ident, docs))
    need(len(selected) == 35 and len({p for _, _, p in selected}) == 35, "unique selected input closure")
    need(not output.exists() and output.parent.resolve(strict=True) == output.parent
         and not any(output == p or output.is_relative_to(p) for p in protected), "safe fresh output outside inputs")
    summaries = [reconcile_attempt(ident, docs) for ident, docs in docs_list]
    controls = mutation_controls(docs_list)
    cap.stable()
    output.mkdir()
    (output / "retained").mkdir()
    retained = []
    for index, (path, raw) in enumerate(tuple(cap.raw.items())):
        destination = output / "retained" / f"{index:02d}-{path.name}"
        destination.write_bytes(raw)
        cap.take(destination, cap=len(raw))
        retained.append({"original_path": str(path), "path": str(destination), "relative_path": destination.relative_to(output).as_posix(),
                         "sha256": sha(raw), "size_bytes": len(raw)})
    report = {"schema": REPORT_SCHEMA, "status": "passed", "fixture_origin": manifest["fixture_origin"],
              "manifest_sha256": sha(manifest_raw), **bindings, **{x: True for x in TRUE}, **{x: False for x in FALSE}, **{x: 0 for x in ZERO},
              "attempt_count": 3, "failed_whole_attempt_count": 3, "recorded_native_phase_count": sum(x["phase_count"] for x in summaries),
              "completed_batch_count": sum(x["completed_batch_count"] for x in summaries), "completed_case_count": sum(x["completed_case_count"] for x in summaries),
              "recorded_no_result_control_count": sum(x["recorded_no_result_control_count"] for x in summaries),
              "controls_count": len(controls), "controls_refused": len(controls), "controls": controls,
              "selected_file_count": 35, "selected_input_bytes": sum(len(cap.raw[p]) for _, _, p in selected), "attempts": summaries,
              "retained_files": retained, "bounds": {"max_files": MAX_FILES, "max_total_bytes": MAX_TOTAL, "max_file_bytes": MAX_FILE},
              "scope": "Historical failed whole-operation records and retained partial cases; no new result, authority or success qualification"}
    raw = canonical(report)
    need(len(raw) <= MAX_REPORT, "report allocation bound")
    report_path = output / REPORT_NAME
    report_path.write_bytes(raw)
    cap.take(report_path, cap=MAX_REPORT)
    expected = {row["relative_path"] for row in retained} | {REPORT_NAME}
    final_fence(cap, output, expected)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = audit(args.manifest, args.output)
    except (Refusal, OSError, UnicodeError, json.JSONDecodeError, RecursionError, KeyError, TypeError, OverflowError) as exc:
        parser.exit(2, "receiving refused: " + str(exc) + "\n")
    print(json.dumps({k: report[k] for k in ("status", "attempt_count", "failed_whole_attempt_count", "recorded_native_phase_count")}))


if __name__ == "__main__":
    main()
