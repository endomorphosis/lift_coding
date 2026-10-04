"""Bounded source-only successor syntax and historical content exposure diagnostics."""
from __future__ import annotations

import argparse
import ast
import base64
import copy
import hashlib
import json
import math
import os
import stat
import sys
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

from codebase_ir_final_targets import derive_source

INPUT_SCHEMA = "codebase-ir-source-delta-analysis-input@1"
REPORT_SCHEMA = "codebase-ir-source-delta-analysis@1"
ROLES = ("review", "source_result", "source_audit", "ignored_result", "failed_ignore_result",
         "historical_cohort_report", "checkpoint_result")
ANCHORS = dict(zip(ROLES, (
    "fb7664d68f863de982e12361014296cdaf668ea2bc22fa20d16a313e3452d040",
    "207021f2c0cee2c37199c1e5876ea91cc1ada94a3ddad0560272f7c175ba3900",
    "558e93a6a01d6760b54ad83d45aeb132a3a6f6be5d71f762e7bdc53629bef411",
    "028c380286c3ed12f5208bdc061294d9dd25e6135f35f0e61746d39e34fcea83",
    "027d7edc9e4f4f6f9bf8e88d592a629b264a9cb5234bcf2c700e4d7e03876f69",
    "2fefb318e63fc5aa0098ae382a164333fc438ee692f29e2d32eb9dad0729430d",
    "1d528b5e1027da410d709f3fa26d0f3ffaa3c59f188cdaca73578b5b24f1cc3b",
), strict=True))
TRUE_FLAGS = ("source_delta_accounting_produced", "complete_union_accounting_available",
              "source_bytes_comparisons_rederived", "source_syntax_comparisons_rederived",
              "captured_ast_bindings_rederived", "clone_and_template_impact_rederived",
              "syntactic_dependency_frontier_rederived", "historical_content_exposure_accounted",
              "original_failed_observation_preserved", "input_files_unchanged",
              "unknown_pretraining_exposure", "current_exposure_unknown")
FALSE_FLAGS = ("native_execution_performed", "training_executed", "current_authority_claimed",
               "owner_sources_imported", "git_executable_invoked", "owner_database_opened", "profile_keys_read",
               "model_predictions_evaluated", "optimizer_state_replayed", "source_execution_attested",
               "scan_execution_attested", "source_semantics_verified", "source_runtime_truth_verified",
               "physical_absence_verified", "semantic_rename_verified", "numerical_reuse_authorized",
               "model_advanced", "candidate_model_qualified", "producer_authentication_verified",
               "numerical_provenance_verified", "heldout_independence_verified",
               "complete_pretraining_exposure_verified", "current_training_roles_transferred",
               "historical_exposure_roles_transferred", "full_ancestry_verified",
               "current_model_eligibility_qualified", "proof_reuse_eligibility_qualified",
               "learned_weight_dependence_verified", "learned_quality_improvement_verified",
               "universal_source_label_equivalence_verified", "model_selection_performed",
               "promotion_performed", "final_population_modified")
MiB = 1024 * 1024
MAX_ORIGINALS, MAX_FILES, MAX_BYTES = 1024, 2048, 64 * MiB
MEMBER_FIELDS = {"ast_cid", "entry_cid", "opaque_reason", "parse_status", "path", "raw_path_hex",
                 "source_cid", "source_key", "source_size_bytes"}
AST_FIELDS = {"calls", "diagnostics", "effects", "frontend", "imports", "module", "provenance",
              "references", "schema", "scopes", "symbols", "unsupported"}
HEAD_FIELDS = {"schema", "repository_id", "generation", "ast_revision_id", "snapshot_cid", "manifest_cid", "receipt_cid"}
DELTA_FIELDS = {"schema", "authority", "capture_policy", "coverage", "current_head", "current_membership_cid",
                "current_publication_receipt", "implementation", "ledger", "limits", "model_advanced",
                "numerical_reuse", "optimized", "physical_absence_verified", "previous_head",
                "previous_membership_cid", "previous_publication_receipt", "removal_scope"}
AUTHORITY_FIELDS = {"admission_authority", "authoritative_cache_eligible", "behavioral_satisfaction", "completion_authority",
                    "decoded_formulas_generated", "execution_authority", "mutation_authority", "proof_authority",
                    "repository_code_executed", "runtime_behavior_verified", "scan_execution_attested",
                    "source_execution_attested", "source_semantics_verified", "training_executed"}


class Refused(ValueError):
    """Selected source/export bytes do not satisfy this closed diagnostic profile."""


def require(condition, reason):
    if not condition:
        raise Refused(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def cid(raw, structured=False):
    return "b" + base64.b32encode((b"\x01\xa9\x02\x12\x20" if structured else b"\x01\x55\x12\x20")
                                 + hashlib.sha256(raw).digest()).decode("ascii").lower().rstrip("=")


def object_cid(value):
    return cid(wire(value), True)


def report_bytes(value):
    chunks, size = [], 0
    for chunk in json.JSONEncoder(sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False).iterencode(value):
        raw = chunk.encode("utf-8")
        size += len(raw)
        require(size + 1 <= 4 * MiB, "main report allocation bound")
        chunks.append(raw)
    return b"".join(chunks) + b"\n"


def closed(value, fields, reason):
    require(type(value) is dict and set(value) == set(fields), reason)


def document(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, "duplicate JSON field")
            value[key] = item
        return value

    def integer(token):
        require(len(token) <= 20, "JSON integer allocation bound")
        value = int(token)
        require(abs(value) <= 2**63 - 1, "JSON integer bound")
        return value

    def floating(token):
        require(len(token) <= 64 and math.isfinite(float(token)), "finite JSON number required")
        return float(token)

    def bad(_):
        raise Refused("nonfinite JSON constant")

    value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_int=integer,
                       parse_float=floating, parse_constant=bad)
    pending, nodes = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        require(depth <= 64 and nodes <= 1000000, "JSON structure budget")
        if type(item) is dict:
            pending.extend((x, depth + 1) for x in item)
            pending.extend((x, depth + 1) for x in item.values())
        elif type(item) is list:
            pending.extend((x, depth + 1) for x in item)
        elif type(item) is str:
            item.encode("utf-8")
    require(type(value) is dict, "JSON object required")
    return value


def descriptor(value):
    closed(value, {"path", "sha256", "size_bytes"}, "closed raw descriptor required")
    require(type(value["path"]) is str and type(value["sha256"]) is str
            and len(value["sha256"]) == 64 and all(x in "0123456789abcdef" for x in value["sha256"])
            and type(value["size_bytes"]) is int and 0 <= value["size_bytes"], "typed exact raw descriptor required")
    return Path(value["path"])


class Reads:
    def __init__(self):
        self.plan, self.raw, self.inodes = {}, {}, {}

    def reserve(self, path, pin, cap):
        path = Path(path)
        require(path.is_absolute() and path.resolve(strict=True) == path, "canonical selected file required")
        require(type(pin) is dict and set(pin) == {"sha256", "size_bytes"}
                and type(pin["size_bytes"]) is int and 0 <= pin["size_bytes"] <= cap, "declared preallocation body bound")
        require(type(pin["sha256"]) is str and len(pin["sha256"]) == 64
                and all(x in "0123456789abcdef" for x in pin["sha256"]), "raw SHA required")
        if path in self.plan:
            require(self.plan[path] == pin, "conflicting selected descriptor")
            return
        require(len(self.plan) < MAX_ORIGINALS and 2 * (sum(x["size_bytes"] for x in self.plan.values())
                + pin["size_bytes"]) <= MAX_BYTES, "complete original and copy reservation budget")
        info = path.stat(follow_symlinks=False)
        require(stat.S_ISREG(info.st_mode) and info.st_size == pin["size_bytes"], "regular exact selected size")
        inode = (info.st_dev, info.st_ino)
        require(inode not in self.inodes, "hardlink selected alias")
        self.inodes[inode], self.plan[path] = path, pin

    @staticmethod
    def bounded(path, cap):
        require(path.is_absolute() and path.resolve(strict=True) == path, "canonical bounded read required")
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            before = os.fstat(fd)
            require(stat.S_ISREG(before.st_mode) and before.st_size <= cap, "bounded regular descriptor required")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                raw = stream.read(cap + 1)
            after, final = os.fstat(fd), path.stat(follow_symlinks=False)
            def identity(value):
                return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns
            require(len(raw) == before.st_size and identity(before) == identity(after) == identity(final), "selected descriptor drift")
            return raw
        finally:
            os.close(fd)

    def take(self, path):
        require(path in self.plan, "unreserved read refused")
        if path not in self.raw:
            pin = self.plan[path]
            raw = self.bounded(path, pin["size_bytes"])
            require(sha(raw) == pin["sha256"], "selected raw SHA mismatch")
            self.raw[path] = raw
        return self.raw[path]

    def stable(self):
        for path, raw in self.raw.items():
            require(self.bounded(path, len(raw)) == raw, "late original selected body drift")


def child_pin(root, relative, pins, reads, cap):
    require(type(relative) is str and not PurePosixPath(relative).is_absolute()
            and ".." not in PurePosixPath(relative).parts and relative in pins, "explicit declared child selector required")
    value = pins[relative]
    require(type(value) is dict and type(value.get("bytes")) is int, "declared child byte count required")
    path = root / relative
    reads.reserve(path, {"sha256": value["sha256"], "size_bytes": value["bytes"]}, cap)
    return path


def head(value):
    closed(value, HEAD_FIELDS, "closed source head")
    require(value["schema"] == "codebase-head@1" and type(value["generation"]) is int
            and value["generation"] > 0 and value["ast_revision_id"] == "rev:" + value["repository_id"]
            + ":snapshot:" + value["snapshot_cid"], "source head identity")


def _member(entry, unit):
    return {"ast_cid": unit["ast_cid"], "entry_cid": entry["entry_cid"], "opaque_reason": entry["opaque_reason"],
            "parse_status": unit["parse_status"], "path": entry["path"], "raw_path_hex": entry["raw_path_hex"],
            "source_cid": entry["source_cid"], "source_key": "raw:" + entry["raw_path_hex"], "source_size_bytes": entry["size_bytes"]}


def capture(manifest, expected_head, policy):
    closed(manifest, {"schema", "ast_revision_id", "authority", "coverage", "semantic_state", "snapshot", "units"}, "closed source manifest")
    require(manifest["schema"] == "codebase-ir-structural-manifest@1" and manifest["authority"] == "structural_only"
            and manifest["ast_revision_id"] == expected_head["ast_revision_id"]
            and object_cid(manifest) == expected_head["manifest_cid"], "manifest head binding")
    snapshot = manifest["snapshot"]
    closed(snapshot, {"entries", "exclusions", "git_commit", "git_tree", "max_entries", "max_file_bytes", "mode", "repository_id", "schema", "snapshot_cid"}, "closed captured snapshot")
    require(snapshot["schema"] == "ipfs-datasets.software-contracts.semantic-repository-snapshot@4", "unsupported captured snapshot schema")
    require(snapshot["repository_id"] == expected_head["repository_id"]
            and snapshot["snapshot_cid"] == expected_head["snapshot_cid"], "snapshot source head binding")
    require({k: snapshot[k] for k in policy} == policy and type(policy["max_entries"]) is int
            and 0 < policy["max_entries"] <= 512 and type(policy["max_file_bytes"]) is int
            and 0 < policy["max_file_bytes"] <= 65536, "capture policy and bound")
    seed = dict(snapshot)
    seed.pop("snapshot_cid")
    require(object_cid(seed) == expected_head["snapshot_cid"], "snapshot CID preimage")
    entries, units = snapshot["entries"], manifest["units"]
    require(type(entries) is list and type(units) is list and len(entries) == len(units) <= min(512, policy["max_entries"]), "whole capture population bound")
    unit_map = {x["source_key"]: x for x in units}
    require(len(unit_map) == len(units), "duplicate manifest unit")
    result = {}
    for entry in entries:
        closed(entry, {"acquisition", "disposition", "entry_cid", "git_blob_oid", "head_blob_oid", "index_blob_oids", "kind", "opaque_reason", "path", "raw_path_hex", "schema", "size_bytes", "source_cid"}, "closed captured entry")
        require(entry["schema"] == "ipfs-datasets.software-contracts.semantic-snapshot-entry@3", "unsupported captured entry schema")
        require(type(entry["size_bytes"]) is int and 0 <= entry["size_bytes"] <= 2**63 - 1, "typed captured source size")
        seed = dict(entry)
        entry_cid = seed.pop("entry_cid")
        require(entry_cid == object_cid(seed), "entry CID preimage")
        raw_path = bytes.fromhex(entry["raw_path_hex"])
        require(entry["path"] == raw_path.decode("utf-8", errors="surrogateescape")
                and len(raw_path) <= 1024 and b"\0" not in raw_path, "exact raw path binding")
        key = "raw:" + entry["raw_path_hex"]
        require(key not in result and key in unit_map, "exact source key population")
        unit = unit_map[key]
        closed(unit, {"schema", "source_key", "entry_cid", "ast_cid", "parse_status"}, "closed structural unit")
        require(unit["schema"] == "codebase-ir-structural-unit@1" and unit["entry_cid"] == entry_cid, "unit entry binding")
        result[key] = {"entry": entry, "member": _member(entry, unit)}
    require(set(result) == set(unit_map), "complete unit entry identity")
    return dict(sorted(result.items()))


def span(value, raw):
    closed(value, {"start_byte", "end_byte", "start_line", "end_line", "start_column", "end_column"}, "closed source span")
    require(all(type(x) is int for x in value.values()), "typed span offsets")
    start, end = value["start_byte"], value["end_byte"]
    require(0 <= start <= end <= len(raw), "source span bounds")
    lines = raw.split(b"\n")
    offsets, total = [], 0
    for line in lines:
        offsets.append(total)
        total += len(line) + 1
    for side, position in (("start", start), ("end", end)):
        line, column = value[side + "_line"], value[side + "_column"]
        require(1 <= line <= len(lines) and 0 <= column <= len(lines[line - 1])
                and offsets[line - 1] + column == position, "source span coordinate preimage")
    return start, end


def syntax(member, raw, captured, source_head):
    base = {"source_sha256": sha(raw) if raw is not None else None, "syntax_disposition": "unavailable",
            "normalized_ast_sha256": None, "template_ast_sha256": None, "label": None,
            "label_binding": None, "label_reason": "source syntax unavailable", "dependency_paths": [], "reference_span_count": 0}
    if raw is None:
        require(member["parse_status"] == "opaque" and captured is None, "missing source is not opaque")
        return base
    require(len(raw) == member["source_size_bytes"] and len(raw) <= 65536, "raw source length binding")
    if captured is None:
        require(member["parse_status"] == "unindexed", "missing AST is not unindexed")
        return dict(base, syntax_disposition="unindexed")
    closed(captured, AST_FIELDS, "closed captured AST")
    require(captured["schema"] == "ipfs-datasets.software-contracts.ast-ir@1.0.0", "unsupported captured AST schema")
    provenance = captured["provenance"]
    require(provenance["repository_id"] == source_head["repository_id"]
            and provenance["repository_tree_cid"] == source_head["snapshot_cid"]
            and provenance["revision"] == "snapshot:" + source_head["snapshot_cid"]
            and provenance["path"] == member["path"] and provenance["source_cid"] == member["source_cid"], "captured AST source provenance")
    require(captured["module"]["module_id"] == "module:" + member["source_cid"]
            and span(captured["module"]["span"], raw) == (0, len(raw)), "module source binding")
    pending, nodes, spans = [captured], 0, 0
    while pending:
        item = pending.pop()
        nodes += 1
        require(nodes <= 16384, "captured AST walk budget")
        if type(item) is dict:
            if "span" in item:
                span(item["span"], raw)
                spans += 1
                require(spans <= 4096, "captured AST span budget")
            pending.extend(v for k, v in item.items() if k != "span")
        elif type(item) is list:
            pending.extend(item)
    try:
        tree = ast.parse(raw.decode("utf-8"), type_comments=True)
    except (SyntaxError, UnicodeDecodeError):
        require(member["parse_status"] == "failed" and bool(captured["diagnostics"])
                and bool(captured["unsupported"]) and captured["references"] == captured["symbols"] == [], "captured failed parse disposition")
        return dict(base, syntax_disposition="parse_failed")
    require(member["parse_status"] == "ok", "parsed source disposition")
    nodes = []
    for node in ast.walk(tree):
        require(len(nodes) < 4096, "source AST allocation budget")
        nodes.append(node)
    offsets, total = [], 0
    for line in raw.split(b"\n"):
        offsets.append(total)
        total += len(line) + 1

    def extent(node):
        return offsets[node.lineno - 1] + node.col_offset, offsets[node.end_lineno - 1] + node.end_col_offset

    type_names = set()
    for node in nodes:
        annotation = node.annotation if isinstance(node, ast.arg | ast.AnnAssign) else node.returns if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) else None
        if annotation is not None:
            type_names.update(id(x) for x in ast.walk(annotation) if isinstance(x, ast.Name))

    def context(node):
        return "type" if id(node) in type_names else "write" if isinstance(node.ctx, ast.Store) else "read"

    references = sorted([(n.id, context(n), *extent(n)) for n in nodes if isinstance(n, ast.Name)]
                        + [(n.func.id, "call", *extent(n.func)) for n in nodes if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)])
    symbols = sorted([("function", n.name, *extent(n)) for n in nodes if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)]
                     + [("parameter", n.arg, *extent(n)) for n in nodes if isinstance(n, ast.arg)])
    require(sorted((r["name"], r["context"], *span(r["span"], raw)) for r in captured["references"]) == references, "independent reference population")
    require(sorted((r["kind"], r["name"], *span(r["span"], raw)) for r in captured["symbols"]) == symbols, "independent symbol population")
    scopes = {x["scope_id"] for x in captured["scopes"]}
    require(len(scopes) == len(captured["scopes"]) and len({x["symbol_id"] for x in captured["symbols"]}) == len(captured["symbols"])
            and all(x["scope_id"] in scopes for x in captured["references"] + captured["symbols"]), "captured reference scope closure")
    for node in nodes:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            symbol = next(x for x in captured["symbols"] if x["kind"] == "function" and x["name"] == node.name and span(x["span"], raw) == extent(node))
            signature = symbol["signature"]
            if not node.args.posonlyargs and not node.args.kwonlyargs and not node.args.vararg and not node.args.kwarg and not node.args.defaults:
                parameters = [{"name": arg.arg, "annotation": ast.unparse(arg.annotation) if arg.annotation is not None else None,
                               "position": index, "kind": "positional_or_named", "default_kind": "none"} for index, arg in enumerate(node.args.args)]
                require(wire(signature["parameters"]) == wire(parameters) and signature["return_annotation"] == (ast.unparse(node.returns) if node.returns is not None else None), "independent signature annotations")
    dependencies = sorted({n.module.split(".")[0] + ".py" for n in nodes if isinstance(n, ast.ImportFrom) and n.module}
                          | {a.name.split(".")[0] + ".py" for n in nodes if isinstance(n, ast.Import) for a in n.names})
    template = copy.deepcopy(tree)
    for node in ast.walk(template):
        if isinstance(node, ast.Constant):
            node.value = "constant_type:" + type(node.value).__name__
    try:
        binding, label, reason = derive_source(raw)
    except (ValueError, SyntaxError, RecursionError) as exc:
        binding, label, reason = None, None, str(exc)
    return dict(base, syntax_disposition="parsed", normalized_ast_sha256=sha(ast.dump(tree, include_attributes=False).encode()),
                template_ast_sha256=sha(ast.dump(template, include_attributes=False).encode()), label=label,
                label_binding=binding, label_reason=reason, dependency_paths=dependencies, reference_span_count=len(references))


def compare(old, new, field):
    if old is None or new is None or old[field] is None or new[field] is None:
        return "unavailable"
    return "equal" if old[field] == new[field] else "different"


def groups(rows, field):
    result = defaultdict(list)
    for key, row in rows.items():
        if row[field] is not None:
            result[row[field]].append(key)
    return [{"sha256": k, "source_keys": sorted(v)} for k, v in sorted(result.items()) if len(v) > 1]


def derive_delta(envelope, previous_manifest, current_manifest, raw_sources, raw_asts):
    closed(envelope, {"artifact_cid", "value"}, "closed delta envelope")
    value = envelope["value"]
    closed(value, DELTA_FIELDS, "closed source delta")
    closed(value["authority"], AUTHORITY_FIELDS, "closed native authority vocabulary")
    require(value["schema"] == "codebase-inventory-source-delta@1" and object_cid(value) == envelope["artifact_cid"], "source delta CID preimage")
    require(all(x is False for x in value["authority"].values()) and len(value["authority"]) == 14
            and value["numerical_reuse"] is value["model_advanced"] is value["physical_absence_verified"] is False
            and type(value["optimized"]) is bool, "source delta authority ceiling")
    old_head, new_head = value["previous_head"], value["current_head"]
    head(old_head)
    head(new_head)
    require(new_head["repository_id"] == old_head["repository_id"] and new_head["generation"] == old_head["generation"] + 1, "successive same repository heads")
    for which, source_head in (("previous", old_head), ("current", new_head)):
        receipt = value[which + "_publication_receipt"]
        require(object_cid(receipt) == source_head["receipt_cid"]
                and all(receipt[k] == source_head[k] for k in ("repository_id", "generation", "ast_revision_id", "snapshot_cid", "manifest_cid")), "publication receipt head binding")
    require(value["current_publication_receipt"]["previous_head"] == old_head, "exact predecessor publication")
    captures = {"previous": capture(previous_manifest, old_head, value["capture_policy"]),
                "current": capture(current_manifest, new_head, value["capture_policy"])}
    rows, syntaxes, counters = [], {"previous": {}, "current": {}}, {k: Counter() for k in ("entry", "bytes", "ast", "syntax", "label")}
    source_keys = sorted(set(captures["previous"]) | set(captures["current"]))
    require(len(source_keys) <= 1024, "source union allocation bound")
    for which in captures:
        members = [x["member"] for x in captures[which].values()]
        require(object_cid(members) == value[which + "_membership_cid"], "complete member CID preimage")
        for key, item in captures[which].items():
            member = item["member"]
            raw = raw_sources.get(member["source_cid"])
            captured = raw_asts.get(member["ast_cid"])
            if member["source_cid"] is not None and member["parse_status"] != "opaque":
                require(raw is not None and cid(raw) == member["source_cid"], "complete raw source CID closure")
            if member["ast_cid"] is not None:
                require(captured is not None and object_cid(captured) == member["ast_cid"], "complete AST CID closure")
            syntaxes[which][key] = syntax(member, raw, captured, old_head if which == "previous" else new_head)
    for key in source_keys:
        old, new = captures["previous"].get(key), captures["current"].get(key)
        kind = "added" if old is None else "removed" if new is None else "retained" if old["entry"] == new["entry"] else "changed"
        bytes_comparison = "unavailable"
        ast_comparison = "unavailable"
        if old is not None and new is not None:
            a, b = old["member"], new["member"]
            if a["parse_status"] != "opaque" and b["parse_status"] != "opaque" and a["source_cid"] in raw_sources and b["source_cid"] in raw_sources:
                bytes_comparison = "equal" if raw_sources[a["source_cid"]] == raw_sources[b["source_cid"]] else "different"
            if a["ast_cid"] is not None and b["ast_cid"] is not None:
                ast_comparison = "equal" if a["ast_cid"] == b["ast_cid"] else "different"
        row = {"source_key": key, "classification": kind, "previous": old, "current": new,
               "source_bytes_comparison": bytes_comparison, "ast_identity_comparison": ast_comparison}
        rows.append(row)
        for counter, result in (("entry", kind), ("bytes", bytes_comparison), ("ast", ast_comparison),
                                ("syntax", compare(syntaxes["previous"].get(key), syntaxes["current"].get(key), "normalized_ast_sha256")),
                                ("label", compare(syntaxes["previous"].get(key), syntaxes["current"].get(key), "label"))):
            counters[counter][result] += 1
    require(wire(value["ledger"]) == wire(rows), "independent complete source ledger")
    coverage = {"previous_entries": len(captures["previous"]), "current_entries": len(captures["current"]),
                "union_entries": len(rows), "classifications": {k: counters["entry"][k] for k in ("retained", "changed", "added", "removed")},
                "source_bytes_comparisons": {k: counters["bytes"][k] for k in ("equal", "different", "unavailable")},
                "ast_identity_comparisons": {k: counters["ast"][k] for k in ("equal", "different", "unavailable")}}
    require(wire(value["coverage"]) == wire(coverage), "independent complete coverage")
    changes = {x["source_key"] for x in rows if x["classification"] != "retained"}
    dependencies = []
    for which in captures:
        paths = {x["member"]["path"]: key for key, x in captures[which].items()}
        for key, result in syntaxes[which].items():
            for path in result["dependency_paths"]:
                dependencies.append({"side": which, "from_source_key": key, "syntactic_import_path": path,
                                     "local_source_key": paths.get(path), "resolution_qualified": False})
    affected = set(changes)
    for _ in range(len(rows) + 1):
        before = set(affected)
        affected.update(x["from_source_key"] for x in dependencies if x["local_source_key"] in affected)
        if affected == before:
            break
    cross_path = []
    for old_key, a in syntaxes["previous"].items():
        if a["source_sha256"] is None:
            continue
        for new_key, b in syntaxes["current"].items():
            if old_key != new_key and a["source_sha256"] == b["source_sha256"]:
                cross_path.append({"previous_source_key": old_key, "current_source_key": new_key,
                                   "source_sha256": a["source_sha256"], "rename_inferred": False})
                require(len(cross_path) <= 4096, "cross-path content pair allocation budget")
    return {"previous_head": old_head, "current_head": new_head, "coverage": coverage,
            "rows": [{"source_key": row["source_key"], "entry_transition": row["classification"],
                      "source_bytes_comparison": row["source_bytes_comparison"], "captured_ast_comparison": row["ast_identity_comparison"],
                      "source_syntax_comparison": compare(syntaxes["previous"].get(row["source_key"]), syntaxes["current"].get(row["source_key"]), "normalized_ast_sha256"),
                      "structural_label_comparison": compare(syntaxes["previous"].get(row["source_key"]), syntaxes["current"].get(row["source_key"]), "label"),
                      "previous": syntaxes["previous"].get(row["source_key"]), "current": syntaxes["current"].get(row["source_key"])} for row in rows],
            "comparison_counts": {k: dict(v) for k, v in counters.items()},
            "previous_clones": groups(syntaxes["previous"], "normalized_ast_sha256"), "current_clones": groups(syntaxes["current"], "normalized_ast_sha256"),
            "previous_templates": groups(syntaxes["previous"], "template_ast_sha256"), "current_templates": groups(syntaxes["current"], "template_ast_sha256"),
            "cross_path_content_pairs": cross_path, "syntactic_dependencies": dependencies,
            "potential_dependency_frontier": {"source_change_seed_keys": sorted(changes), "syntactic_reverse_closure_keys": sorted(affected),
                                              "proof_dependencies": "unknown; no proof dependency owner or evidence opened",
                                              "model_dependencies": "unknown; no source-bound model generation selected",
                                              "new_current_head_receipt_required_for_every_previous_context": True}}


def selected_capture(root, pins, reads, reference):
    names = ["previous-manifest.json", "current-manifest.json", "previous-publication-receipt.json", "current-publication-receipt.json", "optimized-source-delta.json"]
    if reference:
        names.append("reference-source-delta.json")
    paths = {name: child_pin(root, name, pins, reads, 4 * MiB if "manifest" in name else MiB) for name in names}
    values = {name: document(reads.take(path)) for name, path in paths.items()}
    envelope = values["optimized-source-delta.json"]
    value = envelope["value"]
    if reference:
        ref = values["reference-source-delta.json"]
        require(ref["artifact_cid"] == object_cid(ref["value"]) and value["optimized"] is True and ref["value"]["optimized"] is False, "optimized reference identities")
        require({k: v for k, v in value.items() if k != "optimized"} == {k: v for k, v in ref["value"].items() if k != "optimized"}, "reference byte-independent full value equivalence")
    for which in ("previous", "current"):
        require(values[which + "-publication-receipt.json"] == value[which + "_publication_receipt"], "independent named publication receipt")
    ids = {"source": set(), "structured": set()}
    for manifest_name in ("previous-manifest.json", "current-manifest.json"):
        manifest = values[manifest_name]
        require(type(manifest["units"]) is list and type(manifest["snapshot"]["entries"]) is list
                and len(manifest["units"]) == len(manifest["snapshot"]["entries"]) <= 512, "selected capture preallocation population bound")
        unit_map = {x["source_key"]: x for x in manifest["units"]}
        for entry in manifest["snapshot"]["entries"]:
            if entry["source_cid"] is not None and entry["opaque_reason"] is None:
                ids["source"].add(entry["source_cid"])
            ast_cid = unit_map["raw:" + entry["raw_path_hex"]]["ast_cid"]
            if ast_cid is not None:
                ids["structured"].add(ast_cid)
    cas_paths = {}
    for kind in ids:
        for identity in sorted(ids[kind]):
            relative = "private/source-artifacts/" + kind + "/" + identity[:4] + "/" + identity
            cas_paths[(kind, identity)] = child_pin(root, relative, pins, reads, 65536 if kind == "source" else 128 * 1024)
    sources, asts = {}, {}
    for (kind, identity), path in cas_paths.items():
        raw = reads.take(path)
        if kind == "source":
            require(cid(raw) == identity, "raw source CAS CID")
            sources[identity] = raw
        else:
            asts[identity] = document(raw)
            require(object_cid(asts[identity]) == identity, "AST CAS CID")
    return derive_delta(envelope, values["previous-manifest.json"], values["current-manifest.json"], sources, asts)


def exposure(main, historical, checkpoint, historical_pin):
    finding = checkpoint["qualification_findings"]["resumed_cohort_audit"]
    require(checkpoint["tests_passed"] is True and finding["status"] == historical["status"] == "passed"
            and finding["sha256"] == historical_pin["sha256"], "independent historical report checkpoint binding")
    require(historical["schema"] == "codebase-ir-resumed-cohort-audit@1" and historical["unknown_pretraining_exposure"] is True
            and historical["source_semantics_verified"] is historical["heldout_independence_verified"] is False, "historical exposure scope")
    require(all(historical.get(name) is False for name in ("candidate_model_qualified", "producer_authentication_verified",
            "numerical_provenance_verified", "model_selection_performed", "optimizer_state_replayed",
            "complete_pretraining_exposure_verified")), "historical quality and exposure authority ceiling")
    members = {x["path"]: x for x in historical["members"]}
    require(len(members) == len(historical["members"]) <= 512, "historical member population")
    exposures = defaultdict(list)
    lineages = historical["retained_lineage_selection_ledger"]
    require(type(lineages) is list and len(lineages) <= 8, "historical lineage metadata budget")
    for lineage in lineages:
        selections = {x["path"]: x["role"] for x in lineage["selections"]}
        targets = lineage["target_observations"]
        require(len(targets) <= 32, "historical observation metadata budget")
        for item in targets:
            path, role = item["path"], item["role"]
            require(role in {"train", "tune", "canary", "replay"} and selections[path] == ("train" if role == "replay" else role), "historical selection role binding")
            require(path in members and members[path]["source_sha256"] == item["source_sha256"]
                    and members[path]["source_body_available"] is True, "historical target source binding")
            exposures[item["source_sha256"]].append({"historical_path": path, "declared_role": role,
                                                      "version_id": lineage["version_id"], "current_role_transferred": False})
    matches, counts = [], Counter()
    for row in main["rows"]:
        for side in ("previous", "current"):
            value = row[side]
            if value is not None and value["source_sha256"] in exposures:
                roles = sorted({x["declared_role"] for x in exposures[value["source_sha256"]]})
                counts.update(roles)
                matches.append({"side": side, "source_key": row["source_key"], "source_sha256": value["source_sha256"],
                                "historical_declarations": exposures[value["source_sha256"]], "current_exposure": "unknown"})
    return {"historical_head": historical["captured_source_head"], "historical_report_sha256": historical_pin["sha256"],
            "method": "new exact raw source SHA joined to already sealed historical byte diagnostic; old raw bytes not reopened",
            "ancestry": "unknown; no cross-repository or cross-head ancestry certified", "matches": matches,
            "role_occurrence_counts": dict(counts), "historical_model_or_lineage_envelopes_opened": False,
            "current_exposure": "unknown for every member, including matches and zero matches"}


def population(root, expected):
    require(root.is_absolute() and root.resolve(strict=True) == root and stat.S_ISDIR(root.stat(follow_symlinks=False).st_mode), "canonical output directory required")
    before = root.stat(follow_symlinks=False)
    found = set()
    with os.scandir(root) as entries:
        for entry in entries:
            require(len(found) < len(expected) and entry.name in expected and entry.is_file(follow_symlinks=False)
                    and not entry.is_symlink(), "exact regular bounded output population")
            found.add(entry.name)
    require(found == set(expected), "exact complete output population")
    for name, raw in expected.items():
        require(Reads.bounded(root / name, len(raw)) == raw, "late retained output body drift")
    after = root.stat(follow_symlinks=False)
    require((before.st_dev, before.st_ino) == (after.st_dev, after.st_ino) and root.resolve(strict=True) == root, "late output root alias")
    with os.scandir(root) as entries:
        final = []
        for entry in entries:
            require(len(final) < len(expected) and entry.is_file(follow_symlinks=False) and not entry.is_symlink(), "closing regular population")
            final.append(entry.name)
    require(set(final) == set(expected), "closing exact output population")


def evaluate(manifest_path, output):
    manifest_path, output = Path(manifest_path).absolute(), Path(output).absolute()
    reads = Reads()
    manifest_raw = Reads.bounded(manifest_path, MiB)
    reads.reserve(manifest_path, {"sha256": sha(manifest_raw), "size_bytes": len(manifest_raw)}, MiB)
    reads.take(manifest_path)
    spec = document(manifest_raw)
    closed(spec, {"schema", *ROLES}, "closed source delta analysis input")
    require(spec["schema"] == INPUT_SCHEMA, "source delta input schema")
    for role in ROLES:
        path = descriptor(spec[role])
        require(spec[role]["sha256"] == ANCHORS[role], "fixed original outer anchor " + role)
        reads.reserve(path, {k: spec[role][k] for k in ("sha256", "size_bytes")}, MiB)
    values = {role: document(reads.take(Path(spec[role]["path"]))) for role in ROLES}
    review, source, audit = (values[role] for role in ("review", "source_result", "source_audit"))
    for role, recorded in (("source_result", review["source_native"]["result"]), ("source_audit", review["source_independent_audit"]["report"]),
                           ("ignored_result", review["ignored_file_native"]["result"]), ("failed_ignore_result", review["failed_ignore_attempt"]["result"])):
        require(recorded["sha256"] == spec[role]["sha256"] and recorded["bytes"] == spec[role]["size_bytes"], "independent review child declaration")
    require(source["qualified"] is True and audit["qualified"] is True and audit["errors"] == [], "recorded successful source observations")
    require(review["schema"] == "codebase-source-delta-current-runtime-review@1"
            and source["schema"] == "codebase-source-delta-native-qualification@1"
            and audit["schema"] == "codebase-source-delta-independent-audit@1"
            and values["ignored_result"]["schema"] == values["failed_ignore_result"]["schema"] == "codebase-source-delta-ignore-native-qualification@1"
            and values["checkpoint_result"]["schema"] == "codebase-ir-independent-lanes-run@1", "selected native metadata schemas")
    main_root = Path(audit["namespace"])
    require(Path(spec["source_result"]["path"]) == main_root / "result.json", "exact main result namespace")
    main = selected_capture(main_root, audit["guarded_artifacts"], reads, True)
    require(main["coverage"] == source["coverage"] == audit["source_delta"]["coverage"], "three-way source coverage join")
    require(main["previous_head"] == source["previous_head"] and main["current_head"] == source["current_head"], "recorded source head join")
    ignored_audit, ignored_result = audit["ignored_control"], values["ignored_result"]
    ignored_root = Path(ignored_audit["namespace"])
    require(Path(spec["ignored_result"]["path"]) == ignored_root / "result.json", "exact ignored result namespace")
    ignored_pins = {x["path"]: x for x in ignored_audit["archive"]["files"] if x["kind"] == "file"}
    ignored = selected_capture(ignored_root, ignored_pins, reads, False)
    require(ignored["coverage"] == ignored_result["coverage"] == ignored_audit["source_delta"]["coverage"]
            and ignored_result["physical_absence_verified"] is False and ignored_result["physical_bytes_unchanged"] is True, "ignored capture scope")
    present = ignored_result["physical_presence_after"]
    require(present == ignored_result["physical_presence_before"] and present["regular"] is True
            and present["source_cid"] == ignored_result["physical_presence_before"]["source_cid"], "historical physical presence record")
    physical_relative = "private/source-artifacts/source/" + present["source_cid"][:4] + "/" + present["source_cid"]
    physical_path = child_pin(ignored_root, physical_relative, ignored_pins, reads, 65536)
    require(sha(reads.take(physical_path)) == present["sha256"] and len(reads.take(physical_path)) == present["bytes"], "ignored source body pin")
    failed = values["failed_ignore_result"]
    require(failed["qualified"] is review["failed_ignore_attempt"]["qualified"] is False
            and failed["error"] == review["failed_ignore_attempt"]["error"], "original failed ignored observation preserved")
    history = exposure(main, values["historical_cohort_report"], values["checkpoint_result"], spec["historical_cohort_report"])
    require(not output.exists() and output.parent.resolve(strict=True) == output.parent, "fresh canonical output required")
    protected = {p.parent for p in reads.plan} | {main_root, ignored_root, manifest_path.parent}
    require(all(output != scope and not output.is_relative_to(scope) and not scope.is_relative_to(output) for scope in protected), "output overlaps selected input scope")
    reads.stable()
    output.mkdir()
    output_info = output.stat(follow_symlinks=False)
    output_identity = output_info.st_dev, output_info.st_ino
    def root_identity():
        current = output.stat(follow_symlinks=False)
        require(stat.S_ISDIR(current.st_mode) and (current.st_dev, current.st_ino) == output_identity
                and output.resolve(strict=True) == output, "created output root identity drift")
    expected, inputs = {}, []
    for index, (path, raw) in enumerate(sorted(reads.raw.items(), key=lambda x: str(x[0]))):
        name = f"input-{index:04d}.bin"
        with (output / name).open("xb") as stream:
            stream.write(raw)
        expected[name] = raw
        inputs.append({"path": str(path), "sha256": sha(raw), "size_bytes": len(raw), "retained_path": str(output / name)})
    report = {"schema": REPORT_SCHEMA, "status": "passed", "manifest_sha256": sha(manifest_raw),
              **{role + "_sha256": spec[role]["sha256"] for role in ROLES},
              **dict.fromkeys(TRUE_FLAGS, True), **dict.fromkeys(FALSE_FLAGS, False),
              "additional_attempted_training_epochs": 0, "new_final_assignments": 0,
              "scope": "exact source-only successor syntax and sealed historical content exposure; no eligibility or quality",
              "previous_member_count": main["coverage"]["previous_entries"], "current_member_count": main["coverage"]["current_entries"],
              "union_member_count": main["coverage"]["union_entries"], "entry_transition_counts": main["comparison_counts"]["entry"],
              "source_bytes_comparison_counts": main["comparison_counts"]["bytes"], "captured_ast_comparison_counts": main["comparison_counts"]["ast"],
              "source_syntax_comparison_counts": main["comparison_counts"]["syntax"], "structural_label_comparison_counts": main["comparison_counts"]["label"],
              "cross_path_content_pair_count": len(main["cross_path_content_pairs"]), "previous_clone_group_count": len(main["previous_clones"]),
              "current_clone_group_count": len(main["current_clones"]), "previous_template_group_count": len(main["previous_templates"]),
              "current_template_group_count": len(main["current_templates"]), "syntactic_dependency_edge_count": len(main["syntactic_dependencies"]),
              "historical_content_match_member_count": len(history["matches"]), "historical_content_match_role_counts": history["role_occurrence_counts"],
              "current_exposure_unknown_member_count": main["coverage"]["current_entries"], "affected_head_binding_count": 2,
              "ignored_removed_count": ignored["coverage"]["classifications"].get("removed", 0),
              "source_transition": main, "ignored_transition": ignored, "historical_content_exposure": history,
              "ignored_physical_presence_recorded": present, "physical_presence_live_replayed": False,
              "original_failed_ignored_observation": {"qualified": False, "error": failed["error"], "raw_sha256": spec["failed_ignore_result"]["sha256"]},
              "input_files": inputs, "input_file_count": len(inputs), "input_bytes": sum(len(x) for x in reads.raw.values()),
              "bounds": {"max_original_files": MAX_ORIGINALS, "max_original_copy_read_files": MAX_FILES, "max_original_copy_bytes": MAX_BYTES,
                         "max_side_members": 512, "max_union_members": 1024, "max_source_bytes": 65536, "max_ast_bytes": 128 * 1024,
                         "max_manifest_bytes": 4 * MiB, "max_delta_bytes": MiB, "max_report_bytes": 4 * MiB}}
    raw_report = report_bytes(report)
    reads.stable()
    population(output, expected)
    root_identity()
    with (output / "source_delta_analysis.json").open("xb") as stream:
        stream.write(raw_report)
    expected["source_delta_analysis.json"] = raw_report
    reads.stable()
    population(output, expected)
    root_identity()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = evaluate(args.manifest, args.output)
    except (Refused, OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, RecursionError, OverflowError) as exc:
        print(json.dumps({"schema": REPORT_SCHEMA, "status": "refused", "error": str(exc),
                          "unknown_pretraining_exposure": True, "current_exposure_unknown": True,
                          **dict.fromkeys(FALSE_FLAGS, False)}, sort_keys=True), file=sys.stderr)
        return 3
    print(json.dumps({"status": report["status"], "union_member_count": report["union_member_count"],
                      "input_file_count": report["input_file_count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
