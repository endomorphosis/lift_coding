"""Receive frozen Apalache admission records without executing captured programs."""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import math
import os
import re
import shlex
import stat
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

INPUT_SCHEMA = "codebase-ir-apalache-admission-controls-input@1"
REPORT_SCHEMA = "codebase-ir-apalache-admission-controls@1"
REPORT_NAME = "apalache_admission_controls.json"
IDS = ("capacity_failed", "resource_failed", "accepted_smoke", "accepted_full")
DIRECTORIES = dict(
    zip(
        IDS,
        ("native-selected", "native-qualified", "native-final-smoke", "native-accepted"),
        strict=True,
    )
)
ROLES = (
    "result",
    "command_result",
    "request_audit",
    "launch_audit",
    "lifecycle_audit",
    "control_audit",
    "environment_audit",
    "fixtures",
    "scheduler_config",
)
LEAVES = {
    "result": "result.json",
    "request_audit": "request-audit.json",
    "launch_audit": "launch-audit.json",
    "lifecycle_audit": "lifecycle-audit.json",
    "control_audit": "control-audit.json",
    "environment_audit": "apalache-environment-audit.json",
    "fixtures": "fixtures.json",
    "scheduler_config": "saved-scheduler-config.json",
}
TOP = {
    "qualification": "qualification.json",
    "focused_xml": "unit-final.xml",
    "registry_diagnostic_xml": "unit-registry-diagnostic-two.xml",
    "registry_test_source": "unit-final-test-source/tests/unit/logic/backends/test_apalache_resource_admission.py",
}
QUALIFICATION_ANCHOR = "a4610f2017c2047d94ed388386d30d21fc9e17a4ac41000e5dea695c98112572"
ANCHORS = {
    "capacity_failed": {
        "result": "ba03f113e8680790a8f63c17be0f7e21aa189cc2b37c98de6baf8e616e47e5f5",
        "command_result": "2eeb91cd456cfc3b4ed716d6c59a0af220fd0c768cbc3782b59e5c9c691dd610",
    },
    "resource_failed": {
        "result": "7d4cd9c047b7ce2eeea43244cff14a617d1fab1f26c18df48d38e3a2388b0dd6",
        "command_result": "793b29b41a07593c7d3bd5032331240f0be8ecd0d583c1b72310639b93c6899b",
    },
    "accepted_smoke": {
        "result": "5ee41c4936f67fb043c354680aff4b659cbcccc5a420bb97e02326f798c2698b",
        "command_result": "904da02d55c3723e08f457e95cd5096fdda07ca39fefecd55d7f495ad6f54b96",
    },
    "accepted_full": {
        "result": "f202f38d4e73894dbc5c6a1088153ba85e3c2d9db6f141a11b92763974bdd804",
        "command_result": "e98b8f8329f853af8993ddbc81b0c71333613e15862f78ed765a1ce9654c4629",
    },
}
TRUE = (
    "retained_apalache_admission_custody_conformance",
    "recorded_phase_bindings_reconciled",
    "failed_whole_attempts_preserved",
    "raw_witness_only_scope_preserved",
    "registry_error_regression_preserved",
    "input_files_unchanged",
)
FALSE = (
    "native_execution_performed",
    "training_executed",
    "current_authority_claimed",
    "owner_database_opened",
    "profile_keys_read",
    "owner_sources_imported",
    "source_execution_replayed",
    "checker_executions_replayed",
    "signature_authentication_performed",
    "process_origin_attested",
    "resource_enforcement_qualified",
    "original_request_custody_qualified",
    "model_check_authority_qualified",
    "proof_authority_qualified",
    "counterexample_replay_qualified",
    "registry_native_success_qualified",
    "whole_install_cancellation_qualified",
    "hard_aggregate_containment_qualified",
    "live_eligibility_qualified",
    "production_acceptance_qualified",
    "native_export_adoption_qualified",
    "throughput_improvement_qualified",
    "model_quality_qualified",
)
ZERO = ("runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs")
MAX_FILES, MAX_TOTAL, MAX_FILE = 96, 32 * 1024 * 1024, 1024 * 1024
MAX_MANIFEST, MAX_REPORT = 128 * 1024, 4 * 1024 * 1024
STOP_KINDS = ("pre_setup_cancel", "live_model_cancel", "after_model_cancel", "live_model_deadline")
LIFE_FLAGS = (
    "cancelled",
    "output_truncated",
    "process_tree_terminated",
    "resource_exhausted",
    "timed_out",
    "unavailable",
    "workspace_cleaned",
    "workspace_limit_exceeded",
)
REGISTRY_NAME = "test_all_default_execution_routes_reserve_actual_apalache_profile[registry]"
REGISTRY_ERROR = "AttributeError: type object 'ResultStatus' has no attribute 'TIMEOUT'"
BASE_RESULT_FIELDS = {
    "audit_sha256",
    "checks",
    "child_usage",
    "controls",
    "elapsed_seconds",
    "launches",
    "lifecycles",
    "mixed_cases",
    "native_lifecycles",
    "packaged_native_entries",
    "phase_counts",
    "prelaunch_lifecycles",
    "runs",
    "runtime",
    "schema",
    "scope",
    "shared_after",
    "shared_before",
    "shared_pool_compatibility",
    "smoke",
    "source_pins_after",
    "source_pins_before",
    "status",
    "tool_files_after",
    "tool_files_before",
    "tool_selection",
}
EXTRA_FIELDS = {
    "capacity_failed": {"error"},
    "resource_failed": {"dispatches", "error", "mixed_dispatch", "mixed_elapsed_seconds"},
    "accepted_smoke": {"dispatches"},
    "accepted_full": {
        "dispatches",
        "mixed_dispatch",
        "mixed_elapsed_seconds",
        "mixed_overlap_required",
    },
}
WIRE_FIELDS = {
    "counterexample_status",
    "disposition",
    "evidence",
    "interface",
    "outcome",
    "provider",
    "request_digest",
    "request_id",
    "result",
    "schema_version",
}
EVIDENCE_FIELDS = {
    "authority_ceiling",
    "authorizes_universal_proof",
    "available",
    "bindings_complete",
    "bounds",
    "capability",
    "claim_model_check",
    "claim_other_provider_capability",
    "claim_proof",
    "claim_theorem",
    "confidence",
    "config",
    "content_digest",
    "counterexample",
    "counterexample_status",
    "diagnostics",
    "disposition",
    "evidence_id",
    "external_tool_proof",
    "fallback_output_present",
    "fluent_text_present",
    "interface",
    "is_proved",
    "is_theorem_authority",
    "metadata",
    "mock_output_present",
    "mode",
    "model_check_established",
    "module",
    "proof_established",
    "properties",
    "provider",
    "receipt",
    "request_digest",
    "request_id",
    "result_authority",
    "result_status",
    "role",
    "schema_version",
    "semantics",
    "source_ref_ids",
    "theorem_established",
    "translation_ceiling",
}
RECEIPT_FIELDS = {
    "artifact_digest",
    "bounded",
    "capability",
    "checked_liveness_properties",
    "checked_safety_properties",
    "command",
    "configuration_digest",
    "configuration_text",
    "counterexample",
    "elapsed_ms",
    "executable",
    "fairness_limitations",
    "jvm_available",
    "model_digest",
    "output_truncated",
    "reason",
    "receipt_id",
    "returncode",
    "schema_version",
    "status",
    "stderr",
    "stdout",
    "timeout_seconds",
    "tool",
    "tool_version",
    "unbounded_proof",
}
CE_FIELDS = {
    "bindings_complete",
    "bounds",
    "config",
    "interface",
    "module",
    "property",
    "property_binding",
    "property_name",
    "raw_trace",
    "replay_notes",
    "replay_outcome",
    "replayed",
    "schema_version",
    "source",
    "state_count",
    "states",
    "status",
}
QUALIFICATION_FIELDS = {
    "artifact_sha256",
    "benchmark_evolution",
    "checks",
    "deselected_legacy_native_tests",
    "focused_attempts",
    "focused_tests",
    "initial_native_attempts",
    "intermediate_native_attempts",
    "native_full",
    "native_smoke",
    "native_success_cases",
    "new_admission_tests",
    "new_cache_replay",
    "new_codebase_smt_execution",
    "operation_stop_controls",
    "preservation",
    "production_tasks_closed",
    "recorded_at_utc",
    "schema",
    "selected_test_cases",
    "selected_tests",
    "status",
    "test_counts_summed",
    "total_lifecycles_across_all_attempts",
    "total_native_phases",
    "total_native_phases_across_all_attempts",
}


class Refusal(ValueError):
    """The closed historical receiving profile was not satisfied."""


def need(condition, label):
    if not condition:
        raise Refusal(label)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (
        json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode()


def same(left, right):
    return canonical(left) == canonical(right)


def closed(value, fields, label):
    need(type(value) is dict and set(value) == set(fields), label + " closed fields")


def integer(value, low=0, high=2**63 - 1):
    return type(value) is int and low <= value <= high


def number(value, low=0):
    return type(value) in (int, float) and math.isfinite(value) and low <= value <= 1e100


def digest(value):
    return type(value) is str and len(value) == 64 and set(value) <= set("0123456789abcdef")


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
        need(len(token) <= 64 and math.isfinite(float(token)), "finite JSON number")
        return float(token)

    def invalid(_):
        raise Refusal("nonfinite JSON")

    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=pairs,
        parse_int=parse_integer,
        parse_float=parse_float,
        parse_constant=invalid,
    )
    count, todo = 0, [(value, 0)]
    while todo:
        node, depth = todo.pop()
        count += 1
        need(depth <= 48 and count <= 180000, "JSON structural bound")
        if type(node) is str:
            need(
                len(node) <= 200000 and not any(0xD800 <= ord(c) <= 0xDFFF for c in node),
                "JSON string/surrogate bound",
            )
        elif type(node) is dict:
            need(len(node) <= 2048, "JSON mapping bound")
            todo.extend((v, depth + 1) for item in node.items() for v in item)
        elif type(node) is list:
            need(len(node) <= 4096, "JSON list bound")
            todo.extend((v, depth + 1) for v in node)
    return value


def bounded(path, cap):
    need(path.is_absolute() and path.resolve(strict=True) == path, "canonical input path")
    before = path.stat(follow_symlinks=False)
    need(stat.S_ISREG(before.st_mode) and before.st_size <= cap, "regular preallocation bound")

    def identity(value):
        return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns

    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        need(
            stat.S_ISREG(os.fstat(fd).st_mode) and identity(os.fstat(fd)) == identity(before),
            "descriptor identity",
        )
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(cap + 1)
        need(
            len(raw) == before.st_size
            and identity(os.fstat(fd))
            == identity(before)
            == identity(path.stat(follow_symlinks=False))
            and path.resolve(strict=True) == path,
            "stable bounded descriptor",
        )
        return raw
    finally:
        os.close(fd)


class Capture:
    def __init__(self):
        self.raw, self.total = {}, 0

    def take(self, path, pin=None, cap=MAX_FILE):
        path = Path(path).absolute()
        if pin is not None:
            closed(pin, ("path", "sha256", "size_bytes"), "descriptor")
            need(
                type(pin["path"]) is str
                and Path(pin["path"]) == path
                and digest(pin["sha256"])
                and integer(pin["size_bytes"], 0, cap),
                "descriptor exact types",
            )
            cap = min(cap, pin["size_bytes"])
        if path not in self.raw:
            need(len(self.raw) < MAX_FILES, "unique path allocation bound")
            available = min(cap, MAX_TOTAL - self.total)
            need(available >= 0, "aggregate allocation bound")
            raw = bounded(path, available)
            self.raw[path], self.total = raw, self.total + len(raw)
        raw = self.raw[path]
        need(len(raw) <= cap, "cached byte bound")
        if pin is not None:
            need(
                len(raw) == pin["size_bytes"] and sha(raw) == pin["sha256"],
                "raw descriptor binding",
            )
        return raw

    def stable(self):
        for path, raw in self.raw.items():
            need(bounded(path, len(raw)) == raw, "late original/copy/report drift")


def phase(argv):
    need(
        type(argv) is list
        and 0 < len(argv) <= 256
        and all(type(v) is str and len(v.encode()) <= 4096 for v in argv),
        "native argv profile",
    )
    return (
        "setup"
        if "-version" in argv
        else "help"
        if "version" in argv or "-help" in argv
        else "model"
    )


def rows_by_phase(rows, lifecycle=False):
    need(type(rows) is list and len(rows) <= 128, "native row population bound")
    result = {}
    for row in rows:
        need(type(row) is dict and type(row.get("case")) is str, "phase case label")
        key = row["case"], phase(row["request"]["argv"] if lifecycle else row["argv"])
        need(key not in result, "duplicate/ambiguous phase")
        result[key] = row
    return result


def is_apalache(argv):
    return Path(argv[0]).name == "apalache-mc"


def reconcile_phase(key, req, launch, life, budget, env, runtime):
    need(integer(runtime["pid"], 1) and type(runtime["boot_id"]) is str, "typed recorded process-owner identity")
    closed(
        req,
        ("argv", "case", "input_bytes", "input_sha256", "limits", "output_paths"),
        "native request",
    )
    closed(life, ("case", "request", "result", "shared_backoff_after"), "native lifecycle")
    lr, out, limits = life["request"], life["result"], req["limits"]
    closed(
        lr,
        (
            "argv",
            "input_file_count",
            "java_option_environment_absent",
            "max_output_bytes",
            "memory_bytes",
            "output_path_count",
            "resident_memory_bytes",
            "stdin_is_empty",
            "timeout_seconds",
        ),
        "lifecycle request",
    )
    closed(
        out,
        (
            "command",
            "elapsed_seconds",
            "error",
            "interface_version",
            "output_files",
            "pid",
            "returncode",
            "runtime",
            "stderr",
            "stdout",
            "termination_reason",
            *LIFE_FLAGS,
        ),
        "lifecycle result",
    )
    need(
        out["interface_version"] == "bounded-tool-runner/v1" and out["runtime"] == "jvm",
        "closed native result schema/runtime",
    )
    need(same(req["argv"], lr["argv"]) and same(lr["argv"], out["command"]), "phase argv custody")
    need(type(out["returncode"]) is int or out["returncode"] is None, "typed lifecycle returncode")
    need(
        all(type(out[k]) is bool for k in LIFE_FLAGS) and out["workspace_cleaned"] is True,
        "typed lifecycle/recorded cleanup",
    )
    need(
        number(out["elapsed_seconds"])
        and all(type(out[k]) is str for k in ("stdout", "stderr", "error", "termination_reason")),
        "lifecycle scalar types",
    )
    need(
        type(out["output_files"]) is dict
        and set(out["output_files"]) <= set(req["output_paths"])
        and all(type(v) is str for v in out["output_files"].values()),
        "output scope/bytes",
    )
    closed(
        limits,
        (
            "cpu_seconds",
            "enforce_file_size_limit",
            "max_argument_bytes",
            "max_arguments",
            "max_environment_bytes",
            "max_file_bytes",
            "max_input_bytes",
            "max_output_bytes",
            "max_output_files",
            "max_path_bytes",
            "max_workspace_bytes",
            "memory_bytes",
            "resident_memory_bytes",
            "termination_grace_seconds",
            "timeout_seconds",
        ),
        "native limits",
    )
    for field in (
        "max_argument_bytes",
        "max_arguments",
        "max_environment_bytes",
        "max_input_bytes",
        "max_output_bytes",
        "max_output_files",
        "max_path_bytes",
        "max_workspace_bytes",
        "memory_bytes",
        "resident_memory_bytes",
    ):
        need(integer(limits[field], 1), "integer native resource bound")
    need(
        number(limits["cpu_seconds"])
        and limits["cpu_seconds"] > 0
        and number(limits["timeout_seconds"])
        and limits["timeout_seconds"] > 0
        and number(limits["termination_grace_seconds"])
        and limits["enforce_file_size_limit"] is True,
        "finite native time/file bounds",
    )
    need(
        limits["max_output_bytes"] == 65536 and limits["memory_bytes"] == 4 * 1024**3,
        "selected output/address-space profile",
    )
    need(
        type(req["input_bytes"]) is dict
        and type(req["input_sha256"]) is dict
        and set(req["input_bytes"]) == set(req["input_sha256"])
        and all(integer(v) for v in req["input_bytes"].values())
        and all(digest(v) for v in req["input_sha256"].values())
        and type(req["output_paths"]) is list
        and len(set(req["output_paths"])) == len(req["output_paths"]),
        "input/output declaration population",
    )
    need(
        integer(lr["input_file_count"])
        and lr["input_file_count"] == len(req["input_bytes"])
        and integer(lr["output_path_count"])
        and lr["output_path_count"] == len(req["output_paths"])
        and lr["java_option_environment_absent"] is lr["stdin_is_empty"] is True,
        "recorded input/caller environment shape",
    )
    for field in ("max_output_bytes", "memory_bytes", "resident_memory_bytes"):
        need(type(lr[field]) is int and lr[field] == limits[field], "exact integer request bound")
    need(
        number(lr["timeout_seconds"])
        and lr["timeout_seconds"] == limits["timeout_seconds"] == budget["request_timeout_seconds"],
        "exact recorded phase timeout",
    )
    apalache = is_apalache(req["argv"])
    memory_mb = 512 if apalache else 256
    process_slots = 3 if apalache else 1
    need(limits["resident_memory_bytes"] == memory_mb * 1024**2, "selected requested RSS profile")
    if apalache:
        need(
            limits["max_file_bytes"] == 64 * 1024**2
            and type(limits["max_file_bytes"]) is int
            and limits["max_workspace_bytes"] == 128 * 1024**2,
            "finite Apalache extraction profile",
        )
        if key[1] == "model":
            need(
                req["argv"][1:]
                == [
                    "check",
                    "--config-file=apalache-runtime.json",
                    "--run-dir=apalache-run",
                    "--out-dir=apalache-out",
                    "--smt-solver=z3",
                    "--config=apalache.cfg",
                    "--length=3",
                    "--inv=Safety",
                    "--no-deadlock",
                    "BoundedCounter.tla",
                ],
                "owned model/config/solver/output arguments",
            )
            need(
                req["input_bytes"].get("apalache-runtime.json") == 3
                and type(req["input_bytes"]["apalache-runtime.json"]) is int
                and req["input_sha256"].get("apalache-runtime.json") == sha(b"{}\n"),
                "explicit empty runtime configuration",
            )
        else:
            need(
                req["argv"][1:] == ["version"]
                and req["input_bytes"] == {}
                and req["output_paths"] == [],
                "version descriptive profile",
            )
    if launch is None:
        need(
            out["pid"] is out["returncode"] is None
            and out["stdout"] == out["stderr"] == ""
            and out["output_files"] == {}
            and out["timed_out"] is True
            and out["termination_reason"] == "timeout"
            and "resource admission timed out" in out["error"]
            and key[1] == "help"
            and apalache
            and env is None,
            "prelaunch refusal stays distinct",
        )
        return {
            "case": key[0],
            "phase": key[1],
            "launched": False,
            "request": req,
            "launch": None,
            "lifecycle": life,
            "budget": budget,
            "environment": None,
            "execution_authenticated": False,
        }
    closed(
        launch,
        (
            "argv",
            "at_monotonic",
            "case",
            "launch_lease_id",
            "owned_leases",
            "root_allocations",
            "thread",
            "waiting",
        ),
        "native launch",
    )
    need(
        integer(out["pid"], 1)
        and integer(launch["thread"], 1)
        and integer(launch["waiting"])
        and number(launch["at_monotonic"]),
        "recorded launch scalar types",
    )
    file_size = (
        limits["max_file_bytes"]
        if limits["max_file_bytes"] is not None
        else limits["max_workspace_bytes"]
    )
    need(integer(file_size, 1), "launch file cap")
    cpu = math.ceil(limits["cpu_seconds"])
    prefix = [
        "/usr/bin/prlimit",
        "--core=0:0",
        f"--fsize={file_size}:{file_size}",
        f"--cpu={cpu}:{cpu}",
        f"--as={limits['memory_bytes']}:{limits['memory_bytes']}",
        "--",
    ]
    need(launch["argv"] == prefix + req["argv"], "exact recorded launch limits")
    leases = launch["owned_leases"]
    need(
        type(leases) is list
        and 0 < len(leases) <= 8
        and len({x["lease_id"] for x in leases}) == len(leases),
        "recorded lease population",
    )
    target = [x for x in leases if x["lease_id"] == launch["launch_lease_id"]]
    need(len(target) == 1, "launch lease identity")
    for lease in leases:
        closed(
            lease,
            (
                "acquired_at",
                "cancelled",
                "child_process_slots",
                "cpu_slots",
                "expires_at",
                "gpu_memory_mb",
                "heartbeat_at",
                "lane",
                "lease_id",
                "lease_key",
                "memory_mb",
                "owner_birth_marker",
                "owner_boot_id",
                "owner_pid",
                "parent_lease_id",
                "request_id",
                "requires_gpu",
                "sequence",
                "unified_memory_mb",
                "wait_seconds",
            ),
            "recorded lease",
        )
        need(
            all(
                integer(lease[k])
                for k in (
                    "child_process_slots",
                    "cpu_slots",
                    "gpu_memory_mb",
                    "memory_mb",
                    "owner_pid",
                    "sequence",
                    "unified_memory_mb",
                )
            )
            and all(
                number(lease[k])
                for k in ("acquired_at", "expires_at", "heartbeat_at", "wait_seconds")
            )
            and lease["cancelled"] is lease["requires_gpu"] is False
            and lease["parent_lease_id"] is None
            and lease["lane"] == "validation"
            and lease["owner_pid"] == runtime["pid"]
            and lease["owner_boot_id"] == runtime["boot_id"],
            "recorded root lease types/owner labels",
        )
    lease = target[0]
    need(
        lease["cpu_slots"] == 1
        and lease["child_process_slots"] == process_slots
        and lease["memory_mb"] == memory_mb
        and lease["gpu_memory_mb"] == lease["unified_memory_mb"] == 0,
        "recorded admitted provider profile",
    )
    closed(
        launch["root_allocations"],
        ("child_process_slots", "cpu_slots", "memory_mb"),
        "recorded root allocation",
    )
    owned_allocations = {k: sum(x[k] for x in leases) for k in launch["root_allocations"]}
    need(
        all(
            integer(launch["root_allocations"][k])
            and launch["root_allocations"][k] >= owned_allocations[k]
            for k in launch["root_allocations"]
        ),
        "whole-pool allocation cannot undercount selected owned roots",
    )
    foreign_difference = {
        k: launch["root_allocations"][k] - owned_allocations[k] for k in owned_allocations
    }
    if apalache:
        closed(
            env,
            (
                "case",
                "foreign_configuration_environment_absent",
                "jvm_args",
                "jvm_gc_args",
                "phase",
                "private_home_and_tmpdir",
            ),
            "recorded JVM environment",
        )
        need(
            env["case"] == key[0]
            and env["phase"] == key[1]
            and env["foreign_configuration_environment_absent"]
            is env["private_home_and_tmpdir"]
            is True,
            "managed environment scope",
        )
        expected = [
            "-Xms16m",
            f"-Xmx{memory_mb // 2}m",
            "-Xss1m",
            "-XX:ActiveProcessorCount=1",
            "-XX:MaxMetaspaceSize=128m",
            "-XX:ReservedCodeCacheSize=64m",
            "-XX:-UsePerfData",
            "-Duser.home=.",
        ]
        need(
            shlex.split(env["jvm_args"]) == expected
            and shlex.split(env["jvm_gc_args"]) == ["-XX:+UseSerialGC"],
            "half-RSS/serial-GC/cpu/private-home JVM profile",
        )
    else:
        need(env is None, "no Apalache environment for Java/TLC")
    return {
        "case": key[0],
        "phase": key[1],
        "launched": True,
        "request": req,
        "launch": launch,
        "lifecycle": life,
        "budget": budget,
        "environment": env,
        "recorded_owned_allocations": owned_allocations,
        "recorded_foreign_allocation_difference": foreign_difference,
        "foreign_ownership_authenticated": False,
        "execution_authenticated": False,
    }


def reconcile_case(case, docs, requests, lives):
    closed(
        case,
        (
            "case",
            "elapsed_seconds",
            "phase_count",
            "provider",
            "raw_witness",
            "result",
            "route",
            "valid",
        ),
        "completed case",
    )
    need(
        type(case["valid"]) is bool
        and integer(case["phase_count"], 3, 3)
        and number(case["elapsed_seconds"])
        and case["route"] in ("engine", "helper")
        and case["provider"] in ("apalache", "tlc"),
        "typed completed case identity",
    )
    label, provider, valid = case["case"], case["provider"], case["valid"]
    req, life = requests[(label, "model")], lives[(label, "model")]["result"]
    for phase_name in ("setup", "model", "help"):
        key = (label + ":constructor" if phase_name == "setup" else label, phase_name)
        row = lives[key]["result"]
        expected_exit = (
            12
            if not valid and phase_name == "model"
            else 1
            if provider == "tlc" and phase_name == "help"
            else 0
        )
        need(
            all(row[k] is False for k in LIFE_FLAGS if k != "workspace_cleaned")
            and row["workspace_cleaned"] is True
            and integer(row["returncode"], 0, 12)
            and row["returncode"] == expected_exit,
            "completed safe recorded phases",
        )
    outcome = case["result"]
    closed(outcome, WIRE_FIELDS, "wire execution result")
    need(
        outcome["schema_version"] == "state-execution-result/v2"
        and outcome["interface"] == "StateExecutionResult@2"
        and outcome["provider"] == provider
        and outcome["request_id"] == "req:" + label
        and digest(outcome["request_digest"]),
        "wire case/request schema binding",
    )
    raw, evidence = outcome["outcome"], outcome["evidence"]
    closed(
        raw,
        ("artifacts", "interface_version", "receipt", "request_digest", "result"),
        "backend outcome",
    )
    closed(evidence, EVIDENCE_FIELDS, "wire evidence")
    need(
        raw["interface_version"]
        == ("ApalacheBackend@1" if provider == "apalache" else "TLCBackend@1")
        and evidence["schema_version"] == "state-provider-evidence/v2"
        and evidence["interface"] == "StateProviderEvidence@2"
        and evidence["provider"] == provider
        and evidence["request_id"] == outcome["request_id"]
        and evidence["request_digest"] == outcome["request_digest"]
        and digest(raw["request_digest"])
        and digest(evidence["content_digest"])
        and same(raw["result"], outcome["result"]),
        "backend/evidence/request bindings",
    )
    receipt, wire_receipt = raw["receipt"], evidence["receipt"]
    closed(receipt, RECEIPT_FIELDS, "backend receipt")
    closed(wire_receipt, RECEIPT_FIELDS, "wire receipt")
    need(
        receipt["schema_version"] == "tla-model-check-receipt/v1"
        and wire_receipt["schema_version"] == "tla-model-check-receipt/v1"
        and same(
            {k: v for k, v in receipt.items() if k != "timeout_seconds"},
            {k: v for k, v in wire_receipt.items() if k != "timeout_seconds"},
        )
        and number(receipt["timeout_seconds"])
        and number(wire_receipt["timeout_seconds"])
        and receipt["timeout_seconds"] == wire_receipt["timeout_seconds"],
        "wire receipt exact fields and numeric timeout normalization",
    )
    need(
        type(receipt["returncode"]) is int
        and receipt["returncode"] == life["returncode"]
        and receipt["command"] == life["command"]
        and receipt["stdout"] == life["stdout"]
        and receipt["stderr"] == life["stderr"]
        and receipt["output_truncated"] is False
        and len(life["stdout"].encode()) + len(life["stderr"].encode())
        <= req["limits"]["max_output_bytes"],
        "receipt raw lifecycle custody",
    )
    artifacts = raw["artifacts"]
    need(
        artifacts["schema_version"] == "tla-generated-artifact/v1"
        and artifacts["interface_version"] == "TLABackend@1"
        and artifacts["bounded"] is receipt["bounded"] is True
        and artifacts["unbounded_proof"] is receipt["unbounded_proof"] is False,
        "generated artifact/receipt closed version and ceiling",
    )
    need(
        receipt["artifact_digest"]
        == artifacts["artifact_digest"]
        == evidence["module"]["artifact_digest"]
        and receipt["model_digest"]
        == artifacts["model_digest"]
        == req["input_sha256"]["BoundedCounter.tla"],
        "artifact/native input identities",
    )
    config_name = "apalache.cfg" if provider == "apalache" else "BoundedCounter.cfg"
    need(
        receipt["configuration_digest"]
        == req["input_sha256"][config_name]
        == evidence["config"]["configuration_digest"],
        "configuration native/V2 identity",
    )
    need(
        all(
            evidence[k] is False
            for k in (
                "claim_proof",
                "claim_theorem",
                "authorizes_universal_proof",
                "proof_established",
                "theorem_established",
                "is_proved",
                "is_theorem_authority",
                "claim_other_provider_capability",
            )
        )
        and evidence["authority_ceiling"] == evidence["translation_ceiling"] == "bounded"
        and evidence["confidence"] == 0.0
        and type(evidence["confidence"]) in (int, float),
        "bounded recorded authority ceiling",
    )
    need(
        all(
            evidence[k] is True
            for k in (
                "available",
                "bindings_complete",
                "claim_model_check",
                "model_check_established",
                "external_tool_proof",
            )
        )
        and all(
            evidence[k] is False
            for k in ("mock_output_present", "fallback_output_present", "fluent_text_present")
        ),
        "typed recorded publisher evidence claims",
    )
    module, config = evidence["module"], evidence["config"]
    closed(
        module,
        (
            "artifact_digest",
            "interface",
            "model_digest",
            "module_name",
            "schema_version",
            "source_document_id",
            "source_kind",
            "source_map_size",
        ),
        "module binding",
    )
    closed(
        config,
        (
            "config_kind",
            "configuration_digest",
            "configuration_text",
            "interface",
            "provider",
            "schema_version",
        ),
        "config binding",
    )
    need(
        module["schema_version"] == "state-module-binding/v2"
        and module["interface"] == "StateModuleBinding@2"
        and module["model_digest"] == receipt["model_digest"]
        and integer(module["source_map_size"], 0, 0)
        and config["schema_version"] == "state-config-binding/v2"
        and config["interface"] == "StateConfigBinding@2"
        and config["provider"] == provider
        and config["configuration_text"] == receipt["configuration_text"].rstrip("\n"),
        "module/config exact versions and raw declarations",
    )
    ce = evidence["counterexample"]
    closed(ce, CE_FIELDS, "counterexample binding")
    need(
        ce["schema_version"] == "state-counterexample-binding/v2"
        and ce["interface"] == "StateCounterexampleBinding@2"
        and integer(ce["state_count"])
        and ce["state_count"] == len(ce["states"])
        and type(ce["replayed"]) is bool
        and same(ce["module"], evidence["module"])
        and same(ce["config"], evidence["config"])
        and same(ce["bounds"], evidence["bounds"])
        and same(ce["property_binding"], evidence["properties"])
        and ce["property"]
        == ce["property_name"]
        == evidence["properties"]["primary_property"]
        == "Safety",
        "counterexample bound/schema/property/population",
    )
    expected = "satisfied" if valid else "counterexample"
    need(
        outcome["disposition"] == evidence["disposition"] == expected
        and outcome["result"]["schema_version"] == "typed-backend-result/v1"
        and outcome["result"]["status"] == ("satisfied" if valid else "violated")
        and evidence["result_status"] == outcome["result"]["status"]
        and evidence["result_authority"] == outcome["result"]["authority"] == "model_check",
        "recorded typed disposition",
    )
    witness = None
    if provider == "apalache":
        fi = docs["fixtures"]["valid" if valid else "invalid"]
        inputs = {
            "BoundedCounter.tla": fi["model_text"].encode(),
            "apalache.cfg": fi["apalache_config_text"].encode(),
            "apalache-runtime.json": b"{}\n",
        }
        need(
            same(req["input_bytes"], {k: len(v) for k, v in inputs.items()})
            and req["input_sha256"] == {k: sha(v) for k, v in inputs.items()}
            and artifacts["artifact_digest"] == fi["artifact_digest"]
            and artifacts["model_digest"] == fi["model_digest"]
            and config["configuration_text"] == fi["apalache_config_text"].strip(),
            "exact UTF8 retained model/config inputs",
        )
        need(
            receipt["tool_version"] == "0.58.3"
            and lives[(label, "help")]["result"]["stdout"].strip() == receipt["tool_version"],
            "recorded version phase custody",
        )
        semantics, bounds, properties = (
            evidence["semantics"],
            evidence["bounds"],
            evidence["properties"],
        )
        need(
            semantics["schema_version"] == "state-semantics-binding/v2"
            and semantics["finite_state"] is semantics["liveness"] is semantics["fairness"] is False
            and semantics["step_bounded"] is semantics["safety"] is True
            and bounds["schema_version"] == "state-bounds-binding/v2"
            and bounds["finite_state"] is False
            and bounds["finite_trace_only"] is bounds["step_bounded"] is True
            and integer(bounds["max_steps"], 3, 3)
            and properties["schema_version"] == "state-property-binding/v2"
            and properties["checked_liveness"] == []
            and properties["checked_safety"] == ["Safety"],
            "finite safety-only Apalache scope",
        )
        need(
            ce["states"] == [] and ce["state_count"] == 0,
            "empty Apalache parsed states never replay authority",
        )
        if valid:
            need(
                receipt["counterexample"] is None
                and ce["replayed"] is False
                and case["raw_witness"] is None,
                "valid Apalache witness frontier",
            )
        else:
            raw_ce = receipt["counterexample"]
            closed(
                raw_ce,
                ("raw", "replay_notes", "replayed", "schema_version", "source", "states"),
                "raw counterexample",
            )
            trace = life["output_files"].get("apalache-run/violation.tla")
            need(
                type(trace) is str
                and raw_ce["schema_version"] == "tla-counterexample/v1"
                and raw_ce["raw"] == trace
                and ce["raw_trace"] == trace.strip()
                and raw_ce["states"] == ce["states"] == []
                and raw_ce["replayed"] is ce["replayed"] is True
                and raw_ce["replay_notes"]
                == ce["replay_notes"]
                == ["counterexample contained no parseable State blocks"],
                "raw witness/legacy empty replay flag custody",
            )
            values = re.findall(r"(?m)^State([0-9]+) == n = (-?[0-9]+)$", trace)
            need(
                values == [("0", "0"), ("1", "1"), ("2", "2")], "captured raw witness labels/values"
            )
            declared = case["raw_witness"]
            need(
                declared["path"] == "apalache-run/violation.tla"
                and declared["sha256"] == sha(trace.encode())
                and declared["raw_state_values"] == ["0", "1", "2"]
                and integer(declared["parsed_state_count"], 0, 0),
                "raw witness digest/population declaration",
            )
            witness = {
                "raw_sha256": sha(trace.encode()),
                "raw_labels": [0, 1, 2],
                "raw_values": ["0", "1", "2"],
                "parsed_state_count": 0,
                "legacy_replayed_recorded": True,
                "structural_replay_qualified": False,
            }
    elif valid:
        need(
            ce["states"] == [] and ce["replayed"] is False and receipt["counterexample"] is None,
            "separate TLC valid frontier",
        )
    else:
        need(
            same(receipt["counterexample"]["states"], ce["states"])
            and [x["index"] for x in ce["states"]] == [1, 2, 3]
            and all(type(x["index"]) is int for x in ce["states"]),
            "separate TLC captured state rows",
        )
    return {
        "case": label,
        "provider": provider,
        "route": case["route"],
        "valid": valid,
        "recorded_result": outcome,
        "raw_witness": witness,
        "original_request_bytes_available": False,
        "mixed_tlc_fixture_body_available": False if provider == "tlc" else None,
        "new_model_check_authority": False,
        "counterexample_replay_qualified": False,
    }


def reconcile_attempt(ident, docs):
    need(ident in IDS, "known attempt")
    r, command = docs["result"], docs["command_result"]
    closed(r, BASE_RESULT_FIELDS | EXTRA_FIELDS[ident], "native result")
    need(
        r["schema"] == "apalache-resource-admission-benchmark@1", "closed native benchmark version"
    )
    accepted = ident.startswith("accepted")
    need(
        r["status"] == ("passed" if accepted else "failed")
        and (accepted or type(r["error"]) is str and r["error"]),
        "accepted/failed whole operation distinction",
    )
    closed(
        command,
        (
            "after",
            "argv",
            "before",
            "cwd",
            "env_overrides",
            "freeze_sha256",
            "returncode",
            "seconds",
        ),
        "outer command",
    )
    need(
        type(command["returncode"]) is int
        and command["returncode"] == (0 if accepted else 1)
        and number(command["seconds"])
        and number(r["elapsed_seconds"])
        and digest(command["freeze_sha256"]),
        "typed command disposition/clocks",
    )
    need(
        same(command["before"], command["after"])
        and same(command["before"], r["source_pins_before"])
        and same(r["source_pins_before"], r["source_pins_after"])
        and len(r["source_pins_before"]) == 80
        and all(digest(v) for v in r["source_pins_before"].values()),
        "80 inert source declarations stable",
    )
    need(
        same(r["tool_files_before"], r["tool_files_after"])
        and all(digest(v) for v in r["tool_files_before"].values()),
        "inert tool hash declarations stable",
    )
    need(
        type(r["checks"]) is dict
        and all(v is True for v in r["checks"].values())
        and {"owned_work_drained", "shared_config_unchanged", "sources_stable"} <= set(r["checks"]),
        "recorded cleanup checks",
    )
    config = docs["scheduler_config"]
    need(
        config["schema"] == "codebase-saved-scheduler-config@1"
        and same(config["config"], r["shared_before"]["config"])
        and same(r["shared_before"]["config"], r["shared_after"]["config"])
        and all(
            integer(r["shared_after"][k], 0, 0)
            for k in ("owned_active_leases", "owned_waiting_requests")
        ),
        "recorded shared configuration/owned drain",
    )
    closed(docs["fixtures"], ("invalid", "valid"), "fixture population")
    for fixture in docs["fixtures"].values():
        need(
            fixture["schema_version"] == "tla-generated-artifact/v1"
            and fixture["interface_version"] == "TLABackend@1"
            and fixture["bounded"] is True
            and fixture["unbounded_proof"] is False
            and digest(fixture["artifact_digest"])
            and sha(fixture["model_text"].encode()) == fixture["model_digest"]
            and sha(fixture["apalache_config_text"].encode()) == fixture["apalache_config_digest"]
            and sha(fixture["tlc_config_text"].encode()) == fixture["tlc_config_digest"],
            "typed fixture raw UTF8 digest bindings",
        )
    requests, launches, lives = (
        rows_by_phase(docs["request_audit"]),
        rows_by_phase(docs["launch_audit"]),
        rows_by_phase(docs["lifecycle_audit"], True),
    )
    need(
        set(requests) == set(lives) and set(launches) <= set(lives),
        "complete request/lifecycle/launch joins",
    )
    operation_phases = {}
    for label, phase_name in requests:
        operation_phases.setdefault(label.removesuffix(":constructor"), []).append(phase_name)
    need(
        all(
            value in (["setup"], ["setup", "model"], ["setup", "model", "help"])
            for value in operation_phases.values()
        ),
        "recorded per-operation phase ordering",
    )
    absent = set(lives) - set(launches)
    need(
        absent == ({("parallel:4:engine:False", "help")} if ident == "capacity_failed" else set()),
        "exact prelaunch refusal population",
    )
    ca = docs["control_audit"]
    closed(ca, ("boundaries", "phase_budgets", "triggers"), "control audit")
    need(
        type(ca["phase_budgets"]) is list and len(ca["phase_budgets"]) <= 128,
        "phase budget population bound",
    )
    budgets = {}
    for budget in ca["phase_budgets"]:
        closed(
            budget,
            (
                "at_monotonic",
                "case",
                "deadline",
                "phase",
                "remaining_seconds",
                "request_timeout_seconds",
            ),
            "phase budget",
        )
        key = (
            budget["case"] + (":constructor" if budget["phase"] == "setup" else ""),
            budget["phase"],
        )
        need(
            key not in budgets
            and key in requests
            and all(
                number(budget[k])
                for k in (
                    "at_monotonic",
                    "deadline",
                    "remaining_seconds",
                    "request_timeout_seconds",
                )
            ),
            "unique typed budget identity",
        )
        budgets[key] = budget
    need(set(budgets) == set(requests), "complete budget population")
    envs = {}
    need(
        type(docs["environment_audit"]) is list and len(docs["environment_audit"]) <= 128,
        "environment population bound",
    )
    for env in docs["environment_audit"]:
        key = env["case"], env["phase"]
        need(key not in envs, "duplicate environment phase")
        envs[key] = env
    need(
        set(envs) == {key for key in launches if is_apalache(requests[key]["argv"])},
        "exact managed environment population",
    )
    phases = [
        reconcile_phase(
            key, req, launches.get(key), lives[key], budgets[key], envs.get(key), r["runtime"]
        )
        for key, req in requests.items()
    ]
    for event in ca["boundaries"] + ca["triggers"]:
        key = event["case"], "model"
        need(
            key in lives
            and integer(event["pid"], 1)
            and event["pid"] == lives[key]["result"]["pid"]
            and number(event["at_monotonic"]),
            "recorded boundary/trigger model PID identity",
        )
        if event.get("kind") == "after_actual_completed_model":
            need(
                type(event["returncode"]) is int
                and event["returncode"] == lives[key]["result"]["returncode"] == 12
                and event["workspace_cleaned"] is lives[key]["result"]["workspace_cleaned"] is True,
                "after-model cancellation completed raw violation custody",
            )
        else:
            need(event["observed_live"] is True, "recorded live boundary marker")
    expected = {
        "capacity_failed": {"setup": 12, "model": 12, "help": 12},
        "resource_failed": {"setup": 19, "model": 19, "help": 16},
        "accepted_smoke": {"setup": 2, "model": 2, "help": 2},
        "accepted_full": {"setup": 19, "model": 19, "help": 16},
    }[ident]
    need(
        same(dict(Counter(key[1] for key in requests)), expected)
        and same(r["phase_counts"], expected),
        "typed exact phase populations",
    )
    need(
        integer(r["launches"])
        and r["launches"] == len(launches) == r["native_lifecycles"]
        and type(r["native_lifecycles"]) is int
        and integer(r["lifecycles"])
        and r["lifecycles"] == len(lives)
        and integer(r["prelaunch_lifecycles"])
        and r["prelaunch_lifecycles"] == len(absent),
        "launch/lifecycle denominators",
    )
    batches = r["runs"]
    widths = (
        [1, 2] if ident == "capacity_failed" else [1] if ident == "accepted_smoke" else [1, 2, 4]
    )
    need(
        type(batches) is list
        and [x["workers"] for x in batches] == widths
        and all(type(x["workers"]) is int for x in batches),
        "ordered historical batch population",
    )
    cases, covered = [], set()
    for batch in batches:
        need(number(batch["elapsed_seconds"]), "recorded batch timing")
        width = batch["workers"]
        expected_cases = [
            (f"parallel:{width}:{route}:{valid}", route, valid)
            for route in (("engine",) if ident == "accepted_smoke" else ("engine", "helper"))
            for valid in (True, False)
        ]
        need(
            [(x["case"], x["route"], x["valid"]) for x in batch["cases"]] == expected_cases
            and all(x["provider"] == "apalache" for x in batch["cases"]),
            "complete ordered batch cases",
        )
        if ident != "capacity_failed":
            need(
                integer(batch["requested_workers"], width, width)
                and integer(batch["effective_workers"], 1, 1)
                and batch["dispatch"]["requested_workers"] == width
                and type(batch["dispatch"]["requested_workers"]) is int
                and integer(batch["dispatch"]["effective_workers"], 1, 1),
                "requested callers distinct from effective dispatch",
            )
        for case in batch["cases"]:
            cases.append(reconcile_case(case, docs, requests, lives))
            covered.update(
                key for key in requests if key[0].removesuffix(":constructor") == case["case"]
            )
    mixed = r["mixed_cases"]
    if ident != "capacity_failed":
        expected_dispatches = [batch["dispatch"] for batch in batches]
        if ident in ("resource_failed", "accepted_full"):
            need(integer(r["mixed_dispatch"]["requested_workers"], 4, 4) and integer(r["mixed_dispatch"]["effective_workers"], 1, 1), "mixed requested callers remain serial dispatch")
            expected_dispatches.append(r["mixed_dispatch"])
        need(same(r["dispatches"], expected_dispatches), "complete ordered advisory dispatch population")
        if ident == "accepted_full":
            need(r["mixed_overlap_required"] is False, "serial mixed dispatch does not qualify overlap")
    need(
        [(x["case"], x["provider"], x["valid"]) for x in mixed]
        == (
            []
            if ident in ("capacity_failed", "accepted_smoke")
            else [
                (f"mixed:{provider}:{valid}", provider, valid)
                for valid in (True, False)
                for provider in ("apalache", "tlc")
            ]
        ),
        "ordered mixed provider population",
    )
    for case in mixed:
        cases.append(reconcile_case(case, docs, requests, lives))
        covered.update(
            key for key in requests if key[0].removesuffix(":constructor") == case["case"]
        )
    kinds = (
        []
        if ident in ("capacity_failed", "accepted_smoke")
        else list(STOP_KINDS[:3] if ident == "resource_failed" else STOP_KINDS)
    )
    need([x["kind"] for x in r["controls"]] == kinds, "complete retained stop population")
    controls = []
    for item in r["controls"]:
        need(
            item["case"] == "control:" + item["kind"]
            and item["result_published"] is False
            and integer(item["operation_timeout_ms"], 1),
            "stopped operation withheld result",
        )
        stop, timed = item["interruption"], item["kind"] == "live_model_deadline"
        need(
            stop["type"] == ("ProofOperationTimeout" if timed else "ProofOperationCancelled")
            and stop["kind"] == ("timeout" if timed else "cancelled")
            and type(stop["timeout_ms"]) is int
            and stop["timeout_ms"] == item["operation_timeout_ms"]
            and integer(stop["elapsed_ms"]),
            "typed outer interruption precedence",
        )
        keys = [key for key in requests if key[0].removesuffix(":constructor") == item["case"]]
        need(
            integer(item["phase_count"])
            and item["phase_count"] == len(keys)
            and Counter(item["phases"]) == Counter(key[1] for key in keys),
            "stop complete phase frontier",
        )
        need(
            same(item["boundaries"], [x for x in ca["boundaries"] if x["case"] == item["case"]])
            and same(
                item["live_triggers"], [x for x in ca["triggers"] if x["case"] == item["case"]]
            ),
            "stop trigger/boundary custody",
        )
        covered.update(keys)
        controls.append(copy.deepcopy(item))
    unreturned = [x for x in phases if (x["case"], x["phase"]) not in covered]
    need(
        len(unreturned)
        == (12 if ident == "capacity_failed" else 2 if ident == "resource_failed" else 0),
        "complete unreturned frontier",
    )
    failure = None
    if ident == "capacity_failed":
        need(
            "unexpected Apalache phases/lifecycles" in r["error"]
            and all(x["case"].startswith("parallel:4:") for x in unreturned),
            "capacity failure with unavailable returned result",
        )
        failure = (
            "prelaunch_version_admission_refusal; failed case exact returned V2 result unavailable"
        )
    elif ident == "resource_failed":
        need(
            "interrupted operation published a model result" in r["error"]
            and {x["case"].removesuffix(":constructor") for x in unreturned}
            == {"control:live_model_deadline"},
            "failed deadline assertion remains unreturned frontier",
        )
        model = next(x for x in unreturned if x["phase"] == "model")
        out = model["lifecycle"]["result"]
        need(
            type(out["returncode"]) is int
            and out["returncode"] == -9
            and out["resource_exhausted"] is True
            and out["timed_out"] is False
            and out["termination_reason"] == "resource_limit"
            and out["elapsed_seconds"] < model["request"]["limits"]["timeout_seconds"],
            "resource stop is not accepted wall timeout",
        )
        failure = "recorded resource-limit termination before intended wall deadline; OS cause and returned V2 result unavailable"
    return {
        "id": ident,
        "recorded_whole_status": r["status"],
        "recorded_command_returncode": command["returncode"],
        "accepted_current_generation": accepted,
        "recorded_command_seconds": command["seconds"],
        "recorded_native_seconds": r["elapsed_seconds"],
        "phase_counts": expected,
        "native_phase_count": len(launches),
        "lifecycle_count": len(lives),
        "prelaunch_refusal_count": len(absent),
        "completed_case_count": len(cases),
        "completed_stop_control_count": len(controls),
        "phases": phases,
        "completed_cases": cases,
        "no_result_controls": controls,
        "unreturned_operation_phases": unreturned,
        "recorded_failure": failure,
        "failed_case_return_value_available": False if not accepted else None,
        "recorded_error": r.get("error"),
        "recorded_control_audit": ca,
        "raw_witness_case_count": sum(x["raw_witness"] is not None for x in cases),
        "recorded_source_pins": r["source_pins_before"],
        "recorded_tool_pins": r["tool_files_before"],
        "recorded_shared_after": r["shared_after"],
        "recorded_dispatches": r.get("dispatches", []),
        "source_bodies_verified": False,
        "tool_bodies_verified": False,
        "aggregate_resource_enforcement_qualified": False,
        "whole_operation_success_qualified": False,
        "counterexample_replay_qualified": False,
        "unknowns": [
            "original caller request bytes",
            "producer/process origin",
            "aggregate and whole-install enforcement",
            "source/checker truth",
            "current eligibility",
            "unseen digest recipes",
            "native registry result",
        ],
    }


def registry_controls(focused_raw, diagnostic_raw, source_raw):
    def xml(raw):
        text = raw.decode("utf-8")
        need(
            len(raw) <= MAX_FILE
            and "<!DOCTYPE" not in text.upper()
            and "<!ENTITY" not in text.upper()
            and "\x00" not in text,
            "bounded inert XML",
        )
        root = ET.fromstring(text)
        cases = list(root.iter("testcase"))
        need(
            len(cases) <= 2048
            and len({(x.get("classname"), x.get("name")) for x in cases}) == len(cases),
            "unique XML testcase population",
        )
        return cases

    focused, diagnostic = xml(focused_raw), xml(diagnostic_raw)
    need(
        len(focused) == 424
        and all(
            not any(x.tag in ("failure", "error", "skipped") for x in case) for case in focused
        ),
        "focused accepted 424 population",
    )
    passed = [x for x in focused if x.get("name") == REGISTRY_NAME]
    need(
        len(passed) == 1 and len(diagnostic) == 1 and diagnostic[0].get("name") == REGISTRY_NAME,
        "registry focused/diagnostic identity",
    )
    failures = diagnostic[0].findall("failure")
    need(
        len(failures) == 1
        and "registry result error" in "".join(failures[0].itertext())
        and REGISTRY_ERROR in "".join(failures[0].itertext()),
        "recorded registry ERROR diagnostic",
    )
    need(len(source_raw) <= 65536, "inert test-source parse bound")
    tree = ast.parse(source_raw.decode())
    nodes = []
    for node in ast.walk(tree):
        need(len(nodes) < 16384, "inert AST node allocation bound")
        nodes.append(node)
    functions = [
        x
        for x in tree.body
        if isinstance(x, ast.FunctionDef) and x.name == REGISTRY_NAME.split("[")[0]
    ]
    need(len(functions) == 1, "registry assertion source identity")
    branches = [
        x
        for x in ast.walk(functions[0])
        if isinstance(x, ast.If)
        and isinstance(x.test, ast.Compare)
        and ast.unparse(x.test) == "route == 'registry'"
    ]
    need(len(branches) == 1, "explicit registry branch")
    assertions = [ast.unparse(x.test) for x in branches[0].body if isinstance(x, ast.Assert)]
    need(
        "result.status.value == 'error'" in assertions
        and f"result.diagnostics == ({REGISTRY_ERROR!r},)" in assertions,
        "inert registry ERROR expectation",
    )
    return {
        "focused_case_count": 424,
        "registry_case_identity": REGISTRY_NAME,
        "diagnostic_test_failure_preserved": True,
        "recorded_registry_status": "error",
        "recorded_diagnostic": REGISTRY_ERROR,
        "passed_final_controlled_expectation": True,
        "source_executed": False,
        "native_registry_result_available": False,
        "registry_native_success_qualified": False,
    }


def qualification_summary(q, summaries):
    closed(q, QUALIFICATION_FIELDS, "qualification")
    need(
        q["schema"] == "apalache-execution-admission-qualification@1"
        and q["status"] == "passed_partial_scope",
        "qualification exact version/partial scope",
    )
    expected = {
        "total_native_phases": 60,
        "total_native_phases_across_all_attempts": 161,
        "total_lifecycles_across_all_attempts": 162,
        "native_success_cases": 18,
        "operation_stop_controls": 4,
        "focused_tests": 424,
        "selected_tests": 1708,
        "new_admission_tests": 47,
    }
    need(
        all(type(q[k]) is int and q[k] == v for k, v in expected.items()),
        "typed qualification counts",
    )
    need(
        q["new_cache_replay"] is q["new_codebase_smt_execution"] is q["test_counts_summed"] is False
        and q["production_tasks_closed"] == [],
        "qualification nonpromotion scope",
    )
    accepted = {x["id"]: x for x in summaries if x["accepted_current_generation"]}
    for role, ident in (("native_smoke", "accepted_smoke"), ("native_full", "accepted_full")):
        value, s = q[role], accepted[ident]
        need(
            value["result"] == DIRECTORIES[ident] + "/result.json"
            and type(value["native_phases"]) is int
            and value["native_phases"] == s["native_phase_count"]
            and integer(value["success_cases"])
            and value["success_cases"] == s["completed_case_count"]
            and integer(value["controls"])
            and value["controls"] == s["completed_stop_control_count"]
            and same(value["phase_counts"], s["phase_counts"]),
            "qualification accepted phase/case joins",
        )
    return {
        "recorded_qualification_status": q["status"],
        "accepted_native_phase_count": 60,
        "accepted_success_case_count": 18,
        "accepted_stop_control_count": 4,
        "declared_all_attempt_native_phase_count": 161,
        "declared_all_attempt_lifecycle_count": 162,
        "reported_all_attempt_counts_fully_reaudited": False,
        "selected_attempt_count": 4,
        "accepted_attempt_count": 2,
        "failed_attempt_count": 2,
        "selected_native_phase_count": sum(x["native_phase_count"] for x in summaries),
        "selected_lifecycle_count": sum(x["lifecycle_count"] for x in summaries),
        "selected_prelaunch_refusal_count": sum(x["prelaunch_refusal_count"] for x in summaries),
        "selected_case_count": sum(x["completed_case_count"] for x in summaries),
        "historical_completed_stop_control_count": sum(
            x["completed_stop_control_count"] for x in summaries
        ),
        "registry_native_result_available": False,
    }


def mutation_controls(docs_list):
    base = dict(docs_list)["accepted_full"]
    faults = (
        (
            "future native version repaired",
            lambda d: d["result"].update(schema="apalache-resource-admission-benchmark@2"),
        ),
        ("Boolean command exit", lambda d: d["command_result"].update(returncode=False)),
        ("phase omitted", lambda d: d["lifecycle_audit"].pop()),
        (
            "duplicate phase ambiguity",
            lambda d: d["request_audit"].append(copy.deepcopy(d["request_audit"][0])),
        ),
        ("Boolean phase count", lambda d: d["result"].update(launches=True)),
        (
            "Boolean lifecycle exit",
            lambda d: d["lifecycle_audit"][0]["result"].update(returncode=False),
        ),
        (
            "requested RSS widened",
            lambda d: d["request_audit"][1]["limits"].update(resident_memory_bytes=1024**3),
        ),
        (
            "file extraction cap absent",
            lambda d: d["request_audit"][1]["limits"].update(max_file_bytes=None),
        ),
        (
            "launch limit rebound",
            lambda d: d["launch_audit"][0]["argv"].__setitem__(1, "--core=1:1"),
        ),
        (
            "process reservation shrunk",
            lambda d: d["launch_audit"][1]["owned_leases"][0].update(child_process_slots=1),
        ),
        (
            "heap exceeds half RSS",
            lambda d: d["environment_audit"][0].update(
                jvm_args=d["environment_audit"][0]["jvm_args"].replace("-Xmx256m", "-Xmx512m")
            ),
        ),
        (
            "ambient environment promoted",
            lambda d: d["environment_audit"][0].update(
                foreign_configuration_environment_absent=False
            ),
        ),
        (
            "runtime config overridden",
            lambda d: d["request_audit"][1]["input_sha256"].update(
                {"apalache-runtime.json": "0" * 64}
            ),
        ),
        (
            "descriptive version forged",
            lambda d: d["lifecycle_audit"][2]["result"].update(stdout="0.99.0\n"),
        ),
        (
            "wire future version repaired",
            lambda d: d["result"]["runs"][0]["cases"][0]["result"].update(
                schema_version="state-execution-result/v3"
            ),
        ),
        (
            "Boolean wire returncode",
            lambda d: d["result"]["runs"][0]["cases"][0]["result"]["outcome"]["receipt"].update(
                returncode=False
            ),
        ),
        (
            "universal proof promoted",
            lambda d: d["result"]["runs"][0]["cases"][0]["result"]["evidence"].update(
                claim_theorem=True
            ),
        ),
        (
            "Apalache fairness promoted",
            lambda d: d["result"]["runs"][0]["cases"][0]["result"]["evidence"]["semantics"].update(
                fairness=True
            ),
        ),
        (
            "empty trace manufactured state",
            lambda d: d["result"]["runs"][0]["cases"][1]["result"]["evidence"][
                "counterexample"
            ].update(states=[{"index": 1}], state_count=1),
        ),
        (
            "raw witness digest forged",
            lambda d: d["result"]["runs"][0]["cases"][1]["raw_witness"].update(sha256="0" * 64),
        ),
        (
            "captured witness altered",
            lambda d: d["lifecycle_audit"][4]["result"]["output_files"].update(
                {"apalache-run/violation.tla": "State0 == n = 99\n"}
            ),
        ),
        (
            "stop result published",
            lambda d: d["result"]["controls"][0].update(result_published=True),
        ),
        (
            "outer timeout reason aliased",
            lambda d: d["result"]["controls"][-1]["interruption"].update(
                type="ProofOperationCancelled"
            ),
        ),
        (
            "Boolean timeout budget",
            lambda d: d["result"]["controls"][-1]["interruption"].update(timeout_ms=True),
        ),
        (
            "caller width confused with dispatch",
            lambda d: d["result"]["runs"][-1].update(effective_workers=4),
        ),
        ("batch order changed", lambda d: d["result"]["runs"].reverse()),
        ("advisory dispatch omitted", lambda d: d["result"]["dispatches"].pop()),
        ("case result omitted", lambda d: d["result"]["runs"][0]["cases"].pop()),
        (
            "cleanup drain false",
            lambda d: d["result"]["shared_after"].update(owned_waiting_requests=1),
        ),
        ("unknown native field", lambda d: d["result"].update(current_authority=True)),
    )
    controls = []
    for label, mutate in faults:
        changed = copy.deepcopy(base)
        mutate(changed)
        changed["result"]["audit_sha256"] = {
            LEAVES[role]: sha(canonical(changed[role]))
            for role in (
                "request_audit",
                "launch_audit",
                "lifecycle_audit",
                "control_audit",
                "environment_audit",
            )
        }
        try:
            reconcile_attempt("accepted_full", changed)
        except (Refusal, KeyError, TypeError, StopIteration) as exc:
            controls.append(
                {
                    "control": label,
                    "refused": True,
                    "reason": str(exc),
                    "independent_original_anchors_unchanged": True,
                }
            )
        else:
            raise Refusal("unrefused authored control: " + label)
    return controls


def output_population(root, expected):
    need(
        root.is_absolute()
        and root.resolve(strict=True) == root
        and stat.S_ISDIR(root.stat(follow_symlinks=False).st_mode),
        "canonical output root",
    )
    root_identity = root.stat(follow_symlinks=False)
    files, dirs = set(), set()
    for folder in (root, root / "retained"):
        need(
            folder.resolve(strict=True) == folder
            and stat.S_ISDIR(folder.stat(follow_symlinks=False).st_mode),
            "canonical nested output directory",
        )
        with os.scandir(folder) as rows:
            for row in rows:
                info = row.stat(follow_symlinks=False)
                relative = Path(row.path).relative_to(root).as_posix()
                if stat.S_ISREG(info.st_mode):
                    need(relative in expected and len(files) < 48, "unexpected output file")
                    files.add(relative)
                else:
                    need(
                        stat.S_ISDIR(info.st_mode) and relative == "retained",
                        "unexpected output directory/alias",
                    )
                    dirs.add(relative)
    end = root.stat(follow_symlinks=False)
    need(
        files == set(expected)
        and dirs == {"retained"}
        and root.resolve(strict=True) == root
        and (root_identity.st_dev, root_identity.st_ino) == (end.st_dev, end.st_ino),
        "exact final output population",
    )


def final_fence(capture, output, expected):
    capture.stable()
    output_population(output, expected)
    for path, raw in capture.raw.items():
        if path.is_relative_to(output):
            need(bounded(path, len(raw)) == raw, "late local retained/report bytes")
    capture.stable()
    output_population(output, expected)


def bounded_report(value):
    chunks, total = [], 0
    encoder = json.JSONEncoder(sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
    for text in encoder.iterencode(value):
        raw = text.encode()
        need(total + len(raw) + 1 <= MAX_REPORT, "report allocation bound")
        total += len(raw)
        chunks.append(raw)
    return b"".join(chunks) + b"\n"


def audit(manifest_path, output):
    manifest_path, output = Path(manifest_path).absolute(), Path(output).absolute()
    capture = Capture()
    raw_manifest = capture.take(manifest_path, cap=MAX_MANIFEST)
    manifest = document(raw_manifest)
    closed(manifest, ("schema", "fixture_origin", "attempts", *TOP), "input manifest")
    need(
        manifest["schema"] == INPUT_SCHEMA
        and manifest["fixture_origin"] == "retained_apalache_admission_receipts",
        "closed receiving input profile",
    )
    need(
        type(manifest["attempts"]) is list
        and [x.get("id") for x in manifest["attempts"]] == list(IDS),
        "ordered selected attempts",
    )
    protected, selected, docs_list = {manifest_path.parent}, [], []
    top_raw = {}
    for role in TOP:
        pin = manifest[role]
        closed(pin, ("path", "sha256", "size_bytes"), "top descriptor")
        path = Path(pin["path"])
        protected.add(path.parent)
        top_raw[role] = capture.take(path, pin)
        selected.append(path)
    need(
        sha(top_raw["qualification"]) == QUALIFICATION_ANCHOR,
        "immutable independent qualification anchor",
    )
    q = document(top_raw["qualification"])
    for role, name in TOP.items():
        if role != "qualification":
            need(
                sha(top_raw[role]) == q["artifact_sha256"][name],
                "qualification named top role binding",
            )
    bindings = {"qualification_sha256": sha(top_raw["qualification"])}
    for item in manifest["attempts"]:
        closed(item, ("id", *ROLES), "attempt descriptor population")
        ident, docs = item["id"], {}
        for role in ROLES:
            pin = item[role]
            closed(pin, ("path", "sha256", "size_bytes"), "input descriptor")
            path = Path(pin["path"])
            protected.add(path.parent)
            raw = capture.take(path, pin)
            selected.append(path)
            native_name = (
                DIRECTORIES[ident] + "-command-result.json"
                if role == "command_result"
                else DIRECTORIES[ident] + "/" + LEAVES[role]
            )
            need(
                sha(raw) == q["artifact_sha256"][native_name],
                "qualification named attempt role binding",
            )
            if role in ANCHORS[ident]:
                need(sha(raw) == ANCHORS[ident][role], "immutable independent attempt anchor")
                bindings[ident + "_" + role + "_sha256"] = sha(raw)
            docs[role] = document(raw)
        need(
            set(docs["result"]["audit_sha256"])
            == {
                LEAVES[k]
                for k in (
                    "request_audit",
                    "launch_audit",
                    "lifecycle_audit",
                    "control_audit",
                    "environment_audit",
                )
            }
            and all(
                docs["result"]["audit_sha256"][LEAVES[k]] == item[k]["sha256"]
                for k in (
                    "request_audit",
                    "launch_audit",
                    "lifecycle_audit",
                    "control_audit",
                    "environment_audit",
                )
            ),
            "raw audit commitment closure",
        )
        docs_list.append((ident, docs))
    need(
        len(selected) == len(set(selected)) == 40 and manifest_path not in selected,
        "40 unique selected bodies",
    )
    need(
        not output.exists()
        and output.parent.resolve(strict=True) == output.parent
        and not any(output == parent or output.is_relative_to(parent) for parent in protected),
        "safe fresh output outside inputs",
    )
    summaries = [reconcile_attempt(ident, docs) for ident, docs in docs_list]
    counts = qualification_summary(q, summaries)
    registry = registry_controls(
        top_raw["focused_xml"], top_raw["registry_diagnostic_xml"], top_raw["registry_test_source"]
    )
    controls = mutation_controls(docs_list)
    capture.stable()
    output.mkdir()
    (output / "retained").mkdir()
    retained = []
    for index, (path, raw) in enumerate(tuple(capture.raw.items())):
        destination = output / "retained" / f"{index:02d}-{path.name}"
        with destination.open("xb") as stream:
            stream.write(raw)
        capture.take(destination, cap=len(raw))
        retained.append(
            {
                "original_path": str(path),
                "path": str(destination),
                "relative_path": destination.relative_to(output).as_posix(),
                "sha256": sha(raw),
                "size_bytes": len(raw),
            }
        )
    report = {
        "schema": REPORT_SCHEMA,
        "status": "passed",
        "fixture_origin": manifest["fixture_origin"],
        "manifest_sha256": sha(raw_manifest),
        **bindings,
        **{x: True for x in TRUE},
        **{x: False for x in FALSE},
        **{x: 0 for x in ZERO},
        **counts,
        "selected_file_count": 40,
        "selected_input_bytes": sum(len(capture.raw[p]) for p in selected),
        "attempts": summaries,
        "registry": registry,
        "controls_count": len(controls),
        "controls_refused": len(controls),
        "controls": controls,
        "retained_files": retained,
        "bounds": {
            "max_files": MAX_FILES,
            "max_total_bytes": MAX_TOTAL,
            "max_file_bytes": MAX_FILE,
            "max_manifest_bytes": MAX_MANIFEST,
            "max_report_bytes": MAX_REPORT,
        },
        "scope": "Historical Apalache phase/admission and raw-witness custody; no execution, enforcement, trace replay or registry-native authority",
    }
    raw_report = bounded_report(report)
    report_path = output / REPORT_NAME
    with report_path.open("xb") as stream:
        stream.write(raw_report)
    capture.take(report_path, cap=MAX_REPORT)
    final_fence(capture, output, {REPORT_NAME} | {row["relative_path"] for row in retained})
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = audit(args.manifest, args.output)
    except (
        Refusal,
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        RecursionError,
        KeyError,
        TypeError,
        OverflowError,
        ET.ParseError,
        SyntaxError,
    ) as exc:
        parser.exit(2, "receiving refused: " + str(exc) + "\n")
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "status",
                    "selected_native_phase_count",
                    "accepted_native_phase_count",
                    "selected_lifecycle_count",
                )
            }
        )
    )


if __name__ == "__main__":
    main()
