#!/usr/bin/env python3
"""Audit frozen scalar feature vocabulary against captured source targets.

Counts describe an independent projection of inert target documents. No state,
optimizer, producer, source program, model or checker is executed.
"""
from __future__ import annotations

import argparse
import ast
import copy
import json
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

import codebase_ir_corpus_audit as audit
import codebase_ir_final_evaluation as final
import codebase_ir_final_lock as lock_tool
import codebase_ir_final_targets as targets
import codebase_ir_native_source384_diagnostics as native
import codebase_ir_native_source_comparison as comparison

INPUT_SCHEMA = "codebase-ir-native-feature-coverage-input@1"
REPORT_SCHEMA = "codebase-ir-native-feature-coverage@1"
PROFILE = "qualification/source-bound-scalar-feature-basis-coverage@1"
INPUT_ROLES = ("provenance_input", "parent_export", "child_export")
BATCH_ROLES = {"training_targets": "train", "tuning_targets": "tune", "canary_targets": "canary", "replay_targets": "replay"}
TRUE_FLAGS = {"source_bound_feature_coverage_available", "source_labels_rederived", "frozen_basis_signatures_rederived",
              "raw_exports_retained_unmodified", "all_declared_target_roles_preserved", "input_files_unchanged", "unknown_pretraining_exposure"}
FALSE_FLAGS = comparison.FALSE_FLAGS | {"native_feature_vector_execution_replayed", "model_predictions_evaluated", "optimizer_state_replayed",
    "training_absence_certified", "feature_recipe_execution_authenticated", "heldout_quality_verified", "feature_model_decoder_qualified",
    "complete_ancestral_exposure_verified", "normalized_feature_vectors_rederived"}
FEATURE_FIELDS = {"admitted", "columns", "domain_id", "excluded_projection_ids", "formalized", "normalization", "projection_ids", "projections",
                  "promotion_performed", "qualified", "schema", "training_sources", "training_targets_sha256"}
VIEW_FIELDS = {"expression", "feature_only", "logic_family", "producer_id", "producer_version", "profile", "projection_id", "properties",
               "representation_kind", "target_schema", "view_id", "view_role"}
PROJECTIONS = ("codebase_ir.contracts@1", "codebase_ir.program@1")


@dataclass(frozen=True)
class Limits:
    max_files: int = 4
    max_file_bytes: int = 1024 * 1024
    max_total_bytes: int = 4 * 1024 * 1024
    max_targets: int = 64
    max_columns: int = 4096
    max_atoms: int = 4096
    max_source_bytes: int = 65536

    def __post_init__(self):
        audit._require(all(type(v) is int and v > 0 for v in asdict(self).values()), "positive exact feature coverage limits required")


DEFAULT_LIMITS = Limits()


def _json(raw, limits):
    return audit._load_json(raw, audit.Limits(max_json_bytes=limits.max_file_bytes, max_json_nodes=150000))


def _same(a, b):
    return audit._canonical(a) == audit._canonical(b)


def _atom_record(projection, encoded, count):
    path, value = json.loads(encoded)
    return {"projection_id": projection, "atom": [path, value], "scalar_type": "null" if value is None else
            {str: "string", bool: "boolean", int: "integer", float: "number"}[type(value)], "count": count}


def _atoms(value, limits):
    result = Counter()
    total = 0

    def visit(node, path, depth):
        nonlocal total
        audit._require(depth <= 64, "scalar feature path depth exceeded")
        if type(node) is dict:
            for name in sorted(node):
                audit._text(name, "scalar feature field", 256)
                visit(node[name], [*path, name], depth + 1)
        elif type(node) is list:
            for index, child in enumerate(node):
                visit(child, [*path, index], depth + 1)
        else:
            audit._require(node is None or type(node) in {str, bool, int, float}, "JSON scalar feature value required")
            if type(node) is str:
                audit._require(len(node.encode()) <= 4096, "scalar feature string bound exceeded")
            if type(node) in {int, float}:
                audit._require(native._finite_number(node), "bounded finite scalar feature number required")
            audit._require(total < limits.max_atoms, "scalar feature atom budget exceeded")
            result[audit._canonical([path, node]).decode()] += 1
            total += 1

    visit(value, [], 0)
    return result


def _columns(feature, limits):
    audit._closed(feature, FEATURE_FIELDS, "frozen native feature basis")
    audit._require(feature["schema"] == "native-projection-feature-space/v1" and feature["domain_id"] == "codebase_ir"
                   and feature["projection_ids"] == list(PROJECTIONS) and feature["excluded_projection_ids"] == []
                   and feature["normalization"] == "log1p_then_l2_per_projection", "closed native scalar feature basis profile required")
    audit._require(all(feature[k] is False for k in ("admitted", "formalized", "qualified", "promotion_performed")), "feature basis authority elevation")
    columns = feature["columns"]
    audit._require(type(columns) is list and 1 <= len(columns) <= limits.max_columns, "bounded nonempty feature columns required")
    keys = []
    for column in columns:
        audit._require(type(column) is list and len(column) == 2 and column[0] in PROJECTIONS and type(column[1]) is str,
                       "typed projection/scalar atom column required")
        audit._require(len(column[1].encode()) <= 8192, "scalar column text bound exceeded")
        atom = json.loads(column[1], object_pairs_hook=audit._json_pairs, parse_constant=audit._reject_constant)
        audit._require(type(atom) is list and len(atom) == 2 and type(atom[0]) is list and len(atom[0]) <= 64
                       and all(type(v) is str or type(v) is int and 0 <= v <= limits.max_atoms for v in atom[0])
                       and not isinstance(atom[1], dict | list) and audit._canonical(atom).decode() == column[1], "canonical scalar column path/value required")
        _atoms(atom[1], limits)
        keys.append(tuple(column))
    audit._require(len(set(keys)) == len(keys) and keys == sorted(keys), "unique ordered feature columns required")
    audit._require(set(feature["projections"]) == set(PROJECTIONS), "complete projection descriptors required")
    return keys


def _source(raw, limits):
    source_limits = audit.Limits(max_source_bytes=limits.max_source_bytes)
    binding, label, reason = targets.derive_source(raw, source_limits)
    if label is None:
        return binding, None, reason
    function, body = label["function"], label["body"]
    if not (len(function["parameters"]) == 1 and function["parameters"][0]["sort"] == function["returns"] == "Int"
            and body.get("kind") == "binary" and body.get("operator") in {"Add", "Sub", "Mult"}
            and body["left"] == {"kind": "reference", "name": function["parameters"][0]["name"], "sort": "Int"}
            and body["right"].get("kind") == "literal" and body["right"].get("sort") == "Int"):
        return binding, None, "outside one-Int-parameter arithmetic literal source profile"
    return binding, label, None


def _program_view(program):
    """Closed positional feature view; retained native effect/order IDs stay raw."""
    document = {k: copy.deepcopy(v) for k, v in program.items() if k not in {"program_id", "metadata", "sources", "spans"}}
    maps = {}
    for collection, field, prefix in (("symbols", "symbol_id", "symbol"), ("expressions", "expression_id", "expression"),
                                      ("commands", "command_id", "command"), ("functions", "function_id", "function")):
        rows = document[collection]
        audit._require(type(rows) is list and len({r[field] for r in rows}) == len(rows), "unique native positional member identities required")
        maps[collection] = {row[field]: f"{prefix}:{index}" for index, row in enumerate(rows)}
        for row in rows:
            row.pop("source_ref_ids")
            row.pop("span_ids")
            row[field] = maps[collection][row[field]]

    def replace(values, mapping):
        audit._require(type(values) is list and all(v in mapping for v in values), "feature view unresolved native reference")
        return [mapping[v] for v in values]

    for row in document["expressions"]:
        row["operand_ids"] = replace(row["operand_ids"], maps["expressions"])
        row["symbol_ids"] = replace(row["symbol_ids"], maps["symbols"])
    for row in document["commands"]:
        row["expression_ids"] = replace(row["expression_ids"], maps["expressions"])
        row["target_symbol_ids"] = replace(row["target_symbol_ids"], maps["symbols"])
    for row in document["functions"]:
        for name in ("parameter_symbol_ids", "local_symbol_ids", "exception_symbol_ids"):
            row[name] = replace(row[name], maps["symbols"])
        audit._require(row["result_symbol_id"] in maps["symbols"], "feature view result symbol missing")
        row["result_symbol_id"] = maps["symbols"][row["result_symbol_id"]]
        cfg = row["cfg"]
        block_map = {block["block_id"]: f"block:{i}" for i, block in enumerate(cfg["blocks"])}
        audit._require(len(block_map) == len(cfg["blocks"]) and not cfg["edges"], "closed single-block CFG feature profile required")
        for block in cfg["blocks"]:
            block.pop("source_ref_ids")
            block.pop("span_ids")
            block["command_ids"] = replace(block["command_ids"], maps["commands"])
            block["block_id"] = block_map[block["block_id"]]
        cfg["entry_block_id"] = block_map[cfg["entry_block_id"]]
        for name in ("normal_exit_block_ids", "exceptional_exit_block_ids"):
            cfg[name] = replace(cfg[name], block_map)
        cfg["graph_id"] = "graph:0"
    document["global_symbol_ids"] = replace(document["global_symbol_ids"], maps["symbols"])
    return {"schema": "codebase-ir-native-structural-feature-view@1", "native_kind": "program", "document": document}


def _source_program(details, raw, label):
    graph = details["native_program"]
    binding = details["source_binding"]
    audit._require(len(graph["sources"]) == 1 and graph["sources"][0]["content_sha256"] == audit._sha(raw)
                   and graph["sources"][0]["source_id"] == binding["path"]
                   and graph["sources"][0]["source_revision"] == binding["source_revision"], "native source reference/body/revision differs")
    audit._require(graph["schema_version"] == "program-ir/v1" and len(graph["functions"]) == len(graph["commands"]) == 1
                   and len(graph["expressions"]) == 3 and len(graph["symbols"]) == 2 and not graph["global_symbol_ids"], "closed literal ProgramIR shape required")
    function, command = graph["functions"][0], graph["commands"][0]
    source_fn = label["function"]
    param = next((s for s in graph["symbols"] if s["kind"] == "parameter"), None)
    result = next((s for s in graph["symbols"] if s["kind"] == "result"), None)
    audit._require(param is not None and result is not None and param["name"] == source_fn["parameters"][0]["name"]
                   and param["type_ref"] == result["type_ref"] == function["return_type"] == "int"
                   and function["name"] == source_fn["name"] and function["parameter_symbol_ids"] == [param["symbol_id"]]
                   and function["result_symbol_id"] == result["symbol_id"], "source declarations/native typed members differ")
    symbol, literal, binary = graph["expressions"]
    audit._require(symbol["kind"] == "symbol" and symbol["symbol_ids"] == [param["symbol_id"]] and not symbol["operand_ids"]
                   and literal["kind"] == "literal" and literal["type_ref"] == "int"
                   and _same(literal["attributes"], {"value": label["body"]["right"]["value"]})
                   and binary["kind"] == "binary" and binary["operator"] == {"Add": "add", "Sub": "sub", "Mult": "mul"}[label["body"]["operator"]]
                   and binary["operand_ids"] == binary["evaluation_order"] == [symbol["expression_id"], literal["expression_id"]], "source literal/operator/operand correspondence failed")
    audit._require(command["kind"] == "return" and command["expression_ids"] == command["evaluation_order"] == [binary["expression_id"]]
                   and not command["target_symbol_ids"], "source return reference correspondence failed")
    cfg = function["cfg"]
    audit._require(len(cfg["blocks"]) == 1 and cfg["blocks"][0]["command_ids"] == [command["command_id"]]
                   and cfg["normal_exit_block_ids"] == [cfg["entry_block_id"]] == [cfg["blocks"][0]["block_id"]]
                   and cfg["exceptional_exit_block_ids"] == cfg["edges"] == [], "source single-return CFG correspondence failed")
    tree = ast.parse(raw.decode())
    fn = tree.body[0]
    expected_nodes = {param["symbol_id"]: fn.args.args[0], result["symbol_id"]: fn,
                      symbol["expression_id"]: fn.body[0].value.left, literal["expression_id"]: fn.body[0].value.right,
                      binary["expression_id"]: fn.body[0].value, command["command_id"]: fn.body[0], function["function_id"]: fn}
    lines = raw.splitlines(keepends=True)
    spans = {s["span_id"]: s for s in graph["spans"]}
    correspondence = {s["span_id"]: s for s in details["correspondence"]["spans"]}
    audit._require(len(spans) == len(graph["spans"]) == len(correspondence) == 6, "complete unique source span inventory required")
    for row in [*graph["symbols"], *graph["expressions"], command, function]:
        identity = row.get("symbol_id", row.get("expression_id", row.get("command_id", row.get("function_id"))))
        node = expected_nodes[identity]
        start = sum(map(len, lines[:node.lineno - 1])) + node.col_offset
        end = sum(map(len, lines[:node.end_lineno - 1])) + node.end_col_offset
        audit._require(len(row["span_ids"]) == 1 and row["span_ids"][0] in spans, "native member source span missing")
        span = spans[row["span_ids"][0]]
        bound = correspondence[span["span_id"]]
        audit._require(row["source_ref_ids"] == [graph["sources"][0]["ref_id"]] and span["source_ref_id"] == bound["source_ref_id"] == row["source_ref_ids"][0], "member/span/source reference differs")
        audit._require(type(span["start_byte"]) is type(span["end_byte"]) is int and span["start_byte"] == start and span["end_byte"] == end
                       and bound["start_byte"] == start and bound["end_byte"] == end and bound["source_text"] == raw[start:end].decode(), "source AST byte span differs")
    return _unknown_sorts(details)


def _unknown_sorts(details):
    graph = details["native_program"]
    unknown = [{"field": "type_ref", "native_id": row["expression_id"], "native_kind": "expressions", "value": row["type_ref"]}
               for row in graph["expressions"] if row["type_ref"] == "any"]
    audit._require(all(row["type_ref"] in {"int", "any"} for row in graph["expressions"])
                   and _same(unknown, details["unknown_inventory"]), "unknown-sort inventory differs from native expressions")
    return unknown


def _target(target, identifier, role, version, columns, loader, limits):
    unit, raw = loader.native_target(target, identifier, "train" if role == "replay" else role)
    audit._require(len(raw) <= limits.max_source_bytes, "target source byte bound exceeded")
    details = target["validation"][0]["details"]
    audit._require(all(details[k] is False for k in ("completion_authority", "execution_authority", "proof_authority", "source_semantics_verified", "semantic_formula_decoder")), "target source/semantic authority elevation")
    source_binding, label, reason = _source(raw, limits)
    views = {}
    for projection in target["projections"]:
        audit._closed(projection, VIEW_FIELDS, "native source feature projection")
        identity = projection["projection_id"]
        audit._require(identity in PROJECTIONS and identity not in views and projection["feature_only"] is True
                       and projection["target_schema"] == audit.NATIVE_TARGET_SCHEMA, "complete unique feature-only projections required")
        views[identity] = projection["expression"]
    audit._require(set(views) == set(PROJECTIONS) and details["authored_contracts"] == details["native_contracts"] == [], "closed empty-contract feature profile required")
    audit._require(_same(views["codebase_ir.contracts@1"], {"schema": "codebase-ir-native-structural-feature-view@1", "native_kind": "contracts", "documents": []}), "empty contract projection mismatch")
    unknown = _source_program(details, raw, label) if label is not None else _unknown_sorts(details)
    audit._require(_same(views["codebase_ir.program@1"], _program_view(details["native_program"])), "positional feature view differs from raw native ProgramIR")
    atoms = {identity: _atoms(view, limits) for identity, view in views.items()}
    counts = [atoms[identity][atom] for identity, atom in columns]
    vocabulary = set(columns)
    unrepresented = [_atom_record(identity, atom, count)
                     for identity in PROJECTIONS for atom, count in sorted(atoms[identity].items()) if (identity, atom) not in vocabulary]
    return {"id": identifier, "version_id_claim": version, "original_role": role, "exposure_role": "train" if role == "replay" else role,
            "source_sha256": audit._sha(raw), "source_bytes": len(raw), "source_path_claim": unit["path"], "source_revision_claim": unit["revision"],
            "native_target_source_digest": target["source_digest"], "source_binding": source_binding,
            "source_label": label, "source_label_disposition": "supported" if label is not None else "unsupported", "source_label_reason": reason,
            "native_program_sha256": audit._sha(audit._canonical(details["native_program"])),
            "scalar_atom_count": sum(sum(v.values()) for v in atoms.values()), "frozen_basis_counts": counts,
            "frozen_basis_signature_sha256": audit._sha(audit._canonical(counts)), "unrepresented_atoms": unrepresented,
            "scalar_atom_vocabulary": [_atom_record(identity, atom, count) for identity in PROJECTIONS for atom, count in sorted(atoms[identity].items())],
            "unknown_sort_inventory": unknown, "unknown_sort_inventory_disposition": "rederived" if label is not None else "native_inventory_rederived_source_profile_unsupported",
            "projection_losses": {"native_source_reference_count": len(details["native_program"]["sources"]),
                "native_source_span_count": len(details["native_program"]["spans"]), "feature_view_source_reference_count": 0,
                "feature_view_source_span_count": 0, "source_provenance_retained_outside_feature_expression": True,
                "native_identity_renumbering": "positional_member_ids_with_original_effect_and_evaluation_order_labels_retained",
                "source_runtime_loss_semantics_certified": False},
            "source_runtime_truth_verified": False, "model_prediction_available": False}, atoms


def _coverage(provenance_spec, exports, limits):
    audit._closed(provenance_spec, {"schema", "units", "native_records", "ancestral_training", "ancestry_complete"}, "original provenance capture input")
    records = provenance_spec["native_records"]
    audit._require(provenance_spec["schema"] == "codebase-ir-corpus-audit-input@1" and provenance_spec["units"] == []
                   and type(records) is list and len(records) == 2 and provenance_spec["ancestral_training"] == [], "two captured export records required")
    versions = []
    for record in records:
        audit._closed(record, {"file", "sha256", "unit_metadata", "version_id"}, "captured export record")
        audit._relative_path(record["file"], "captured export file")
        audit._require(record["unit_metadata"] == {}, "source roles must remain original")
        versions.append(audit._text(record["version_id"], "captured version", 128))
    audit._require(len(set(versions)) == 2, "distinct captured version labels required")
    basis = exports["parent_export"]["feature_space"]
    columns = _columns(basis, limits)
    audit._require(_same(basis, exports["child_export"]["feature_space"]), "child changed frozen feature basis")
    loader = audit._Loader(Path("/nonexecuting-feature-coverage"), audit.Limits(max_source_bytes=limits.max_source_bytes))
    rows, parent_training_atoms = [], set()
    for export_role, version in zip(("parent_export", "child_export"), versions, strict=True):
        exported = exports[export_role]
        audit._closed(exported, {"contract", "feature_space", "report", "state"}, "native feature checkpoint envelope")
        report = exported["report"]
        provenance = audit._closed(report["codebase_provenance"], audit.NATIVE_PROVENANCE_FIELDS, "source feature provenance")
        audit._require(provenance["schema"] == audit.NATIVE_LINEAGE_SCHEMA and all(provenance[k] is False for k in audit.NATIVE_FALSE), "nonauthoritative feature provenance required")
        audit._require(provenance["parent_version_id"] == (None if export_role == "parent_export" else versions[0])
                       and provenance["continuation"] == ("fresh_feature_basis" if export_role == "parent_export" else "exact_frozen_basis_adam_resume"), "captured parent/continuation claim differs")
        selections = provenance["selections"]
        audit._require(type(selections) is list and 3 <= len(selections) <= 16, "bounded original selections required")
        selected_paths, selected_roles = {}, set()
        for selection in selections:
            audit._closed(selection, {"path", "role", "contracts"}, "source feature selection")
            path = audit._relative_path(selection["path"], "selected source path")
            audit._require(path not in selected_paths and selection["role"] in {"train", "tune", "canary"}
                           and selection["contracts"] == [], "unique original empty-contract roles required")
            selected_paths[path] = selection["role"]
            selected_roles.add(selection["role"])
        audit._require(selected_roles == {"train", "tune", "canary"}, "original source roles incomplete")
        basis_sha = audit._sha(audit._canonical(basis))
        audit._require(report["feature_space_sha256"] == provenance["feature_space_sha256"] == basis_sha, "basis raw object binding differs")
        audit._digest(report["contract_sha256"], "recorded contract identity")
        audit._require(report["contract_sha256"] == provenance["contract_sha256"], "recorded contract identity differs")
        for batch, role in BATCH_ROLES.items():
            values = provenance[batch]
            audit._require(type(values) is list and 1 <= len(values) <= 32 and len(rows) + len(values) <= limits.max_targets, "bounded complete target population required")
            for index, target in enumerate(values):
                identifier = f"native/{version}/{batch}/{index}"
                row, atoms = _target(target, identifier, role, version, columns, loader, limits)
                audit._require(selected_paths.get(row["source_path_claim"]) == row["exposure_role"], "target batch role differs from independent original selection")
                for projection in target["projections"]:
                    audit._require(_same({k: projection[k] for k in basis["projections"][projection["projection_id"]]},
                                         basis["projections"][projection["projection_id"]]), "projection descriptor differs from frozen basis")
                rows.append(row)
                if export_role == "parent_export" and batch == "training_targets":
                    parent_training_atoms.update((identity, atom) for identity, values in atoms.items() for atom in values)
            if batch in {"training_targets", "tuning_targets"}:
                prefix = "training" if batch == "training_targets" else "tuning"
                audit._require(report[prefix + "_target_count"] == len(values) and type(report[prefix + "_target_count"]) is int
                               and report[prefix + "_targets_sha256"] == audit._sha(audit._canonical(values)), "recorded target population/digest differs")
        audit._require(all(r["source_path_claim"] in {s["path"] for s in provenance["selections"]} for r in rows if r["version_id_claim"] == version), "target outside selected source paths")
    audit._require(set(columns) == parent_training_atoms and basis["training_targets_sha256"] == exports["parent_export"]["report"]["training_targets_sha256"], "frozen vocabulary differs from exact parent training atoms")
    audit._require(basis["training_sources"] == sorted({t["source_digest"] for t in exports["parent_export"]["report"]["codebase_provenance"]["training_targets"]}), "basis training source declarations differ")
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["frozen_basis_signature_sha256"]].append(row)
    collision_groups = []
    for signature, members in sorted(grouped.items()):
        labels = {audit._sha(audit._canonical(r["source_label"])) for r in members if r["source_label"] is not None}
        roles = sorted({r["original_role"] for r in members})
        literals = sorted({r["source_label"]["body"]["right"]["value"] for r in members if r["source_label"] is not None})
        collision_groups.append({"signature_sha256": signature, "member_ids": [r["id"] for r in members], "original_roles": roles,
                                 "distinct_source_label_count": len(labels), "source_literals": literals,
                                 "different_source_labels_same_signature": len(labels) > 1,
                                 "cross_role_literal_collision": len(literals) > 1 and len(set(roles) - {"replay"}) > 1,
                                 "model_predictions_compared": False, "heldout_independence_verified": False})
    return {"targets": rows, "historical_target_count": len(rows), "unique_source_count": len({r["source_sha256"] for r in rows}),
            "frozen_basis_column_count": len(columns), "frozen_basis_column_sha256": audit._sha(audit._canonical(basis["columns"])),
            "frozen_basis_canonical_sha256": audit._sha(audit._canonical(basis)), "role_counts": dict(sorted(Counter(r["original_role"] for r in rows).items())),
            "frozen_basis_columns": [_atom_record(identity, atom, 0) for identity, atom in columns],
            "out_of_vocabulary_target_count": sum(bool(r["unrepresented_atoms"]) for r in rows),
            "out_of_vocabulary_atom_count": sum(sum(a["count"] for a in r["unrepresented_atoms"]) for r in rows),
            "distinguishing_collision_group_count": sum(g["different_source_labels_same_signature"] for g in collision_groups),
            "cross_role_literal_collision_group_count": sum(g["cross_role_literal_collision"] for g in collision_groups),
            "unknown_sort_occurrence_count": sum(len(r["unknown_sort_inventory"] or []) for r in rows),
            "unsupported_source_target_count": sum(r["source_label"] is None for r in rows), "collision_groups": collision_groups,
            "declared_normalization_claim": basis["normalization"], "normalization_applied_by_auditor": False,
            "ancestral_exposure_claims": {role: exported["report"]["codebase_provenance"]["ancestral_training"] for role, exported in exports.items()},
            "contract_identities": {role: {"contract_sha256_claim": exported["report"]["contract_sha256"],
                "contract_body_canonical_sha256": audit._sha(audit._canonical(exported["contract"])), "producer_identity_recipe_verified": False}
                for role, exported in exports.items()},
            "recorded_producer_effort": {role: {k: exported["report"][k] for k in ("attempted_epochs", "epochs", "elapsed_seconds")}
                for role, exported in exports.items()}}


def evaluate(manifest: Path, output: Path, limits: Limits = DEFAULT_LIMITS):
    manifest, output = manifest.absolute(), output.absolute()
    audit._require(str(manifest.resolve(strict=True)) == str(manifest), "canonical feature coverage manifest required")
    pins = native.Pins(limits)
    raw_manifest = pins.read(manifest, min(limits.max_file_bytes, 256 * 1024))
    spec = _json(raw_manifest, limits)
    audit._closed(spec, {"schema", *INPUT_ROLES}, "feature coverage manifest")
    audit._require(spec["schema"] == INPUT_SCHEMA, "feature coverage input schema required")
    raw_inputs = {}
    for role in INPUT_ROLES:
        _, raw_inputs[role] = pins.descriptor(spec[role])
    original = _json(raw_inputs["provenance_input"], limits)
    audit._require(type(original.get("native_records")) is list and len(original["native_records"]) == 2, "exact original export selectors required")
    for role, record in zip(("parent_export", "child_export"), original["native_records"], strict=True):
        audit._require(record["sha256"] == spec[role]["sha256"] and record["file"] == Path(spec[role]["path"]).name, "original export selector/raw pin join failed")
    lock_tool._preflight_output(output, sorted({p.parent for p in pins.files}))
    exports = {role: _json(raw_inputs[role], limits) for role in ("parent_export", "child_export")}
    summary = _coverage(original, exports, limits)
    pins.recheck()
    output.mkdir(exist_ok=False)
    retained = []
    for index, (path, raw) in enumerate(pins.files.items()):
        copy_path = output / f"input-{index:02d}-{path.name}"
        copy_path.write_bytes(raw)
        audit._require(final.Capture.regular(copy_path, len(raw)) == raw, "retained feature coverage copy mismatch")
        retained.append({"path": str(path), "retained_path": str(copy_path), "sha256": audit._sha(raw), "size_bytes": len(raw)})
    pins.recheck()
    for row in retained:
        audit._require(final.Capture.regular(Path(row["retained_path"]), row["size_bytes"]) == pins.files[Path(row["path"])], "late retained feature coverage copy drift")
    report = {"schema": REPORT_SCHEMA, "status": "passed", "profile": PROFILE,
              "scope": "historical_source_bound_targets_and_independent_frozen_scalar_column_counts_only",
              "manifest_sha256": audit._sha(raw_manifest), **{role + "_sha256": spec[role]["sha256"] for role in INPUT_ROLES},
              **dict.fromkeys(TRUE_FLAGS, True), **dict.fromkeys(FALSE_FLAGS, False), **summary,
              "input_files": retained, "limits": asdict(limits), "captured_input_file_count": len(pins.files), "captured_input_bytes": pins.total,
              "additional_attempted_training_epochs": 0, "new_final_assignments": 0,
              "limitations": ["Count signatures project retained target scalar atoms onto the declared frozen columns; they are not replayed native numerical feature vectors or model predictions.",
                  "Distinct literal targets can share a fixed-basis signature. This certifies scoped representation indistinguishability, not runtime equivalence, learned performance or a qualified decoder.",
                  "Native any-sort occurrences remain unknown rather than being repaired from source annotations. Annotations are declared assumptions, not runtime facts.",
                  "Embedded source, selected version/head labels and recorded ancestral exposure remain unsigned claims; absent earlier training exposure remains unknown.",
                  "Original train/tune/canary/replay roles are preserved; replay is conservatively training exposure. No historical source is assigned to FINAL.",
                  "Checkpoint state and optimizer bodies are not interpreted. Owner modules, source programs, training, inference, compilers and checkers are never executed."]}
    final._write(output / "native_feature_coverage.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = evaluate(args.manifest, args.output)
    except (audit.AuditInputError, ValueError, OSError, KeyError, TypeError, OverflowError, RecursionError, UnicodeError) as exc:
        print(json.dumps({"schema": REPORT_SCHEMA, "status": "refused", "reason": str(exc),
                          "unknown_pretraining_exposure": True, **dict.fromkeys(FALSE_FLAGS, False)}, sort_keys=True), file=sys.stderr)
        return 3
    print(json.dumps({"status": report["status"], "targets": report["historical_target_count"],
                      "distinguishing_collision_groups": report["distinguishing_collision_group_count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
