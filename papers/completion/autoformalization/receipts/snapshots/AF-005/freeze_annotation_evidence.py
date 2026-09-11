#!/usr/bin/env python3
"""Freeze AF-005 candidate-blind packets, pending gold slots, and provenance.

This program constructs annotation evidence from public AF-004 counts and
development locators. It does not inspect model outputs, does not bind
private final-test identities, and does not invent independent review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

SCHEMA = "autoformalization-gold-facet/v1"
PACKET_SCHEMA = "autoformalization-annotation-packet/v1"
PROVENANCE_SCHEMA = "autoformalization-annotation-provenance/v1"
GUIDELINE_FREEZE = "AF-005/v1"
SPLITS_SHA256 = "d4989a3ea15f7035a4e85621bc220b4567828537733c4de4947fd17637bc0b27"
MINIMAL_PAIRS_SHA256 = "7c7ad5f7ce7da2fda456982e903fe9a5e819fe54d354fac880362dbccb4a0a30"
PILOT_FIXTURE_SHA256 = "6d34cdd1392d3a9964f04e4260f722e076ba7b96c3cdd2fc59749460756cf167"
FORBIDDEN_PACKET_KEYS = {
    "gold", "gold_ir", "gold_facets", "teacher_ir", "teacher_label",
    "model_output", "candidate_output", "candidate_ir", "score",
    "proof_receipt", "retrieval_hit", "advice",
}
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
DEV_EXPORTS = {
    "train": "papers/completion/autoformalization/receipts/snapshots/AF-004/train.sources.jsonl",
    "selection": "papers/completion/autoformalization/receipts/snapshots/AF-004/selection.sources.jsonl",
    "fixed_canary": "papers/completion/autoformalization/receipts/snapshots/AF-004/fixed_canary.sources.jsonl",
}


DEV_EXPORT_SHA256 = {'train': '4e54b902980cef97ae4cd5c8516f0b038505adf3251bde5a2aedd6d4e2abd532', 'selection': '182adaba0b9fc218d30ab56915ad600a176295d2cab687f72a81abcc75bd308c', 'fixed_canary': '98549048682ea1eb727812a6bb8e9d7a9834c22d43a62fd5373b7b7fad97c207'}

def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def dump_canonical(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def pending_facet() -> dict:
    return {
        "status": "unmeasured_pending_independent_review",
        "values": [],
        "admissible_alternatives": [],
        "annotator_ids": [],
        "disagreements": [],
        "adjudication": None,
    }


def expand_histogram(histogram: dict) -> list[int]:
    sizes: list[int] = []
    for size_key, count in histogram.items():
        size = int(size_key)
        for _ in range(int(count)):
            sizes.append(size)
    sizes.sort()
    return sizes


def allocate_final_test_slots(group_sizes: list[int], target: int = 100) -> list[int]:
    if len(group_sizes) < 20:
        raise ValueError("final-test allocation requires at least 20 operational groups")
    alloc = [1] * len(group_sizes)
    remaining = target - len(group_sizes)
    progressed = True
    while remaining > 0 and progressed:
        progressed = False
        for index, size in enumerate(group_sizes):
            cap = min(5, size)
            if alloc[index] < cap and remaining > 0:
                alloc[index] += 1
                remaining -= 1
                progressed = True
    giant = max(range(len(group_sizes)), key=lambda i: (group_sizes[i], i))
    progressed = True
    while remaining > 0 and progressed:
        progressed = False
        for index, size in enumerate(group_sizes):
            if index == giant:
                continue
            if alloc[index] < size and remaining > 0:
                alloc[index] += 1
                remaining -= 1
                progressed = True
    while remaining > 0 and alloc[giant] < group_sizes[giant]:
        alloc[giant] += 1
        remaining -= 1
    if remaining != 0 or sum(alloc) != target:
        raise ValueError("unable to freeze a 100-unit allocation from the public histogram")
    if any(n < 1 or n > group_sizes[i] for i, n in enumerate(alloc)):
        raise ValueError("allocation violates per-group capacity")
    return alloc


def extract_guideline_schema(text: str) -> dict:
    match = re.search(r"```json\n(\{.*?\n\})\n```", text, re.S)
    if not match:
        raise ValueError("annotation guidelines lack a frozen JSON schema fence")
    return json.loads(match.group(1))


def development_locator(record: dict, split: str, export_path: str, export_sha256: str) -> dict:
    rights = record.get("rights_review") or {}
    metadata = record.get("metadata") or {}
    return {
        "split": split,
        "record_id": record["record_id"],
        "citation": record.get("citation"),
        "family": record.get("family"),
        "source_time": record.get("current_through"),
        "document_sha256": record.get("document_sha256"),
        "source_sha256": (record.get("source_lineage") or {}).get("source_sha256"),
        "source_cid": record.get("source_cid"),
        "document_cid": record.get("document_cid"),
        "part": metadata.get("part"),
        "stable_id": metadata.get("stable_id"),
        "rights_review_status": rights.get("review_status"),
        "rights_review_is_semantic_gold": False,
        "export_path": export_path,
        "export_sha256": export_sha256,
        "body_in_packet": False,
    }


def load_development_packets(root: Path) -> list[dict]:
    packets = []
    for split, relpath in DEV_EXPORTS.items():
        path = root / relpath
        export_sha = sha256_file(path)
        if export_sha != DEV_EXPORT_SHA256[split]:
            raise ValueError("development export differs from accepted AF-004 snapshot")
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            if any(key in record for key in FORBIDDEN_PACKET_KEYS):
                raise ValueError(f"development export {relpath}:{line_no} contains forbidden label keys")
            packet_id = f"AF005-DEV-{split}-{record['record_id']}"
            packets.append({
                "schema": PACKET_SCHEMA,
                "packet_id": packet_id,
                "packet_role": "development_calibration",
                "evaluation_sample": False,
                "candidate_blind": True,
                "model_outputs_present": False,
                "teacher_ir_present": False,
                "gold_values_present": False,
                "guideline_freeze": GUIDELINE_FREEZE,
                "facet_schema": SCHEMA,
                "facet_ids": list(FACETS),
                "annotation_status": "pending_independent_review",
                "source": {
                    "disclosure": "development_locator_only",
                    "locator": development_locator(record, split, relpath, export_sha),
                },
            })
    packets.sort(key=lambda row: row["packet_id"])
    return packets


def final_test_packets(group_sizes: list[int], allocation: list[int]) -> list[dict]:
    packets = []
    giant_size = max(group_sizes)
    for index, (size, n_units) in enumerate(zip(group_sizes, allocation), start=1):
        group_id = f"G{index:02d}"
        for unit_index in range(1, n_units + 1):
            packet_id = f"AF005-FT-{group_id}-U{unit_index:02d}"
            packets.append({
                "schema": PACKET_SCHEMA,
                "packet_id": packet_id,
                "packet_role": "planned_final_annotation_slot",
                "evaluation_sample": False,
        "evaluation_eligible": False,
                "candidate_blind": True,
                "model_outputs_present": False,
                "teacher_ir_present": False,
                "gold_values_present": False,
                "guideline_freeze": GUIDELINE_FREEZE,
                "facet_schema": SCHEMA,
                "facet_ids": list(FACETS),
                "annotation_status": "pending_independent_review",
                "source": {
                    "split": "final_test",
                    "disclosure": "withheld_owner_only",
                    "body_in_packet": False,
                    "private_binding": "pending_authorized_annotator_workstation",
                    "group_slot": group_id,
                    "group_slot_index": index,
                    "public_group_record_size": size,
                    "is_giant_component_slot": size == giant_size,
                    "unit_index_in_group_sample": unit_index,
                    "units_allocated_to_group": n_units,
                    "identities_published": False,
                },
            })
    return packets


def gold_record(packet: dict) -> dict:
    return {
        "schema": SCHEMA,
        "packet_id": packet["packet_id"],
        "packet_role": packet["packet_role"],
        "evaluation_sample": False,
        "evaluation_eligible": False,
        "label_origin": None,
        "intended_label_origin": "independent_human_review",
        "label_status": "pending_independent_review",
        "teacher_derived": False,
        "constructed_conformance_witness": False,
        "rights_review_is_semantic_review": False,
        "annotators": [],
        "annotator_independence_attested": False,
        "agreement": {
            "double_annotated_units": 0,
            "agreements": 0,
            "disagreements": 0,
        },
        "adjudication": {
            "status": "pending_independent_review",
            "adjudicator_ids": [],
            "records": [],
        },
        "facets": {name: pending_facet() for name in FACETS},
        "semantic_claim_status": "unmeasured",
    }


def build_provenance(
    *,
    root: Path,
    recorded_at: str,
    guidelines_sha: str,
    packets: list[dict],
    gold: list[dict],
    group_sizes: list[int],
    allocation: list[int],
    teacher: dict,
    splits: dict,
    corpus: dict,
    guideline_schema: dict,
) -> dict:
    ft_packets = [p for p in packets if p["packet_role"] == "planned_final_annotation_slot"]
    dev_packets = [p for p in packets if p["packet_role"] == "development_calibration"]
    input_hashes = {
        "splits.json": sha256_file(root / "papers/completion/autoformalization/data/splits.json"),
        "corpus_manifest.json": sha256_file(root / "papers/completion/autoformalization/data/corpus_manifest.json"),
        "teacher_manifest.json": sha256_file(root / "papers/completion/autoformalization/data/teacher_manifest.json"),
        "protocol.md": sha256_file(root / "papers/completion/autoformalization/protocol.md"),
        "experiment_plan.json": sha256_file(root / "papers/completion/autoformalization/config/experiment_plan.json"),
        "annotation_guidelines.md": guidelines_sha,
        "minimal_pairs.jsonl": sha256_file(root / "papers/completion/autoformalization/data/minimal_pairs.jsonl"),
        "pilot_cases.json": sha256_file(root / "external/ipfs_datasets/tests/fixtures/semantic_roundtrip/pilot_cases.json"),
    }
    teacher_derived = {
        "identified_separately": True,
        "admitted_as_gold": False,
        "compiler_and_view_targets_produced": teacher["compiler_and_view_targets"]["targets_produced"],
        "existing_semantic_labels_used": teacher["semantic_gold"]["existing_semantic_labels_used"],
        "semantic_gold_status": teacher["semantic_gold"]["status"],
        "rights_review_is_not_semantic_review": teacher["semantic_gold"]["rights_review_is_not_semantic_review"],
        "mock_targets_semantic_claim_admission": teacher["mock_targets"]["semantic_claim_admission"],
        "hashed_term_projections": "excluded_from_semantic_embedding_and_teacher_claims",
        "constructed_minimal_pairs": {
            "path": "papers/completion/autoformalization/data/minimal_pairs.jsonl",
            "sha256": input_hashes["minimal_pairs.jsonl"],
            "status": "independently_specified_constructed_witnesses_not_natural_gold",
        },
        "synthetic_roundtrip_fixtures": {
            "path": "external/ipfs_datasets/tests/fixtures/semantic_roundtrip/pilot_cases.json",
            "sha256": input_hashes["pilot_cases.json"],
            "status": "excluded_synthetic_fixture",
        },
    }
    reusable_audit = {
        "independently_reviewed_labels_found": 0,
        "reused": 0,
        "rejected_as_non_gold": [
            "AF-004 rights_review metadata",
            "AF-004 teacher/compiler/view targets (none produced)",
            "AF-006 constructed minimal pairs",
            "semantic_roundtrip pilot fixtures",
        ],
        "rule": "The inspected teacher manifest records no reused semantic labels. No independent labels are supplied to this preparation; any future reuse needs a separate provenance audit.",
    }
    agreement = {
        "basis": "real_inventory_of_annotation_records",
        "independent_human_annotators": 0,
        "completed_double_annotated_units": 0,
        "agreements": 0,
        "disagreements": 0,
        "adjudications": 0,
        "kappa_or_majority_imputed": False,
        "note": "Zero is the observed count of independent annotation records, not a measured agreement statistic.",
    }
    sampling = {
        "population_unique_final_test_units": splits["counts"]["final_test"]["natural_source_units"],
        "population_operational_groups": splits["counts"]["final_test"]["operational_connected_components"],
        "public_group_record_sizes_ascending": group_sizes,
        "allocation_per_group_slot": allocation,
        "provisional_template_slots": sum(allocation),
        "actual_bound_final_units": 0,
        "actual_adjudicated_final_units": 0,
        "allocation_status": "provisional_record_histogram_template_not_a_frozen_unique_unit_sample",
        "minimum_per_group": min(allocation),
        "giant_component_record_size": max(group_sizes),
        "giant_component_allocated_units": allocation[group_sizes.index(max(group_sizes))],
        "groups_unable_to_supply_five": sum(1 for size in group_sizes if size < 5),
        "estimand": "pending_versioned_unit_vs_group_weighting_decision_before_private_binding_or_outcomes",
        "primary_group_weights": None,
        "supplementary_source_weights_declared_pre_outcome": None,
        "four_macro_editions_assumed_in_sample": False,
        "private_binding": "pending_authorized_private_unique_unit_counts_and_versioned_sampling_estimand_before_outcomes",
        "shortfall_rule": "If aliasing leaves fewer unique units than allocated, report shortfall; do not backfill after annotation",
    }
    freeze = {
        "guideline_freeze": GUIDELINE_FREEZE,
        "schema": SCHEMA,
        "packet_schema": PACKET_SCHEMA,
        "before_scored_model_output_inspection": True,
        "model_outputs_inspected": False,
        "inspection_scope": "This generator reads only its listed pinned protocol, source-manifest, development-export, guideline and conformance-fixture inputs. It does not inspect scored candidate outputs; this is not a universal audit of other processes or filesystem history.",
        "final_test_bodies_inspected": False,
        "extracted_guideline_schema": guideline_schema,
    }
    independent_review = {
        "required": True,
        "available": False,
        "status": "pending",
        "effect": "affected_semantic_claims_remain_unmeasured",
        "semantic_claims_measured": False,
        "packets_prepared": True,
        "gold_values_filled": False,
    }
    payload = {
        "schema": PROVENANCE_SCHEMA,
        "task_id": "AF-005",
        "guideline_freeze": GUIDELINE_FREEZE,
        "recorded_at": recorded_at,
        "freeze": freeze,
        "sampling": sampling,
        "packet_inventory": {
            "planned_final_annotation_slot_packets": len(ft_packets),
            "development_calibration_packets": len(dev_packets),
            "pending_gold_record_templates": len(gold),
            "completed_gold_records": 0,
            "gold_records_with_values": 0,
        },
        "teacher_derived_labels": teacher_derived,
        "reusable_independent_label_audit": reusable_audit,
        "agreement_disagreement_adjudication": agreement,
        "independent_review": independent_review,
        "input_sha256": input_hashes,
        "partition_pins": {
            "frozen_splits_sha256": SPLITS_SHA256,
            "observed_splits_sha256": input_hashes["splits.json"],
            "private_membership_commitment_sha256": splits["partition_membership_commitment_sha256"],
            "corpus_private_inventory_commitment_sha256": corpus["private_inventory_commitment_sha256"],
        },
        "limitations": [
            "Independent human review was unavailable; packets are prepared and gold values are unfilled.",
            "Final-test source identities and bodies remain owner-only; public entries are unbound provisional templates, not committed sample membership.",
            "Development locators are calibration only and are not the 100-unit evaluation sample.",
            "Teacher-derived and constructed-conformance labels are identified separately and are not gold.",
            "Zero agreement counts are an inventory of missing independent records, not high annotator reliability.",
            "Coding/implementation and natural-trace populations remain unqualified and out of this sample.",
        ],
    }
    canonical = {key: value for key, value in payload.items() if key != "recorded_at"}
    payload["canonical_payload_sha256"] = sha256_bytes(dump_canonical(canonical).encode("utf-8"))
    return payload


def expected_outputs(root: Path, recorded_at: str) -> tuple[list[dict], list[dict], dict, str]:
    guidelines_path = root / "papers/completion/autoformalization/data/annotation_guidelines.md"
    splits_path = root / "papers/completion/autoformalization/data/splits.json"
    teacher_path = root / "papers/completion/autoformalization/data/teacher_manifest.json"
    corpus_path = root / "papers/completion/autoformalization/data/corpus_manifest.json"
    pairs_path = root / "papers/completion/autoformalization/data/minimal_pairs.jsonl"
    fixture_path = root / "external/ipfs_datasets/tests/fixtures/semantic_roundtrip/pilot_cases.json"
    guidelines = guidelines_path.read_text(encoding="utf-8")
    required_phrases = (
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
    lowered = guidelines.lower()
    missing = [phrase for phrase in required_phrases if phrase not in lowered]
    if missing:
        raise ValueError(f"guidelines missing required instruction coverage: {missing}")
    guideline_schema = extract_guideline_schema(guidelines)
    if guideline_schema.get("schema") != SCHEMA:
        raise ValueError("frozen guideline schema identity mismatch")
    if guideline_schema.get("facet_ids") != list(FACETS):
        raise ValueError("frozen facet inventory mismatch")
    if guideline_schema.get("teacher_derived_admitted_as_gold") is not False:
        raise ValueError("guidelines must refuse teacher-derived gold")
    if guideline_schema.get("unique_string_match_required") is not False:
        raise ValueError("guidelines must forbid unique-string match")
    splits = json.loads(splits_path.read_text(encoding="utf-8"))
    teacher = json.loads(teacher_path.read_text(encoding="utf-8"))
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    if sha256_file(splits_path) != SPLITS_SHA256:
        raise ValueError("splits.json does not match the frozen AF-004 digest")
    if sha256_file(pairs_path) != MINIMAL_PAIRS_SHA256:
        raise ValueError("minimal_pairs.jsonl digest changed; constructed witnesses are not AF-005 gold")
    if sha256_file(fixture_path) != PILOT_FIXTURE_SHA256:
        raise ValueError("pilot fixture digest changed; fixtures remain excluded")
    if teacher["semantic_gold"]["existing_semantic_labels_used"] != 0:
        raise ValueError("teacher manifest reports semantic labels; audit before reuse")
    if teacher["compiler_and_view_targets"]["targets_produced"] != 0:
        raise ValueError("compiler/view targets exist and must stay out of gold")
    histogram = splits["counts"]["final_test"]["component_record_size_histogram"]
    group_sizes = expand_histogram(histogram)
    if len(group_sizes) != 20:
        raise ValueError("public final-test histogram does not contain 20 groups")
    allocation = allocate_final_test_slots(group_sizes)
    ft = final_test_packets(group_sizes, allocation)
    dev = load_development_packets(root)
    if len(ft) != 100:
        raise ValueError("final-test packet count is not 100")
    expected_dev = (
        splits["counts"]["train"]["natural_source_units"]
        + splits["counts"]["selection"]["natural_source_units"]
        + splits["counts"]["fixed_canary"]["natural_source_units"]
    )
    if len(dev) != expected_dev:
        raise ValueError(f"development packet count {len(dev)} != {expected_dev}")
    packets = ft + dev
    gold = [gold_record(packet) for packet in ft]
    provenance = build_provenance(
        root=root,
        recorded_at=recorded_at,
        guidelines_sha=sha256_file(guidelines_path),
        packets=packets,
        gold=gold,
        group_sizes=group_sizes,
        allocation=allocation,
        teacher=teacher,
        splits=splits,
        corpus=corpus,
        guideline_schema=guideline_schema,
    )
    return packets, gold, provenance, sha256_file(guidelines_path)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(dump_canonical(row) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def paths(root: Path) -> dict[str, Path]:
    base = root / "papers/completion/autoformalization"
    return {
        "guidelines": base / "data/annotation_guidelines.md",
        "packets": base / "data/annotation_packets.jsonl",
        "gold": base / "data/gold_facets.jsonl",
        "provenance": base / "evidence/annotation_provenance.json",
    }


def check_existing(root: Path, packets: list[dict], gold: list[dict], provenance: dict) -> None:
    located = paths(root)
    observed_packets = load_jsonl(located["packets"])
    observed_gold = load_jsonl(located["gold"])
    observed_prov = json.loads(located["provenance"].read_text(encoding="utf-8"))
    if observed_packets != packets:
        raise ValueError("annotation_packets.jsonl does not match the frozen generator")
    if observed_gold != gold:
        raise ValueError("gold_facets.jsonl does not match the frozen generator")
    ignore = {"recorded_at"}
    left = {k: v for k, v in observed_prov.items() if k not in ignore}
    right = {k: v for k, v in provenance.items() if k not in ignore}
    # Recompute canonical digest from the observed document.
    canonical = {k: v for k, v in observed_prov.items() if k not in {"recorded_at", "canonical_payload_sha256"}}
    expected_digest = sha256_bytes(dump_canonical(canonical).encode("utf-8"))
    if observed_prov.get("canonical_payload_sha256") != expected_digest:
        raise ValueError("annotation_provenance canonical digest mismatch")
    right.pop("canonical_payload_sha256", None)
    left.pop("canonical_payload_sha256", None)
    if left != right:
        raise ValueError("annotation_provenance.json does not match the frozen generator")
    if observed_prov["independent_review"]["status"] != "pending":
        raise ValueError("independent review must remain pending")
    if any(row["label_status"] != "pending_independent_review" for row in observed_gold):
        raise ValueError("gold facet values were filled without independent review")
    if any(not row["candidate_blind"] or row["teacher_ir_present"] or row["model_outputs_present"] for row in observed_packets):
        raise ValueError("packets are not candidate-blind")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--recorded-at")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    located = paths(root)
    recorded_at = args.recorded_at
    if recorded_at is None and args.check and located["provenance"].is_file():
        recorded_at = json.loads(located["provenance"].read_text(encoding="utf-8"))["recorded_at"]
    if recorded_at is None:
        from datetime import datetime, timezone
        recorded_at = datetime.now(timezone.utc).isoformat()
    packets, gold, provenance, guidelines_sha = expected_outputs(root, recorded_at)
    if args.write:
        write_jsonl(located["packets"], packets)
        write_jsonl(located["gold"], gold)
        write_json(located["provenance"], provenance)
    if args.check or args.write:
        check_existing(root, packets, gold, provenance)
    summary = {
        "guideline_freeze": GUIDELINE_FREEZE,
        "guidelines_sha256": guidelines_sha,
        "unbound_final_annotation_slots": sum(p["packet_role"] == "planned_final_annotation_slot" for p in packets),
        "development_packets": sum(p["packet_role"] == "development_calibration" for p in packets),
        "pending_gold_record_templates": len(gold),
        "completed_gold_records": 0,
        "gold_values_filled": 0,
        "independent_review": provenance["independent_review"]["status"],
        "teacher_derived_admitted_as_gold": False,
        "semantic_claims": "unmeasured",
        "allocation": provenance["sampling"]["allocation_per_group_slot"],
        "canonical_payload_sha256": provenance["canonical_payload_sha256"],
        "mode": "write" if args.write else "check",
        "status": "PASS",
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
