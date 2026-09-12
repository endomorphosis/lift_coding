#!/usr/bin/env python3
"""Structural audit for NS-015's no-retained-extension closure.

Stdlib only. This program does not import extension modules, train, synthesize,
bind hidden oracles, consume a world/procedure pre-root, or treat source
presence as a retained result.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[6]
PAPER = ROOT / "papers/completion/neurosymbolic_supervision"
QUAL = PAPER / "qualification"
SNAP = PAPER / "receipts/snapshots/NS-015"
SNAP_QUAL = SNAP / "qualification"
INVENTORY = SNAP / "source_review/source_inventory.json"
EXTRACT = PAPER / "paper_extracted.txt"
PGIR_RESULT = ROOT / (
    "external/ipfs_accelerate/data/agent_supervisor/proof_grounded_ir_learning"
    "/freeze/result.v3.json"
)
PGIR_INPUT = ROOT / (
    "external/ipfs_accelerate/data/agent_supervisor/proof_grounded_ir_learning"
    "/freeze/campaign_input_root.json"
)
TOKENIZER = ROOT / (
    "external/ipfs_accelerate/data/agent_supervisor/proof_grounded_ir_learning"
    "/freeze/tokenizer_policy.json"
)
SEARCH_ROOTS = (
    ROOT / "external/ipfs_accelerate/ipfs_accelerate_py",
    ROOT / "external/ipfs_datasets/ipfs_datasets_py",
    ROOT / "implementation_plan",
)
ABSENT_TOKENS = (
    "ProcedureCegis",
    "IncomingMemory",
    "incoming_memory",
    "TAGSeq",
    "DAGSeq",
)
REQUIRED_EXTENSION_IDS = (
    "required_mode_world_procedure_consumption",
    "procedure_cegis",
    "incoming_memory",
    "learned_call_event_inverse_repair_models",
    "architecture_refactoring_remodularization",
    "broad_w1_w4_graph_learning",
    "federation_multi_agent_world_roots",
)
FILE_DIGESTS = {
    "external/ipfs_accelerate/data/agent_supervisor/proof_grounded_ir_learning/freeze/result.v3.json":
        "8baf9a5b26d7f3bf76902d702601c0b6ab9bea2d67560d4a4ce2f7266a276bfc",
    "external/ipfs_accelerate/data/agent_supervisor/proof_grounded_ir_learning/freeze/campaign_input_root.json":
        "1ac9703071918508dde24d9f9d39c43aec0eb346348d3ea7857985bb77cd1f97",
    "external/ipfs_accelerate/data/agent_supervisor/proof_grounded_ir_learning/freeze/tokenizer_policy.json":
        "e48ed2ebac07fbdaf2aabeeeca22c8716e1c06c9829b8d9c84b0d6bbc276eddc",
    "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/formal_assurance_cegis.py":
        "9d4c230b0948628eef7818eceb5583f029c1b862fdea63e9566dc223243dc2f4",
    "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/deterministic_failure_memory.py":
        "fc86d2a47960697e7439dd08f392253a111a6a31969781fd4fd2f2a85c2d6916",
    "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/ir_learning_campaign_planner.py":
        "6710398b62a2ee36fee97f0a52c1614cc860f11fd38342b008468f142e0a9a56",
    "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/program_repair_synthesis.py":
        "8f7421b368a504ab1fd9319f5bc5ad3b521f2901c62f5927e6b84b5a425364c0",
    "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/world_snapshot_builder.py":
        "194b8fc082ce799a19947e250ee21483fd2cfb8a94df3eec538e32ed03ae8726",
    "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/world_view.py":
        "9cf6ba28eba11ef0a9482de6f660e96b1ea607f625d768e25e24c06c825b6ddd",
}
OUTPUTS = {
    "extensions_scope.json": QUAL / "extensions_scope.json",
    "extension_holdout_protocol.md": QUAL / "extension_holdout_protocol.md",
    "extension_results.jsonl": QUAL / "extension_results.jsonl",
    "extensions_report.md": QUAL / "extensions_report.md",
}


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def fail(message: str) -> None:
    raise AssertionError(message)


def iter_python_files(root: Path):
    if not root.exists():
        return
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts or not path.is_file():
            continue
        yield path


def search_tokens() -> dict[str, list[str]]:
    hits = {token: [] for token in ABSENT_TOKENS}
    for root in SEARCH_ROOTS:
        for path in iter_python_files(root):
            text = path.read_text(encoding="utf-8", errors="replace")
            relative = str(path.relative_to(ROOT))
            for token in ABSENT_TOKENS:
                if token in text:
                    hits[token].append(relative)
    return hits


def main() -> None:
    for relative, expected in FILE_DIGESTS.items():
        path = ROOT / relative
        if not path.is_file():
            fail(f"missing inspected source: {relative}")
        if digest(path) != expected:
            fail(f"source digest drifted: {relative}")
    fabric = ROOT / "implementation_plan/proof_grounded_ir_learning_fabric"
    if fabric.exists():
        fail("suggested learned-fabric path is present; this closure assumed it missing")

    pgir = load_json(PGIR_RESULT)
    if pgir.get("task_id") != "PGIR-014" or pgir.get("decision") != "no_go":
        fail("PGIR-014 freeze result is not the preserved no-go")
    if pgir.get("training_task_eligible_count") != 0:
        fail("PGIR-014 eligible training count is not zero")
    campaign = load_json(PGIR_INPUT)
    counts = campaign.get("ir_campaign_input_root") or campaign
    if not isinstance(counts, dict):
        fail("campaign input root is not an object")
    # The counts live on the campaign envelope, not necessarily the top-level key.
    admitted = campaign.get("training_admitted_rows")
    quarantined = campaign.get("rights_quarantined_rows")
    if admitted is None or quarantined is None:
        def walk(node):
            if isinstance(node, dict):
                if node.get("training_admitted_rows") == 0 and node.get("rights_quarantined_rows") == 7173:
                    return True
                return any(walk(value) for value in node.values())
            if isinstance(node, list):
                return any(walk(value) for value in node)
            return False
        if not walk(campaign):
            fail("campaign input root does not record 0 admitted / 7173 quarantined rows")
    elif admitted != 0 or quarantined != 7173:
        fail("campaign input root training counts drifted")
    tokenizer = load_json(TOKENIZER)
    if tokenizer.get("status") != "no_learned_tokenizer_admitted":
        fail("tokenizer freeze policy is not no_learned_tokenizer_admitted")

    inventory = load_json(INVENTORY)
    if inventory.get("schema") != "paper-ns015-current-source-inventory/v1":
        fail("source inventory schema mismatch")
    if digest(INVENTORY) != "6856905bc509fad5c02950bb46da007a4b0bcadefe4afe68a52faf8ea7378e8e":
        fail("source inventory digest drifted from the scope binding")
    for relative, expected in FILE_DIGESTS.items():
        record = inventory["files"][relative]
        if record["sha256"] != expected or record["exists"] is not True:
            fail(f"inventory mismatch for {relative}")
    if inventory["files"]["implementation_plan/proof_grounded_ir_learning_fabric/"]["exists"] is not False:
        fail("inventory still claims the missing fabric path exists")

    extract = EXTRACT.read_text(encoding="utf-8")
    if "ProcedureCegis" not in extract or "TAGSeq" not in extract:
        fail("paper extract no longer contains the named extension claims")
    if "incoming memory method" not in extract:
        fail("paper extract no longer contains the incoming-memory claim")

    hits = search_tokens()
    for token, matched in hits.items():
        if matched:
            fail(f"{token} unexpectedly present in Python source: {matched[:5]}")
        recorded = inventory["identifier_search"]["tokens"][token]["matched_files"]
        if recorded:
            fail(f"inventory recorded Python hits for {token}")

    scope = load_json(OUTPUTS["extensions_scope.json"])
    if scope.get("task_id") != "NS-015":
        fail("scope task_id mismatch")
    if scope.get("qualification_status") != "no_retained_extensions":
        fail("qualification_status must be no_retained_extensions")
    if scope.get("retained_extensions") != []:
        fail("retained_extensions must be empty")
    table = scope["table18_row"]
    if table["ns015_closure"] != "untested_out_of_scope":
        fail("Table 18 row was not closed untested/out of scope")
    if table["retained_required_mode_claim"] is not False:
        fail("required-mode claim must not be retained")
    if table["paired_pre_post_consumption_evidence"] is not False:
        fail("paired consumption evidence must be absent")
    for field in ("safe_rejection", "valid_progress", "evidence_id"):
        if table[field] is not None:
            fail(f"Table 18 {field} must be null, not a simulated value")
    modes = scope["consumption_modes"]
    for name in ("shadow_write", "shadow_read", "guarded", "required"):
        if name not in modes:
            fail(f"missing consumption mode {name}")
        if modes[name]["observed_required_mode_use"] is not False:
            fail(f"{name} was marked as observed required-mode use")
    if modes["shadow_write"]["qualifies_table18_row"] is not False:
        fail("shadow_write must not qualify the Table 18 row")
    if modes["shadow_read"]["qualifies_table18_row"] is not False:
        fail("shadow_read must not qualify the Table 18 row")
    if modes["required"]["qualifies_table18_row"] is not True:
        fail("required mode is the Table 18-qualifying mode")
    if modes["required"]["qualification_status"] != "untested_out_of_scope":
        fail("required mode was not closed untested")
    for name in ("guarded", "required"):
        if modes[name]["worker_self_promotion_permitted"] is not False:
            fail(f"{name} permits worker self-promotion")
        if modes[name]["protected_validator_edits_permitted"] is not False:
            fail(f"{name} permits protected-validator edits")
    invariants = scope["authority_invariants"]
    if invariants["worker_self_promotion"] is not False:
        fail("worker self-promotion invariant failed")
    if invariants["protected_validator_edits"] is not False:
        fail("protected-validator-edit invariant failed")
    if invariants["training_or_synthesis_may_inspect_final_acceptance"] is not False:
        fail("training/synthesis isolation invariant failed")
    if invariants["sidecar_logging_is_consumed_evidence"] is not False:
        fail("sidecar logging must not count as consumed evidence")
    candidates = {item["id"]: item for item in scope["candidates"]}
    expected_candidates = {
        "procedure_cegis",
        "incoming_memory",
        "learned_call_event_inverse_repair_models",
        "architecture_refactoring_remodularization",
        "required_mode_world_procedure_consumption",
        "w1_semantic_addressed_world",
        "w2_program_world",
        "w3_parallel_sealing_tdd_campaign",
        "w4_semantic_refactoring",
        "graph_learning_tagseq_dagseq",
        "federation_multi_agent_world_roots",
    }
    if set(candidates) != expected_candidates:
        fail("candidate set drifted")
    for item in candidates.values():
        if item.get("retained") is not False:
            fail(f"candidate {item['id']} is retained without evidence")
    if candidates["procedure_cegis"]["source"] is not None:
        fail("ProcedureCegis must remain specification-only")
    if candidates["procedure_cegis"]["identifier_search"]["found_in_python_source"] is not False:
        fail("ProcedureCegis identifier search was not fail-closed")
    nearby = {entry["name"] for entry in candidates["procedure_cegis"]["nearby_non_substitutes"]}
    if nearby != {"FormalAssuranceCegis", "ProgramRepairSynthesizer"}:
        fail("ProcedureCegis non-substitutes drifted")
    learned = candidates["learned_call_event_inverse_repair_models"]
    if learned["frozen_learned_artifact"] is not False:
        fail("a frozen learned artifact was claimed")
    if learned["prior_no_go"]["decision"] != "no_go":
        fail("PGIR-014 no-go was not preserved in scope")
    required = candidates["required_mode_world_procedure_consumption"]
    if required["consumed_pre_state"] is not None or required["published_post_state"] is not None:
        fail("required-mode consumption evidence was invented")
    if scope["current_source_inventory"]["sha256"] != digest(INVENTORY):
        fail("scope inventory digest does not match the snapshot inventory")
    if scope["observation_hygiene"]["hidden_oracles_not_inspected"] is not True:
        fail("scope must record that hidden oracles were not inspected")
    if "NS-007" not in " ".join(scope["core_not_blocked"]["planned_core_evaluation"]):
        fail("core evaluation list omitted NS-007")

    protocol = OUTPUTS["extension_holdout_protocol.md"].read_text(encoding="utf-8")
    for phrase in (
        "cannot inspect final acceptance",
        "applicability failure",
        "abstention",
        "shadow_write",
        "shadow_read",
        "guarded",
        "required",
        "No worker self-promotion",
        "family holdout",
        "time holdout",
        "rollback",
    ):
        if phrase.lower() not in protocol.lower() and phrase not in protocol:
            fail(f"holdout protocol missing required phrase: {phrase}")
    if "W3" not in protocol or "shadow_hash" not in protocol:
        fail("protocol does not distinguish world-consumption modes from W3 sealing gates")
    if "does **not**" not in protocol and "does not" not in protocol:
        fail("protocol must state that NS-015 does not execute the optional campaigns")

    rows = [
        json.loads(line)
        for line in OUTPUTS["extension_results.jsonl"].read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != 7:
        fail(f"expected 7 extension result records, found {len(rows)}")
    by_id = {row["extension_id"]: row for row in rows}
    if set(by_id) != set(REQUIRED_EXTENSION_IDS):
        fail("extension result identities drifted")
    for row in rows:
        if row.get("task_id") != "NS-015":
            fail("result task_id mismatch")
        if row.get("retained") is not False:
            fail(f"{row['extension_id']} is retained")
        if row.get("qualification_status") != "no_retained_extensions":
            fail("result qualification_status drifted")
        holdout = row["holdout"]
        if holdout.get("training_inspected_final_acceptance") is not False:
            fail(f"{row['extension_id']} inspected final acceptance")
        if holdout.get("family_split_executed") is not False or holdout.get("time_split_executed") is not False:
            fail(f"{row['extension_id']} claims an executed holdout")
        visibility = row["visibility"]
        for field in (
            "applicability_failures_visible",
            "abstentions_visible",
            "bad_predictions_visible",
            "rollback_costs_visible",
        ):
            if visibility.get(field) is not True:
                fail(f"{row['extension_id']} dropped visibility of {field}")
        if "no experimental" not in visibility.get("scope", "").lower():
            fail(f"{row['extension_id']} visibility scope must remain prospective")
    table_row = by_id["required_mode_world_procedure_consumption"]
    if table_row["result_class"] != "untested_out_of_scope":
        fail("Table 18 result_class drifted")
    for field in ("safe_rejection", "valid_progress", "evidence_id"):
        if table_row[field] is not None:
            fail(f"Table 18 {field} must be null")
    consumed = table_row["consumed_result"]
    if any(consumed.get(key) is not None for key in ("pre_state", "action", "accepted_transition", "post_state")):
        fail("consumed-result fields were filled without an execution")
    if consumed.get("sidecar_logging_counted") is not False:
        fail("sidecar logging was counted as consumption")
    mode = table_row["consumption_mode"]
    if mode["worker_self_promotion"] is not False or mode["protected_validator_edits"] is not False:
        fail("authority flags were not fail-closed on the Table 18 row")
    if mode["guarded"] is not False or mode["required"] is not False:
        fail("guarded/required consumption was claimed")
    learned_row = by_id["learned_call_event_inverse_repair_models"]
    if learned_row["result_class"] != "preserve_prior_no_go":
        fail("learned-candidate result_class drifted")
    if learned_row["frozen_learned_artifact"] is not False:
        fail("learned-candidate record invented a frozen artifact")
    if learned_row["prior_no_go"]["rights_quarantined_rows"] != 7173:
        fail("learned-candidate quarantined-row count drifted")
    narrowing = by_id["broad_w1_w4_graph_learning"]
    if narrowing["result_class"] != "unevaluated_narrowed_without_blocking_core":
        fail("W1–W4 narrowing result_class drifted")
    for task in ("NS-007", "NS-008", "NS-009", "NS-010", "NS-011", "NS-012", "NS-013"):
        if task not in narrowing["core_not_blocked"]:
            fail(f"narrowing record omitted core task {task}")
    if narrowing["consumption_mode"]["shadow_write_distinguished_from_guarded_required"] is not True:
        fail("narrowing record lost the shadow/guarded/required distinction")

    report = OUTPUTS["extensions_report.md"].read_text(encoding="utf-8")
    report_lower = report.lower()
    for phrase in (
        "no procedure, world-consumption, or refactoring",
        "untested / out of scope",
        "W1–W4",
        "does not block the measured core",
        "PGIR-014",
        "cannot inspect final acceptance",
        "No worker self-promotion",
        "shadow-write",
        "shadow-read",
        "null, not zero",
    ):
        if phrase not in report and phrase.lower() not in report_lower:
            fail(f"extensions report missing required phrase: {phrase}")
    if "FormalAssuranceCegis" not in report or "not" not in report.lower():
        fail("report must refuse FormalAssuranceCegis substitution")

    for name, current in OUTPUTS.items():
        snapshot = SNAP_QUAL / name
        if not snapshot.is_file():
            fail(f"missing snapshot copy: {name}")
        if digest(current) != digest(snapshot):
            fail(f"current output differs from snapshot: {name}")

    print("NS-015 no-retained-extension closure: OK")
    print("retained_extensions=0; table18=untested_out_of_scope; training=not_run; hidden_oracles=not_inspected")
    print("procedure_cegis=missing; pgir014=no_go; w1_w4=narrowed_without_blocking_core")


if __name__ == "__main__":
    main()
