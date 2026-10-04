"""Reconcile one retained source publication and its declared dependency frontier.

Only two explicitly selected archived Python bodies are parsed. Source is never
executed, and structural changes do not establish behavior or intent. Graph
edges and owner table counts remain producer declarations.
"""

from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import json
import math
import os
import re
import stat
from collections import Counter
from pathlib import Path

INPUT_SCHEMA = "codebase-ir-publication-dependency-audit-input@1"
REPORT_SCHEMA = "codebase-ir-publication-dependency-audit@1"
REPORT_NAME = "publication_dependency_audit.json"
ROLES = (
    "native_result",
    "published_source_receipt",
    "owners_before",
    "owners_after",
    "inherited_scan_root",
    "inherited_scan_completion",
    "generation2_manifest",
    "generation3_manifest",
    "generation2_calc_source",
    "generation3_calc_source",
    "generation2_calc_ast",
    "generation3_calc_ast",
    "expansion_review",
)
TRUE = (
    "retained_publication_dependency_accounting_produced",
    "complete_selected_capture_population_reconciled",
    "stable_symbol_population_reconciled",
    "declared_reverse_dependency_frontier_rederived",
    "fixed_archived_source_syntax_rederived",
    "inherited_scan_head_staleness_reconciled",
    "legacy_catalog_count_observations_preserved",
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
    "source_execution_performed",
    "model_execution_performed",
    "native_parser_imported",
    "source_semantics_verified",
    "source_intent_verified",
    "behavioral_equivalence_verified",
    "behavioral_difference_verified",
    "native_invalidation_completeness_verified",
    "semantic_state_identity_recipe_verified",
    "stable_symbol_identity_recipe_verified",
    "dependency_semantics_verified",
    "unresolved_dependency_frontiers_closed",
    "stale_head_refusal_reperformed",
    "new_scan_performed",
    "all_source_bodies_reopened",
    "physical_published_worktree_verified",
    "whole_repository_coverage",
    "model_quality_qualified",
    "full_transitive_dependency_attestation",
    "producer_authentication_verified",
    "process_origin_attested",
    "production_default_activated",
    "production_acceptance_closed",
    "historical_receipts_rewritten",
)
ZERO = ("runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs")
MIB = 1024 * 1024
MAX_BODY, MAX_TOTAL, MAX_MANIFEST, MAX_REPORT, MAX_FILES = (
    4 * MIB,
    16 * MIB,
    128 * 1024,
    4 * MIB,
    128,
)
HEAD_FIELDS = {
    "ast_revision_id",
    "generation",
    "manifest_cid",
    "receipt_cid",
    "repository_id",
    "schema",
    "snapshot_cid",
}
MANIFEST_FIELDS = {
    "ast_revision_id",
    "authority",
    "coverage",
    "schema",
    "semantic_state",
    "snapshot",
    "units",
}
ENTRY_FIELDS = {
    "acquisition",
    "disposition",
    "entry_cid",
    "git_blob_oid",
    "head_blob_oid",
    "index_blob_oids",
    "kind",
    "opaque_reason",
    "path",
    "raw_path_hex",
    "schema",
    "size_bytes",
    "source_cid",
}
SYMBOL_FIELDS = {
    "annotations",
    "confidence",
    "decorators",
    "extractor_name",
    "extractor_version",
    "kind",
    "language",
    "metadata",
    "module_path",
    "namespace",
    "normalized_ast",
    "property_role",
    "qualified_name",
    "repository_id",
    "schema",
    "semantic_index_schema",
    "signature",
    "source_cid",
    "span",
    "stable_id",
    "version_cid",
}
EDGE_FIELDS = {
    "confidence",
    "edge_id",
    "extraction_method",
    "extractor_version",
    "metadata",
    "relation",
    "schema",
    "source_id",
    "span",
    "target_id",
}
TABLES = (
    "ast_blobs",
    "ast_nodes",
    "calls",
    "diagnostics",
    "effects",
    "imports",
    "interfaces",
    "invalidations",
    "references",
    "scopes",
    "source_files",
    "source_revisions",
    "symbols",
)
AUTHORITY_FIELDS = {
    "admission_authority",
    "authoritative_cache_eligible",
    "behavioral_satisfaction",
    "completion_authority",
    "decoded_formulas_generated",
    "execution_authority",
    "mutation_authority",
    "proof_authority",
    "repository_code_executed",
    "runtime_behavior_verified",
    "scan_execution_attested",
    "source_execution_attested",
    "source_semantics_verified",
    "training_executed",
}
NATIVE_FIELDS = {
    "final_resource_cleanup_verified",
    "source_execution_attested",
    "new_fitting_epochs",
    "complete_scan_reexecuted_here",
    "reference_scope",
    "selected_version_id",
    "scan_execution_attested",
    "residual_task",
    "384d_qualified",
    "cuda_qualified",
    "overall_deadline_seconds",
    "public_receivers_reference_close",
    "observed_worker_allocations",
    "scheduler_state_path",
    "local_pool_bounded_by_host_envelope",
    "native_task_statuses",
    "new_reference_pages",
    "production_default_activated",
    "paired_entry_seconds",
    "resource_before_stop",
    "source_delta_cid",
    "inherited_scan_pages",
    "new_scan_pages",
    "previous_head",
    "numerical_after",
    "scan_coverage",
    "selection_cid",
    "inherited_reference_pages",
    "native_source_generation_advanced",
    "phases",
    "materialization",
    "publication",
    "start",
    "inference_attempt_count",
    "bootstrap_errors",
    "elapsed_seconds_so_far",
    "previous_version_id",
    "task_observations",
    "scheduler_configuration",
    "completion_cid",
    "recorded_seconds",
    "controls",
    "current_head",
    "stop",
    "worker_launched",
    "resource_after_native_owner_close",
    "full_administrator_population_completed",
    "operation_deadlines",
    "qualified",
    "post_setup_fit_attempt_count",
    "schema",
    "container_resource_authority_pin",
    "root_cid",
    "scope",
    "provider_calls",
    "original_source_artifacts_preserved",
    "inherited_setup_epochs",
    "final_resources",
    "remaining_processes",
    "paired_close_seconds",
    "pid",
    "native_worker_qualified",
    "shares_host_pid_state",
    "proof_authority",
    "numerical_before",
    "authored_worker_receipt",
    "native_task_body_bytes",
    "native_diagnostics",
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
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
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
        require(depth <= 64 and count_values <= 300000, "JSON allocation boundary")
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


def cid(raw, structured=False):
    prefix = b"\x01\xa9\x02\x12\x20" if structured else b"\x01\x55\x12\x20"
    return "b" + base64.b32encode(prefix + hashlib.sha256(raw).digest()).decode().lower().rstrip(
        "="
    )


def object_cid(value):
    return cid(wire(value), True)


def content_id(value):
    require(
        type(value) is str and re.fullmatch(r"b[a-z2-7]{20,128}", value), "bounded declared CID"
    )
    return value


def text(value, cap=4096):
    require(type(value) is str and 0 < len(value.encode()) <= cap, "bounded nonempty text")
    return value


def head(value, generation):
    closed(value, HEAD_FIELDS, "source head")
    require(
        value["schema"] == "codebase-head@1" and integer(value["generation"]) == generation,
        "fixed source head generation",
    )
    require(
        value["repository_id"] == "qualification:source-successor"
        and value["ast_revision_id"]
        == "rev:" + value["repository_id"] + ":snapshot:" + content_id(value["snapshot_cid"]),
        "source head repository/revision",
    )
    content_id(value["manifest_cid"])
    content_id(value["receipt_cid"])


def semantic_span(value, path):
    closed(
        value,
        {"schema", "path", "start_line", "end_line", "start_column", "end_column"},
        "declared semantic span",
    )
    require(
        value["schema"] == "ipfs-datasets.software-contracts.semantic-source-span@1"
        and value["path"] == path,
        "declared semantic span path",
    )
    for field in ("start_line", "end_line"):
        integer(value[field], 1, 65536)
    for field in ("start_column", "end_column"):
        integer(value[field], 0, 65536)
    require(
        (value["start_line"], value["start_column"]) <= (value["end_line"], value["end_column"]),
        "declared semantic span ordering",
    )


def capture(value, source_head):
    closed(value, MANIFEST_FIELDS, "structural manifest")
    require(
        value["schema"] == "codebase-ir-structural-manifest@1"
        and value["authority"] == "structural_only"
        and value["ast_revision_id"] == source_head["ast_revision_id"]
        and object_cid(value) == source_head["manifest_cid"],
        "structural manifest head/CID binding",
    )
    snapshot = value["snapshot"]
    closed(
        snapshot,
        {
            "entries",
            "exclusions",
            "git_commit",
            "git_tree",
            "max_entries",
            "max_file_bytes",
            "mode",
            "repository_id",
            "schema",
            "snapshot_cid",
        },
        "captured snapshot",
    )
    require(
        snapshot["schema"] == "ipfs-datasets.software-contracts.semantic-repository-snapshot@4"
        and snapshot["repository_id"] == source_head["repository_id"]
        and snapshot["snapshot_cid"] == source_head["snapshot_cid"],
        "snapshot declaration/head",
    )
    preimage = dict(snapshot)
    preimage.pop("snapshot_cid")
    require(object_cid(preimage) == source_head["snapshot_cid"], "snapshot CID recipe")
    require(
        integer(snapshot["max_entries"], 1, 512) == 512
        and integer(snapshot["max_file_bytes"], 1, 65536) == 65536
        and snapshot["mode"] == "git-clean",
        "capture bounds/declarations",
    )
    require(
        type(snapshot["exclusions"]) is list
        and all(type(x) is str for x in snapshot["exclusions"]),
        "capture exclusion declarations",
    )
    for field in ("git_commit", "git_tree"):
        require(
            type(snapshot[field]) is str and re.fullmatch("[0-9a-f]{40}", snapshot[field]),
            "declared Git identity only",
        )
    entries, units = snapshot["entries"], value["units"]
    require(
        type(entries) is list and type(units) is list and len(entries) == len(units) == 300,
        "complete selected capture denominator",
    )
    unit_map = {}
    for unit in units:
        closed(
            unit,
            {"ast_cid", "entry_cid", "parse_status", "schema", "source_key"},
            "structural unit",
        )
        require(
            unit["schema"] == "codebase-ir-structural-unit@1"
            and unit["parse_status"] in {"ok", "failed", "unindexed", "opaque"},
            "unit declarations",
        )
        require(unit["source_key"] not in unit_map, "unique structural source key")
        content_id(unit["entry_cid"])
        if unit["ast_cid"] is not None:
            content_id(unit["ast_cid"])
        unit_map[unit["source_key"]] = unit
    rows, order = {}, []
    for entry in entries:
        closed(entry, ENTRY_FIELDS, "snapshot entry")
        require(
            entry["schema"] == "ipfs-datasets.software-contracts.semantic-snapshot-entry@3",
            "snapshot entry declaration",
        )
        integer(entry["size_bytes"], 0, 2**63 - 1)
        require(
            type(entry["raw_path_hex"]) is str
            and re.fullmatch("(?:[0-9a-f]{2}){1,1024}", entry["raw_path_hex"]),
            "raw path byte declaration",
        )
        raw_path = bytes.fromhex(entry["raw_path_hex"])
        require(
            entry["path"] == raw_path.decode("utf-8")
            and b"\0" not in raw_path
            and not entry["path"].startswith("/")
            and ".." not in Path(entry["path"]).parts,
            "raw path correspondence",
        )
        preimage = dict(entry)
        preimage.pop("entry_cid")
        require(object_cid(preimage) == entry["entry_cid"], "entry CID recipe")
        require(
            entry["disposition"] == "clean"
            and entry["acquisition"] in {"git-object", "opaque"}
            and type(entry["index_blob_oids"]) is dict
            and not entry["index_blob_oids"],
            "fixed clean capture declarations",
        )
        require(
            entry["git_blob_oid"] == entry["head_blob_oid"]
            and re.fullmatch("[0-9a-f]{40}", text(entry["git_blob_oid"])),
            "declared clean Git blob identity",
        )
        if entry["source_cid"] is not None:
            content_id(entry["source_cid"])
        key = "raw:" + entry["raw_path_hex"]
        require(
            key in unit_map
            and entry["path"] not in rows
            and unit_map[key]["entry_cid"] == entry["entry_cid"],
            "whole entry/unit join",
        )
        unit = unit_map[key]
        require(
            (unit["parse_status"] == "opaque") is (entry["kind"] == "opaque"),
            "opaque declaration join",
        )
        require(
            (unit["ast_cid"] is None) is (unit["parse_status"] in {"opaque", "unindexed"}),
            "AST declaration availability",
        )
        rows[entry["path"]] = {"entry": entry, "unit": unit}
        order.append(key)
    require(
        order == sorted(order) and set(order) == set(unit_map), "ordered complete source population"
    )
    semantic = value["semantic_state"]
    closed(
        semantic,
        {
            "artifacts",
            "edges",
            "extractor_name",
            "extractor_version",
            "repository_id",
            "schema",
            "state_cid",
            "symbols",
        },
        "semantic index container",
    )
    require(
        semantic["schema"] == "ipfs-datasets.software-contracts.semantic-index@2"
        and semantic["repository_id"] == source_head["repository_id"]
        and semantic["extractor_name"] == "semantic-repository-scanner"
        and semantic["extractor_version"] == "1",
        "semantic container declarations",
    )
    content_id(semantic["state_cid"])
    require(
        type(semantic["symbols"]) is list
        and len(semantic["symbols"]) == 590
        and type(semantic["edges"]) is list
        and len(semantic["edges"]) == 7
        and type(semantic["artifacts"]) is list
        and len(semantic["artifacts"]) == 5,
        "complete selected semantic denominator",
    )
    symbols, edges, artifacts = {}, {}, {}
    for symbol in semantic["symbols"]:
        closed(symbol, SYMBOL_FIELDS, "declared semantic symbol")
        require(
            symbol["schema"] == "ipfs-datasets.software-contracts.semantic-symbol@2"
            and symbol["semantic_index_schema"] == semantic["schema"]
            and symbol["repository_id"] == source_head["repository_id"]
            and symbol["language"] == "python"
            and symbol["kind"] in {"module", "function"},
            "semantic symbol declarations",
        )
        sid = content_id(symbol["stable_id"])
        content_id(symbol["version_cid"])
        require(
            sid not in symbols and symbol["module_path"] in rows,
            "unique symbol and captured module join",
        )
        require(
            symbol["source_cid"] == rows[symbol["module_path"]]["entry"]["source_cid"]
            and rows[symbol["module_path"]]["unit"]["parse_status"] == "ok",
            "symbol source correspondence",
        )
        require(
            type(symbol["normalized_ast"]) is dict
            and type(symbol["signature"]) is dict
            and type(symbol["annotations"]) is dict
            and type(symbol["metadata"]) is dict
            and type(symbol["decorators"]) is list,
            "typed structural symbol payload",
        )
        text(symbol["qualified_name"])
        semantic_span(symbol["span"], symbol["module_path"])
        symbols[sid] = symbol
    for edge in semantic["edges"]:
        closed(edge, EDGE_FIELDS, "declared semantic edge")
        eid = content_id(edge["edge_id"])
        require(
            eid not in edges
            and edge["schema"] == "ipfs-datasets.software-contracts.semantic-edge@1"
            and edge["source_id"] in symbols,
            "unique edge/source symbol join",
        )
        metadata = edge["metadata"]
        if edge["relation"] == "calls":
            closed(
                metadata,
                {"native_boundary", "resolution", "unresolved_target"},
                "call edge metadata",
            )
            require(metadata["native_boundary"] is False, "selected nonnative edge declaration")
        elif edge["relation"] == "imports":
            closed(metadata, {"alias", "resolution", "unresolved_target"}, "import edge metadata")
            text(metadata["alias"])
        elif edge["relation"] == "reads_state":
            closed(metadata, {"resolution", "unresolved_target"}, "state edge metadata")
        require(
            type(metadata) is dict and metadata.get("resolution") in {"definite", "unresolved"},
            "explicit edge resolution frontier",
        )
        if metadata["resolution"] == "definite":
            require(edge["target_id"] in symbols, "definite edge target symbol join")
        else:
            require(
                edge["target_id"] not in symbols
                and edge["target_id"] == metadata.get("unresolved_target")
                and edge["target_id"].startswith(("global:", "lexical:")),
                "unresolved edge declaration",
            )
        semantic_span(edge["span"], symbols[edge["source_id"]]["module_path"])
        require(edge["relation"] in {"calls", "reads_state", "imports"}, "selected edge relation")
        edges[eid] = edge
    for artifact in semantic["artifacts"]:
        closed(
            artifact,
            {"artifact_id", "confidence", "kind", "metadata", "path", "schema", "source_cid"},
            "declared semantic artifact",
        )
        require(
            artifact["schema"] == "ipfs-datasets.software-contracts.semantic-artifact@1"
            and artifact["artifact_id"] not in artifacts
            and type(artifact["metadata"]) is dict,
            "unique artifact declaration",
        )
        if artifact["kind"] == "snapshot-evidence":
            require(
                artifact["path"] == "@snapshot-evidence"
                and artifact["source_cid"] == source_head["snapshot_cid"]
                and same(artifact["metadata"].get("snapshot"), snapshot),
                "embedded snapshot evidence join",
            )
        else:
            require(
                artifact["path"] in rows
                and artifact["source_cid"] == rows[artifact["path"]]["entry"]["source_cid"],
                "artifact source correspondence",
            )
        artifacts[artifact["artifact_id"]] = artifact
    counts = Counter(x["parse_status"] for x in units)
    coverage = {
        "ast_failed": counts["failed"],
        "ast_ok": counts["ok"],
        "ast_partial": 0,
        "captured_entries": 300 - counts["opaque"],
        "checked_properties": 0,
        "formalized_properties": 0,
        "inventory_entries": 300,
        "opaque_entries": counts["opaque"],
        "semantic_symbols": 590,
        "unindexed_entries": counts["unindexed"],
    }
    require(
        same(value["coverage"], coverage)
        and same(dict(counts), {"ok": 296, "failed": 1, "opaque": 2, "unindexed": 1}),
        "independently counted typed capture coverage",
    )
    require(
        Counter(s["kind"] for s in symbols.values()) == {"module": 296, "function": 294},
        "selected symbol kind denominator",
    )
    return rows, symbols, edges, artifacts


def normalize(node):
    if isinstance(node, ast.AST):
        return {
            "_type": type(node).__name__,
            **{field: normalize(value) for field, value in ast.iter_fields(node)},
        }
    if type(node) is list:
        return [normalize(value) for value in node]
    require(node is None or type(node) in {str, bool, int}, "selected AST literal type")
    return node


def source_span(value, raw):
    closed(
        value,
        {"start_byte", "end_byte", "start_line", "end_line", "start_column", "end_column"},
        "AST source span",
    )
    for field, number in value.items():
        integer(number, 1 if field.endswith("line") else 0, 65536)
    start, end = value["start_byte"], value["end_byte"]
    require(start <= end <= len(raw), "AST byte span bounds")
    lines = raw.split(b"\n")
    offsets, total = [], 0
    for line in lines:
        offsets.append(total)
        total += len(line) + 1
    for side in ("start", "end"):
        line, column = value[side + "_line"], value[side + "_column"]
        require(
            line <= len(lines)
            and column <= len(lines[line - 1])
            and offsets[line - 1] + column == value[side + "_byte"],
            "AST byte/line/column correspondence",
        )
    return start, end


def syntax(raw, captured, row, source_head, semantic_symbols, expected_order):
    require(
        len(raw) <= 65536
        and len(raw) == row["entry"]["size_bytes"]
        and cid(raw) == row["entry"]["source_cid"]
        and object_cid(captured) == row["unit"]["ast_cid"],
        "fixed archived source/AST content binding",
    )
    closed(
        captured,
        {
            "calls",
            "diagnostics",
            "effects",
            "frontend",
            "imports",
            "module",
            "provenance",
            "references",
            "schema",
            "scopes",
            "symbols",
            "unsupported",
        },
        "captured AST",
    )
    require(
        captured["schema"] == "ipfs-datasets.software-contracts.ast-ir@1.0.0", "captured AST schema"
    )
    closed(
        captured["provenance"],
        {"path", "repository_id", "repository_tree_cid", "revision", "source_cid"},
        "AST provenance",
    )
    require(
        same(
            captured["provenance"],
            {
                "path": "calc.py",
                "repository_id": source_head["repository_id"],
                "repository_tree_cid": source_head["snapshot_cid"],
                "revision": "snapshot:" + source_head["snapshot_cid"],
                "source_cid": row["entry"]["source_cid"],
            },
        ),
        "AST provenance/source head",
    )
    require(
        captured["calls"]
        == captured["diagnostics"]
        == captured["effects"]
        == captured["imports"]
        == captured["unsupported"]
        == [],
        "selected AST absent unsupported/dependency records",
    )
    closed(
        captured["frontend"],
        {
            "ast_schema",
            "capabilities",
            "frontend_name",
            "frontend_version",
            "language",
            "language_version",
            "schema",
            "source_extensions",
            "toolchain_cid",
        },
        "AST frontend declaration",
    )
    frontend = captured["frontend"]
    require(
        frontend["schema"] == "ipfs-datasets.software-contracts.frontend-capability@1.0.0"
        and frontend["language"] == "python"
        and frontend["frontend_name"] == "cpython-ast",
        "AST frontend schema/language declarations",
    )
    closed(
        frontend["ast_schema"],
        {"identifier", "major", "minor", "name", "patch"},
        "AST schema declaration",
    )
    require(
        same(
            frontend["ast_schema"],
            {
                "identifier": "ipfs-datasets.software-contracts.ast-ir@1.0.0",
                "major": 1,
                "minor": 0,
                "name": "ipfs-datasets.software-contracts.ast-ir",
                "patch": 0,
            },
        ),
        "typed AST schema version",
    )
    content_id(frontend["toolchain_cid"])
    for field in ("capabilities", "source_extensions"):
        require(
            type(frontend[field]) is list
            and len(frontend[field]) <= 64
            and all(type(v) is str for v in frontend[field]),
            "bounded frontend declarations",
        )
    closed(
        captured["module"],
        {"export_names", "module_id", "name", "scope_id", "span"},
        "AST module declaration",
    )
    require(
        captured["module"]["name"] == "calc"
        and captured["module"]["scope_id"] == "scope:module"
        and captured["module"]["export_names"] == ["increment"],
        "selected module declarations",
    )
    for reference in captured["references"]:
        closed(
            reference,
            {"context", "is_qualified", "name", "reference_id", "scope_id", "span"},
            "AST reference",
        )
        require(reference["is_qualified"] is False, "selected unqualified references")
    for symbol in captured["symbols"]:
        closed(
            symbol,
            {
                "decorator_names",
                "definition_ordinal",
                "flags",
                "kind",
                "name",
                "qualified_name",
                "scope_id",
                "signature",
                "span",
                "symbol_id",
                "visibility",
            },
            "AST symbol",
        )
        integer(symbol["definition_ordinal"])
    for scope in captured["scopes"]:
        closed(
            scope, {"kind", "owner_symbol_id", "parent_scope_id", "scope_id", "span"}, "AST scope"
        )
    pending = [captured]
    while pending:
        value = pending.pop()
        if type(value) is dict:
            if "span" in value:
                source_span(value["span"], raw)
            pending.extend(x for k, x in value.items() if k != "span")
        elif type(value) is list:
            pending.extend(value)
    require(
        captured["module"]["module_id"] == "module:" + row["entry"]["source_cid"]
        and source_span(captured["module"]["span"], raw) == (0, len(raw)),
        "AST whole module extent",
    )
    try:
        tree = ast.parse(raw.decode("utf-8"), type_comments=True)
    except (SyntaxError, UnicodeError, RecursionError) as exc:
        raise Refused("bounded selected archived Python syntax") from exc
    require(
        len(list(ast.walk(tree))) <= 128
        and len(tree.body) == 1
        and isinstance(tree.body[0], ast.FunctionDef),
        "bounded selected archived function grammar",
    )
    function = tree.body[0]
    require(
        function.name == "increment"
        and len(function.body) == 1
        and isinstance(function.body[0], ast.Return),
        "single selected return function",
    )
    returned = function.body[0].value
    require(
        isinstance(returned, ast.BinOp) and isinstance(returned.op, ast.Add),
        "selected structural Add expression",
    )
    shape = [normalize(returned.left), normalize(returned.right)]
    expected = [normalize(ast.Name(id="n", ctx=ast.Load())), normalize(ast.Constant(value=2))]
    if expected_order == "constant_then_name":
        expected.reverse()
    require(same(shape, expected), "fixed syntactic operand order")
    selected = [
        s
        for s in semantic_symbols.values()
        if s["module_path"] == "calc.py" and s["kind"] == "function"
    ]
    require(
        len(selected) == 1 and same(selected[0]["normalized_ast"], normalize(function)),
        "independent function AST/semantic record correspondence",
    )
    offsets, total = [], 0
    for line in raw.split(b"\n"):
        offsets.append(total)
        total += len(line) + 1

    def extent(node):
        return offsets[node.lineno - 1] + node.col_offset, offsets[
            node.end_lineno - 1
        ] + node.end_col_offset

    refs = sorted(
        (n.id, "read" if n.id == "n" else "type", *extent(n))
        for n in ast.walk(tree)
        if isinstance(n, ast.Name)
    )
    symbols = sorted(
        ("function", n.name, *extent(n))
        if isinstance(n, ast.FunctionDef)
        else ("parameter", n.arg, *extent(n))
        for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef | ast.arg)
    )
    require(
        refs
        == sorted(
            (r["name"], r["context"], *source_span(r["span"], raw)) for r in captured["references"]
        ),
        "independent complete AST reference/span population",
    )
    require(
        symbols
        == sorted(
            (s["kind"], s["name"], *source_span(s["span"], raw)) for s in captured["symbols"]
        ),
        "independent complete AST symbol/span population",
    )
    declared_function = next(s for s in captured["symbols"] if s["kind"] == "function")
    require(
        same(
            declared_function["signature"],
            {
                "is_async": False,
                "is_generator": False,
                "parameters": [
                    {
                        "annotation": "int",
                        "default_kind": "none",
                        "kind": "positional_or_named",
                        "name": "n",
                        "position": 0,
                    }
                ],
                "return_annotation": "int",
            },
        ),
        "independent selected function signature",
    )
    scopes = {s["scope_id"] for s in captured["scopes"]}
    require(
        len(scopes) == len(captured["scopes"]) == 2
        and all(s["scope_id"] in scopes for s in captured["symbols"] + captured["references"]),
        "AST scope closure",
    )
    span = selected[0]["span"]
    require(
        same(
            {k: span[k] for k in ("start_line", "end_line", "start_column", "end_column")},
            {
                "start_line": function.lineno,
                "end_line": function.end_lineno,
                "start_column": function.col_offset,
                "end_column": function.end_col_offset,
            },
        ),
        "function semantic/source span",
    )
    return {
        "source_sha256": sha(raw),
        "source_cid": cid(raw),
        "source_size_bytes": len(raw),
        "captured_ast_cid": object_cid(captured),
        "normalized_function_sha256": sha(wire(normalize(function))),
        "normalized_whole_ast_sha256": sha(ast.dump(tree, include_attributes=False).encode()),
        "return_operand_order": expected_order,
        "reference_count": len(refs),
        "symbol_count": len(symbols),
        "source_span_count": sum(
            "span" in x for x in captured["references"] + captured["symbols"] + captured["scopes"]
        )
        + 1,
        "syntax_only": True,
        "behavioral_claim": False,
    }


def authority(value):
    closed(value, AUTHORITY_FIELDS, "inherited scan authority")
    require(all(x is False for x in value.values()), "inherited scan false authority")


def envelope(value, schema, fields):
    closed(value, {"artifact_cid", "value"}, "scan envelope")
    closed(value["value"], fields, "scan artifact")
    require(
        value["value"]["schema"] == schema and object_cid(value["value"]) == value["artifact_cid"],
        "scan artifact schema/CID binding",
    )
    return value["value"]


def member(row):
    e, u = row["entry"], row["unit"]
    return {
        "ast_cid": u["ast_cid"],
        "entry_cid": e["entry_cid"],
        "opaque_reason": e["opaque_reason"],
        "parse_status": u["parse_status"],
        "path": e["path"],
        "raw_path_hex": e["raw_path_hex"],
        "source_cid": e["source_cid"],
        "source_key": u["source_key"],
        "source_size_bytes": e["size_bytes"],
    }


def derive(metadata):
    docs = {k: document(v) for k, v in metadata.items() if not k.endswith("_source")}
    native = docs["native_result"]
    closed(native, NATIVE_FIELDS, "retained native result")
    require(
        native["schema"] == "codebase-signed-successor-native-qualification@1"
        and native["qualified"]
        is native["native_worker_qualified"]
        is native["native_source_generation_advanced"]
        is True,
        "qualified retained worker source milestone",
    )
    for field in (
        "proof_authority",
        "production_default_activated",
        "384d_qualified",
        "cuda_qualified",
        "complete_scan_reexecuted_here",
        "scan_execution_attested",
        "source_execution_attested",
    ):
        require(native[field] is False, "native declaration false authority/scan scope")
    for field in (
        "new_fitting_epochs",
        "new_scan_pages",
        "new_reference_pages",
        "inference_attempt_count",
        "post_setup_fit_attempt_count",
        "provider_calls",
    ):
        require(integer(native[field]) == 0, "no new fitting/inference/scan declarations")
    before, after = docs["owners_before"], docs["owners_after"]
    for owner in (before, after):
        closed(owner, {"model_artifacts", "registry", "source"}, "retained owner metadata")
        closed(owner["source"], {"current_head", "tables"}, "retained source metadata")
        closed(owner["source"]["tables"], TABLES, "complete source table observation population")
        for row in owner["source"]["tables"].values():
            closed(row, {"rows", "sha256"}, "source table count/digest observation")
            integer(row["rows"])
            digest(row["sha256"])
    h2, h3 = before["source"]["current_head"], after["source"]["current_head"]
    head(h2, 2)
    head(h3, 3)
    head(native["current_head"], 2)
    head(native["previous_head"], 1)
    require(same(native["current_head"], h2), "inherited native head exact source join")
    receipt = docs["published_source_receipt"]
    closed(
        receipt,
        {
            "ast_revision_id",
            "generation",
            "manifest_cid",
            "operation_id",
            "previous_head",
            "repository_id",
            "request_cid",
            "schema",
            "snapshot_cid",
        },
        "publication receipt",
    )
    require(
        receipt["schema"] == "codebase-publication-receipt@1"
        and object_cid(receipt) == h3["receipt_cid"]
        and same(receipt["previous_head"], h2)
        and receipt["operation_id"] == "signed-successor-format-publication",
        "publication predecessor/receipt CID binding",
    )
    content_id(receipt["request_cid"])
    require(
        all(
            same(receipt[k], h3[k])
            for k in (
                "ast_revision_id",
                "generation",
                "manifest_cid",
                "repository_id",
                "snapshot_cid",
            )
        ),
        "publication head exact typed join",
    )
    a, b = docs["generation2_manifest"], docs["generation3_manifest"]
    rows2, symbols2, edges2, artifacts2 = capture(a, h2)
    rows3, symbols3, edges3, artifacts3 = capture(b, h3)
    require(
        set(rows2) == set(rows3) and set(symbols2) == set(symbols3),
        "complete unchanged member/stable ID sets",
    )
    paths = sorted(rows2)
    changed = [p for p in paths if not same(rows2[p]["entry"], rows3[p]["entry"])]
    require(changed == ["calc.py"], "exact one changed captured path")
    changed_units = [p for p in paths if not same(rows2[p]["unit"], rows3[p]["unit"])]
    require(
        len(changed_units) == 297
        and all(
            rows2[p]["unit"]["ast_cid"] is not None
            and rows3[p]["unit"]["ast_cid"] is not None
            and rows2[p]["unit"]["ast_cid"] != rows3[p]["unit"]["ast_cid"]
            for p in changed_units
        ),
        "complete observed AST identity churn",
    )
    for field in ("exclusions", "max_entries", "max_file_bytes", "mode", "repository_id", "schema"):
        require(same(a["snapshot"][field], b["snapshot"][field]), "capture policy invariant")
    pub = native["publication"]
    closed(
        pub,
        {
            "baseline_commit",
            "changed_paths",
            "parents",
            "public_checks",
            "public_checks_passed",
            "published_commit",
        },
        "publication declarations",
    )
    require(
        pub["changed_paths"] == changed
        and pub["baseline_commit"] == a["snapshot"]["git_commit"]
        and pub["published_commit"] == b["snapshot"]["git_commit"],
        "publication/captured Git identity declarations",
    )
    require(same(a["coverage"], b["coverage"]), "capture denominator remains unchanged")
    changed_symbols = [sid for sid in sorted(symbols2) if not same(symbols2[sid], symbols3[sid])]
    require(
        len(changed_symbols) == 2
        and all(
            symbols2[s]["module_path"] == symbols3[s]["module_path"] == "calc.py"
            for s in changed_symbols
        ),
        "exact two changed calc symbol records",
    )
    versions = [
        s for s in changed_symbols if symbols2[s]["version_cid"] != symbols3[s]["version_cid"]
    ]
    require(
        len(versions) == 1 and symbols2[versions[0]]["kind"] == "function",
        "one changed function version",
    )
    require(
        all(same(symbols2[s]["signature"], symbols3[s]["signature"]) for s in changed_symbols),
        "retained calc signature invariant",
    )
    require(same(edges2, edges3), "all declared edges unchanged")
    require(
        set(artifacts2) == set(artifacts3)
        and [k for k in artifacts2 if not same(artifacts2[k], artifacts3[k])]
        == ["artifact:snapshot-evidence"],
        "only snapshot artifact metadata changes",
    )
    incoming = [
        e
        for e in edges3.values()
        if e["metadata"]["resolution"] == "definite" and e["target_id"] in versions
    ]
    unresolved = [e for e in edges3.values() if e["metadata"]["resolution"] == "unresolved"]
    require(
        len(incoming) == 4
        and len(unresolved) == 3
        and Counter(e["relation"] for e in incoming) == {"calls": 2, "imports": 2},
        "declared dependency frontier denominator",
    )
    reached, frontier, layers = set(versions), set(versions), []
    while frontier:
        fresh = {
            e["source_id"]
            for e in edges3.values()
            if e["metadata"]["resolution"] == "definite" and e["target_id"] in frontier
        } - reached
        if not fresh:
            break
        require(len(layers) < 590, "bounded finite graph traversal")
        layers.append(sorted(fresh))
        reached |= fresh
        frontier = fresh
    affected = sorted(reached - set(versions))
    affected_paths = sorted({symbols3[s]["module_path"] for s in affected})
    require(
        len(affected) == 2 and affected_paths == ["check_offset.py", "check_type.py"],
        "finite declared reverse dependency closure",
    )
    source_rows = [
        syntax(
            metadata[f"generation{generation}_calc_source"],
            docs[f"generation{generation}_calc_ast"],
            rows["calc.py"],
            h,
            symbols,
            order,
        )
        for generation, rows, h, symbols, order in (
            (2, rows2, h2, symbols2, "name_then_constant"),
            (3, rows3, h3, symbols3, "constant_then_name"),
        )
    ]
    require(
        source_rows[0]["normalized_whole_ast_sha256"]
        != source_rows[1]["normalized_whole_ast_sha256"],
        "observed whole syntax differs without behavioral claim",
    )
    scan = envelope(
        docs["inherited_scan_root"],
        "codebase-inventory-resume-root@1",
        {
            "authority",
            "head",
            "head_cid",
            "implementation",
            "limits",
            "members",
            "membership_cid",
            "model",
            "optimized",
            "schema",
        },
    )
    completion = envelope(
        docs["inherited_scan_completion"],
        "codebase-inventory-resume-completion@1",
        {
            "authority",
            "coverage",
            "head_cid",
            "membership_cid",
            "model_artifact_cid",
            "pages",
            "root_cid",
            "schema",
        },
    )
    authority(scan["authority"])
    authority(completion["authority"])
    members = [member(row) for row in rows2.values()]
    members.sort(key=lambda x: x["source_key"])
    require(
        same(scan["head"], h2)
        and scan["head_cid"] == object_cid(h2)
        and same(scan["members"], members)
        and scan["membership_cid"] == object_cid(members),
        "inherited full scan head/member exact population",
    )
    require(
        scan["optimized"] is True
        and completion["root_cid"]
        == docs["inherited_scan_root"]["artifact_cid"]
        == native["root_cid"]
        and completion["head_cid"] == scan["head_cid"]
        and completion["membership_cid"] == scan["membership_cid"]
        and docs["inherited_scan_completion"]["artifact_cid"] == native["completion_cid"],
        "inherited completion root/head join",
    )
    require(
        type(completion["pages"]) is list
        and len(completion["pages"]) == 10
        and same(completion["coverage"], native["scan_coverage"])
        and same(
            completion["coverage"],
            {
                "dispositions": {
                    "deferred_budget": 89,
                    "inferred": 205,
                    "opaque": 2,
                    "parse_failed": 1,
                    "unindexed": 1,
                    "unsupported_target": 2,
                },
                "inferred_rows": 205,
                "inventory_entries": 300,
                "pages": 10,
            },
        ),
        "inherited scan complete metadata denominator",
    )
    controls = native["controls"]
    require(
        type(controls) is list and len(controls) == 1, "exact retained stale control population"
    )
    closed(
        controls[0],
        {"error", "error_type", "integrity_refusal_claimed", "name", "refused"},
        "stale control observation",
    )
    require(
        same(
            controls[0],
            {
                "error": "resume catalog head changed",
                "error_type": "StaleCodebaseError",
                "integrity_refusal_claimed": True,
                "name": "published_source_rejects_old_completion",
                "refused": True,
            },
        ),
        "retained exact stale-head observation",
    )
    review = docs["expansion_review"]
    require(
        type(review) is dict
        and review.get("signed_successor_dispatch_qualified") is True
        and review.get("source_semantics_verified") is False
        and review.get("proof_authority") is False
        and review.get("full_transitive_dependency_attestation") is False
        and review.get("process_origin_attested") is False
        and same(review["signed_worker"]["publication"], pub),
        "private reviewed milestone metadata join",
    )
    pin = review["signed_worker"]["native_result"]
    require(
        pin["sha256"] == sha(metadata["native_result"])
        and integer(pin["bytes"]) == len(metadata["native_result"]),
        "review/native raw identity join",
    )
    table_counts = [
        {
            "table": k,
            "previous_rows": before["source"]["tables"][k]["rows"],
            "published_rows": after["source"]["tables"][k]["rows"],
            "previous_sha256": before["source"]["tables"][k]["sha256"],
            "published_sha256": after["source"]["tables"][k]["sha256"],
            "native_rows_replayed": False,
        }
        for k in TABLES
    ]
    require(
        before["source"]["tables"]["source_revisions"]["rows"] == 2
        and after["source"]["tables"]["source_revisions"]["rows"] == 3
        and before["source"]["tables"]["invalidations"]["rows"] == 1
        and after["source"]["tables"]["invalidations"]["rows"] == 2,
        "retained revision/invalidation count observations",
    )
    changed_rows = [
        {
            "stable_id": s,
            "qualified_name": symbols3[s]["qualified_name"],
            "kind": symbols3[s]["kind"],
            "previous_source_cid": symbols2[s]["source_cid"],
            "published_source_cid": symbols3[s]["source_cid"],
            "previous_version_cid": symbols2[s]["version_cid"],
            "published_version_cid": symbols3[s]["version_cid"],
            "version_changed": s in versions,
            "signature_unchanged": True,
            "previous_span": symbols2[s]["span"],
            "published_span": symbols3[s]["span"],
        }
        for s in changed_symbols
    ]
    return {
        "generation_delta": {
            "previous_head": h2,
            "published_head": h3,
            "publication_receipt_cid": object_cid(receipt),
            "changed_paths": changed,
            "unchanged_entry_count": 299,
            "unchanged_unit_count": 3,
            "changed_unit_count": 297,
            "changed_ast_identity_count": 297,
            "unavailable_ast_identity_count": 3,
            "unchanged_entry_changed_ast_count": 296,
            "unselected_ast_pair_count": 296,
            "source_change": {
                "previous": member(rows2["calc.py"]),
                "published": member(rows3["calc.py"]),
            },
            "capture_coverage": a["coverage"],
            "previous_git_commit": a["snapshot"]["git_commit"],
            "published_git_commit": b["snapshot"]["git_commit"],
            "git_identity_scope": "declaration_only",
        },
        "inventory_entries": 300,
        "symbol_count": 590,
        "unchanged_symbol_count": 588,
        "changed_symbol_count": 2,
        "changed_function_version_count": 1,
        "edge_count": 7,
        "unchanged_edge_count": 7,
        "artifact_count": 5,
        "changed_artifact_count": 1,
        "changed_symbols": changed_rows,
        "entry_comparisons": [
            {
                "path": p,
                "source_key": rows2[p]["unit"]["source_key"],
                "classification": "changed" if p in changed else "unchanged",
                "previous_entry_cid": rows2[p]["entry"]["entry_cid"],
                "published_entry_cid": rows3[p]["entry"]["entry_cid"],
                "previous_ast_cid": rows2[p]["unit"]["ast_cid"],
                "published_ast_cid": rows3[p]["unit"]["ast_cid"],
            }
            for p in paths
        ],
        "declared_dependency_frontier": {
            "changed_function_stable_ids": versions,
            "incoming_edge_count": 4,
            "incoming_edges": incoming,
            "affected_symbol_ids": affected,
            "affected_paths": affected_paths,
            "reverse_layers": layers,
            "unresolved_frontier_count": 3,
            "unresolved_edges": unresolved,
            "scope": "selected_declared_graph_only",
        },
        "archived_source_syntax": source_rows,
        "inherited_scan_staleness": {
            "scan_head_cid": scan["head_cid"],
            "published_head_cid": object_cid(h3),
            "heads_differ": True,
            "root_cid": native["root_cid"],
            "completion_cid": native["completion_cid"],
            "prior_capture_member_count": 300,
            "coverage": completion["coverage"],
            "recorded_refusal": controls[0],
            "refusal_reperformed": False,
            "fresh_published_scan_present": False,
        },
        "catalog_table_observations": table_counts,
        "semantic_state_identity_scope": "unverified_native_identity_recipe",
        "stable_symbol_identity_scope": "retained_declared_ids_not_native_recipe",
    }


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
        and manifest["fixture_origin"] == "retained_signed_successor_publication",
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
        manifest_sha256=sha(manifest_raw),
        selected_files=selected,
        selected_file_count=13,
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
        ),
        limitations=[
            "Selected retained structural records and two archived Python bodies only; no source behavior or intent claim.",
            "Definite and unresolved dependency edges are declarations, not independently executed dependency semantics.",
            "Native table counts and stale-head refusal are retained observations; no database row or runtime replay.",
            "Semantic-state and stable-symbol identity recipes remain unverified; manifest/snapshot/entry CID seals are derived.",
            "299 unchanged entry records, 3 unchanged unit records and 588 symbol records do not reopen every source body or the published worktree.",
            "Per-file closing fences are not an atomic filesystem snapshot or producer authentication.",
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
                    "inventory_entries",
                    "changed_symbol_count",
                    "changed_function_version_count",
                )
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
