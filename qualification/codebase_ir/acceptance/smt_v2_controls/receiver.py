"""Receive selected SMT@2 requests, evidence and recorded native phases offline.

Archived runtime sources are parsed as inert text. No owner import, solver,
database, executable, stdin reconstruction or live resource observation occurs.
"""
from __future__ import annotations

import argparse
import ast
import copy
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from inventory_query_controls import native_receiver as codec

INPUT_SCHEMA = "codebase-ir-smt-v2-custody-input@1"
REPORT_SCHEMA = "codebase-ir-smt-v2-custody-report@1"
QUALIFICATION_SHA = "c80c5cbec17b29401fc55022d63bdd7c94cc38cdf295d51dd995a9d27eef560a"
NATIVE_RESULT_SHA = "274d817e2f574e5476e4601fa5265396cb516e75b476c3d2e34ff87fd32764c7"
MAX_FILE, MAX_TOTAL, MAX_FILES, MAX_PHASES, MAX_CASES = 1024 * 1024, 8 * 1024 * 1024, 12, 512, 64
ROLES = {"prior_qualification": "qualification.json", "native_result": "native-selected/result.json",
         "native_command": "native-selected/command.json", "launch_audit": "native-selected/launch-audit.json",
         "lifecycle_audit": "native-selected/lifecycle-audit.json", "control_audit": "native-selected/control-audit.json",
         "wire_before": "wire-before.json", "wire_after": "wire-after.json", "wire_comparison": "wire-comparison.json",
         "runtime_before": "prior-runtime-source/execution_v2.py", "runtime_after": "runtime-source-after/execution_v2.py"}
WIRE_CLASSES = ("SmtArtifactBindingV2", "SmtDifferentialBindingV2", "SmtReplayReceiptV2", "SmtExecutionRequestV2",
                "SmtProviderEvidenceV2", "SmtExecutionResultV2")
IDENTITY_FIELDS = {"disposition", "mode", "obligation_digest", "proof_established", "provider", "query_mode", "request_id",
                   "satisfiability_established", "schema_version", "script_digest", "solver_verdict", "theorem_established"}
FALSE_FLAGS = ("native_execution_performed", "training_executed", "current_authority_claimed", "owner_database_opened",
               "profile_keys_read", "signature_authentication_performed", "numerical_state_replayed", "source_execution_replayed",
               "checker_executions_replayed", "live_eligibility_qualified", "production_acceptance_qualified",
               "solver_verdict_authenticated", "runtime_resource_enforcement_verified", "raw_phase_stdin_custody_verified",
               "raw_caller_request_custody_verified", "unique_phase_execution_attestation_verified",
               "behavioral_evidence_admission_qualified", "proof_certificate_verified")
TRUE_FLAGS = ("smt_v2_structural_custody_conformance", "retained_request_evidence_bindings_reconciled",
              "wire_fixture_compatibility_reconciled", "frozen_wire_definitions_unchanged", "input_files_unchanged")
REQUEST_FIELDS = {"available", "bounds", "confidence", "fallback_output", "fluent_text", "has_fallback_output", "has_mock_output",
                  "interface", "metadata", "mock_output", "mode", "obligation", "provider", "request_id", "request_proof",
                  "schema_version", "source_ref_ids"}
REPLAY_FIELDS = {"diagnostics", "interface", "matched", "obligation_digest", "original_disposition", "original_verdict",
                 "replay_claimed", "replay_id", "replayed_disposition", "replayed_verdict", "request_id", "schema_version", "script_digest"}
ARTIFACT_FIELDS = {"atoms", "digest", "interface", "kind", "present", "schema_version", "supported", "text_excerpt"}
EVIDENCE_FIELDS = {"authority_ceiling", "available", "bounds_exhausted", "claim_proof", "claim_satisfiability", "claim_theorem",
    "compilation_id", "confidence", "content_digest", "diagnostics", "differential", "disposition", "evidence_id",
    "fallback_output_present", "fluent_text_present", "interface", "is_conclusive", "is_proved", "metadata", "mock_output_present",
    "mode", "model", "obligation_digest", "obligation_id", "proof", "proof_established", "provider", "query_mode", "replay",
    "request_digest", "request_id", "result_authority", "result_status", "role", "satisfiability_established", "schema_version",
    "script_digest", "solver_backend_id", "solver_verdict", "solver_version", "source_ref_ids", "theorem_established",
    "translation_ceiling", "translation_receipt_id", "unsat_core"}
PHASE_REQUEST_FIELDS = {"argv", "max_output_bytes", "memory_bytes", "resident_memory_bytes", "stdin_sha256", "terminal_command", "timeout_seconds"}
CONTROL_NAMES = ("control:v2:live-cancellation", "control:v2:aggregate-deadline", "control:v2:between_peers",
                 "control:v2:before_automatic_replay", "control:v2:during_explicit_replay", "control:v2:after_evidence")


def exact_int(value, minimum=0, maximum=2**63 - 1):
    codec.require(type(value) is int and minimum <= value <= maximum, "exact bounded SMT integer")
    return value


def number(value, maximum=2**53):
    codec.require(type(value) in (int, float) and 0 <= value <= maximum and math.isfinite(value), "finite recorded SMT number")
    return value


def digest(value):
    codec.require(type(value) is str and len(value) == 64 and all(char in "0123456789abcdef" for char in value), "recorded SMT SHA256")
    return value


def hashed(value):
    return codec.sha(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode())


def bounded_list(value, maximum):
    codec.require(type(value) is list and len(value) <= maximum, "bounded SMT population")
    return value


def document(raw, limit=MAX_FILE):
    codec.require(type(raw) is bytes and len(raw) <= limit, "SMT JSON byte bound")
    # Wrapping a bounded public array reuses the existing strict duplicate,
    # finite, surrogate, magnitude and structure checks without owner imports.
    if raw.lstrip().startswith(b"["):
        return codec.document(b'{"items":' + raw + b'}', limit + 10)["items"]
    return codec.document(raw, limit)


class Capture:
    def __init__(self):
        self.raw, self.total = {}, 0

    def take(self, path, pin=None, limit=MAX_FILE):
        codec.require(path not in self.raw and len(self.raw) < MAX_FILES, "SMT input identity/file bound")
        allowance = min(limit, MAX_TOTAL - self.total, pin["bytes"] if pin else limit)
        raw = codec.OriginalCapture.read(path, allowance)
        if pin:
            codec.require(len(raw) == pin["bytes"] and codec.sha(raw) == pin["sha256"], "SMT selected raw pin")
        self.raw[path], self.total = raw, self.total + len(raw)
        return raw

    def stable(self):
        for path, raw in self.raw.items():
            codec.require(codec.OriginalCapture.read(path, len(raw)) == raw, "private frozen SMT input drift")


def bounds(value):
    codec.closed(value, {"max_memory_bytes", "max_output_bytes", "max_steps", "timeout_ms"}, "SMT request bounds")
    for name, child in value.items():
        exact_int(child, 1, 2147483647 if name == "timeout_ms" else 2**63 - 1)


def artifact(value, expected_kind):
    codec.closed(value, ARTIFACT_FIELDS, "SMT artifact binding")
    codec.require(value["schema_version"] == "smt-artifact-binding/v2" and value["interface"] == "SmtArtifactBinding@2"
                  and value["kind"] in {expected_kind, "none"}, "SMT artifact schema/kind")
    codec.require(type(value["present"]) is bool and type(value["supported"]) is bool, "typed artifact availability")
    atoms = bounded_list(value["atoms"], 64)
    codec.require(all(type(atom) is str for atom in atoms) and len(set(atoms)) == len(atoms)
                  and type(value["text_excerpt"]) is str and len(value["text_excerpt"].encode()) <= 65536, "artifact bounded atoms/text")
    if value["present"]:
        codec.require(expected_kind in {"model", "unsat_core"}, "selected profile has no proof artifact")
        payload = {"model": value["text_excerpt"]} if expected_kind == "model" else {"unsat_core": atoms}
        codec.require(value["digest"] == hashed(payload), "artifact content digest")
    else:
        codec.require(value["digest"] == "" and atoms == [] and value["text_excerpt"] == "", "absent artifact is explicit")


def replay(value, evidence):
    codec.closed(value, REPLAY_FIELDS, "SMT replay receipt")
    codec.require(value["schema_version"] == "smt-replay-receipt/v2" and value["interface"] == "SmtReplayReceipt@2"
                  and value["matched"] is True and value["replay_claimed"] is True, "typed recorded matched replay")
    for name in ("request_id", "obligation_digest", "script_digest"):
        codec.require(value[name] == evidence[name], "replay exact request/obligation/script binding")
    codec.require(value["replay_id"] == "replay:smt:" + evidence["request_id"]
                  and value["original_disposition"] == value["replayed_disposition"] == evidence["disposition"]
                  and value["original_verdict"] == value["replayed_verdict"] == evidence["solver_verdict"], "replay retained disposition/verdict")


def backend(value, evidence, request, provider):
    codec.require(type(value) is dict and value["schema_version"] == "typed-backend-result/v1"
                  and value["backend_id"] == provider and value["bounds"] == request["bounds"], "backend provider/request bounds")
    metadata, witness = value["metadata"], value["witness"]
    for name in ("compilation_id", "script_digest", "translation_receipt_id"):
        codec.require(metadata[name] == evidence[name], "backend/evidence identity")
    codec.require(witness["obligation_id"] == evidence["obligation_id"] and witness["query_mode"] == evidence["query_mode"]
                  and witness["solver_verdict"] == evidence["solver_verdict"] and witness["solver_version"] == evidence["solver_version"]
                  and value["status"] == evidence["result_status"] and value["authority"] == evidence["result_authority"], "backend/evidence recorded result")
    translation = witness["translation_receipt"]
    codec.require(translation["receipt_id"] == evidence["translation_receipt_id"] and translation["source_identity"] == metadata["source_identity"]
                  and translation["target_identity"] == metadata["target_identity"], "retained translation identity")


def outcome(value, original_request=None, original_obligation=None, expected_provider=None, expected_mode=None):
    codec.closed(value, {"backend_result", "differential_report", "evidence", "interface", "request", "schema_version"}, "SMT result")
    codec.require(value["schema_version"] == "smt-execution-result/v2" and value["interface"] == "SmtExecutionResult@2", "SMT result schema")
    request, evidence = value["request"], value["evidence"]
    codec.closed(request, REQUEST_FIELDS, "typed SMT request")
    codec.closed(evidence, EVIDENCE_FIELDS, "typed SMT evidence")
    codec.require(request["schema_version"] == "smt-execution-request/v2" and request["interface"] == "SmtExecutionRequest@2"
                  and evidence["schema_version"] == "smt-provider-evidence/v2" and evidence["interface"] == "SMTProviderEvidence@2", "SMT request/evidence schema")
    codec.require((original_request is None or codec.equal(request, original_request))
                  and (original_obligation is None or codec.equal(request["obligation"], original_obligation)), "independent original SMT input correspondence")
    codec.require(request["provider"] in {"z3", "cvc5", "differential"} and request["mode"] in {"pinned_solver", "hermetic_fixture"}
                  and (expected_provider is None or request["provider"] == expected_provider)
                  and (expected_mode is None or request["mode"] == expected_mode), "expected SMT provider/mode")
    bounds(request["bounds"])
    refs = bounded_list(request["source_ref_ids"], 64)
    codec.require(all(type(ref) is str for ref in refs) and len(set(refs)) == len(refs), "complete unique request source refs")
    codec.require(request["available"] is True and request["request_proof"] is False and request["has_mock_output"] is False
                  and request["has_fallback_output"] is False and request["mock_output"] is None and request["fallback_output"] is None
                  and request["fluent_text"] == "" and request["confidence"] == 0.0 and type(request["confidence"]) is float
                  and request["metadata"] == {}, "selected actual request has no injected authority channel")
    for name in ("request_id", "provider", "mode", "source_ref_ids"):
        codec.require(codec.equal(evidence[name], request[name]), "request/evidence exact identity")
    codec.require(evidence["request_digest"] == hashed(request) and evidence["obligation_digest"] == hashed(request["obligation"])
                  and evidence["content_digest"] == hashed({name: evidence[name] for name in IDENTITY_FIELDS}), "SMT request/obligation/evidence digests")
    codec.require(evidence["obligation_id"] == request["obligation"]["obligation_id"] and evidence["query_mode"] == request["obligation"]["query_mode"], "obligation evidence identity")
    for name in ("script_digest", "content_digest", "request_digest", "obligation_digest"):
        digest(evidence[name])
    for name in ("available", "bounds_exhausted", "claim_proof", "claim_satisfiability", "claim_theorem", "fallback_output_present",
                 "fluent_text_present", "is_conclusive", "is_proved", "mock_output_present", "proof_established", "satisfiability_established", "theorem_established"):
        codec.require(type(evidence[name]) is bool, "exact evidence Boolean")
    codec.require(evidence["proof_established"] is False and evidence["claim_proof"] is False and evidence["bounds_exhausted"] is False
                  and evidence["available"] is True and evidence["is_conclusive"] is True and evidence["metadata"] == {}, "selected evidence proof ceiling")
    for name in ("fluent_text_present", "fallback_output_present", "mock_output_present"):
        codec.require(evidence[name] is False, "no text/mock/fallback evidence authority")
    expected = {("theorem_by_negation", "unsat"): "proved", ("theorem_by_negation", "sat"): "disproved", ("satisfiability", "sat"): "satisfiable"}
    codec.require(evidence["disposition"] == expected.get((evidence["query_mode"], evidence["solver_verdict"])), "recorded SMT verdict/disposition distinction")
    codec.require(evidence["authority_ceiling"] == "satisfiability" and evidence["translation_ceiling"] == "bounded"
                  and evidence["result_status"] == evidence["disposition"]
                  and evidence["result_authority"] == ("theorem" if evidence["query_mode"] == "theorem_by_negation" else "satisfiability"),
                  "selected evidence recorded authority category ceiling")
    codec.require(evidence["is_proved"] == (evidence["disposition"] == "proved")
                  and evidence["theorem_established"] == (evidence["query_mode"] == "theorem_by_negation")
                  and evidence["claim_theorem"] == evidence["theorem_established"]
                  and evidence["satisfiability_established"] is True and evidence["claim_satisfiability"] is True,
                  "typed recorded API claim category consistency")
    for name in ("model", "proof", "unsat_core"):
        artifact(evidence[name], name)
    backend(value["backend_result"], evidence, request, "z3" if request["provider"] == "differential" else request["provider"])
    differential = value["differential_report"]
    if request["provider"] == "differential":
        codec.require(type(differential) is dict and differential["agreement"] is True and differential["left_backend_id"] == "z3"
                      and differential["right_backend_id"] == "cvc5" and differential["left_verdict"] == differential["right_verdict"] == evidence["solver_verdict"], "differential peer agreement identities")
        for side, provider in (("left", "z3"), ("right", "cvc5")):
            peer = differential[side]
            peer_evidence = {**evidence, "solver_version": peer["solver_version"]}
            backend(peer["result"], peer_evidence, request, provider)
            codec.require(peer["script_digest"] == evidence["script_digest"] and peer["obligation_id"] == evidence["obligation_id"], "differential common request/script")
        codec.require(value["backend_result"] == differential["left"]["result"] and evidence["differential"]["agreement"] is True
                      and evidence["differential"]["script_digest"] == evidence["script_digest"]
                      and evidence["differential"]["left_verdict"] == evidence["differential"]["right_verdict"] == evidence["solver_verdict"], "differential primary/evidence binding")
        codec.require(differential["classification"] == evidence["differential"]["classification"] == "agree_" + evidence["disposition"]
                      and evidence["differential"]["left_backend_id"] == "z3" and evidence["differential"]["right_backend_id"] == "cvc5"
                      and evidence["differential"]["disagreement_preserved"] is False, "differential recorded classification/provider correspondence")
    else:
        codec.require(differential is None and evidence["differential"] is None, "single provider has no fabricated peer")
    if request["mode"] == "hermetic_fixture":
        replay(evidence["replay"], evidence)
    else:
        codec.require(evidence["replay"] is None, "pinned mode automatic replay absent")
    return {"request_id": request["request_id"], "provider": request["provider"], "mode": request["mode"],
            "request_sha256": hashed(request), "obligation_sha256": hashed(request["obligation"]),
            "evidence_identity_sha256": evidence["content_digest"], "declared_bounds": request["bounds"],
            "recorded_disposition": evidence["disposition"], "recorded_verdict": evidence["solver_verdict"],
            "recorded_api_claim_categories": {name: evidence[name] for name in ("theorem_established", "satisfiability_established", "proof_established", "is_proved")},
            "script_sha256_claim": evidence["script_digest"], "solver_verdict_authenticated": False,
            "caller_request_origin": "independent_outer_wire_fixture" if original_request is not None else "result_embedded_request_with_independent_fixture_obligation"}


def frozen_wire_sources(before, after):
    trees = [ast.parse(raw.decode("utf-8")) for raw in (before, after)]
    classes = [{node.name: node for node in tree.body if isinstance(node, ast.ClassDef)} for tree in trees]
    for name in WIRE_CLASSES:
        codec.require(ast.dump(classes[0][name], include_attributes=False) == ast.dump(classes[1][name], include_attributes=False), "frozen wire definition changed")
    method = next(node for node in classes[0]["SmtProviderEvidenceV2"].body if isinstance(node, ast.FunctionDef) and node.name == "_identity_payload")
    codec.require({key.value for key in method.body[0].value.keys} == IDENTITY_FIELDS, "frozen evidence identity payload codec")
    return list(WIRE_CLASSES)


def wire_fixtures(before, after, comparison, sources):
    codec.require(before["source_sha256"] == codec.sha(sources[0]) and after["source_sha256"] == codec.sha(sources[1]), "wire/source generation raw binding")
    rows = bounded_list(before["cases"], 12)
    expected_keys = [f"{goal}:{provider}:{mode}" for goal in ("proved", "satisfiable") for provider in ("z3", "cvc5", "differential") for mode in ("pinned_solver", "hermetic_fixture")]
    codec.require(len(rows) == 12 and [row["key"] for row in rows] == expected_keys and codec.equal(rows, after["cases"]), "complete original before/after wire fixture order")
    codec.require(comparison["case_count"] == 12 and type(comparison["case_count"]) is int and comparison["all_complete_wire_values_equal"] is True
                  and comparison["controls_are_runtime_only"] is True and comparison["runtime_before_sha256"] == codec.sha(sources[0])
                  and comparison["runtime_after_sha256"] == codec.sha(sources[1]), "wire comparison original source commitments")
    results = []
    for row in rows:
        codec.closed(row, {"key", "request", "result", "replay"}, "original wire fixture")
        record = outcome(row["result"], original_request=row["request"])
        replay(row["replay"], row["result"]["evidence"])
        codec.require(record["recorded_disposition"] == row["key"].split(":")[0], "wire key disposition")
        results.append({"key": row["key"], **record})
    return results


def phase_receipts(launches, lifecycles, expected_counts, cases):
    codec.require(len(bounded_list(launches, MAX_PHASES)) == len(bounded_list(lifecycles, MAX_PHASES)) == 446, "complete 446 phase observations")
    launched, completed = defaultdict(list), defaultdict(list)
    for value in launches:
        codec.closed(value, {"argv", "at_monotonic", "case", "launch_lease_id", "owned_leases", "root_allocations", "thread", "waiting"}, "recorded launch")
        number(value["at_monotonic"])
        exact_int(value["thread"], 1)
        codec.require(type(value["case"]) is str and value["case"] in expected_counts, "launch case coverage")
        argv = bounded_list(value["argv"], 32)
        codec.require(all(type(arg) is str for arg in argv) and "--" in argv and Path(argv[0]).name == "prlimit", "recorded bounded launch wrapper")
        leases = bounded_list(value["owned_leases"], 16)
        codec.require(sum(lease["lease_id"] == value["launch_lease_id"] for lease in leases) == 1, "recorded launch lease population")
        launched[value["case"]].append(value)
    for value in lifecycles:
        codec.closed(value, {"case", "request", "result", "shared_backoff_after"}, "recorded phase lifecycle")
        codec.require(type(value["case"]) is str and value["case"] in expected_counts, "lifecycle case coverage")
        completed[value["case"]].append(value)
    codec.require({name: len(rows) for name, rows in launched.items()} == {name: len(rows) for name, rows in completed.items()} == expected_counts, "launch/lifecycle complete case populations")
    receipts = []
    for name, count in expected_counts.items():
        previous = -1
        for ordinal, (launch, completion) in enumerate(zip(launched[name], completed[name], strict=True)):
            request, result = completion["request"], completion["result"]
            codec.closed(request, PHASE_REQUEST_FIELDS, "native phase request")
            argv = launch["argv"]
            command = argv[argv.index("--") + 1:]
            codec.require(command and request["argv"] and Path(command[0]).name == request["argv"][0]
                          and command[1:] == request["argv"][1:] and result["command"] == request["argv"], "case ordinal phase command correspondence")
            codec.require(launch["at_monotonic"] >= previous, "case-local launch order")
            previous = launch["at_monotonic"]
            timeout = number(request["timeout_seconds"], 5)
            codec.require(timeout > 0, "positive remaining phase timeout")
            memory = exact_int(request["memory_bytes"], 1)
            codec.require(request["resident_memory_bytes"] == memory and type(request["resident_memory_bytes"]) is int
                          and f"--as={memory}:{memory}" in argv, "phase declared memory/argv limit binding")
            budget = exact_int(request["max_output_bytes"], 1, 1048576)
            codec.require(type(result["stdout"]) is str and type(result["stderr"]) is str
                          and len(result["stdout"].encode()) + len(result["stderr"].encode()) <= budget, "recorded phase output budget")
            codec.require(result["runtime"] == "native" and result["workspace_cleaned"] is True
                          and result["output_truncated"] is False and result["unavailable"] is False, "recorded native phase disposition")
            for flag in ("cancelled", "timed_out", "resource_exhausted", "process_tree_terminated", "workspace_limit_exceeded"):
                codec.require(type(result[flag]) is bool, "typed native lifecycle Boolean")
            codec.require(type(result["returncode"]) is int or (result["returncode"] is None and (result["cancelled"] or result["timed_out"])),
                          "exact recorded native return code")
            codec.require(request["terminal_command"] in {"", "(check-sat)", "(get-model)", "(get-unsat-core)"}, "recorded phase terminal request")
            digest(request["stdin_sha256"])
            if name in cases:
                ceiling = cases[name]["declared_bounds"]
                codec.require(timeout * 1000 <= ceiling["timeout_ms"] and memory == ceiling["max_memory_bytes"]
                              and budget <= ceiling["max_output_bytes"] and result["cancelled"] is False
                              and result["timed_out"] is False and result["returncode"] == 0, "successful case phase declared budget/disposition")
            receipts.append({"case": name, "ordinal_within_case": ordinal, "terminal_command": request["terminal_command"],
                "argv_sha256": hashed(request["argv"]), "stdin_sha256_claim": request["stdin_sha256"],
                "stdout_sha256": codec.sha(result["stdout"].encode()), "stderr_sha256": codec.sha(result["stderr"].encode()),
                "declared_remaining_timeout_seconds": timeout, "declared_memory_bytes": memory, "declared_output_bytes": budget,
                "recorded_termination_reason": result["termination_reason"], "join_basis": "retained_case_local_order_and_command",
                "unique_phase_execution_attestation_verified": False, "raw_stdin_available": False})
        codec.require(count == len(launched[name]), "phase population retained")
    return receipts


def receive(documents, sources):
    q, native, command = (documents[name] for name in ("prior_qualification", "native_result", "native_command"))
    codec.require(q["schema"] == "smt-v2-operation-control-qualification@1" and q["status"] == "passed_partial_scope"
                  and q["production_tasks_closed"] == [], "frozen qualification partial scope")
    codec.require(native["schema"] == "smt-v2-operation-control-benchmark@1" and native["status"] == "passed"
                  and q["native_checks"] == native["checks"] and all(value is True for value in native["checks"].values()), "whole selected native operation checks")
    codec.require(native["source_pins_before"] == native["source_pins_after"], "recorded source pins stable")
    codec.closed(command, {"argv", "cwd", "environment"}, "original benchmark command")
    codec.require(command["argv"] == ["benchmarks/bench_smt_v2_operation_control.py", "--output", "workspace/smt-v2-operation-control-qualification-20261003/native-selected"], "retained original benchmark invocation")
    definitions = frozen_wire_sources(*sources)
    wires = wire_fixtures(documents["wire_before"], documents["wire_after"], documents["wire_comparison"], sources)
    for role in ("launch_audit", "lifecycle_audit", "control_audit"):
        codec.require(native[ROLES[role].split("/")[-1] + "_sha256"] == hashed_raw_document(documents[role]), "native independently retained phase audit binding")
    runs = bounded_list(native["runs"], 3)
    codec.require(len(runs) == 3 and [run["workers"] for run in runs] == [1, 2, 4] and all(type(run["workers"]) is int for run in runs), "three original caller matrices")
    cases, counts, records = {}, {}, []

    def successful(value):
        name = value["case"]
        codec.require(type(name) is str and name not in cases and type(value["valid"]) is bool, "unique typed original case")
        record = outcome(value["outcome"], original_obligation=value["fixture"], expected_provider=value["provider"], expected_mode=value["mode"])
        codec.require(record["request_id"] == "req:v2:" + name and record["declared_bounds"]["timeout_ms"] == value["default_aggregate_timeout_ms"]
                      and type(value["default_aggregate_timeout_ms"]) is int
                      and record["recorded_disposition"] == ("proved" if value["valid"] else "disproved"), "original native case request/disposition")
        replay(value["explicit_replay"], value["outcome"]["evidence"])
        count = (12 if value["provider"] == "differential" else 6) + (6 if value["mode"] == "hermetic_fixture" else 0)
        codec.require(type(value["phase_count"]) is int and value["phase_count"] == count, "complete case automatic/explicit replay phases")
        cases[name], counts[name] = record, count
        records.append({"case": name, "phase_count": count, **record})

    for run in runs:
        values = bounded_list(run["cases"], 12)
        expected = {f"parallel:{run['workers']}:0:{provider}:{mode}:{valid}" for provider in ("z3", "cvc5", "differential") for mode in ("pinned_solver", "hermetic_fixture") for valid in (True, False)}
        codec.require(len(values) == 12 and {value["case"] for value in values} == expected, "complete duplicate-free original case matrix")
        for value in values:
            successful(value)
    nested = bounded_list(native["nested_cases"], 2)
    codec.require([value["case"] for value in nested] == ["nested:differential:hermetic_fixture:True", "nested:cvc5:hermetic_fixture:False"], "two parent-owned recorded cases")
    for value in nested:
        successful(value)
    controls = bounded_list(native["controls"], 6)
    codec.require([value["case"] for value in controls] == list(CONTROL_NAMES), "complete six stop controls")
    stops = []
    audit = documents["control_audit"]
    codec.closed(audit, {"completed_peers", "native_starts", "triggers", "v2_boundaries"}, "independent stop observations")
    for index, value in enumerate(controls):
        kind = "timeout" if index == 1 else "cancelled"
        codec.require(value["returned_result"] is False and value["no_followup_launch"] is True
                      and value.get("returned_replay_receipt", False) is False and value["expected_kind"] == kind
                      and value["exception"]["kind"] == kind and value["exception_type"] == ("ProofOperationTimeout" if kind == "timeout" else "ProofOperationCancelled"), "typed stop withholds evidence and replay")
        expected_phases = [1, 1, 3, 3, 9, 3][index]
        codec.require(value["phase_count"] == expected_phases and value["launch_count"] == expected_phases
                      and type(value["phase_count"]) is int and type(value["launch_count"]) is int, "exact stopped phase populations")
        counts[value["case"]] = expected_phases
        if index == 4:
            counts[value["case"]] = 3
            counts[value["case"] + ":original"] = 6
            outcome(value["original_result"])
        for field, section in (("trigger", "triggers"), ("native_start", "native_starts")):
            if field in value:
                codec.require(sum(codec.equal(value[field], item) for item in audit[section]) == 1, "independent stop boundary correspondence")
        stops.append({"case": value["case"], "recorded_stop_kind": kind, "phase_count": expected_phases,
                      "returned_result": False, "returned_replay_receipt": False, "current_stop_execution_verified": False})
    phases = phase_receipts(documents["launch_audit"], documents["lifecycle_audit"], counts, cases)
    codec.require(q["native_cases"] == 36 and q["native_nested_cases"] == 2 and q["native_launches"] == q["native_lifecycles"] == native["launches"] == native["lifecycles"] == 446, "independent qualification full phase totals")
    return {"cases": records, "stopped_calls": stops, "phase_receipts": phases, "wire_fixtures": wires,
            "unchanged_wire_definitions": definitions, "phase_join_scope": "case-local recorded order and commands; no unique phase ID or execution authentication"}


def hashed_raw_document(value):
    # Actual public audit writers serialize sorted, indented UTF-8 JSON.
    return codec.sha((json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode())


def load_input(manifest):
    capture = Capture()
    spec = codec.document(capture.take(manifest, limit=codec.MAX_MANIFEST), codec.MAX_MANIFEST)
    codec.closed(spec, {"schema", *ROLES}, "SMT input manifest")
    codec.require(spec["schema"] == INPUT_SCHEMA, "SMT input schema")
    for role in ROLES:
        codec.descriptor(spec[role], original=role != "prior_qualification")
    codec.require(spec["prior_qualification"]["sha256"] == QUALIFICATION_SHA and spec["prior_qualification"]["bytes"] == 137146
                  and spec["native_result"]["sha256"] == NATIVE_RESULT_SHA, "fixed independent qualification and native-result anchors")
    documents, sources = {}, []
    namespace = Path(spec["native_result"]["original_path"]).parent.parent
    for role, relative in ROLES.items():
        descriptor = spec[role]
        raw = capture.take(codec.canonical_path(descriptor["path"]), descriptor)
        if role != "prior_qualification":
            codec.require(descriptor["original_path"] == str(namespace / relative)
                          and documents["prior_qualification"]["artifact_sha256"].get(relative) == descriptor["sha256"], "independent public role/raw commitment")
        if role.startswith("runtime_"):
            sources.append(raw)
        else:
            documents[role] = document(raw, MAX_FILE)
    codec.require(documents["wire_comparison"]["before_sha256"] == spec["wire_before"]["sha256"]
                  and documents["wire_comparison"]["after_sha256"] == spec["wire_after"]["sha256"], "independent original wire raw pins")
    return capture, spec, documents, sources


def audit(manifest, output):
    manifest, output = codec.canonical_path(str(manifest)), codec.canonical_path(str(output))
    capture, spec, documents, sources = load_input(manifest)
    protected = {path.parent for path in capture.raw if path != manifest}
    protected.update(codec.canonical_path(spec[role]["original_path"]).parent for role in ROLES if role != "prior_qualification")
    resolved = output.resolve()
    codec.require(not output.exists() and not output.is_symlink()
                  and all(resolved != path.resolve() and path.resolve() not in resolved.parents for path in protected),
                  "fresh output outside frozen/original input scopes")
    received = receive(documents, sources)
    negative = mutation_controls(documents, sources)
    capture.stable()
    output.mkdir(parents=True, exist_ok=False)
    (output / "inputs").mkdir()
    retained = []
    for index, (path, raw) in enumerate(capture.raw.items()):
        destination = output / "inputs" / f"{index:02d}-{path.name}"
        destination.write_bytes(raw)
        codec.require(codec.OriginalCapture.read(destination, len(raw)) == raw, "SMT retained raw copy")
        retained.append({"path": str(path), "retained_path": str(destination), "sha256": codec.sha(raw), "bytes": len(raw)})
    capture.stable()
    for row in retained:
        codec.require(codec.sha(codec.OriginalCapture.read(Path(row["retained_path"]), row["bytes"])) == row["sha256"], "SMT retained copy drift")
    report = {"schema": REPORT_SCHEMA, "status": "passed", "scope": "selected_historical_smt_v2_protocol_custody_not_solver_or_resource_authentication",
              "historical_qualification_status": documents["prior_qualification"]["status"],
              "input_origin": "retained_native_operation_records_with_separate_deterministic_injected_wire_fixtures",
              "count_scope": "recorded_historical_observations_only",
              "manifest_sha256": codec.sha(capture.raw[manifest]), **{role + "_sha256": spec[role]["sha256"] for role in ROLES},
              **dict.fromkeys(TRUE_FLAGS, True), **dict.fromkeys(FALSE_FLAGS, False), "runtime_fact_count": 0, "tasks_omitted_count": 0,
              "additional_attempted_training_epochs": 0, "baseline_case_count": 36, "nested_case_count": 2, "interruption_control_count": 6,
              "native_launch_count": 446, "native_lifecycle_count": 446, "baseline_phase_count": 396, "nested_phase_count": 30,
              "interruption_phase_count": 20, "wire_fixture_case_count": 12, "unchanged_wire_definition_count": 6,
              "input_file_count": len(retained), "input_bytes": capture.total, "mutation_control_count": len(negative),
              "limits": {"max_files": MAX_FILES, "max_file_bytes": MAX_FILE, "max_total_bytes": MAX_TOTAL,
                         "max_manifest_bytes": codec.MAX_MANIFEST, "max_phases": MAX_PHASES, "max_cases": MAX_CASES},
              "input_files": retained, "received": received, "mutation_controls": negative,
              "recorded_producer_effort": {"qualification": "historical_recorded_claims_only", "elapsed_seconds": documents["native_result"]["elapsed_seconds"],
                  "elapsed_seconds_by_workers": documents["native_result"]["elapsed_seconds_by_workers"], "child_usage": documents["native_result"]["child_usage"]},
              "limitations": ["Frozen raw qualification/result anchors are unsigned; authentic solver execution, source truth and proof certificates are not established.",
                  "Native complete caller requests are only embedded in results; independent outer fixtures bind obligations, providers and modes. Injected wire cases have independent outer requests and are reported separately.",
                  "Phase stdin bodies were not retained; their digest claims cannot be recomputed from the selected closure. No script compiler or solver is invoked.",
                  "Launch/lifecycle joins use retained case-local ordinal and command correspondence, not unique shared phase IDs; repeated identical phases have no independent unique invocation attestation.",
                  "Recorded limits, leases, output and stops are protocol observations, not present resource enforcement, host containment or current authority.",
                  "Historical original path, executable, cwd and source URI strings are provenance labels and never opened by this receiver. Only selected frozen private inputs and retained copies are reread.",
                  "Runtime pre/post sources are inert AST input; six wire definitions are compared without importing their owners."]}
    (output / "smt_v2_custody.json").write_bytes(codec.wire(report) + b"\n")
    return report


def mutation_controls(documents, sources):
    results = []

    def run(name, mutate):
        changed = copy.deepcopy(documents)
        mutate(changed)
        # Rehash mutable request/evidence containers, keeping independent fixture
        # obligations, original requests, qualification and separate audits fixed.
        for suite in changed["native_result"]["runs"]:
            for case in suite["cases"]:
                evidence = case["outcome"]["evidence"]
                evidence["request_digest"] = hashed(case["outcome"]["request"])
                evidence["obligation_digest"] = hashed(case["outcome"]["request"]["obligation"])
                evidence["content_digest"] = hashed({key: evidence[key] for key in IDENTITY_FIELDS})
        for role in ("launch_audit", "lifecycle_audit", "control_audit"):
            changed["native_result"][ROLES[role].split("/")[-1] + "_sha256"] = hashed_raw_document(changed[role])
        try:
            receive(changed, sources)
        except (codec.ReceiverRefusal, KeyError, TypeError, ValueError, StopIteration):
            results.append({"name": name, "mutable_identity_digests_recomputed": True, "independent_anchors_preserved": True, "rejected": True})
            return
        raise codec.ReceiverRefusal("SMT mutation control accepted: " + name)

    def first(value):
        return value["native_result"]["runs"][0]["cases"][0]

    run("independent_fixture_goal_substitution", lambda value: first(value)["outcome"]["request"]["obligation"]["goal"].update(kind="lt"))
    run("request_provider_substituted", lambda value: first(value)["outcome"]["request"].update(provider="cvc5"))
    run("request_declared_budget_changed", lambda value: first(value)["outcome"]["request"]["bounds"].update(timeout_ms=6000))
    run("request_identity_substituted", lambda value: first(value)["outcome"]["request"].update(request_id="req:other"))
    run("replay_script_substituted", lambda value: first(value)["explicit_replay"].update(script_digest="0" * 64))
    run("replay_disposition_swapped", lambda value: first(value)["explicit_replay"].update(replayed_disposition="disproved"))
    run("kernel_proof_claim_promoted", lambda value: first(value)["outcome"]["evidence"].update(proof_established=True))
    run("integer_alias_in_evidence", lambda value: first(value)["outcome"]["evidence"].update(is_conclusive=1))
    run("case_omitted", lambda value: value["native_result"]["runs"][-1]["cases"].pop())
    run("case_duplicate", lambda value: value["native_result"]["runs"][-1]["cases"].append(copy.deepcopy(value["native_result"]["runs"][-1]["cases"][0])))
    run("whole_operation_failed", lambda value: value["native_result"].update(status="failed"))
    run("late_integrity_check_failed", lambda value: value["native_result"]["checks"].update(sources_stable=False))
    run("source_generation_drift", lambda value: value["native_result"]["source_pins_after"].update({next(iter(value["native_result"]["source_pins_after"])): "0" * 64}))
    run("stop_returns_result", lambda value: value["native_result"]["controls"][0].update(returned_result=True))
    run("stop_returns_late_replay", lambda value: value["native_result"]["controls"][4].update(returned_replay_receipt=True))
    run("stop_kind_swapped", lambda value: value["native_result"]["controls"][1]["exception"].update(kind="cancelled"))
    run("original_wire_request_changed", lambda value: value["wire_after"]["cases"][0]["request"]["bounds"].update(timeout_ms=6000))
    run("original_wire_case_order_changed", lambda value: value["wire_after"]["cases"].reverse())
    run("original_wire_case_omitted", lambda value: value["wire_after"]["cases"].pop())
    run("benchmark_invocation_changed", lambda value: value["native_command"]["argv"].append("--widen-limits"))
    run("lifecycle_phase_omitted", lambda value: value["lifecycle_audit"].pop())
    run("launch_phase_duplicated", lambda value: value["launch_audit"].append(copy.deepcopy(value["launch_audit"][0])))
    run("lifecycle_case_substituted", lambda value: value["lifecycle_audit"][0].update(case="not:original-case"))
    run("phase_command_substituted", lambda value: value["lifecycle_audit"][0]["request"]["argv"].append("--unrecorded-option"))
    run("phase_memory_exceeds_original_request", lambda value: [value["lifecycle_audit"][0]["request"].update(memory_bytes=268435456, resident_memory_bytes=268435456),
        value["launch_audit"][0]["argv"].__setitem__(4, "--as=268435456:268435456")])
    run("phase_remaining_timeout_exceeds_request", lambda value: value["lifecycle_audit"][0]["request"].update(timeout_seconds=6.0))
    run("phase_output_exceeds_recorded_budget", lambda value: value["lifecycle_audit"][0]["request"].update(max_output_bytes=1))
    run("success_phase_cancelled", lambda value: value["lifecycle_audit"][0]["result"].update(cancelled=True))
    run("phase_cleanup_integer_alias", lambda value: value["lifecycle_audit"][0]["result"].update(workspace_cleaned=1))
    run("launch_lease_identity_missing", lambda value: value["launch_audit"][0].update(launch_lease_id="not:recorded-lease"))
    run("stop_independent_trigger_changed", lambda value: value["native_result"]["controls"][0]["trigger"].update(kind="timeout"))
    run("model_or_core_artifact_digest_changed", lambda value: first(value)["outcome"]["evidence"]["unsat_core"].update(digest="0" * 64))
    run("automatic_replay_omitted", lambda value: value["native_result"]["runs"][0]["cases"][2]["outcome"]["evidence"].update(replay=None))
    run("differential_right_peer_substituted", lambda value: value["native_result"]["runs"][0]["cases"][8]["outcome"]["differential_report"]["right"]["result"].update(backend_id="z3"))
    run("phase_returncode_boolean_alias", lambda value: value["lifecycle_audit"][0]["result"].update(returncode=False))
    run("evidence_kernel_authority_promoted", lambda value: first(value)["outcome"]["evidence"].update(authority_ceiling="kernel"))
    run("differential_classification_swapped", lambda value: value["native_result"]["runs"][0]["cases"][8]["outcome"]["evidence"]["differential"].update(classification="agree_disproved"))
    return results


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
    print(json.dumps({"status": "passed", "phases": report["native_lifecycle_count"], "cases": report["baseline_case_count"], "controls": report["mutation_control_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
