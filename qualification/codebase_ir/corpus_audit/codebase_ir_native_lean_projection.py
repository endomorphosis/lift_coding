#!/usr/bin/env python3
"""Compare inert emitted Lean declarations with exact source-bound ProgramIR.

This closed offline profile parses exported text; it never runs a compiler,
checker, numerical producer, source program or production owner module.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import codebase_ir_corpus_audit as audit
import codebase_ir_final_evaluation as final
import codebase_ir_final_lock as lock_tool
import codebase_ir_native_program_graph as graph_tool
import codebase_ir_native_source384_diagnostics as native
import codebase_ir_native_source_comparison as comparison

INPUT_SCHEMA = "codebase-ir-native-lean-projection-input@1"
REPORT_SCHEMA = "codebase-ir-native-lean-projection@1"
PROFILE = "qualification/source-bound-two-int-binary-lean-projection@1"
BODY_ROLES = ("learned_lake_receipt", "learned_lean", "source_label_baseline_lake_receipt", "source_label_baseline_lean")
INPUT_ROLES = ("program_graph_input", "program_graph_report", *BODY_ROLES)
PUBLIC_PATHS = dict(zip(BODY_ROLES, ("public/learned-lake/receipt.json", "public/learned-lake/SecuritySourcePrograms.lean",
                                   "public/model-off-lake/receipt.json", "public/model-off-lake/SecuritySourcePrograms.lean"), strict=True))
TRUE_FLAGS = {"lean_projection_conformance_available", "program_graph_independently_rederived", "projection_evidence_reconciled",
              "raw_lean_bodies_retained_unmodified", "source_label_baseline_separate", "input_files_unchanged", "unknown_pretraining_exposure"}
FALSE_FLAGS = graph_tool.FALSE_FLAGS | {"compiler_output_semantics_verified", "operational_semantics_verified", "native_checker_results_replayed",
    "universal_semantics_verified", "semantic_projection_loss_certified", "producer_execution_authenticated"}
AUTHORITY_FIELDS = {"admitted", "claim_proved", "completion_authority", "execution_authority", "formalized", "promotion_performed",
                    "proof_authority", "security_specification_inferred", "source_semantics_verified", "whole_program_semantics_verified"}
RECEIPT_FIELDS = AUTHORITY_FIELDS | {"all_candidates_compiled", "assumptions", "backend_executed", "count", "execution", "input_sha256",
    "lean_source", "lean_source_sha256", "library", "producer", "rows", "schema", "scope", "source_replay_passed", "status", "supported_count",
    "tool_binary_sha256", "tool_pin_scope"}
ROW_FIELDS = AUTHORITY_FIELDS | {"candidate_sha256", "id", "lake_status", "lean_declarations_sha256", "lowering", "parser_status", "program_sha256",
    "reason", "semantic_lowering_supported", "source_qualification", "source_sha256"}
LOWERING_FIELDS = {"actual_reads", "actual_writes", "assumptions", "complete_read_write_summaries_checked", "completion_authority", "effect_audit",
    "effect_audit_sha256", "execution_authority", "metadata_emitted_as_explicit_evidence", "operational_view_program_id", "operational_view_sha256",
    "operational_view_transformation", "operators", "original_metadata_sha256", "original_program_id", "original_program_modified",
    "original_source_references", "profile", "program_sha256", "proof_authority", "security_specification_inferred", "source_bytes_replayed",
    "source_hash_consistency_checked", "source_semantics_verified", "validator", "whole_program_semantics_verified"}
EVIDENCE_FALSE = ("proof_authority", "execution_authority", "completion_authority", "source_semantics_verified",
                  "whole_program_semantics_verified", "security_specification_inferred")


@dataclass(frozen=True)
class Limits:
    max_files: int = 32
    max_file_bytes: int = 2 * 1024 * 1024
    max_total_bytes: int = 40 * 1024 * 1024
    max_rows: int = 32
    max_lean_bytes: int = 64 * 1024
    max_lean_lines: int = 2048

    def __post_init__(self):
        audit._require(all(type(v) is int and v > 0 for v in asdict(self).values()), "positive exact Lean projection limits required")


DEFAULT_LIMITS = Limits()


def _json(raw, limits):
    return audit._load_json(raw, audit.Limits(max_json_bytes=limits.max_file_bytes, max_json_nodes=100_000))


def _false(value, fields):
    audit._require(all(value[key] is False for key in fields), "Lean receipt authority/source semantics elevation")


def _lean_string(value):
    # The declared archive profile uses JSON-compatible Lean string escapes.
    audit._require(type(value) is str and all(ord(c) >= 32 for c in value), "bounded printable evidence string required")
    return json.dumps(value, ensure_ascii=False)


def _strings(values):
    audit._require(type(values) is list and len(values) <= 128, "bounded Lean string list required")
    return "[" + ", ".join(_lean_string(value) for value in values) + "]"


def _sections(raw, limits):
    audit._require(len(raw) <= limits.max_lean_bytes and b"\r" not in raw, "Lean body byte/newline profile bound")
    try:
        text = raw.decode("utf-8")
    except UnicodeError as exc:
        raise audit.AuditInputError("Lean UTF-8 required") from exc
    lines = text.splitlines(keepends=True)
    audit._require(len(lines) <= limits.max_lean_lines and text.endswith("\n"), "bounded LF-terminated Lean text required")
    meaningful = [(index, line.strip()) for index, line in enumerate(lines) if line.strip()]
    audit._require(meaningful and meaningful[0][1] == "namespace SecuritySourcePrograms"
                   and meaningful[-1][1] == "end SecuritySourcePrograms", "closed Lean outer namespace required")
    sections, current, start = [], None, None
    for index, line in meaningful[1:-1]:
        if current is None:
            audit._require(line == "namespace Candidate_" + str(len(sections)), "ordered closed Lean candidate namespace required")
            current, start = [], index + 1
        elif line == "end Candidate_" + str(len(sections)):
            sections.append({"lines": current, "raw": "".join(lines[start:index]).encode("utf-8")})
            current, start = None, None
        else:
            audit._require(not line.startswith(("namespace ", "end ", "import ", "axiom ", "opaque ")),
                           "unexpected nested namespace/import/axiom in Lean projection")
            current.append(line)
    audit._require(current is None and len(sections) <= limits.max_rows, "complete bounded Lean namespace population required")
    return sections


def _evidence_pairs(rows, identity, footprint):
    return "[" + ", ".join("(" + _lean_string(row[identity]) + ", " + _strings(row["effects"][footprint]) + ")"
                           for row in sorted(rows, key=lambda x: x[identity])) + "]"


def _declarations(graph, lowering):
    """Reconstruct this closed textual projection from the pinned graph only."""
    metadata = graph["metadata"]
    operational = copy.deepcopy(graph)
    operational["metadata"] = {}
    # The producer's program ID is a recorded label. Its enclosing body digest
    # is independently recomputed; this does not authenticate that ID's origin.
    operational["program_id"] = lowering["operational_view_program_id"]
    operational_sha = audit._sha(audit._canonical(operational))
    strings = {
        "sourceEvidenceOriginalProgramSHA256": audit._sha(audit._canonical(graph)),
        "sourceEvidenceOperationalViewSHA256": operational_sha,
        "sourceEvidenceSourceSHA256": metadata["source_sha256"],
        "sourceEvidenceMetadataJSON": audit._canonical(metadata).decode("utf-8"),
        "sourceEvidenceSourceReferencesJSON": audit._canonical(graph["sources"]).decode("utf-8"),
        "sourceEvidenceEffectAuditJSON": audit._canonical(metadata["effect_summary_audit"]).decode("utf-8"),
    }
    lines = ["def " + name + " : String := " + _lean_string(value) for name, value in strings.items()]
    lines.append("def sourceEvidenceAssumptions : List String := " + _strings([*metadata["assumptions"], metadata["effect_summary_assumption"]]))
    lines.extend("def sourceEvidence_" + key + " : Bool := false" for key in EVIDENCE_FALSE)
    for collection, identity in (("commands", "command_id"), ("functions", "function_id")):
        for footprint in ("reads", "writes"):
            lines.append("def sourceEvidence_" + collection + "_" + footprint + " : List (String × List String) := "
                         + _evidence_pairs(graph[collection], identity, footprint))
    lines += ["set_option linter.unusedVariables false", "structure Store where"]
    symbols = sorted(graph["symbols"], key=lambda x: x["symbol_id"])
    slots = {symbol["symbol_id"]: "v" + str(index) for index, symbol in enumerate(symbols)}
    lines += [slots[s["symbol_id"]] + " : Int" for s in symbols]
    lines += ["deriving DecidableEq", "inductive Outcome where", "| returned (store : Store) (value : Int)",
              "| blocked", "| assertionFailure", "deriving DecidableEq"]
    expressions = sorted(graph["expressions"], key=lambda x: x["expression_id"])
    exprs = {row["expression_id"]: row for row in expressions}
    expr_names = {row["expression_id"]: "expression_" + str(index) for index, row in enumerate(expressions)}

    def expression(identity, seen):
        audit._require(identity in exprs and identity not in seen, "unresolved or cyclic emitted expression reference")
        row = exprs[identity]
        if row["kind"] == "symbol":
            audit._require(len(row["symbol_ids"]) == 1 and row["symbol_ids"][0] in slots, "unresolved emitted symbol slot")
            return "current." + slots[row["symbol_ids"][0]]
        audit._require(row["kind"] == "binary" and row["operator"] in {"add", "sub", "mul"} and len(row["operand_ids"]) == 2,
                       "unsupported emitted arithmetic expression")
        operator = {"add": "+", "sub": "-", "mul": "*"}[row["operator"]]
        return "(" + expression(row["operand_ids"][0], seen | {identity}) + " " + operator + " " + expression(row["operand_ids"][1], seen | {identity}) + ")"

    for row in expressions:
        lines.append("def " + expr_names[row["expression_id"]] + " (initial current : Store) (returned : Int) : Int := "
                     + expression(row["expression_id"], set()))
    audit._require(len(graph["commands"]) == 1 and graph["commands"][0]["kind"] == "return", "one emitted return required")
    command = graph["commands"][0]
    audit._require(len(command["expression_ids"]) == 1 and command["expression_ids"][0] in expr_names, "return expression not resolvable")
    lines += ["def run (initial : Store) : Outcome :=", "let current := initial;",
              "Outcome.returned current (" + expr_names[command["expression_ids"][0]] + " initial current (0 : Int))"]
    reads, writes = graph["functions"][0]["effects"]["reads"], graph["functions"][0]["effects"]["writes"]
    for name, values in (("Reads", reads), ("Writes", writes)):
        lines.append("def declared" + name + " (symbol : String) : Bool := " + _strings(values) + ".contains symbol")
        lines.append("example : (" + _strings(values) + " : List String).all declared" + name + " = true := by decide")
    return lines, slots, expr_names, operational_sha


def _receipt(raw, lean_raw, limits):
    value = audit._closed(_json(raw, limits), RECEIPT_FIELDS, "released Lake receipt")
    audit._require(value["schema"] == "source-program-384-lake/v1" and value["library"] == "SecuritySourcePrograms", "closed Lake library/schema required")
    _false(value, AUTHORITY_FIELDS)
    for flag in ("all_candidates_compiled", "backend_executed", "source_replay_passed"):
        audit._require(type(value[flag]) is bool, "exact recorded Lake Boolean required")
    for count in ("count", "supported_count"):
        audit._require(type(value[count]) is int and 0 <= value[count] <= limits.max_rows, "bounded exact Lake population required")
    audit._require(type(value["rows"]) is list and len(value["rows"]) == value["count"], "whole Lake row population differs")
    audit._digest(value["input_sha256"], "claimed compiler input SHA")
    audit._require(value["lean_source_sha256"] == audit._sha(lean_raw) and value["lean_source"].encode("utf-8") == lean_raw,
                   "receipt and exact emitted Lean body differ")
    audit._require(type(value["execution"]) is dict and value["execution"].get("backend_executed") is value["backend_executed"], "recorded Lake execution metadata inconsistent")
    rows, supported = {}, 0
    for index, row in enumerate(value["rows"]):
        audit._closed(row, ROW_FIELDS, "released compiler row")
        _false(row, AUTHORITY_FIELDS)
        name = audit._text(row["id"], "Lake native ID")
        audit._require(name not in rows, "duplicate Lake native ID")
        for key in ("source_sha256", "candidate_sha256", "program_sha256", "lean_declarations_sha256"):
            audit._digest(row[key], "recorded Lake row " + key)
        audit._require(type(row["semantic_lowering_supported"]) is bool, "exact compiler supported disposition required")
        supported += row["semantic_lowering_supported"]
        rows[name] = (index, row)
    audit._require(supported == value["supported_count"], "Lake supported denominator differs")
    return value, rows


def _join(graph, summary, row, original_contract):
    audit._require(row["source_sha256"] == graph["metadata"]["source_sha256"] and row["program_sha256"] == audit._sha(audit._canonical(graph)),
                   "compiler row source/program differs from source-bound graph")
    audit._require(row["source_qualification"] == original_contract and row["candidate_sha256"] == original_contract["candidate_sha256"],
                   "compiler source qualification or original candidate substituted")
    audit._require(row["parser_status"] == row["lake_status"] == "passed" and row["semantic_lowering_supported"] is True,
                   "supported projection contradicts recorded compiler disposition")
    lower = audit._closed(row["lowering"], LOWERING_FIELDS, "native Lean lowering ledger")
    _false(lower, {*EVIDENCE_FALSE, "original_program_modified", "source_bytes_replayed"})
    audit._require(lower["profile"] == "native-source-program-straight-line-lean/v2" and lower["operators"] == ["return"]
                   and lower["original_program_id"] == graph["program_id"] and lower["program_sha256"] == row["program_sha256"], "native lowering profile/program differs")
    audit._require(lower["actual_reads"] == summary["syntactic_reads"] and lower["actual_writes"] == summary["syntactic_writes"], "Lean lowering read/write footprint differs")
    audit._require(lower["original_metadata_sha256"] == audit._sha(audit._canonical(graph["metadata"]))
                   and lower["original_source_references"] == graph["sources"] and lower["effect_audit"] == graph["metadata"]["effect_summary_audit"]
                   and lower["effect_audit_sha256"] == audit._sha(audit._canonical(lower["effect_audit"])), "extracted metadata/source/effect evidence differs")
    audit._require(all(lower[name] is True for name in ("complete_read_write_summaries_checked", "metadata_emitted_as_explicit_evidence", "source_hash_consistency_checked")),
                   "recorded extraction checks must remain explicit")
    audit._require(lower["operational_view_transformation"] == "closed_validated_metadata_extracted_to_explicit_Lean_evidence_declarations", "unrecognized operational view transformation")
    audit._text(lower["operational_view_program_id"], "claimed operational program ID")
    lines, slots, names, op_sha = _declarations(graph, lower)
    audit._require(op_sha == lower["operational_view_sha256"], "operational view body commitment differs from unchanged graph with extracted metadata")
    return lines, slots, names, op_sha


def evaluate(manifest: Path, output: Path, limits: Limits = DEFAULT_LIMITS):
    manifest, output = manifest.absolute(), output.absolute()
    pins = native.Pins(limits)
    raw = pins.read(manifest, limits.max_file_bytes)
    spec = audit._closed(_json(raw, limits), {"schema", *INPUT_ROLES}, "native Lean projection input")
    audit._require(spec["schema"] == INPUT_SCHEMA, "versioned Lean projection input required")
    selected = {}
    for role in INPUT_ROLES:
        if role.endswith("_lean"):
            descriptor = spec[role]
            audit._require(type(descriptor) is dict and type(descriptor.get("size_bytes")) is int
                           and 0 <= descriptor["size_bytes"] <= limits.max_lean_bytes, "Lean body byte budget exceeded before allocation")
        selected[role] = pins.descriptor(spec[role])
    prior = _json(selected["program_graph_report"][1], limits)
    audit._require(prior.get("schema") == graph_tool.REPORT_SCHEMA and prior.get("status") == "passed"
                   and prior.get("manifest_sha256") == audit._sha(selected["program_graph_input"][1]), "Lean/program graph raw input/report binding differs")
    graph_spec = audit._closed(_json(selected["program_graph_input"][1], limits), {"schema", "source_comparison_input", "source_comparison"}, "nested graph input")
    comparison_path, comparison_raw = pins.descriptor(graph_spec["source_comparison"])
    prior_comparison = _json(comparison_raw, limits)
    audit._require(prior_comparison.get("schema") == comparison.REPORT_SCHEMA and prior_comparison.get("status") == "passed", "nested source comparison required")
    audit._require(pins.total + graph_tool.DEFAULT_LIMITS.max_total_bytes <= limits.max_total_bytes
                   and len(pins.files) + graph_tool.DEFAULT_LIMITS.max_files <= limits.max_files, "combined Lean/graph budget exceeded before nested reads")
    protected = [path.parent for path in pins.files]
    for prior_report in (prior, prior_comparison):
        population = prior_report.get("input_files")
        audit._require(type(population) is list and len(population) <= graph_tool.DEFAULT_LIMITS.max_files, "bounded nested original scope required")
        protected += [comparison._descriptor(item, limits).parent for item in population]
    lock_tool._preflight_output(output, protected)
    pins.recheck()
    output.mkdir(mode=0o700)
    report = {"schema": REPORT_SCHEMA, "status": "refused", "profile": PROFILE, "limits": asdict(limits), **dict.fromkeys(FALSE_FLAGS, False),
        **dict.fromkeys(TRUE_FLAGS, False), "unknown_pretraining_exposure": True, "manifest_sha256": audit._sha(raw),
        **{role + "_sha256": audit._sha(body) for role, (_, body) in selected.items()},
        "source_replay_sha256": prior.get("source_replay_sha256"), "public_manifest_sha256": prior.get("public_manifest_sha256")}
    copies = {}
    try:
        nested = output / "program-graph-rederived"
        rederived = graph_tool.evaluate(selected["program_graph_input"][0], nested)
        audit._require(rederived["status"] == "passed" and rederived == prior
                       and final.Capture.regular(nested / "native_program_graph.json", limits.max_file_bytes) == selected["program_graph_report"][1],
                       "program graph report does not reproduce exactly")
        source_nested = nested / "source-comparison-rederived"
        native_nested = source_nested / "native-diagnostics-rederived/inputs"
        public_raw = final.Capture.regular(native_nested / "public_manifest.json", limits.max_file_bytes)
        nested_reads = {native_nested / "public_manifest.json": public_raw}
        public = _json(public_raw, limits)
        audit._require(audit._sha(public_raw) == prior["public_manifest_sha256"] and public["schema"] == "codebase-source384-acceptance-evidence@1", "exact public parent manifest differs")
        public_files = {item["path"]: item for item in public["files"]}
        for role in BODY_ROLES:
            declaration = public_files.get(PUBLIC_PATHS[role])
            audit._require(type(declaration) is dict and declaration["sha256"] == spec[role]["sha256"]
                           and declaration["bytes"] == spec[role]["size_bytes"], "selected Lean/Lake body differs from released public child commitment")
        native_bodies = {}
        for role in ("learned", "source_label_baseline"):
            path = native_nested / (role + ".json")
            body = final.Capture.regular(path, limits.max_file_bytes)
            nested_reads[path] = body
            native_bodies[role] = _json(body, limits)
        native_rows = {role: {row["id"]: row for row in (body["lake"]["rows"] if role == "source_label_baseline" else body["result"]["inference"]["rows"])}
                       for role, body in native_bodies.items()}
        receipts, row_maps, sections = {}, {}, {}
        records = prior["records"]
        audit._require(type(records) is list and len(records) <= limits.max_rows, "bounded historical Lean source population required")
        for role in ("learned", "source_label_baseline"):
            receipts[role], row_maps[role] = _receipt(selected[role + "_lake_receipt"][1], selected[role + "_lean"][1], limits)
            sections[role] = _sections(selected[role + "_lean"][1], limits)
            audit._require(set(row_maps[role]) == {record["native_id"] for record in records} and len(sections[role]) == receipts[role]["supported_count"],
                           "complete historical compiler/native ID or namespace population differs")
        (output / "inputs").mkdir(mode=0o700)
        for role, (_path, body) in {"manifest": (manifest, raw), **selected}.items():
            destination = output / "inputs" / (role + (".source" if role.endswith("_lean") else ".json"))
            comparison._copy(destination, body)
            copies[destination] = body
        comparisons, conformance = [], 0
        for record in records:
            modes = {"zero_head": {"status": "missing_graph_and_unavailable_lean_projection", "projection_created": False}}
            audit._require(record["role_graphs"]["zero_head"]["status"] == "missing_graph", "zero-head Lean profile must not fill a missing graph")
            for role in ("learned", "source_label_baseline"):
                summary = record["role_graphs"][role]
                index, row = row_maps[role][record["native_id"]]
                if summary["status"] != "conformant_source_projection":
                    audit._require(row["semantic_lowering_supported"] is False, "missing/unsupported graph silently compiled")
                    modes[role] = {"status": "unsupported_graph_profile", "projection_created": False}
                    continue
                audit._require(index < len(sections[role]), "supported namespace index unavailable")
                graph_raw = final.Capture.regular(nested / summary["graph_extract"], limits.max_file_bytes)
                graph = _json(graph_raw, limits)
                original = native_rows[role][record["native_id"]]
                contract = original["source_qualification"] if role == "source_label_baseline" else original["source_contract"]
                expected, slots, names, op_sha = _join(graph, summary, row, contract)
                audit._require(sections[role][index]["lines"] == expected, "emitted Lean expression/slot/return/evidence declarations differ from exact ProgramIR")
                conformance += 1
                modes[role] = {"status": "conformant_closed_textual_projection", "projection_created": False, "namespace": "Candidate_" + str(index),
                    "native_program_canonical_sha256": summary["native_graph_canonical_sha256"], "operational_view_canonical_sha256": op_sha,
                    "recorded_operational_view_program_id": row["lowering"]["operational_view_program_id"], "recorded_program_id_authenticated": False,
                    "original_candidate_sha256": row["candidate_sha256"], "raw_candidate_declarations_sha256": audit._sha(sections[role][index]["raw"]),
                    "recorded_compiler_declarations_sha256": row["lean_declarations_sha256"], "recorded_compiler_declaration_digest_semantics_verified": False,
                    "symbol_slot_map": slots, "expression_definition_map": names, "syntactic_expression_count": len(names), "store_slot_count": len(slots),
                    "return_definition_count": 1, "evidence_definition_count": 17, "individual_source_spans_emitted": 0,
                    "native_source_spans_retained_in_graph": len(graph["spans"]), "runtime_truth": "unknown"}
            comparisons.append({"native_id": record["native_id"], "source_sha256": record["source_sha256"], "role_projections": modes})
        for prior_report, parent in ((prior, nested), (prior_comparison, source_nested)):
            for item in prior_report["input_files"]:
                body = final.Capture.regular(Path(item["path"]), item["size_bytes"])
                audit._require(len(body) == item["size_bytes"] and audit._sha(body) == item["sha256"], "nested original input drifted after Lean comparison")
            for item in prior_report["retained_files"]:
                body = final.Capture.regular(parent / item["path"], item["size_bytes"])
                audit._require(len(body) == item["size_bytes"] and audit._sha(body) == item["sha256"], "nested retained body drifted after Lean comparison")
        pins.recheck()
        for path, body in nested_reads.items():
            audit._require(final.Capture.regular(path, len(body)) == body, "nested native diagnostic copy drifted after Lean comparison")
        for path, body in copies.items():
            audit._require(final.Capture.regular(path, len(body)) == body, "retained Lean projection input drifted")
        metrics = {role: {"present_count": sum(record["role_projections"][role]["status"] != "missing_graph_and_unavailable_lean_projection" for record in comparisons),
                         "conformant_count": sum(record["role_projections"][role]["status"] == "conformant_closed_textual_projection" for record in comparisons),
                         "missing_count": sum(record["role_projections"][role]["status"] == "missing_graph_and_unavailable_lean_projection" for record in comparisons),
                         "unsupported_count": sum(record["role_projections"][role]["status"] == "unsupported_graph_profile" for record in comparisons)}
                   for role in ("learned", "zero_head", "source_label_baseline")}
        report.update(status="passed", **dict.fromkeys(TRUE_FLAGS, True), historical_case_count=len(records), source_byte_count=prior["source_byte_count"],
            role_projection_metrics=metrics, records=comparisons, compiler_output_body_equal=selected["learned_lean"][1] == selected["source_label_baseline_lean"][1],
            projection_stage="deterministic_native_graph_to_emitted_Lean_text_not_learned_free_running_program_output",
            projection_coverage={"conformant_projection_count": conformance, "expression_definitions": conformance * 3, "store_slots": conformance * 3,
                "return_definitions": conformance, "evidence_definitions": conformance * 17, "source_span_occurrences_retained_in_graph": conformance * 7,
                "source_span_occurrences_individually_emitted": 0, "syntactic_scope_only": True},
            projection_losses={"semantic_loss_assessment": "unavailable", "operational_semantics_assessment": "unavailable",
                "source_spans": "retained_in_pinned_graph_not_individually_serialized_as_Lean_declarations",
                "native_identifiers": "specialized_to_store_slots_and_expression_names_with_mapping_retained_here",
                "control_flow": "one_return_block_specialized_to_run_definition_only",
                "metadata": "extracted_to_descriptive_Lean_evidence_strings_not_operational_semantics"},
            exposure={"status": "unknown", "complete_ancestral_inventory_supplied": False, "final_partition_assignment_performed": False},
            recorded_compiler_execution={role: {"backend_executed_claim": receipts[role]["backend_executed"], "status_claim": receipts[role]["status"],
                "execution_metadata": receipts[role]["execution"], "replayed_by_auditor": False} for role in receipts},
            input_files=[{"path": str(path), "sha256": audit._sha(body), "size_bytes": len(body)} for path, body in sorted(pins.files.items())],
            retained_files=[{"path": path.relative_to(output).as_posix(), "sha256": audit._sha(body), "size_bytes": len(body)} for path, body in sorted(copies.items())],
            scope="closed textual IR/compiler-output and extracted-evidence correspondence; identical output bodies do not measure learned gain",
            invocation_input_body_available=False, historical_declaration_digest_recipe_qualified=False)
        report["lean_projection_conformance_available"] = conformance > 0
    except (audit.AuditInputError, OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        report.update(error=f"{type(exc).__name__}: {exc}")
    final._write(output / "native_lean_projection.json", report)
    (output / "native_lean_projection.json").chmod(0o600)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        report = evaluate(args.manifest, args.output)
    except (audit.AuditInputError, OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        parser.exit(3, f"native Lean projection refused: {type(exc).__name__}: {exc}\n")
    print(audit._canonical({key: report[key] for key in ("status", "manifest_sha256", "program_graph_report_sha256")}).decode())
    return 0 if report["status"] == "passed" else 3


if __name__ == "__main__":
    sys.exit(main())
