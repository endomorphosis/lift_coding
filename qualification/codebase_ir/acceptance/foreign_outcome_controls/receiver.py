"""Receive selected historical registry records using only bounded local bytes.

No captured program, tool, owner database, source import or signing key is used.
Recorded native execution and source identities remain historical observations.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import re
import stat
from pathlib import Path

INPUT_SCHEMA = "codebase-ir-foreign-outcome-controls-input@1"
REPORT_SCHEMA = "codebase-ir-foreign-outcome-controls@1"
REPORT_NAME = "foreign_outcome_controls.json"
IDS = ("initial_failed", "accepted")
ROLES = (
    "result",
    "command_result",
    "request_audit",
    "launch_audit",
    "lifecycle_audit",
    "phase_budget_audit",
    "environment_audit",
    "fixtures",
    "scheduler_config",
)
LEAVES = {
    "request_audit": "request-audit.json",
    "launch_audit": "launch-audit.json",
    "lifecycle_audit": "lifecycle-audit.json",
    "phase_budget_audit": "phase-budget-audit.json",
    "environment_audit": "apalache-environment-audit.json",
}
TRUE = (
    "retained_foreign_outcome_custody_conformance",
    "generic_unknown_authority_preserved",
    "exact_typed_payload_preserved",
    "recorded_phase_bindings_reconciled",
    "failed_whole_attempt_preserved",
    "historical_raw_witness_scope_preserved",
    "input_files_unchanged",
)
FALSE = (
    "native_execution_performed",
    "training_executed",
    "current_authority_claimed",
    "owner_database_opened",
    "profile_keys_read",
    "owner_sources_imported",
    "checker_executions_replayed",
    "source_execution_replayed",
    "signature_authentication_performed",
    "process_origin_attested",
    "original_request_custody_qualified",
    "model_check_authority_qualified",
    "proof_authority_qualified",
    "counterexample_replay_qualified",
    "registry_native_success_qualified",
    "resource_enforcement_qualified",
    "hard_aggregate_containment_qualified",
    "whole_install_cancellation_qualified",
    "live_eligibility_qualified",
    "production_acceptance_qualified",
    "native_export_adoption_qualified",
    "throughput_improvement_qualified",
    "model_quality_qualified",
    "output_digest_algorithm_rederived",
)
ZERO = ("runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs")
MAX_FILES, MAX_FILE, MAX_TOTAL = 64, 1024 * 1024, 8 * 1024 * 1024
MAX_MANIFEST, MAX_REPORT = 128 * 1024, 4 * 1024 * 1024
ANCHORS = {
    "qualification": "b54504ba7f9302bc1cb2d2518402162c328e1aa94fedbe47486d0da704a0fe88",
    "source_evolution": "45e1268e50dfab73eaec1e7f9e2f89d5c31a0b8ef3e9df4818c5b65e7393b664",
    "initial_failed.result": "73de6317be6b386b2ca36c52d8e6329a832e64f4a2ab0b28e116a2a5bb4d3cfa",
    "initial_failed.command_result": "78d21a8c3f6c36f52f6eb1769e3bb79643ac77062422ab0b81f456c7b06c0d5c",
    "accepted.result": "74af9ee8403559b964459c628cfe77bdea64568584fd52d6c9d5327e198c84a1",
    "accepted.command_result": "a65ce39dd6ff4bad46cf9e7c5861ce88b7ebeb29435608824d3672886a826533",
}
DIAGNOSTIC = (
    "foreign outcome recorded without authority upgrade; generic conclusions remain non-conclusive"
)
TRACE_NOTE = "counterexample contained no parseable State blocks"
CASE_IDS = ("registry:apalache:true", "registry:apalache:false")
RESULT_FIELDS = {
    "audit_sha256",
    "cases",
    "checks",
    "child_usage",
    "dispatches",
    "elapsed_seconds",
    "launches",
    "lifecycles",
    "native_lifecycles",
    "packaged_native_entries",
    "phase_counts",
    "prelaunch_lifecycles",
    "runtime",
    "schema",
    "scope",
    "shared_after",
    "shared_before",
    "shared_pool_compatibility",
    "source_pins_after",
    "source_pins_before",
    "status",
    "tool_files_after",
    "tool_files_before",
    "tool_selection",
}
CASE_FIELDS = {
    "aggregate_scope_owner",
    "attempt",
    "attempt_digest",
    "case",
    "default_lazy_factory_used",
    "dispatch",
    "elapsed_seconds",
    "factory_restored",
    "operation_timeout_ms",
    "original_outcome",
    "original_return_observer_restored",
    "phase_count",
    "projection_checks",
    "raw_witness",
    "request",
    "request_digest",
    "result",
    "selected_delegate_count",
    "valid",
}
REQUEST_FIELDS = {
    "assumption_ids",
    "bounds",
    "claim_digest",
    "claim_id",
    "declaration_id",
    "logic_family",
    "obligation_digest",
    "obligation_id",
    "payload",
    "query_kind",
    "request_id",
    "requested_backend_id",
    "schema_version",
}
ATTEMPT_FIELDS = {
    "artifact_digests",
    "attempt_id",
    "backend_id",
    "backend_version",
    "bounds",
    "diagnostics",
    "output_digest",
    "request_digest",
    "schema_version",
    "status",
    "usage",
}
GENERIC_FIELDS = {
    "assumption_ids",
    "attempt_digest",
    "authority",
    "backend_id",
    "backend_version",
    "bounds",
    "claim_digest",
    "declaration_id",
    "diagnostics",
    "obligation_digest",
    "obligation_id",
    "output_digest",
    "payload",
    "request_digest",
    "result_id",
    "result_type",
    "schema_version",
    "status",
    "usage",
}
TYPED_FIELDS = {
    "assumptions",
    "authority",
    "backend_id",
    "backend_version",
    "bounds",
    "diagnostics",
    "metadata",
    "reason",
    "result_id",
    "result_type",
    "schema_version",
    "status",
    "translation_ceiling",
    "usage",
    "witness",
}
ARTIFACT_FIELDS = {
    "apalache_config_digest",
    "apalache_config_text",
    "artifact_digest",
    "bounded",
    "bounds",
    "fairness_limitations",
    "interface_version",
    "liveness_properties",
    "losses",
    "model_digest",
    "model_text",
    "module_name",
    "safety_properties",
    "schema_version",
    "source_document_id",
    "source_kind",
    "source_map",
    "tlc_config_digest",
    "tlc_config_text",
    "translator",
    "unbounded_proof",
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
LIFE_FALSE = (
    "cancelled",
    "output_truncated",
    "process_tree_terminated",
    "resource_exhausted",
    "timed_out",
    "unavailable",
    "workspace_limit_exceeded",
)


class Refusal(ValueError):
    """Selected material does not satisfy this closed historical profile."""


def need(condition, label):
    if not condition:
        raise Refusal(label)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def same(left, right):
    return canonical(left) == canonical(right)


def closed(value, fields, label):
    need(type(value) is dict and set(value) == set(fields), label + " closed fields")


def integer(value, low=0, high=2**63 - 1):
    return type(value) is int and low <= value <= high


def number(value, low=0):
    return type(value) in (int, float) and math.isfinite(value) and low <= value <= 1e15


def digest(value):
    return type(value) is str and re.fullmatch("[0-9a-f]{64}", value) is not None


def document(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, "duplicate JSON field")
            result[key] = value
        return result

    def reject(value):
        raise Refusal("non-finite JSON constant: " + value)

    try:
        text = raw.decode("utf-8", errors="strict")
        # Check depth before the JSON parser can allocate recursive containers.
        depth, quoted, escaped = 0, False, False
        for char in text:
            if quoted:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    quoted = False
            elif char == '"':
                quoted = True
            elif char in "[{":
                depth += 1
                need(depth <= 32, "JSON nesting bound")
            elif char in "]}":
                depth -= 1
        value = json.loads(text, object_pairs_hook=pairs, parse_constant=reject)
        pending, count = [(value, 0)], 0
        while pending:
            item, depth = pending.pop()
            count += 1
            need(count <= 100000 and depth <= 32, "JSON value/depth bound")
            if type(item) is dict:
                pending.extend((x, depth + 1) for x in item.values())
                pending.extend((x, depth + 1) for x in item)
            elif type(item) is list:
                pending.extend((x, depth + 1) for x in item)
            elif type(item) is str:
                need(not any(0xD800 <= ord(x) <= 0xDFFF for x in item), "JSON surrogate")
            elif type(item) is int:
                need(abs(item) <= 2**63 - 1, "JSON integer bound")
            elif type(item) is float:
                need(math.isfinite(item), "JSON finite number")
        return value
    except (UnicodeError, json.JSONDecodeError, RecursionError, OverflowError) as exc:
        raise Refusal("bounded JSON input") from exc


def bounded(path, cap):
    path = Path(path)
    need(path.is_absolute() and path.resolve(strict=True) == path, "canonical selected path")
    before = path.stat(follow_symlinks=False)
    need(stat.S_ISREG(before.st_mode) and before.st_size <= cap, "regular selected body/cap")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        start = os.fstat(fd)
        need(stat.S_ISREG(start.st_mode), "selected descriptor regular file")
        need(
            (start.st_dev, start.st_ino) == (before.st_dev, before.st_ino),
            "selected descriptor identity",
        )
        chunks, total = [], 0
        while True:
            chunk = os.read(fd, min(65536, cap + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            need(total <= cap, "selected read cap")
        end = os.fstat(fd)
    finally:
        os.close(fd)

    def signature(s):
        return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns

    need(signature(before) == signature(start) == signature(end), "selected descriptor changed")
    need(
        path.resolve(strict=True) == path
        and signature(path.stat(follow_symlinks=False)) == signature(end),
        "selected path changed",
    )
    raw = b"".join(chunks)
    need(len(raw) == end.st_size, "complete bounded selected body")
    return raw


class Capture:
    def __init__(self):
        self.raw, self.total = {}, 0

    def take(self, path, cap=MAX_FILE):
        path = Path(path)
        if path in self.raw:
            need(len(self.raw[path]) <= cap, "reused body cap")
            return self.raw[path]
        need(len(self.raw) < MAX_FILES, "selected file population cap")
        raw = bounded(path, cap)
        need(self.total + len(raw) <= MAX_TOTAL, "selected byte aggregate cap")
        self.raw[path], self.total = raw, self.total + len(raw)
        return raw

    def stable(self):
        for path, raw in self.raw.items():
            need(bounded(path, len(raw)) == raw, "late selected raw body changed")


def phase(argv):
    need(type(argv) is list and argv and all(type(x) is str for x in argv), "recorded argv")
    if argv[-1] == "-version":
        return "setup"
    if "check" in argv:
        return "model"
    if "version" in argv:
        return "help"
    raise Refusal("unselected phase")


def bounds_record(value):
    closed(
        value, ("max_memory_bytes", "max_output_bytes", "max_steps", "timeout_ms"), "request bounds"
    )
    need(all(integer(x, 1) for x in value.values()), "typed positive request bounds")


def usage_record(value):
    closed(value, ("elapsed_ms", "output_bytes", "peak_memory_bytes", "steps"), "usage")
    need(all(integer(x) for x in value.values()), "typed usage quantities")


def artifact_record(value, expected_steps):
    closed(value, ARTIFACT_FIELDS, "text-bearing artifact")
    need(
        value["schema_version"] == "tla-generated-artifact/v1"
        and value["interface_version"] == "TLABackend@1",
        "artifact schema",
    )
    need(value["bounded"] is True and value["unbounded_proof"] is False, "artifact bounded ceiling")
    for text, pin in (
        ("model_text", "model_digest"),
        ("apalache_config_text", "apalache_config_digest"),
        ("tlc_config_text", "tlc_config_digest"),
    ):
        need(
            type(value[text]) is str and sha(value[text].encode()) == value[pin],
            "artifact exact text digest",
        )
    need(digest(value["artifact_digest"]), "recorded artifact identity")
    closed(
        value["bounds"],
        (
            "default_integer_lower",
            "default_integer_upper",
            "max_actions",
            "max_enum_members",
            "max_integer_span",
            "max_module_bytes",
            "max_predicates",
            "max_steps",
            "max_variables",
            "schema_version",
        ),
        "compile bounds",
    )
    need(
        value["bounds"]["schema_version"] == "tla-compile-bounds/v1"
        and integer(value["bounds"]["max_steps"])
        and value["bounds"]["max_steps"] == expected_steps,
        "historical declared compiler bound",
    )
    need(
        all(integer(v) for k, v in value["bounds"].items() if k != "schema_version"),
        "compile integer fields",
    )
    need(
        value["source_map"]
        == value["losses"]
        == value["liveness_properties"]
        == value["fairness_limitations"]
        == [],
        "historical default artifact metadata",
    )
    need(
        value["safety_properties"] == ["Safety"]
        and value["module_name"] == "BoundedCounter"
        and value["source_kind"] == "state_transition",
        "historical selected artifact profile",
    )
    need(
        same(
            value["translator"], {"id": "state-transition-ir-to-tla", "version": "tla-compiler/v1"}
        ),
        "translator declaration",
    )


def reconcile_case(case, fixture, model_life):
    closed(case, CASE_FIELDS, "foreign case")
    valid = case["valid"]
    need(
        type(valid) is bool and case["case"] == CASE_IDS[0 if valid else 1],
        "ordered selected case identity",
    )
    for key in (
        "default_lazy_factory_used",
        "factory_restored",
        "original_return_observer_restored",
    ):
        need(case[key] is True, "historical factory/observer restoration")
    need(
        case["aggregate_scope_owner"] == "benchmark"
        and integer(case["operation_timeout_ms"])
        and case["operation_timeout_ms"] == 30000,
        "benchmark-owned historical operation scope",
    )
    need(
        integer(case["selected_delegate_count"])
        and case["selected_delegate_count"] == 1
        and integer(case["phase_count"])
        and case["phase_count"] == 3
        and number(case["elapsed_seconds"]),
        "historical case counts",
    )
    request, attempt, result, original = (
        case[x] for x in ("request", "attempt", "result", "original_outcome")
    )
    closed(request, REQUEST_FIELDS, "protocol request")
    closed(attempt, ATTEMPT_FIELDS, "protocol attempt")
    closed(result, GENERIC_FIELDS, "generic result")
    closed(
        original,
        ("artifacts", "interface_version", "receipt", "request_digest", "result"),
        "captured original outcome",
    )
    need(
        request["schema_version"] == "proof-backend-request/v1"
        and request["requested_backend_id"] == "apalache"
        and request["logic_family"] == "state_transition"
        and request["query_kind"] == "satisfiability",
        "selected protocol route",
    )
    bounds_record(request["bounds"])
    request_digest, attempt_digest = sha(canonical(request)), sha(canonical(attempt))
    need(
        request_digest
        == case["request_digest"]
        == original["request_digest"]
        == attempt["request_digest"]
        == result["request_digest"],
        "independent request digest binding",
    )
    need(
        attempt_digest == case["attempt_digest"] == result["attempt_digest"],
        "independent attempt digest binding",
    )
    need(
        attempt["schema_version"] == "proof-backend-attempt/v1"
        and attempt["status"] == "succeeded"
        and result["schema_version"] == "bounded-result/v1"
        and result["status"] == "unknown",
        "generic non-conclusive conversion",
    )
    need(
        attempt["backend_id"] == result["backend_id"] == "apalache"
        and attempt["backend_version"] == result["backend_version"] == "matrix-declared/v1",
        "generic backend declaration",
    )
    need(
        attempt["attempt_id"] == "attempt:apalache:" + request_digest[:24]
        and result["result_id"] == "result:apalache:" + request_digest[:24],
        "generic deterministic recorded IDs",
    )
    need(
        same(request["bounds"], attempt["bounds"]) and same(request["bounds"], result["bounds"]),
        "request/attempt/result exact bounds",
    )
    for key in (
        "claim_digest",
        "declaration_id",
        "obligation_digest",
        "obligation_id",
        "assumption_ids",
    ):
        need(same(request[key], result[key]), "generic original request field binding")
    need(result["result_type"] == request["query_kind"], "generic result type binding")
    for value in (
        request["claim_digest"],
        request["obligation_digest"],
        attempt["output_digest"],
        result["output_digest"],
    ):
        need(digest(value), "recorded protocol digest form")
    need(
        attempt["output_digest"] == result["output_digest"],
        "recorded generic output digest preserved",
    )
    need(attempt["artifact_digests"] == [], "no generic evidence artifacts minted")
    need(
        attempt["diagnostics"] == result["diagnostics"] == [DIAGNOSTIC],
        "mandatory no-upgrade diagnostic",
    )
    usage_record(attempt["usage"])
    usage_record(result["usage"])
    need(
        same(attempt["usage"], result["usage"])
        and all(integer(v) and v == 0 for v in result["usage"].values()),
        "generic usage not inferred from native execution",
    )
    authority = result["authority"]
    closed(
        authority,
        (
            "configuration_digest",
            "evidence_digests",
            "issuer",
            "kind",
            "method",
            "schema_version",
            "scope_digest",
        ),
        "generic declared authority",
    )
    need(
        authority["schema_version"] == "result-authority/v1"
        and authority["issuer"] == "apalache"
        and authority["kind"] == "satisfiability"
        and authority["method"] == "proof-backend-adapter/v1",
        "generic authority declaration profile",
    )
    need(
        authority["scope_digest"] == request_digest
        and digest(authority["configuration_digest"])
        and authority["evidence_digests"] == [],
        "generic authority scope remains descriptive",
    )
    closed(request["payload"], ("artifacts",), "request payload")
    need(same(request["payload"]["artifacts"], fixture), "request equals selected full fixture")
    artifact_record(fixture, 64)
    artifact_without_text = {
        k: v
        for k, v in fixture.items()
        if k not in ("model_text", "apalache_config_text", "tlc_config_text")
    }
    need(
        same(original["artifacts"], artifact_without_text)
        and original["interface_version"] == "ApalacheBackend@1",
        "original outcome exact nontext artifact",
    )
    typed, receipt, payload = original["result"], original["receipt"], result["payload"]
    closed(
        payload,
        ("adapter_return_type", "result", "result_authority", "result_status"),
        "foreign descriptive payload",
    )
    closed(typed, TYPED_FIELDS, "original typed result")
    closed(receipt, RECEIPT_FIELDS, "original bounded receipt")
    need(
        same(payload["result"], typed) and payload["adapter_return_type"] == "ModelCheckOutcome",
        "exact original typed result preservation",
    )
    expected_status = "satisfied" if valid else "violated"
    need(
        typed["status"] == payload["result_status"] == expected_status
        and typed["authority"] == payload["result_authority"] == "model_check",
        "typed status and bounded authority preserved",
    )
    need(
        typed["schema_version"] == "typed-backend-result/v1"
        and typed["result_type"] == "model_check"
        and typed["translation_ceiling"] == "bounded",
        "typed evidence ceiling",
    )
    need(
        typed["backend_id"] == "apalache"
        and typed["backend_version"] == "ApalacheBackend@1"
        and same(typed["bounds"], request["bounds"])
        and same(typed["assumptions"], request["assumption_ids"]),
        "typed original protocol binding",
    )
    need(typed["result_id"] == result["result_id"], "typed result identity preserved")
    usage_record(typed["usage"])
    need(
        receipt["schema_version"] == "tla-model-check-receipt/v1"
        and receipt["tool"] == "apalache"
        and receipt["bounded"] is True
        and receipt["unbounded_proof"] is False,
        "bounded receipt ceiling",
    )
    witness = typed["witness"]
    fields = (
        "artifact_digest",
        "bounded",
        "capability",
        "checked_liveness_properties",
        "checked_safety_properties",
        "configuration_digest",
        "fairness_limitations",
        "model_digest",
        "receipt_id",
        "tool",
        "unbounded_proof",
    ) + (() if valid else ("counterexample",))
    closed(witness, fields, "typed witness")
    need(all(same(witness[k], receipt[k]) for k in fields), "exact original witness receipt fields")
    need(
        receipt["artifact_digest"] == fixture["artifact_digest"] == request["obligation_digest"]
        and receipt["model_digest"] == fixture["model_digest"] == request["claim_digest"]
        and receipt["configuration_digest"] == fixture["apalache_config_digest"],
        "artifact/request/receipt digests",
    )
    need(
        receipt["configuration_text"] == fixture["apalache_config_text"]
        and receipt["command"] == model_life["command"],
        "configuration and actual recorded command",
    )
    need(
        receipt["stdout"] == model_life["stdout"]
        and receipt["stderr"] == model_life["stderr"]
        and receipt["returncode"] == model_life["returncode"]
        and integer(receipt["returncode"]),
        "original native output preserved",
    )
    need(
        receipt["status"] == ("passed" if valid else "counterexample")
        and receipt["returncode"] == (0 if valid else 12),
        "original tool classification",
    )
    need(
        receipt["jvm_available"] is True
        and receipt["output_truncated"] is False
        and number(receipt["timeout_seconds"], 0.001)
        and integer(receipt["elapsed_ms"]),
        "original receipt measurements",
    )
    capability = receipt["capability"]
    closed(
        capability,
        (
            "backend_version",
            "checks_fairness",
            "checks_liveness",
            "checks_safety",
            "executable_candidates",
            "finite_trace_only",
            "limitations",
            "max_declared_steps",
            "requires_jvm",
            "schema_version",
            "tool",
        ),
        "historical capability",
    )
    need(
        capability["checks_safety"] is True
        and capability["checks_liveness"] is False
        and capability["checks_fairness"] is False
        and capability["finite_trace_only"] is True
        and capability["requires_jvm"] is True,
        "retained Apalache capability limitations",
    )
    need(
        capability["schema_version"] == "tla-model-checker-capability/v1"
        and capability["backend_version"] == "ApalacheBackend@1"
        and capability["tool"] == "apalache"
        and integer(capability["max_declared_steps"])
        and capability["max_declared_steps"] == 200,
        "historical declared capability identity",
    )
    need(
        capability["executable_candidates"] == ["apalache-mc", "apalache"]
        and type(capability["limitations"]) is list
        and capability["limitations"],
        "declared tool limitations",
    )
    metadata = typed["metadata"]
    closed(metadata, ("executable", "jvm_available", "tool_version"), "typed tool metadata")
    need(
        metadata["jvm_available"] is True
        and metadata["executable"] == receipt["executable"]
        and metadata["tool_version"] == receipt["tool_version"],
        "original tool metadata bound to receipt",
    )
    need(
        receipt["checked_safety_properties"] == ["Safety"]
        and receipt["checked_liveness_properties"] == [],
        "no checked liveness",
    )
    need(
        type(receipt["fairness_limitations"]) is list and receipt["fairness_limitations"],
        "explicit bounded limitations",
    )
    projection = {
        "generic_attempt_status": "succeeded",
        "generic_result_status": "unknown",
        "generic_theorem_authority": False,
        "original_authority": "model_check",
        "original_result_status": expected_status,
        "payload_exact_original_result": True,
    }
    need(same(case["projection_checks"], projection), "independent projection checks")
    if valid:
        need(
            receipt["counterexample"] is None and case["raw_witness"] is None,
            "valid case no counterexample",
        )
    else:
        ce = receipt["counterexample"]
        closed(
            ce,
            ("raw", "replay_notes", "replayed", "schema_version", "source", "states"),
            "historical raw counterexample",
        )
        need(
            ce["schema_version"] == "tla-counterexample/v1"
            and ce["source"] == "checker_counterexample_file"
            and ce["states"] == []
            and ce["replayed"] is True
            and ce["replay_notes"] == [TRACE_NOTE],
            "historical zero-state legacy replay observation",
        )
        need(
            type(ce["raw"]) is str
            and model_life["output_files"].get("apalache-run/violation.tla") == ce["raw"],
            "raw counterexample exact retained output",
        )
        values = re.findall(r"^State[0-9]+\s*==\s*n\s*=\s*([0-9]+)\s*$", ce["raw"], re.MULTILINE)
        need(values == ["0", "1", "2"], "raw witness values descriptive only")
        need(
            same(
                case["raw_witness"],
                {
                    "parsed_state_count": 0,
                    "path": "apalache-run/violation.tla",
                    "raw_state_values": values,
                    "scope": "Original raw Apalache file retained; no structural replay attestation",
                    "sha256": sha(ce["raw"].encode()),
                },
            ),
            "raw-only witness descriptor",
        )
        need(TRACE_NOTE in typed["diagnostics"], "raw-only diagnostic retained")
    return {
        "case": case["case"],
        "valid": valid,
        "generic_attempt_status": "succeeded",
        "generic_result_status": "unknown",
        "typed_result_status": expected_status,
        "typed_authority": "model_check",
        "request_digest": request_digest,
        "attempt_digest": attempt_digest,
        "recorded_output_digest": result["output_digest"],
        "output_digest_algorithm_rederived": False,
        "parsed_state_count": 0,
        "semantic_replay_qualified": False,
        "complete_recorded_payload_preserved": True,
    }


def reconcile_attempt(ident, docs):
    need(ident in IDS, "selected attempt identity")
    failed = ident == "initial_failed"
    result, command = docs["result"], docs["command_result"]
    closed(result, RESULT_FIELDS | ({"error"} if failed else set()), "native attempt")
    need(
        result["schema"] == "registry-foreign-outcome-benchmark@1"
        and result["status"] == ("failed" if failed else "passed"),
        "historical whole attempt status",
    )
    count = 3 if failed else 6
    for field in ("launches", "lifecycles", "native_lifecycles"):
        need(
            integer(result[field]) and result[field] == count, "exact historical native population"
        )
    need(
        integer(result["prelaunch_lifecycles"]) and result["prelaunch_lifecycles"] == 0,
        "no omitted prelaunch observations",
    )
    need(
        same(
            result["phase_counts"], {"help": count // 3, "model": count // 3, "setup": count // 3}
        ),
        "ordered phase populations",
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
        "native command result",
    )
    need(
        integer(command["returncode"])
        and command["returncode"] == int(failed)
        and number(command["seconds"]),
        "whole wrapper attempt classification",
    )
    need(
        same(command["before"], command["after"])
        and same(result["source_pins_before"], result["source_pins_after"])
        and same(result["tool_files_before"], result["tool_files_after"]),
        "historical source/tool observations stable",
    )
    need(
        type(command["before"]) is dict
        and command["before"]
        and all(digest(v) for v in command["before"].values()),
        "historical source pins metadata only",
    )
    checks = {
        "java_selection_environment_restored",
        "owned_work_drained",
        "selected_tool_files_unchanged",
        "shared_config_unchanged",
        "sources_stable",
    }
    if not failed:
        checks |= {
            "exact_foreign_typed_payload",
            "exact_two_serial_cases",
            "expected_real_phases",
            "native_environments_sanitized",
            "no_generic_authority_promotion",
            "observer_and_factory_restored",
            "owned_apalache_jvm_environments",
        }
    closed(result["checks"], checks, "producer checks")
    need(all(v is True for v in result["checks"].values()), "producer checks retained")
    scope = result["scope"]
    closed(
        scope,
        (
            "aggregate_scope_owner",
            "default_registry_aggregate_budget_claim",
            "factory_override",
            "hard_aggregate_resource_guarantee",
            "installation",
            "jvm_probe_injected",
            "native_transport_injected",
            "new_proof_cache_or_replay",
            "raw_counterexample_only",
            "registry_route",
            "throughput_scaling_claim",
            "tlc_execution",
        ),
        "native historical scope",
    )
    need(
        scope["aggregate_scope_owner"] == "benchmark"
        and scope["registry_route"] == "default_backend_registry/LazyMatrixProofBackend"
        and scope["raw_counterexample_only"] is True,
        "historical registry route scope",
    )
    need(
        all(
            scope[k] is False
            for k in (
                "default_registry_aggregate_budget_claim",
                "hard_aggregate_resource_guarantee",
                "installation",
                "jvm_probe_injected",
                "native_transport_injected",
                "new_proof_cache_or_replay",
                "throughput_scaling_claim",
                "tlc_execution",
            )
        ),
        "no new runtime/authority/resource scope",
    )
    before, after = result["shared_before"], result["shared_after"]
    need(
        same(before["config"], after["config"])
        and same(after["config"], docs["scheduler_config"]["config"]),
        "recorded shared config unchanged",
    )
    for key in ("owned_active_leases", "owned_waiting_requests"):
        need(integer(after[key]) and after[key] == 0, "recorded owned resources drained")
    requests, launches, lives, budgets, environments = (
        docs[x]
        for x in (
            "request_audit",
            "launch_audit",
            "lifecycle_audit",
            "phase_budget_audit",
            "environment_audit",
        )
    )
    need(
        all(type(x) is list and len(x) == count for x in (requests, launches, lives, budgets)),
        "complete selected phase audit rows",
    )
    need(
        type(environments) is list and len(environments) == count // 3 * 2,
        "complete selected JVM environment rows",
    )
    need(
        type(docs["fixtures"]) is dict and set(docs["fixtures"]) == {"false", "true"},
        "two historical fixtures",
    )
    for fixture in docs["fixtures"].values():
        artifact_record(fixture, 3 if failed else 64)
    summaries, models, jvm_index = [], {}, 0
    for index, (request, launch, life, budget) in enumerate(
        zip(requests, launches, lives, budgets, strict=True)
    ):
        ph = ("setup", "model", "help")[index % 3]
        label = CASE_IDS[index // 3]
        expected_case = label + ":constructor" if ph == "setup" else label
        need(
            request["case"] == launch["case"] == life["case"] == expected_case
            and budget["case"] == label
            and budget["phase"] == ph
            and phase(request["argv"]) == ph,
            "ordered case/phase audit identity",
        )
        native = life["result"]
        need(
            same(request["argv"], native["command"])
            and same(request["argv"], life["request"]["argv"])
            and launch["argv"][-len(request["argv"]) :] == request["argv"],
            "logical/native/actual command binding",
        )
        need(
            integer(native["returncode"])
            and native["returncode"] == (12 if ph == "model" and index // 3 == 1 else 0),
            "historical phase outcome",
        )
        need(
            native["workspace_cleaned"] is True and all(native[k] is False for k in LIFE_FALSE),
            "historical native cleanup and no interruption",
        )
        need(
            number(native["elapsed_seconds"])
            and type(native["stdout"]) is str
            and type(native["stderr"]) is str,
            "native phase output and timing",
        )
        need(
            life["request"]["stdin_is_empty"] is True
            and life["request"]["java_option_environment_absent"] is True,
            "recorded isolated Java request",
        )
        need(
            number(budget["deadline"])
            and number(budget["at_monotonic"])
            and number(budget["remaining_seconds"], 0.001)
            and number(budget["request_timeout_seconds"], 0.001),
            "historical phase deadline quantities",
        )
        need(
            abs(budget["deadline"] - budget["at_monotonic"] - budget["remaining_seconds"]) < 0.02
            and budget["request_timeout_seconds"] <= budget["remaining_seconds"] + 0.02,
            "benchmark-owned bounded phase deadlines",
        )
        limits = request["limits"]
        need(
            number(limits["timeout_seconds"], 0.001)
            and limits["timeout_seconds"]
            == budget["request_timeout_seconds"]
            == life["request"]["timeout_seconds"],
            "recorded timeout propagation",
        )
        need(
            type(launch["owned_leases"]) is list and len(launch["owned_leases"]) == 1,
            "one recorded owned child lease",
        )
        lease = launch["owned_leases"][0]
        need(
            lease["lease_id"] == launch["launch_lease_id"]
            and lease["cancelled"] is False
            and lease["parent_lease_id"] is None,
            "recorded owned root lease identity",
        )
        wanted = {
            "cpu_slots": 1,
            "memory_mb": 256 if ph == "setup" else 512,
            "child_process_slots": 1 if ph == "setup" else 3,
        }
        need(
            all(integer(lease[k]) and lease[k] == v for k, v in wanted.items()),
            "recorded native lease profile",
        )
        allocation = launch["root_allocations"]
        need(
            all(integer(allocation[k]) and allocation[k] >= v for k, v in wanted.items()),
            "owned allocation lower bound; foreign leases not authenticated",
        )
        if ph == "model":
            fixture = docs["fixtures"]["true" if index // 3 == 0 else "false"]
            need(
                "--length=64" in request["argv"] and "--length=3" not in request["argv"],
                "actual historical decoder default64 command",
            )
            need(
                request["input_sha256"].get("BoundedCounter.tla") == fixture["model_digest"]
                and request["input_sha256"].get("apalache.cfg")
                == fixture["apalache_config_digest"],
                "selected model/configuration native inputs",
            )
            need(
                request["input_bytes"].get("BoundedCounter.tla")
                == len(fixture["model_text"].encode())
                and request["input_bytes"].get("apalache.cfg")
                == len(fixture["apalache_config_text"].encode()),
                "exact model/configuration input sizes",
            )
            models[label] = native
        if ph != "setup":
            env = environments[jvm_index]
            jvm_index += 1
            need(
                env["case"] == label
                and env["phase"] == ph
                and env["foreign_configuration_environment_absent"] is True
                and env["private_home_and_tmpdir"] is True,
                "recorded private Apalache environment",
            )
            need(
                "-Xmx256m" in env["jvm_args"].split()
                and "-XX:ActiveProcessorCount=1" in env["jvm_args"].split()
                and env["jvm_gc_args"] == "-XX:+UseSerialGC",
                "recorded managed JVM profile",
            )
        summaries.append(
            {
                "case": label,
                "phase": ph,
                "returncode": native["returncode"],
                "command": native["command"],
                "workspace_cleaned": True,
                "recorded_owned_lease_id": launch["launch_lease_id"],
            }
        )
    if failed:
        need(
            result["cases"] == []
            and type(result["error"]) is str
            and "Apalache logical/actual command differs from reviewed argv" in result["error"],
            "whole failed attempt has no accepted case",
        )
        case_summaries = []
    else:
        need(
            type(result["cases"]) is list
            and [c.get("case") for c in result["cases"]] == list(CASE_IDS),
            "complete two accepted cases",
        )
        case_summaries = [
            reconcile_case(c, docs["fixtures"]["true" if i == 0 else "false"], models[c["case"]])
            for i, c in enumerate(result["cases"])
        ]
    return {
        "attempt": ident,
        "status": result["status"],
        "accepted": not failed,
        "recorded_native_phase_count": count,
        "accepted_case_count": len(case_summaries),
        "phases": summaries,
        "cases": case_summaries,
        "declared_artifact_steps": 3 if failed else 64,
        "actual_model_command_steps": 64,
        "whole_attempt_failure": result.get("error"),
        "benchmark_owned_operation_budget": True,
        "default_registry_aggregate_budget_claim": False,
        "historical_owned_resource_drain": True,
        "resource_enforcement_qualified": False,
    }


def qualification_summary(q, summaries):
    closed(
        q,
        (
            "additional_suite_counts",
            "artifact_sha256",
            "checks",
            "deselected_legacy_native_tests",
            "focused_attempts",
            "focused_tests",
            "initial_native_attempt",
            "native_phases",
            "native_seconds",
            "native_success_cases",
            "native_wrapper_seconds",
            "new_cache_replay",
            "new_codebase_smt_execution",
            "new_foreign_tests",
            "preservation",
            "production_tasks_closed",
            "recorded_at_utc",
            "schema",
            "selected_test_cases",
            "selected_tests",
            "status",
            "test_counts_summed",
            "total_native_phases_across_attempts",
        ),
        "qualification",
    )
    need(
        q["schema"] == "registry-foreign-outcome-qualification@1"
        and q["status"] == "passed_partial_scope",
        "selected qualification profile",
    )
    for key, value in (
        ("selected_tests", 1914),
        ("new_foreign_tests", 82),
        ("focused_tests", 363),
        ("native_success_cases", 2),
        ("native_phases", 6),
        ("total_native_phases_across_attempts", 9),
        ("deselected_legacy_native_tests", 15),
    ):
        need(integer(q[key]) and q[key] == value, "separate historical qualification counts")
    need(
        q["test_counts_summed"] is False
        and q["new_cache_replay"] is False
        and q["new_codebase_smt_execution"] is False
        and q["production_tasks_closed"] == [],
        "qualification remains partial and counts not summed",
    )
    need(
        type(q["checks"]) is dict and all(v is True for v in q["checks"].values()),
        "qualification producer checks",
    )
    need(
        integer(q["initial_native_attempt"]["native_phases"])
        and q["initial_native_attempt"]["native_phases"] == 3
        and q["initial_native_attempt"]["accepted"] is False
        and q["initial_native_attempt"]["status"] == "failed"
        and q["initial_native_attempt"]["returned_case_serialized"] is False,
        "retained failed initial attempt declaration",
    )
    need(
        sum(x["recorded_native_phase_count"] for x in summaries) == 9
        and summaries[0]["accepted"] is False
        and summaries[1]["accepted"] is True,
        "nine historical phases, six accepted",
    )
    need(
        type(q["selected_test_cases"]) is list
        and len(q["selected_test_cases"]) == len(set(q["selected_test_cases"])) == 1914
        and all(type(x) is str for x in q["selected_test_cases"]),
        "historical distinct selected test population",
    )
    preservation = q["preservation"]
    need(
        integer(preservation["prior_artifacts"])
        and preservation["prior_artifacts"] == 1341
        and integer(preservation["prior_qualifications"])
        and preservation["prior_qualifications"] == 16,
        "producer preservation declaration, not nested body audit",
    )
    return {
        "selected_test_count": 1914,
        "new_foreign_test_count": 82,
        "focused_test_count": 363,
        "counts_additive": False,
        "legacy_native_tests_deselected": 15,
        "accepted_native_phase_count": 6,
        "failed_native_phase_count": 3,
        "historical_native_phase_count": 9,
        "producer_declared_preserved_prior_artifacts": 1341,
        "producer_declared_preserved_prior_qualifications": 16,
        "nested_preservation_bodies_independently_opened": False,
        "production_tasks_closed": [],
    }


def mutation_controls(accepted):
    faults = (
        (
            "generic positive conclusion",
            lambda d: d["result"]["cases"][0]["result"].update(status="satisfiable"),
        ),
        (
            "generic authority promoted",
            lambda d: d["result"]["cases"][0]["result"]["authority"].update(kind="theorem_proof"),
        ),
        (
            "typed status lost",
            lambda d: d["result"]["cases"][0]["result"]["payload"].update(result_status="proved"),
        ),
        (
            "payload original result altered",
            lambda d: d["result"]["cases"][0]["result"]["payload"]["result"].update(
                reason="invented"
            ),
        ),
        (
            "original request identity changed",
            lambda d: d["result"]["cases"][0]["request"].update(declaration_id="other"),
        ),
        (
            "attempt identity changed",
            lambda d: d["result"]["cases"][0]["attempt"].update(attempt_id="other"),
        ),
        (
            "generic output digest unbound",
            lambda d: d["result"]["cases"][0]["result"].update(output_digest="0" * 64),
        ),
        (
            "upgrade diagnostic omitted",
            lambda d: d["result"]["cases"][0]["result"].update(diagnostics=[]),
        ),
        (
            "generic usage inferred",
            lambda d: d["result"]["cases"][0]["result"]["usage"].update(elapsed_ms=1),
        ),
        (
            "historical raw trace manufactured states",
            lambda d: d["result"]["cases"][1]["original_outcome"]["receipt"][
                "counterexample"
            ].update(states=[{"index": 1}]),
        ),
        (
            "raw witness digest forged",
            lambda d: d["result"]["cases"][1]["raw_witness"].update(sha256="0" * 64),
        ),
        (
            "default64 declared as three",
            lambda d: d["fixtures"]["true"]["bounds"].update(max_steps=3),
        ),
        ("missing accepted case", lambda d: d["result"]["cases"].pop()),
        ("Boolean native count", lambda d: d["result"].update(prelaunch_lifecycles=False)),
        (
            "Boolean native returncode",
            lambda d: d["lifecycle_audit"][1]["result"].update(returncode=False),
        ),
        ("owned drain leaked", lambda d: d["result"]["shared_after"].update(owned_active_leases=1)),
        ("phase command drift", lambda d: d["launch_audit"][1]["argv"].append("--length=3")),
        (
            "deadline not propagated",
            lambda d: d["phase_budget_audit"][1].update(request_timeout_seconds=100),
        ),
        (
            "native authority scope forged",
            lambda d: d["result"]["scope"].update(default_registry_aggregate_budget_claim=True),
        ),
        ("unknown native authority field", lambda d: d["result"].update(current_authority=True)),
    )
    controls = []
    for label, mutate in faults:
        changed = copy.deepcopy(accepted)
        mutate(changed)
        changed["result"]["audit_sha256"] = {
            leaf: sha(canonical(changed[role])) for role, leaf in LEAVES.items()
        }
        try:
            reconcile_attempt("accepted", changed)
        except (Refusal, KeyError, TypeError, ValueError) as exc:
            controls.append(
                {
                    "control": label,
                    "refused": True,
                    "reason": str(exc),
                    "recorded_audit_digests_recomputed": True,
                    "original_selected_bodies_unchanged": True,
                }
            )
        else:
            raise Refusal("unrefused authored control: " + label)
    return controls


def population(output, expected):
    need(
        output.is_absolute()
        and output.resolve(strict=True) == output
        and stat.S_ISDIR(output.stat(follow_symlinks=False).st_mode),
        "canonical output directory",
    )
    identity = output.stat(follow_symlinks=False)
    files, dirs = set(), set()
    for folder in (output, output / "retained"):
        need(
            folder.resolve(strict=True) == folder
            and stat.S_ISDIR(folder.stat(follow_symlinks=False).st_mode),
            "canonical retained directory",
        )
        with os.scandir(folder) as rows:
            for row in rows:
                info = row.stat(follow_symlinks=False)
                relative = Path(row.path).relative_to(output).as_posix()
                if stat.S_ISREG(info.st_mode):
                    need(relative in expected, "unexpected output body")
                    files.add(relative)
                else:
                    need(
                        stat.S_ISDIR(info.st_mode) and relative == "retained",
                        "unexpected output directory or alias",
                    )
                    dirs.add(relative)
    end = output.stat(follow_symlinks=False)
    need(
        files == set(expected)
        and dirs == {"retained"}
        and (identity.st_dev, identity.st_ino) == (end.st_dev, end.st_ino),
        "exact final output population",
    )


def final_fence(capture, output, expected):
    capture.stable()
    population(output, expected)
    capture.stable()
    population(output, expected)


def report_bytes(value):
    chunks, total = [], 0
    for text in json.JSONEncoder(
        sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False
    ).iterencode(value):
        raw = text.encode("ascii")
        total += len(raw)
        need(total + 1 <= MAX_REPORT, "report serialization cap")
        chunks.append(raw)
    return b"".join(chunks) + b"\n"


def audit(manifest_path, output):
    manifest_path, output = Path(manifest_path).absolute(), Path(output).absolute()
    capture = Capture()
    manifest_raw = capture.take(manifest_path, MAX_MANIFEST)
    manifest = document(manifest_raw)
    closed(
        manifest,
        ("schema", "fixture_origin", "qualification", "source_evolution", "attempts"),
        "input manifest",
    )
    need(
        manifest["schema"] == INPUT_SCHEMA
        and manifest["fixture_origin"] == "retained_registry_foreign_outcome_receipts",
        "closed historical input profile",
    )
    need(
        type(manifest["attempts"]) is list
        and [x.get("id") for x in manifest["attempts"]] == list(IDS),
        "ordered selected attempt input",
    )
    slots = [(key, manifest[key]) for key in ("qualification", "source_evolution")]
    for attempt in manifest["attempts"]:
        closed(attempt, ("id", *ROLES), "selected attempt input")
        slots.extend((attempt["id"] + "." + role, attempt[role]) for role in ROLES)
    docs, selections, selected_paths = {}, [], set()
    for role, pin in slots:
        closed(pin, ("path", "sha256", "size"), "selected descriptor")
        need(
            type(pin["path"]) is str
            and digest(pin["sha256"])
            and integer(pin["size"], 1, MAX_FILE),
            "typed selected descriptor",
        )
        path = Path(pin["path"])
        need(
            path.is_absolute() and path not in selected_paths and path != manifest_path,
            "unique selected absolute bodies",
        )
        raw = capture.take(path)
        need(
            len(raw) == pin["size"] and sha(raw) == pin["sha256"], "exact selected body descriptor"
        )
        if role in ANCHORS:
            need(pin["sha256"] == ANCHORS[role], "independently selected immutable anchor")
        docs[role] = document(raw)
        selected_paths.add(path)
        selections.append({"role": role, "path": str(path), "sha256": sha(raw), "size": len(raw)})
    need(len(selections) == 20, "exact selected input population")
    need(
        not output.exists() and output.parent.resolve(strict=True) == output.parent,
        "fresh output under canonical parent",
    )
    need(
        not any(
            output == p.parent or output.is_relative_to(p.parent) or p.is_relative_to(output)
            for p in selected_paths | {manifest_path}
        ),
        "output separated from selected input directories",
    )
    capture.stable()
    attempts = []
    for ident in IDS:
        packet = {role: docs[ident + "." + role] for role in ROLES}
        for role, leaf in LEAVES.items():
            need(
                packet["result"]["audit_sha256"].get(leaf)
                == next(x["sha256"] for x in selections if x["role"] == ident + "." + role),
                "selected raw audit binding",
            )
        attempts.append(reconcile_attempt(ident, packet))
    q = qualification_summary(docs["qualification"], attempts)
    for role, row in zip(("initial_failed", "accepted"), manifest["attempts"], strict=True):
        prefix, directory = (
            ("native", "native")
            if role == "initial_failed"
            else ("native-selected", "native-selected")
        )
        pins = docs["qualification"]["artifact_sha256"]
        for name in ROLES:
            leaf = (
                prefix + "-command-result.json"
                if name == "command_result"
                else directory
                + "/"
                + {
                    "result": "result.json",
                    "fixtures": "fixtures.json",
                    "scheduler_config": "saved-scheduler-config.json",
                    **LEAVES,
                }[name]
            )
            need(pins[leaf] == row[name]["sha256"], "qualification exact selected role binding")
    need(
        docs["qualification"]["artifact_sha256"]["source-evolution.json"]
        == manifest["source_evolution"]["sha256"],
        "qualification source evolution metadata binding",
    )
    evolution = docs["source_evolution"]
    need(type(evolution) is dict and len(evolution) == 2, "selected source evolution metadata")
    for path, value in evolution.items():
        closed(
            value,
            (
                "after_sha256",
                "after_snapshot",
                "before_sha256",
                "before_snapshot",
                "diff",
                "diff_sha256",
                "kind",
            ),
            "source evolution row",
        )
        need(
            type(path) is str
            and all(digest(value[k]) for k in ("before_sha256", "after_sha256", "diff_sha256")),
            "source evolution digest declarations",
        )
    need(
        {v["kind"] for v in evolution.values()} == {"production", "existing_test"},
        "two historical source evolution roles",
    )
    controls = mutation_controls({role: docs["accepted." + role] for role in ROLES})
    capture.stable()
    output.mkdir()
    retained = output / "retained"
    retained.mkdir()
    expected = {REPORT_NAME, "retained/input_manifest.json"}
    local_manifest = retained / "input_manifest.json"
    local_manifest.write_bytes(manifest_raw)
    capture.take(local_manifest, MAX_MANIFEST)
    for index, row in enumerate(selections):
        relative = f"retained/{index:02d}-{row['role']}.json"
        local = output / relative
        local.write_bytes(capture.raw[Path(row["path"])])
        capture.take(local)
        row["retained_copy"] = {"path": str(local), "sha256": row["sha256"], "size": row["size"]}
        expected.add(relative)
    report = {
        "schema": REPORT_SCHEMA,
        "workflow": "foreign_outcome_controls",
        "status": "passed",
        "qualified": True,
        "fixture_origin": manifest["fixture_origin"],
        "manifest_sha256": sha(manifest_raw),
        **{key: True for key in TRUE},
        **{key: False for key in FALSE},
        **{key: 0 for key in ZERO},
        "qualification_sha256": manifest["qualification"]["sha256"],
        "source_evolution_sha256": manifest["source_evolution"]["sha256"],
        "initial_result_sha256": manifest["attempts"][0]["result"]["sha256"],
        "initial_command_result_sha256": manifest["attempts"][0]["command_result"]["sha256"],
        "accepted_result_sha256": manifest["attempts"][1]["result"]["sha256"],
        "accepted_command_result_sha256": manifest["attempts"][1]["command_result"]["sha256"],
        "selected_file_count": 20,
        "selected_input_bytes": sum(x["size"] for x in selections),
        "selected_files": selections,
        "attempts": attempts,
        "qualification": q,
        "source_evolution_metadata": evolution,
        "controls": controls,
        "production_tasks_closed": [],
        "limitations": [
            "Pure stdlib selected-byte custody; native executables, databases, keys and owner sources are never opened or imported.",
            "Original typed model-check evidence remains historical, bounded and non-authoritative for this receiver.",
            "Inherited generic output digests are bound and preserved; their producer algorithm is not independently rederived.",
            "Raw State0/1/2 values are descriptive evidence; the historical empty parsed state list and legacy true replay flag establish no structural or semantic replay.",
            "Failed whole attempt has three phases and no accepted cases; accepted whole attempt has six phases. Focused and joined producer tests overlap.",
            "Earlier artifact preservation counts and source/tool pins are declarations in selected records; their nested bodies are outside this receiver's closure.",
            "The benchmark owned the operation deadline; this historical increment does not qualify default registry setup budgets, hard resource containment, concurrency throughput or production task closure.",
        ],
        "custody": {
            "retained_manifest": {
                "path": str(local_manifest),
                "sha256": sha(manifest_raw),
                "size": len(manifest_raw),
            },
            "raw_bodies_reread": True,
            "exact_output_population": True,
        },
        "limits": {
            "max_selected_files": MAX_FILES,
            "max_body_bytes": MAX_FILE,
            "max_aggregate_bytes": MAX_TOTAL,
            "max_manifest_bytes": MAX_MANIFEST,
            "max_report_bytes": MAX_REPORT,
            "max_json_depth": 32,
            "max_json_values": 100000,
        },
    }
    target = output / REPORT_NAME
    target.write_bytes(report_bytes(report))
    capture.take(target, MAX_REPORT)
    final_fence(capture, output, expected)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = audit(args.manifest, args.output)
    except (Refusal, OSError, ValueError, KeyError, TypeError) as exc:
        print("refused: " + str(exc))
        return 1
    print(
        json.dumps(
            {
                "status": report["status"],
                "report": str(args.output / REPORT_NAME),
                "selected_file_count": report["selected_file_count"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
