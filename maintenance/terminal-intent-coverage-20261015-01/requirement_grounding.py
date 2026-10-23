"""Replay structural source facts and nominate clause anchors without entailment.

This module reads only inert caller supplied JSON/UTF-8.  It never opens a
repository, database, cache, or source module.  A complete historical manifest
and head can bind candidates; the native index owner must separately observe
current source before and after consuming them.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import PurePosixPath
import re

SCHEMA = "terminal-requirement-source-grounding@1"
FLAGS = {name: False for name in (
    "semantic_alignment_verified", "source_semantics_verified", "behavioral_satisfaction",
    "proof_authority", "execution_authority", "completion_authority", "mutation_authority",
    "omission_authority", "full_task_satisfaction", "source_to_model_equivalence",
    "convergence_proved", "contract_recall_verified")}
TASKS = frozenset(("headless-terminal", "feal-differential-cryptanalysis",
    "break-filter-js-from-html", "llm-inference-batching-scheduler"))
_OUTPUTS = {
    "headless-terminal": (("/app/headless_terminal.py", "HeadlessTerminal"),),
    "feal-differential-cryptanalysis": (("/app/attack.py", "attack"),),
    "break-filter-js-from-html": (("/app/out.html", None),),
    "llm-inference-batching-scheduler": (("/app/task_file/output_data/plan_b1.jsonl", None),
        ("/app/task_file/output_data/plan_b2.jsonl", None)),
}
_WORD = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")


class RequirementGroundingError(ValueError):
    """A supplied historical instruction/source binding did not replay."""


def _wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False).encode("ascii")


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def _require(condition, message):
    if not condition:
        raise RequirementGroundingError(message)


def _json(value):
    pending, count = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        count += 1
        _require(depth <= 64 and count <= 500_000, "bounded inert JSON required")
        if type(item) is dict:
            _require(all(type(k) is str for k in item), "exact JSON string keys required")
            pending.extend((v, depth + 1) for v in item.values())
        elif type(item) is list:
            pending.extend((v, depth + 1) for v in item)
        else:
            _require(type(item) in (str, int, float, bool, type(None)), "exact inert JSON values required")
    try:
        raw = _wire(value)
    except (TypeError, ValueError, RecursionError) as exc:
        raise RequirementGroundingError("finite inert JSON required") from exc
    _require(len(raw) <= 32 * 1024 * 1024, "bounded JSON envelope required")
    return json.loads(raw)


def _path(value):
    _require(type(value) is str and 0 < len(value) <= 4096, "canonical source path required")
    p = PurePosixPath(value)
    _require(not p.is_absolute() and str(p) == value and ".." not in p.parts
        and ".git" not in p.parts and "\\" not in value and not any(ord(c) < 32 for c in value),
        "canonical source path required")
    return value


def _instructions(inventories, corpus):
    from clause_inventory import validate_instruction_inventory
    _require(type(corpus) is dict and type(corpus.get("tasks")) is list,
        "complete explicit corpus required")
    tasks = {t["task_id"]: t for t in corpus["tasks"]}
    _require(len(tasks) == len(corpus["tasks"]) == 4 and set(tasks) == TASKS,
        "exact four-task instruction scope required")
    _require(type(inventories) is list and len(inventories) == 4,
        "exact four instruction inventories required")
    lookup = {}
    unit_fields = {"unit_id", "start_char", "end_char", "start_byte", "end_byte", "text",
        "sha256", "classification", "reason", "candidate_document_ids"}
    for report in inventories:
        _require(type(report) is dict and report.get("schema") == "terminal-instruction-clause-inventory@1",
            "native companion clause inventory schema required")
        task = report.get("task_id")
        _require(task in tasks and task not in lookup, "unique task-scoped inventory required")
        instruction = report.get("instruction")
        _require(type(instruction) is dict and set(instruction) == {"text", "bytes", "characters", "sha256"},
            "complete original instruction identity required")
        text = instruction["text"]
        _require(type(text) is str and instruction["sha256"] == _sha(text.encode("utf-8"))
            and instruction["bytes"] == len(text.encode("utf-8")) and instruction["characters"] == len(text),
            "instruction UTF8 identity differs")
        pin = tasks[task]["instruction"]
        _require(pin["sha256"] == instruction["sha256"] and pin["bytes"] == instruction["bytes"],
            "instruction differs from corpus task identity")
        try:
            validate_instruction_inventory(report, task_id=task, instruction=text.encode("utf-8"))
        except (TypeError, ValueError, KeyError) as exc:
            raise RequirementGroundingError("clause inventory native replay differs") from exc
        units = report.get("units")
        _require(type(units) is list and len(units) <= 4096 and len(units) == len(text.splitlines(keepends=True)),
            "complete source line inventory required")
        cursor = 0
        for ordinal, (unit, line) in enumerate(zip(units, text.splitlines(keepends=True))):
            _require(type(unit) is dict and set(unit) == unit_fields, "closed instruction unit required")
            expected = {"start_char": cursor, "end_char": cursor + len(line),
                "start_byte": len(text[:cursor].encode("utf-8")),
                "end_byte": len(text[:cursor + len(line)].encode("utf-8")),
                "text": line, "sha256": _sha(line.encode("utf-8"))}
            _require(all(type(unit[k]) is type(v) and unit[k] == v for k, v in expected.items()),
                "instruction unit is not the exact original UTF8 slice")
            _require(unit["unit_id"] == "instruction-line:" + task + ":" + str(ordinal + 1),
                "instruction unit task identity differs")
            _require(type(unit["candidate_document_ids"]) is list
                and all(type(v) is str for v in unit["candidate_document_ids"]), "inert candidate references required")
            cursor += len(line)
        _require(len({u["unit_id"] for u in units}) == len(units), "duplicate instruction unit identity")
        _require(cursor == len(text), "full instruction source accounting required")
        lookup[task] = report
    _require(set(lookup) == set(tasks), "complete task inventory required")
    return tasks, lookup


def _quote(raw, span):
    left, right = span["start_byte"], span["end_byte"]
    _require(type(left) is int and type(right) is int and 0 <= left <= right <= len(raw),
        "native source citation lies outside its exact bytes")
    try:
        text = raw[left:right].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RequirementGroundingError("native quote must preserve UTF8 boundaries") from exc
    return {"start_byte": left, "end_byte": right, "span_unit": "utf8_bytes",
        "text": text, "sha256": _sha(raw[left:right])}


def _source_replay(source_records, manifest, tasks):
    from ipfs_datasets_py.logic.software_contracts.content import cid_for_bytes
    from ipfs_datasets_py.logic.software_contracts.python_frontend import PythonASTExtractor
    from ipfs_datasets_py.logic.software_contracts.semantic_index.scanner import RepositoryScanner

    _require(type(source_records) is list and len(source_records) == 5, "exact five-source inventory required")
    pins = {}
    task_paths = {}
    for task_id, task in tasks.items():
        paths = []
        for row in task["sources"]:
            path = _path(row["path"])
            _require(path.startswith(task_id + "/environment/") and path not in pins,
                "source task scope differs or duplicates")
            pins[path] = row
            paths.append(path)
        task_paths[task_id] = frozenset(paths)
    entries = {entry.path: entry for entry in manifest.snapshot.entries}
    units = {u.source_key: u for u in manifest.units}
    _require(len(entries) == len(pins) == 5 and set(entries) == set(pins),
        "complete native and corpus source inventory must be a bijection")
    records, raw_sources, asts, bindings = {}, {}, {}, []
    for row in source_records:
        _require(type(row) is dict and set(row) == {"path", "sha256", "source_text"},
            "closed exact source record required")
        path = _path(row["path"])
        _require(path in pins and path not in records, "unique admitted source path required")
        text = row["source_text"]
        _require(type(text) is str, "exact UTF8 source text required")
        raw = text.encode("utf-8")
        _require(0 < len(raw) <= 8192 and _sha(raw) == row["sha256"] == pins[path]["sha256"]
            and len(raw) == pins[path]["bytes"], "source bytes differ from exact corpus identity")
        entry, unit = entries[path], units[entries[path].source_key]
        _require(not entry.is_opaque and entry.source_cid == cid_for_bytes(raw) and entry.size_bytes == len(raw)
            and unit.parse_status == "ok" and unit.ast_cid is not None,
            "native snapshot/AST source binding differs")
        ast = PythonASTExtractor().extract(raw, path=path, repository_id=manifest.snapshot.repository_id,
            revision="snapshot:" + manifest.snapshot.snapshot_cid,
            repository_tree_cid=manifest.snapshot.snapshot_cid)
        _require(ast.cid == unit.ast_cid, "exact source AST/effect/interface extraction replay differs")
        records[path], raw_sources[entry.source_key], asts[path] = row, raw, ast
        bindings.append({"path": path, "sha256": row["sha256"], "bytes": len(raw),
            "source_cid": entry.source_cid, "entry_cid": entry.entry_cid, "ast_cid": unit.ast_cid,
            "parse_status": unit.parse_status})
    _require(set(records) == set(entries), "source records must cover the complete native inventory")
    replay = RepositoryScanner(repository_id=manifest.snapshot.repository_id).scan_snapshot(manifest.snapshot, raw_sources)
    _require(_wire(replay.to_dict()) == _wire(manifest.semantic_state.to_dict()),
        "exact source semantic symbol/edge extraction replay differs")
    return records, asts, sorted(bindings, key=lambda r: r["path"]), task_paths


def _catalog(records, asts, manifest):
    """Each original frontend row gets an exact citation; no semantic resolver."""
    catalog = []
    for path, ast in sorted(asts.items()):
        raw = records[path]["source_text"].encode("utf-8")
        for family, rows in (("symbol", ast.symbols), ("effect", ast.effects), ("call", ast.calls),
                ("interface", tuple(s for s in ast.symbols if s.signature is not None))):
            for row in rows:
                body = row.to_dict()
                name = body.get("name") or body.get("subject") or body.get("callee_name") or ""
                projection = {"family": family, "path": path,
                    "source_sha256": records[path]["sha256"], "ast_cid": ast.cid,
                    "native_record": body, "citation": _quote(raw, body["span"]),
                    "lexical_names": sorted(set(_WORD.findall(name)))}
                projection["semantic_symbol_bindings"] = [
                    {"stable_id": s.stable_id, "version_cid": s.version_cid,
                        "qualified_name": s.qualified_name, "kind": s.kind}
                    for s in manifest.semantic_state.symbols
                    if family in {"symbol", "interface"} and s.module_path == path
                    and s.qualified_name == body.get("qualified_name")]
                projection["projection_id"] = "source-projection:" + _sha(_wire(projection))
                catalog.append(projection)
    return sorted(catalog, key=lambda r: (r["path"], r["family"], r["projection_id"]))


def build_requirement_grounding(*, inventories: list, source_records: list,
        structural_manifest: dict, head: dict, corpus: dict) -> dict:
    """Replay all source facts and nominate task-local lexical anchors per unit."""
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    from ipfs_datasets_py.logic.software_contracts.codebase_ir import CodebaseIRManifest

    inventories, source_records = _json(inventories), _json(source_records)
    corpus, structural_manifest, head = _json(corpus), _json(structural_manifest), _json(head)
    tasks, inventories = _instructions(inventories, corpus)
    try:
        manifest = CodebaseIRManifest.from_dict(structural_manifest)
        native_head = CodebaseHead.from_dict(head)
    except (TypeError, ValueError, KeyError) as exc:
        raise RequirementGroundingError("invalid native manifest/head") from exc
    _require(native_head.manifest_cid == manifest.cid
        and native_head.repository_id == manifest.snapshot.repository_id
        and native_head.snapshot_cid == manifest.snapshot.snapshot_cid
        and native_head.ast_revision_id == manifest.ast_revision_id,
        "native head does not bind the complete structural manifest")
    records, asts, bindings, task_paths = _source_replay(source_records, manifest, tasks)
    catalog = _catalog(records, asts, manifest)
    task_reports = []
    for task_id in sorted(tasks):
        inventory = inventories[task_id]
        selected = [c for c in catalog if c["path"] in task_paths[task_id]]
        units = []
        for unit in inventory["units"]:
            words = set(_WORD.findall(unit["text"]))
            anchors = []
            for candidate in selected:
                matched = sorted(words.intersection(candidate["lexical_names"]))
                if matched:
                    anchors.append({"projection_id": candidate["projection_id"],
                        "match_kind": "exact_case_sensitive_identifier_overlap", "matched_identifiers": matched})
            files = []
            for path in sorted(task_paths[task_id]):
                alias = "/app/" + path.split("/environment/", 1)[1]
                if alias in unit["text"] or PurePosixPath(path).name in unit["text"]:
                    files.append({"source_path": path, "app_path_alias": alias,
                        "match_kind": "authored_environment_prefix_map_and_exact_path_text"})
            units.append({"unit_id": unit["unit_id"], "instruction_sha256": inventory["instruction"]["sha256"],
                "source_unit_sha256": unit["sha256"], "source_unit_start_byte": unit["start_byte"],
                "source_unit_end_byte": unit["end_byte"], "projection_anchors": anchors, "file_anchors": files,
                "status": "candidate_lexical_anchors" if anchors or files else "no_source_anchor",
                "no_anchor_reason": None if anchors or files else "no_exact_task_local_identifier_or_source_path_match",
                "requirement_resolved": False, **FLAGS})
        outputs = []
        for app_path, symbol in _OUTPUTS[task_id]:
            _require(app_path in inventory["instruction"]["text"], "authored output nomination is absent from original instruction")
            source_path = task_id + "/environment/" + app_path.removeprefix("/app/")
            found = [c["projection_id"] for c in selected if c["family"] == "symbol"
                and c["native_record"]["name"] == symbol] if symbol is not None else []
            outputs.append({"app_path": app_path, "authored_task_relative_path": source_path,
                "symbol_name": symbol, "path_in_admitted_inventory": source_path in records,
                "matching_symbol_projection_ids": found, "absence_scope": "admitted_source_inventory_only",
                "interpretation": "manually_authored_output_candidate", "behavioral_satisfaction": False})
        task_reports.append({"task_id": task_id, "instruction_sha256": inventory["instruction"]["sha256"],
            "clause_inventory_sha256": _sha(_wire(inventory)), "source_paths": sorted(task_paths[task_id]),
            "units": units, "authored_output_candidates": outputs,
            "all_instruction_units_retained": True, "resolved_requirement_ids": [], **FLAGS})
    result = {"schema": SCHEMA, "head": head, "structural_manifest_cid": manifest.cid,
        "snapshot_cid": manifest.snapshot.snapshot_cid, "semantic_state_cid": manifest.semantic_state.state_cid,
        "source_bindings": bindings, "source_projections": catalog, "tasks": task_reports,
        "query_method": "pure_in_memory_exact_native_frontend_replay_then_task_scoped_lexical_join",
        "native_source_ast_effect_interface_replay": True, "native_semantic_symbol_edge_replay": True,
        "task_scope_bijection_verified": True, "source_body_executed": False,
        "database_accessed": False, "provider_calls": 0, "training_executed": False,
        "current_head_verified_here": False, "native_generation_freshness_verified_here": False,
        "caller_requires_current_head_observation": True,
        "required_observation_api": "RepositoryCodebaseIndex.observe_current",
        "nominations_are_entailment": False, "absence_proves_repository_wide_absence": False,
        "resolved_requirement_ids": [], "removed_task_ids": [], **FLAGS}
    result["report_sha256"] = _sha(_wire(result))
    return _json(result)


def validate_requirement_grounding(report, *, inventories, source_records,
        structural_manifest, head, corpus):
    """Rebuild candidate evidence; a rehashed serialized report grants no trust."""
    supplied = _json(report)
    expected = build_requirement_grounding(inventories=inventories, source_records=source_records,
        structural_manifest=structural_manifest, head=head, corpus=corpus)
    _require(_wire(supplied) == _wire(expected), "requirement grounding report exact replay differs")
    return supplied


__all__ = ["SCHEMA", "RequirementGroundingError", "build_requirement_grounding", "validate_requirement_grounding"]
