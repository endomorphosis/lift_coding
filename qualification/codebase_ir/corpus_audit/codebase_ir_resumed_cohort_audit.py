#!/usr/bin/env python3
"""Account for a retained completed scan and declared source training exposure.

Only explicitly selected inert bodies are read. Source is parsed as syntax; no
repository, model, optimizer, registry, worker, compiler or checker is executed.
"""

from __future__ import annotations

import argparse
import ast
import base64
import copy
import json
import os
import stat
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

import codebase_ir_corpus_audit as audit
import codebase_ir_final_evaluation as final
import codebase_ir_final_lock as lock_tool
import codebase_ir_native_source384_diagnostics as native

INPUT_SCHEMA = "codebase-ir-resumed-cohort-audit-input@1"
REPORT_SCHEMA = "codebase-ir-resumed-cohort-audit@1"
PROFILE = "qualification/completed-resumed-source-cohort-accounting@1"
INPUT_ROLES = ("qualification_review", "native_result")
FROZEN_PINS = {
    "qualification_review": (
        "600f377ef6828a0c5001baba5f23096a751f7203beb222ff90fb6d03f3f6b725",
        86084,
    ),
    "native_result": ("b6307c0c8cd912c55161c3f6d50563cbf71e2d1ac9ba5538b52cb498a90e353f", 341072),
}
TRUE_FLAGS = {
    "source_artifact_body_pins_verified",
    "source_ast_membership_accounting_available",
    "complete_paged_disposition_accounting_available",
    "normalized_ast_groups_rederived",
    "declared_exposure_roles_preserved",
    "retained_training_selections_accounted",
    "unknown_pretraining_exposure",
    "input_files_stable",
    "input_files_unchanged",
}
FALSE_FLAGS = native.FALSE_FLAGS | {
    "source_runtime_truth_verified",
    "training_population_equals_inventory",
    "complete_pretraining_exposure_verified",
    "model_predictions_evaluated",
    "optimizer_state_replayed",
    "final_population_modified",
    "scan_execution_attested",
    "source_execution_attested",
    "runtime_behavior_verified",
    "source_ast_semantics_verified",
    "native_target_recipe_replayed",
}
DISPOSITIONS = {
    "inferred",
    "deferred_budget",
    "opaque",
    "parse_failed",
    "unindexed",
    "unsupported_target",
    "zero_vocabulary",
}
MEMBER_FIELDS = {
    "ast_cid",
    "entry_cid",
    "opaque_reason",
    "parse_status",
    "path",
    "raw_path_hex",
    "source_cid",
    "source_key",
    "source_size_bytes",
}
AST_FIELDS = {
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
}


@dataclass(frozen=True)
class Limits:
    max_files: int = 768
    max_file_bytes: int = 8 * 1024 * 1024
    max_total_bytes: int = 64 * 1024 * 1024
    max_manifest_bytes: int = 1024 * 1024
    max_members: int = 512
    max_source_artifacts: int = 640
    max_pages: int = 32
    max_source_bytes: int = 65536
    max_ast_nodes: int = 4096
    max_json_nodes: int = 1000000
    max_lineage_targets: int = 32

    def __post_init__(self):
        audit._require(
            all(type(v) is int and v > 0 for v in asdict(self).values()),
            "positive exact cohort limits required",
        )


DEFAULT_LIMITS = Limits()


def _json(raw, limits):
    return audit._load_json(
        raw,
        audit.Limits(max_json_bytes=limits.max_file_bytes, max_json_nodes=limits.max_json_nodes),
    )


def _same(a, b):
    return audit._canonical(a) == audit._canonical(b)


def _cid(raw, kind):
    prefix = {"source": bytes.fromhex("01551220"), "structured": bytes.fromhex("01a9021220")}[kind]
    return "b" + base64.b32encode(prefix + bytes.fromhex(audit._sha(raw))).decode().lower().rstrip(
        "="
    )


def _count(value, maximum, label):
    audit._require(
        type(value) is int and 0 <= value <= maximum, "bounded exact integer required: " + label
    )
    return value


def _authority(value):
    audit._require(
        type(value) is dict and value and all(v is False for v in value.values()),
        "retained structural authority must remain false",
    )


def _selection(result, limits):
    setup = result["setup_reuse"]["copied_members"]
    scan = result["source_scan_seed"]["copied_members"]
    audit._require(
        type(setup) is list and len(setup) <= 1536 and type(scan) is list and len(scan) <= 64,
        "bounded retained selection receipt required",
    )
    selected = [
        x
        for x in setup
        if type(x) is dict
        and type(x.get("path")) is str
        and x["path"].startswith("private/source-artifacts/")
    ]
    audit._require(
        len(selected) <= limits.max_source_artifacts, "source artifact selection budget exceeded"
    )
    selected_scan = [x for x in scan if type(x) is dict and x.get("kind") == "cas"]
    audit._require(
        len(selected_scan) <= limits.max_pages + 4, "scan artifact selection budget exceeded"
    )
    records, seen = [], set()
    for row, is_scan in [(x, False) for x in selected] + [(x, True) for x in selected_scan]:
        fields = (
            {"path", "sha256", "bytes", "mode", "kind", "cid", "codec", "role"}
            if is_scan
            else {"path", "sha256", "bytes", "mode"}
        )
        audit._closed(row, fields, "explicit retained artifact descriptor")
        path = audit._text(row["path"], "retained artifact selector", 512)
        parts = path.split("/")
        expected_prefix = ["cas"] if is_scan else ["private", "source-artifacts"]
        audit._require(
            parts[: len(expected_prefix)] == expected_prefix
            and len(parts) == len(expected_prefix) + 3,
            "only explicit flat source artifact CAS selectors permitted",
        )
        kind, shard, cid = parts[-3:]
        audit._require(
            kind in {"source", "structured"}
            and shard == cid[:4]
            and shard == ("bafk" if kind == "source" else "bagu"),
            "closed source artifact CID selector required",
        )
        audit._digest(row["sha256"], "retained artifact SHA")
        size = _count(row["bytes"], limits.max_file_bytes, "retained artifact bytes")
        audit._require(cid not in seen, "duplicate or aliased selected CAS identity")
        seen.add(cid)
        if is_scan:
            audit._require(
                row["cid"] == cid and row["codec"] == ("raw" if kind == "source" else "dag-json"),
                "scan descriptor codec identity mismatch",
            )
        records.append(
            {
                "cid": cid,
                "kind": kind,
                "sha256": row["sha256"],
                "size_bytes": size,
                "path": "private/source-artifacts/" + "/".join(parts[-3:]),
                "role": row["role"] if is_scan else "captured_source_artifact",
            }
        )
    audit._require(
        2 + len(INPUT_ROLES) + len(records) <= limits.max_files,
        "selected population exceeds file budget before allocation",
    )
    # The budget covers both originals in memory and retained copies before capture.
    audit._require(
        2 * sum(x["size_bytes"] for x in records) <= limits.max_total_bytes,
        "selected raw and copied byte budget exceeded before allocation",
    )
    return records


def _span(value, raw):
    audit._closed(
        value,
        {"start_byte", "end_byte", "start_line", "end_line", "start_column", "end_column"},
        "captured source span",
    )
    audit._require(
        all(type(v) is int for v in value.values()), "exact source span integers required"
    )
    start, end = value["start_byte"], value["end_byte"]
    audit._require(0 <= start <= end <= len(raw), "captured span outside exact source")
    lines = raw.splitlines(keepends=True)
    if not lines or raw.endswith((b"\n", b"\r")):
        lines.append(b"")
    for side, offset in (("start", start), ("end", end)):
        line, column = value[side + "_line"], value[side + "_column"]
        audit._require(
            1 <= line <= len(lines)
            and 0 <= column <= len(lines[line - 1])
            and sum(map(len, lines[: line - 1])) + column == offset,
            "captured span line/column differs from exact bytes",
        )
    return start, end


def _syntax(member, raw, captured, head, limits):
    audit._require(
        len(raw) <= limits.max_source_bytes and len(raw) == member["source_size_bytes"],
        "exact source byte limit/length differs",
    )
    decoded = raw.decode("utf-8", errors="strict")
    if captured is None:
        audit._require(
            member["parse_status"] == "unindexed", "available Python source missing captured AST"
        )
        return {
            "syntax_disposition": "unindexed",
            "normalized_ast_sha256": None,
            "template_ast_sha256": None,
            "dependency_paths": [],
            "reference_span_count": 0,
        }
    try:
        tree = ast.parse(decoded)
    except SyntaxError:
        audit._require(
            member["parse_status"] == "failed"
            and captured is not None
            and captured["diagnostics"]
            and captured["unsupported"],
            "retained failed parse disposition differs",
        )
        tree = None
    audit._closed(captured, AST_FIELDS, "captured AST record")
    audit._require(
        captured["schema"] == "ipfs-datasets.software-contracts.ast-ir@1.0.0",
        "closed captured AST schema required",
    )
    provenance = captured["provenance"]
    audit._require(
        provenance["path"] == member["path"]
        and provenance["source_cid"] == member["source_cid"]
        and provenance["repository_id"] == head["repository_id"]
        and provenance["repository_tree_cid"] == head["snapshot_cid"]
        and provenance["revision"] == "snapshot:" + head["snapshot_cid"],
        "captured AST source/revision membership differs",
    )
    audit._require(
        captured["module"]["module_id"] == "module:" + member["source_cid"],
        "captured AST module/source identity differs",
    )
    audit._require(
        _span(captured["module"]["span"], raw) == (0, len(raw)),
        "captured AST module does not cover exact source",
    )
    spans = []

    def walk(node, depth=0):
        audit._require(depth <= 64, "captured AST span depth budget exceeded")
        if type(node) is dict:
            if "span" in node and type(node["span"]) is dict:
                audit._require(
                    len(spans) < limits.max_ast_nodes, "captured span population budget exceeded"
                )
                spans.append(_span(node["span"], raw))
            for key, value in node.items():
                if key != "span":
                    walk(value, depth + 1)
        elif type(node) is list:
            for value in node:
                walk(value, depth + 1)

    walk(captured)
    if tree is None:
        audit._require(
            not captured["references"] and not captured["symbols"],
            "failed syntax cannot have successful symbol/reference population",
        )
        return {
            "syntax_disposition": "parse_failed",
            "normalized_ast_sha256": None,
            "template_ast_sha256": None,
            "dependency_paths": [],
            "reference_span_count": 0,
        }
    nodes = []
    for node in ast.walk(tree):
        audit._require(
            len(nodes) < limits.max_ast_nodes,
            "independent syntax node budget exceeded before allocation",
        )
        nodes.append(node)
    audit._require(
        len(nodes) <= limits.max_ast_nodes and member["parse_status"] == "ok",
        "bounded successful syntax population required",
    )
    lines = raw.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))

    def node_span(node):
        return offsets[node.lineno - 1] + node.col_offset, offsets[
            node.end_lineno - 1
        ] + node.end_col_offset

    expected_refs = sorted(
        (node.id, *node_span(node)) for node in nodes if isinstance(node, ast.Name)
    )
    expected_refs += [
        (node.func.id, *node_span(node.func))
        for node in nodes
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    actual_refs = sorted((ref["name"], *_span(ref["span"], raw)) for ref in captured["references"])
    audit._require(
        actual_refs == sorted(expected_refs),
        "captured AST reference population/spans differ from independent syntax",
    )
    expected_symbols = sorted(
        ("function", n.name, *node_span(n))
        for n in nodes
        if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
    )
    expected_symbols += sorted(
        ("parameter", n.arg, *node_span(n)) for n in nodes if isinstance(n, ast.arg)
    )
    actual_symbols = sorted(
        (s["kind"], s["name"], *_span(s["span"], raw)) for s in captured["symbols"]
    )
    audit._require(
        sorted(expected_symbols) == actual_symbols,
        "captured AST symbol population/spans differ from independent syntax",
    )
    dependencies = sorted(
        {
            n.module.split(".")[0] + ".py"
            for n in nodes
            if isinstance(n, ast.ImportFrom) and n.module
        }
        | {
            a.name.split(".")[0] + ".py"
            for n in nodes
            if isinstance(n, ast.Import)
            for a in n.names
        }
    )
    template = copy.deepcopy(tree)
    for node in ast.walk(template):
        if isinstance(node, ast.Constant):
            node.value = "constant_type:" + type(node.value).__name__
    return {
        "syntax_disposition": "parsed",
        "normalized_ast_sha256": audit._sha(ast.dump(tree, include_attributes=False).encode()),
        "template_ast_sha256": audit._sha(ast.dump(template, include_attributes=False).encode()),
        "dependency_paths": dependencies,
        "reference_span_count": len(actual_refs),
    }


def _lineages(bodies, root, members, sources, limits):
    lineages = []
    for version in root["model"]["ancestry"]:
        matching = [
            value
            for value in bodies.values()
            if type(value) is dict
            and value.get("schema") == "codebase-source-feature-training@1"
            and value.get("version_id") == version["version_id"]
        ]
        audit._require(
            len(matching) == 1,
            "exact retained lineage envelope for each declared ancestor required",
        )
        envelope = matching[0]
        audit._require(
            _same(envelope["head"], root["head"])
            and envelope["training_performed_during_load"] is False
            and envelope["state_sha256"]
            == (
                root["model"]["state_sha256"]
                if envelope["version_id"] == root["model"]["version_id"]
                else envelope["state_sha256"]
            ),
            "lineage captured head or load claim differs",
        )
        _authority(envelope["authority"])
        audit._require(
            type(envelope["report_json"]) is str, "retained training source report string required"
        )
        report = _json(envelope["report_json"].encode(), limits)
        provenance = audit._closed(
            report["codebase_provenance"],
            audit.NATIVE_PROVENANCE_FIELDS,
            "retained training source provenance",
        )
        audit._require(
            _same(provenance["head"], root["head"])
            and provenance["parent_version_id"] == envelope["parent_version_id"],
            "training source report lineage/head differs",
        )
        selections = provenance["selections"]
        audit._require(
            type(selections) is list and len(selections) <= limits.max_lineage_targets,
            "training selection population budget exceeded",
        )
        roles = {}
        for selection in selections:
            audit._closed(selection, {"path", "role", "contracts"}, "declared source selection")
            path, role = selection["path"], selection["role"]
            audit._require(
                path in members
                and path not in roles
                and role in {"train", "tune", "canary"}
                and selection["contracts"] == [],
                "unique explicit cohort source role required",
            )
            roles[path] = role
        observations = []
        for batch, role in (
            ("training_targets", "train"),
            ("tuning_targets", "tune"),
            ("canary_targets", "canary"),
            ("replay_targets", "replay"),
        ):
            values = provenance[batch]
            audit._require(
                type(values) is list and len(values) <= limits.max_lineage_targets,
                "training target selection budget exceeded",
            )
            seen = set()
            for value in values:
                details = value["validation"][0]["details"]
                binding = details["source_binding"]
                path = binding["path"]
                audit._require(
                    path in members
                    and path not in seen
                    and roles.get(path) == ("train" if role == "replay" else role),
                    "target path differs from independent declared selection role",
                )
                seen.add(path)
                member, raw = members[path], sources.get(path)
                audit._require(
                    raw is not None
                    and details["source_bytes_hex"] == raw.hex()
                    and binding["content_sha256"] == audit._sha(raw)
                    and binding["source_cid"] == member["source_cid"]
                    and binding["ast_cid"] == member["ast_cid"]
                    and binding["source_key"] == member["source_key"]
                    and _same(binding["head"], root["head"]),
                    "training target exact retained source/AST/head binding differs",
                )
                observations.append(
                    {
                        "path": path,
                        "role": role,
                        "source_sha256": audit._sha(raw),
                        "recorded_target_source_digest": value["source_digest"],
                    }
                )
            if role != "replay":
                audit._require(
                    seen == {p for p, r in roles.items() if r == role},
                    "declared target role population incomplete",
                )
        ancestral = provenance["ancestral_training"]
        audit._require(
            type(ancestral) is list and len(ancestral) <= limits.max_lineage_targets,
            "ancestral exposure budget exceeded",
        )
        for row in ancestral:
            audit._closed(
                row,
                {"path", "repository_id", "source_digest"},
                "declared ancestral source exposure",
            )
            audit._require(
                row["path"] in sources
                and row["repository_id"] == root["head"]["repository_id"]
                and row["source_digest"] == audit._sha(sources[row["path"]]),
                "ancestral source exposure raw binding differs",
            )
        lineages.append(
            {
                "version_id": envelope["version_id"],
                "parent_version_id": envelope["parent_version_id"],
                "selections": selections,
                "target_observations": observations,
                "ancestral_training_claims": ancestral,
            }
        )
    by_version = {x["version_id"]: x for x in lineages}
    audit._require(
        len(by_version) == len(lineages) == 2, "closed two-generation inherited lineage required"
    )
    for lineage in lineages:
        parent = lineage["parent_version_id"]
        if parent is not None:
            audit._require(
                parent in by_version and parent != lineage["version_id"],
                "declared parent lineage missing/cyclic",
            )
            expected = sorted(
                {
                    (r["path"], r["source_sha256"])
                    for r in by_version[parent]["target_observations"]
                    if r["role"] == "train"
                }
            )
            actual = sorted(
                (r["path"], r["source_digest"]) for r in lineage["ancestral_training_claims"]
            )
            audit._require(
                expected == actual,
                "declared ancestral training differs from retained parent selection",
            )
        else:
            audit._require(
                not lineage["ancestral_training_claims"],
                "root cannot claim unseen retained ancestry",
            )
    return lineages


def _analyse(result, records, raw_bodies, limits):
    audit._require(
        result["schema"] == "codebase-inventory-resume-native-qualification@1",
        "retained native result schema required",
    )
    audit._require(
        _count(result["inherited_actual_setup_epochs"], 2, "inherited setup epochs") == 2
        and _count(result["new_scan_pages_created"], 0, "new scan pages") == 0
        and _count(result["scan_reuse"]["new_fitting_epochs"], 0, "new fitting epochs") == 0,
        "closed inherited setup/new work accounting differs",
    )
    kinds = {r["cid"]: r["kind"] for r in records}
    audit._require(
        len(kinds) == len(records) and set(kinds) == set(raw_bodies),
        "exact selected body population required",
    )
    bodies = {
        cid: _json(raw, limits) for cid, raw in raw_bodies.items() if kinds[cid] == "structured"
    }
    selectors = {r["role"]: r["cid"] for r in records if r["role"] != "captured_source_artifact"}
    audit._require(
        {"root", "completion", "optout-root", "optout-reference-page"} <= set(selectors),
        "closed root/completion/reference selectors required",
    )
    root, completion = bodies[selectors["root"]], bodies[selectors["completion"]]
    audit._require(
        root["schema"] == "codebase-inventory-resume-root@1"
        and completion["schema"] == "codebase-inventory-resume-completion@1",
        "completed retained scan schemas required",
    )
    _authority(root["authority"])
    _authority(completion["authority"])
    audit._require(
        _same(root["head"], result["head"])
        and root["model"]["version_id"] == result["selected_version_id"]
        and result["scan_root_cid"] == selectors["root"]
        and result["completed_scan_cid"] == selectors["completion"],
        "native/root/completion identity differs",
    )
    population = root["members"]
    audit._require(
        type(population) is list and 0 < len(population) <= limits.max_members,
        "bounded nonempty source membership required",
    )
    members = {}
    for member in population:
        audit._closed(member, MEMBER_FIELDS, "sealed source inventory member")
        path = audit._text(member["path"], "source path", 512)
        audit._require(
            path not in members
            and not Path(path).is_absolute()
            and ".." not in Path(path).parts
            and path.encode().hex() == member["raw_path_hex"]
            and member["source_key"] == "raw:" + member["raw_path_hex"],
            "unique exact UTF8 source membership key required",
        )
        _count(member["source_size_bytes"], limits.max_file_bytes, "source declared length")
        audit._require(
            member["parse_status"] in {"ok", "failed", "opaque", "unindexed"},
            "closed source parse disposition required",
        )
        members[path] = member
    audit._require(
        list(members) == sorted(members, key=lambda p: bytes.fromhex(members[p]["raw_path_hex"])),
        "sealed membership order differs",
    )
    snapshot = bodies.get(root["head"]["manifest_cid"])
    audit._require(
        snapshot is not None
        and snapshot["schema"] == "codebase-ir-structural-manifest@1"
        and snapshot["ast_revision_id"] == root["head"]["ast_revision_id"]
        and snapshot["snapshot"]["snapshot_cid"] == root["head"]["snapshot_cid"],
        "captured structural snapshot head differs",
    )
    audit._require(snapshot["authority"] == "structural_only", "captured snapshot must retain structural-only scope")
    units = {u["source_key"]: u for u in snapshot["units"]}
    entries = {e["entry_cid"]: e for e in snapshot["snapshot"]["entries"]}
    audit._require(
        len(units)
        == len(snapshot["units"])
        == len(entries)
        == len(snapshot["snapshot"]["entries"])
        == len(members),
        "exact snapshot entry/unit populations required",
    )
    sources, rows = {}, []
    for path, member in members.items():
        unit = units.get(member["source_key"])
        entry = entries.get(member["entry_cid"])
        audit._require(
            unit is not None
            and entry is not None
            and unit["ast_cid"] == member["ast_cid"]
            and unit["entry_cid"] == member["entry_cid"]
            and unit["parse_status"] == member["parse_status"]
            and all(
                entry[k] == member[k]
                for k in ("path", "raw_path_hex", "source_cid", "opaque_reason")
            )
            and entry["size_bytes"] == member["source_size_bytes"],
            "sealed member/snapshot unit/entry correspondence differs",
        )
        raw = raw_bodies.get(member["source_cid"])
        captured = bodies.get(member["ast_cid"])
        if raw is not None:
            audit._require(_cid(raw, "source") == member["source_cid"], "exact source CID mismatch")
            sources[path] = raw
            syntax = _syntax(member, raw, captured, root["head"], limits)
        else:
            audit._require(
                member["parse_status"] == "opaque"
                and member["opaque_reason"] in {"undecodable", "oversized"}
                and captured is None,
                "unexplained missing source/AST body",
            )
            syntax = {
                "syntax_disposition": "unavailable_opaque_source",
                "normalized_ast_sha256": None,
                "template_ast_sha256": None,
                "dependency_paths": [],
                "reference_span_count": 0,
            }
        rows.append(
            {
                **member,
                "source_sha256": audit._sha(raw) if raw is not None else None,
                "source_body_available": raw is not None,
                "ast_record_available": captured is not None,
                **syntax,
            }
        )
    page_roles = sorted(
        (r for r in selectors if r.startswith("page-")), key=lambda x: int(x.split("-")[1])
    )
    audit._require(
        0 < len(page_roles) <= limits.max_pages
        and page_roles == [f"page-{i:02d}" for i in range(1, len(page_roles) + 1)],
        "complete contiguous page role population required",
    )
    pages, offset, previous, counts, inferred = [], 0, None, Counter(), 0
    for role in page_roles:
        cid = selectors[role]
        page = _json(raw_bodies[cid], limits)
        audit._require(
            page["schema"] == "codebase-inventory-resume-page@1"
            and page["root_cid"] == selectors["root"]
            and page["previous_page_cid"] == previous
            and page["start"] == offset
            and type(page["start"]) is type(page["end"]) is int
            and page["total_entries"] == len(rows)
            and page["head_cid"] == root["head_cid"]
            and page["membership_cid"] == root["membership_cid"]
            and page["model_artifact_cid"] == root["model"]["artifact_cid"],
            "retained page continuity/root/model membership differs",
        )
        _authority(page["authority"])
        audit._require(
            type(page["entries"]) is list
            and 0 < len(page["entries"]) <= root["limits"]["page_entries"]
            and page["end"] == offset + len(page["entries"]) <= len(rows),
            "exact bounded page entry population required",
        )
        pcounts, selected_rows = (
            Counter(),
            page["inference"]["rows"] if page["inference"] is not None else [],
        )
        indices = []
        for index, entry in enumerate(page["entries"], start=offset):
            row = rows[index]
            audit._require(
                type(entry["member_index"]) is int
                and entry["member_index"] == index
                and entry["source_key"] == row["source_key"]
                and entry["entry_cid"] == row["entry_cid"]
                and entry["disposition"] in DISPOSITIONS,
                "paged disposition exact member join differs",
            )
            disposition = entry["disposition"]
            pcounts[disposition] += 1
            expected_static = {
                "opaque": "opaque",
                "failed": "parse_failed",
                "unindexed": "unindexed",
            }.get(row["parse_status"])
            audit._require(
                (
                    expected_static is None
                    and disposition not in {"opaque", "parse_failed", "unindexed"}
                )
                or disposition == expected_static,
                "source parse/disposition category differs",
            )
            if disposition == "inferred":
                ix = entry["inference_index"]
                audit._require(
                    type(ix) is int
                    and ix == len(indices)
                    and ix < len(selected_rows)
                    and selected_rows[ix]["source_digest"] == entry["source_digest"],
                    "exact page inference row membership differs",
                )
                audit._digest(entry["source_digest"], "recorded target source digest")
                audit._digest(entry["target_sha256"], "recorded target SHA")
                indices.append(ix)
            else:
                audit._require(
                    entry["inference_index"] is None,
                    "noninferred member cannot claim numerical row",
                )
            row.update(
                {
                    "disposition": disposition,
                    "recorded_reason": entry["reason"],
                    "page_cid": cid,
                    "recorded_target_sha256": entry["target_sha256"],
                    "recorded_target_source_digest": entry["source_digest"],
                }
            )
        audit._require(
            len(indices) == len(selected_rows)
            and page["coverage"]
            == {
                "dispositions": dict(pcounts),
                "inferred_rows": len(indices),
                "inventory_entries": len(page["entries"]),
            },
            "independently counted page coverage differs",
        )
        counts.update(pcounts)
        inferred += len(indices)
        offset = page["end"]
        previous = cid
        pages.append(
            {
                "cid": cid,
                "membership_cid": page["page_membership_cid"],
                "start": page["start"],
                "end": offset,
                "dispositions": dict(pcounts),
                "inferred_rows": len(indices),
            }
        )
    coverage = {
        "dispositions": dict(counts),
        "inferred_rows": inferred,
        "inventory_entries": len(rows),
        "pages": len(pages),
    }
    completion_pages = [
        {
            "page_cid": p["cid"],
            **{
                k: p[k] for k in ("membership_cid", "start", "end", "dispositions", "inferred_rows")
            },
        }
        for p in pages
    ]
    audit._require(
        offset == len(rows)
        and _same(completion["coverage"], coverage)
        and _same(result["scan_coverage"], coverage)
        and completion["root_cid"] == selectors["root"]
        and _same(completion["pages"], completion_pages)
        and completion["head_cid"] == root["head_cid"]
        and completion["membership_cid"] == root["membership_cid"]
        and completion["model_artifact_cid"] == root["model"]["artifact_cid"],
        "final complete population/coverage differs",
    )
    lineages = _lineages(bodies, root, members, sources, limits)
    exposure = defaultdict(set)
    for lineage in lineages:
        for row in lineage["target_observations"]:
            exposure[row["path"]].add("train" if row["role"] == "replay" else row["role"])
    grouped = defaultdict(list)
    templates = defaultdict(list)
    for row in rows:
        row["declared_exposure_roles"] = sorted(exposure[row["path"]])
        row["exposure_disposition"] = (
            "declared_in_retained_lineage"
            if exposure[row["path"]]
            else "not_selected_in_retained_lineage_pretraining_unknown"
        )
        if row["normalized_ast_sha256"]:
            grouped[row["normalized_ast_sha256"]].append(row["path"])
            templates[row["template_ast_sha256"]].append(row["path"])
    groups = [
        {
            "normalized_ast_sha256": key,
            "paths": paths,
            "declared_exposure_roles": sorted({r for p in paths for r in exposure[p]}),
        }
        for key, paths in sorted(grouped.items())
    ]
    clones = [g for g in groups if len(g["paths"]) > 1]
    coupled = [g for g in clones if g["declared_exposure_roles"]]
    dependencies = [
        {"path": row["path"], "dependency_path": path, "in_cohort": path in members}
        for row in rows
        for path in row["dependency_paths"]
    ]
    return {
        "inventory_member_count": len(rows),
        "page_count": len(pages),
        "disposition_counts": dict(counts),
        "inferred_row_count": inferred,
        "source_artifact_body_count": sum(r["role"] == "captured_source_artifact" for r in records),
        "source_bytes_available_member_count": len(sources),
        "ast_record_available_member_count": sum(r["ast_record_available"] for r in rows),
        "normalized_ast_group_count": len(groups),
        "clone_group_count": len(clones),
        "normalized_ast_groups": groups,
        "clone_groups_with_declared_exposure": coupled,
        "template_groups": [
            {
                "template_ast_sha256": k,
                "paths": v,
                "scope": "syntactic_constant_type_mask_only_not_semantic_equivalence",
            }
            for k, v in sorted(templates.items())
        ],
        "source_missing_members": [
            {"path": r["path"], "source_cid": r["source_cid"], "opaque_reason": r["opaque_reason"]}
            for r in rows
            if not r["source_body_available"]
        ],
        "dependency_edges": dependencies,
        "members": rows,
        "pages": pages,
        "retained_lineage_selection_ledger": lineages,
        "declared_training_paths": sorted(p for p, roles in exposure.items() if "train" in roles),
        "declared_tuning_paths": sorted(p for p, roles in exposure.items() if "tune" in roles),
        "declared_canary_paths": sorted(p for p, roles in exposure.items() if "canary" in roles),
        "recorded_inherited_setup_epochs": result["inherited_actual_setup_epochs"],
        "recorded_new_scan_pages": result["new_scan_pages_created"],
        "recorded_new_fitting_epochs": result["scan_reuse"]["new_fitting_epochs"],
        "captured_source_head": root["head"],
        "captured_source_head_sha256": audit._sha(audit._canonical(root["head"])),
        "recorded_model_ancestry_ids": [v["version_id"] for v in root["model"]["ancestry"]],
        "retained_inventory_root_cid": selectors["root"],
        "retained_completion_cid": selectors["completion"],
        "revision_groups": [
            {
                "repository_id": root["head"]["repository_id"],
                "snapshot_cid": root["head"]["snapshot_cid"],
                "paths": list(members),
                "scope": "one_captured_revision_no_independent_revision_population",
            }
        ],
    }


def _output_population(output, retained, limits):
    audit._require(
        output.resolve(strict=True) == output
        and not any(p.is_symlink() for p in (output, *output.parents)),
        "canonical nonsymlink cohort output root required",
    )
    before = output.lstat()
    audit._require(stat.S_ISDIR(before.st_mode), "regular cohort output directory required")
    expected = {Path(r["retained_path"]).name: r for r in retained}
    audit._require(
        len(expected) == len(retained) <= limits.max_files
        and all(Path(r["retained_path"]).parent == output for r in retained),
        "exact flat copied population required",
    )
    for row in retained:
        if "path" in row:
            original = final.Capture.regular(Path(row["path"]), row["size_bytes"])
            audit._require(
                len(original) == row["size_bytes"] and audit._sha(original) == row["sha256"],
                "publication fence selected original drift",
            )
    found = set()
    with os.scandir(output) as entries:
        for entry in entries:
            audit._require(
                len(found) < len(expected) and entry.name in expected,
                "unexpected cohort output population",
            )
            row = expected[entry.name]
            state = entry.stat(follow_symlinks=False)
            audit._require(
                stat.S_ISREG(state.st_mode) and state.st_size == row["size_bytes"],
                "regular exact copied body required",
            )
            raw = final.Capture.regular(output / entry.name, row["size_bytes"])
            audit._require(audit._sha(raw) == row["sha256"], "late cohort copied body drift")
            found.add(entry.name)
    after = output.lstat()
    audit._require(
        found == set(expected)
        and output.resolve(strict=True) == output
        and stat.S_ISDIR(after.st_mode)
        and (before.st_dev, before.st_ino, before.st_mtime_ns, before.st_ctime_ns)
        == (after.st_dev, after.st_ino, after.st_mtime_ns, after.st_ctime_ns),
        "cohort root or final population drift",
    )


def evaluate(manifest: Path, output: Path, limits: Limits = DEFAULT_LIMITS):
    manifest, output = manifest.absolute(), output.absolute()
    audit._require(manifest.resolve(strict=True) == manifest, "canonical cohort manifest required")
    pins = native.Pins(limits)
    raw_manifest = pins.read(manifest, min(limits.max_manifest_bytes, limits.max_file_bytes))
    spec = audit._closed(
        _json(raw_manifest, limits), {"schema", *INPUT_ROLES}, "resumed cohort manifest"
    )
    audit._require(spec["schema"] == INPUT_SCHEMA, "closed resumed cohort input schema required")
    inputs = {}
    for role in INPUT_ROLES:
        audit._require(
            (spec[role]["sha256"], spec[role]["size_bytes"]) == FROZEN_PINS[role],
            "independently frozen native inputs required",
        )
        _, raw = pins.descriptor(spec[role])
        inputs[role] = _json(raw, limits)
    review, result = inputs["qualification_review"], inputs["native_result"]
    declaration = review["native_result"]
    audit._require(
        declaration["sha256"] == spec["native_result"]["sha256"]
        and declaration["bytes"] == spec["native_result"]["size_bytes"]
        and Path(spec["native_result"]["path"]).parts[-len(Path(declaration["path"]).parts) :]
        == Path(declaration["path"]).parts,
        "selected native result differs from public review declaration",
    )
    records = _selection(result, limits)
    directory = Path(spec["native_result"]["path"]).parent
    raw_bodies = {}
    for record in records:
        _, raw = pins.descriptor(
            {
                "path": str(directory / record["path"]),
                "sha256": record["sha256"],
                "size_bytes": record["size_bytes"],
            }
        )
        audit._require(
            _cid(raw, record["kind"]) == record["cid"], "selected source/scan CAS identity mismatch"
        )
        raw_bodies[record["cid"]] = raw
    lock_tool._preflight_output(output, sorted({p.parent for p in pins.files}))
    summary = _analyse(result, records, raw_bodies, limits)
    pins.recheck()
    output.mkdir(exist_ok=False)
    retained = []
    for index, (path, raw) in enumerate(pins.files.items()):
        copied = output / f"input-{index:03d}-{path.name}"
        copied.write_bytes(raw)
        audit._require(
            final.Capture.regular(copied, len(raw)) == raw, "retained cohort copy differs"
        )
        retained.append(
            {
                "path": str(path),
                "retained_path": str(copied),
                "sha256": audit._sha(raw),
                "size_bytes": len(raw),
            }
        )
    pins.recheck()
    for row in retained:
        audit._require(
            final.Capture.regular(Path(row["retained_path"]), row["size_bytes"])
            == pins.files[Path(row["path"])],
            "late retained cohort copy differs",
        )
    report = {
        "schema": REPORT_SCHEMA,
        "status": "passed",
        "profile": PROFILE,
        "scope": "retained_source_syntax_complete_scan_dispositions_and_declared_lineage_exposure_only",
        "manifest_sha256": audit._sha(raw_manifest),
        **{role + "_sha256": spec[role]["sha256"] for role in INPUT_ROLES},
        **dict.fromkeys(TRUE_FLAGS, True),
        **dict.fromkeys(FALSE_FLAGS, False),
        **summary,
        "input_files": retained,
        "captured_input_file_count": len(pins.files),
        "captured_input_bytes": pins.total,
        "additional_attempted_training_epochs": 0,
        "new_final_assignments": 0,
        "limits": asdict(limits),
        "limitations": [
            "Complete membership and dispositions do not establish training or evaluation coverage, independent splits, learned decoder quality or runtime semantics.",
            "All source-artifact CAS bodies are retained without modification. DBs, checkpoint bodies, .git, keys and undeclared repository bytes are never opened.",
            "Training selections and source bindings are declared retained lineage evidence; no numerical recipe, optimizer state or tensor is replayed.",
            "Normalized AST groups preserve syntax and literals. Template groups mask constant types only, with no semantic equivalence claim.",
            "Non-UTF8 source is absent from the selected closure and oversized source has no CID. Their recorded opaque disposition remains explicit.",
            "Target digests and numerical scan rows are retained claims. This audit does not rederive the native target recipe or evaluate model predictions.",
            "One captured revision and explicitly selected ancestral paths cannot establish complete pretraining exposure or heldout independence.",
        ],
    }
    _output_population(output, retained, limits)
    final._write(output / "resumed_cohort_audit.json", report)
    published = audit._canonical(report) + b"\n"
    audit._require(
        final.Capture.regular(output / "resumed_cohort_audit.json", limits.max_file_bytes)
        == published,
        "published cohort report differs",
    )
    _output_population(
        output,
        [
            *retained,
            {
                "retained_path": str(output / "resumed_cohort_audit.json"),
                "sha256": audit._sha(published),
                "size_bytes": len(published),
            },
        ],
        limits,
    )
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = evaluate(args.manifest, args.output)
    except (
        audit.AuditInputError,
        ValueError,
        OSError,
        KeyError,
        TypeError,
        OverflowError,
        RecursionError,
        UnicodeError,
    ) as exc:
        print(
            json.dumps(
                {
                    "schema": REPORT_SCHEMA,
                    "status": "refused",
                    "reason": str(exc),
                    "unknown_pretraining_exposure": True,
                    **dict.fromkeys(FALSE_FLAGS, False),
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 3
    print(
        json.dumps(
            {
                "status": report["status"],
                "inventory_members": report["inventory_member_count"],
                "inferred_rows": report["inferred_row_count"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
