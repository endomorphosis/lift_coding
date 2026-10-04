#!/usr/bin/env python3
"""Reconstruct bounded import metadata from explicitly captured Python sources."""
from __future__ import annotations

import argparse
import ast
import os
import sys
from collections import defaultdict
from pathlib import Path, PurePosixPath

import codebase_ir_corpus_audit as audit

REPORT_SCHEMA = "codebase-ir-source-metadata-reconstruction@1"
SAFE_BUILTINS = frozenset({
    "int", "bool", "float", "str", "bytes", "object", "len", "range", "abs", "min", "max", "sum",
    "round", "list", "tuple", "dict", "set", "frozenset", "enumerate", "zip", "all", "any", "sorted",
    "reversed", "type", "isinstance", "issubclass", "Exception", "ValueError", "TypeError", "__name__",
    "__doc__", "__package__",
})
DYNAMIC_NAMES = frozenset({"__import__", "eval", "exec", "globals", "locals", "getattr", "setattr", "vars"})


def _module(path: str) -> tuple[str, str]:
    parts = list(PurePosixPath(path).parts)
    parts[-1] = parts[-1][:-3]
    initializer = parts[-1] == "__init__"
    if initializer:
        parts.pop()
    name = ".".join(parts)
    package = name if initializer else ".".join(parts[:-1])
    return name, package


def _module_bindings(tree: ast.Module) -> set[str]:
    result = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            result.add(node.name)
        elif isinstance(node, ast.Assign | ast.AnnAssign):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                result.update(item.id for item in ast.walk(target) if isinstance(item, ast.Name))
        elif isinstance(node, ast.Import):
            result.update(alias.asname or alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            result.update(alias.asname or alias.name for alias in node.names if alias.name != "*")
    return result


class _NameFrontiers(ast.NodeVisitor):
    """Conservative lexical lookup, independent of imported module execution."""
    def __init__(self, tree: ast.Module, imported_roots: set[str]):
        self.scopes = [_module_bindings(tree) | set(SAFE_BUILTINS)]
        self.imported_roots = imported_roots
        self.frontiers: set[tuple[str, str, int]] = set()

    def frontier(self, code: str, reference: str, node: ast.AST) -> None:
        self.frontiers.add((code, reference, getattr(node, "lineno", 0)))

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load) and not any(node.id in scope for scope in self.scopes):
            self.frontier("unresolved_global_name", node.id, node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        for value in (*node.decorator_list, *node.args.defaults, *[v for v in node.args.kw_defaults if v]):
            self.visit(value)
        for argument in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs):
            if argument.annotation is not None:
                self.visit(argument.annotation)
        if node.returns is not None:
            self.visit(node.returns)
        local = {argument.arg for argument in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)}
        for argument in (node.args.vararg, node.args.kwarg):
            if argument is not None:
                local.add(argument.arg)
                if argument.annotation is not None:
                    self.visit(argument.annotation)
        if getattr(node, "type_params", ()):
            self.frontier("type_parameter_scope_frontier", node.name, node)
        # Scope collection excludes nested scopes and does not execute declarations.
        pending = list(node.body)
        while pending:
            item = pending.pop()
            if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                local.add(item.name)
                continue
            if isinstance(item, ast.Name) and isinstance(item.ctx, ast.Store | ast.Del):
                local.add(item.id)
            if isinstance(item, ast.Import):
                local.update(alias.asname or alias.name.split(".")[0] for alias in item.names)
            if isinstance(item, ast.ImportFrom):
                local.update(alias.asname or alias.name for alias in item.names if alias.name != "*")
            pending.extend(ast.iter_child_nodes(item))
        self.scopes.append(local)
        for item in node.body:
            self.visit(item)
        self.scopes.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.frontier("class_runtime_lookup_frontier", node.name, node)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in DYNAMIC_NAMES:
            self.frontier("dynamic_lookup_or_execution", node.func.id, node)
        if isinstance(node.func, ast.Attribute):
            root = node.func.value
            while isinstance(root, ast.Attribute):
                root = root.value
            if node.func.attr in {"import_module", "__import__"}:
                self.frontier("dynamic_import", node.func.attr, node)
            elif not isinstance(root, ast.Name) or root.id not in self.imported_roots:
                self.frontier("dynamic_attribute_call", node.func.attr, node)
        self.generic_visit(node)

    def visit_Global(self, node: ast.Global) -> None:
        self.frontier("global_rebinding_frontier", ",".join(node.names), node)

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        self.frontier("nonlocal_rebinding_frontier", ",".join(node.names), node)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        self.frontier("lambda_lookup_frontier", "lambda", node)
        self.generic_visit(node)

    def visit_ListComp(self, node: ast.AST) -> None:
        self.frontier("comprehension_scope_frontier", type(node).__name__, node)
        self.generic_visit(node)

    visit_SetComp = visit_ListComp
    visit_DictComp = visit_ListComp
    visit_GeneratorExp = visit_ListComp

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.frontier("exception_binding_scope_frontier", node.name or "except", node)
        self.generic_visit(node)

    def visit_Match(self, node: ast.AST) -> None:
        self.frontier("pattern_binding_scope_frontier", "match", node)
        self.generic_visit(node)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        self.frontier("assignment_expression_scope_frontier", "named_expression", node)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if isinstance(node.ctx, ast.Store | ast.Del):
            self.frontier("attribute_rebinding_frontier", node.attr, node)
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        if isinstance(node.ctx, ast.Store | ast.Del):
            root = node.value
            while isinstance(root, ast.Attribute):
                root = root.value
            if isinstance(root, ast.Name) and root.id in self.imported_roots:
                self.frontier("module_namespace_mutation_frontier", root.id, node)
        self.generic_visit(node)


class _Captured:
    def __init__(self, path: Path, limits: audit.Limits):
        # First replay all existing structural/source checks without fitting.
        self.audit_report = audit.audit_manifest(path, limits)
        self.raw = audit._read_bounded(path, limits.max_json_bytes)
        audit._require(audit._sha(self.raw) == self.audit_report["input_sha256"],
                       "manifest changed during reconstruction")
        self.manifest = audit._load_json(self.raw, limits)
        self.loader = audit._Loader(path.parent, limits)
        self.loader.json_bytes = len(self.raw)
        for row in self.manifest["units"]:
            self.loader.manual_unit(row)
        for row in self.manifest["native_records"]:
            self.loader.native_record(row)
        for row in self.manifest["ancestral_training"]:
            self.loader.history_row(row)
        self.loader.finish_history()
        self.exports = {}
        for row in self.manifest["native_records"]:
            raw = audit._read_bounded(audit._input_file(path.parent, row["file"]), limits.max_json_bytes)
            audit._require(audit._sha(raw) == row["sha256"], "native export changed during reconstruction")
            self.exports[row["version_id"]] = raw


class _Resolver:
    def __init__(self, units: dict[str, audit.Unit], sources: dict[str, bytes], limits: audit.Limits):
        self.units, self.sources, self.limits = units, sources, limits
        self.modules: dict[tuple[str, str], list[str]] = defaultdict(list)
        self.trees = {}
        self.exported_names = {}
        for unit_id, unit in sorted(units.items()):
            module, _ = _module(unit.path)
            self.modules[unit.repository_id, module].append(unit_id)
            tree = ast.parse(sources[unit_id].decode("utf-8"), type_comments=True)
            self.trees[unit_id] = tree
            self.exported_names[unit_id] = _module_bindings(tree)

    def derive(self, unit_id: str) -> dict:
        unit, tree = self.units[unit_id], self.trees[unit_id]
        module, package = _module(unit.path)
        dependencies = set(unit.dependencies)
        imported_roots = set()
        frontiers: set[tuple[str, str, int]] = set()
        observations = []

        def frontier(code: str, reference: str, node: ast.AST) -> None:
            frontiers.add((code, reference, getattr(node, "lineno", 0)))

        def resolve(name: str, node: ast.AST, *, optional: bool = False) -> list[str]:
            candidates = self.modules.get((unit.repository_id, name), [])
            same_revision = [other for other in candidates if self.units[other].revision == unit.revision]
            selected = same_revision or candidates
            if not selected:
                if not optional:
                    frontier("unresolved_import", name, node)
                return []
            identities = {(self.units[other].path, self.units[other].content_sha256) for other in selected}
            if len(identities) > 1:
                frontier("ambiguous_import_revision_or_module", name, node)
            dependencies.update(selected)
            observations.append({"module": name, "resolved_unit_ids": sorted(selected),
                                 "resolution": "same_revision" if same_revision else "captured_equivalent_or_ambiguous_revisions",
                                 "line": getattr(node, "lineno", 0)})
            return selected

        def package_initializers(name: str, node: ast.AST) -> None:
            parts = name.split(".")
            for index in range(1, len(parts)):
                package_name = ".".join(parts[:index])
                candidates = resolve(package_name, node)
                if candidates and any(not self.units[other].path.endswith("/__init__.py") for other in candidates):
                    frontier("package_initializer_frontier", package_name, node)

        top_level = {id(node) for node in tree.body}
        if module:
            package_initializers(module, tree)
        import_count = 0
        for node in ast.walk(tree):
            if not isinstance(node, ast.Import | ast.ImportFrom):
                continue
            import_count += len(node.names)
            audit._require(import_count <= self.limits.max_links, "import reference budget exceeded")
            if id(node) not in top_level:
                frontier("conditional_or_local_import_frontier", "import", node)
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_roots.add(alias.asname or alias.name.split(".")[0])
                    package_initializers(alias.name, node)
                    resolve(alias.name, node)
            else:
                base = node.module or ""
                if node.level:
                    parts = package.split(".") if package else []
                    if node.level > len(parts):
                        frontier("relative_import_beyond_supplied_package", "." * node.level + base, node)
                        continue
                    prefix = parts[:len(parts) - node.level + 1]
                    base = ".".join([*prefix, *([base] if base else [])])
                if not base:
                    frontier("relative_import_package_unresolved", "from", node)
                    continue
                package_initializers(base, node)
                base_candidates = resolve(base, node)
                for alias in node.names:
                    if alias.name == "*":
                        frontier("wildcard_import_frontier", base, node)
                        continue
                    imported_roots.add(alias.asname or alias.name)
                    submodule = base + "." + alias.name
                    submodule_candidates = resolve(submodule, node, optional=True)
                    if not submodule_candidates and base_candidates:
                        if not all(alias.name in self.exported_names[other] for other in base_candidates):
                            frontier("imported_symbol_unresolved", submodule, node)
                    if base in {"importlib", "builtins"} and alias.name in {"import_module", "__import__"}:
                        frontier("dynamic_import_alias", alias.asname or alias.name, node)
        visitor = _NameFrontiers(tree, imported_roots)
        visitor.visit(tree)
        frontiers.update(visitor.frontiers)
        if not module:
            frontiers.add(("root_package_identity_unresolved", unit.path, 0))
        for reference in dependencies:
            if reference not in self.units:
                frontiers.add(("unresolved_declared_dependency", reference, 0))
        dependencies.discard(unit_id)
        audit._require(len(dependencies) <= self.limits.max_links, "derived dependency link budget exceeded")
        return {
            "unit_id": unit_id, "module": module, "package": package,
            "dependencies": sorted(dependencies), "static_source_scope_resolved": not frontiers,
            "frontiers": [{"code": code, "reference": reference, "line": line}
                          for code, reference, line in sorted(frontiers)],
            "imports": sorted(observations, key=lambda row: (row["line"], row["module"], row["resolved_unit_ids"])),
        }


def _write_bytes(path: Path, raw: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(raw)


def export_metadata(manifest_path: str | Path, output: str | Path, *, supplement_paths: tuple[Path, ...] = (),
                    accept_supplied_scope: bool = False, limits: audit.Limits = audit.DEFAULT_LIMITS) -> dict:
    """Emit a candidate while recording observed scope and every caller claim."""
    audit._bool(accept_supplied_scope, "accept_supplied_scope")
    paths = [Path(manifest_path), *map(Path, supplement_paths)]
    audit._require(len(paths) <= limits.max_native_records, "supplement input budget exceeded")
    captures = [_Captured(path, limits) for path in paths]
    audit._require(sum(capture.loader.json_bytes for capture in captures) <= limits.max_total_json_bytes,
                   "aggregate JSON byte budget exceeded")
    units, sources, exports, original_native, histories = {}, {}, {}, {}, {}
    input_inventory = []
    for path, captured in zip(paths, captures, strict=True):
        input_inventory.append({"sha256": audit._sha(captured.raw), "file": path.as_posix()})
        for unit_id, unit in captured.loader.units.items():
            if unit.origin == "ancestral_training":
                continue
            audit._require(unit_id not in units, "duplicate unit ID across supplied manifests")
            units[unit_id] = unit
            sources[unit_id] = captured.loader.sources[unit.identity()]
        for row in captured.manifest["native_records"]:
            version = row["version_id"]
            audit._require(version not in exports, "duplicate native version across supplied manifests")
            exports[version] = captured.exports[version]
            original_native[version] = row
        for row in captured.manifest["ancestral_training"]:
            histories[audit._sha(audit._canonical(row))] = row
    audit._require(len(units) <= limits.max_units, "aggregate unit budget exceeded")
    audit._require(len(exports) <= limits.max_native_records, "aggregate native record budget exceeded")
    audit._require(sum(len(raw) for raw in sources.values()) <= limits.max_total_source_bytes,
                   "aggregate source byte budget exceeded")
    resolver = _Resolver(units, sources, limits)
    derived = {unit_id: resolver.derive(unit_id) for unit_id in sorted(units)}
    observed_paths: dict[tuple[str, str], list[str]] = defaultdict(list)
    for unit_id, unit in sorted(units.items()):
        observed_paths[unit.repository_id, unit.path].append(unit_id)
    revision_links = []
    for group in observed_paths.values():
        anchor = group[0]
        for unit_id in group[1:]:
            if (units[unit_id].revision, units[unit_id].content_sha256) != (units[anchor].revision, units[anchor].content_sha256):
                derived[unit_id]["observed_related_revisions"] = [anchor]
                revision_links.append({"from": unit_id, "to": anchor,
                                       "basis": "same_repository_path_across_captured_revisions",
                                       "directed_ancestry_asserted": False})
    parents = {version: parent for capture in captures for version, parent in capture.loader.parents.items()}
    source_identities = {unit.identity() for unit in units.values()}
    observed_history = {identity for capture in captures for identity in capture.loader.history}
    unavailable_lineage = (any(parent is not None and parent not in parents for parent in parents.values())
                           or bool(observed_history - source_identities))
    candidate = {"schema": audit.INPUT_SCHEMA, "units": [], "native_records": [],
                 "ancestral_training": sorted(histories.values(), key=audit._canonical),
                 "ancestry_complete": all(capture.manifest["ancestry_complete"] for capture in captures)}
    metadata = {}
    for unit_id, unit in sorted(units.items()):
        item = derived[unit_id]
        item["source_identity"] = {"repository_id": unit.repository_id, "path": unit.path,
                                   "revision": unit.revision, "content_sha256": unit.content_sha256,
                                   "normalized_ast_sha256": unit.normalized_ast_sha256, "role": unit.role,
                                   "origin": unit.origin}
        revision_refs = set(unit.related_revisions) | set(item.get("observed_related_revisions", []))
        missing_revisions = sorted(ref for ref in revision_refs if ref not in units)
        item["unresolved_declared_revisions"] = missing_revisions
        dependency_claim = (unit.dependencies_complete or accept_supplied_scope) and item["static_source_scope_resolved"]
        revision_claim = ((unit.revision_relations_complete or accept_supplied_scope)
                          and not missing_revisions and not unavailable_lineage)
        extra = {"dependencies": item["dependencies"], "dependencies_complete": dependency_claim,
                 "related_revisions": sorted(revision_refs), "revision_relations_complete": revision_claim}
        metadata[unit_id] = extra
        item["candidate_claims"] = {"dependencies_complete": dependency_claim,
                                    "revision_relations_complete": revision_claim,
                                    "claim_origin": "explicit_supplied_scope_opt_in" if accept_supplied_scope
                                    else "retained_caller_claims_frontier_checked"}
        if not unit_id.startswith("native/"):
            candidate["units"].append({"id": unit_id, "role": unit.role, "repository_id": unit.repository_id,
                                       "path": unit.path, "revision": unit.revision,
                                       "content_sha256": unit.content_sha256,
                                       "source": {"bytes_hex": sources[unit_id].hex()}, **extra})
    audit._require(sum(len(row["dependencies"]) + len(row["related_revisions"]) for row in metadata.values())
                   <= limits.max_links, "aggregate derived link budget exceeded")
    for version in sorted(exports):
        row = original_native[version]
        candidate["native_records"].append({"version_id": version, "file": f"native_exports/{row['sha256']}.json",
            "sha256": row["sha256"], "unit_metadata": {unit_id: metadata[unit_id] for unit_id in sorted(units)
                                                        if unit_id.startswith(f"native/{version}/")}})
    output = Path(output)
    try:
        output.mkdir(mode=0o700, parents=False, exist_ok=False)
        if exports:
            (output / "native_exports").mkdir(mode=0o700)
        for version, raw in sorted(exports.items()):
            destination = output / "native_exports" / (original_native[version]["sha256"] + ".json")
            if destination.exists():
                audit._require(audit._read_bounded(destination, limits.max_json_bytes) == raw,
                               "conflicting native export file identity")
            else:
                _write_bytes(destination, raw)
        audit.write_private_report(output / "candidate_manifest.json", candidate)
        candidate_report = audit.audit_manifest(output / "candidate_manifest.json", limits)
        audit.write_private_report(output / "candidate_audit_report.json", candidate_report)
        native_bindings = []
        native_heads = []
        for version, raw in sorted(exports.items()):
            value = audit._load_json(raw, limits)
            provenance = value if value.get("schema") == audit.NATIVE_LINEAGE_SCHEMA else value["report"]["codebase_provenance"]
            native_heads.append({"version_id": version, "head": provenance["head"],
                                 "head_sha256": audit._sha(audit._canonical(provenance["head"])),
                                 "file_sha256": original_native[version]["sha256"]})
            for field in ("training_targets", "tuning_targets", "canary_targets", "replay_targets"):
                for index, target in enumerate(provenance[field]):
                    binding = target["validation"][0]["details"]["source_binding"]
                    native_bindings.append({"unit_id": f"native/{version}/{field}/{index}",
                                            "head_sha256": audit._sha(audit._canonical(binding["head"])),
                                            "source_digest": target["source_digest"],
                                            "content_sha256": binding["content_sha256"],
                                            "source_revision": binding["source_revision"]})
        clones = defaultdict(list)
        for unit_id, unit in sorted(units.items()):
            clones[unit.normalized_ast_sha256].append(unit_id)
        report = {
            "schema": REPORT_SCHEMA, "candidate_audit_status": candidate_report["status"],
            "candidate_complete_for_declared_scope": candidate_report["complete_for_declared_scope"],
            "candidate_manifest_sha256": candidate_report["input_sha256"],
            "source_scope": "explicit captured files/revisions; source-derived static imports and declared references",
            "whole_repository_coverage": False, "unseen_rename_ancestry_verified": False,
            "accept_supplied_scope_caller_claim": accept_supplied_scope,
            "native_replay_performed": False, "native_registry_receipts_verified": False,
            "training_executed": False, "promotion_decisions_made": False,
            "final_sources_used_for_fitting": False, "proof_authority": False,
            "input_manifests": input_inventory, "source_unit_count": len(units),
            "unique_repository_path_count": len(observed_paths),
            "native_unique_repository_path_count": len({(unit.repository_id, unit.path)
                                                         for unit_id, unit in units.items()
                                                         if unit_id.startswith("native/")}),
            "supplemental_final_path_count": len({(unit.repository_id, unit.path)
                                                   for unit_id, unit in units.items()
                                                   if not unit_id.startswith("native/") and unit.role == "final"}),
            "unique_source_revision_count": len({(u.repository_id, u.path, u.revision, u.content_sha256)
                                                 for u in units.values()}),
            "source_metadata": [derived[unit_id] for unit_id in sorted(derived)],
            "observed_revision_links": revision_links,
            "native_exports": candidate_report["native_exports"],
            "native_heads": native_heads, "native_target_bindings": native_bindings,
            "observed_ast_clone_groups": [{"normalized_ast_sha256": digest, "unit_ids": group}
                                          for digest, group in sorted(clones.items()) if len(group) > 1],
            "candidate_issues": candidate_report["issues"], "candidate_leaks": candidate_report["leaks"],
            "clone_normalization": candidate_report["normalization"],
            "python_ast_version": candidate_report["python_ast_version"],
        }
        audit.write_private_report(output / "reconstruction_report.json", report)
    except OSError as exc:
        raise audit.AuditInputError("new private output directory with existing parent required") from exc
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--supplement", action="append", default=[], type=Path,
                        help="additional closed source audit manifest; roles and IDs are retained")
    parser.add_argument("--output", required=True, type=Path, help="fresh private directory with existing parent")
    parser.add_argument("--accept-supplied-scope", action="store_true",
                        help="record explicit caller closure claim restricted to supplied scope; frontiers still block it")
    arguments = parser.parse_args(argv)
    try:
        report = export_metadata(arguments.manifest, arguments.output,
                                 supplement_paths=tuple(arguments.supplement),
                                 accept_supplied_scope=arguments.accept_supplied_scope)
    except audit.AuditInputError as exc:
        print(f"invalid input: {exc}", file=sys.stderr)
        return 3
    print(f"candidate created: {report['candidate_audit_status']}; "
          f"{len(report['candidate_issues'])} issues; whole repository coverage: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
