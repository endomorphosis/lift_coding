"""Checks for complete byte accounting and deliberately limited native scope."""
from copy import deepcopy
import hashlib
from pathlib import Path

import pytest

from clause_inventory import (InstructionInventoryError, TASK_OUTPUTS,
    build_instruction_inventory, validate_instruction_inventory)

INSTRUCTIONS = Path(__file__).resolve().parent.parent / "terminal-planning-admission-20261015-01" / "experiment-01" / "instructions"


@pytest.fixture(scope="module")
def inventories():
    return {task_id: build_instruction_inventory(task_id=task_id,
        instruction=(INSTRUCTIONS / task_id / "instruction.md").read_bytes())
        for task_id in TASK_OUTPUTS}


@pytest.mark.parametrize("task_id", tuple(TASK_OUTPUTS))
def test_full_source_accounting_and_native_rejection(inventories, task_id):
    report = inventories[task_id]
    raw = (INSTRUCTIONS / task_id / "instruction.md").read_bytes()
    assert validate_instruction_inventory(report, task_id=task_id, instruction=raw) is report
    assert "".join(row["text"] for row in report["units"]).encode() == raw
    assert [row["text"] for row in report["units"]] == raw.decode().splitlines(keepends=True)
    assert report["source_accounting_complete"] is True
    assert report["semantic_support_complete"] is False
    assert report["native_coverage"]["receipt"]["accepted"] is False
    assert any(row["code"] == "unsupported_source_units" for row in report["native_coverage"]["receipt"]["errors"])
    for ledger_key in ("native_frontend_requirement_ledger", "native_requirement_ledger"):
        ledger = report[ledger_key]
        assert "".join(row["text"] for row in ledger["source_units"]).encode() == raw
        assert ledger["source_accounting_complete"] is True
        assert ledger["semantic_support_complete"] is False
        assert all(row["disposition"] != "non_requirement" or not row["text"].strip()
            for row in ledger["source_units"])
    assert report["native_frontend_report"]["candidates"] == []
    assert report["learned_inference_executed"] is False
    assert report["native_original_task_admission"] is False
    assert report["native_coverage"]["validation_commands_executed"] is False
    assert report["semantic_residual_units"] == [row for row in report["units"] if row["text"].strip()]
    assert report["semantic_residual_unit_count"] == len(report["semantic_residual_units"])
    assert report["verified_semantic_unit_count"] == 0


def test_scheduler_unicode_bytes_are_not_character_offsets(inventories):
    report = inventories["llm-inference-batching-scheduler"]
    raw = report["instruction"]["text"].encode()
    assert len(raw) == 4365
    assert report["instruction"]["characters"] == 4346
    assert any(row["start_byte"] != row["start_char"] for row in report["units"])
    for row in report["units"]:
        assert raw[row["start_byte"]:row["end_byte"]] == row["text"].encode()
        assert hashlib.sha256(row["text"].encode()).hexdigest() == row["sha256"]


def test_complex_scheduler_requirements_never_become_supported_atoms(inventories):
    report = inventories["llm-inference-batching-scheduler"]
    complex_rows = [row for row in report["units"] if any(value in row["text"] for value in
        ("exactly once", "Max 8", "ceil(", "| ``requests_bucket_", "unchanged"))]
    assert len(complex_rows) >= 8
    assert all(row["classification"] == "compound_frontier" for row in complex_rows)
    assert all(row["candidate_document_ids"] == [] for row in complex_rows)
    assert len(report["native_intent_documents"]) == 2


@pytest.mark.parametrize("task_id", tuple(TASK_OUTPUTS))
def test_candidate_nodes_remain_authored_unreviewed_inferred(inventories, task_id):
    from ipfs_datasets_py.logic.intent_ir.decoder import decode_intent_ir
    from ipfs_datasets_py.logic.intent_ir.canonicalize import canonical_intent_ir_bytes
    report = inventories[task_id]
    assert report["native_intent_documents"]
    for row in report["native_intent_documents"]:
        native = decode_intent_ir(row["document"])
        assert hashlib.sha256(canonical_intent_ir_bytes(native)).hexdigest() == row["canonical_sha256"]
        assert all(statement.review_status.value == "unreviewed" and statement.grounding.value == "inferred"
            and statement.confidence == 0.0 for statement in native.statements)
        assert all(source.review_status.value == "unreviewed" for source in native.sources)
        assert all(statement.kind.value == "goal" and statement.modality.value == "required"
            for statement in native.statements)


def test_candidate_presentation_trims_only_native_text_not_original_selectors(inventories):
    report = inventories["llm-inference-batching-scheduler"]
    text = report["instruction"]["text"]
    assert report["candidate_presentation_normalization"] == "outer_whitespace_trim_on_native_normalized_text_only"
    for entry in report["native_intent_documents"]:
        document = entry["document"]
        span = document["sources"][0]["span"]
        original = text[span["start_char"]:span["end_char"]]
        assert original.startswith("  ")
        assert document["statements"][0]["normalized_text"] == original.strip()
        assert any(unit["text"] == original and unit["start_char"] == span["start_char"]
            for unit in report["native_requirement_ledger"]["source_units"])
    assert "".join(row["text"] for row in report["units"]) == text


@pytest.mark.parametrize("field,value", [("classification", "authored_atomic_candidate"),
    ("text", "dropped original instructions"), ("start_byte", 99)])
def test_reclassified_or_rewritten_source_is_rejected(inventories, field, value):
    task_id = "llm-inference-batching-scheduler"
    altered = deepcopy(inventories[task_id])
    altered["units"][0][field] = value
    with pytest.raises(InstructionInventoryError):
        validate_instruction_inventory(altered, task_id=task_id,
            instruction=(INSTRUCTIONS / task_id / "instruction.md").read_bytes())


def test_whitespace_and_missing_newline_are_not_normalized():
    raw = b"\r\n  source context\r\n\nlast line  "
    report = build_instruction_inventory(task_id="headless-terminal", instruction=raw)
    assert [row["text"] for row in report["units"]] == raw.decode().splitlines(keepends=True)
    assert "".join(row["text"] for row in report["units"]).encode() == raw
    assert report["native_intent_documents"] == []
    assert report["native_coverage"]["receipt"]["accepted"] is False


def test_invalid_source_shapes_refuse():
    for raw in (b"", b"\xff", b"a\0b", "not bytes"):
        with pytest.raises(InstructionInventoryError):
            build_instruction_inventory(task_id="headless-terminal", instruction=raw)
    with pytest.raises(InstructionInventoryError):
        build_instruction_inventory(task_id="unseen-task", instruction=b"hello")


def test_native_structure_checks_do_not_validate_authored_meaning(inventories):
    # This is a control for the semantic frontier, not a fake failure test: the
    # native schema accepts a differently named predicate.  Our deterministic
    # inventory rejects that mutation, but cannot establish the original name's
    # semantic truth either.
    from ipfs_datasets_py.logic.intent_ir.decoder import decode_intent_ir
    changed = deepcopy(inventories["headless-terminal"])
    changed["native_intent_documents"][0]["document"]["statements"][0]["predicate"] = "unverified_unrelated_candidate"
    assert decode_intent_ir(changed["native_intent_documents"][0]["document"]).statements[0].predicate == "unverified_unrelated_candidate"
    with pytest.raises(InstructionInventoryError):
        validate_instruction_inventory(changed, task_id="headless-terminal",
            instruction=(INSTRUCTIONS / "headless-terminal" / "instruction.md").read_bytes())


def _resign_outer_report(report):
    import json
    report.pop("report_sha256", None)
    report["report_sha256"] = hashlib.sha256(json.dumps(report, sort_keys=True,
        separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()).hexdigest()


@pytest.mark.parametrize("mutation", ("unicode-byte-span", "drop-threshold", "rewrite-threshold",
    "semantic-promotion", "review-promotion", "hide-candidate-residual"))
def test_selfconsistent_outer_digest_cannot_erase_source_or_promote_candidates(inventories, mutation):
    task_id = "llm-inference-batching-scheduler"
    altered = deepcopy(inventories[task_id])
    if mutation == "unicode-byte-span":
        unit = next(row for row in altered["units"] if row["start_byte"] != row["start_char"])
        unit["start_byte"] = unit["start_char"]
        unit["end_byte"] = unit["end_char"]
    elif mutation == "drop-threshold":
        altered["units"] = [row for row in altered["units"] if "``3.0e11``" not in row["text"]]
    elif mutation == "rewrite-threshold":
        unit = next(row for row in altered["units"] if "``3.0e11``" in row["text"])
        unit["text"] = unit["text"].replace("``3.0e11``", "``9.0e99``")
        unit["sha256"] = hashlib.sha256(unit["text"].encode()).hexdigest()
    elif mutation == "semantic-promotion":
        altered["semantic_support_complete"] = True
        altered["verified_semantic_unit_count"] = len(altered["units"])
    elif mutation == "review-promotion":
        document = altered["native_intent_documents"][0]["document"]
        document["statements"][0]["review_status"] = "human_reviewed"
        document["statements"][0]["grounding"] = "grounded"
        document["statements"][0]["confidence"] = 1.0
    else:
        altered["semantic_residual_units"] = [row for row in altered["semantic_residual_units"]
            if not row["candidate_document_ids"]]
        altered["semantic_residual_unit_count"] = len(altered["semantic_residual_units"])
    _resign_outer_report(altered)
    with pytest.raises(InstructionInventoryError):
        validate_instruction_inventory(altered, task_id=task_id,
            instruction=(INSTRUCTIONS / task_id / "instruction.md").read_bytes())
