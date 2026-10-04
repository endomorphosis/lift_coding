"""Independent bounded correlation of retained finite admission evidence.

The default mode checks artifact identity and task meaning using only stdlib.
Optional public historical signature replay is separate from current permission.
"""
from __future__ import annotations

import argparse
import ast
import base64
import copy
import hashlib
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from codebase_ir_acceptance import OFFSET_CLAUSE, TYPE_CLAUSE
from codebase_ir_external_pins import _bounded_document, _parse_document

SCHEMA = "codebase-ir-retained-admission-audit@1"
TASK_BINDINGS = {TYPE_CLAUSE: "FINITE-TYPE", OFFSET_CLAUSE: "FINITE-OFFSET"}
DOMAIN = [-2, -1, 0, 1, 2]
FALSE_FLAGS = {"source_semantics_verified", "runtime_behavior_verified", "proof_authority",
    "code_proof_authority", "production_admitted", "production_activation", "execution_authority",
    "completion_authority", "mutation_authority", "omission_authority", "worker_launched", "convergence_proved"}
MATCH_FALSE = {"source_semantics_verified", "runtime_behavior_verified", "behavior_authority",
    "proof_authority", "execution_authority", "completion_authority", "mutation_authority"}
CAPACITY_FALSE = (FALSE_FLAGS - {"code_proof_authority", "production_activation"}) | {"behavior_authority"}
VOLATILE = {"status", "created_at_ms", "updated_at_ms", "observed_at_ms", "started_at_ms", "finished_at_ms"}
RECORDS = ("result.json", "before-declaration.json", "before-admission.json", "materialized.json",
    "successor-admission.json", "cold-admission.json", "fresh-process-replay.json", "cold-comparison.json")
MAX_FILES = 128
MAX_TOTAL_BYTES = 32 * 1024 * 1024
MAX_FILE_BYTES = 4 * 1024 * 1024
SIGNED_PRODUCER_MODULES = frozenset({
    "ipfs_accelerate_py.agent_supervisor.planning.finite_integer_capacity_preview",
    "ipfs_accelerate_py.agent_supervisor.planning.finite_integer_codebase",
    "ipfs_accelerate_py.agent_supervisor.runtime.finite_repository_admission",
    "ipfs_accelerate_py.agent_supervisor.runtime.local_planning_admission",
    "ipfs_datasets_py.logic.software_contracts.codebase_finite_integer_observation",
    "ipfs_datasets_py.logic.software_contracts.codebase_integer_model_lean",
})
MODEL_FRONTEND_MODULES = frozenset({
    "ipfs_datasets_py.logic.backends.process",
    "ipfs_datasets_py.logic.backends.smt.compiler",
    "ipfs_datasets_py.logic.backends.smt.differential",
    "ipfs_datasets_py.logic.software_contracts.codebase_integer_model_lean",
    "ipfs_datasets_py.logic.software_contracts.codebase_integer_profile",
    "ipfs_datasets_py.logic.software_verification.pipeline",
    "ipfs_datasets_py.logic.software_verification.program",
    "ipfs_datasets_py.logic.software_verification.source_adapters",
    "ipfs_datasets_py.logic.software_verification.vc",
})
SOURCE_PIN_MODULES = {"signed_producer": SIGNED_PRODUCER_MODULES, "model_frontend": MODEL_FRONTEND_MODULES}


class AdmissionEvidenceError(ValueError):
    pass


def need(condition: bool, message: str) -> None:
    if not condition:
        raise AdmissionEvidenceError(message)


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def cid(value: Any) -> str:
    """Structural DAG-JSON CID comparison, without authentication authority."""
    return "b" + base64.b32encode(b"\x01\xa9\x02\x12\x20" + hashlib.sha256(canonical(value)).digest()).decode().lower().rstrip("=")


def raw_cid(raw: bytes) -> str:
    return "b" + base64.b32encode(b"\x01\x55\x12\x20" + hashlib.sha256(raw).digest()).decode().lower().rstrip("=")


def exact(left: Any, right: Any) -> bool:
    return canonical(left) == canonical(right)


def source_pin_groups(admission: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Require the selected v1 profile's independently specified module population."""
    groups = {"signed_producer": admission["declaration"]["payload"]["implementation"]["source_sha256"],
        "model_frontend": admission["evidence"]["operational_model"]["translation"]["frontend"]["source_sha256"]}
    for name, expected in SOURCE_PIN_MODULES.items():
        pins = groups[name]
        need(type(pins) is dict and set(pins) == expected, "exact selected source pin population required: " + name)
        need(all(type(digest) is str and len(digest) == 64 and all(character in "0123456789abcdef" for character in digest)
                 for digest in pins.values()), "lowercase SHA256 source pins required: " + name)
    return groups


class ArtifactReader:
    def __init__(self, root: Path):
        self.root = root.resolve(strict=True)
        need(self.root.is_dir() and not root.is_symlink(), "canonical retained fixture directory required")
        self.pins: dict[str, dict[str, Any]] = {}
        self.total = 0

    def read(self, path: Path, *, limit: int = MAX_FILE_BYTES) -> bytes:
        need(path.is_absolute() and path.is_relative_to(self.root) and path.resolve(strict=True) == path
            and not any(part.is_symlink() for part in (path, *path.parents)), "retained artifact escaped exact fixture root")
        key = str(path)
        if key not in self.pins:
            need(len(self.pins) < MAX_FILES, "retained artifact count cap exceeded")
            limit = min(limit, MAX_TOTAL_BYTES - self.total)
            need(limit > 0, "retained artifact total byte cap exceeded")
        else:
            limit = min(limit, self.pins[key]["size_bytes"])
        raw = _bounded_document(path, limit)
        pin = {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}
        if key in self.pins:
            need(self.pins[key] == pin, "retained artifact bytes changed between reads")
        else:
            need(len(self.pins) < MAX_FILES and self.total + len(raw) <= MAX_TOTAL_BYTES, "retained artifact count or total byte cap exceeded")
            self.pins[key] = pin
            self.total += len(raw)
        return raw

    def record(self, name: str) -> dict[str, Any]:
        value = parse_document(self.read(self.root / name))
        need(type(value) is dict, "retained record must be a JSON object")
        return value

    def recheck(self) -> bool:
        for path, pin in tuple(self.pins.items()):
            need(hashlib.sha256(self.read(Path(path))).hexdigest() == pin["sha256"], "retained evidence drifted during audit")
        return True


def parse_document(raw: bytes) -> Any:
    value = _parse_document(raw)
    pending, count = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        count += 1
        need(count <= 200000 and depth <= 64, "retained JSON node/depth budget exceeded")
        if type(item) is dict:
            pending.extend((member, depth + 1) for member in item.values())
        elif type(item) is list:
            pending.extend((member, depth + 1) for member in item)
        elif type(item) is float:
            need(math.isfinite(item), "nonfinite retained JSON number")
    return value


def _false(record: dict[str, Any], required=()) -> None:
    need(type(record) is dict and set(required) <= set(record), "required finite authority fields missing")
    for key in (FALSE_FLAGS | MATCH_FALSE) & set(record):
        need(record[key] is False, "finite context acquired authority: " + key)


def _nested_false(value: Any) -> None:
    if type(value) is dict:
        _false(value)
        for member in value.values():
            _nested_false(member)
    elif type(value) is list:
        for member in value:
            _nested_false(member)


def _workflow_payload(value: Any) -> Any:
    if type(value) is dict:
        return {key: _workflow_payload(member) for key, member in value.items() if key not in VOLATILE}
    if type(value) is list:
        return [_workflow_payload(member) for member in value]
    return value


def _workflow_ids(value: Any) -> None:
    if type(value) is dict:
        if "content_id" in value and str(value.get("schema", "")).startswith("ipfs_accelerate_py/agent-supervisor/prompt-"):
            need(value["content_id"] == cid(_workflow_payload({key: member for key, member in value.items() if key != "content_id"})),
                 "native workflow content identity differs from complete record")
        for member in value.values():
            _workflow_ids(member)
    elif type(value) is list:
        for member in value:
            _workflow_ids(member)


def _envelope(envelope: dict[str, Any]) -> dict[str, Any]:
    need(type(envelope) is dict and set(envelope) == {"payload", "binding"}, "complete signed envelope required")
    binding = envelope["binding"]
    need(type(binding) is dict and set(binding) == {"identity", "profile_id", "signature"}
        and all(type(binding[key]) is str and binding[key] for key in binding), "signed envelope binding fields differ")
    try:
        signature = base64.b64decode(binding["signature"], validate=True)
    except ValueError as exc:
        raise AdmissionEvidenceError("signed envelope signature encoding differs") from exc
    need(len(signature) == 64, "signed envelope signature size differs")
    need(type(envelope["payload"]) is dict, "signed envelope payload required")
    return envelope["payload"]


def _assert_query_and_predicates(declaration, document, semantic, match):
    """Rebuild the selected requirement meanings without importing their producer."""
    contract = {"schema": "codebase-integer-offset-contract@1", "profile": "python-integer-offset@1",
                "path": "calc.py", "function_name": "increment", "parameter": "n", "offset": 2}
    text = ("Under python-integer-offset-finite@1, calc.py::increment(n) must return an exact int for inputs [-2,-1,0,1,2].\n"
            "Under python-integer-offset-finite@1, calc.py::increment(n) must return n + 2 for inputs [-2,-1,0,1,2].")
    need(declaration["source_text"] == text, "complete original finite instruction changed")
    digest = hashlib.sha256(text.encode()).hexdigest()
    statements = sorted(document["statements"], key=lambda row: row["statement_id"])
    sources = sorted(document["sources"], key=lambda row: row["ref_id"])
    for source in sources:
        need(source["content_sha256"] == digest, "clause source digest drift")
    for statement in statements:
        need(statement["kind"] == "goal" and statement["modality"] == "required", "finite clause polarity changed")
        span = next(source["span"] for source in sources if source["ref_id"] == statement["source_ref_ids"][0])
        need(type(span["start_char"]) is int and type(span["end_char"]) is int
             and text[span["start_char"]:span["end_char"]] == statement["normalized_text"], "finite clause source span drift")
    query = {"schema": "supervisor-finite-integer-query@1", "profile": "python-integer-offset-finite@1",
        "cnl_profile": "finite-integer-intent-sentences@1", "native_document_sha256": hashlib.sha256(declaration["intent_json"].encode()).hexdigest(),
        "intent_source_sha256": digest, "intent_sources": sources,
        "statements": [{key: row[key] for key in ("statement_id", "predicate", "arguments", "kind", "modality", "normalized_text", "source_ref_ids")}
                       for row in statements], "requirement_ids": sorted(TASK_BINDINGS),
        "contract": contract, "contract_cid": cid(contract), "domain_inputs": DOMAIN,
        "domain_cid": cid({"schema": "codebase-finite-integer-domain@1", "profile": "python-integer-offset-finite@1", "inputs": DOMAIN}),
        "supported": True, "reasons": [], "semantic_alignment_verified": True,
        "alignment_scope": "finite-integer-intent-sentences@1", **{key: False for key in MATCH_FALSE}}
    query["query_cid"] = cid(query)
    need(exact(semantic.get("query"), query) and exact(match.get("query"), query), "finite query meaning or original instruction drift")
    head, source = declaration["head"], match["source_cid"]
    refs = sorted({query["query_cid"], cid(head), head["snapshot_cid"], digest})
    expected, mapping = [], {}
    for statement in statements:
        kind = statement["predicate"]
        binding = {"schema": "supervisor-finite-integer-predicate-binding@1", "profile": "python-integer-offset-finite@1",
            "requirement_id": statement["statement_id"], "query_cid": query["query_cid"], "head": head,
            "source_cid": source, "contract": contract, "domain_cid": query["domain_cid"], "domain_inputs": DOMAIN, "predicate": kind}
        identity = cid(binding)
        selectors = [{"schema": "ipfs_accelerate_py/agent-supervisor/obligation-invalidation-selector@1",
            "selector_id": name + ":" + identity, "kind": selector_kind, "value_ref": value, "provenance_refs": refs}
            for name, selector_kind, value in (("domain", "policy", query["query_cid"]), ("path", "path", "calc.py"),
                                              ("root", "root", head["snapshot_cid"]), ("source", "evidence", source))]
        predicate = {"schema": "ipfs_accelerate_py/agent-supervisor/obligation-predicate@1",
            "predicate_id": "finite-requirement:" + identity, "predicate_type": kind + "_under_python_integer_offset_finite_v1",
            "subject_ref": cid(head), "object_ref": identity, "property_id": kind, "polarity": "positive", "support": "reviewed",
            "provenance_refs": sorted(set(refs + [source])), "invalidation_selectors": selectors,
            "proof_requirement_refs": [], "validation_requirement_refs": [], "assumption_refs": []}
        expected.append(predicate)
        mapping[statement["statement_id"]] = predicate["predicate_id"]
    typed = match["typed_intent"]
    need(exact(typed["metadata"]["requirement_predicate_ids"], mapping)
         and exact(sorted(typed["desired_predicates"], key=lambda row: row["predicate_id"]), sorted(expected, key=lambda row: row["predicate_id"]))
         and exact(semantic["typed_intent"], typed) and typed["current_root_id"] == head["snapshot_cid"],
         "typed requirement predicate identity, selectors or meaning drift")


def assert_admission(admission: dict[str, Any], *, successor: bool) -> dict[str, Any]:
    need(type(admission) is dict and set(admission) == {"declaration", "graph", "evidence", "local_admission", "receipt"}, "complete original admission population required")
    declaration = _envelope(admission["declaration"])
    _nested_false(admission)
    need(declaration.get("schema") == "supervisor-finite-repository-declaration@1", "finite declaration schema differs")
    source_pin_groups(admission)
    manifest = _envelope(declaration["manifest"])
    need(manifest.get("schema") == "supervisor-local-benchmark-manifest@1", "only retained joined manifest version1 is independently exercised")
    need(declaration.get("task_bindings") == TASK_BINDINGS, "type/offset identities must retain their original native task meanings")
    specs = manifest.get("tasks")
    need(type(specs) is list and len(specs) == 2 and {row["task_key"] for row in specs} == set(TASK_BINDINGS.values()), "complete original administrator tasks required")
    by_spec = {row["task_key"]: row for row in specs}
    graph = admission["graph"]
    _workflow_ids(graph)
    tasks = graph.get("tasks", [])
    need(type(tasks) is list and len(tasks) == 2 and {row["task_key"] for row in tasks} == set(by_spec), "complete native graph task population required")
    by_task = {row["task_key"]: row for row in tasks}
    need(len({row["content_id"] for row in tasks}) == 2, "distinct native task identities required")
    for key, spec in by_spec.items():
        task = by_task[key]
        expected_check = "public-type" if key == "FINITE-TYPE" else "public-offset"
        expected_file = "check_type.py" if key == "FINITE-TYPE" else "check_offset.py"
        dependency_keys = [] if key == "FINITE-TYPE" else ["FINITE-TYPE"]
        need(spec.get("dependencies") == dependency_keys
            and task.get("dependency_task_cids") == [by_task[dep]["content_id"] for dep in dependency_keys], "native administrator prerequisite changed")
        need(spec.get("outputs") == [{"effect": "modify", "media_type": "text/x-python", "path": "calc.py"}]
            and task.get("predicted_files") == ["calc.py"]
            and [{name: row[name] for name in ("effect", "media_type", "path")} for row in task.get("outputs", [])] == spec["outputs"], "native task output selector drift")
        need(sorted(spec.get("scope_paths", [])) == sorted(task.get("scope_paths", [])) == ["calc.py", "check_offset.py", "check_type.py"], "original validation scope changed")
        for field in ("validations", "acceptance"):
            projected = [{name: member for name, member in row.items()
                          if name not in {"schema", "contract_version", "content_id"}}
                         for row in task.get(field, [])]
            need(exact(projected, spec.get(field)), "native task detached from complete signed " + field)
        for container in (spec, task):
            validations = container.get("validations", [])
            need(len(validations) == 1 and validations[0].get("validation_key") == expected_check
                and validations[0].get("argv", [])[1:] == [expected_file]
                and validations[0].get("cwd") == "." and exact(validations[0].get("expected_exit_codes"), [0]), "original public type/offset validation meaning changed")
            acceptance = container.get("acceptance", [])
            need(len(acceptance) == 1 and acceptance[0].get("validation_keys") == [expected_check], "native task acceptance check changed")
    request = declaration["request"]
    head = declaration["head"]
    need(graph.get("request_cid") == manifest["planning_roots"]["request_cid"]
        and graph.get("program_root") == request["roots"]["program_root"] == manifest["planning_roots"]["program_root"]
        and request["roots"]["repository_root_cid"] == head["snapshot_cid"]
        and request.get("scope_paths") == ["calc.py"], "signed request/source/graph root drift")
    document = parse_document(declaration["intent_json"].encode())
    statements = document.get("statements", [])
    need(len(statements) == 2 and {row["statement_id"] for row in statements} == set(TASK_BINDINGS), "complete finite clause population required")
    for row in statements:
        expected_predicate = "finite_integer_exact_type" if row["statement_id"] == TYPE_CLAUSE else "finite_integer_offset"
        expected_value = "exact_int" if row["statement_id"] == TYPE_CLAUSE else "2"
        need(row.get("predicate") == expected_predicate and row.get("arguments") == ["calc.py", "increment", "n", "[-2,-1,0,1,2]", "python-integer-offset-finite@1", expected_value], "typed clause semantic identity changed")
    operations = declaration["operation_catalog"]["operations"]
    need(len(operations) == 2 and {row["requirement_id"] for row in operations} == set(TASK_BINDINGS), "complete reviewed operation population required")
    for row in operations:
        kind = "type" if row["requirement_id"] == TYPE_CLAUSE else "offset"
        need(row == {"requirement_id": row["requirement_id"], "task_id": "task:finite:" + kind,
            "producer_id": "producer:finite:" + kind, "path": "calc.py", "function_name": "increment", "parameter": "n",
            "review_ref": "review:authored-finite-service-operations", "operation": "update"}, "reviewed operation relabeled or retargeted")
    receipt = _envelope(admission["receipt"])
    need(receipt.get("schema") == "supervisor-finite-repository-admission@1"
        and admission["receipt"]["binding"]["identity"] == declaration["manifest"]["binding"]["identity"]
        and receipt.get("declaration_cid") == cid(admission["declaration"])
        and receipt.get("graph_cid") == cid(graph) and receipt.get("evidence_cid") == cid(admission["evidence"]), "signed admission reference drift")
    semantic = receipt["semantic_context"]
    need(receipt.get("semantic_context_cid") == cid(semantic), "semantic context digest drift")
    _false(receipt, FALSE_FLAGS)
    _false(receipt["policy"], FALSE_FLAGS)
    _false(semantic, FALSE_FLAGS)
    need(receipt["policy"].get("preserve_complete_administrator_task_population") is True
        and receipt["policy"].get("finite_facts_are_context_only") is True and receipt["policy"].get("models") == "off", "fixed task-population model-off policy changed")
    expected_native = {clause: {"task_key": key, "task_cid": by_task[key]["content_id"]} for clause, key in TASK_BINDINGS.items()}
    need(semantic.get("native_task_bindings") == expected_native
        and semantic.get("administrator_task_cids") == sorted(row["content_id"] for row in tasks)
        and semantic.get("task_population_preserved") is True, "full signed native task identity population changed")
    eligible = sorted(TASK_BINDINGS) if successor else [TYPE_CLAUSE]
    residual = [] if successor else [OFFSET_CLAUSE]
    selected = [] if successor else ["task:finite:offset"]
    evidence = admission["evidence"]
    match = evidence["match"]
    _false(evidence, CAPACITY_FALSE)
    _false(match, MATCH_FALSE)
    _assert_query_and_predicates(declaration, document, semantic, match)
    need(evidence.get("schema") == "finite-integer-capacity-bound-plan-preview@2"
        and type(evidence.get("planning_model_calls")) is int and evidence["planning_model_calls"] == 0
        and type(evidence.get("training_steps_during_preview")) is int and evidence["training_steps_during_preview"] == 0,
        "exact supported model-off capacity profile required")
    need(semantic.get("head") == match.get("head") == head and semantic.get("source_cid") == match.get("source_cid")
        and match.get("source_cid") == match["observation"].get("source_cid") == evidence["operational_model"].get("source_cid")
        and semantic.get("eligible_requirement_ids") == match.get("eligible_clause_ids") == eligible
        and semantic.get("residual_requirement_ids") == match.get("residual_clause_ids") == residual
        and semantic.get("finite_selected_task_ids") == evidence.get("selected_task_ids") == selected,
        "complete finite type/offset partition or selected task changed")
    need(exact(semantic.get("domain_inputs"), DOMAIN) and exact(match.get("domain_inputs"), DOMAIN), "exact integer domain inputs required")
    rows = semantic.get("observations")
    expected_rows = [{"input": value, "input_type": "int", "output": value + (2 if successor else 1), "output_type": "int"} for value in DOMAIN]
    need(exact(rows, expected_rows) and exact(match["observation"].get("observations"), expected_rows), "complete exact-integer observation rows required")
    facts = match.get("current_facts")
    mapping = match["typed_intent"]["metadata"]["requirement_predicate_ids"]
    need(type(facts) is list and len(facts) == len(eligible)
        and {row["predicate"]["predicate_id"] for row in facts} == {mapping[key] for key in eligible}
        and all(row.get("authority") == "bounded_observation" for row in facts), "bounded facts relabeled or upgraded")
    desired = {row["predicate_id"]: row for row in match["typed_intent"]["desired_predicates"]}
    for fact in facts:
        predicate = desired.get(fact["predicate"]["predicate_id"])
        need(predicate is not None and exact(fact["predicate"], predicate) and fact.get("truth") == "true"
             and fact.get("current_root_id") == head["snapshot_cid"]
             and fact.get("invalidation_selectors") == predicate["invalidation_selectors"],
             "bounded fact truth, meaning, root or selectors changed")
    need(receipt.get("planning_permitted") is (not successor) and receipt.get("no_work_review_only") is successor,
        "historical local planning versus no-work review scope changed")
    if successor:
        need(admission["local_admission"] is None and receipt.get("local_admission_cid") is None, "no-work receipt cannot omit tasks or grant local admission")
    else:
        local = admission["local_admission"]
        need(type(local) is dict and local.get("manifest") == declaration["manifest"] and local.get("graph") == graph
            and receipt.get("local_admission_cid") == cid(local), "complete signed local admission detached from original tasks")
        local_receipt = _envelope(local["receipt"])
        _false(local_receipt, {"code_proof_authority", "completion_authority", "production_activation"})
        need(local_receipt.get("planning_permitted") is True, "historical local planning receipt differs")
    return {"task_keys": sorted(by_task), "task_cids": semantic["administrator_task_cids"],
        "eligible_requirement_ids": eligible, "residual_requirement_ids": residual,
        "planning_permitted_historically": receipt["planning_permitted"], "no_work_review_only": successor}


def load_fixture(reader: ArtifactReader) -> dict[str, Any]:
    records = {name: reader.record(name) for name in RECORDS}
    materialized = records["materialized.json"]
    reference = materialized["finite_admission_ref"]
    need(reference.get("schema") == "supervisor-finite-repository-admission-reference@1"
        and type(reference.get("bytes")) is int and 0 < reference["bytes"] <= MAX_FILE_BYTES,
        "bounded complete admission reference required")
    raw = reader.read(Path(reference["path"]))
    need(hashlib.sha256(raw).hexdigest() == reference.get("sha256") and len(raw) == reference["bytes"], "native plan reference byte identity drift")
    retained = parse_document(raw)
    need(retained == records["before-admission.json"] and cid(retained) == reference.get("admission_cid") == materialized.get("finite_admission_cid"), "native plan reference does not retain the complete admission")
    records["referenced_admission"] = retained
    for name, offset in (("before-admission.json", 1), ("successor-admission.json", 2), ("cold-admission.json", 2)):
        admission = records[name]
        for record in (admission["evidence"]["match"]["observation"], admission["evidence"]["operational_model"]):
            artifacts = record["artifacts"]
            need(type(artifacts) is dict and 1 <= len(artifacts) <= 16, "complete bounded native artifact population required")
            for artifact in artifacts.values():
                need(type(artifact) is dict and set(artifact) == {"path", "sha256", "size_bytes", "cid"}
                    and type(artifact["size_bytes"]) is int and 0 <= artifact["size_bytes"] <= MAX_FILE_BYTES
                    and Path(artifact["path"]).parent == Path(record["output"]), "native artifact descriptor scope differs")
                data = reader.read(Path(artifact["path"]), limit=MAX_FILE_BYTES)
                need(len(data) == artifact["size_bytes"] and hashlib.sha256(data).hexdigest() == artifact["sha256"]
                    and raw_cid(data) == artifact["cid"], "retained native artifact byte drift")
            need(reader.read(Path(record["output"]) / "result.json") == canonical(record), "complete retained native observation/model differs")
            source = reader.read(Path(artifacts["source"]["path"]))
            parsed = ast.parse(source)
            need(len(parsed.body) == 1 and type(parsed.body[0]) is ast.FunctionDef, "retained selected arithmetic source changed")
            function = parsed.body[0]
            need(function.name == "increment" and len(function.body) == 1 and type(function.body[0]) is ast.Return,
                "retained selected function or guard changed")
            arguments = function.args
            need(len(arguments.args) == 1 and arguments.args[0].arg == "n"
                 and type(arguments.args[0].annotation) is ast.Name and arguments.args[0].annotation.id == "int"
                 and type(function.returns) is ast.Name and function.returns.id == "int"
                 and not arguments.posonlyargs and not arguments.kwonlyargs and arguments.vararg is None
                 and arguments.kwarg is None and not arguments.defaults and not arguments.kw_defaults
                 and not function.decorator_list, "retained source outside exact integer profile")
            value = function.body[0].value
            need(type(value) is ast.BinOp and type(value.op) is ast.Add and type(value.left) is ast.Name
                and value.left.id == "n" and type(value.right) is ast.Constant and type(value.right.value) is int
                and value.right.value == offset, "retained arithmetic body/offset differs")
            need(hashlib.sha256(source).hexdigest() == admission["declaration"]["payload"]["manifest"]["payload"]["sources"]["calc.py"]["sha256"],
                "native observed source detached from signed original manifest")
            need(record.get("source_cid") == raw_cid(source), "native source content identity differs")
    return records


def assert_fixture(records: dict[str, Any]) -> dict[str, Any]:
    result = records["result.json"]
    need(result.get("schema") == "finite-repository-admission-qualification@1" and result.get("status") == "completed", "complete retained producer fixture required")
    baseline = records["before-admission.json"]
    need(records["before-declaration.json"] == baseline["declaration"], "original declaration replaced")
    population = assert_admission(baseline, successor=False)
    successor = assert_admission(records["successor-admission.json"], successor=True)
    assert_admission(records["cold-admission.json"], successor=True)
    need(records["referenced_admission"] == baseline, "full signed reference population reduced")
    materialized = records["materialized.json"]
    _false(materialized, FALSE_FLAGS)
    _false(materialized["finite_admission_ref"], {"execution_authority", "completion_authority", "mutation_authority"})
    need(materialized.get("administrator_task_population_preserved") is True
        and materialized.get("task_cids") == result.get("task_cids") == population["task_cids"], "materialized original task population changed")
    replay = records["fresh-process-replay.json"]
    need(replay == result.get("fresh_process_historical_replay") and replay.get("verified") is True
        and replay.get("tasks_present") is True and replay.get("current_freshness_claimed") is False
        and replay.get("worker_launched") is False and type(replay.get("training_steps")) is int and replay["training_steps"] == 0
        and replay.get("task_statuses") == {"FINITE-TYPE": "completed", "FINITE-OFFSET": "in_progress"}, "retained historical task statuses or scope changed")
    need(result.get("complete_task_population_committed") is True and result.get("task_omission_authority") is False
        and result.get("worker_launched") is False and result.get("production_activated") is False
        and result.get("public_type_check_passed") is True and result.get("public_offset_check_passed") is False
        and result.get("native_worker_successor_loop_qualified") is False,
        "retained result falsely grants completion, omission or native worker authority")
    need(baseline["declaration"]["payload"]["head"] == result["original_head"]
        and records["successor-admission.json"]["declaration"]["payload"]["head"] == result["successor_head"]
        and result["original_head"]["snapshot_cid"] != result["successor_head"]["snapshot_cid"], "original/successor generation identities collapsed")
    comparison = records["cold-comparison.json"]
    compared = ["source_cid", "query", "domain_inputs", "observations", "eligible_requirement_ids", "residual_requirement_ids",
        "finite_selected_task_ids", "operation_catalog_cid", "model_status"]
    incremental = records["successor-admission.json"]["receipt"]["payload"]["semantic_context"]
    cold = records["cold-admission.json"]["receipt"]["payload"]["semantic_context"]
    need(comparison.get("agreement") is True and comparison.get("compared_fields") == compared
        and comparison.get("incremental_head") == incremental["head"] and comparison.get("cold_head") == cold["head"]
        and not exact(incremental["head"], cold["head"])
        and all(exact(incremental[field], cold[field]) for field in compared)
        and result.get("incremental_cold_finite_outcomes_agree") is True,
        "complete cold/incremental finite comparison or distinct generation envelopes changed")
    return {"actual_preserved_task_population": {**population, "source": "retained_signed_graph_materialization_and_producer_historical_replay",
        "native_task_store_reopened": False}, "successor": successor}


def mutation_controls(records: dict[str, Any]) -> list[dict[str, Any]]:
    controls = []
    for name in ("drop_original_task", "swap_clause_tasks", "retarget_decoy", "drop_prerequisite", "wrong_native_cid",
            "relabel_fact", "boolean_row", "reduced_reference", "grant_authority", "change_manifest_version", "grant_no_work",
            "foreign_validation_executable", "foreign_validation_policy", "missing_authority_flag", "false_fact",
            "relabel_fact_property", "retarget_query", "grant_inner_local_authority", "relabel_predicate_mapping",
            "correlated_source_label", "drop_cold_comparison", "empty_signed_producer_pins", "partial_signed_producer_pins",
            "extra_signed_producer_pins", "invalid_signed_producer_hash", "empty_model_frontend_pins", "partial_model_frontend_pins",
            "extra_model_frontend_pins", "invalid_model_frontend_hash"):
        changed = copy.deepcopy(records)
        admission = changed["before-admission.json"]
        declaration = admission["declaration"]["payload"]
        if name == "drop_original_task":
            declaration["manifest"]["payload"]["tasks"].pop()
        elif name == "swap_clause_tasks":
            declaration["task_bindings"] = {TYPE_CLAUSE: "FINITE-OFFSET", OFFSET_CLAUSE: "FINITE-TYPE"}
        elif name == "retarget_decoy":
            declaration["operation_catalog"]["operations"][0]["path"] = "decoy.py"
        elif name == "drop_prerequisite":
            next(row for row in admission["graph"]["tasks"] if row["task_key"] == "FINITE-OFFSET")["dependency_task_cids"] = []
        elif name == "wrong_native_cid":
            admission["receipt"]["payload"]["semantic_context"]["native_task_bindings"][TYPE_CLAUSE]["task_cid"] = "foreign:task"
        elif name == "relabel_fact":
            admission["evidence"]["match"]["current_facts"][0]["authority"] = "proved"
        elif name == "boolean_row":
            admission["receipt"]["payload"]["semantic_context"]["observations"][3]["input"] = True
        elif name == "reduced_reference":
            changed["referenced_admission"]["graph"]["tasks"].pop()
        elif name == "grant_authority":
            admission["receipt"]["payload"]["execution_authority"] = True
        elif name == "change_manifest_version":
            declaration["manifest"]["payload"]["schema"] = "supervisor-local-benchmark-manifest@2"
        elif name == "grant_no_work":
            changed["successor-admission.json"]["receipt"]["payload"]["planning_permitted"] = True
        elif name.startswith("foreign_validation"):
            field, value = ("argv", ["/foreign/python", "check_offset.py"]) if name.endswith("executable") else ("policy_cid", "foreign:policy")
            admission["graph"]["tasks"][0]["validations"][0][field] = value
        elif name == "missing_authority_flag":
            admission["receipt"]["payload"].pop("execution_authority")
        elif name == "false_fact":
            admission["evidence"]["match"]["current_facts"][0]["truth"] = "false"
        elif name == "relabel_fact_property":
            admission["evidence"]["match"]["current_facts"][0]["predicate"]["property_id"] = "finite_integer_offset"
        elif name == "retarget_query":
            admission["receipt"]["payload"]["semantic_context"]["query"]["contract"]["path"] = "decoy.py"
        elif name == "grant_inner_local_authority":
            admission["local_admission"]["receipt"]["payload"]["execution_authority"] = True
        elif name == "relabel_predicate_mapping":
            match = admission["evidence"]["match"]
            match["typed_intent"]["metadata"]["requirement_predicate_ids"][TYPE_CLAUSE] = "foreign:predicate"
            match["current_facts"][0]["predicate"]["predicate_id"] = "foreign:predicate"
        elif name == "correlated_source_label":
            admission["evidence"]["match"]["source_cid"] = "foreign:source"
            admission["receipt"]["payload"]["semantic_context"]["source_cid"] = "foreign:source"
        elif name == "drop_cold_comparison":
            changed["cold-comparison.json"]["agreement"] = False
            changed["cold-comparison.json"]["compared_fields"] = []
        else:
            group = "signed_producer" if "signed_producer" in name else "model_frontend"
            pins = source_pin_groups(admission)[group]
            if name.startswith("empty_"):
                pins.clear()
            elif name.startswith("partial_"):
                pins.pop(next(iter(pins)))
            elif name.startswith("extra_"):
                pins["foreign.extra_module"] = "a" * 64
            else:
                pins[next(iter(pins))] = "A" * 64
        # Correlate edited declarations and rehash unsigned parent references;
        # no signatures are issued and these copies never become native evidence.
        changed["before-declaration.json"] = copy.deepcopy(admission["declaration"])
        if admission["local_admission"] is not None:
            admission["local_admission"]["manifest"] = copy.deepcopy(admission["declaration"]["payload"]["manifest"])
            admission["local_admission"]["graph"] = copy.deepcopy(admission["graph"])
        receipt = admission["receipt"]["payload"]
        receipt.update({"declaration_cid": cid(admission["declaration"]), "graph_cid": cid(admission["graph"]),
            "evidence_cid": cid(admission["evidence"]), "semantic_context_cid": cid(receipt["semantic_context"]),
            "local_admission_cid": cid(admission["local_admission"])})
        if name != "reduced_reference":
            changed["referenced_admission"] = copy.deepcopy(admission)
        try:
            assert_fixture(changed)
        except AdmissionEvidenceError as exc:
            controls.append({"mutation_id": name, "outcome": "refused", "exception": type(exc).__name__, "message": str(exc),
                "scope": "authored_structural_corruption_no_signature_authority"})
        else:
            raise AssertionError("corrupted retained admission accepted: " + name)
    return controls


def run(fixture_root: Path, output: Path, *, historical_replay: bool = False, replay_python: Path | None = None,
        workspace: Path | None = None, snapshot_roots: list[Path] | None = None, snapshot_sha256: str | None = None) -> dict[str, Any]:
    need(not output.exists(), "admission audit output must be fresh")
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    reader = ArtifactReader(fixture_root)
    report: dict[str, Any] = {"schema": SCHEMA, "status": "incomplete", "started_at": datetime.now(UTC).isoformat(),
        "fixture_root": str(reader.root), "historical_verification": {"status": "not_requested", "observed_current": False,
            "current_launch_permission_claimed": False}, "signature_authentication_performed_by_structural_audit": False,
        "native_worker_launched": False, "task_store_opened": False, "training_steps": 0,
        "manifest_version_coverage": {"1": {"retained_fixture_exercised": False},
            "2": {"independently_exercised": False, "status": "unqualified"},
            "3": {"independently_exercised": False, "status": "unqualified"},
            "4": {"independently_exercised": False, "producer_profile_status": "rejected"}}}
    try:
        records = load_fixture(reader)
        report["input_result_sha256"] = reader.pins[str(reader.root / "result.json")]["sha256"]
        report.update(assert_fixture(records))
        report["manifest_version_coverage"]["1"]["retained_fixture_exercised"] = True
        manifest = records["before-admission.json"]["declaration"]["payload"]["manifest"]["payload"]
        current = reader.read(reader.root / "repository" / "calc.py")
        report["retained_current_source_comparison"] = {"path": "calc.py", "current_sha256": hashlib.sha256(current).hexdigest(),
            "original_signed_sha256": manifest["sources"]["calc.py"]["sha256"],
            "matches_original_signed_source": hashlib.sha256(current).hexdigest() == manifest["sources"]["calc.py"]["sha256"],
            "scope": "byte_comparison_only_no_current_native_verification"}
        controls = mutation_controls(records)
        report.update({"structural_controls": controls, "structural_control_count": len(controls), "structural_controls_refused": len(controls)})
        if historical_replay:
            from codebase_ir_admission_history import launch_historical_replay
            report["historical_verification"] = launch_historical_replay(reader.root, output,
                python=replay_python or Path(sys.executable).absolute(), expected_result_sha256=report["input_result_sha256"],
                workspace=workspace or Path.cwd(), snapshot_roots=snapshot_roots, snapshot_sha256=snapshot_sha256)
        report["status"] = "passed"
    except (ValueError, OSError, KeyError, TypeError, RecursionError, SyntaxError) as exc:
        report.update({"status": "refused", "error": f"{type(exc).__name__}: {exc}"})
    finally:
        try:
            report["retained_artifacts_unchanged"] = reader.recheck()
        except (ValueError, OSError) as exc:
            report.update({"status": "refused", "error": f"{type(exc).__name__}: {exc}", "retained_artifacts_unchanged": False})
        report["artifact_pins"] = [{"path": path, **pin} for path, pin in sorted(reader.pins.items())]
        report["artifact_total_bytes"] = reader.total
        report["finished_at"] = datetime.now(UTC).isoformat()
        (output / "admission_evidence.json").write_bytes(canonical(report) + b"\n")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--historical-replay", action="store_true")
    parser.add_argument("--replay-python", type=Path)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--snapshot-root", type=Path, action="append", help="sealed historical core import root; repeat for accelerate/datasets")
    parser.add_argument("--snapshot-sha256", help="canonical release generation identity verified before and after historical replay")
    args = parser.parse_args(argv)
    try:
        report = run(args.fixture_root, args.output, historical_replay=args.historical_replay, replay_python=args.replay_python,
                     workspace=args.workspace, snapshot_roots=args.snapshot_root, snapshot_sha256=args.snapshot_sha256)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"retained admission audit refused: {exc}\n")
    print(json.dumps({"status": report["status"], "report": str(args.output / "admission_evidence.json"),
        "historical_status": report["historical_verification"]["status"], "current_launch_permission_claimed": False}))
    return 0 if (report["status"] == "passed" and report["historical_verification"]["status"] in {"not_requested", "passed"}) else 3


if __name__ == "__main__":
    raise SystemExit(main())
