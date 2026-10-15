"""Source, byte-span, task-scope and rehashed-evidence refusal controls."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from requirement_grounding import (
    FLAGS, RequirementGroundingError, build_requirement_grounding, validate_requirement_grounding)

PUBLIC = Path(__file__).resolve().parent.parent / "terminal-planning-admission-20261015-01" / "experiment-01"


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def _native_inputs(corpus, records, inventories):
    """Fresh native in-memory source extraction, not retained SQL/CAS authority."""
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    from ipfs_datasets_py.logic.software_contracts.codebase_ir import CodebaseIRManifest, CodebaseUnit
    from ipfs_datasets_py.logic.software_contracts.content import cid_for_bytes, cid_for_structured
    from ipfs_datasets_py.logic.software_contracts.python_frontend import PythonASTExtractor
    from ipfs_datasets_py.logic.software_contracts.semantic_index.scanner import RepositoryScanner
    from ipfs_datasets_py.logic.software_contracts.semantic_index.snapshot import RepositorySnapshot, SnapshotEntry

    entries = tuple(SnapshotEntry(row["path"], "python", len(row["source_text"].encode()),
        cid_for_bytes(row["source_text"].encode()), disposition="filesystem",
        captured_bytes=row["source_text"].encode()) for row in records)
    snapshot = RepositorySnapshot("test:four-task-grounding", entries, "filesystem", max_entries=5, max_file_bytes=8192)
    state = RepositoryScanner(repository_id=snapshot.repository_id).scan_snapshot(snapshot,
        {entry.source_key: entry.captured_bytes for entry in entries})
    units = []
    for entry in entries:
        ast = PythonASTExtractor().extract(entry.captured_bytes, path=entry.path,
            repository_id=snapshot.repository_id, revision="snapshot:" + snapshot.snapshot_cid,
            repository_tree_cid=snapshot.snapshot_cid)
        units.append(CodebaseUnit(entry.source_key, entry.entry_cid, ast.cid, "ok"))
    manifest = CodebaseIRManifest(snapshot, state,
        "rev:" + snapshot.repository_id + ":snapshot:" + snapshot.snapshot_cid, tuple(units))
    head = CodebaseHead(snapshot.repository_id, 1, manifest.cid, snapshot.snapshot_cid,
        manifest.ast_revision_id, cid_for_structured({"schema": "test-owned-head-receipt-placeholder@1"}))
    return {"corpus": corpus, "source_records": records, "inventories": inventories,
        "structural_manifest": manifest.to_dict(), "head": head.to_dict()}


@pytest.fixture(scope="module")
def inputs():
    from clause_inventory import build_instruction_inventory
    corpus = json.loads((PUBLIC / "corpus-manifest.json").read_bytes())
    records, inventories = [], []
    for task in corpus["tasks"]:
        instruction = (PUBLIC / "instructions" / task["task_id"] / "instruction.md").read_bytes()
        inventories.append(build_instruction_inventory(task_id=task["task_id"], instruction=instruction))
        for pin in task["sources"]:
            raw = (PUBLIC / "source-repository" / pin["path"]).read_bytes()
            records.append({"path": pin["path"], "sha256": _sha(raw), "source_text": raw.decode("utf-8")})
    return _native_inputs(corpus, records, inventories)


@pytest.fixture(scope="module")
def report(inputs):
    return build_requirement_grounding(**inputs)


def _rehash_manifest_head(inputs, manifest):
    inputs["structural_manifest"] = manifest.to_dict()
    inputs["head"]["manifest_cid"] = manifest.cid


def test_full_instruction_inventory_and_every_source_projection_are_retained(inputs, report):
    assert len(report["source_bindings"]) == 5
    assert len(report["tasks"]) == 4
    assert report["native_source_ast_effect_interface_replay"] is True
    assert report["native_semantic_symbol_edge_replay"] is True
    assert {row["family"] for row in report["source_projections"]} == {"symbol", "interface", "effect", "call"}
    assert any(row["semantic_symbol_bindings"] for row in report["source_projections"])
    original = {r["task_id"]: r for r in inputs["inventories"]}
    for task in report["tasks"]:
        assert [u["unit_id"] for u in task["units"]] == [u["unit_id"] for u in original[task["task_id"]]["units"]]
        assert any(u["status"] == "no_source_anchor" for u in task["units"])
        assert all(u["requirement_resolved"] is False for u in task["units"])
        assert task["resolved_requirement_ids"] == []
    assert report["removed_task_ids"] == []
    assert all(report[key] is False for key in FLAGS)


def test_citations_are_exact_source_bytes_and_no_cross_task_anchors(inputs, report):
    sources = {r["path"]: r["source_text"].encode("utf-8") for r in inputs["source_records"]}
    catalog = {r["projection_id"]: r for r in report["source_projections"]}
    for row in catalog.values():
        citation = row["citation"]
        raw = sources[row["path"]][citation["start_byte"]:citation["end_byte"]]
        assert citation["text"].encode("utf-8") == raw
        assert citation["sha256"] == _sha(raw)
    for task in report["tasks"]:
        for unit in task["units"]:
            for anchor in unit["projection_anchors"]:
                assert catalog[anchor["projection_id"]]["path"] in task["source_paths"]
            for anchor in unit["file_anchors"]:
                assert anchor["source_path"] in task["source_paths"]


def test_output_absence_is_only_admitted_inventory_scope(report):
    outputs = [o for t in report["tasks"] for o in t["authored_output_candidates"]]
    assert len(outputs) == 5
    assert all(o["path_in_admitted_inventory"] is False for o in outputs)
    assert all(o["absence_scope"] == "admitted_source_inventory_only" for o in outputs)
    assert report["absence_proves_repository_wide_absence"] is False
    assert report["nominations_are_entailment"] is False


@pytest.mark.parametrize("change", ["missing_source", "extra_source", "changed_source", "wrong_task_path"])
def test_source_inventory_and_bytes_refuse_scope_substitution(inputs, change):
    value = deepcopy(inputs)
    if change == "missing_source":
        value["source_records"].pop()
    elif change == "extra_source":
        value["source_records"].append(deepcopy(value["source_records"][0]))
    elif change == "changed_source":
        row = value["source_records"][0]
        row["source_text"] += "# authored adversarial source edit\n"
        row["sha256"] = _sha(row["source_text"].encode())
    else:
        value["source_records"][0]["path"] = "feal-differential-cryptanalysis/environment/base_terminal.py"
    with pytest.raises(RequirementGroundingError):
        build_requirement_grounding(**value)


@pytest.mark.parametrize("change", ["missing_inventory", "duplicate_task", "reclassified", "unicode_byte_span", "dropped_candidate"])
def test_full_native_instruction_inventory_cannot_be_silently_weakened(inputs, change):
    value = deepcopy(inputs)
    if change == "missing_inventory":
        value["inventories"].pop()
    elif change == "duplicate_task":
        value["inventories"][1] = deepcopy(value["inventories"][0])
    elif change == "reclassified":
        value["inventories"][0]["units"][0]["classification"] = "whitespace"
    elif change == "dropped_candidate":
        selected = next(row for row in value["inventories"] if row["native_requirement_ledger"]["requirements"])
        selected["native_requirement_ledger"]["requirements"].pop()
    else:
        selected = next(row for row in value["inventories"] if row["task_id"] == "llm-inference-batching-scheduler")
        unit = next(unit for unit in selected["units"] if unit["end_byte"] != unit["end_char"])
        unit["end_byte"] = unit["end_char"]
    with pytest.raises(RequirementGroundingError):
        build_requirement_grounding(**value)


@pytest.mark.parametrize("change", ["span", "signature"])
def test_consistently_rehashed_native_semantic_symbol_forgery_fails_exact_replay(inputs, change):
    from ipfs_datasets_py.logic.software_contracts.codebase_ir import CodebaseIRManifest
    from ipfs_datasets_py.logic.software_contracts.semantic_index.identity import symbol_version_cid
    value = deepcopy(inputs)
    manifest = CodebaseIRManifest.from_dict(value["structural_manifest"])
    selected = next(row for row in manifest.semantic_state.symbols if row.kind == "method")
    if change == "span":
        forged = replace(selected, span=replace(selected.span, start_line=selected.span.start_line + 1))
    else:
        wire = selected.to_dict()
        wire["signature"]["parameters"][1]["annotation"] = "int"
        cid = symbol_version_cid(selected.stable_id, wire["normalized_ast"], wire["signature"],
            wire["decorators"], wire["annotations"], extractor_name=selected.extractor_name,
            extractor_version=selected.extractor_version, semantic_index_schema=selected.semantic_index_schema,
            property_role=selected.property_role)
        forged = replace(selected, signature=wire["signature"], version_cid=cid)
    state = replace(manifest.semantic_state, symbols=tuple(forged if s.stable_id == selected.stable_id else s
        for s in manifest.semantic_state.symbols))
    _rehash_manifest_head(value, replace(manifest, semantic_state=state))
    # The attacker made a structurally valid native object with new identities.
    CodebaseIRManifest.from_dict(value["structural_manifest"])
    with pytest.raises(RequirementGroundingError, match="semantic symbol/edge extraction replay"):
        build_requirement_grounding(**value)


def test_rehashed_native_ast_effect_forgery_cannot_become_a_source_fact(inputs):
    from ipfs_datasets_py.logic.software_contracts.codebase_ir import CodebaseIRManifest
    from ipfs_datasets_py.logic.software_contracts.python_frontend import PythonASTExtractor
    value = deepcopy(inputs)
    manifest = CodebaseIRManifest.from_dict(value["structural_manifest"])
    record = next(row for row in value["source_records"] if row["path"].endswith("filter.py"))
    parsed = PythonASTExtractor().extract(record["source_text"].encode(), path=record["path"],
        repository_id=manifest.snapshot.repository_id, revision="snapshot:" + manifest.snapshot.snapshot_cid,
        repository_tree_cid=manifest.snapshot.snapshot_cid)
    assert parsed.effects
    # Drop a real lexical effect and rebuild the AST CID and manifest/head CIDs.
    forged = replace(parsed, effects=parsed.effects[1:])
    entry = next(e for e in manifest.snapshot.entries if e.path == record["path"])
    units = tuple(replace(u, ast_cid=forged.cid) if u.source_key == entry.source_key else u for u in manifest.units)
    _rehash_manifest_head(value, replace(manifest, units=units))
    CodebaseIRManifest.from_dict(value["structural_manifest"])
    with pytest.raises(RequirementGroundingError, match="AST/effect/interface extraction replay"):
        build_requirement_grounding(**value)


def test_rehashed_native_semantic_edge_forgery_fails_replay(inputs):
    from ipfs_datasets_py.logic.software_contracts.codebase_ir import CodebaseIRManifest
    value = deepcopy(inputs)
    manifest = CodebaseIRManifest.from_dict(value["structural_manifest"])
    selected = manifest.semantic_state.edges[0]
    forged = replace(selected, metadata={**selected.to_dict()["metadata"], "invented_source_fact": True})
    state = replace(manifest.semantic_state, edges=tuple(forged if e.edge_id == selected.edge_id else e
        for e in manifest.semantic_state.edges))
    _rehash_manifest_head(value, replace(manifest, semantic_state=state))
    CodebaseIRManifest.from_dict(value["structural_manifest"])
    with pytest.raises(RequirementGroundingError, match="semantic symbol/edge extraction replay"):
        build_requirement_grounding(**value)


def test_native_unicode_source_spans_quote_bytes_without_character_offset_confusion():
    from ipfs_datasets_py.logic.software_contracts.python_frontend import PythonASTExtractor
    from requirement_grounding import _quote
    raw = 'préfixe = "😀"\ndef répondre(entrée: str):\n    return entrée + "α"\n'.encode("utf-8")
    parsed = PythonASTExtractor().extract(raw, path="unicode.py", repository_id="test:unicode-citation")
    function = next(s for s in parsed.symbols if s.name == "répondre")
    quoted = _quote(raw, function.span.to_dict())
    assert quoted["text"] == 'def répondre(entrée: str):\n    return entrée + "α"'
    assert quoted["start_byte"] == len('préfixe = "😀"\n'.encode("utf-8"))
    assert quoted["start_byte"] != len('préfixe = "😀"\n')
    left = raw.index("😀".encode("utf-8")) + 1
    with pytest.raises(RequirementGroundingError, match="UTF8 boundaries"):
        _quote(raw, {"start_byte": left, "end_byte": left + 1})


def test_head_binding_is_required_and_current_generation_authority_is_not_invented(inputs, report):
    from ipfs_datasets_py.logic.software_contracts.content import cid_for_structured
    value = deepcopy(inputs)
    value["head"]["manifest_cid"] = cid_for_structured({"schema": "test-wrong-manifest@1"})
    with pytest.raises(RequirementGroundingError, match="head does not bind"):
        build_requirement_grounding(**value)
    assert report["current_head_verified_here"] is False
    assert report["native_generation_freshness_verified_here"] is False
    assert report["required_observation_api"] == "RepositoryCodebaseIndex.observe_current"


@pytest.mark.parametrize("change", ["quote", "cross_task_anchor", "head_generation", "authority", "resolved_unit"])
def test_public_report_rehash_does_not_bypass_recomputation(inputs, report, change):
    forged = deepcopy(report)
    if change == "quote":
        forged["source_projections"][0]["citation"]["text"] = "lossful replacement"
    elif change == "cross_task_anchor":
        task = forged["tasks"][0]
        foreign = next(c for c in forged["source_projections"] if c["path"] not in task["source_paths"])
        task["units"][0]["projection_anchors"] = [{"projection_id": foreign["projection_id"]}]
    elif change == "head_generation":
        forged["head"]["generation"] += 1
    elif change == "authority":
        forged["behavioral_satisfaction"] = True
    else:
        forged["tasks"][0]["units"][0]["requirement_resolved"] = True
    forged["report_sha256"] = _sha(_wire({k: v for k, v in forged.items() if k != "report_sha256"}))
    with pytest.raises(RequirementGroundingError, match="exact replay"):
        validate_requirement_grounding(forged, **inputs)


def test_independent_pure_replay_matches_exact_report(inputs, report):
    assert validate_requirement_grounding(report, **inputs) == report
