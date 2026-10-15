"""Bounded function targets from exact public bytes and native AST records.

Vocabulary is fitted exclusively on training functions. Numeric modalities are
lossy count views; ordered syntax/native records remain separate sidecars.
"""
from __future__ import annotations

import ast
from collections import Counter
import hashlib
import json
import math
from pathlib import PurePosixPath
import re

SCHEMA = "terminal-typed-function-count-targets@1"
MAX_FILES, MAX_FILE_BYTES, MAX_FUNCTIONS = 5, 8192, 128
MAX_NODES, MAX_ATOMS, MAX_REPORT_BYTES = 16384, 8192, 16 * 1024 * 1024
MODALITIES = ("ast", "calls", "diagnostics", "effects", "imports", "interfaces",
              "literals", "references", "scopes", "symbols", "types")
CLAIMS = {"proof_authority": False, "source_model_equivalence_proved": False,
          "exact_source_decoder": False, "full_task_satisfaction_proved": False,
          "training_convergence_proved": False, "source_body_execution": False,
          "count_reconstruction_is_semantic_equivalence": False}


class TypedTargetError(ValueError):
    """The bounded corpus, native provenance or training-only projection differs."""


def wire(value):
    try:
        result = json.dumps(value, sort_keys=True, separators=(",", ":"),
                            ensure_ascii=True, allow_nan=False).encode()
    except (TypeError, ValueError, RecursionError) as error:
        raise TypedTargetError("finite bounded JSON required") from error
    if len(result) > MAX_REPORT_BYTES:
        raise TypedTargetError("typed target byte bound exceeded")
    return result


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def atom(modality, *values):
    if modality not in MODALITIES:
        raise TypedTargetError("unknown target modality")
    return modality + "|" + wire(list(values)).decode()


def _need(condition, message):
    if not condition:
        raise TypedTargetError(message)


def _members(manifest):
    _need(type(manifest) is dict and manifest.get("schema") == "terminal-codebase-ir-corpus@1",
          "named public corpus manifest required")
    tasks = manifest.get("tasks")
    _need(type(tasks) is list and 1 <= len(tasks) <= 16, "bounded task-exclusive corpus required")
    members, task_ids = {}, set()
    for task in tasks:
        _need(type(task) is dict and type(task.get("task_id")) is str
              and task["task_id"] not in task_ids, "unique task identity required")
        task_ids.add(task["task_id"])
        _need(task.get("split") in {"train", "validation", "evaluation"}, "explicit split required")
        _need(type(task.get("sources")) is list and task["sources"], "explicit source members required")
        for pin in task["sources"]:
            path = pin.get("path")
            _need(type(path) is str and PurePosixPath(path).as_posix() == path
                  and not PurePosixPath(path).is_absolute() and ".." not in PurePosixPath(path).parts
                  and path.endswith(".py") and path not in members, "unique canonical Python member required")
            _need(type(pin.get("sha256")) is str and re.fullmatch("[0-9a-f]{64}", pin["sha256"])
                  and type(pin.get("bytes")) is int and 0 < pin["bytes"] <= MAX_FILE_BYTES,
                  "exact bounded source pin required")
            members[path] = {**pin, "task_id": task["task_id"], "split": task["split"]}
    _need(1 <= len(members) <= MAX_FILES, "source member bound exceeded")
    _need(any(row["split"] == "train" for row in members.values()), "training task required")
    return dict(sorted(members.items()))


def _span(node, offsets):
    if not hasattr(node, "lineno"):
        return None
    return {"start_byte": offsets[node.lineno - 1] + node.col_offset,
            "end_byte": offsets[node.end_lineno - 1] + node.end_col_offset,
            "start_line": node.lineno, "end_line": node.end_lineno,
            "start_column": node.col_offset, "end_column": node.end_col_offset}


def _literal(value):
    kind = type(value).__name__
    if value is None:
        return ["none", "None"]
    if value is Ellipsis:
        return ["ellipsis", "..."]
    if type(value) is bool:
        return ["bool", "true" if value else "false"]
    if type(value) is int and value.bit_length() <= 256:
        return ["int", str(value)]
    if type(value) is str and len(value.encode("utf-8")) <= 256:
        return ["str", value]
    if type(value) is bytes and len(value) <= 128:
        return ["bytes", value.hex()]
    if type(value) is float and math.isfinite(value):
        return ["float_hex", value.hex()]
    if type(value) is complex and math.isfinite(value.real) and math.isfinite(value.imag):
        return ["complex_hex", value.real.hex(), value.imag.hex()]
    return None


def _syntax(function, offsets):
    counts, nodes, edges, residuals = Counter(), [], [], []
    def visit(node, parent=None, field=None, position=None, ancestor=None, depth=0):
        _need(depth <= 128 and len(nodes) < MAX_NODES, "bounded AST occurrence tree required")
        index = len(nodes)
        kind = type(node).__name__
        row = {"node_id": f"node:{index}", "kind": kind, "span": _span(node, offsets)}
        nodes.append(row)
        counts[atom("ast", "kind", kind)] += 1
        if parent is not None:
            edges.append({"parent": f"node:{parent}", "field": field,
                          "list_position": position, "child": f"node:{index}"})
            counts[atom("ast", "edge", nodes[parent]["kind"], field, kind)] += 1
            if ancestor is not None:
                grandparent, prior_field = ancestor
                counts[atom("ast", "triple", nodes[grandparent]["kind"], prior_field,
                            nodes[parent]["kind"], field, kind)] += 1
        if isinstance(node, ast.Constant):
            value = _literal(node.value)
            if value is None:
                residuals.append({"kind": "literal_outside_bounded_atom_profile", "type": type(node.value).__name__,
                                  "span": row["span"]})
            else:
                row["literal"] = value
                counts[atom("literals", *value)] += 1
        for child_field, value in ast.iter_fields(node):
            if isinstance(value, ast.AST):
                visit(value, index, child_field, None, None if parent is None else (parent, field), depth + 1)
            elif isinstance(value, list):
                for number, child in enumerate(value):
                    if isinstance(child, ast.AST):
                        visit(child, index, child_field, number, None if parent is None else (parent, field), depth + 1)
    visit(function)
    return counts, {"nodes": nodes, "field_edges": edges}, residuals


def _inside(span, container):
    return span is not None and container["start_byte"] <= span["start_byte"] <= span["end_byte"] <= container["end_byte"]


def _native_target(record, function, span):
    counts, target, selected_ids = Counter(), {}, {}
    owners = [row for row in record["symbols"] if row["name"] == function.name
              and row["kind"] in {"function", "method", "constructor"} and row["span"] == span]
    _need(len(owners) == 1, "one exact native function symbol/span correspondence required")
    scopes = {row["scope_id"]: row for row in record["scopes"]}
    symbols = {row["symbol_id"]: row for row in record["symbols"]}
    imported = {row["local_name"] for row in record["imports"]}
    local_names = {row["name"]: row["kind"] for row in record["symbols"]}
    def role(name):
        base = re.split(r"[.\[]", name)[0]
        return "imported" if base in imported else local_names.get(base, "unresolved")
    for family in ("symbols", "scopes", "calls", "effects", "imports", "references", "diagnostics"):
        selected = [row for row in record[family] if _inside(row.get("span"), span)]
        selected_ids[family] = selected
        normalized = []
        for number, row in enumerate(selected):
            scope = scopes.get(row.get("scope_id"))
            scope_kind = "none" if scope is None else scope["kind"]
            values = {"normalized_id": f"{family}:{number}"}
            if family == "symbols":
                values.update(kind=row["kind"], visibility=row["visibility"], flags=row["flags"])
                counts[atom(family, row["kind"], row["visibility"], scope_kind)] += 1
                for flag in row["flags"]:
                    counts[atom(family, "flag", flag)] += 1
                signature = row["signature"]
                if signature is not None:
                    values["signature"] = {k: v for k, v in signature.items() if k != "parameters"}
                    values["signature"]["parameters"] = [{k: v for k, v in parameter.items() if k != "name"}
                                                               for parameter in signature["parameters"]]
                    counts[atom("interfaces", "parameter_count", len(signature["parameters"]))] += 1
                    counts[atom("interfaces", "async", signature["is_async"], "generator", signature["is_generator"])] += 1
                    annotations = [signature["return_annotation"]]
                    for parameter in signature["parameters"]:
                        counts[atom("interfaces", "parameter", parameter["kind"], parameter["default_kind"])] += 1
                        annotations.append(parameter["annotation"])
                    for annotation in annotations:
                        if len(annotation.encode()) <= 128:
                            counts[atom("types", "annotation", annotation or "unknown")] += 1
            elif family == "scopes":
                parent = scopes.get(row["parent_scope_id"])
                owner = symbols.get(row["owner_symbol_id"])
                values.update(kind=row["kind"], parent_kind="none" if parent is None else parent["kind"],
                              owner_kind="none" if owner is None else owner["kind"])
                counts[atom(family, row["kind"], values["parent_kind"], values["owner_kind"])] += 1
            elif family == "calls":
                values.update(kind=row["kind"], argument_count=row["argument_count"],
                              awaited=row["is_awaited"], callee_role=role(row["callee_name"]),
                              named_argument_count=len(row["named_argument_names"]))
                counts[atom(family, row["kind"], row["argument_count"], row["is_awaited"], values["callee_role"], scope_kind)] += 1
            elif family == "effects":
                values.update(kind=row["kind"], operation=row["operation"], subject_role=role(row["subject"]))
                counts[atom(family, row["kind"], row["operation"], scope_kind)] += 1
            elif family == "imports":
                values.update(kind=row["kind"], type_only=row["is_type_only"])
                counts[atom(family, row["kind"], row["is_type_only"], scope_kind)] += 1
                if len(row["module"].encode()) <= 128:
                    values["module"] = row["module"]
                    counts[atom(family, "module", row["module"])] += 1
            elif family == "references":
                values.update(context=row["context"], qualified=row["is_qualified"], role=role(row["name"]))
                counts[atom(family, row["context"], row["is_qualified"], values["role"], scope_kind)] += 1
            else:
                values.update(code=row["code"], severity=row["severity"])
                counts[atom(family, row["code"], row["severity"])] += 1
            normalized.append(values)
        target[family] = normalized
    binding = {"symbol_id": owners[0]["symbol_id"], "scope_ids": [row["scope_id"] for row in record["scopes"]
               if row["owner_symbol_id"] == owners[0]["symbol_id"]], "symbol_span": owners[0]["span"]}
    return counts, target, binding, selected_ids


def _file_rows(pin, source, raw):
    from ipfs_datasets_py.logic.software_contracts.ast_ir import ASTRecord
    from ipfs_datasets_py.logic.software_contracts.content import cid_for_bytes, cid_for_structured
    from ipfs_datasets_py.logic.formalization.autoencoder.security import codebase_autoencoder as baseline
    _need(type(raw) is bytes and len(raw) == pin["bytes"] and sha(raw) == pin["sha256"], "public source byte pin differs")
    payload = source["ast"]
    _need(type(payload) is dict and len(wire(payload)) <= MAX_REPORT_BYTES, "bounded native AST artifact required")
    native = ASTRecord.from_dict(payload).to_dict()
    _need(wire(native) == wire(payload) and cid_for_structured(native) == source["ast_cid"], "native AST identity differs")
    provenance = native["provenance"]
    _need(source["path"] == pin["path"] == provenance["path"]
          and source["sha256"] == pin["sha256"] and source["bytes"] == len(raw)
          and source["source_cid"] == provenance["source_cid"] == cid_for_bytes(raw), "native source provenance differs")
    _need(provenance["repository_tree_cid"] is not None
          and provenance["revision"] == "snapshot:" + provenance["repository_tree_cid"], "native snapshot revision binding required")
    _need(source["parse_status"] == "ok", "failed or partial native parse remains unsupported")
    tree = ast.parse(raw.decode("utf-8"))
    _need(sum(1 for _ in ast.walk(tree)) <= MAX_NODES, "file syntax node bound exceeded")
    offsets = [0] + [index + 1 for index, value in enumerate(raw) if value == 10]
    original44, unsupported = baseline._features({pin["path"]: raw}, [pin["path"]], MAX_FUNCTIONS)
    _need(not unsupported, "native baseline cannot silently omit source")
    baseline_rows = {row["row_id"]: row for row in original44}
    rows, covered = [], {family: set() for family in ("symbols", "scopes", "calls", "effects", "imports", "references", "diagnostics")}
    def visit(node, prefix=""):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            span = _span(node, offsets)
            syntax_counts, syntax, residuals = _syntax(node, offsets)
            native_counts, target, native_binding, selected = _native_target(native, node, span)
            counts = syntax_counts + native_counts
            _need(len(counts) <= MAX_ATOMS, "function atom bound exceeded")
            ast_hash = sha(ast.dump(node, include_attributes=False).encode())
            identity = {"path": pin["path"], "symbol": prefix + node.name,
                        "line": node.lineno, "ast_sha256": ast_hash}
            row_id = sha(wire(identity))
            _need(row_id in baseline_rows, "baseline function row identity differs")
            for family, chosen in selected.items():
                covered[family].update(sha(wire(row)) for row in chosen)
            rows.append({**identity, "row_id": row_id, "unit_id": row_id,
                "task_id": pin["task_id"], "split": pin["split"],
                "start_byte": span["start_byte"], "end_byte": span["end_byte"],
                "source_sha256": pin["sha256"], "source_cid": source["source_cid"],
                "native_ast_cid": source["ast_cid"], "native_binding": native_binding,
                "atom_counts": dict(sorted(counts.items())), "baseline44_features": baseline_rows[row_id]["features"],
                "lexical_text": raw[span["start_byte"]:span["end_byte"]].decode(),
                "typed_target": {"syntax": syntax, "native_normalized": target,
                                  "unsupported": residuals + [row for row in native["unsupported"] if _inside(row.get("span"), span)]}})
            prefix += node.name + "."
        elif isinstance(node, ast.ClassDef):
            prefix += node.name + "."
        for child in ast.iter_child_nodes(node):
            visit(child, prefix)
    visit(tree)
    _need(len(rows) == len(original44), "complete native baseline function inventory differs")
    outside = {family: [row for row in native[family] if sha(wire(row)) not in covered[family]] for family in covered}
    return rows, {"path": pin["path"], "task_id": pin["task_id"], "split": pin["split"],
        "source_sha256": pin["sha256"], "source_cid": source["source_cid"], "native_ast_cid": source["ast_cid"],
        "native_provenance": provenance, "native_frontend": native["frontend"],
        "native_module": native["module"], "file_scope_residuals": outside,
        "unsupported": native["unsupported"], "syntax_origin": "independent Python ast.parse of exact native-CID-bound bytes",
        "native_record_lacks_full_syntax_nodes_and_literals": True}, list(baseline.FEATURES)


def build_targets(corpus_manifest, source_records, source_bytes=None):
    """Return per-function targets; source bytes are supplied, never discovered."""
    members = _members(corpus_manifest)
    if type(source_records) is dict:
        records = dict(source_records)
    else:
        _need(type(source_records) is list and len(source_records) <= MAX_FILES, "bounded source record list required")
        records = {row["path"]: row for row in source_records}
        _need(len(records) == len(source_records), "duplicate source record refused")
    _need(set(records) == set(members), "complete source/native record membership differs")
    if source_bytes is not None:
        _need(type(source_bytes) is dict and set(source_bytes) == set(members), "complete explicit byte mapping required")
    rows, files, original44_names = [], [], None
    for path, pin in members.items():
        source = records[path]
        raw = source.get("source_bytes") if source_bytes is None else source_bytes[path]
        found, file_record, original44_names = _file_rows(dict(pin, path=path), source, raw)
        rows.extend(found)
        files.append(file_record)
    _need(1 <= len(rows) <= MAX_FUNCTIONS, "bounded complete function inventory required")
    ast_splits = {}
    for row in rows:
        prior = ast_splits.setdefault(row["ast_sha256"], row["split"])
        _need(prior == row["split"], "crosssplit exact function AST leakage refused")
    training = [row for row in rows if row["split"] == "train"]
    vocabulary = sorted({key for row in training for key in row["atom_counts"]})
    _need(0 < len(vocabulary) <= MAX_ATOMS, "training-only atom vocabulary exceeds bound")
    spans = []
    for modality in sorted(MODALITIES):
        indices = [i for i, key in enumerate(vocabulary) if key.startswith(modality + "|")]
        if indices:
            spans.append({"modality": modality, "start": indices[0], "stop": indices[-1] + 1})
    known = set(vocabulary)
    for row in rows:
        counts = row["atom_counts"]
        numeric = [math.log1p(counts.get(key, 0)) for key in vocabulary]
        for block in spans:
            norm = math.sqrt(sum(value * value for value in numeric[block["start"]:block["stop"]])) or 1.0
            numeric[block["start"]:block["stop"]] = [value / norm for value in numeric[block["start"]:block["stop"]]]
        unknown = [{"atom": key, "count": value} for key, value in counts.items() if key not in known]
        row.update(features=numeric, vector=list(numeric), raw_counts=[counts.get(key, 0) for key in vocabulary],
                   unknown_atoms=unknown, oov_atoms=list(unknown),
                   known_atom_mass=sum(counts.get(key, 0) for key in vocabulary),
                   unknown_atom_mass=sum(item["count"] for item in unknown))
    result = {"schema": SCHEMA, "representation": "lossy typed structural per-function count reconstruction",
        "feature_names": vocabulary, "input_width": len(vocabulary), "modality_spans": spans,
        "vocabulary_fit_split": "train", "vocabulary_fit_unit_ids": sorted(row["unit_id"] for row in training),
        "heldout_atoms_added_to_vocabulary": False, "identities_spans_cids_in_learned_vectors": False,
        "baseline44_feature_names": original44_names, "baseline44_is_separate": True,
        "split_counts": {split: sum(row["split"] == split for row in rows) for split in ("train", "validation", "evaluation")},
        "rows": rows, "files": files, "corpus_unsupported_frontier": corpus_manifest.get("unsupported_sources", []),
        "claims": dict(CLAIMS)}
    wire(result)
    return result


def validate_targets(corpus_manifest, source_records, expected, source_bytes=None):
    observed = build_targets(corpus_manifest, source_records, source_bytes)
    _need(wire(observed) == wire(expected), "complete typed target replay differs")
    return {"schema": "terminal-typed-function-count-target-replay@1", "verified": True,
            "target_sha256": sha(wire(observed)), "rows": len(observed["rows"]),
            "input_width": observed["input_width"], "claims": dict(CLAIMS)}
