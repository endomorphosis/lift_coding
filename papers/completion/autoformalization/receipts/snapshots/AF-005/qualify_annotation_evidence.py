#!/usr/bin/env python3
"""Independent AF-005 freeze-contract check. Not human annotation or scoring."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path

TASK = "AF-005"
GUIDELINE_FREEZE = "AF-005/v1"
SCHEMA = "autoformalization-gold-facet/v1"
PACKET_SCHEMA = "autoformalization-annotation-packet/v1"
PROVENANCE_SCHEMA = "autoformalization-annotation-provenance/v1"
SPLITS_SHA256 = "d4989a3ea15f7035a4e85621bc220b4567828537733c4de4947fd17637bc0b27"
TEACHER_SHA256 = "90dab08c92142210e386f9c71343766eba42ca920e5db0318a015a44e8ae3fa4"
CORPUS_SHA256 = "ca410804725f7e323551082243cea3ca5e381bcdc87b0726a0dd6f5dcfbb5ed6"
PROTOCOL_SHA256 = "8f81d8d7c46de327f14b93100a24b97f18194518d18220ad459521e849f51401"
PLAN_SHA256 = "b58ca30cca5c80b37df6875fe8534118fad3a4552b726304c926aa88640d058c"
MINIMAL_PAIRS_SHA256 = "7c7ad5f7ce7da2fda456982e903fe9a5e819fe54d354fac880362dbccb4a0a30"
PILOT_FIXTURE_SHA256 = "6d34cdd1392d3a9964f04e4260f722e076ba7b96c3cdd2fc59749460756cf167"
PRIVATE_COMMITMENT_SHA256 = "fd6f3bf368de242f7a6d21867695d4eb5c644bf09a4a7f82cf687a76fa2c9126"
FACETS = (
    "propositions",
    "modality",
    "negation",
    "actor_recipient_roles",
    "quantifiers",
    "exceptions",
    "temporal_interpretation",
    "ambiguity",
    "source_spans",
    "admissible_assumptions",
)
FORBIDDEN_KEYS = {
    "gold",
    "gold_ir",
    "gold_facets",
    "teacher_ir",
    "teacher_label",
    "model_output",
    "candidate_output",
    "candidate_ir",
    "score",
    "proof_receipt",
    "retrieval_hit",
    "advice",
    "leaderboard",
}
GUIDELINE_PHRASES = (
    "propositions",
    "modality",
    "negation",
    "actor",
    "quantifier",
    "exception",
    "temporal",
    "ambiguity",
    "source span",
    "admissible assumption",
    "candidate-blind",
    "before",
    "pending",
    "teacher",
    "unmeasured",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump_canonical(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_no} is not a JSON object")
        rows.append(row)
    return rows


def nested_keys(value) -> set[str]:
    found: set[str] = set()
    stack = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            found.update(current)
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)
    return found


def extract_guideline_schema(text: str) -> dict:
    match = re.search(r"```json\n(\{.*?\n\})\n```", text, re.S)
    if not match:
        raise ValueError("annotation guidelines lack a frozen JSON schema fence")
    return json.loads(match.group(1))


def load_freeze(script: Path):
    spec = importlib.util.spec_from_file_location("af005_freeze_annotation_evidence", script)
    if spec is None or spec.loader is None:
        raise ValueError("unable to load freeze_annotation_evidence.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def paths(root: Path) -> dict[str, Path]:
    base = root / "papers/completion/autoformalization"
    snap = base / "receipts/snapshots/AF-005"
    return {
        "guidelines": base / "data/annotation_guidelines.md",
        "packets": base / "data/annotation_packets.jsonl",
        "gold": base / "data/gold_facets.jsonl",
        "provenance": base / "evidence/annotation_provenance.json",
        "splits": base / "data/splits.json",
        "teacher": base / "data/teacher_manifest.json",
        "corpus": base / "data/corpus_manifest.json",
        "protocol": base / "protocol.md",
        "plan": base / "config/experiment_plan.json",
        "pairs": base / "data/minimal_pairs.jsonl",
        "fixture": root / "external/ipfs_datasets/tests/fixtures/semantic_roundtrip/pilot_cases.json",
        "freeze": snap / "freeze_annotation_evidence.py",
        "snap_guidelines": snap / "qualified-outputs/data/annotation_guidelines.md",
        "snap_packets": snap / "qualified-outputs/data/annotation_packets.jsonl",
        "snap_gold": snap / "qualified-outputs/data/gold_facets.jsonl",
        "snap_provenance": snap / "qualified-outputs/evidence/annotation_provenance.json",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    located = paths(root)
    failures: list[str] = []

    def check(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    for name in (
        "guidelines",
        "packets",
        "gold",
        "provenance",
        "splits",
        "teacher",
        "corpus",
        "protocol",
        "plan",
        "pairs",
        "fixture",
        "freeze",
        "snap_guidelines",
        "snap_packets",
        "snap_gold",
        "snap_provenance",
    ):
        check(located[name].is_file(), f"missing required file: {located[name]}")
    if failures:
        raise ValueError("; ".join(failures))

    pin = {
        "splits.json": SPLITS_SHA256,
        "teacher_manifest.json": TEACHER_SHA256,
        "corpus_manifest.json": CORPUS_SHA256,
        "protocol.md": PROTOCOL_SHA256,
        "experiment_plan.json": PLAN_SHA256,
        "minimal_pairs.jsonl": MINIMAL_PAIRS_SHA256,
        "pilot_cases.json": PILOT_FIXTURE_SHA256,
    }
    observed_input = {
        "splits.json": sha256_file(located["splits"]),
        "teacher_manifest.json": sha256_file(located["teacher"]),
        "corpus_manifest.json": sha256_file(located["corpus"]),
        "protocol.md": sha256_file(located["protocol"]),
        "experiment_plan.json": sha256_file(located["plan"]),
        "minimal_pairs.jsonl": sha256_file(located["pairs"]),
        "pilot_cases.json": sha256_file(located["fixture"]),
        "annotation_guidelines.md": sha256_file(located["guidelines"]),
    }
    for name, digest in pin.items():
        check(observed_input[name] == digest, f"pinned input digest changed: {name}")

    guidelines = located["guidelines"].read_text(encoding="utf-8")
    lowered = guidelines.lower()
    missing_phrases = [phrase for phrase in GUIDELINE_PHRASES if phrase not in lowered]
    check(not missing_phrases, f"guidelines missing required instruction coverage: {missing_phrases}")
    check("scored model outputs" in lowered, "guidelines must freeze before scored model outputs")
    check("independent human review" in lowered, "guidelines must require independent human review")
    schema = extract_guideline_schema(guidelines)
    check(schema.get("schema") == SCHEMA, "frozen guideline schema identity mismatch")
    check(schema.get("facet_ids") == list(FACETS), "frozen facet inventory mismatch")
    check(schema.get("teacher_derived_admitted_as_gold") is False, "guidelines must refuse teacher-derived gold")
    check(schema.get("unique_string_match_required") is False, "guidelines must forbid unique-string match")
    check(schema.get("abstention_permitted") is True, "guidelines must permit abstention")
    check("independent_human_review" in schema.get("label_origin", []), "schema must name independent human origin")
    check("automatic_teacher_derived" in schema.get("label_origin", []), "schema must identify teacher-derived labels")
    check("pending_independent_review" in schema.get("adjudication_status", []), "schema must include pending adjudication")

    packets = load_jsonl(located["packets"])
    gold = load_jsonl(located["gold"])
    provenance = json.loads(located["provenance"].read_text(encoding="utf-8"))
    splits = json.loads(located["splits"].read_text(encoding="utf-8"))
    teacher = json.loads(located["teacher"].read_text(encoding="utf-8"))
    corpus = json.loads(located["corpus"].read_text(encoding="utf-8"))

    ft = [row for row in packets if row.get("packet_role") == "planned_final_annotation_slot"]
    dev = [row for row in packets if row.get("packet_role") == "development_calibration"]
    check(len(packets) == len(ft) + len(dev), "unexpected packet_role values")
    check(len(ft) == 100, f"final-test packet count is {len(ft)}, not 100 unbound templates")
    expected_dev = (
        splits["counts"]["train"]["natural_source_units"]
        + splits["counts"]["selection"]["natural_source_units"]
        + splits["counts"]["fixed_canary"]["natural_source_units"]
    )
    check(expected_dev == 122, "development unit total is no longer 122")
    check(len(dev) == expected_dev, f"development packet count {len(dev)} != {expected_dev}")
    check(len(gold) == 100, f"gold template count is {len(gold)}, not 100 pending records")
    check({row["packet_id"] for row in gold} == {row["packet_id"] for row in ft}, "gold templates must match final slots")

    for row in packets:
        keys = nested_keys(row)
        leaked = keys & FORBIDDEN_KEYS
        check(not leaked, f"{row.get('packet_id')} contains forbidden keys {sorted(leaked)}")
        check(row.get("schema") == PACKET_SCHEMA, f"{row.get('packet_id')} packet schema mismatch")
        check(row.get("guideline_freeze") == GUIDELINE_FREEZE, f"{row.get('packet_id')} guideline freeze mismatch")
        check(row.get("facet_schema") == SCHEMA, f"{row.get('packet_id')} facet schema mismatch")
        check(row.get("facet_ids") == list(FACETS), f"{row.get('packet_id')} facet inventory mismatch")
        check(row.get("candidate_blind") is True, f"{row.get('packet_id')} is not candidate-blind")
        check(row.get("model_outputs_present") is False, f"{row.get('packet_id')} includes model outputs")
        check(row.get("teacher_ir_present") is False, f"{row.get('packet_id')} includes teacher IR")
        check(row.get("gold_values_present") is False, f"{row.get('packet_id')} includes gold values")
        check(row.get("evaluation_sample") is False, f"{row.get('packet_id')} marked as evaluation sample")
        check(row.get("annotation_status") == "pending_independent_review", f"{row.get('packet_id')} is not pending")
        source = row.get("source") or {}
        locator = source.get("locator") if isinstance(source.get("locator"), dict) else {}
        body_in_packet = source.get("body_in_packet")
        if body_in_packet is None:
            body_in_packet = locator.get("body_in_packet")
        check(body_in_packet is False, f"{row.get('packet_id')} inlined a source body")

    for row in ft:
        check(row.get("evaluation_eligible") is False, f"{row.get('packet_id')} marked evaluation-eligible")
        source = row.get("source") or {}
        check(source.get("disclosure") == "withheld_owner_only", f"{row.get('packet_id')} disclosed a final-test body")
        check(source.get("identities_published") is False, f"{row.get('packet_id')} published a final-test identity")
        check(source.get("split") == "final_test", f"{row.get('packet_id')} is not a final-test slot")
        check(
            source.get("private_binding") == "pending_authorized_annotator_workstation",
            f"{row.get('packet_id')} is bound without an authorized annotator workstation",
        )
        check("record_id" not in source, f"{row.get('packet_id')} published a final-test record_id")
        check("locator" not in source, f"{row.get('packet_id')} published a final-test locator")

    for row in dev:
        source = row.get("source") or {}
        locator = source.get("locator") or {}
        check(source.get("disclosure") == "development_locator_only", f"{row.get('packet_id')} is not a development locator")
        check(locator.get("rights_review_is_semantic_gold") is False, f"{row.get('packet_id')} treats rights review as gold")
        check(locator.get("split") in {"train", "selection", "fixed_canary"}, f"{row.get('packet_id')} has a non-development split")
        check("text" not in locator and "body" not in locator, f"{row.get('packet_id')} inlined development text")

    for row in gold:
        check(row.get("schema") == SCHEMA, f"{row.get('packet_id')} gold schema mismatch")
        check(row.get("label_origin") is None, f"{row.get('packet_id')} has a filled label origin")
        check(row.get("intended_label_origin") == "independent_human_review", f"{row.get('packet_id')} intended origin mismatch")
        check(row.get("label_status") == "pending_independent_review", f"{row.get('packet_id')} gold status is not pending")
        check(row.get("teacher_derived") is False, f"{row.get('packet_id')} is marked teacher-derived gold")
        check(row.get("constructed_conformance_witness") is False, f"{row.get('packet_id')} is marked constructed gold")
        check(row.get("rights_review_is_semantic_review") is False, f"{row.get('packet_id')} treats rights review as semantic")
        check(row.get("annotators") == [], f"{row.get('packet_id')} invents annotators")
        check(row.get("annotator_independence_attested") is False, f"{row.get('packet_id')} attests independence without review")
        check(row.get("evaluation_sample") is False, f"{row.get('packet_id')} gold marked evaluation sample")
        check(row.get("evaluation_eligible") is False, f"{row.get('packet_id')} gold marked evaluation-eligible")
        check(row.get("semantic_claim_status") == "unmeasured", f"{row.get('packet_id')} semantic claim is not unmeasured")
        agreement = row.get("agreement") or {}
        check(agreement.get("agreements") == 0, f"{row.get('packet_id')} invents agreements")
        check(agreement.get("disagreements") == 0, f"{row.get('packet_id')} invents disagreements")
        check(agreement.get("double_annotated_units") == 0, f"{row.get('packet_id')} invents double annotation")
        adjudication = row.get("adjudication") or {}
        check(adjudication.get("status") == "pending_independent_review", f"{row.get('packet_id')} adjudication is not pending")
        check(adjudication.get("adjudicator_ids") == [], f"{row.get('packet_id')} invents adjudicators")
        check(adjudication.get("records") == [], f"{row.get('packet_id')} invents adjudication records")
        facets = row.get("facets") or {}
        check(set(facets) == set(FACETS), f"{row.get('packet_id')} facet set mismatch")
        for name, facet in facets.items():
            check(facet.get("status") == "unmeasured_pending_independent_review", f"{row.get('packet_id')}.{name} is filled")
            check(facet.get("values") == [], f"{row.get('packet_id')}.{name} has values")
            check(facet.get("admissible_alternatives") == [], f"{row.get('packet_id')}.{name} has alternatives")
            check(facet.get("annotator_ids") == [], f"{row.get('packet_id')}.{name} has annotators")
            check(facet.get("disagreements") == [], f"{row.get('packet_id')}.{name} has disagreements")
            check(facet.get("adjudication") is None, f"{row.get('packet_id')}.{name} has adjudication")

    check(provenance.get("schema") == PROVENANCE_SCHEMA, "provenance schema mismatch")
    check(provenance.get("task_id") == TASK, "provenance task_id mismatch")
    check(provenance.get("guideline_freeze") == GUIDELINE_FREEZE, "provenance guideline freeze mismatch")
    freeze = provenance.get("freeze") or {}
    check(freeze.get("before_scored_model_output_inspection") is True, "provenance does not freeze before outputs")
    check(freeze.get("model_outputs_inspected") is False, "provenance claims model-output inspection")
    check(freeze.get("final_test_bodies_inspected") is False, "provenance claims final-test body inspection")
    check(freeze.get("extracted_guideline_schema") == schema, "provenance schema does not match guidelines")
    review = provenance.get("independent_review") or {}
    check(review.get("required") is True, "independent review must be required")
    check(review.get("available") is False, "independent review must be recorded unavailable")
    check(review.get("status") == "pending", "independent review must remain pending")
    check(review.get("effect") == "affected_semantic_claims_remain_unmeasured", "pending review must keep claims unmeasured")
    check(review.get("semantic_claims_measured") is False, "semantic claims must remain unmeasured")
    check(review.get("packets_prepared") is True, "packets_prepared must be true")
    check(review.get("gold_values_filled") is False, "gold values must remain unfilled")
    agreement = provenance.get("agreement_disagreement_adjudication") or {}
    check(agreement.get("basis") == "real_inventory_of_annotation_records", "agreement basis must be real records")
    check(agreement.get("independent_human_annotators") == 0, "annotator count must be the observed zero")
    check(agreement.get("completed_double_annotated_units") == 0, "double-annotated count must be the observed zero")
    check(agreement.get("agreements") == 0, "agreements must be the observed zero")
    check(agreement.get("disagreements") == 0, "disagreements must be the observed zero")
    check(agreement.get("adjudications") == 0, "adjudications must be the observed zero")
    check(agreement.get("kappa_or_majority_imputed") is False, "kappa/majority must not be imputed")
    teacher_labels = provenance.get("teacher_derived_labels") or {}
    check(teacher_labels.get("identified_separately") is True, "teacher labels must be identified separately")
    check(teacher_labels.get("admitted_as_gold") is False, "teacher labels must not be admitted as gold")
    check(teacher_labels.get("compiler_and_view_targets_produced") == 0, "compiler/view targets must remain unused")
    check(teacher_labels.get("existing_semantic_labels_used") == 0, "existing semantic labels must remain unused")
    check(teacher["semantic_gold"]["existing_semantic_labels_used"] == 0, "teacher manifest reports reused semantic labels")
    check(teacher["compiler_and_view_targets"]["targets_produced"] == 0, "teacher manifest reports compiler/view targets")
    check(teacher["semantic_gold"]["rights_review_is_not_semantic_review"] is True, "rights review must stay non-semantic")
    check(teacher["mock_targets"]["semantic_claim_admission"] is False, "mock targets must stay out of semantic claims")
    reusable = provenance.get("reusable_independent_label_audit") or {}
    check(reusable.get("independently_reviewed_labels_found") == 0, "reusable independent labels were invented")
    check(reusable.get("reused") == 0, "non-gold labels were reused as gold")
    inventory = provenance.get("packet_inventory") or {}
    check(inventory.get("planned_final_annotation_slot_packets") == 100, "provenance final-slot count mismatch")
    check(inventory.get("development_calibration_packets") == 122, "provenance development-packet count mismatch")
    check(inventory.get("pending_gold_record_templates") == 100, "provenance pending-gold count mismatch")
    check(inventory.get("completed_gold_records") == 0, "provenance reports completed gold")
    check(inventory.get("gold_records_with_values") == 0, "provenance reports filled gold values")
    sampling = provenance.get("sampling") or {}
    check(sampling.get("population_unique_final_test_units") == 1913, "final-test unique-unit count mismatch")
    check(sampling.get("population_operational_groups") == 20, "final-test group count mismatch")
    check(sampling.get("provisional_template_slots") == 100, "provisional slot count mismatch")
    check(sampling.get("actual_bound_final_units") == 0, "final units were bound without review")
    check(sampling.get("actual_adjudicated_final_units") == 0, "final units were adjudicated without review")
    check(sum(sampling.get("allocation_per_group_slot") or []) == 100, "allocation does not sum to 100")
    check(len(sampling.get("allocation_per_group_slot") or []) == 20, "allocation is not 20 groups")
    check(sampling.get("four_macro_editions_assumed_in_sample") is False, "sample must not assume four macro-editions")
    check(sampling.get("primary_group_weights") is None, "group weights must remain unfixed pending private binding")
    check(provenance.get("input_sha256") == observed_input, "provenance input hashes do not match current files")
    pins = provenance.get("partition_pins") or {}
    check(pins.get("frozen_splits_sha256") == SPLITS_SHA256, "provenance frozen splits pin mismatch")
    check(pins.get("observed_splits_sha256") == SPLITS_SHA256, "provenance observed splits pin mismatch")
    check(pins.get("private_membership_commitment_sha256") == PRIVATE_COMMITMENT_SHA256, "membership commitment mismatch")
    check(pins.get("corpus_private_inventory_commitment_sha256") == PRIVATE_COMMITMENT_SHA256, "corpus commitment mismatch")
    check(splits.get("partition_membership_commitment_sha256") == PRIVATE_COMMITMENT_SHA256, "splits commitment mismatch")
    check(corpus.get("private_inventory_commitment_sha256") == PRIVATE_COMMITMENT_SHA256, "corpus inventory commitment mismatch")
    canonical = {key: value for key, value in provenance.items() if key not in {"recorded_at", "canonical_payload_sha256"}}
    expected_digest = hashlib.sha256(dump_canonical(canonical).encode("utf-8")).hexdigest()
    check(provenance.get("canonical_payload_sha256") == expected_digest, "annotation_provenance canonical digest mismatch")

    for current, snapshot in (
        (located["guidelines"], located["snap_guidelines"]),
        (located["packets"], located["snap_packets"]),
        (located["gold"], located["snap_gold"]),
        (located["provenance"], located["snap_provenance"]),
    ):
        check(current.read_bytes() == snapshot.read_bytes(), f"snapshot copy differs from current output: {current.name}")

    freeze_mod = load_freeze(located["freeze"])
    recorded_at = provenance["recorded_at"]
    expected_packets, expected_gold, expected_provenance, guidelines_sha = freeze_mod.expected_outputs(root, recorded_at)
    check(guidelines_sha == observed_input["annotation_guidelines.md"], "guidelines digest mismatch")
    check(packets == expected_packets, "annotation_packets.jsonl does not match the frozen generator")
    check(gold == expected_gold, "gold_facets.jsonl does not match the frozen generator")
    left = {key: value for key, value in provenance.items() if key not in {"recorded_at", "canonical_payload_sha256"}}
    right = {key: value for key, value in expected_provenance.items() if key not in {"recorded_at", "canonical_payload_sha256"}}
    check(left == right, "annotation_provenance.json does not match the frozen generator")
    freeze_mod.check_existing(root, expected_packets, expected_gold, expected_provenance)

    summary = {
        "schema": "paper-af005-annotation-qualification/v1",
        "task_id": TASK,
        "passed": not failures,
        "guideline_freeze": GUIDELINE_FREEZE,
        "guidelines_sha256": observed_input["annotation_guidelines.md"],
        "packets_sha256": sha256_file(located["packets"]),
        "gold_sha256": sha256_file(located["gold"]),
        "provenance_sha256": sha256_file(located["provenance"]),
        "canonical_payload_sha256": provenance["canonical_payload_sha256"],
        "unbound_final_annotation_slots": len(ft),
        "development_packets": len(dev),
        "pending_gold_record_templates": len(gold),
        "completed_gold_records": 0,
        "gold_values_filled": 0,
        "independent_review": review.get("status"),
        "independent_review_available": False,
        "agreements": 0,
        "disagreements": 0,
        "adjudications": 0,
        "teacher_derived_admitted_as_gold": False,
        "semantic_claims": "unmeasured",
        "model_outputs_inspected": False,
        "human_annotation_or_research_evaluation_claimed": False,
        "inspection_scope": freeze.get("inspection_scope"),
        "failures": failures,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    if failures:
        raise ValueError("; ".join(failures))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
