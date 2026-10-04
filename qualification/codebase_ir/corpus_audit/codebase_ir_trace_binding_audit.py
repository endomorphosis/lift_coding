"""Audit retained scalar trace and declared symbol bindings without executing a checker.

The parser accepts only the documented StateN scalar assignment format. It does
not evaluate TLA expressions, transitions, invariants or the meaning of source IDs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import stat
import xml.etree.ElementTree as ET
from pathlib import Path

INPUT_SCHEMA = "codebase-ir-trace-binding-audit-input@1"
REPORT_SCHEMA = "codebase-ir-trace-binding-audit@1"
REPORT_NAME = "trace_binding_audit.json"
ROLES = (
    "qualification",
    "native_result",
    "native_lifecycle",
    "native_fixtures",
    "native_request",
    "preflight_initial",
    "preflight_selected",
    "historical_native_result",
    "focused_initial_result",
    "focused_initial_junit",
    "focused_initial_log",
    "focused_selected_result",
    "focused_selected_junit",
    "joined_selected_result",
    "joined_selected_junit",
    "source_evolution",
    "report",
)
TRUE = (
    "retained_trace_binding_accounting_produced",
    "scalar_assignment_projection_rederived",
    "original_labels_and_positive_ordinals_preserved",
    "declared_source_symbol_bindings_reconciled",
    "historical_zero_state_gap_preserved",
    "failed_duplicate_diagnostic_trial_preserved",
    "complete_selected_test_population_reconciled",
    "input_files_unchanged",
)
FALSE = (
    "native_execution_performed",
    "training_executed",
    "current_authority_claimed",
    "owner_sources_imported",
    "owner_database_opened",
    "profile_keys_read",
    "git_executable_invoked",
    "native_parser_imported",
    "source_execution_performed",
    "model_execution_performed",
    "checker_execution_reperformed",
    "arbitrary_tla_expression_evaluated",
    "transition_semantics_verified",
    "invariant_semantics_verified",
    "source_map_semantics_verified",
    "semantic_counterexample_replay_qualified",
    "solver_replay_performed",
    "liveness_verified",
    "fairness_verified",
    "theorem_authority_qualified",
    "generic_authority_promoted",
    "process_origin_attested",
    "resource_enforcement_qualified",
    "producer_authentication_verified",
    "whole_repository_coverage",
    "production_default_activated",
    "historical_receipts_rewritten",
    "unmapped_negative_original_mapping_replayed",
    "test_counts_additive",
)
ZERO = ("runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs")
MIB = 1024 * 1024
MAX_BODY, MAX_TOTAL, MAX_MANIFEST, MAX_REPORT, MAX_FILES = MIB, 8 * MIB, 128 * 1024, 4 * MIB, 64
ANCHORS = {
    "qualification": "6c47ec8f7238dc502ca3b2c21d048f375cf785c4f737eaa32b311b05750280e5",
    "native_result": "28d8a2e9fbe29c6e41a38f2518aee1af143ee9190e2a0b73d1175c51afb678b5",
    "historical_native_result": "95e1595ece08ec69d9d83ff84931fb7d64638a93dddb2b3eda34be57d18a233b",
}
TRACE_FIELDS = {"raw", "replay_notes", "replayed", "schema_version", "source", "states"}
STATE_FIELDS = {"assignments", "index", "label", "raw", "schema_version"}
MAP_FIELDS = {"line_hint", "role", "schema_version", "source_id", "source_kind", "tla_symbol"}
CE_SCHEMA = "tla-counterexample/v1"
STRUCTURAL_NOTE = (
    "structural source-symbol mapping only; transitions and invariants were not evaluated"
)
FAILED_ID = (
    "tests.unit.logic.backends.test_tla_counterexample_replay",
    "test_long_source_identity_keeps_truthful_replay_and_bounded_v2_notes",
)

# Closed selected protocol generations; no owner implementation is imported.
NATIVE_FIELDS = {
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
PREFLIGHT_FIELDS = {
    "benchmark_sha256",
    "decoder_cases",
    "expected_native_phases",
    "expected_phase_counts",
    "helper_sha256",
    "native_v2_execution",
    "negative_controls",
    "packaged_native_entries",
    "parsed_trace",
    "registry_discovery_loaded_delegates",
    "requests",
    "retained_trace_before",
    "retained_trace_raw_sha256",
    "retained_trace_source",
    "retained_trace_source_sha256",
    "scope",
    "selection",
    "semantic_counterexample_replay_claim",
    "source_count",
    "source_map_structural_check",
    "source_pins",
    "source_pins_unchanged",
    "status",
    "structurally_replayed_trace",
    "tool_files",
    "trace_checks",
}
QUALIFICATION_FIELDS = {
    "artifact_sha256",
    "checks",
    "deselected_legacy_native_tests",
    "focused_tests",
    "native_phases",
    "native_seconds",
    "native_success_cases",
    "native_wrapper_seconds",
    "new_cache_replay",
    "new_codebase_smt_execution",
    "new_counterexample_tests",
    "preservation",
    "production_tasks_closed",
    "recorded_at_utc",
    "schema",
    "selected_test_cases",
    "selected_tests",
    "status",
    "test_attempts",
    "test_counts_summed",
}
WRAPPER_FIELDS = {
    "cwd",
    "after",
    "seconds",
    "before",
    "suite",
    "env_overrides",
    "test_snapshots",
    "returncode",
    "argv",
}
EVOLUTION_FIELDS = {
    "diff",
    "kind",
    "after_snapshot",
    "before_snapshot",
    "diff_sha256",
    "before_sha256",
    "after_sha256",
}
STRUCTURAL_FIELDS = {
    "assignment_values",
    "invariant_reevaluation",
    "mapped_source_id",
    "original_labels",
    "parsed_state_count",
    "positive_ordinal_indexes",
    "raw_state_blocks_preserved",
    "semantic_transition_check",
    "solver_rerun",
    "structural_mapping_only",
}

NATIVE_SCOPE_CURRENT = {
    "aggregate_scope_owner",
    "complete_serialized_artifact_preserved",
    "default_registry_aggregate_budget_claim",
    "factory_override",
    "hard_aggregate_resource_guarantee",
    "installation",
    "jvm_probe_injected",
    "native_transport_injected",
    "native_v2_execution",
    "new_proof_cache_or_replay",
    "raw_counterexample_and_parsed_states",
    "registry_route",
    "semantic_counterexample_replay_claim",
    "source_map_structural_check",
    "throughput_scaling_claim",
    "tlc_execution",
}
NATIVE_SCOPE_HISTORICAL = {
    "aggregate_scope_owner",
    "complete_serialized_artifact_preserved",
    "default_registry_aggregate_budget_claim",
    "factory_override",
    "hard_aggregate_resource_guarantee",
    "installation",
    "jvm_probe_injected",
    "native_transport_injected",
    "native_v2_execution",
    "new_proof_cache_or_replay",
    "raw_counterexample_only",
    "registry_route",
    "source_map_structural_replay_claim",
    "throughput_scaling_claim",
    "tlc_execution",
}


class Refused(ValueError):
    pass


def require(value, reason):
    if not value:
        raise Refused(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def wire(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode()


def same(left, right):
    return wire(left) == wire(right)


def closed(value, keys, label):
    require(type(value) is dict and set(value) == set(keys), "closed " + label)


def integer(value, low=0, high=2**63 - 1):
    require(type(value) is int and low <= value <= high, "typed bounded integer")
    return value


def digest(value):
    require(type(value) is str and re.fullmatch("[0-9a-f]{64}", value), "typed SHA256")
    return value


def document(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, "duplicate JSON field")
            out[key] = value
        return out

    def number(token):
        require(len(token) <= 64 and math.isfinite(float(token)), "finite bounded JSON number")
        return float(token)

    def count(token):
        require(len(token) <= 20 and abs(int(token)) < 2**63, "bounded JSON integer")
        return int(token)

    def invalid(_token):
        raise Refused("nonfinite JSON constant")

    try:
        obj = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=pairs,
            parse_float=number,
            parse_int=count,
            parse_constant=invalid,
        )
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise Refused("bounded UTF8 JSON") from exc
    pending, count_values = [(obj, 0)], 0
    while pending:
        value, depth = pending.pop()
        count_values += 1
        require(depth <= 32 and count_values <= 100000, "JSON allocation boundary")
        if type(value) is dict:
            pending.extend((v, depth + 1) for v in value.values())
            pending.extend((k, depth + 1) for k in value)
        elif type(value) is list:
            pending.extend((v, depth + 1) for v in value)
        elif type(value) is str:
            value.encode("utf-8")
    return obj


class Reads:
    def __init__(self):
        self.plan, self.held, self.inodes, self.identities = {}, {}, {}, {}

    @staticmethod
    def identity(info):
        return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns

    def reserve(self, path, size, expected=None, cap=MAX_BODY):
        path = Path(path)
        require(path.is_absolute() and path.resolve(strict=True) == path, "canonical explicit path")
        integer(size, 0, cap)
        if expected is not None:
            digest(expected)
        if path in self.plan:
            require(self.plan[path] == (size, expected, cap), "consistent read declaration")
            return path
        require(
            len(self.plan) < MAX_FILES
            and sum(v[0] for v in self.plan.values()) + size <= MAX_TOTAL,
            "aggregate reservation",
        )
        info = path.lstat()
        require(stat.S_ISREG(info.st_mode) and info.st_size == size, "regular exact selected file")
        inode = info.st_dev, info.st_ino
        require(inode not in self.inodes, "physical file alias")
        self.inodes[inode], self.plan[path] = path, (size, expected, cap)
        self.identities[path] = self.identity(info)
        return path

    def read(self, path):
        path = Path(path)
        size, expected, _cap = self.plan[path]
        require(path.resolve(strict=True) == path, "late canonical path")
        before = path.lstat()
        require(
            stat.S_ISREG(before.st_mode)
            and self.inodes.get((before.st_dev, before.st_ino)) == path,
            "late physical selected identity",
        )
        require(
            self.identity(before) == self.identities[path], "retained selected physical generation"
        )
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            with os.fdopen(fd, "rb", closefd=False) as stream:
                raw = stream.read(size + 1)
            require(
                self.identity(before) == self.identity(os.fstat(fd)) == self.identity(path.lstat())
                and len(raw) == size,
                "stable bounded raw body",
            )
        finally:
            os.close(fd)
        require(expected is None or sha(raw) == expected, "exact selected raw SHA")
        if path in self.held:
            require(raw == self.held[path], "late raw byte drift")
        else:
            self.held[path] = raw
        return raw

    def close(self):
        for path in tuple(self.held):
            self.read(path)


def literal(value):
    """Return a scalar kind without evaluating a TLA expression."""
    if len(value.encode()) > 256:
        return None
    if re.fullmatch("-?(0|[1-9][0-9]{0,18})", value) and abs(int(value)) < 2**63:
        return "integer"
    if value in {"TRUE", "FALSE"}:
        return "boolean"
    if value.startswith('"'):
        try:
            parsed = json.loads(value)
        except (ValueError, RecursionError):
            return None
        if type(parsed) is str:
            try:
                if len(parsed.encode()) <= 256:
                    return "json_string"
            except UnicodeError:
                return None
    return None


def parse_scalar_blocks(raw):
    """A bounded independent projection of StateN scalar records and comments."""
    require(type(raw) is str and len(raw.encode()) <= 65536, "scalar trace byte boundary")
    lines = raw.splitlines(keepends=True)
    starts = []
    for index, line in enumerate(lines):
        match = re.fullmatch(r"State([0-9]{1,6})[ \t]*==[ \t]*(.*?)[\r\n]*", line)
        if match:
            starts.append((index, "State" + match[1], match[2]))
    require(len(starts) <= 128, "scalar state count boundary")
    states, issues, labels = [], [], set()
    for index, line in enumerate(lines):
        if re.match(r"State[^\n]*==", line) and index not in {x[0] for x in starts}:
            issues.append({"index": None, "frontier": "unsupported_state_header"})
    for ordinal, (start, label, inline) in enumerate(starts, 1):
        end = starts[ordinal][0] if ordinal < len(starts) else len(lines)
        body = [inline]
        stop = end
        comment = False
        for index in range(start + 1, end):
            text = lines[index].strip()
            if comment:
                if "*)" in text:
                    if text.split("*)", 1)[1].strip():
                        issues.append({"index": ordinal, "frontier": "unsupported_comment_suffix"})
                    comment = False
                continue
            if not text:
                continue
            if text.startswith("(*"):
                comment = "*)" not in text
                if not comment and text.split("*)", 1)[1].strip():
                    issues.append({"index": ordinal, "frontier": "unsupported_comment_suffix"})
                continue
            if re.match(r"[A-Za-z_][A-Za-z0-9_]*[ \t]*=(?!=)", text):
                body.append(text)
            else:
                if not re.match(r"[A-Za-z_][A-Za-z0-9_]*[ \t]*==", text) and not text.startswith(
                    ("====", "----")
                ):
                    issues.append({"index": ordinal, "frontier": "unsupported_scalar_block_syntax"})
                stop = index
                break
        if comment:
            issues.append({"index": ordinal, "frontier": "unterminated_scalar_comment"})
        block = "".join(lines[start:stop]).strip()
        require(len(block.encode()) <= 4096 and len(body) <= 32, "scalar state allocation boundary")
        assignments = {}
        for statement in body:
            if not statement.strip():
                continue
            match = re.fullmatch(
                r"([A-Za-z_][A-Za-z0-9_]{0,63})[ \t]*=(?!=)[ \t]*(.*)", statement.strip()
            )
            if not match or literal(match[2]) is None:
                issues.append(
                    {"index": ordinal, "frontier": "unsupported_or_missing_scalar_literal"}
                )
                continue
            if match[1] in assignments:
                issues.append({"index": ordinal, "frontier": "duplicate_assignment"})
                continue
            assignments[match[1]] = match[2]
        if label in labels:
            issues.append({"index": ordinal, "frontier": "duplicate_original_label"})
        labels.add(label)
        if not assignments:
            issues.append({"index": ordinal, "frontier": "no_supported_scalar_assignments"})
        states.append(
            dict(
                assignments=assignments,
                index=ordinal,
                label=label,
                raw=block,
                schema_version=CE_SCHEMA,
            )
        )
    if not states:
        issues.append({"index": None, "frontier": "no_supported_state_blocks"})
    return states, issues


def mappings(rows):
    require(type(rows) is list and len(rows) == 2, "complete declared source map")
    result = {}
    for row in rows:
        closed(row, MAP_FIELDS, "source map row")
        require(row["schema_version"] == "tla-source-map/v1", "source map schema")
        require(
            type(row["source_id"]) is str and 0 < len(row["source_id"].encode()) <= 256,
            "bounded declared source ID",
        )
        require(
            type(row["line_hint"]) is str and len(row["line_hint"].encode()) <= 256,
            "bounded line hint",
        )
        require(row["tla_symbol"] not in result, "unique declared TLA symbol")
        result[row["tla_symbol"]] = row
    require(set(result) == {"n", "Safety"}, "complete declared variable/property symbols")
    require(
        result["n"]["role"] == "variable"
        and result["n"]["source_kind"] == "state_variable"
        and result["n"]["source_id"] == "variable:counter:n"
        and result["Safety"]["role"] == "safety"
        and result["Safety"]["source_kind"] == "state_predicate"
        and result["Safety"]["source_id"] == "property:counter:safety",
        "declared fixture source symbols",
    )
    return result


def trace_slot(label, trace, source_map, *, historical=False, unmapped_declaration=False):
    if trace is None:
        return dict(
            slot=label,
            present=False,
            recorded_state_count=0,
            independent_scalar_state_count=0,
            recorded_replayed=None,
            historical_zero_state_gap=False,
            structural_bindings=[],
            binding_status="no_counterexample",
            frontier=[],
            semantic_replay_qualified=False,
        )
    closed(trace, TRACE_FIELDS, "counterexample")
    require(
        trace["schema_version"] == CE_SCHEMA
        and trace["source"] in {"checker_counterexample_file", "stdout_stderr"},
        "retained trace schema/source",
    )
    require(
        type(trace["replayed"]) is bool
        and type(trace["replay_notes"]) is list
        and all(type(x) is str and len(x.encode()) <= 4096 for x in trace["replay_notes"]),
        "typed trace replay metadata",
    )
    require(
        type(trace["states"]) is list and len(trace["states"]) <= 128,
        "bounded recorded state population",
    )
    for ordinal, state in enumerate(trace["states"], 1):
        closed(state, STATE_FIELDS, "parsed state")
        integer(state["index"], ordinal, ordinal)
        require(
            state["schema_version"] == CE_SCHEMA
            and type(state["label"]) is str
            and type(state["raw"]) is str
            and type(state["assignments"]) is dict,
            "typed recorded scalar state",
        )
        require(
            all(type(k) is str and type(v) is str for k, v in state["assignments"].items()),
            "string scalar assignments",
        )
    projected, issues = parse_scalar_blocks(trace["raw"])
    if historical:
        require(
            trace["states"] == []
            and trace["replayed"] is True
            and trace["replay_notes"] == ["counterexample contained no parseable State blocks"],
            "unchanged legacy zero-state receipt",
        )
        require(
            [s["label"] for s in projected] == ["State0", "State1", "State2"]
            and [s["assignments"] for s in projected] == [{"n": "0"}, {"n": "1"}, {"n": "2"}]
            and not issues,
            "historical raw scalar gap",
        )
    else:
        require(same(trace["states"], projected), "exact independent stored state/block projection")
    bindings = []
    if source_map is not None:
        declared = mappings(source_map)
        for state in projected:
            for symbol, value in state["assignments"].items():
                row = declared.get(symbol)
                if row is not None and row["role"] == "variable":
                    bindings.append(
                        dict(
                            index=state["index"],
                            original_label=state["label"],
                            symbol=symbol,
                            literal=value,
                            literal_kind=literal(value),
                            declared_source_id=row["source_id"],
                        )
                    )
                else:
                    issues.append({"index": state["index"], "frontier": "unmapped_scalar_symbol"})
    if unmapped_declaration:
        require(
            source_map is None
            and trace["replayed"] is False
            and "counterexample has no mapped source variables" in trace["replay_notes"],
            "recorded unmapped negative declaration",
        )
        issues.append({"index": None, "frontier": "original_negative_source_map_not_retained"})
    if trace["replayed"] and not historical:
        require(
            not issues
            and len(bindings) == len(projected) > 0
            and STRUCTURAL_NOTE in trace["replay_notes"],
            "recorded structural mapping ceiling",
        )
    return dict(
        slot=label,
        present=True,
        raw_sha256=sha(trace["raw"].encode()),
        raw_bytes=len(trace["raw"].encode()),
        recorded_state_count=len(trace["states"]),
        independent_scalar_state_count=len(projected),
        recorded_replayed=trace["replayed"],
        historical_zero_state_gap=historical,
        structural_bindings=bindings,
        independent_scalar_states=projected,
        binding_status="historical_gap"
        if historical
        else "unknown"
        if issues
        else "declared_scalar_bindings",
        frontier=issues,
        original_negative_mapping_available=False
        if unmapped_declaration
        else source_map is not None,
        source_map_semantics_verified=False,
        semantic_replay_qualified=False,
    )


def native_slots(value, fixtures, *, historical=False, lifecycle=None, requests=None):
    closed(value, NATIVE_FIELDS, "native result")
    closed(
        value["scope"],
        NATIVE_SCOPE_HISTORICAL if historical else NATIVE_SCOPE_CURRENT,
        "native scope",
    )
    if not historical:
        require(
            value["scope"]["semantic_counterexample_replay_claim"] is False
            and value["scope"]["native_v2_execution"] is False
            and value["scope"]["source_map_structural_check"] is True,
            "native structural authority ceiling",
        )
    expected_schema = (
        "tla-artifact-payload-benchmark@1"
        if historical
        else "tla-counterexample-replay-benchmark@1"
    )
    require(
        value["schema"] == expected_schema and value["status"] == "passed",
        "fixed historical native result schema",
    )
    require(
        type(value["cases"]) is list and len(value["cases"]) == 2,
        "complete serial native case population",
    )
    integer(value["native_lifecycles"], 6, 6)
    require(
        same(value["phase_counts"], {"help": 2, "model": 2, "setup": 2}),
        "recorded six phase population",
    )
    require(
        value["source_pins_before"] == value["source_pins_after"],
        "historical source pin observations",
    )
    if lifecycle is not None:
        require(
            type(lifecycle) is list
            and len(lifecycle) == 6
            and type(requests) is list
            and len(requests) == 6,
            "complete selected lifecycle/request population",
        )
    slots = []
    for index, case in enumerate(value["cases"]):
        valid = index == 0
        require(
            case["valid"] is valid and case["complete_artifact_equal"] is True,
            "ordered preserved native case",
        )
        request, attempt, result, original = (
            case[k] for k in ("request", "attempt", "result", "original_outcome")
        )
        closed(
            original,
            {"artifacts", "interface_version", "receipt", "request_digest", "result"},
            "original outcome",
        )
        require(
            request["schema_version"] == "proof-backend-request/v1"
            and attempt["schema_version"] == "proof-backend-attempt/v1"
            and result["schema_version"] == "bounded-result/v1"
            and request["requested_backend_id"] == "apalache",
            "protocol schemas",
        )
        request_sha, attempt_sha = sha(wire(request)), sha(wire(attempt))
        require(
            request_sha
            == case["request_digest"]
            == original["request_digest"]
            == attempt["request_digest"]
            == result["request_digest"]
            and attempt_sha == case["attempt_digest"] == result["attempt_digest"],
            "independent protocol wire identity",
        )
        require(
            attempt["status"] == "succeeded" and result["status"] == "unknown",
            "generic nonconclusive projection",
        )
        closed(
            result["authority"],
            {
                "configuration_digest",
                "evidence_digests",
                "issuer",
                "kind",
                "method",
                "schema_version",
                "scope_digest",
            },
            "generic descriptive authority",
        )
        require(
            result["authority"]["kind"] == "satisfiability"
            and result["authority"]["evidence_digests"] == []
            and result["authority"]["scope_digest"] == request_sha,
            "generic authority is descriptive only",
        )
        typed, receipt = original["result"], original["receipt"]
        require(
            typed["status"] == ("satisfied" if valid else "violated")
            and typed["authority"] == "model_check"
            and typed["translation_ceiling"] == "bounded",
            "typed bounded original result",
        )
        require(same(typed, result["payload"]["result"]), "exact original typed payload")
        require(
            result["payload"]["result_status"] == typed["status"]
            and result["payload"]["result_authority"] == "model_check",
            "no generic authority promotion",
        )
        fixture = fixtures["true" if valid else "false"]
        require(
            same(case["submitted_artifact"], fixture)
            and same(case["decoded_artifact"]["source_map"], fixture["source_map"])
            and same(original["artifacts"]["source_map"], fixture["source_map"]),
            "selected declared source map joins",
        )
        source_map = fixture["source_map"]
        mappings(source_map)
        trace = receipt["counterexample"]
        if valid:
            require(trace is case["raw_witness"] is None, "valid case has no counterexample")
        else:
            require(
                same(trace, typed["witness"]["counterexample"]),
                "typed/receipt exact counterexample",
            )
            require(
                same(case["raw_witness"]["states"], trace["states"])
                if not historical
                else case["raw_witness"]["parsed_state_count"] == 0,
                "raw witness recorded parsed population",
            )
            require(
                case["raw_witness"]["sha256"] == sha(trace["raw"].encode()),
                "recorded raw witness digest",
            )
        if lifecycle is not None:
            native = lifecycle[index * 3 + 1]["result"]
            require(
                receipt["stdout"] == native["stdout"]
                and receipt["stderr"] == native["stderr"]
                and same(receipt["command"], native["command"]),
                "trace receipt selected native output",
            )
            integer(receipt["returncode"], 0 if valid else 12, 0 if valid else 12)
            require(
                "--length=3" in native["command"] and native["workspace_cleaned"] is True,
                "recorded native three step fixture",
            )
            if not valid:
                require(
                    trace["raw"] == native["output_files"]["apalache-run/violation.tla"],
                    "exact retained trace output file",
                )
            require(
                same(requests[index * 3 + 1]["argv"], native["command"]),
                "native recorded argv join",
            )
        slot = trace_slot(
            ("historical_native" if historical else "current_native")
            + (":valid" if valid else ":invalid"),
            trace,
            source_map,
            historical=historical and not valid,
        )
        if not valid and not historical:
            require(
                slot["recorded_state_count"] == 3 and len(slot["structural_bindings"]) == 3,
                "complete current native scalar binding",
            )
            checks = case["raw_witness"]["structural_checks"]
            closed(checks, STRUCTURAL_FIELDS, "structural checks")
            require(
                same(checks["positive_ordinal_indexes"], [1, 2, 3])
                and checks["original_labels"] == ["State0", "State1", "State2"]
                and checks["assignment_values"] == ["0", "1", "2"]
                and checks["mapped_source_id"] == "variable:counter:n"
                and checks["raw_state_blocks_preserved"]
                is checks["structural_mapping_only"]
                is True,
                "recorded original label/ordinal/literal distinction",
            )
            integer(checks["parsed_state_count"], 3, 3)
            require(
                all(
                    checks[k] is False
                    for k in ("invariant_reevaluation", "semantic_transition_check", "solver_rerun")
                ),
                "no recorded semantic replay",
            )
        slots.append(slot)
    return slots


def static_slots(value, label, historical, fixtures):
    closed(value, PREFLIGHT_FIELDS, "static preflight")
    require(
        value["status"] == "passed"
        and value["semantic_counterexample_replay_claim"] is False
        and value["native_v2_execution"] is False
        and value["source_map_structural_check"] is True,
        "static structural scope",
    )
    require(
        value["retained_trace_source_sha256"] == ANCHORS["historical_native_result"],
        "historical selected native trace identity",
    )
    require(
        same(value["retained_trace_before"], historical)
        and value["retained_trace_raw_sha256"] == sha(historical["raw"].encode()),
        "unchanged old raw/receipt evidence",
    )
    maps = fixtures["false"]["source_map"]
    out = [
        trace_slot(
            label + ":retained_before", value["retained_trace_before"], maps, historical=True
        ),
        trace_slot(label + ":parsed", value["parsed_trace"], maps),
        trace_slot(label + ":structural", value["structurally_replayed_trace"], maps),
    ]
    require(
        value["parsed_trace"]["replayed"] is False
        and value["structurally_replayed_trace"]["replayed"] is True,
        "parse observation distinct from recorded structural replay",
    )
    require(
        type(value["negative_controls"]) is list
        and [r["case"] for r in value["negative_controls"]] == ["empty", "malformed", "unmapped"],
        "complete explicit negative frontier population",
    )
    for row in value["negative_controls"]:
        closed(row, {"case", "replayed", "trace"}, "negative frontier")
        require(
            row["replayed"] is row["trace"]["replayed"] is False,
            "negative trace never successful replay",
        )
        unmapped = row["case"] == "unmapped"
        out.append(
            trace_slot(
                label + ":" + row["case"],
                row["trace"],
                None if unmapped else maps,
                unmapped_declaration=unmapped,
            )
        )
    return out


def junit(raw):
    require(
        b"<!DOCTYPE" not in raw.upper() and b"<!ENTITY" not in raw.upper(),
        "XML external/declaration boundary",
    )
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise Refused("bounded JUnit XML") from exc
    nodes = list(root.iter())
    require(
        len(nodes) <= 10000
        and root.tag == "testsuites"
        and len(root) == 1
        and root[0].tag == "testsuite",
        "closed JUnit suite structure",
    )
    require(
        all(
            n.tag in {"testsuites", "testsuite", "testcase", "failure", "error", "skipped"}
            for n in nodes
        ),
        "closed JUnit tags",
    )
    rows, failures, skips = {}, {}, 0
    for case in root.findall(".//testcase"):
        key = (case.get("classname"), case.get("name"))
        require(
            all(type(x) is str and 0 < len(x.encode()) <= 4096 for x in key) and key not in rows,
            "unique bounded complete JUnit IDs",
        )
        result = "passed"
        for child in case:
            require(child.tag in {"failure", "error", "skipped"}, "closed JUnit outcome")
            require(result == "passed", "single JUnit outcome")
            result = child.tag
            if result in {"failure", "error"}:
                failures[key] = child.get("message", "")
            else:
                skips += 1
        rows[key] = result
    suite = root[0]
    counts = {
        "tests": len(rows),
        "failures": sum(v == "failure" for v in rows.values()),
        "errors": sum(v == "error" for v in rows.values()),
        "skipped": skips,
    }
    for name, expected in counts.items():
        require(suite.get(name) == str(expected), "independent XML aggregate counts")
    return rows, failures, counts


def trials(metadata, docs):
    inventories, result = {}, []
    for label, expected, accepted in (
        ("focused_initial", 605, False),
        ("focused_selected", 605, True),
        ("joined_selected", 2089, True),
    ):
        rows, failures, counts = junit(metadata[label + "_junit"])
        wrapper = docs[label + "_result"]
        closed(wrapper, WRAPPER_FIELDS, "test wrapper result")
        integer(wrapper["returncode"], 0 if accepted else 1, 0 if accepted else 1)
        require(same(wrapper["before"], wrapper["after"]), "historical test source pins stable")
        require(
            len(rows) == expected and counts["skipped"] == counts["errors"] == 0,
            "complete selected test population",
        )
        require(
            failures == {}
            if accepted
            else failures
            == {
                FAILED_ID: "ipfs_datasets_py.logic.backends.results.ResultNormalizationError: diagnostics must not contain duplicates"
            },
            "initial duplicate diagnostic failure preserved",
        )
        require(
            rows[FAILED_ID] == ("passed" if accepted else "failure"),
            "same regression ID corrected only in selected trials",
        )
        replay_count = sum(k[0].endswith("test_tla_counterexample_replay") for k in rows)
        require(replay_count == 74, "complete replay case count")
        inventories[label] = set(rows)
        result.append(
            dict(
                trial=label,
                accepted=accepted,
                recorded_returncode=wrapper["returncode"],
                complete_case_count=len(rows),
                passed_case_count=sum(v == "passed" for v in rows.values()),
                failure_count=counts["failures"],
                error_count=0,
                skipped_count=0,
                replay_case_count=replay_count,
                corrected_regression_passed=accepted,
                case_population_sha256=sha(wire(sorted(rows))),
            )
        )
    require(
        inventories["focused_initial"] == inventories["focused_selected"]
        and inventories["focused_selected"] <= inventories["joined_selected"],
        "focused identical and joined overlapping population",
    )
    require(
        b"diagnostics must not contain duplicates" in metadata["focused_initial_log"],
        "retained duplicate diagnostic log",
    )
    return result


def derive(metadata):
    docs = {
        role: document(body)
        for role, body in metadata.items()
        if role
        not in {
            "report",
            "focused_initial_log",
            "focused_initial_junit",
            "focused_selected_junit",
            "joined_selected_junit",
        }
    }
    q = docs["qualification"]
    closed(q, QUALIFICATION_FIELDS, "qualification")
    require(
        q["schema"] == "tla-counterexample-replay-qualification@1"
        and q["status"] == "passed_partial_scope",
        "partial trace qualification",
    )
    for key, expected in (
        ("selected_tests", 2089),
        ("focused_tests", 605),
        ("new_counterexample_tests", 74),
        ("native_phases", 6),
        ("native_success_cases", 2),
    ):
        integer(q[key], expected, expected)
    require(
        q["test_counts_summed"] is q["new_cache_replay"] is q["new_codebase_smt_execution"] is False
        and q["production_tasks_closed"] == [],
        "partial nonadditive qualification",
    )
    fixtures = docs["native_fixtures"]
    closed(fixtures, {"true", "false"}, "native fixtures")
    current = native_slots(
        docs["native_result"],
        fixtures,
        lifecycle=docs["native_lifecycle"],
        requests=docs["native_request"],
    )
    old = native_slots(docs["historical_native_result"], fixtures, historical=True)
    historical = docs["historical_native_result"]["cases"][1]["original_outcome"]["receipt"][
        "counterexample"
    ]
    slots = current + old
    for label in ("preflight_initial", "preflight_selected"):
        slots.extend(static_slots(docs[label], label, historical, fixtures))
    require(
        len(slots) == 16
        and sum(row["present"] for row in slots) == 14
        and sum(row["recorded_state_count"] for row in slots) == 23,
        "complete trace instance accounting",
    )
    require(
        sum(row["historical_zero_state_gap"] for row in slots) == 3,
        "historical zero-state gap denominator",
    )
    native = docs["native_result"]
    for role, selector in (
        ("native_lifecycle", "lifecycle-audit.json"),
        ("native_request", "request-audit.json"),
    ):
        require(
            native["audit_sha256"][selector] == sha(metadata[role]),
            "trace-specific native raw audit join",
        )
    selectors = {
        "native_result": "native/result.json",
        "native_lifecycle": "native/lifecycle-audit.json",
        "native_request": "native/request-audit.json",
        "native_fixtures": "native/fixtures.json",
        "preflight_initial": "benchmark-preflight.json",
        "preflight_selected": "benchmark-preflight-selected.json",
        "source_evolution": "source-evolution.json",
    }
    for label in ("focused_initial", "focused_selected", "joined_selected"):
        stem = label.replace("_", "-")
        selectors[label + "_result"] = stem + ".result.json"
        selectors[label + "_junit"] = stem + ".xml"
    selectors["focused_initial_log"] = "focused-initial.log"
    for role, selector in selectors.items():
        require(
            q["artifact_sha256"][selector] == sha(metadata[role]),
            "qualification exact selected metadata join",
        )
    evolution = docs["source_evolution"]
    require(type(evolution) is dict and len(evolution) == 2, "two declared source evolution rows")
    for path, row in evolution.items():
        closed(row, EVOLUTION_FIELDS, "source evolution metadata")
        require(
            type(path) is str and row["kind"] == "production",
            "declared production source evolution",
        )
        for field in ("before_sha256", "after_sha256", "diff_sha256"):
            digest(row[field])
        require(
            native["source_pins_after"][path] == row["after_sha256"],
            "current source metadata identity join",
        )
    return dict(
        trace_slots=slots,
        trace_slot_count=16,
        present_trace_count=14,
        absent_counterexample_count=2,
        recorded_parsed_state_observation_count=23,
        historical_zero_state_gap_count=3,
        current_native_case_count=2,
        recorded_native_phase_count=6,
        native_invalid_positive_ordinal_indexes=[1, 2, 3],
        native_invalid_original_labels=["State0", "State1", "State2"],
        native_invalid_assignment_literals=["0", "1", "2"],
        declared_variable_source_id="variable:counter:n",
        declared_nonassignment_safety_source_id="property:counter:safety",
        test_trials=trials(metadata, docs),
        source_evolution_metadata=evolution,
        unmapped_negative_scope="reported missing map; original mutated mapping artifact is not retained",
        trace_parser_scope="StateN plus bounded decimal, TRUE/FALSE or JSON-string scalar assignments; no expression evaluation",
    )


def population(output, expected, identity):
    require(
        output.resolve(strict=True) == output
        and stat.S_ISDIR(output.lstat().st_mode)
        and (output.lstat().st_dev, output.lstat().st_ino) == identity,
        "output root physical identity",
    )
    files, dirs = set(), set()
    for root, folders, names in os.walk(output, followlinks=False):
        require(len(files) + len(dirs) <= 64, "output walk boundary")
        for name in folders:
            p = Path(root) / name
            require(
                stat.S_ISDIR(p.lstat().st_mode) and not p.is_symlink(),
                "nonsymlink output directory",
            )
            require(len(files) + len(dirs) < 64, "output entry allocation boundary")
            dirs.add(p.relative_to(output).as_posix())
        for name in names:
            p = Path(root) / name
            require(stat.S_ISREG(p.lstat().st_mode) and not p.is_symlink(), "regular output member")
            require(len(files) + len(dirs) < 64, "output entry allocation boundary")
            files.add(p.relative_to(output).as_posix())
    require(files == expected and dirs == {"inputs"}, "exact final output population")


def publication_fence(reads, output, expected, identity):
    reads.close()
    population(output, expected, identity)


def audit(manifest_path, output):
    manifest_path, output = Path(manifest_path).absolute(), Path(output).absolute()
    reads = Reads()
    reads.reserve(manifest_path, manifest_path.lstat().st_size, cap=MAX_MANIFEST)
    manifest_raw = reads.read(manifest_path)
    manifest = document(manifest_raw)
    closed(manifest, {"schema", "fixture_origin", "selected_files"}, "input profile")
    require(
        manifest["schema"] == INPUT_SCHEMA
        and manifest["fixture_origin"] == "retained_tla_counterexample_metadata",
        "fixed input schema/origin",
    )
    require(
        type(manifest["selected_files"]) is list
        and [r["role"] for r in manifest["selected_files"]] == list(ROLES),
        "complete ordered selected role population",
    )
    metadata, selected = {}, []
    for row in manifest["selected_files"]:
        closed(row, {"role", "path", "size_bytes", "sha256"}, "selected descriptor")
        path = reads.reserve(row["path"], row["size_bytes"], row["sha256"])
        require(path != manifest_path, "selected body is distinct from manifest")
        body = reads.read(path)
        if row["role"] in ANCHORS:
            require(sha(body) == ANCHORS[row["role"]], "fixed independent metadata anchor")
        metadata[row["role"]] = body
        selected.append(dict(row))
    derived = derive(metadata)
    require(
        not output.exists() and output.parent.resolve(strict=True) == output.parent,
        "fresh canonical output",
    )
    require(
        all(
            not output.is_relative_to(path.parent) and not path.is_relative_to(output)
            for path in reads.plan
        ),
        "output separated from inputs",
    )
    reads.close()
    output.mkdir()
    info = output.lstat()
    identity = info.st_dev, info.st_ino
    (output / "inputs").mkdir()
    expected = {REPORT_NAME, "input.json"}
    with (output / "input.json").open("xb") as stream:
        stream.write(manifest_raw)
    reads.reserve(output / "input.json", len(manifest_raw), sha(manifest_raw), cap=MAX_MANIFEST)
    reads.read(output / "input.json")
    for index, row in enumerate(selected):
        local = output / "inputs" / f"{index:03d}-{row['role']}.body"
        body = metadata[row["role"]]
        with local.open("xb") as stream:
            stream.write(body)
        reads.reserve(local, len(body), sha(body))
        reads.read(local)
        row["retained_path"] = str(local)
        expected.add(local.relative_to(output).as_posix())
    report = dict(
        schema=REPORT_SCHEMA,
        status="passed",
        fixture_origin=manifest["fixture_origin"],
        selected_manifest_sha256=sha(manifest_raw),
        selected_files=selected,
        selected_file_count=17,
        selected_input_bytes=sum(map(len, metadata.values())),
        **derived,
        **dict.fromkeys(TRUE, True),
        **dict.fromkeys(FALSE, False),
        **dict.fromkeys(ZERO, 0),
        production_tasks_closed=[],
        limits=dict(
            max_file_bytes=MAX_BODY,
            max_aggregate_bytes=MAX_TOTAL,
            max_manifest_bytes=MAX_MANIFEST,
            max_report_bytes=MAX_REPORT,
            max_selected_files=MAX_FILES,
            max_trace_bytes=65536,
            max_trace_states=128,
            max_state_bytes=4096,
            max_assignments_per_state=32,
        ),
        limitations=[
            "Structural scalar and declared symbol metadata only; no transition, invariant, liveness or fairness semantics.",
            "Source mappings are caller declarations, not authenticated semantic bindings.",
            "The unmapped negative omits its original mutated map artifact; its map absence is reported only.",
            "Historical zero-state receipts retain their original replayed flags and raw bytes.",
            "Per-file rereads and exact output populations are not an atomic filesystem snapshot or producer authentication.",
        ],
    )
    encoded = (json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    require(len(encoded) <= MAX_REPORT, "bounded report output")
    reads.close()
    with (output / REPORT_NAME).open("xb") as stream:
        stream.write(encoded)
    reads.reserve(output / REPORT_NAME, len(encoded), sha(encoded), cap=MAX_REPORT)
    require(reads.read(output / REPORT_NAME) == encoded, "exact published report")
    publication_fence(reads, output, expected, identity)
    publication_fence(reads, output, expected, identity)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = audit(args.manifest, args.output)
    except (Refused, OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "refused", "reason": str(exc)}, sort_keys=True))
        return 2
    print(
        json.dumps(
            {
                k: report[k]
                for k in (
                    "status",
                    "trace_slot_count",
                    "present_trace_count",
                    "recorded_parsed_state_observation_count",
                )
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
