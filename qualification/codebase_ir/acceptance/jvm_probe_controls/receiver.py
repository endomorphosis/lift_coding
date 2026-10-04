"""Receive recorded JVM identity-probe custody without running Java or owners.

This closed historical profile checks support observations, not model checking,
proofs, present resource enforcement, toolchain authenticity or current authority.
"""
from __future__ import annotations

import argparse
import ast
import copy
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from inventory_query_controls import native_receiver as codec

INPUT_SCHEMA = "codebase-ir-jvm-probe-custody-input@1"
REPORT_SCHEMA = "codebase-ir-jvm-probe-custody-report@1"
QUALIFICATION_SHA = "8c274ef09bf40f173955bd8005c26de8a610a85a773b541a709006e324489838"
NATIVE_RESULT_SHA = "ddeb99132e4108f541f61c2dc1127463d19ca27f3f288b21719f11539e8d5837"
MAX_FILE, MAX_TOTAL, MAX_FILES, MAX_PHASES, MAX_CASES = 512 * 1024, 4 * 1024 * 1024, 12, 64, 40
ROLES = {"prior_qualification": "qualification.json", "native_result": "native-selected/result.json",
         "native_command": "native-selected/command.json", "launch_audit": "native-selected/launch-audit.json",
         "lifecycle_audit": "native-selected/lifecycle-audit.json", "control_audit": "native-selected/control-audit.json",
         "wire_before": "java-wire-before.json", "wire_after": "java-wire-after.json", "wire_comparison": "java-wire-comparison.json",
         "runtime_before": "prior-runtime-source/state_model.py", "runtime_after": "runtime-source-after/state_model.py"}
ROUTES = ("direct_banner", "runtime_probe", "tlc_constructor", "apalache_constructor", "registry_tlc")
CONTROLS = ("control:pre-cancel:direct_banner", "control:pre-cancel:runtime_probe",
            "control:live-cancel:local_probe", "control:live-cancel:ambient_operation")
WIRE_FIELDS = ("executable", "source", "minimum_major", "banner", "major", "usable", "reason_code")
JVM_FLAGS = ("-Xms16m", "-Xmx128m", "-Xss1m", "-XX:+UseSerialGC", "-XX:ActiveProcessorCount=1",
             "-XX:MaxMetaspaceSize=128m", "-XX:ReservedCodeCacheSize=64m", "-XX:-UsePerfData", "-version")
TRUE_FLAGS = ("jvm_probe_structural_custody_conformance", "recorded_probe_phase_bindings_reconciled",
              "wire_fixture_compatibility_reconciled", "frozen_wire_definitions_unchanged", "input_files_unchanged")
FALSE_FLAGS = ("native_execution_performed", "training_executed", "current_authority_claimed", "owner_database_opened",
    "profile_keys_read", "signature_authentication_performed", "numerical_state_replayed", "source_execution_replayed",
    "checker_executions_replayed", "live_eligibility_qualified", "production_acceptance_qualified",
    "runtime_resource_enforcement_verified", "raw_phase_stdin_custody_verified", "raw_caller_request_custody_verified",
    "unique_phase_execution_attestation_verified", "behavioral_evidence_admission_qualified", "proof_certificate_verified",
    "model_checker_execution_qualified", "jvm_binary_identity_authenticated", "launcher_body_custody_verified",
    "parent_constructor_propagation_qualified", "throughput_improvement_qualified", "native_deadline_expiry_observed",
    "native_pressure_backoff_observed")
PHASE_REQUEST_FIELDS = {"argv", "input_file_count", "java_option_environment_absent", "max_output_bytes", "memory_bytes",
                        "output_path_count", "resident_memory_bytes", "stdin_is_empty", "timeout_seconds"}
PHASE_RESULT_FIELDS = {"cancelled", "command", "elapsed_seconds", "error", "interface_version", "output_files", "output_truncated",
    "pid", "process_tree_terminated", "resource_exhausted", "returncode", "runtime", "stderr", "stdout", "termination_reason",
    "timed_out", "unavailable", "workspace_cleaned", "workspace_limit_exceeded"}
LEASE_FIELDS = {"acquired_at", "cancelled", "child_process_slots", "cpu_slots", "expires_at", "gpu_memory_mb", "heartbeat_at", "lane",
    "lease_id", "lease_key", "memory_mb", "owner_birth_marker", "owner_boot_id", "owner_pid", "parent_lease_id", "request_id",
    "requires_gpu", "sequence", "unified_memory_mb", "wait_seconds"}


def integer(value, minimum=0, maximum=2**63 - 1):
    codec.require(type(value) is int and minimum <= value <= maximum, "exact bounded JVM integer")
    return value


def number(value, maximum=2**53):
    codec.require(type(value) in (int, float) and 0 <= value <= maximum and math.isfinite(value), "finite recorded JVM number")
    return value


def digest(value):
    codec.require(type(value) is str and re.fullmatch("[0-9a-f]{64}", value) is not None, "recorded JVM SHA256")
    return value


def rows(value, maximum):
    codec.require(type(value) is list and len(value) <= maximum, "bounded JVM population")
    return value


def document(raw, limit=MAX_FILE):
    codec.require(type(raw) is bytes and len(raw) <= limit, "JVM JSON byte bound")
    if raw.lstrip().startswith(b"["):
        return codec.document(b'{"items":' + raw + b'}', limit + 10)["items"]
    return codec.document(raw, limit)


def raw_document_hash(value):
    return codec.sha((json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode())


class Capture:
    def __init__(self):
        self.raw, self.total = {}, 0

    def take(self, path, pin=None, limit=MAX_FILE):
        codec.require(path not in self.raw and len(self.raw) < MAX_FILES, "JVM input identity/file bound")
        allowance = min(limit, MAX_TOTAL - self.total, pin["bytes"] if pin else limit)
        raw = codec.OriginalCapture.read(path, allowance)
        if pin:
            codec.require(len(raw) == pin["bytes"] and codec.sha(raw) == pin["sha256"], "JVM selected raw pin")
        self.raw[path], self.total = raw, self.total + len(raw)
        return raw

    def stable(self):
        for path, raw in self.raw.items():
            codec.require(codec.OriginalCapture.read(path, len(raw)) == raw, "private frozen JVM input drift")


def wire_value(value, usable=True):
    codec.closed(value, set(WIRE_FIELDS), "seven-field JVM wire record")
    integer(value["minimum_major"], 1, 1000)
    codec.require(type(value["source"]) is str and value["usable"] is usable, "typed JVM usability/source")
    if usable:
        integer(value["major"], value["minimum_major"], 1000)
        codec.require(type(value["executable"]) is str and type(value["banner"]) is str and value["reason_code"] is None,
                      "successful JVM wire identity")
    else:
        codec.require(value["executable"] is value["banner"] is value["major"] is None
                      and value["reason_code"] == "java_probe_failed", "unusable JVM wire withholds identity")


def wire_compatibility(documents, sources):
    classes = []
    for source in sources:
        tree = ast.parse(source.decode("utf-8"))
        matches = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "JavaRuntimeProbe"]
        codec.require(len(matches) == 1, "exact one inert JavaRuntimeProbe definition")
        classes.append(matches[0])
    codec.require(ast.dump(classes[0], include_attributes=False) == ast.dump(classes[1], include_attributes=False),
                  "frozen JavaRuntimeProbe AST definition")
    fields = [node.target.id for node in classes[0].body if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)]
    codec.require(fields == list(WIRE_FIELDS), "original ordered seven-field JavaRuntimeProbe codec")
    before, after, comparison = (documents[role] for role in ("wire_before", "wire_after", "wire_comparison"))
    for value, source in ((before, sources[0]), (after, sources[1])):
        codec.closed(value, {"source_sha256", "observation", "runtime"}, "independent deterministic JVM wire fixture")
        codec.require(value["source_sha256"] == codec.sha(source)
                      and value["observation"] == "Explicit version/read-path fixtures; no native process or scheduler", "wire source/origin")
        wire_value(value["runtime"])
    codec.closed(comparison, {"before_source_sha256", "after_source_sha256", "exact_runtime_wire_equal"}, "JVM wire comparison")
    codec.require(codec.equal(before["runtime"], after["runtime"]) and comparison["exact_runtime_wire_equal"] is True
                  and comparison["before_source_sha256"] == codec.sha(sources[0])
                  and comparison["after_source_sha256"] == codec.sha(sources[1]), "independent original JVM wire compatibility")
    return {"fixture_origin": "separate_deterministic_non_native_wire_observation", "runtime": before["runtime"],
            "wire_fields": fields, "definition_ast_sha256": codec.sha(ast.dump(classes[0], include_attributes=False).encode()),
            "native_probe_identity_inferred_from_wire_fixture": False}


def shared_snapshot(value, configuration):
    codec.closed(value, {"active_leases", "config", "next_sequence", "owned_active_leases", "owned_waiting_requests",
                         "schema_version", "waiting_requests"}, "recorded JVM shared snapshot")
    codec.require(value["schema_version"] == "legal-ir-global-resource-scheduler-v1"
                  and codec.equal(value["config"], configuration), "recorded unchanged shared configuration")
    for key in ("active_leases", "owned_active_leases", "owned_waiting_requests", "waiting_requests"):
        codec.require(integer(value[key]) == 0, "recorded owned JVM work drained")
    integer(value["next_sequence"], 1)


def lease_binding(launch, nested, runtime):
    codec.closed(launch, {"argv", "at_monotonic", "case", "launch_lease_id", "owned_leases", "root_allocations", "thread", "waiting"}, "JVM launch")
    number(launch["at_monotonic"])
    integer(launch["thread"], 1)
    integer(launch["waiting"])
    leases = rows(launch["owned_leases"], 8)
    ids = [lease["lease_id"] for lease in leases]
    codec.require(len(ids) == len(set(ids)) and ids.count(launch["launch_lease_id"]) == 1, "unique actual launch lease binding")
    by_id = {lease["lease_id"]: lease for lease in leases}
    for lease in leases:
        codec.closed(lease, LEASE_FIELDS, "recorded JVM lease")
        codec.require(type(lease["lease_id"]) is str and len(lease["lease_id"]) == 32
                      and lease["cancelled"] is False and lease["requires_gpu"] is False and lease["lane"] == "validation"
                      and lease["owner_pid"] == runtime["pid"] and type(lease["owner_pid"]) is int
                      and lease["owner_boot_id"] == runtime["boot_id"] and type(lease["owner_birth_marker"]) is str,
                      "recorded lease owner/availability identity")
        for key in ("cpu_slots", "child_process_slots", "memory_mb", "sequence"):
            integer(lease[key], 1)
        for key in ("gpu_memory_mb", "unified_memory_mb"):
            codec.require(integer(lease[key]) == 0, "support JVM lease has no device budget")
        for key in ("acquired_at", "expires_at", "heartbeat_at", "wait_seconds"):
            number(lease[key])
        codec.require(lease["acquired_at"] <= lease["heartbeat_at"] < lease["expires_at"], "recorded lease lifetime")
        if lease["parent_lease_id"] is not None:
            codec.require(lease["parent_lease_id"] in by_id and by_id[lease["parent_lease_id"]]["parent_lease_id"] is None,
                          "recorded child has actual captured root")
    selected = by_id[launch["launch_lease_id"]]
    codec.require(selected["cpu_slots"] == selected["child_process_slots"] == 1 and selected["memory_mb"] == 256
                  and selected["request_id"] == "native-prover:jvm", "declared one-probe resource reservation")
    roots = [lease for lease in leases if lease["parent_lease_id"] is None]
    allocation = {key: sum(lease[key] for lease in roots) for key in ("cpu_slots", "child_process_slots", "memory_mb")}
    codec.require(codec.equal(allocation, launch["root_allocations"]) and allocation["cpu_slots"] <= 4
                  and allocation["child_process_slots"] <= 4 and allocation["memory_mb"] <= 1024, "recorded roots counted once")
    if nested:
        parent = by_id.get(selected["parent_lease_id"])
        codec.require(parent is not None and len(roots) == 1 and parent["cpu_slots"] == parent["child_process_slots"] == 2
                      and parent["memory_mb"] == 512, "actual parent-owned two-probe allocation")
        children = [lease for lease in leases if lease["parent_lease_id"] == parent["lease_id"]]
        codec.require(len(children) == 2 and all(sum(lease[key] for lease in children) <= parent[key]
                      for key in ("cpu_slots", "child_process_slots", "memory_mb")), "nested capacity within one parent")
    else:
        codec.require(selected["parent_lease_id"] is None and len(roots) == len(leases), "ordinary probe retains root ownership")
    return {"launch_lease_id_claim": selected["lease_id"], "parent_lease_id_claim": selected["parent_lease_id"],
            "recorded_root_allocations": allocation, "lease_execution_authenticated": False}


def successful_case(value, expected_name, route, lifecycle, executable):
    codec.closed(value, {"banner_sha256", "case", "elapsed_seconds", "observed_major", "outcome", "phase_count", "route", "support_only"}, "JVM successful case")
    codec.require(value["case"] == expected_name and value["route"] == route and value["support_only"] is True
                  and integer(value["phase_count"]) == 1, "ordered complete support-only original case")
    number(value["elapsed_seconds"])
    result = lifecycle["result"]
    banner = result["stderr"].strip()
    match = re.match(r'(?:openjdk|java) version "(\d+)\.', banner)
    codec.require(match is not None and value["observed_major"] == int(match[1]) == 17
                  and type(value["observed_major"]) is int and value["banner_sha256"] == codec.sha(banner.encode()), "native output banner/major binding")
    outcome = value["outcome"]
    if route == "direct_banner":
        codec.closed(outcome, {"banner", "major", "returncode"}, "direct banner outcome")
        codec.require(type(outcome["returncode"]) is int and outcome["returncode"] == 0
                      and outcome["banner"] == banner and type(outcome["major"]) is int and outcome["major"] == 17, "direct native identity")
    elif route == "runtime_probe":
        wire_value(outcome)
        codec.require(outcome["banner"] == banner and outcome["major"] == 17 and outcome["minimum_major"] == 17
                      and outcome["executable"] == executable and outcome["source"] == "argument", "native runtime probe wire correspondence")
    else:
        codec.closed(outcome, {"backend_id", "checker_availability", "jvm_usable", "model_checker_executed", "selected_java"}, "constructor support outcome")
        codec.require(outcome["backend_id"] == ("apalache" if route == "apalache_constructor" else "tlc")
                      and outcome["selected_java"] == executable and outcome["jvm_usable"] is True
                      and outcome["model_checker_executed"] is False
                      and outcome["checker_availability"] is (True if route == "registry_tlc" else None), "constructor usability grants no model check")
    return {"case": expected_name, "route": route, "recorded_banner_sha256": value["banner_sha256"], "recorded_major": 17,
            "support_only": True, "model_checker_executed": False}


def phase_binding(launch, life, executable, runtime, stopped=False):
    codec.closed(life, {"case", "request", "result", "shared_backoff_after"}, "JVM lifecycle")
    request, result = life["request"], life["result"]
    codec.closed(request, PHASE_REQUEST_FIELDS, "JVM lifecycle request")
    codec.closed(result, PHASE_RESULT_FIELDS, "JVM lifecycle result")
    argv = [executable, *JVM_FLAGS]
    timeout = number(request["timeout_seconds"], 5 if life["case"] == CONTROLS[3] else 10)
    codec.require(timeout > 0 and codec.equal(request["argv"], argv) and codec.equal(result["command"], argv), "original finite JVM command/deadline")
    wrapper = ["/usr/bin/prlimit", "--core=0:0", "--fsize=1048576:1048576",
               f"--cpu={math.ceil(timeout)}:{math.ceil(timeout)}", "--as=4294967296:4294967296", "--", *argv]
    codec.require(codec.equal(launch["argv"], wrapper), "native launch wrapper joins command and limits")
    for key, expected in (("input_file_count", 0), ("output_path_count", 0), ("max_output_bytes", 65536),
                          ("memory_bytes", 4294967296), ("resident_memory_bytes", 268435456)):
        codec.require(integer(request[key]) == expected, "declared support probe bytes/file/resource bounds")
    codec.require(request["stdin_is_empty"] is True and request["java_option_environment_absent"] is True,
                  "recorded empty input and sanitized Java options")
    for key in ("cancelled", "output_truncated", "process_tree_terminated", "resource_exhausted", "timed_out", "unavailable",
                "workspace_cleaned", "workspace_limit_exceeded"):
        codec.require(type(result[key]) is bool, "exact native lifecycle Boolean")
    codec.require(result["runtime"] == "jvm" and result["interface_version"] == "bounded-tool-runner/v1"
                  and result["workspace_cleaned"] is True and result["output_files"] == {} and result["error"] == ""
                  and result["output_truncated"] is result["resource_exhausted"] is result["timed_out"] is result["unavailable"] is result["workspace_limit_exceeded"] is False,
                  "clean native lifecycle gate")
    integer(result["pid"], 1)
    integer(result["returncode"], -255, 255)
    number(result["elapsed_seconds"], 60)
    codec.require(type(result["stdout"]) is str and type(result["stderr"]) is str
                  and len(result["stdout"].encode()) + len(result["stderr"].encode()) <= request["max_output_bytes"], "bounded recorded native output")
    codec.require(result["cancelled"] is stopped and result["process_tree_terminated"] is stopped
                  and result["returncode"] == (-15 if stopped else 0)
                  and result["termination_reason"] == ("cancelled" if stopped else "completed")
                  and result["stdout"] == "" and (not stopped or result["stderr"] == "")
                  and life["shared_backoff_after"] == {}, "support success versus stopped phase disposition")
    lease = lease_binding(launch, life["case"].startswith("nested:"), runtime)
    return {"case": life["case"], "request_command_sha256": codec.sha(codec.wire(argv)),
            "recorded_stdout_sha256": codec.sha(result["stdout"].encode()), "recorded_stderr_sha256": codec.sha(result["stderr"].encode()),
            "declared_timeout_seconds": timeout, "recorded_returncode": result["returncode"], "recorded_stop": stopped,
            "recorded_workspace_cleaned": True, "resource_execution_authenticated": False, **lease}


def receive(documents, sources):
    q, native = documents["prior_qualification"], documents["native_result"]
    codec.require(q["schema"] == "jvm-probe-admission-qualification@1" and q["status"] == "passed_partial_scope"
                  and q["production_tasks_closed"] == [] and native["schema"] == "java-probe-admission-benchmark@1"
                  and native["status"] == "passed" and all(value is True for value in native["checks"].values())
                  and codec.equal(native["checks"], q["native_checks"]), "complete historical support-only qualification checks")
    codec.require(native["scope"] == "Installed JVM identity and support usability only; no model checking, proving, or installation",
                  "historical support observations have no proof scope")
    codec.require(len(native["source_pins_before"]) == 38 and codec.equal(native["source_pins_before"], native["source_pins_after"]), "recorded exact source generation")
    for value in native["source_pins_before"].values():
        digest(value)
    model_path = next(key for key in native["source_pins_before"] if key.endswith("/installers/state_model.py"))
    codec.require(native["source_pins_before"][model_path] == codec.sha(sources[1]), "captured inert runtime source generation")
    configuration = native["shared_before"]["config"]
    codec.require(codec.equal(configuration, q["native_pool_configuration"]) and configuration["total_cpu_slots"] == 4
                  and configuration["total_child_process_slots"] == 4 and configuration["total_memory_mb"] == 9830,
                  "unchanged finite historical pool envelope")
    shared_snapshot(native["shared_before"], configuration)
    shared_snapshot(native["shared_after"], configuration)
    codec.require(codec.equal(native["shared_pool_compatibility"], q["shared_pool_compatibility"])
                  and native["shared_pool_compatibility"]["mode"] == "native_config", "separate benchmark configuration compatibility")
    command = documents["native_command"]
    codec.closed(command, {"argv", "cwd", "environment"}, "original benchmark invocation")
    codec.require(command["argv"] == ["benchmarks/bench_java_probe_admission.py", "--output", "workspace/jvm-probe-admission-qualification-20261003/native-selected"]
                  and command["cwd"].endswith("/external/ipfs_datasets")
                  and command["environment"]["IPFS_TEST_PROOF_REUSE_MODE"] == "off"
                  and command["environment"]["IPFS_DATASETS_AUTO_INSTALL_TEST_DEPS"] == "0", "fixed selected benchmark request")
    launches, lifecycles = (rows(documents[role], MAX_PHASES) for role in ("launch_audit", "lifecycle_audit"))
    codec.require(len(launches) == len(lifecycles) == 34, "all34 recorded probe phases")
    launch_map, life_map = ({value["case"]: value for value in values} for values in (launches, lifecycles))
    codec.require(len(launch_map) == len(life_map) == 34 and set(launch_map) == set(life_map), "unique case-local launch/lifecycle membership")
    codec.require(len({value["launch_lease_id"] for value in launches}) == 34, "unique selected launch lease population")
    for role in ("launch_audit", "lifecycle_audit", "control_audit"):
        codec.require(native[ROLES[role].split("/")[-1] + "_sha256"] == raw_document_hash(documents[role]), "recorded independent audit raw join")
    executable = native["executable"]["path"]
    codec.require(type(executable) is str and native["executable"]["resolved_path"] == executable, "recorded launcher label")
    digest(native["executable"]["sha256"])
    wire = wire_compatibility(documents, sources)
    cases, names = [], []
    runs = rows(native["runs"], 6)
    codec.require([(integer(v["workers"]), integer(v["repeat"])) for v in runs] == [(w, r) for w in (1, 2, 4) for r in (0, 1)], "original ordered width/repeat matrix")
    for run in runs:
        codec.closed(run, {"cases", "elapsed_seconds", "repeat", "workers"}, "probe cohort")
        number(run["elapsed_seconds"])
        values = rows(run["cases"], 5)
        codec.require(len(values) == 5, "complete five-route cohort")
        for route, value in zip(ROUTES, values, strict=True):
            name = f"parallel:{run['workers']}:{run['repeat']}:{route}"
            names.append(name)
            cases.append(successful_case(value, name, route, life_map[name], executable))
    nested = rows(native["nested_cases"], 2)
    codec.require(len(nested) == 2, "two original actual-parent probes")
    for route, value in zip(ROUTES[:2], nested, strict=True):
        name = "nested:" + route
        names.append(name)
        cases.append(successful_case(value, name, route, life_map[name], executable))
    codec.require(len({value["recorded_banner_sha256"] for value in cases}) == 1, "all32 support probes share output identity")
    controls = rows(native["controls"], 4)
    codec.require([value["case"] for value in controls] == list(CONTROLS), "complete original four stop controls")
    audit = documents["control_audit"]
    codec.closed(audit, {"native_environments", "triggers"}, "independent JVM environment/stop observations")
    environments, triggers = rows(audit["native_environments"], MAX_PHASES), rows(audit["triggers"], 2)
    codec.require(len(environments) == 34 and len({value["case"] for value in environments}) == 34
                  and {value["case"] for value in environments} == set(launch_map), "complete independent environment observations")
    for env in environments:
        codec.closed(env, {"case", "java_option_environment_absent", "launch_lease_id", "thread"}, "sanitized environment record")
        launch = launch_map[env["case"]]
        codec.require(env["java_option_environment_absent"] is True and env["launch_lease_id"] == launch["launch_lease_id"]
                      and env["thread"] == launch["thread"] and type(env["thread"]) is int, "case/thread/lease environment join")
    codec.require(len(triggers) == 2 and [value["case"] for value in triggers] == list(CONTROLS[2:]), "exact two native live stop boundaries")
    stops = []
    for index, value in enumerate(controls):
        name, live = value["case"], index >= 2
        number(value["elapsed_seconds"])
        codec.require(integer(value["phase_count"]) == integer(value["launch_count"]) == int(live), "stopped support population")
        shared_snapshot(value["shared_after"], configuration)
        if not live:
            codec.require(integer(value["lifecycle_count"]) == 0 and name not in launch_map, "pre-cancel has no launch/lifecycle")
        else:
            names.append(name)
            trigger = triggers[index - 2]
            codec.require(codec.equal(value["trigger"], trigger) and trigger["boundary"] == "immediately_after_actual_probe_popen"
                          and trigger["observed_live"] is True and trigger["pid"] == life_map[name]["result"]["pid"]
                          and type(trigger["pid"]) is int and number(trigger["at_monotonic"]) >= launch_map[name]["at_monotonic"]
                          and value["no_followup_launch"] is True and value["ambient_operation"] is (index == 3), "independent recorded live stop boundary")
        if index in (0, 2):
            codec.require(value["outcome"] == [None, None], "local cancellation withholds banner and identity")
        elif index == 1:
            wire_value(value["outcome"], usable=False)
        else:
            codec.require(value["returned_result"] is False and value["exception_type"] == "ProofOperationCancelled"
                          and value["exception"]["kind"] == "cancelled" and value["exception"]["phase"] == "native execution"
                          and integer(value["exception"]["timeout_ms"]) == 5000
                          and 0 <= integer(value["exception"]["elapsed_ms"]) < 5000, "ambient typed cancellation withholds result")
        stops.append({"case": name, "recorded_stop_kind": "cancelled", "recorded_native_phase_count": int(live),
                      "recorded_outcome": "typed_ambient_interruption" if index == 3 else "unusable_identity",
                      "returned_usable_identity": False, "current_stop_execution_verified": False})
    codec.require(set(names) == set(launch_map) and len(names) == 34, "no unselected/missing support phase")
    phases = [phase_binding(launch_map[name], life_map[name], executable, native["runtime"], name in CONTROLS[2:]) for name in names]
    parents = {value["parent_lease_id_claim"] for value in phases if value["parent_lease_id_claim"] is not None}
    codec.require(len(parents) == 1 and sum(value["parent_lease_id_claim"] is not None for value in phases) == 2,
                  "two actual child probes share one parent reservation")
    peak = {key: max(value["recorded_root_allocations"][key] for value in phases) for key in ("cpu_slots", "child_process_slots", "memory_mb")}
    codec.require(codec.equal(peak, q["peak_observed_root_reservations"]), "independent recorded root peak")
    for key, expected in (("native_cases", 30), ("native_nested_cases", 2), ("native_launches", 34), ("native_lifecycles", 34), ("all_lifecycles", 34)):
        codec.require(integer(q[key]) == expected, "independent qualification typed population")
    for key in ("launches", "lifecycles", "native_lifecycles"):
        codec.require(integer(native[key]) == 34, "recorded native typed phase total")
    codec.require(integer(native["prelaunch_lifecycles"]) == 0 and codec.equal(q["native_stop_controls"], controls), "independent original stop ledger")
    return {"successful_probes": cases, "stopped_calls": stops, "phase_receipts": phases, "wire_fixture": wire,
            "recorded_peak_root_allocations": peak, "phase_join_scope": "unique case and selected lease labels; no shared authenticated invocation ID"}


def load_input(manifest):
    capture = Capture()
    spec = codec.document(capture.take(manifest, limit=codec.MAX_MANIFEST), codec.MAX_MANIFEST)
    codec.closed(spec, {"schema", *ROLES}, "JVM input manifest")
    codec.require(spec["schema"] == INPUT_SCHEMA, "JVM input schema")
    for role in ROLES:
        codec.descriptor(spec[role], original=role != "prior_qualification")
    codec.require(spec["prior_qualification"]["sha256"] == QUALIFICATION_SHA and spec["prior_qualification"]["bytes"] == 149557
                  and spec["native_result"]["sha256"] == NATIVE_RESULT_SHA, "fixed independent JVM qualification/native anchors")
    namespace = Path(spec["native_result"]["original_path"]).parent.parent
    documents, sources = {}, []
    for role, relative in ROLES.items():
        descriptor = spec[role]
        raw = capture.take(codec.canonical_path(descriptor["path"]), descriptor)
        if role != "prior_qualification":
            codec.require(descriptor["original_path"] == str(namespace / relative)
                          and documents["prior_qualification"]["artifact_sha256"].get(relative) == descriptor["sha256"], "independent public JVM role/raw commitment")
        if role.startswith("runtime_"):
            sources.append(raw)
        else:
            documents[role] = document(raw)
    return capture, spec, documents, sources


def mutation_controls(documents, sources):
    result = []

    def run(name, mutate):
        changed = copy.deepcopy(documents)
        mutate(changed)
        for role in ("launch_audit", "lifecycle_audit", "control_audit"):
            changed["native_result"][ROLES[role].split("/")[-1] + "_sha256"] = raw_document_hash(changed[role])
        try:
            receive(changed, sources)
        except (codec.ReceiverRefusal, KeyError, TypeError, ValueError, StopIteration):
            result.append({"name": name, "mutable_audit_digests_recomputed": True, "independent_anchors_preserved": True, "rejected": True})
            return
        raise codec.ReceiverRefusal("JVM mutation control accepted: " + name)

    def first(packet):
        return packet["native_result"]["runs"][0]["cases"][0]

    run("complete_route_order_changed", lambda p: p["native_result"]["runs"][0]["cases"].reverse())
    run("complete_route_omitted", lambda p: p["native_result"]["runs"][0]["cases"].pop())
    run("cohort_width_boolean_alias", lambda p: p["native_result"]["runs"][0].update(workers=True))
    run("support_promoted_to_model_check", lambda p: p["native_result"]["runs"][0]["cases"][2]["outcome"].update(model_checker_executed=True))
    run("case_banner_digest_substituted", lambda p: first(p).update(banner_sha256="0" * 64))
    run("observed_major_boolean_alias", lambda p: first(p).update(observed_major=True))
    run("direct_returncode_boolean_alias", lambda p: first(p)["outcome"].update(returncode=False))
    run("runtime_probe_usable_integer_alias", lambda p: p["native_result"]["runs"][0]["cases"][1]["outcome"].update(usable=1))
    run("whole_operation_failed", lambda p: p["native_result"].update(status="failed"))
    run("late_source_check_failed", lambda p: p["native_result"]["checks"].update(sources_stable=False))
    run("source_generation_drift", lambda p: p["native_result"]["source_pins_after"].update({next(iter(p["native_result"]["source_pins_after"])): "0" * 64}))
    run("original_wire_runtime_changed", lambda p: p["wire_after"]["runtime"].update(minimum_major=12))
    run("original_wire_boolean_alias", lambda p: p["wire_after"]["runtime"].update(usable=1))
    run("benchmark_invocation_widened", lambda p: p["native_command"]["argv"].append("--unbounded"))
    run("lifecycle_omitted", lambda p: p["lifecycle_audit"].pop())
    run("launch_duplicated", lambda p: p["launch_audit"].append(copy.deepcopy(p["launch_audit"][0])))
    run("phase_case_substituted", lambda p: p["lifecycle_audit"][0].update(case="unknown:case"))
    run("phase_returncode_boolean_alias", lambda p: p["lifecycle_audit"][0]["result"].update(returncode=False))
    run("phase_cleanup_integer_alias", lambda p: p["lifecycle_audit"][0]["result"].update(workspace_cleaned=1))
    run("phase_usable_after_cancel", lambda p: p["lifecycle_audit"][0]["result"].update(cancelled=True))
    run("phase_deadline_widened", lambda p: p["lifecycle_audit"][0]["request"].update(timeout_seconds=20.0))
    run("phase_input_not_empty", lambda p: p["lifecycle_audit"][0]["request"].update(stdin_is_empty=False))
    run("phase_output_budget_widened", lambda p: p["lifecycle_audit"][0]["request"].update(max_output_bytes=131072))
    run("phase_jvm_flags_changed", lambda p: p["lifecycle_audit"][0]["request"]["argv"].__setitem__(2, "-Xmx256m"))
    run("phase_as_limit_widened", lambda p: p["launch_audit"][0]["argv"].__setitem__(4, "--as=8589934592:8589934592"))
    run("phase_environment_not_sanitized", lambda p: p["control_audit"]["native_environments"][0].update(java_option_environment_absent=False))
    run("environment_lease_substituted", lambda p: p["control_audit"]["native_environments"][0].update(launch_lease_id="0" * 32))
    run("launch_lease_missing", lambda p: p["launch_audit"][0].update(launch_lease_id="0" * 32))
    run("root_double_counts_child", lambda p: next(v for v in p["launch_audit"] if v["case"].startswith("nested:")).update(root_allocations={"cpu_slots": 4, "child_process_slots": 4, "memory_mb": 1024}))
    run("parent_capacity_widened", lambda p: next(v for v in next(v for v in p["launch_audit"] if v["case"].startswith("nested:"))["owned_leases"] if v["parent_lease_id"] is None).update(memory_mb=768))
    run("local_stop_returns_usable", lambda p: p["native_result"]["controls"][2].update(outcome=[17, "late success"]))
    run("ambient_stop_returns_result", lambda p: p["native_result"]["controls"][3].update(returned_result=True))
    run("ambient_stop_kind_swapped", lambda p: p["native_result"]["controls"][3]["exception"].update(kind="timeout"))
    run("pre_cancel_launch_count_added", lambda p: p["native_result"]["controls"][0].update(launch_count=1))
    run("stop_independent_pid_changed", lambda p: p["native_result"]["controls"][2]["trigger"].update(pid=1))
    run("stop_cleanup_missing", lambda p: p["lifecycle_audit"][-1]["result"].update(process_tree_terminated=False))
    run("final_owned_work_not_drained", lambda p: p["native_result"]["shared_after"].update(owned_active_leases=1))
    return result


def audit(manifest, output):
    manifest, output = codec.canonical_path(str(manifest)), codec.canonical_path(str(output))
    capture, spec, documents, sources = load_input(manifest)
    protected = {path.parent for path in capture.raw if path != manifest}
    protected.update(codec.canonical_path(spec[role]["original_path"]).parent for role in ROLES if role != "prior_qualification")
    resolved = output.resolve()
    codec.require(not output.exists() and not output.is_symlink()
                  and all(resolved != path.resolve() and path.resolve() not in resolved.parents for path in protected),
                  "fresh output outside frozen/original JVM input scopes")
    received, negative = receive(documents, sources), mutation_controls(documents, sources)
    capture.stable()
    output.mkdir(parents=True, exist_ok=False)
    (output / "inputs").mkdir()
    retained = []
    for index, (path, raw) in enumerate(capture.raw.items()):
        destination = output / "inputs" / f"{index:02d}-{path.name}"
        destination.write_bytes(raw)
        codec.require(codec.OriginalCapture.read(destination, len(raw)) == raw, "JVM retained raw copy")
        retained.append({"path": str(path), "retained_path": str(destination), "sha256": codec.sha(raw), "bytes": len(raw)})
    capture.stable()
    for row in retained:
        codec.require(codec.sha(codec.OriginalCapture.read(Path(row["retained_path"]), row["bytes"])) == row["sha256"], "JVM retained copy drift")
    native = documents["native_result"]
    report = {"schema": REPORT_SCHEMA, "status": "passed", "scope": "selected_historical_jvm_support_probe_custody_only",
        "historical_qualification_status": documents["prior_qualification"]["status"], "count_scope": "recorded_historical_observations_only",
        "input_origin": "retained_native_support_probe_records_with_separate_deterministic_wire_fixture",
        "manifest_sha256": codec.sha(capture.raw[manifest]), **{role + "_sha256": spec[role]["sha256"] for role in ROLES},
        **dict.fromkeys(TRUE_FLAGS, True), **dict.fromkeys(FALSE_FLAGS, False), "runtime_fact_count": 0, "tasks_omitted_count": 0,
        "additional_attempted_training_epochs": 0, "baseline_case_count": 30, "nested_case_count": 2, "successful_probe_count": 32,
        "interruption_control_count": 4, "prelaunch_stop_count": 2, "live_stop_count": 2, "native_launch_count": 34, "native_lifecycle_count": 34,
        "root_probe_phase_count": 32, "parent_owned_probe_phase_count": 2, "wire_fixture_case_count": 1, "wire_field_count": 7,
        "unchanged_wire_definition_count": 1, "input_file_count": len(retained), "input_bytes": capture.total, "mutation_control_count": len(negative),
        "limits": {"max_files": MAX_FILES, "max_file_bytes": MAX_FILE, "max_total_bytes": MAX_TOTAL, "max_manifest_bytes": codec.MAX_MANIFEST,
                   "max_phases": MAX_PHASES, "max_cases": MAX_CASES}, "input_files": retained, "received": received, "mutation_controls": negative,
        "recorded_producer_effort": {"scope": "historical_recorded_claims_only", "elapsed_seconds": native["elapsed_seconds"],
            "cohorts": [{key: value[key] for key in ("workers", "repeat", "elapsed_seconds")} for value in native["runs"]],
            "child_usage": native["child_usage"], "memory_observation_scope": native["memory_observation_scope"]},
        "limitations": ["Support probes and constructor usability are not model checks, proofs, source semantics or execution grants.",
            "Unsigned fixed qualification/native anchors preserve historical selected scope, not authentic execution or present authority.",
            "Selected launcher digest has no retained launcher body; delegated JVM binary and full support tree are unavailable and never opened.",
            "Empty stdin and sanitized Java options are recorded flags, not independent original caller/stdin/environment custody.",
            "Launch/lifecycle joins use unique case and selected lease labels without a shared authenticated invocation identifier; cleanup and lease release order remain producer observations.",
            "Local unusable and ambient typed cancellation remain distinct. The native run has no real-time expiry or manufactured pressure/backoff control.",
            "Recorded root/child budgets and sampled RSS establish no hard aggregate containment, resource enforcement, throughput improvement or current scheduler ownership.",
            "Constructor parent propagation to later proof work, Apalache execution, installer probes and supervisor admission remain separate gaps.",
            "Historical source/executable/cwd/path strings are labels; only privately frozen selected bodies and their copies are read. JavaRuntimeProbe sources are inert AST input."]}
    (output / "jvm_probe_custody.json").write_bytes(codec.wire(report) + b"\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = audit(args.manifest, args.output)
    except (codec.ReceiverRefusal, OSError, ValueError, TypeError, KeyError, StopIteration, RecursionError, SyntaxError) as error:
        print(json.dumps({"status": "refused", "reason": str(error)}), file=sys.stderr)
        return 1
    print(json.dumps({"status": "passed", "phases": report["native_lifecycle_count"], "probes": report["successful_probe_count"], "controls": report["mutation_control_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
