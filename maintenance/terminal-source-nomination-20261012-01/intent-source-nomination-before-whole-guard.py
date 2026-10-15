"""Pure, bounded requirement-to-source nominations with no behavioral authority.

The caller supplies independently admitted task identities, captured public
source and an independently pinned review. Native replay verifies structural
joins only. It neither authenticates that review nor discovers a vulnerability.
"""
from __future__ import annotations

import ast
import hashlib
import io
import json
import math
from pathlib import PurePosixPath
import re

SCHEMA = "supervisor-intent-source-nomination@1"
REVIEW_SCHEMA = "supervisor-intent-source-nomination-review@1"
MAX_BYTES = 65536
MAX_SOURCE_BYTES = 2_000_000
MAX_SOURCE_POPULATION_BYTES = 128_000_000
MAX_PATHS = 64
MAX_SELECTORS = 256
MAX_JSON_NODES = 500_000
MAX_JSON_DEPTH = 48
BINDING_FIELDS = frozenset({"task_id", "task_cid", "task_revision", "repository_id", "tree_id",
    "native_tree_id", "native_forest_id", "coverage_id", "contract_cid", "ledger_sha256",
    "instruction_source_sha256", "index_id", "ast_index_id", "source_manifest_sha256"})
AUTHORITY_FIELDS = ("source_authentication_claimed", "review_authentication_claimed",
    "immutable_custody_claimed", "semantic_alignment_verified", "source_semantics_verified",
    "behavioral_satisfaction_verified", "proof_authority", "execution_authority",
    "mutation_authority", "completion_authority")
PRIVATE_PARTS = frozenset({".git", ".ssh", ".codex", "codex-auth", "credentials", "secrets", "state", "root",
    "owner-state", "owner-key", "private", "keys", "keyring"})
PRIVATE_NAMES = frozenset({"auth.json", "id_rsa", "id_ed25519", "token", "owner-token", "private-key", ".env"})
PRIVATE_SUFFIXES = frozenset({".duckdb", ".ducklake", ".sqlite", ".db", ".pem", ".key", ".p12", ".pfx"})


class IntentSourceNominationError(ValueError):
    """Static refusal of malformed or mismatched independent inputs."""


class IntentSourceNominationBoundsError(IntentSourceNominationError):
    """A complete inventory cannot fit the declared bound."""


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _json(value):
    pending, nodes = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        if depth > MAX_JSON_DEPTH or nodes > MAX_JSON_NODES:
            raise IntentSourceNominationBoundsError("JSON structure exceeds its bound")
        if type(item) is dict:
            if any(type(key) is not str for key in item):
                raise IntentSourceNominationError("JSON object keys must be strings")
            pending.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            pending.extend((child, depth + 1) for child in item)
        elif type(item) is float:
            if not math.isfinite(item):
                raise IntentSourceNominationError("finite JSON numbers required")
        elif type(item) not in {str, int, bool, type(None)}:
            raise IntentSourceNominationError("strict JSON types required")
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                          allow_nan=False).encode("utf-8", errors="strict")
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise IntentSourceNominationError("strict UTF-8 JSON required") from exc


def _decoded(value, maximum):
    if type(value) is dict:
        raw = _json(value)
        if len(raw) > maximum:
            raise IntentSourceNominationBoundsError("JSON input exceeds its byte bound")
        return json.loads(raw), raw
    if type(value) is str:
        try:
            value = value.encode("utf-8", errors="strict")
        except UnicodeError as exc:
            raise IntentSourceNominationError("strict UTF-8 JSON required") from exc
    if type(value) is not bytes:
        raise IntentSourceNominationError("JSON object or canonical wire required")
    if len(value) > maximum:
        raise IntentSourceNominationBoundsError("JSON input exceeds its byte bound")
    def pairs(items):
        result = {}
        for key, child in items:
            if key in result:
                raise IntentSourceNominationError("duplicate JSON key refused")
            result[key] = child
        return result
    try:
        parsed = json.loads(value.decode("utf-8", errors="strict"), object_pairs_hook=pairs,
                            parse_constant=lambda _: (_ for _ in ()).throw(
                                IntentSourceNominationError("finite JSON required")))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise IntentSourceNominationError("canonical JSON input required") from exc
    if type(parsed) is not dict or _json(parsed) != value:
        raise IntentSourceNominationError("canonical JSON object without trailing bytes required")
    return parsed, value


def _text(value, maximum=256):
    if (type(value) is not str or not value or value != value.strip()
            or any(char in value for char in "\n\r\x00")):
        raise IntentSourceNominationError("bounded nonempty identity required")
    try:
        raw = value.encode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise IntentSourceNominationError("strict UTF-8 identity required") from exc
    if len(raw) > maximum:
        raise IntentSourceNominationBoundsError("identity exceeds its bound")
    return value


def _digest(value):
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise IntentSourceNominationError("canonical digest required")
    return value


def _path(value):
    _text(value, 2048)
    path = PurePosixPath(value)
    if (not path.parts or path.is_absolute() or str(path) != value or ".." in path.parts
            or any(part.lower() in PRIVATE_PARTS for part in path.parts)
            or path.name.lower() in PRIVATE_NAMES or path.suffix.lower() in PRIVATE_SUFFIXES):
        raise IntentSourceNominationError("canonical public source path required")
    return value


def _definitions(source):
    found = {}
    class Visitor(ast.NodeVisitor):
        def __init__(self):
            self.scope = []
        def definition(self, node):
            name = ".".join([*self.scope, node.name])
            found.setdefault(name, []).append(node)
            self.scope.append(node.name)
            self.generic_visit(node)
            self.scope.pop()
        visit_ClassDef = definition
        visit_FunctionDef = definition
        visit_AsyncFunctionDef = definition
    try:
        Visitor().visit(ast.parse(source))
    except (SyntaxError, ValueError, RecursionError) as exc:
        raise IntentSourceNominationError("fresh Python definition census required") from exc
    return found


def _native_statements(ledger, requirement):
    """Retain exact native statements and their complete source references."""
    if requirement["representation"] != "native_statement":
        return [], []
    from ipfs_datasets_py.logic.intent_ir.canonicalize import canonical_intent_ir_bytes
    from ipfs_datasets_py.logic.intent_ir.decoder import decode_intent_ir
    report = ledger["source_report"]
    while report["schema"] == "source-document-autoencoder/v1":
        report = report.get("rich_intent") or report["intent"]
    candidate = next(item for item in report["candidates"]
                     if item["unit_id"] == requirement["source_unit_id"])
    if "candidate_intent_ir" in candidate:
        document = candidate["candidate_intent_ir"]
    else:
        unit = next(item for item in report["units"] if item["unit_id"] == candidate["unit_id"])
        document = unit["inference"]["logic"]["native_intent_ir"]
    native = decode_intent_ir(document)
    if (_sha(canonical_intent_ir_bytes(native)) != requirement["native_document_sha256"]
            or native.document_id != requirement["native_document_id"]):
        raise IntentSourceNominationError("native requirement document differs")
    by_id = {item.statement_id: item for item in native.statements}
    statements = [by_id[key] for key in requirement["statement_ids"]]
    references = {ref for item in statements for ref in item.source_ref_ids}
    return ([item.to_dict() for item in statements],
            [item.to_dict() for item in native.sources if item.ref_id in references])


def _source_span(source, node, row):
    raw = source.encode("utf-8")
    offsets = [0]
    for line in io.StringIO(source).readlines():
        offsets.append(offsets[-1] + len(line.encode("utf-8")))
    first = min([node.lineno, *[item.lineno for item in node.decorator_list]])
    last = node.end_lineno
    start, end = offsets[first - 1], offsets[last]
    return {"line_start": first, "line_end": last, "native_line_start": row.line_start,
        "native_line_end": row.line_end, "byte_start": start, "byte_end": end,
        "bytes": end - start, "sha256": _sha(raw[start:end])}


def build_intent_source_nomination(*, contract, source_text, task_id, task_cid, task_revision,
        repository_id, tree_id, snapshot, source_by_path, review=None,
        expected_review_sha256=None, max_bytes=MAX_BYTES):
    """Rebuild a complete inert nomination from independently supplied values.

    No filesystem is consulted. ``review`` must be accompanied by its external
    canonical-wire digest; neither a self-hash nor a review_ref authenticates
    review custody. All source-semantic and behavioral requirements stay residual.
    """
    if type(max_bytes) is not int or not 1024 <= max_bytes <= MAX_BYTES:
        raise IntentSourceNominationBoundsError("bounded exact integer output cap required")
    identities = {key: _text(value) for key, value in {
        "task_id": task_id, "task_cid": task_cid, "task_revision": task_revision,
        "repository_id": repository_id, "tree_id": tree_id}.items()}
    if type(source_text) is not str:
        raise IntentSourceNominationError("exact original instruction text required")
    try:
        instruction_raw = source_text.encode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise IntentSourceNominationError("strict UTF-8 instruction required") from exc
    if not instruction_raw or len(instruction_raw) > 4 * 1024 * 1024:
        raise IntentSourceNominationBoundsError("instruction exceeds its byte bound")
    if (review is None) != (expected_review_sha256 is None):
        raise IntentSourceNominationError("review and independent review digest required together")
    reviewed, review_raw = (None, None)
    if review is not None:
        _digest(expected_review_sha256)
        reviewed, review_raw = _decoded(review, MAX_BYTES)
        if _sha(review_raw) != expected_review_sha256:
            raise IntentSourceNominationError("independent review digest differs")
        if set(reviewed) != {"schema", "bindings", "review_ref", "selectors"} or reviewed["schema"] != REVIEW_SCHEMA:
            raise IntentSourceNominationError("closed source nomination review required")
        _text(reviewed["review_ref"])
        if type(reviewed["bindings"]) is not dict or set(reviewed["bindings"]) != BINDING_FIELDS:
            raise IntentSourceNominationError("closed review bindings required")
        if type(reviewed["selectors"]) is not list or len(reviewed["selectors"]) > MAX_SELECTORS:
            raise IntentSourceNominationBoundsError("bounded reviewed selector population required")
    canonical_input, _ = _decoded(contract, 4 * 1024 * 1024)
    from ..prompt.intent_plan_coverage import validate_intent_requirement_contract
    from ..core.multiformats_identity import cid_for_dag_json
    try:
        canonical = validate_intent_requirement_contract(canonical_input, source_text=source_text)
    except (ValueError, KeyError, TypeError) as exc:
        raise IntentSourceNominationError("exact source-bound native requirement contract required") from exc
    if type(source_by_path) is not dict or not 1 <= len(source_by_path) <= MAX_PATHS:
        raise IntentSourceNominationBoundsError("bounded complete source mapping required")
    if any(type(path) is not str for path in source_by_path):
        raise IntentSourceNominationError("source mapping keys must be paths")
    sources, source_manifest, total = {}, [], 0
    for path, source in sorted(source_by_path.items()):
        _path(path)
        if type(source) is not str:
            raise IntentSourceNominationError("strict source text required")
        try:
            raw = source.encode("utf-8", errors="strict")
        except UnicodeError as exc:
            raise IntentSourceNominationError("strict UTF-8 source required") from exc
        total += len(raw)
        if not raw or len(raw) > MAX_SOURCE_BYTES or total > MAX_SOURCE_POPULATION_BYTES:
            raise IntentSourceNominationBoundsError("source population exceeds its byte bound")
        if re.search(r"\r(?!\n)", source):
            raise IntentSourceNominationError("physical LF or CRLF source required")
        sources[path] = source
        source_manifest.append({"path": path, "sha256": _sha(raw), "bytes": len(raw)})
    from ..analysis.code_symbol_vector_index import CodeVectorIndexSnapshot, resolve_code_symbol_ast_facts
    from ..analysis.program_ast_adapters import build_program_evidence_index
    from .supervisor_meta_index import public_replay_without_metadata
    if not isinstance(snapshot, CodeVectorIndexSnapshot):
        raise IntentSourceNominationError("native code index snapshot required")
    # Replay the native closed snapshot parser as well as its source-dependent rows.
    try:
        native_snapshot = CodeVectorIndexSnapshot.from_dict(snapshot.to_dict())
    except (ValueError, KeyError, TypeError) as exc:
        raise IntentSourceNominationError("closed native snapshot required") from exc
    if native_snapshot != snapshot or set(snapshot.included_paths) != set(sources):
        raise IntentSourceNominationError("complete native source scope differs")
    with public_replay_without_metadata():
        try:
            evidence = build_program_evidence_index(sources, max_source_bytes=MAX_SOURCE_BYTES)
            native_ast = evidence.ast_index
            if (not evidence.exhaustive or any(item.status != "success" for item in evidence.results)
                    or native_ast.index_id != snapshot.ast_index_id or set(native_ast.paths) != set(sources)):
                raise IntentSourceNominationError("fresh native AST source index differs")
            records = {item.path: item for item in native_ast.path_records}
            expected_symbols = {(item.path, symbol) for item in native_ast.path_records
                                for symbol in item.ast_record.qualified_symbols}
            if (len(snapshot.rows) != len(expected_symbols)
                    or {(row.path, row.symbol) for row in snapshot.rows} != expected_symbols):
                raise IntentSourceNominationError("native symbol row population differs")
            facts_by_row = {row.row_id: resolve_code_symbol_ast_facts(records[row.path], row)
                            for row in snapshot.rows}
        except (ValueError, KeyError, TypeError, RecursionError) as exc:
            raise IntentSourceNominationError("fresh native source and row replay required") from exc
    definitions = {path: _definitions(source) for path, source in sources.items()
                   if PurePosixPath(path).suffix in {".py", ".pyi"}}
    for path, census in definitions.items():
        if set(census) != set(records[path].ast_record.qualified_symbols):
            raise IntentSourceNominationError("native Python definition census differs")
    ledger = canonical["ledger"]
    bindings = {**identities, "native_tree_id": snapshot.tree_id,
        "native_forest_id": snapshot.forest_id, "coverage_id": snapshot.coverage_id,
        "contract_cid": cid_for_dag_json(canonical), "ledger_sha256": ledger["ledger_sha256"],
        "instruction_source_sha256": _sha(instruction_raw), "index_id": snapshot.index_id,
        "ast_index_id": native_ast.index_id, "source_manifest_sha256": _sha(_json(source_manifest))}
    if reviewed is not None and _json(reviewed["bindings"]) != _json(bindings):
        raise IntentSourceNominationError("independent review bindings differ")
    by_requirement = {item["requirement_id"]: item for item in ledger["requirements"]}
    selected, seen = {}, set()
    for selector in reviewed["selectors"] if reviewed is not None else ():
        if type(selector) is not dict or set(selector) != {"requirement_id", "path", "qualified_symbol"}:
            raise IntentSourceNominationError("closed reviewed source selector required")
        req_id = _text(selector["requirement_id"])
        path, qualified = _path(selector["path"]), _text(selector["qualified_symbol"], 2048)
        identity = (req_id, path, qualified)
        if identity in seen or req_id not in by_requirement:
            raise IntentSourceNominationError("unknown or duplicate reviewed requirement selector")
        seen.add(identity)
        if by_requirement[req_id]["representation"] != "native_statement":
            raise IntentSourceNominationError("native statement review selector required")
        rows = [row for row in snapshot.rows if row.path == path and row.qualified_symbol == qualified]
        if len(rows) != 1 or path not in definitions:
            raise IntentSourceNominationError("unique native Python symbol selector required")
        row = rows[0]
        nodes = definitions[path].get(row.symbol, ())
        if len(nodes) != 1 or (nodes[0].lineno, nodes[0].end_lineno) != (row.line_start, row.line_end):
            raise IntentSourceNominationError("selected native definition is ambiguous")
        nomination = selected.setdefault(row.row_id, {
            "row_id": row.row_id, "path": path, "symbol": row.symbol, "qualified_symbol": row.qualified_symbol,
            "ast_record_id": row.sidecar.ast_record_id, "blob_identity": row.sidecar.blob_identity,
            "source_sha256": row.sidecar.source_sha256, "symbol_hash": row.sidecar.symbol_hash,
            "line_start": row.line_start, "line_end": row.line_end,
            "source_span": _source_span(sources[path], nodes[0], row),
            "native_facts_sha256": _sha(_json({key: list(value) for key, value in facts_by_row[row.row_id].items()})),
            "requirement_ids": [], "review_ref": reviewed["review_ref"],
            "selection_basis": "explicit_reviewed_nomination"})
        nomination["requirement_ids"].append(req_id)
    for nomination in selected.values():
        nomination["requirement_ids"].sort()
    units = {item["unit_id"]: item for item in ledger["source_units"]}
    requirements = []
    for requirement in sorted(ledger["requirements"], key=lambda item: item["requirement_id"]):
        statements, references = _native_statements(ledger, requirement)
        paths = sorted({path for statement in statements for argument in statement["arguments"]
                        for path in sources if argument in {path, "/app/" + path}})
        rows = sorted(row_id for row_id, item in selected.items()
                      if requirement["requirement_id"] in item["requirement_ids"])
        unit = {key: value for key, value in units[requirement["source_unit_id"]].items() if key != "text"}
        requirements.append({"native_requirement": requirement, "source_unit": unit,
            "statements": statements, "source_refs": references,
            "mandatory": requirement["modality"] in {"required", "intended", "prohibited"},
            "residual": True, "file_paths": paths, "symbol_row_ids": rows,
            "status": "reviewed_symbol_nomination" if rows else
                      "explicit_file_unknown_symbols" if paths else "unbound_source_selector"})
    unknown = {"unknown_symbol_requirement_count": sum(not item["symbol_row_ids"] for item in requirements),
        "unbound_requirement_count": sum(not item["file_paths"] and not item["symbol_row_ids"] for item in requirements),
        "residual_requirement_count": len(requirements),
        "mandatory_requirement_count": sum(item["mandatory"] for item in requirements),
        "nonmandatory_requirement_count": sum(not item["mandatory"] for item in requirements),
        "unsupported_source_unit_count": sum(item["disposition"] == "unsupported" for item in ledger["source_units"]),
        "unselected_duplicate_definition_count": sum(max(0, len(nodes) - 1) for census in definitions.values()
                                                     for nodes in census.values()),
        "selected_native_call_count": sum(len(facts_by_row[row_id]["call_refs"]) for row_id in selected),
        "dependencies": {kind: {"status": "not_analyzed", "unknown_count": None} for kind in
                         ("module_resolution", "receiver_resolution", "global_initialization", "control_data_flow")}}
    artifact = {"schema": SCHEMA, "bindings": bindings, "sources": source_manifest,
        "requirements": requirements, "nominations": sorted(selected.values(), key=lambda item: item["row_id"]),
        "review": None if reviewed is None else {"review_ref": reviewed["review_ref"], "sha256": expected_review_sha256},
        "unknown_census": unknown, "native_ast_replay_verified": True, "analysis_complete": False,
        "filesystem_freshness_verified": False, **{key: False for key in AUTHORITY_FIELDS}}
    if len(_json(artifact)) > max_bytes:
        raise IntentSourceNominationBoundsError("complete source nomination exceeds its output bound")
    return artifact


def validate_intent_source_nomination(artifact, **independent_inputs):
    """Compare against a fresh rebuild, never a claimed self-hash or authority."""
    maximum = independent_inputs.get("max_bytes", MAX_BYTES)
    if type(maximum) is not int or not 1024 <= maximum <= MAX_BYTES:
        raise IntentSourceNominationBoundsError("bounded exact integer output cap required")
    parsed, raw = _decoded(artifact, maximum)
    expected = build_intent_source_nomination(**independent_inputs)
    if raw != _json(expected):
        raise IntentSourceNominationError("source nomination differs from independent reconstruction")
    return parsed


__all__ = ["SCHEMA", "REVIEW_SCHEMA", "BINDING_FIELDS", "AUTHORITY_FIELDS", "MAX_BYTES",
    "IntentSourceNominationError", "IntentSourceNominationBoundsError",
    "build_intent_source_nomination", "validate_intent_source_nomination"]
