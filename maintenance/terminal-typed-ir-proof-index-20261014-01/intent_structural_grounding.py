"""Source-bound headless-terminal nominations, with whole-prompt residuals.

This is an explicitly authored candidate interpretation of one pinned public
instruction, not a natural-language parser or a semantic-equivalence proof.
Native CodebaseIR identities describe a supplied historical observation. The
caller must separately call the index owner's ``observe_current`` at use time.
No supplied dictionary, latent vector, or successful task-coverage check can
grant behavioral, execution, proof, completion, or task-omission authority.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import PurePosixPath


SCHEMA = "terminal-intent-structural-grounding@1"
INSTRUCTION_SHA256 = "004ac3efa98dd4c564f3888fe199962772d23de405c96ec9232c1eab1a2089e8"
BASE_SOURCE_SHA256 = "697fd6435a5df3ee8c6f6f2546340c0609a424e53cb8fe80fdb131fe1e9f050f"
PROFILE = "manually_authored_headless_interface_candidate@1"
_FLAGS = dict(semantic_alignment_verified=False, source_semantics_verified=False,
    behavioral_satisfaction=False, proof_authority=False, execution_authority=False,
    completion_authority=False, mutation_authority=False, omission_authority=False,
    full_task_satisfaction=False, source_to_model_equivalence=False,
    convergence_proved=False, contract_recall_verified=False,
    unseen_task_generalization_verified=False)
_REVIEWED_CLAUSES = (
    ("interface", "Implement the provided `BaseTerminal` interface.",
     "implement_interface", ("agent", "BaseTerminal")),
    ("output", "Call your implementation `HeadlessTerminal(BaseTerminal)` and put it in a file called `/app/headless_terminal.py` so that it can be imported as `from headless_terminal import HeadlessTerminal`.",
     "produce_subclass", ("agent", "HeadlessTerminal", "BaseTerminal", "headless_terminal.py")),
)


class GroundingError(ValueError):
    """The bounded reviewed domain or source identities do not match."""


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False).encode("utf-8")


def _json(value, *, maximum=8 * 1024 * 1024):
    pending, count = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        count += 1
        if depth > 48 or count > 100_000:
            raise GroundingError("bounded inert JSON structure required")
        if type(item) is dict:
            if any(type(key) is not str for key in item):
                raise GroundingError("exact string JSON keys required")
            pending.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            pending.extend((child, depth + 1) for child in item)
        elif type(item) not in (str, int, float, bool, type(None)):
            raise GroundingError("exact inert JSON values required")
    try:
        raw = _wire(value)
    except (ValueError, TypeError, RecursionError) as exc:
        raise GroundingError("finite bounded JSON required") from exc
    if len(raw) > maximum:
        raise GroundingError("JSON byte bound exceeded")
    return json.loads(raw)


def _digest(value, name):
    if (type(value) is not str or len(value) != 64
            or any(char not in "0123456789abcdef" for char in value)):
        raise GroundingError("exact lowercase " + name + " SHA256 required")
    return value


def _path(value):
    if type(value) is not str or len(value.encode("utf-8")) > 4096:
        raise GroundingError("bounded canonical source path required")
    path = PurePosixPath(value)
    if (not value or value == "." or path.is_absolute() or ".." in path.parts
            or ".git" in path.parts or str(path) != value or "\\" in value
            or any(char in value for char in "\r\n\0")):
        raise GroundingError("canonical source-relative path required")
    return value


def _source_bindings(source_records, manifest):
    from ipfs_datasets_py.logic.software_contracts.content import cid_for_bytes

    if type(source_records) is not list or not 1 <= len(source_records) <= 256:
        raise GroundingError("bounded nonempty exact source records required")
    records, trees, bindings = {}, {}, []
    entries = {entry.path: entry for entry in manifest.snapshot.entries}
    if any(entry.is_opaque for entry in entries.values()):
        raise GroundingError("this reviewed source-only profile does not consume opaque entries")
    total = 0
    for record in source_records:
        if type(record) is not dict or set(record) != {"path", "sha256", "source_text"}:
            raise GroundingError("exact path, sha256 and source_text fields required")
        path = _path(record["path"])
        if path in records:
            raise GroundingError("duplicate source record path")
        digest = _digest(record["sha256"], "source")
        text = record["source_text"]
        if type(text) is not str or not 0 < len(text.encode("utf-8")) <= 64 * 1024:
            raise GroundingError("bounded exact UTF-8 Python source required")
        raw = text.encode("utf-8")
        total += len(raw)
        if total > 1024 * 1024 or _sha(raw) != digest:
            raise GroundingError("source bytes differ from their claimed SHA256 or source bound")
        entry = entries.get(path)
        if entry is None or entry.source_cid != cid_for_bytes(raw) or entry.size_bytes != len(raw):
            raise GroundingError("source bytes do not match the complete native snapshot entry")
        unit = next(item for item in manifest.units if item.source_key == entry.source_key)
        if unit.parse_status != "ok" or unit.ast_cid is None:
            raise GroundingError("reviewed grounding requires native AST-ok source units")
        try:
            tree = ast.parse(text, filename=path)
        except (SyntaxError, ValueError, RecursionError) as exc:
            raise GroundingError("supplied source is not supported Python syntax") from exc
        records[path], trees[path] = record, tree
        bindings.append({"path": path, "sha256": digest, "source_cid": entry.source_cid,
            "entry_cid": entry.entry_cid, "ast_cid": unit.ast_cid,
            "parse_status": unit.parse_status, "bytes": len(raw)})
    if set(records) != set(entries):
        raise GroundingError("source records must cover the complete native snapshot exactly")
    return records, trees, sorted(bindings, key=lambda item: item["path"])


def _interface(records, trees, manifest):
    from ipfs_datasets_py.logic.software_contracts.semantic_index.identity import normalize_ast
    from ipfs_datasets_py.logic.software_contracts.semantic_index.python_analysis import PythonSemanticAnalyzer

    selected = [path for path, record in records.items()
        if record["sha256"] == BASE_SOURCE_SHA256 and PurePosixPath(path).name == "base_terminal.py"]
    if len(selected) != 1:
        raise GroundingError("unique pinned public BaseTerminal source required")
    path = selected[0]
    classes = [node for node in trees[path].body
        if type(node) is ast.ClassDef and node.name == "BaseTerminal"]
    if len(classes) != 1:
        raise GroundingError("unique top-level BaseTerminal definition required")
    methods = [node for node in classes[0].body
        if type(node) is ast.FunctionDef and node.name == "send_keystrokes"]
    if len(methods) != 1:
        raise GroundingError("unique BaseTerminal.send_keystrokes interface required")
    method = methods[0]
    symbols = [symbol.to_dict() for symbol in manifest.semantic_state.symbols
        if symbol.module_path == path]
    class_rows = [row for row in symbols if row["kind"] == "class"
        and row["qualified_name"].split(".")[-1] == "BaseTerminal"
        and row["normalized_ast"].get("name") == "BaseTerminal"]
    method_rows = [row for row in symbols if row["kind"] == "method"
        and row["qualified_name"].endswith(".BaseTerminal.send_keystrokes")
        and row["normalized_ast"] == normalize_ast(method)]
    if len(class_rows) != 1 or len(method_rows) != 1:
        raise GroundingError("source-derived interface must join exact native semantic symbols")
    # Recomputable hashes alone do not establish that caller-supplied semantic
    # bodies came from the source. Replay the native syntax extractor for this
    # small interface, still without importing/executing source or opening SQL.
    replay = PythonSemanticAnalyzer(repository_id=manifest.snapshot.repository_id).analyze(
        records[path]["source_text"], path)
    replay_rows = {row.stable_id: row.to_dict() for row in replay.symbol_records}
    for row in (*class_rows, *method_rows):
        if replay_rows.get(row["stable_id"]) != row:
            raise GroundingError("native interface symbol differs from exact source extraction replay")
    output_definitions = []
    for source_path, tree in trees.items():
        for node in ast.walk(tree):
            if type(node) is ast.ClassDef and node.name == "HeadlessTerminal":
                output_definitions.append({"path": source_path, "line": node.lineno})
    return {"source_path": path, "source_sha256": records[path]["sha256"],
        "class_symbol": class_rows[0], "method_symbol": method_rows[0],
        "method_source_ast_sha256": _sha(_wire(normalize_ast(method))),
        "method_signature": method_rows[0]["signature"],
        "method_body_kind": "abstract_stub",
        "requested_subclass": "HeadlessTerminal", "requested_output_path": "headless_terminal.py",
        "requested_output_definitions_in_admitted_inventory": output_definitions,
        "absence_scope": "admitted_source_inventory_only",
        "behavioral_satisfaction": False}


def _ledger(instruction_text):
    from ipfs_datasets_py.logic.intent_ir import schema
    from ipfs_datasets_py.logic.intent_ir.canonicalize import canonical_intent_ir_bytes
    from ipfs_datasets_py.logic.intent_ir.decoder import decode_intent_ir
    from ipfs_datasets_py.logic.intent_ir.formalize.requirements import (
        build_intent_requirement_ledger, validate_intent_requirement_ledger)

    units, candidates, documents = [], [], []
    for name, clause, predicate, arguments in _REVIEWED_CLAUSES:
        if instruction_text.count(clause) != 1:
            raise GroundingError("reviewed clause does not select one exact original source span")
        left, right = instruction_text.index(clause), instruction_text.index(clause) + len(clause)
        ref_id, unit_id = "source:" + name, "instruction-unit:" + name
        source = schema.SourceRef(ref_id, "terminal-bench-2:headless-terminal/instruction.md",
            "headless-terminal/instruction.md", "sha256:" + INSTRUCTION_SHA256,
            INSTRUCTION_SHA256, review_status=schema.ReviewStatus.UNREVIEWED,
            span=schema.SourceSpan(left, right))
        statement = schema.IntentStatement("goal:" + name, schema.StatementKind.GOAL,
            schema.IntentModality.REQUIRED, clause, (ref_id,), predicate, arguments,
            confidence=0.0, review_status=schema.ReviewStatus.UNREVIEWED,
            grounding=schema.NodeGrounding.INFERRED)
        document = schema.IntentIRDocument("manual-headless-candidate:" + name,
            "Manually authored headless interface candidate", schema.IntentKind.DECLARATIVE,
            (source,), (statement,), tags=("manual-candidate", "no-semantic-parser", "unverified"))
        document = schema.validate_intent_ir(decode_intent_ir(document.to_dict()))
        documents.append({"document": document.to_dict(),
            "canonical_sha256": _sha(canonical_intent_ir_bytes(document))})
        units.append({"unit_id": unit_id, "start_char": left, "end_char": right,
            "start_byte": len(instruction_text[:left].encode("utf-8")),
            "end_byte": len(instruction_text[:right].encode("utf-8")),
            "text": clause, "sha256": _sha(clause.encode("utf-8")),
            "disposition": "interpreted_candidate", "reason": "manually_authored_candidate_label"})
        candidates.append({"unit_id": unit_id, "candidate_intent_ir": document.to_dict()})
    report = {"schema": "intent-reviewed-source-report@1", "source_sha256": INSTRUCTION_SHA256,
        "source_bytes": len(instruction_text.encode("utf-8")), "source_characters": len(instruction_text),
        "producer": {"name": "manually-authored-headless-candidate-labels", "revision": "1"},
        "interpretation_status": "reviewed_candidate", "units": units, "candidates": candidates,
        "proof_authority": False, "execution_authority": False, "completion_authority": False,
        "source_semantics_verified": False}
    # Native requirement reports use canonical ASCII JSON, separately from this
    # artifact's declared UTF-8 canonicalization.
    report["report_sha256"] = _sha(json.dumps(report, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False).encode("utf-8"))
    identity = {"task_id": "headless-terminal", "instruction_sha256": INSTRUCTION_SHA256,
        "interpretation": "manual_candidate_not_automated_semantic_matching"}
    ledger = build_intent_requirement_ledger(instruction_text, source_report=report,
        source_identity=identity)
    validate_intent_requirement_ledger(ledger, source_text=instruction_text)
    return ledger, documents


def _coverage(ledger, instruction_text):
    from ipfs_accelerate_py.agent_supervisor.prompt.intent_plan_coverage import (
        build_intent_requirement_contract, check_intent_plan_coverage)
    from ipfs_accelerate_py.agent_supervisor.prompt.prompt_workflow import (
        PromptAcceptanceRecord, PromptGoalGraph, PromptGoalRecord, PromptOutputRecord,
        PromptTaskRecord, PromptValidationRecord, prompt_workflow_cid)

    validation = "validation:headless-interface-behavior-pending"
    output = {"path": "headless_terminal.py", "effect": "create", "media_type": "text/x-python"}
    requirements = [{"requirement_id": row["requirement_id"], "outputs": [dict(output)],
        "validation_keys": [validation], "dependency_requirement_ids": []}
        for row in ledger["requirements"]]
    contract = build_intent_requirement_contract(source_path="instruction.md", ledger=ledger,
        requirements=requirements, source_text=instruction_text)
    cid = prompt_workflow_cid({"schema": SCHEMA, "profile": PROFILE,
        "instruction_sha256": INSTRUCTION_SHA256})
    acceptance = PromptAcceptanceRecord(criterion_key="criterion:headless-interface-pending",
        criterion="Implement and validate the requested interface; behavior remains pending.",
        validation_keys=(validation,))
    goal = PromptGoalRecord(goal_key="goal:headless-interface", parent_goal_cid="",
        dependency_goal_cids=(), title="Implement the headless interface",
        objective="Implement the requested subclass after reviewing residual instructions.",
        rationale="Manually authored source-bound candidate only.",
        scope_paths=("headless_terminal.py",), acceptance=(acceptance,))
    task = PromptTaskRecord(task_key="task:headless-interface", goal_cid=goal.goal_cid,
        dependency_task_cids=(), objective=goal.objective, rationale=goal.rationale,
        scope_paths=("headless_terminal.py",), outputs=(PromptOutputRecord(**output),),
        validations=(PromptValidationRecord(validation_key=validation,
            argv=("python", "-m", "pytest")),), acceptance=(acceptance,),
        evidence_cids=(), policy_roots=(cid,))
    graph = PromptGoalGraph(request_cid=cid, scan_cid=cid, program_root=cid,
        policy_roots=(cid,), goals=(goal,), tasks=(task,), evidence=())
    bindings = [{"requirement_id": row["requirement_id"],
        "task_keys": [task.task_key], "validation_keys": [validation]}
        for row in ledger["requirements"]]
    receipt = check_intent_plan_coverage(contract, graph=graph, bindings=bindings)
    if receipt["accepted"] or not any(row["code"] == "unsupported_source_units"
            for row in receipt["errors"]):
        raise GroundingError("partial reviewed intent must remain blocked by native source coverage")
    return {"contract": contract, "graph": graph.to_dict(), "bindings": bindings,
        "coverage": receipt, "native_checker": "check_intent_plan_coverage",
        "validation_commands_executed": False, "symbolic_plan_executed": False,
        "status": "blocked_partial_instruction_coverage"}


def build_grounding(*, instruction_text: str, instruction_sha256: str,
        source_records: list[dict], structural_manifest: dict,
        alignment_projection: dict | None = None) -> dict:
    """Build a closed historical nomination and a genuinely rejected partial plan.

    The source-record population must exactly equal the native snapshot's
    captured inventory. Supplied native AST CIDs are joined, not fetched or
    certified here. Current-head/source observation remains the caller's duty.
    ``alignment_projection`` is inert advisory evidence and cannot affect task
    coverage, source facts, residuals, or any authority flag.
    """
    from ipfs_datasets_py.logic.software_contracts.codebase_ir import CodebaseIRManifest

    _digest(instruction_sha256, "instruction")
    if (type(instruction_text) is not str
            or len(instruction_text.encode("utf-8")) != 755
            or _sha(instruction_text.encode("utf-8")) != instruction_sha256
            or instruction_sha256 != INSTRUCTION_SHA256):
        raise GroundingError("exact pinned public headless instruction required")
    try:
        manifest = CodebaseIRManifest.from_dict(_json(structural_manifest))
    except (TypeError, ValueError, KeyError) as exc:
        raise GroundingError("invalid native structural manifest: " + str(exc)) from exc
    records, trees, bindings = _source_bindings(_json(source_records), manifest)
    interface = _interface(records, trees, manifest)
    projection = None
    if alignment_projection is not None:
        if type(alignment_projection) is not dict:
            raise GroundingError("inert alignment projection object required")
        projection = _json(alignment_projection)
        pending = [projection]
        while pending:
            item = pending.pop()
            if type(item) is dict:
                if any(item[key] is not False for key in _FLAGS if key in item):
                    raise GroundingError("alignment candidates grant no source or behavioral authority")
                pending.extend(item.values())
            elif type(item) is list:
                pending.extend(item)
    ledger, documents = _ledger(instruction_text)
    plan = _coverage(ledger, instruction_text)
    residuals = [{"source_unit_id": unit["unit_id"], "start_char": unit["start_char"],
        "end_char": unit["end_char"], "sha256": unit["sha256"], "text": unit["text"],
        "reason": unit["unsupported_reason"], "status": "unresolved_original_instruction"}
        for unit in ledger["source_units"] if unit["disposition"] == "unsupported"]
    result = {"schema": SCHEMA, "profile": PROFILE,
        "status": "structural_nomination_with_blocked_partial_plan",
        "instruction": {"text": instruction_text, "sha256": instruction_sha256,
            "bytes": len(instruction_text.encode("utf-8")), "task_id": "headless-terminal"},
        "interpretation": {"kind": "manually_authored_candidate",
            "automated_natural_language_parser_used": False, "human_review_claimed": False,
            "learned_intent_decoding_used": False},
        "native_intent_documents": documents, "native_requirement_ledger": ledger,
        "source_bindings": bindings, "structural_interface_nomination": interface,
        "structural_manifest_cid": manifest.cid,
        "snapshot_cid": manifest.snapshot.snapshot_cid,
        "repository_id": manifest.snapshot.repository_id,
        "semantic_state_cid": manifest.semantic_state.state_cid,
        "ast_revision_id": manifest.ast_revision_id,
        "alignment_projection": projection,
        "alignment_projection_sha256": None if projection is None else _sha(_wire(projection)),
        "advisory_projection_changes_nomination": False,
        "original_instruction_residuals": residuals,
        "behavioral_residuals": [{"requirement_id": row["requirement_id"],
            "status": "unresolved_software_behavior", "behavioral_satisfaction": False}
            for row in ledger["requirements"]],
        "partial_plan": plan, "whole_instruction_preserved": True,
        "source_accounting_complete": ledger["source_accounting_complete"],
        "live_head_verified_here": False, "ast_artifact_bytes_verified_here": False,
        "interface_semantic_symbol_extraction_replayed_here": True,
        "caller_requires_current_head_observation": True,
        "required_observation_api": "RepositoryCodebaseIndex.observe_current",
        "current_behavioral_facts": [], "behavioral_satisfied_requirements": [],
        "removed_task_ids": [], "provider_calls": 0, "source_executed": False,
        "training_executed": False, **_FLAGS}
    result["report_sha256"] = _sha(_wire(result))
    return _json(result)


__all__ = ["SCHEMA", "GroundingError", "build_grounding"]
