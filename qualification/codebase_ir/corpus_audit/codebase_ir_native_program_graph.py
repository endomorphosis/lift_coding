#!/usr/bin/env python3
"""Check historical source-bound ProgramIR projections without owner execution."""
from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import codebase_ir_corpus_audit as audit
import codebase_ir_final_evaluation as final
import codebase_ir_final_lock as lock_tool
import codebase_ir_final_targets as targets
import codebase_ir_native_source384_diagnostics as native
import codebase_ir_native_source_comparison as comparison

INPUT_SCHEMA = "codebase-ir-native-program-graph-input@1"
REPORT_SCHEMA = "codebase-ir-native-program-graph@1"
PROFILE = "qualification/source-bound-two-int-binary-program-graph@1"
ROLES = ("learned", "zero_head", "source_label_baseline")
TRUE_FLAGS = {"source_projection_graph_conformance_available", "source_graph_bindings_rederived", "source_graph_effect_footprints_rederived",
              "source_comparison_independently_rederived", "raw_native_graphs_retained_unmodified", "source_label_baseline_separate",
              "input_files_unchanged", "unknown_pretraining_exposure"}
FALSE_FLAGS = comparison.FALSE_FLAGS | {"learned_full_program_prediction_verified", "free_running_full_program_quality_verified",
    "graph_effect_runtime_truth_verified", "complete_ancestral_exposure_verified", "native_compiler_execution_performed", "checker_execution_performed"}
PROGRAM_FIELDS = {"schema_version", "program_id", "sources", "spans", "symbols", "expressions", "commands", "functions", "global_symbol_ids", "metadata"}
EXPR_FIELDS = {"attributes", "evaluation_order", "expression_id", "kind", "operand_ids", "operator", "source_ref_ids", "span_ids", "symbol_ids", "type_ref"}
SYMBOL_FIELDS = {"attributes", "kind", "name", "source_ref_ids", "span_ids", "symbol_id", "type_ref"}
EFFECT_FIELDS = {"allocates", "deallocates", "nondeterministic", "performs_io", "raises", "reads", "synchronizes", "writes"}
PROJECTION_FIELDS = {"bridge", "completion_authority", "execution_authority", "family_id", "kind", "native_document", "profile_id",
                     "proof_authority", "security_specification_inferred", "source_semantics_verified", "whole_program_semantics_verified"}
NATIVE_OPERATORS = {"Add": "add", "Sub": "sub", "Mult": "mul"}
METADATA_FIELDS = {"adapter", "assumptions", "completion_authority", "effect_summary_assumption", "effect_summary_audit", "effect_summary_contract",
                   "execution_authority", "input_type_basis", "language", "path", "proof_authority", "security_specification_inferred",
                   "source_binding_effects_schema", "source_binding_schema", "source_semantics_verified", "source_sha256", "whole_program_semantics_verified"}


@dataclass(frozen=True)
class Limits:
    max_files: int = 20
    max_file_bytes: int = 1024 * 1024
    max_total_bytes: int = 20 * 1024 * 1024
    max_rows: int = 32
    max_graph_items: int = 128
    max_source_bytes: int = 64 * 1024

    def __post_init__(self):
        audit._require(all(type(value) is int and value > 0 for value in asdict(self).values()), "positive exact graph limits required")


DEFAULT_LIMITS = Limits()


def _json(raw, limits):
    return audit._load_json(raw, audit.Limits(max_json_bytes=limits.max_file_bytes, max_json_nodes=100_000))


def _list(value, limits, label):
    audit._require(type(value) is list and len(value) <= limits.max_graph_items, "bounded graph list required: " + label)
    return value


def _unique(rows, key, limits):
    result = {}
    for row in _list(rows, limits, key):
        audit._require(type(row) is dict and key in row, "typed graph member required")
        name = audit._text(row[key], key)
        audit._require(name not in result, "duplicate graph identity: " + key)
        result[name] = row
    return result


def _effects(value, reads, writes):
    audit._closed(value, EFFECT_FIELDS, "syntactic graph effects")
    audit._require(value["reads"] == sorted(reads) and value["writes"] == sorted(writes), "graph read/write footprint differs from source references")
    # This is a closed serialized pure-fragment convention, not a runtime theorem.
    audit._require(all(value[key] == [] for key in ("allocates", "deallocates", "raises"))
                   and all(value[key] is False for key in ("nondeterministic", "performs_io", "synchronizes")),
                   "effect flags outside declared pure source projection profile")


def _source(raw, limits):
    binding, target, reason = targets.derive_source(raw, audit.Limits(max_source_bytes=limits.max_source_bytes))
    if target is None:
        return binding, None, None, reason
    function = target["function"]
    if len(function["parameters"]) != 2 or any(param["sort"] != "Int" for param in function["parameters"]) or function["returns"] != "Int":
        return binding, target, None, "two Int parameters and Int return required by graph profile"
    body = target["body"]
    if body["kind"] != "binary" or body["operator"] not in NATIVE_OPERATORS or any(body[key]["kind"] != "reference" for key in ("left", "right")):
        return binding, target, None, "one arithmetic binary operation over parameter references required"
    if {body[key]["name"] for key in ("left", "right")} != {param["name"] for param in function["parameters"]}:
        return binding, target, None, "both distinct source parameters required"
    node = ast.parse(raw.decode("utf-8"), type_comments=True).body[0]
    return binding, target, node, None


def _ast_span(node, raw):
    lines = raw.split(b"\n")
    start = sum(len(line) + 1 for line in lines[:node.lineno - 1]) + node.col_offset
    end = sum(len(line) + 1 for line in lines[:node.end_lineno - 1]) + node.end_col_offset
    return start, end, node.lineno, node.end_lineno, node.col_offset + 1, node.end_col_offset


def _graph(graph, binding, target, node, raw, contract_binding, candidate, lowering, role, limits):
    audit._closed(graph, PROGRAM_FIELDS, "native program graph")
    audit._require(graph["schema_version"] == "program-ir/v1", "native program schema required")
    audit._text(graph["program_id"], "declared native program identity")
    sources = _unique(graph["sources"], "ref_id", limits)
    symbols = _unique(graph["symbols"], "symbol_id", limits)
    expressions = _unique(graph["expressions"], "expression_id", limits)
    commands = _unique(graph["commands"], "command_id", limits)
    functions = _unique(graph["functions"], "function_id", limits)
    spans = _unique(graph["spans"], "span_id", limits)
    audit._require((len(sources), len(spans), len(symbols), len(expressions), len(commands), len(functions)) == (1, 7, 3, 3, 1, 1)
                   and graph["global_symbol_ids"] == [], "closed source graph population differs")
    source_id, source = next(iter(sources.items()))
    audit._closed(source, {"container_sha256", "container_uri", "content_cid", "content_sha256", "license_expression", "metadata", "ref_id",
                           "review_status", "source_id", "source_revision", "source_uri"}, "native source reference")
    audit._require(source["content_sha256"] == binding["source_sha256"] and type(source["metadata"]) is dict
                   and type(source["metadata"].get("byte_length")) is int and source["metadata"]["byte_length"] == len(raw), "native graph source byte binding differs")
    selected_nodes = [node, *node.args.args, node.body[0], node.body[0].value, node.body[0].value.left, node.body[0].value.right]
    expected_spans = {_ast_span(item, raw): item for item in selected_nodes}
    selected_spans = {}
    for name, span in spans.items():
        audit._closed(span, {"end_byte", "end_char", "end_column", "end_line", "metadata", "source_ref_id", "span_id", "start_byte", "start_char", "start_column", "start_line"}, "native graph span")
        position = tuple(span[key] for key in ("start_byte", "end_byte", "start_line", "end_line", "start_column", "end_column"))
        audit._require(all(type(item) is int for item in position) and position in expected_spans and position not in selected_spans
                       and span["source_ref_id"] == source_id and span["start_char"] is None and span["end_char"] is None and span["metadata"] == {},
                       "native graph span differs from exact selected source AST")
        selected_spans[position] = name
    audit._require(set(selected_spans) == set(expected_spans), "native graph source span coverage differs")

    def origin(row, selected_node):
        audit._require(row["source_ref_ids"] == [source_id] and row["span_ids"] == [selected_spans[_ast_span(selected_node, raw)]],
                       "graph member source reference or AST span differs")

    parameters = {}
    for symbol in symbols.values():
        audit._closed(symbol, SYMBOL_FIELDS, "native graph symbol")
        audit._require(symbol["attributes"] == {} and symbol["type_ref"] == "integer", "graph symbol attributes or source annotation type differs")
        if symbol["kind"] == "parameter":
            audit._require(symbol["name"] not in parameters, "duplicate source parameter name")
            parameters[symbol["name"]] = symbol
    names = [param["name"] for param in target["function"]["parameters"]]
    audit._require(set(parameters) == set(names), "graph parameter declaration differs from source")
    for argument in node.args.args:
        origin(parameters[argument.arg], argument)
    result_symbols = [value for value in symbols.values() if value["kind"] == "result"]
    audit._require(len(result_symbols) == 1 and result_symbols[0]["name"] == "result", "one declared synthetic result slot required")
    origin(result_symbols[0], node)
    roots, leaves = [], {}
    for expression in expressions.values():
        audit._closed(expression, EXPR_FIELDS, "native graph expression")
        audit._require(expression["attributes"] == {} and expression["type_ref"] == "integer", "graph expression attributes/type differs")
        if expression["kind"] == "binary":
            roots.append(expression)
        else:
            audit._require(expression["kind"] == "symbol" and expression["operand_ids"] == [] and expression["evaluation_order"] == []
                           and expression["operator"] == "" and len(expression["symbol_ids"]) == 1, "closed graph reference expression required")
            identity = expression["symbol_ids"][0]
            audit._require(identity in {param["symbol_id"] for param in parameters.values()} and identity not in leaves, "unresolved or repeated graph parameter reference")
            leaves[identity] = expression
    audit._require(len(roots) == 1 and len(leaves) == 2, "closed binary expression graph required")
    root = roots[0]
    source_body = target["body"]
    operands = [leaves[parameters[source_body[side]["name"]]["symbol_id"]]["expression_id"] for side in ("left", "right")]
    audit._require(root["operand_ids"] == operands and root["evaluation_order"] == operands and root["symbol_ids"] == []
                   and root["operator"] == NATIVE_OPERATORS[source_body["operator"]], "graph operator/reference/evaluation order differs from source")
    origin(root, node.body[0].value)
    for side in ("left", "right"):
        origin(leaves[parameters[source_body[side]["name"]]["symbol_id"]], getattr(node.body[0].value, side))
    command = next(iter(commands.values()))
    audit._closed(command, {"attributes", "command_id", "effects", "evaluation_order", "expression_ids", "kind", "source_ref_ids", "span_ids", "target_symbol_ids", "undefined_behavior"}, "native return command")
    audit._require(command["kind"] == "return" and command["attributes"] == {} and command["expression_ids"] == [root["expression_id"]]
                   and command["evaluation_order"] == [root["expression_id"]] and command["target_symbol_ids"] == [] and command["undefined_behavior"] == [], "source return command differs")
    origin(command, node.body[0])
    reads = {param["symbol_id"] for param in parameters.values()}
    _effects(command["effects"], reads, set())
    function = next(iter(functions.values()))
    audit._closed(function, {"cfg", "declared_exceptions", "effects", "exception_symbol_ids", "function_id", "local_symbol_ids", "name", "parameter_symbol_ids", "purity", "result_symbol_id", "return_type", "source_ref_ids", "span_ids"}, "native graph function")
    audit._require(function["name"] == target["function"]["name"] and function["parameter_symbol_ids"] == [parameters[name]["symbol_id"] for name in names]
                   and function["result_symbol_id"] == result_symbols[0]["symbol_id"] and function["return_type"] == "integer"
                   and function["local_symbol_ids"] == [] and function["exception_symbol_ids"] == [] and function["declared_exceptions"] == []
                   and function["purity"] == "pure", "source function declaration/typed result differs")
    origin(function, node)
    _effects(function["effects"], reads, set())
    cfg = audit._closed(function["cfg"], {"blocks", "edges", "entry_block_id", "exceptional_exit_block_ids", "graph_id", "normal_exit_block_ids"}, "native graph CFG")
    blocks = _unique(cfg["blocks"], "block_id", limits)
    audit._require(len(blocks) == 1, "one straight-line source block required")
    block_id, block = next(iter(blocks.items()))
    audit._closed(block, {"block_id", "command_ids", "source_ref_ids", "span_ids"}, "native graph block")
    origin(block, node)
    audit._require(block["command_ids"] == [command["command_id"]] and cfg["entry_block_id"] == block_id
                   and cfg["normal_exit_block_ids"] == [block_id] and cfg["exceptional_exit_block_ids"] == [] and cfg["edges"] == [], "source return CFG differs")
    audit._text(cfg["graph_id"], "declared CFG identity")
    metadata = audit._closed(graph["metadata"], METADATA_FIELDS, "native program graph metadata")
    audit._require(metadata["source_sha256"] == binding["source_sha256"] and metadata["language"] == "python"
                   and metadata["input_type_basis"] == "explicit_int_annotations", "graph source metadata differs")
    audit._require(type(metadata["assumptions"]) is list and len(metadata["assumptions"]) <= limits.max_graph_items, "bounded recorded graph assumptions required")
    for assumption in metadata["assumptions"]:
        audit._text(assumption, "recorded graph assumption", 2048)
    for flag in ("completion_authority", "execution_authority", "proof_authority", "security_specification_inferred", "source_semantics_verified", "whole_program_semantics_verified"):
        audit._require(metadata.get(flag) is False, "native graph metadata authority elevation")
    effect_audit = audit._closed(metadata["effect_summary_audit"], {"base_program_id", "base_program_sha256", "commands", "functions", "schema"}, "recorded graph effect audit")
    audit._require(effect_audit["schema"] == "security-source-program-effect-audit/v1" and len(effect_audit["commands"]) == len(effect_audit["functions"]) == 1,
                   "closed recorded graph effect audit required")
    audit._digest(effect_audit["base_program_sha256"], "recorded base program SHA")
    audit._text(effect_audit["base_program_id"], "recorded base program identity")
    for section, current, identity_key in (("commands", command, "command_id"), ("functions", function, "function_id")):
        entry = effect_audit[section][0]
        audit._closed(entry, {"after", "before", identity_key, "retained_effects"} | ({"purity"} if section == "functions" else set()), "recorded effect refinement")
        audit._require(entry[identity_key] == current[identity_key] and entry["after"] == {"reads": sorted(reads), "writes": []}
                       and entry["retained_effects"] == {key: value for key, value in current["effects"].items() if key not in {"reads", "writes"}}, "recorded effect audit does not bind current source footprint")
        audit._closed(entry["before"], {"reads", "writes"}, "recorded before footprint")
        if section == "functions":
            audit._require(entry["purity"] == function["purity"], "recorded graph purity identity differs")
    audit._closed(contract_binding, {"effect_summary_contract", "effect_summary_refinements", "expression_references", "native_program_id", "operator_mapping", "source_references", "source_sha256", "spans", "type_refinements"}, "native graph contract binding")
    expected_candidate, _ = comparison._expected_fragment(target)
    audit._require(role in ROLES and (role == "source_label_baseline" or candidate is not None), "returned candidate required for learned/zero graph projection")
    raw_candidate = expected_candidate if role == "source_label_baseline" else candidate
    audit._require(raw_candidate == expected_candidate, "returned candidate cannot be replaced by source-derived program projection")
    reference_map = {"expr:result": root["expression_id"], **{"expr:" + name: leaves[param["symbol_id"]]["expression_id"] for name, param in parameters.items()}}
    audit._require(contract_binding["source_sha256"] == binding["source_sha256"] and contract_binding["native_program_id"] == graph["program_id"]
                   and contract_binding["expression_references"] == reference_map and contract_binding["source_references"] == {"source": source_id}
                   and contract_binding["operator_mapping"] == {"candidate": expected_candidate["document"]["operator"], "native": root["operator"]}
                   and contract_binding["effect_summary_refinements"] == effect_audit
                   and contract_binding["effect_summary_contract"] == metadata.get("effect_summary_contract") == "closed-command-expression-reads-and-assignment-writes/v1", "candidate/program source reference or effect binding differs")
    refinement_ids = {("symbol", name) for name in symbols} | {("expression", name) for name in expressions} | {("function", name) for name in functions}
    refinements = _list(contract_binding["type_refinements"], limits, "recorded type refinements")
    seen = set()
    for refinement in refinements:
        audit._closed(refinement, {"after", "before", "id", "kind"}, "recorded graph type refinement")
        identity = refinement["kind"], refinement["id"]
        audit._require(identity in refinement_ids and identity not in seen and refinement["after"] == "integer" and refinement["before"] == "any",
                       "recorded type refinement does not bind current source graph type")
        seen.add(identity)
    audit._require(seen == refinement_ids, "recorded type refinement population differs")
    recorded_spans = {span["span_id"]: span for span in contract_binding["spans"]}
    audit._require(len(recorded_spans) == len(contract_binding["spans"]) and set(recorded_spans) == set(spans), "recorded/native source span population differs")
    for name, span in spans.items():
        audit._require(recorded_spans[name] == {"span_id": name, "start_byte": span["start_byte"], "end_byte": span["end_byte"],
                       "sha256": audit._sha(raw[span["start_byte"]:span["end_byte"]])}, "recorded/native source span hash differs")
    graph_sha = audit._sha(audit._canonical(graph))
    if lowering is not None:
        audit._require(lowering["program_sha256"] == graph_sha and lowering["original_program_id"] == graph["program_id"]
                       and lowering["actual_reads"] == sorted(reads) and lowering["actual_writes"] == [], "recorded baseline lowering graph/footprint binding differs")
    return {"native_program_id": graph["program_id"], "native_graph_canonical_sha256": graph_sha, "parameter_symbols": {name: param["symbol_id"] for name, param in parameters.items()},
            "expression_reference_map": reference_map, "source_reference_id": source_id, "return_command_id": command["command_id"], "function_id": function["function_id"],
            "cfg_entry_block_id": block_id, "syntactic_reads": sorted(reads), "syntactic_writes": [], "recorded_base_effect_program_verified": False,
            "source_uri_claim": source["source_uri"], "source_uri_opened": False, "graph_stage": "deterministic_source_contract_projection_after_validation_not_learned_full_program_output"}


def _bridge(projection, graph):
    audit._closed(projection, PROJECTION_FIELDS, "native program projection")
    audit._require(projection["family_id"] == "program" and projection["kind"] == "program" and projection["profile_id"] == "program_ir", "closed native program projection required")
    for flag in PROJECTION_FIELDS - {"bridge", "family_id", "kind", "native_document", "profile_id"}:
        audit._require(projection[flag] is False, "program projection authority/source truth elevation")
    bridge = projection["bridge"]
    audit._require(type(bridge) is dict and bridge.get("preservation") == "exact" and bridge.get("status") == "ok"
                   and bridge.get("losses") == [] and bridge.get("unsupported") == [] and bridge.get("domain_identity") == graph["program_id"], "recorded program bridge identity/coverage differs")
    payload = bridge["expression"]["root"]["extension"]["payload"]
    audit._require(payload["document"] == graph and payload["domain_identity"] == graph["program_id"], "recorded syntax bridge substituted native graph")


def evaluate(manifest: Path, output: Path, limits: Limits = DEFAULT_LIMITS):
    manifest, output = manifest.absolute(), output.absolute()
    pins = native.Pins(limits)
    raw = pins.read(manifest, limits.max_file_bytes)
    spec = audit._closed(_json(raw, limits), {"schema", "source_comparison_input", "source_comparison"}, "native program graph input")
    audit._require(spec["schema"] == INPUT_SCHEMA, "versioned native program graph input required")
    comparison_input, input_raw = pins.descriptor(spec["source_comparison_input"])
    comparison_report, report_raw = pins.descriptor(spec["source_comparison"])
    prior = _json(report_raw, limits)
    audit._require(prior.get("schema") == comparison.REPORT_SCHEMA and prior.get("status") == "passed" and prior.get("manifest_sha256") == audit._sha(input_raw), "graph/source comparison raw input/report binding differs")
    audit._require(pins.total + comparison.DEFAULT_LIMITS.max_total_bytes <= limits.max_total_bytes
                   and len(pins.files) + comparison.DEFAULT_LIMITS.max_files <= limits.max_files, "combined graph/comparison budget exceeded before nested reads")
    prior_inputs = prior.get("input_files")
    audit._require(type(prior_inputs) is list and len(prior_inputs) <= comparison.DEFAULT_LIMITS.max_files, "bounded prior graph input scope required")
    protected = [manifest.parent, comparison_input.parent, comparison_report.parent]
    for item in prior_inputs:
        protected.append(comparison._descriptor(item, limits).parent)
    lock_tool._preflight_output(output, protected)
    pins.recheck()
    output.mkdir(mode=0o700)
    report = {"schema": REPORT_SCHEMA, "status": "refused", "profile": PROFILE, **dict.fromkeys(FALSE_FLAGS, False), **dict.fromkeys(TRUE_FLAGS, False),
              "unknown_pretraining_exposure": True, "manifest_sha256": audit._sha(raw), "source_comparison_input_sha256": audit._sha(input_raw),
              "source_comparison_report_sha256": audit._sha(report_raw), "source_replay_sha256": prior.get("source_replay_sha256"),
              "public_manifest_sha256": prior.get("public_manifest_sha256"), "limits": asdict(limits)}
    copies = {}
    try:
        nested = output / "source-comparison-rederived"
        rederived = comparison.evaluate(comparison_input, nested)
        nested_report = final.Capture.regular(nested / "native_source_comparison.json", limits.max_file_bytes)
        audit._require(rederived["status"] == "passed" and rederived == prior and nested_report == report_raw, "source comparison does not reproduce exactly from retained inputs")
        audit._require(type(prior["records"]) is list and len(prior["records"]) <= limits.max_rows, "bounded graph source population required")
        bodies = {}
        for role in ROLES:
            path = nested / "native-diagnostics-rederived/inputs" / (role + ".json")
            body = final.Capture.regular(path, limits.max_file_bytes)
            bodies[role] = _json(body, limits)
        native_rows = {role: {row["id"]: row for row in (body["lake"]["rows"] if role == "source_label_baseline" else body["result"]["inference"]["rows"])} for role, body in bodies.items()}
        records, graph_count, source_bytes = [], 0, 0
        (output / "graphs").mkdir(mode=0o700)
        for previous in prior["records"]:
            name = previous["native_id"]
            source = final.Capture.regular(nested / previous["source_export"], limits.max_source_bytes)
            source_bytes += len(source)
            audit._require(audit._sha(source) == previous["source_sha256"], "graph exact source export differs")
            binding, target, node, reason = _source(source, limits)
            roles = {}
            for role in ROLES:
                row = native_rows[role].get(name)
                contract = row.get("source_qualification", row.get("source_contract")) if row else None
                projections = contract["projections"] if contract else []
                audit._require(type(projections) is list and len(projections) <= limits.max_graph_items, "bounded graph projection inventory required")
                if not projections:
                    roles[role] = {"status": "missing_graph", "graph_created": False}
                    continue
                if node is None or len(projections) != 1 or type(projections[0]) is not dict or type(projections[0].get("native_document")) is not dict or projections[0]["native_document"].get("schema_version") != "program-ir/v1":
                    roles[role] = {"status": "unsupported_source_or_graph_profile", "reason": reason, "graph_created": False}
                    continue
                graph = projections[0]["native_document"]
                _bridge(projections[0], graph)
                candidate = row.get("candidate_ir")
                lowering = row.get("lowering")
                summary = _graph(graph, binding, target, node, source, contract["source_binding"], candidate, lowering, role, limits)
                if role == "source_label_baseline":
                    audit._require(row["program_sha256"] == summary["native_graph_canonical_sha256"], "baseline row program digest differs from retained graph")
                destination = output / "graphs" / (name + "-" + role + ".json")
                graph_raw = audit._canonical(graph) + b"\n"
                comparison._copy(destination, graph_raw)
                copies[destination] = graph_raw
                graph_count += 1
                roles[role] = {"status": "conformant_source_projection", **summary, "graph_created": False, "graph_extract": destination.relative_to(output).as_posix(),
                               "candidate_origin": "deterministic_source_label_baseline" if role == "source_label_baseline" else "retained_returned_candidate_not_full_program_prediction"}
            records.append({"native_id": name, "source_sha256": previous["source_sha256"], "function_binding": binding, "source_profile_reason": reason,
                            "role_graphs": roles, "returned_candidate_comparisons": previous["returned_mode_comparisons"], "source_runtime_truth": "unknown"})
        (output / "inputs").mkdir(mode=0o700)
        for role, path in (("manifest", manifest), ("source_comparison_input", comparison_input), ("source_comparison", comparison_report)):
            destination = output / "inputs" / (role + ".json")
            comparison._copy(destination, pins.files[path])
            copies[destination] = pins.files[path]
        # Check the original input population and every nested retained body again.
        for item in prior["input_files"]:
            body = final.Capture.regular(Path(item["path"]), item["size_bytes"])
            audit._require(len(body) == item["size_bytes"] and audit._sha(body) == item["sha256"], "original source comparison input drifted after graph derivation")
        for item in prior["retained_files"]:
            path = nested / item["path"]
            body = final.Capture.regular(path, item["size_bytes"])
            audit._require(len(body) == item["size_bytes"] and audit._sha(body) == item["sha256"], "nested retained source comparison body drifted")
        pins.recheck()
        for path, body in copies.items():
            audit._require(final.Capture.regular(path, len(body)) == body, "retained program graph copy drifted")
        report.update(status="passed", **dict.fromkeys(TRUE_FLAGS, True),
            historical_case_count=len(records), source_graph_count=graph_count, source_byte_count=source_bytes, records=records,
            native_graph_stage="deterministic_source_contract_projection_after_validation_not_learned_full_program_output",
            exposure={"status": "unknown", "complete_ancestral_inventory_supplied": False, "final_partition_assignment_performed": False},
            role_graph_metrics={role: {"present_count": sum(row["role_graphs"][role]["status"] != "missing_graph" for row in records),
                "conformant_count": sum(row["role_graphs"][role]["status"] == "conformant_source_projection" for row in records),
                "missing_count": sum(row["role_graphs"][role]["status"] == "missing_graph" for row in records),
                "unsupported_count": sum(row["role_graphs"][role]["status"] == "unsupported_source_or_graph_profile" for row in records)} for role in ROLES},
            input_files=[{"path": str(path), "sha256": audit._sha(body), "size_bytes": len(body)} for path, body in sorted(pins.files.items())],
            retained_files=[{"path": path.relative_to(output).as_posix(), "sha256": audit._sha(body), "size_bytes": len(body)} for path, body in sorted(copies.items())],
            scope="source-only conformance of historical deterministic native program projections; no learned full-program quality or runtime semantics",
            effect_scope="syntactic reference reads and empty assignment writes under declared pure Int annotations; other serialized effects retain profile assumptions",
            recorded_program_ids_authenticated=False, recorded_before_effect_graph_available=False)
        report["source_projection_graph_conformance_available"] = graph_count > 0
    except (audit.AuditInputError, OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        report.update(error=f"{type(exc).__name__}: {exc}")
    final._write(output / "native_program_graph.json", report)
    (output / "native_program_graph.json").chmod(0o600)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = evaluate(args.manifest, args.output)
    except (audit.AuditInputError, OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        parser.exit(3, f"native program graph refused: {type(exc).__name__}: {exc}\n")
    print(audit._canonical({key: report[key] for key in ("status", "manifest_sha256", "source_comparison_report_sha256")}).decode())
    return 0 if report["status"] == "passed" else 3


if __name__ == "__main__":
    sys.exit(main())
