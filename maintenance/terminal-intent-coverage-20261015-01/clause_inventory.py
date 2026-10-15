"""Lossless instruction accounting and explicitly authored candidate atoms.

Line classification is bookkeeping, not a language parser.  The native no-model
frontend and the separately authored labels are retained as different reports.
Neither report proves that an atom means the source text or that a task succeeds.
"""
from __future__ import annotations

import hashlib
import json
import re

SCHEMA = "terminal-instruction-clause-inventory@1"
MAX_SOURCE_BYTES = 1_048_576
TASK_OUTPUTS = {
    "headless-terminal": ("headless_terminal.py",),
    "feal-differential-cryptanalysis": ("attack.py",),
    "break-filter-js-from-html": ("out.html",),
    "llm-inference-batching-scheduler": (
        "task_file/output_data/plan_b1.jsonl", "task_file/output_data/plan_b2.jsonl"),
}
# These labels were authored for exact public surfaces.  Their predicates have
# no independently established semantic relation to those surfaces.  Small
# subspans deliberately leave relative clauses, runtime bounds and context open.
_CANDIDATES = {
    "headless-terminal": (
        ("interface", "Implement the provided `BaseTerminal` interface.",
         "implement_interface", ("agent", "BaseTerminal")),
        ("interactive", "Supports interactive programs", "support_interactive_programs",
         ("HeadlessTerminal", "interactive_programs")),
        ("dependencies", "Install dependencies into the system python.",
         "install_dependencies", ("agent", "system_python")),
    ),
    "feal-differential-cryptanalysis": (
        ("attack", "Implement a chosen plaintext attack", "implement_attack",
         ("agent", "chosen_plaintext_attack")),
    ),
    "break-filter-js-from-html": (
        ("output", "create a file called /app/out.html", "create_output_file",
         ("agent", "/app/out.html")),
    ),
    "llm-inference-batching-scheduler": (
        ("bucket1-output", "  1) ``/app/task_file/output_data/plan_b1.jsonl`` (for requests_bucket_1.jsonl)",
         "create_output_file", ("agent", "/app/task_file/output_data/plan_b1.jsonl")),
        ("bucket2-output", "  2) ``/app/task_file/output_data/plan_b2.jsonl`` (for requests_bucket_2.jsonl)",
         "create_output_file", ("agent", "/app/task_file/output_data/plan_b2.jsonl")),
    ),
}
_FLAGS = dict(semantic_alignment_verified=False, source_semantics_verified=False,
    semantic_support_complete=False, proof_authority=False, execution_authority=False,
    completion_authority=False, omission_authority=False, full_task_satisfaction=False,
    source_to_model_equivalence=False, convergence_proved=False,
    native_original_task_admission=False)


class InstructionInventoryError(ValueError):
    """Exact original source or deterministic accounting does not match."""


def _wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False).encode("utf-8")


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _source(task_id, instruction):
    if type(task_id) is not str or task_id not in TASK_OUTPUTS:
        raise InstructionInventoryError("one of the four declared public task identities required")
    if type(instruction) is not bytes or not 0 < len(instruction) <= MAX_SOURCE_BYTES:
        raise InstructionInventoryError("bounded nonempty exact UTF-8 instruction bytes required")
    try:
        text = instruction.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise InstructionInventoryError("strict UTF-8 instruction required") from exc
    if "\0" in text:
        raise InstructionInventoryError("instruction cannot contain NUL")
    return text


def _manual_ledger(task_id, text, instruction):
    from ipfs_datasets_py.logic.intent_ir import schema
    from ipfs_datasets_py.logic.intent_ir.canonicalize import canonical_intent_ir_bytes
    from ipfs_datasets_py.logic.intent_ir.decoder import decode_intent_ir
    from ipfs_datasets_py.logic.intent_ir.formalize.requirements import (
        build_intent_requirement_ledger, validate_intent_requirement_ledger)

    digest = _sha(instruction)
    units, candidates, documents = [], [], []
    for name, surface, predicate, arguments in _CANDIDATES[task_id]:
        # Duplicate occurrences are ambiguous; they remain unsupported input.
        if text.count(surface) != 1:
            continue
        left, right = text.index(surface), text.index(surface) + len(surface)
        ref_id = "source:" + task_id + ":" + name
        document_id = "manual-candidate:" + task_id + ":" + name
        source = schema.SourceRef(ref_id, "terminal-bench-2:" + task_id + "/instruction.md",
            task_id + "/instruction.md", "sha256:" + digest, digest,
            review_status=schema.ReviewStatus.UNREVIEWED, span=schema.SourceSpan(left, right))
        statement = schema.IntentStatement("goal:" + task_id + ":" + name,
            schema.StatementKind.GOAL, schema.IntentModality.REQUIRED, surface.strip(), (ref_id,),
            predicate, arguments, confidence=0.0, review_status=schema.ReviewStatus.UNREVIEWED,
            grounding=schema.NodeGrounding.INFERRED)
        document = schema.IntentIRDocument(document_id,
            "Explicitly authored source-bound candidate label", schema.IntentKind.DECLARATIVE,
            (source,), (statement,), tags=("manual-candidate", "unverified", "no-semantic-parser"))
        native = decode_intent_ir(document.to_dict())
        documents.append({"document": native.to_dict(),
            "canonical_sha256": _sha(canonical_intent_ir_bytes(native))})
        units.append({"unit_id": "authored-clause:" + task_id + ":" + name,
            "start_char": left, "end_char": right,
            "start_byte": len(text[:left].encode("utf-8")),
            "end_byte": len(text[:right].encode("utf-8")), "text": surface,
            "sha256": _sha(surface.encode("utf-8")), "disposition": "interpreted_candidate",
            "reason": "explicitly_authored_unreviewed_candidate_not_semantic_inference"})
        candidates.append({"unit_id": units[-1]["unit_id"], "candidate_intent_ir": native.to_dict()})
    paired = sorted(zip(units, candidates, documents), key=lambda triple: triple[0]["start_char"])
    units, candidates, documents = ([item[n] for item in paired] for n in range(3))
    report = {"schema": "intent-reviewed-source-report@1", "source_sha256": digest,
        "source_bytes": len(instruction), "source_characters": len(text),
        "producer": {"name": "explicitly-authored-unreviewed-terminal-clause-labels", "revision": "1"},
        "interpretation_status": "reviewed_candidate", "units": units, "candidates": candidates,
        "proof_authority": False, "execution_authority": False, "completion_authority": False,
        "source_semantics_verified": False}
    # The native schema calls this a reviewed report, but no human review or
    # meaning validation was performed.  Native node review states stay unreviewed.
    report["report_sha256"] = _sha(_wire(report))
    ledger = build_intent_requirement_ledger(text, source_report=report,
        source_identity={"task_id": task_id, "instruction_sha256": digest,
            "interpretation": "explicit_authored_candidate_labels_not_automated_semantic_matching"})
    validate_intent_requirement_ledger(ledger, source_text=text)
    return ledger, documents


def _classification(line, selected, *, in_code):
    value = line.strip()
    if not value:
        return "whitespace", "exact_whitespace_retained"
    if in_code or value.startswith("```"):
        return "context_frontier", "code_example_not_executable_authority"
    if value.startswith("|"):
        return "compound_frontier", "table_relations_and_numeric_thresholds_uninterpreted"
    if value.startswith("**") or value in {"Good luck!"}:
        return "context_frontier", "document_structure_or_context_retained"
    if selected:
        remainder = line
        for row in selected:
            remainder = remainder.replace(row["text"], "", 1)
        if not remainder.strip().strip("-").strip():
            return "authored_atomic_candidate", "only_an_unreviewed_authored_atom_not_verified_meaning"
        return "compound_frontier", "partial_authored_atom_leaves_other_source_context_uninterpreted"
    if re.search(r"\b(all|every|each|exactly|across|maximum|less than|unchanged|after|when|because|and|where|should|must)\b|[<>]=?|\b\d+\b", value, re.I):
        return "compound_frontier", "quantified_numeric_conditional_or_composed_scope_uninterpreted"
    if value.startswith(("Background", "Usage:", "The ", "There's ", "To aid", "A cost", "During ")):
        return "context_frontier", "source_context_retained_without_semantic_discharge"
    return "uninterpreted_frontier", "no_verified_semantic_interpretation"


def _line_units(task_id, text, documents):
    clauses = []
    for entry in documents:
        document = entry["document"]
        source = document["sources"][0]
        span = source["span"]
        clauses.append({"start_char": span["start_char"], "end_char": span["end_char"],
            "text": text[span["start_char"]:span["end_char"]],
            "document_id": document["document_id"]})
    units, offset, in_code = [], 0, False
    for ordinal, line in enumerate(text.splitlines(keepends=True), 1):
        right = offset + len(line)
        selected = [row for row in clauses if row["start_char"] < right and row["end_char"] > offset]
        classification, reason = _classification(line, selected, in_code=in_code)
        units.append({"unit_id": "instruction-line:" + task_id + ":" + str(ordinal),
            "start_char": offset, "end_char": right,
            "start_byte": len(text[:offset].encode("utf-8")),
            "end_byte": len(text[:right].encode("utf-8")), "text": line,
            "sha256": _sha(line.encode("utf-8")), "classification": classification,
            "reason": reason, "candidate_document_ids": [row["document_id"] for row in selected]})
        if line.strip().startswith("```"):
            in_code = not in_code
        offset = right
    if "".join(row["text"] for row in units) != text or offset != len(text):
        raise InstructionInventoryError("line inventory must partition the entire original source")
    return units


def _coverage(task_id, text, ledger):
    from ipfs_accelerate_py.agent_supervisor.prompt.intent_plan_coverage import (
        build_intent_requirement_contract, check_intent_plan_coverage)
    from ipfs_accelerate_py.agent_supervisor.prompt.prompt_workflow import (
        PromptAcceptanceRecord, PromptGoalGraph, PromptGoalRecord, PromptOutputRecord,
        PromptTaskRecord, PromptValidationRecord, prompt_workflow_cid)

    validation = "validation:" + task_id + ":original-task-pending"
    outputs = [{"path": path, "effect": "create", "media_type":
        "application/jsonl" if path.endswith(".jsonl") else "text/html" if path.endswith(".html") else "text/x-python"}
        for path in TASK_OUTPUTS[task_id]]
    requirements = [{"requirement_id": row["requirement_id"], "outputs": outputs,
        "validation_keys": [validation], "dependency_requirement_ids": []}
        for row in ledger["requirements"]]
    contract = build_intent_requirement_contract(source_path="instruction.md", ledger=ledger,
        requirements=requirements, source_text=text)
    root = prompt_workflow_cid({"schema": SCHEMA, "task_id": task_id,
        "instruction_sha256": ledger["source"]["sha256"]})
    acceptance = PromptAcceptanceRecord(criterion_key="criterion:" + task_id + ":pending",
        criterion="The original complete task and validation remain unresolved.",
        validation_keys=(validation,))
    goal = PromptGoalRecord(goal_key="goal:" + task_id + ":candidate", parent_goal_cid="",
        dependency_goal_cids=(), title="Unverified original task proposal",
        objective="Retain complete instructions and unresolved requirements before execution.",
        rationale="Explicitly authored administrative candidate only.",
        scope_paths=tuple(row["path"] for row in outputs), acceptance=(acceptance,))
    task = PromptTaskRecord(task_key="task:" + task_id + ":candidate", goal_cid=goal.goal_cid,
        dependency_task_cids=(), objective=goal.objective, rationale=goal.rationale,
        scope_paths=goal.scope_paths, outputs=tuple(PromptOutputRecord(**row) for row in outputs),
        validations=(PromptValidationRecord(validation_key=validation, argv=("python", "-m", "pytest")),),
        acceptance=(acceptance,), evidence_cids=(), policy_roots=(root,))
    graph = PromptGoalGraph(request_cid=root, scan_cid=root, program_root=root,
        policy_roots=(root,), goals=(goal,), tasks=(task,), evidence=())
    bindings = [{"requirement_id": row["requirement_id"], "task_keys": [task.task_key],
        "validation_keys": [validation]} for row in ledger["requirements"]]
    receipt = check_intent_plan_coverage(contract, graph=graph, bindings=bindings)
    if receipt["accepted"] or not any(row["code"] == "unsupported_source_units" for row in receipt["errors"]):
        raise InstructionInventoryError("incomplete original instruction must remain rejected by native coverage")
    return {"contract": contract, "graph": graph.to_dict(), "bindings": bindings,
        "receipt": receipt, "validation_commands_executed": False,
        "graph_is_authored_proposal": True, "native_original_task_admission": False,
        "grounding_semantics_verified": False, "status": "blocked_unresolved_original_instruction"}


def build_instruction_inventory(*, task_id, instruction: bytes):
    """Account for every byte, retaining native and authored interpretations apart."""
    text = _source(task_id, instruction)
    from ipfs_datasets_py.logic.intent_ir.formalize.document_roundtrip import (
        prepare_intent_document, validate_intent_document_report)
    from ipfs_datasets_py.logic.intent_ir.formalize.requirements import (
        build_intent_requirement_ledger, validate_intent_requirement_ledger)

    baseline = prepare_intent_document(text, checkpoint_descriptor=None)
    validate_intent_document_report(baseline, source_text=text, checkpoint_descriptor=None)
    if baseline["candidates"] or any(baseline[key] != 0 for key in
            ("training_steps", "provider_calls", "download_calls")):
        raise InstructionInventoryError("no-checkpoint baseline must not acquire inferred candidates or external work")
    baseline_ledger = build_intent_requirement_ledger(text, source_report=baseline,
        source_identity={"task_id": task_id, "instruction_sha256": _sha(instruction),
            "interpretation": "native_full_document_frontend_without_checkpoint"})
    validate_intent_requirement_ledger(baseline_ledger, source_text=text)
    ledger, documents = _manual_ledger(task_id, text, instruction)
    units = _line_units(task_id, text, documents)
    report = {"schema": SCHEMA, "task_id": task_id,
        "instruction": {"sha256": _sha(instruction), "bytes": len(instruction),
            "characters": len(text), "text": text}, "units": units,
        "classification_scope": "deterministic_line_bookkeeping_not_semantic_parser",
        "candidate_interpretation": "explicit_authored_unreviewed_labels_not_learned_inference",
        "candidate_presentation_normalization": "outer_whitespace_trim_on_native_normalized_text_only",
        "native_reviewed_report_schema_is_not_human_review": True,
        "native_frontend_report": baseline,
        "native_frontend_requirement_ledger": baseline_ledger,
        "native_requirement_ledger": ledger, "native_intent_documents": documents,
        "native_coverage": _coverage(task_id, text, ledger),
        "residual_source_units": [row for row in ledger["source_units"] if row["disposition"] == "unsupported"],
        # Candidate labels have no verified meaning, so they discharge no
        # semantic requirement.  Retain entire original lines, not only gaps
        # left outside the authored native candidates.
        "semantic_residual_units": [row for row in units if row["text"].strip()],
        "semantic_residual_unit_count": sum(bool(row["text"].strip()) for row in units),
        "verified_semantic_unit_count": 0,
        "source_accounting_complete": True, "raw_instruction_preserved": True,
        "learned_inference_executed": False, "training_steps": 0, "provider_calls": 0,
        "download_calls": 0, **_FLAGS}
    report["report_sha256"] = _sha(_wire(report))
    return report


def validate_instruction_inventory(report, *, task_id, instruction: bytes):
    """Replay exact source accounting and native checks, without semantic promotion."""
    if type(report) is not dict:
        raise InstructionInventoryError("exact instruction inventory object required")
    expected = build_instruction_inventory(task_id=task_id, instruction=instruction)
    try:
        if _wire(report) != _wire(expected):
            raise InstructionInventoryError("inventory differs from deterministic source/native reconstruction")
    except (TypeError, ValueError, RecursionError) as exc:
        if isinstance(exc, InstructionInventoryError):
            raise
        raise InstructionInventoryError("bounded JSON instruction inventory required") from exc
    return report


__all__ = ["build_instruction_inventory", "validate_instruction_inventory", "InstructionInventoryError"]
