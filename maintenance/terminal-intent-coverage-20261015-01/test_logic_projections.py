"""Native declaration routing, exact loss accounting and compiler boundary tests."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from logic_projections import (AUTHORITY, FAMILIES, _combine, _lean_sources,
    build_logic_projections, validate_logic_projections, compile_lean_projections,
    producer_paths)


@pytest.fixture(scope="module")
def inventories():
    from clause_inventory import TASK_OUTPUTS, build_instruction_inventory
    instruction_root = Path(__file__).resolve().parent.parent / "terminal-planning-admission-20261015-01" / "experiment-01" / "instructions"
    return [build_instruction_inventory(task_id=task,
        instruction=(instruction_root / task / "instruction.md").read_bytes()) for task in TASK_OUTPUTS]


@pytest.fixture(scope="module")
def projections(inventories):
    return build_logic_projections(inventories=inventories)


def test_all_tasks_keep_uniform_families_and_explicit_missing_models(projections, inventories):
    assert validate_logic_projections(projections, inventories=inventories) is projections
    assert projections["task_count"] == 4
    for task in projections["tasks"]:
        rows = task["family_report"]["projections"]
        assert {row["family_id"] for row in rows} == set(FAMILIES)
        for family in ("concurrency", "cryptographic_protocol", "event_calculus", "transition_system"):
            selected = [row for row in rows if row["family_id"] == family]
            assert selected and all(row["status"] == "unsupported" for row in selected)
            assert all(row["unsupported"] for row in selected)
        for family in ("frame_logic", "datalog", "horn_chc", "higher_order", "dcec", "tdfol"):
            selected = [row for row in rows if row["family_id"] == family]
            assert selected and all(row["status"] == "projected" for row in selected)
        assert task["whole_original_instruction_formalized"] is False
        assert all(task[key] is False for key in AUTHORITY)
    assert projections["external_backend_calls"] == projections["training_steps"] == projections["provider_calls"] == 0


def test_combining_preserves_exact_semantic_fields_and_source_spans(inventories):
    from ipfs_datasets_py.logic.intent_ir.decoder import decode_intent_ir
    for inventory in inventories:
        combined, maps = _combine(inventory["task_id"], inventory["native_intent_documents"])
        statements = {row.statement_id: row for row in combined.statements}
        sources = {row.ref_id: row for row in combined.sources}
        originals = {row["canonical_sha256"]: decode_intent_ir(row["document"])
            for row in inventory["native_intent_documents"]}
        for mapping in maps:
            original = originals[mapping["canonical_sha256"]]
            ids = {kind: {row["original"]: row["combined"] for row in mapping["identities"]
                    if row["kind"] == kind} for kind in ("source", "statement")}
            for row in original.statements:
                restored = statements[ids["statement"][row.statement_id]].to_dict()
                restored["statement_id"] = row.statement_id
                restored["source_ref_ids"] = list(row.source_ref_ids)
                assert restored == row.to_dict()
            for row in original.sources:
                restored = sources[ids["source"][row.ref_id]].to_dict()
                restored["ref_id"] = row.ref_id
                assert restored == row.to_dict()
        assert len(combined.statements) == sum(len(doc.statements) for doc in originals.values())
        assert not combined.actions and not combined.control_edges


def test_native_lean_source_uses_uninterpreted_modalities(projections):
    sources = _lean_sources(projections)
    assert len(sources) == 5 and sources[-1][2] is False
    for _, source, expected in sources[:-1]:
        assert expected is True
        assert "structure Interpretation where" in source
        assert "required : Prop → Prop" in source
        assert "i.required (i.atom" in source
        assert "theorem " not in source and "axiom " not in source and "sorry" not in source


def _resign(value):
    value.pop("report_sha256", None)
    value["report_sha256"] = hashlib.sha256(json.dumps(value, sort_keys=True,
        separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()).hexdigest()


@pytest.mark.parametrize("mutation", ("missing-family", "unsupported-promotion", "changed-source",
    "changed-document", "dropped-original", "proof-promotion", "missing-task"))
def test_resigned_projection_mutations_refuse(projections, inventories, mutation):
    changed = deepcopy(projections)
    task = changed["tasks"][0]
    if mutation == "missing-family":
        task["family_report"]["projections"] = [row for row in task["family_report"]["projections"]
            if row["family_id"] != "cryptographic_protocol"]
    elif mutation == "unsupported-promotion":
        row = next(row for row in task["family_report"]["projections"] if row["family_id"] == "cryptographic_protocol")
        row["status"] = "projected"
        row["unsupported"] = []
    elif mutation == "changed-source":
        row = next(row for row in task["family_report"]["projections"] if row["family_id"] == "higher_order")
        row["representation"]["source"] += "axiom invented : False\n"
    elif mutation == "changed-document":
        task["combined_document"]["statements"][0]["modality"] = "asserted"
    elif mutation == "dropped-original":
        task["original_documents"] = []
    elif mutation == "proof-promotion":
        changed["proof_authority"] = True
    else:
        changed["tasks"].pop()
    _resign(changed)
    with pytest.raises(ValueError):
        validate_logic_projections(changed, inventories=inventories)


def test_complete_inventory_residuals_are_bound(projections, inventories):
    changed = deepcopy(inventories)
    changed[0]["semantic_residual_units"] = []
    with pytest.raises(ValueError):
        validate_logic_projections(projections, inventories=changed)


def test_document_digest_and_duplicate_clause_refuse(inventories):
    descriptors = deepcopy(inventories[0]["native_intent_documents"])
    with pytest.raises(ValueError):
        _combine(inventories[0]["task_id"], [descriptors[0], descriptors[0]])
    descriptors[0]["canonical_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        _combine(inventories[0]["task_id"], descriptors)


def test_forged_generated_lean_refuses_before_backend(projections):
    changed = deepcopy(projections)
    row = next(row for row in changed["tasks"][0]["family_report"]["projections"] if row["family_id"] == "higher_order")
    row["representation"]["source"] += "def invalid : Nat := \"string\"\n"
    _resign(changed)
    with pytest.raises(ValueError):
        _lean_sources(changed)


@pytest.mark.parametrize("mutation", ("task-proof", "task-whole-source", "drop-original", "rewrite-map",
    "rewrite-combined", "rewrite-combined-digest", "unknown-task-field", "bool-count", "nonzero-training"))
def test_standalone_compiler_boundary_rejects_resigned_claims_and_unions(projections, mutation):
    changed = deepcopy(projections)
    task = changed["tasks"][0]
    if mutation == "task-proof":
        task["proof_authority"] = True
    elif mutation == "task-whole-source":
        task["whole_original_instruction_formalized"] = True
    elif mutation == "drop-original":
        task["original_documents"] = []
    elif mutation == "rewrite-map":
        task["identity_mapping"][0]["identities"][0]["combined"] = "forged:identity"
    elif mutation == "rewrite-combined":
        task["combined_document"]["statements"][0]["arguments"] = ["forged"]
    elif mutation == "rewrite-combined-digest":
        task["combined_document_sha256"] = "0" * 64
    elif mutation == "unknown-task-field":
        task["theorem_authority"] = True
    elif mutation == "bool-count":
        changed["task_count"] = True
    else:
        changed["training_steps"] = 1
    _resign(changed)
    with pytest.raises(ValueError):
        _lean_sources(changed)


def test_fake_lease_refuses_before_output(projections, tmp_path):
    output = tmp_path / "uncreated"
    with pytest.raises(ValueError, match="resource lease"):
        compile_lean_projections(projections, output=output, lease=object())
    assert not output.exists()


def test_named_producers_are_public_pinned_sources_and_installed_binaries():
    paths = producer_paths()
    assert paths and len(paths) == len(set(paths))
    assert all(path.is_absolute() and path.is_file() for path in paths)
    assert Path("/home/barberb/.elan/toolchains/leanprover--lean4---v4.34.1/bin/lean") in paths
    assert Path("/usr/bin/prlimit") in paths
