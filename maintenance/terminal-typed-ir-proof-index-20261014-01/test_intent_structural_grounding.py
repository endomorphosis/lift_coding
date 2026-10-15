"""Meaningful controls for real public instruction grounding and residuals."""
from copy import deepcopy
import hashlib

import pytest

from intent_structural_grounding import (
    BASE_SOURCE_SHA256, INSTRUCTION_SHA256, GroundingError, build_grounding)


INSTRUCTION = (
    'Implement the provided `BaseTerminal` interface. It provides a simple python interface to send keys to a headless terminal.\n\n'
    'Make sure it supports the following functionality.\n\n'
    '- Mimics a terminal, where the process starts as an interactive bash shell and commands are typically executed by typing characters and hitting Enter.\n'
    '- Supports interactive programs \n'
    '- Has support for modifier keys like `"\\x03"` for control C, etc.\n'
    '- Because the shell is interactive, it should source the startup files (e.g. ~/.bashrc)\n\n'
    'Call your implementation `HeadlessTerminal(BaseTerminal)` and put it in a file called `/app/headless_terminal.py` so that it can be imported as `from headless_terminal import HeadlessTerminal`. Install dependencies into the system python.\n'
)
SOURCE = '''from abc import ABC, abstractmethod


class BaseTerminal(ABC):
    @abstractmethod
    def send_keystrokes(self, keystrokes: str, wait_sec: float = 0.0) -> None:
        """
        Sends keystrokes to the terminal.

        Args:
            keystrokes: The keystrokes to send to the terminal.
            wait_sec: The number of seconds to wait for the command to complete.
        """
        pass
'''


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _inputs(*, extra_source=None):
    """Build native in-memory structural history without file or DB operations.

    The AST CID is an honestly named test placeholder: this consumer joins
    manifest identity, and never claims it fetched/certified AST artifact bytes.
    Root integration exercises actual owner-prepared AST artifacts separately.
    """
    from ipfs_datasets_py.logic.software_contracts.codebase_ir import CodebaseIRManifest, CodebaseUnit
    from ipfs_datasets_py.logic.software_contracts.content import cid_for_bytes, cid_for_structured
    from ipfs_datasets_py.logic.software_contracts.semantic_index.scanner import RepositoryScanner
    from ipfs_datasets_py.logic.software_contracts.semantic_index.snapshot import RepositorySnapshot, SnapshotEntry

    records = [{"path": "headless-terminal/environment/base_terminal.py",
        "sha256": BASE_SOURCE_SHA256, "source_text": SOURCE}]
    if extra_source is not None:
        records.append({"path": "unrelated.py", "sha256": _sha(extra_source), "source_text": extra_source})
    entries = tuple(SnapshotEntry(row["path"], "python", len(row["source_text"].encode("utf-8")),
        cid_for_bytes(row["source_text"].encode("utf-8")), disposition="filesystem",
        captured_bytes=row["source_text"].encode("utf-8")) for row in records)
    snapshot = RepositorySnapshot("test:headless-grounding", entries, "filesystem",
        max_entries=8, max_file_bytes=64 * 1024)
    state = RepositoryScanner(repository_id=snapshot.repository_id).scan_snapshot(snapshot,
        {entry.source_key: entry.captured_bytes for entry in entries})
    units = tuple(CodebaseUnit(entry.source_key, entry.entry_cid,
        cid_for_structured({"schema": "test-only-unfetched-ast-placeholder@1", "path": entry.path}), "ok")
        for entry in entries)
    manifest = CodebaseIRManifest(snapshot, state,
        "rev:" + snapshot.repository_id + ":snapshot:" + snapshot.snapshot_cid, units)
    return {"instruction_text": INSTRUCTION, "instruction_sha256": INSTRUCTION_SHA256,
        "source_records": records, "structural_manifest": manifest.to_dict()}


def test_real_public_source_joins_native_symbols_without_behavioral_satisfaction():
    assert _sha(INSTRUCTION) == INSTRUCTION_SHA256
    assert _sha(SOURCE) == BASE_SOURCE_SHA256
    result = build_grounding(**_inputs())
    interface = result["structural_interface_nomination"]
    assert interface["class_symbol"]["kind"] == "class"
    assert interface["method_symbol"]["kind"] == "method"
    assert interface["method_symbol"]["qualified_name"].endswith(".BaseTerminal.send_keystrokes")
    assert interface["method_signature"]["parameters"][1]["annotation"] == "str"
    assert interface["method_signature"]["parameters"][2]["default"] == "0.0"
    assert interface["requested_output_definitions_in_admitted_inventory"] == []
    assert interface["method_body_kind"] == "abstract_stub"
    assert result["current_behavioral_facts"] == []
    assert result["behavioral_satisfied_requirements"] == []
    assert result["removed_task_ids"] == []
    assert result["behavioral_satisfaction"] is False


def test_native_ledger_preserves_the_complete_original_prompt_and_unknown_spans():
    from ipfs_datasets_py.logic.intent_ir.formalize.requirements import validate_intent_requirement_ledger

    result = build_grounding(**_inputs())
    ledger = result["native_requirement_ledger"]
    assert "".join(unit["text"] for unit in ledger["source_units"]) == INSTRUCTION
    assert validate_intent_requirement_ledger(ledger, source_text=INSTRUCTION) == ledger
    assert len(ledger["requirements"]) == 2
    residual_text = "".join(unit["text"] for unit in result["original_instruction_residuals"])
    for detail in ("interactive bash", "interactive programs", "modifier keys", "startup files", "Install dependencies"):
        assert detail in residual_text
    assert result["instruction"]["text"] == INSTRUCTION
    assert result["source_accounting_complete"] is True
    assert result["contract_recall_verified"] is False


def test_genuine_supervisor_coverage_rejects_the_partial_nomination_plan():
    from ipfs_accelerate_py.agent_supervisor.prompt.intent_plan_coverage import check_intent_plan_coverage
    from ipfs_accelerate_py.agent_supervisor.prompt.prompt_workflow import PromptGoalGraph

    result = build_grounding(**_inputs())
    plan = result["partial_plan"]
    replay = check_intent_plan_coverage(plan["contract"],
        graph=PromptGoalGraph.from_dict(plan["graph"]), bindings=plan["bindings"])
    assert replay == plan["coverage"]
    assert replay["accepted"] is False
    assert replay["uncovered_requirement_ids"] == []
    assert any(row["code"] == "unsupported_source_units" for row in replay["errors"])
    assert plan["status"] == "blocked_partial_instruction_coverage"
    assert plan["symbolic_plan_executed"] is False
    assert plan["validation_commands_executed"] is False


@pytest.mark.parametrize("recompute_sha", [False, True])
def test_changed_public_prompt_is_not_silently_reinterpreted(recompute_sha):
    inputs = _inputs()
    inputs["instruction_text"] = INSTRUCTION.replace("BaseTerminal", "OtherTerminal")
    if recompute_sha:
        inputs["instruction_sha256"] = _sha(inputs["instruction_text"])
    with pytest.raises(GroundingError, match="exact pinned public"):
        build_grounding(**inputs)


@pytest.mark.parametrize("recompute_sha", [False, True])
def test_changed_source_is_refused_even_when_its_claimed_hash_is_updated(recompute_sha):
    inputs = _inputs()
    row = inputs["source_records"][0]
    row["source_text"] = SOURCE.replace("pass", "return None")
    if recompute_sha:
        row["sha256"] = _sha(row["source_text"])
    with pytest.raises(GroundingError, match="source bytes"):
        build_grounding(**inputs)


@pytest.mark.parametrize("change", ["snapshot", "repository", "ast_revision", "coverage", "authority"])
def test_tampered_native_snapshot_lineage_and_authority_are_refused(change):
    inputs = _inputs()
    manifest = inputs["structural_manifest"]
    if change == "snapshot":
        manifest["snapshot"]["git_commit"] = "0" * 40
    elif change == "repository":
        manifest["snapshot"]["repository_id"] = "another:repository"
    elif change == "ast_revision":
        manifest["ast_revision_id"] = "rev:forged"
    elif change == "coverage":
        manifest["coverage"]["checked_properties"] = 1
    else:
        manifest["authority"] = "proved_behavior"
    with pytest.raises(GroundingError, match="invalid native structural manifest"):
        build_grounding(**inputs)


def test_public_manifest_is_historical_and_cannot_attest_a_live_head():
    result = build_grounding(**_inputs())
    assert result["live_head_verified_here"] is False
    assert result["caller_requires_current_head_observation"] is True
    assert result["required_observation_api"] == "RepositoryCodebaseIndex.observe_current"
    assert result["ast_artifact_bytes_verified_here"] is False


@pytest.mark.parametrize("change", ["span", "signature", "class_bases"])
def test_rehashed_native_candidate_cannot_substitute_source_symbol_semantics(change):
    from dataclasses import replace
    from ipfs_datasets_py.logic.software_contracts.codebase_ir import CodebaseIRManifest
    from ipfs_datasets_py.logic.software_contracts.semantic_index.identity import symbol_version_cid

    inputs = _inputs()
    manifest = CodebaseIRManifest.from_dict(inputs["structural_manifest"])
    method = next(row for row in manifest.semantic_state.symbols if row.kind == "method")
    cls = next(row for row in manifest.semantic_state.symbols if row.kind == "class")
    row = cls if change == "class_bases" else method
    if change == "span":
        changed = replace(row, span=replace(row.span, start_line=row.span.start_line + 1))
    else:
        wire = row.to_dict()
        if change == "signature":
            wire["signature"]["parameters"][1]["annotation"] = "int"
        else:
            wire["normalized_ast"]["bases"] = [{"_type": "Name", "id": "Unrelated", "ctx": {"_type": "Load"}}]
        version = symbol_version_cid(row.stable_id, wire["normalized_ast"], wire["signature"],
            wire["decorators"], wire["annotations"], extractor_name=row.extractor_name,
            extractor_version=row.extractor_version, semantic_index_schema=row.semantic_index_schema,
            property_role=row.property_role)
        changed = replace(row, version_cid=version,
            normalized_ast=wire["normalized_ast"], signature=wire["signature"])
    state = replace(manifest.semantic_state, symbols=tuple(changed if item.stable_id == row.stable_id
        else item for item in manifest.semantic_state.symbols))
    inputs["structural_manifest"] = replace(manifest, semantic_state=state).to_dict()
    # Native structural wire validation succeeds: all attacker-controlled
    # identities were consistently rebuilt. Exact extraction replay refuses.
    CodebaseIRManifest.from_dict(inputs["structural_manifest"])
    with pytest.raises(GroundingError, match="exact source extraction replay"):
        build_grounding(**inputs)


def test_same_named_unrelated_interface_cannot_replace_the_exact_public_source():
    inputs = _inputs(extra_source="class BaseTerminal:\n    def send_keystrokes(self):\n        return True\n")
    result = build_grounding(**inputs)
    assert result["structural_interface_nomination"]["source_path"] == inputs["source_records"][0]["path"]
    inputs["source_records"] = inputs["source_records"][1:]
    with pytest.raises(GroundingError, match="complete native snapshot"):
        build_grounding(**inputs)


@pytest.mark.parametrize("field", ["proof_authority", "behavioral_satisfaction", "source_semantics_verified",
    "completion_authority", "omission_authority", "contract_recall_verified"])
def test_advisory_alignment_cannot_promote_candidate_authority(field):
    with pytest.raises(GroundingError, match="grant no source or behavioral authority"):
        build_grounding(**_inputs(), alignment_projection={"nested": [{field: True}]})


def test_advisory_similarity_and_loss_cannot_remove_residuals_or_change_coverage():
    inputs = _inputs()
    baseline = build_grounding(**inputs)
    projection = {"schema": "test-only-advisory@1", "similarity": 1.0,
        "reconstruction_loss": 0.0, "behavioral_satisfaction": False}
    result = build_grounding(**inputs, alignment_projection=projection)
    assert result["partial_plan"] == baseline["partial_plan"]
    assert result["original_instruction_residuals"] == baseline["original_instruction_residuals"]
    assert result["structural_interface_nomination"] == baseline["structural_interface_nomination"]
    assert result["advisory_projection_changes_nomination"] is False
    assert result["behavioral_satisfied_requirements"] == []


def test_candidate_labels_are_not_an_automated_semantic_parser_or_human_review_claim():
    result = build_grounding(**_inputs())
    interpretation = result["interpretation"]
    assert interpretation["kind"] == "manually_authored_candidate"
    assert interpretation["automated_natural_language_parser_used"] is False
    assert interpretation["human_review_claimed"] is False
    assert interpretation["learned_intent_decoding_used"] is False
    for row in result["native_intent_documents"]:
        assert row["document"]["sources"][0]["review_status"] == "unreviewed"
        assert row["document"]["statements"][0]["grounding"] == "inferred"
        assert row["document"]["statements"][0]["confidence"] == 0.0


@pytest.mark.parametrize("change", ["duplicate", "extra", "missing", "escape", "nonfinite"])
def test_bounded_closed_input_controls(change):
    inputs = _inputs()
    if change == "duplicate":
        inputs["source_records"].append(deepcopy(inputs["source_records"][0]))
    elif change == "extra":
        inputs["source_records"][0]["proof_authority"] = True
    elif change == "missing":
        inputs["source_records"] = []
    elif change == "escape":
        inputs["source_records"][0]["path"] = "../base_terminal.py"
    else:
        inputs["alignment_projection"] = {"similarity": float("nan")}
    with pytest.raises(GroundingError):
        build_grounding(**inputs)
