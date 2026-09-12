#!/usr/bin/env python3
"""Candidate-blind review importer and public binding verifier for AF-027.

AF-028 receives independent human judgments. This module:

* binds the operator-prepared private 100-unit sample using public
  commitments, grouping, and inclusion weights
* keeps source bodies, unit digests, and gold custody out of repository
  outputs
* validates returned review files without generating labels
* preserves blank/original packets
* fail-closes on empty import, invented annotations, or missing reviews

Standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any, Mapping, Sequence


SCHEMA_BINDING = "autoformalization-review-binding-manifest/v1"
SCHEMA_PACKET = "autoformalization-annotation-packet/v1"
SCHEMA_GOLD = "autoformalization-gold-facet/v1"
SCHEMA_IMPORT = "autoformalization-human-review-import/v1"
SCHEMA_REPORT = "autoformalization-review-binding-verification/v1"
TASK_ID = "AF-027"
PENDING_TASK = "AF-028"
POPULATION_UNITS = 1913
TARGET_UNITS = 100
TARGET_GROUPS = 20
PRIVATE_STORE = Path(
    "/home/barberb/.local/state/ipfs_accelerate_py/vericodegen-2026/"
    "research-inputs/autoformalization/af005-independent-annotation-v1"
)
PRIVATE_COMMITMENTS = {
    "sampling_plan.json": "41bfb6978de5560fcc7404c04e34fe8b42297c3c875c7ec3353c9fc55348e87a",
    "gold_facets.pending.private.jsonl": "8611d4f80dc6d43748cf3a9f1a72c66a6b368079aa650216f42b05c7a071694c",
    "binding_manifest.private.json": "cd5e5a0915144289e20632ae7db0f20df4c9af046806dfcbc9657feeae4a3f91",
    "annotation_packets.private.jsonl": "d9b205cd871deb47f8c28c1597dad531b06a0204080c5d68945118b328432ddf",
}
SAMPLING_PLAN_SHA256 = "41bfb6978de5560fcc7404c04e34fe8b42297c3c875c7ec3353c9fc55348e87a"
FACET_IDS = (
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
HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
REPO_ROOT = PAPER_ROOT.parents[2]


class ReviewImportError(ValueError):
    """Raised when binding, schema, or import contracts fail closed."""


def canonical_dumps(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except ValueError as exc:
        raise ReviewImportError("canonical JSON requires finite numeric values") from exc


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_obj(value: Any) -> str:
    return sha256_text(canonical_dumps(value))


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ReviewImportError(f"{path} contains a non-object row")
        rows.append(row)
    return rows


def default_paths(root: Path | None = None) -> dict[str, Path]:
    paper = (root or REPO_ROOT) / "papers/completion/autoformalization"
    return {
        "root": (root or REPO_ROOT).resolve(),
        "paper": paper,
        "packets": paper / "data" / "annotation_packets.jsonl",
        "gold": paper / "data" / "gold_facets.jsonl",
        "guidelines": paper / "data" / "annotation_guidelines.md",
        "splits": paper / "data" / "splits.json",
        "plan": paper / "config" / "experiment_plan.json",
        "binding": paper / "data" / "review_binding_manifest.json",
        "schema": paper / "data" / "review_packet_schema.json",
        "handoff": paper / "evidence" / "human_review_handoff.md",
        "sampling_plan": (
            paper / "receipts" / "snapshots" / "AF-005" / "private-binding-20260912" / "sampling_plan.json"
        ),
        "binding_report": (
            paper / "receipts" / "snapshots" / "AF-005" / "private-binding-20260912" / "binding_report.json"
        ),
        "independent_verification": (
            paper / "receipts" / "snapshots" / "AF-005" / "private-binding-20260912"
            / "independent_binding_verification.json"
        ),
    }


def histogram_groups() -> list[dict[str, Any]]:
    """Anonymous (N_h, n_h) groups from the operator binding report."""
    counts = {
        "10:2": 2,
        "29:2": 1,
        "3:1": 3,
        "28:2": 1,
        "5:1": 2,
        "1730:74": 1,
        "4:1": 3,
        "15:2": 1,
        "8:2": 1,
        "8:1": 1,
        "6:1": 2,
        "25:2": 1,
        "7:1": 1,
    }
    groups = []
    for key, copies in sorted(counts.items(), key=lambda item: (-int(item[0].split(":")[0]), item[0])):
        n_h_key, n_sample = key.split(":")
        n_h = int(n_h_key)
        n_sample_i = int(n_sample)
        for _ in range(copies):
            groups.append({
                "N_h": n_h,
                "n_h": n_sample_i,
                "inclusion_probability": {
                    "numerator": n_sample_i,
                    "denominator": n_h,
                    "exact": f"{n_sample_i}/{n_h}",
                },
                "inverse_probability_weight": {
                    "numerator": n_h,
                    "denominator": n_sample_i,
                    "exact": f"{n_h}/{n_sample_i}",
                },
            })
    return groups


def grouping_accounting(groups: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if len(groups) != TARGET_GROUPS:
        raise ReviewImportError(f"expected {TARGET_GROUPS} groups, found {len(groups)}")
    sampled = sum(int(item["n_h"]) for item in groups)
    population = sum(int(item["N_h"]) for item in groups)
    weight = sum(Fraction(int(item["N_h"]), int(item["n_h"])) * int(item["n_h"]) for item in groups)
    if sampled != TARGET_UNITS:
        raise ReviewImportError(f"sampled units {sampled} != {TARGET_UNITS}")
    if population != POPULATION_UNITS:
        raise ReviewImportError(f"population units {population} != {POPULATION_UNITS}")
    if weight != POPULATION_UNITS:
        raise ReviewImportError(f"weight sum {weight} != {POPULATION_UNITS}")
    return {
        "groups": TARGET_GROUPS,
        "sampled_units": sampled,
        "population_unique_units": population,
        "weight_sum": int(weight),
        "inclusion_probability": "n_h/N_h",
        "inverse_probability_weight": "N_h/n_h",
        "primary_estimand": (
            "finite-population unit mean over 1913 unique final units; "
            "group dependence retained"
        ),
        "giant_component": {"N_h": 1730, "n_h": 74, "note": "dominates unit weighting"},
    }


def packet_is_blank(packet: Mapping[str, Any]) -> list[str]:
    issues = []
    if packet.get("schema") != SCHEMA_PACKET:
        issues.append("unexpected packet schema")
    if packet.get("gold_values_present"):
        issues.append("gold_values_present")
    if packet.get("model_outputs_present"):
        issues.append("model_outputs_present")
    if packet.get("teacher_ir_present"):
        issues.append("teacher_ir_present")
    if packet.get("evaluation_eligible"):
        issues.append("evaluation_eligible")
    source = packet.get("source") if isinstance(packet.get("source"), Mapping) else {}
    if source.get("body_in_packet"):
        issues.append("source.body_in_packet")
    if source.get("identities_published"):
        issues.append("source.identities_published")
    if packet.get("actual_independent_review"):
        issues.append("actual_independent_review")
    return issues


def gold_is_blank(row: Mapping[str, Any]) -> list[str]:
    issues = []
    if row.get("schema") != SCHEMA_GOLD:
        issues.append("unexpected gold schema")
    if row.get("label_origin") not in {None, "independent_human_review"}:
        issues.append("label_origin set")
    if row.get("annotators"):
        issues.append("annotators present")
    if row.get("annotator_independence_attested"):
        issues.append("annotator_independence_attested")
    if row.get("evaluation_eligible"):
        issues.append("evaluation_eligible")
    if row.get("semantic_claim_status") != "unmeasured":
        issues.append("semantic_claim_status not unmeasured")
    adjudication = row.get("adjudication") if isinstance(row.get("adjudication"), Mapping) else {}
    if adjudication.get("records"):
        issues.append("adjudication records present")
    if adjudication.get("status") != "pending_independent_review":
        issues.append("adjudication not pending")
    facets = row.get("facets") if isinstance(row.get("facets"), Mapping) else {}
    for facet_id in FACET_IDS:
        facet = facets.get(facet_id)
        if not isinstance(facet, Mapping):
            issues.append(f"missing facet {facet_id}")
            continue
        if facet.get("values"):
            issues.append(f"{facet_id}.values")
        if facet.get("annotator_ids"):
            issues.append(f"{facet_id}.annotator_ids")
        if facet.get("adjudication") not in {None}:
            issues.append(f"{facet_id}.adjudication")
        if facet.get("status") != "unmeasured_pending_independent_review":
            issues.append(f"{facet_id}.status")
    return issues


def inspect_private_store() -> dict[str, Any]:
    path = PRIVATE_STORE
    record: dict[str, Any] = {
        "path": str(path),
        "visible": False,
        "mode": None,
        "files": {},
        "commitments_match": False,
        "source_bodies_read": False,
        "worker_boundary": "private store is operator-owned and outside Git",
    }
    try:
        st = path.lstat()
    except OSError as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"
        return record
    record["visible"] = True
    record["mode"] = oct(stat.S_IMODE(st.st_mode))
    matches = []
    for name, expected in PRIVATE_COMMITMENTS.items():
        candidate = path / name
        try:
            digest = sha256_file(candidate)
            mode = oct(stat.S_IMODE(candidate.stat().st_mode))
            record["files"][name] = {"sha256": digest, "mode": mode, "present": True}
            matches.append(digest == expected)
        except OSError as exc:
            record["files"][name] = {"present": False, "error": str(exc)}
            matches.append(False)
    record["commitments_match"] = bool(matches) and all(matches)
    return record


def load_public_population(paths: Mapping[str, Path]) -> dict[str, Any]:
    packets = load_jsonl(paths["packets"])
    gold = load_jsonl(paths["gold"])
    slots = [row for row in packets if row.get("packet_role") == "planned_final_annotation_slot"]
    if len(slots) != TARGET_UNITS:
        raise ReviewImportError(f"public final slots {len(slots)} != {TARGET_UNITS}")
    gold_by_id = {row["packet_id"]: row for row in gold}
    packet_issues = []
    gold_issues = []
    identities = []
    for index, packet in enumerate(slots, 1):
        packet_id = str(packet.get("packet_id") or "")
        bound_id = f"AF005-BOUND-{index:03d}"
        issues = packet_is_blank(packet)
        if issues:
            packet_issues.append({"packet_id": packet_id, "issues": issues})
        gold_row = gold_by_id.get(packet_id)
        if gold_row is None:
            gold_issues.append({"packet_id": packet_id, "issues": ["missing gold template"]})
        else:
            g_issues = gold_is_blank(gold_row)
            if g_issues:
                gold_issues.append({"packet_id": packet_id, "issues": g_issues})
        source = packet.get("source") if isinstance(packet.get("source"), Mapping) else {}
        identities.append({
            "public_packet_id": packet_id,
            "private_bound_packet_id": bound_id,
            "public_group_slot": source.get("group_slot"),
            "split": source.get("split"),
            "judgments": None,
            "gold_values_present": False,
            "source_body_published": False,
            "source_digest_published": False,
            "source_digest_custody": "private_reviewer_store",
            "gold_custody": "private_reviewer_store",
            "reviewer_judgment_status": "blank_until_AF-028",
        })
    if packet_issues or gold_issues:
        raise ReviewImportError(
            f"blank-packet contract failed: packets={packet_issues[:3]} gold={gold_issues[:3]}"
        )
    return {
        "packets": slots,
        "gold": gold,
        "identities": identities,
        "packet_sha256": sha256_file(paths["packets"]),
        "gold_sha256": sha256_file(paths["gold"]),
        "guidelines_sha256": sha256_file(paths["guidelines"]),
        "splits_sha256": sha256_file(paths["splits"]),
        "plan_sha256": sha256_file(paths["plan"]),
    }


def build_binding_manifest(root: Path) -> dict[str, Any]:
    paths = default_paths(root)
    public = load_public_population(paths)
    groups = histogram_groups()
    accounting = grouping_accounting(groups)
    sampling = load_json(paths["sampling_plan"])
    report = load_json(paths["binding_report"])
    verification = load_json(paths["independent_verification"])
    if sha256_file(paths["sampling_plan"]) != SAMPLING_PLAN_SHA256:
        raise ReviewImportError("sampling plan digest drifted from operator freeze")
    if report.get("sampling_plan_sha256") != SAMPLING_PLAN_SHA256:
        raise ReviewImportError("binding report sampling plan digest drifted")
    private = inspect_private_store()
    manifest = {
        "schema": SCHEMA_BINDING,
        "task_id": TASK_ID,
        "pending_review_task": PENDING_TASK,
        "created_at": utc_now(),
        "guideline_freeze": "AF-005/v1",
        "operator_binding": {
            "sampling_plan_sha256": SAMPLING_PLAN_SHA256,
            "binding_report_sha256": sha256_file(paths["binding_report"]),
            "independent_verification_sha256": sha256_file(paths["independent_verification"]),
            "private_directory": str(PRIVATE_STORE),
            "private_commitments": dict(PRIVATE_COMMITMENTS),
            "private_modes": "directory0700/files0600",
            "source_bodies_in_repository": False,
            "final_identities_in_repository": False,
        },
        "population": {
            "unique_final_units": POPULATION_UNITS,
            "operational_groups": TARGET_GROUPS,
            "bound_unique_units": TARGET_UNITS,
            "selection_domain": sampling.get("selection_domain"),
            "seed": 104729,
            "allocation": sampling.get("allocation"),
            "randomization": sampling.get("randomization"),
        },
        "grouping": {
            "stratum": sampling.get("stratum"),
            "anonymous_groups": groups,
            "accounting": accounting,
            "public_provisional_slots_retained": True,
            "private_bound_ids_supersede_provisional_membership": True,
        },
        "inclusion": {
            "probability": "n_h/N_h",
            "inverse_probability_weight": "N_h/n_h",
            "weight_sum": accounting["weight_sum"],
            "no_missing_labels_as_failures": True,
            "evaluation_eligibility": False,
        },
        "gold_custody": {
            "public_templates": "papers/completion/autoformalization/data/gold_facets.jsonl",
            "public_templates_sha256": public["gold_sha256"],
            "private_pending_gold": "gold_facets.pending.private.jsonl",
            "private_pending_gold_sha256": PRIVATE_COMMITMENTS["gold_facets.pending.private.jsonl"],
            "separate_from_packets": True,
            "values_present": False,
            "label_origin": None,
        },
        "packet_identities": public["identities"],
        "reviewer_judgments": {
            "status": "blank_until_AF-028",
            "human_annotations": 0,
            "adjudicated_units": 0,
            "evaluation_eligible_units": 0,
            "invented_annotations_forbidden": True,
        },
        "public_pins": {
            "annotation_packets_sha256": public["packet_sha256"],
            "gold_facets_sha256": public["gold_sha256"],
            "annotation_guidelines_sha256": public["guidelines_sha256"],
            "splits_sha256": public["splits_sha256"],
            "experiment_plan_sha256": public["plan_sha256"],
        },
        "private_store_probe": {
            "visible": private["visible"],
            "commitments_match": private["commitments_match"],
            "source_bodies_read": False,
            "error": private.get("error"),
        },
        "operator_verification": {
            "passed": bool(verification.get("passed")),
            "bound_units": verification.get("bound_units"),
            "human_annotations": verification.get("human_annotations"),
            "evaluation_eligible_units": verification.get("evaluation_eligible_units"),
        },
        "limits": [
            "100 privately bound sources are prepared, not independently annotated.",
            "Repository outputs contain aggregate commitments and schemas only.",
            "Reviewer judgments remain blank until AF-028.",
            "This importer must not generate labels.",
        ],
    }
    manifest["manifest_sha256"] = sha256_obj({key: manifest[key] for key in manifest if key != "manifest_sha256"})
    return manifest


def packet_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "autoformalization-review-packet/v1",
        "title": "AF-027/AF-028 human-review packet and import contracts",
        "description": (
            "Public packets remain candidate-blind templates. Private bound packets "
            "stay in the reviewer store. Returned AF-028 files must preserve packet "
            "identities, distinguish unknown/missing from negative, and must not "
            "include model predictions."
        ),
        "packet_schema": SCHEMA_PACKET,
        "gold_schema": SCHEMA_GOLD,
        "import_schema": SCHEMA_IMPORT,
        "facet_ids": list(FACET_IDS),
        "required_public_packet_fields": [
            "schema",
            "packet_id",
            "packet_role",
            "candidate_blind",
            "gold_values_present",
            "model_outputs_present",
            "teacher_ir_present",
            "evaluation_eligible",
            "annotation_status",
            "source",
        ],
        "blank_until_AF-028": {
            "gold_values_present": False,
            "model_outputs_present": False,
            "teacher_ir_present": False,
            "evaluation_eligible": False,
            "annotators": [],
            "adjudication.status": "pending_independent_review",
            "semantic_claim_status": "unmeasured",
        },
        "returned_review_required_fields": [
            "packet_id",
            "reviewer_id",
            "reviewed_at",
            "attestation",
            "facets",
        ],
        "unknown_or_missing_distinct_from_negative": True,
        "import_refusals": [
            "generated_label",
            "empty_import",
            "missing_review",
            "changed_selection_after_outcomes",
            "model_prediction_in_reviewer_packet",
        ],
        "gold_custody": {
            "public": "blank templates only",
            "private": "pending gold file in operator store",
            "adjudicated": "AF-028 private store, never Git",
        },
        "source_binding": {
            "public": "packet identities and anonymous grouping only",
            "private": "source digests, bodies, record ids, inclusion rows",
        },
    }


def validate_returned_reviews(path: Path, binding: Mapping[str, Any]) -> dict[str, Any]:
    if not path.is_file():
        raise ReviewImportError(
            f"returned review file missing: {path}; empty import cannot pass"
        )
    payload = load_json(path)
    if payload.get("schema") != SCHEMA_IMPORT:
        raise ReviewImportError("returned review schema mismatch")
    records = payload.get("reviews")
    if not isinstance(records, list) or not records:
        raise ReviewImportError("empty import cannot pass")
    expected = {item["private_bound_packet_id"] for item in binding["packet_identities"]}
    expected |= {item["public_packet_id"] for item in binding["packet_identities"]}
    seen = []
    invented = []
    for row in records:
        if not isinstance(row, Mapping):
            raise ReviewImportError("review row is not an object")
        if row.get("generated") or row.get("invented") or row.get("model_generated"):
            invented.append(row.get("packet_id"))
        if row.get("packet_id") not in expected:
            raise ReviewImportError(f"review packet_id not in frozen selection: {row.get('packet_id')}")
        seen.append(row.get("packet_id"))
    if invented:
        raise ReviewImportError(f"generated labels are forbidden: {invented[:5]}")
    missing = sorted(item["private_bound_packet_id"] for item in binding["packet_identities"] if item["private_bound_packet_id"] not in seen and item["public_packet_id"] not in seen)
    if missing:
        raise ReviewImportError(f"missing reviews for frozen packets: {missing[:5]}")
    return {
        "schema": SCHEMA_IMPORT,
        "accepted": True,
        "records": len(records),
        "pending_task": PENDING_TASK,
    }


def verify_blank_state(root: Path) -> dict[str, Any]:
    paths = default_paths(root)
    binding = build_binding_manifest(root)
    report = {
        "schema": SCHEMA_REPORT,
        "task_id": TASK_ID,
        "observed_at": utc_now(),
        "passed": True,
        "bound_units": TARGET_UNITS,
        "groups": TARGET_GROUPS,
        "population_weight_sum": POPULATION_UNITS,
        "public_packets_blank": True,
        "gold_templates_blank": True,
        "human_annotations": 0,
        "evaluation_eligible_units": 0,
        "invented_annotations": 0,
        "returned_reviews_present": False,
        "import_status": "pending_AF-028",
        "binding_manifest_sha256": binding["manifest_sha256"],
        "public_pins": binding["public_pins"],
        "private_store_probe": binding["private_store_probe"],
        "packet_schema_path": str(paths["schema"].relative_to(paths["root"])),
    }
    report["report_sha256"] = sha256_obj({key: report[key] for key in report if key != "report_sha256"})
    return {"binding": binding, "schema": packet_schema(), "verification": report}


def materialize(root: Path) -> dict[str, Any]:
    paths = default_paths(root)
    built = verify_blank_state(root)
    write_json(paths["binding"], built["binding"])
    write_json(paths["schema"], built["schema"])
    return {
        "binding": str(paths["binding"]),
        "schema": str(paths["schema"]),
        "binding_sha256": built["binding"]["manifest_sha256"],
        "verification": built["verification"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    mat = sub.add_parser("materialize", help="Write public binding manifest and packet schema")
    mat.add_argument("--root", type=Path, default=REPO_ROOT)
    ver = sub.add_parser("verify-blank", help="Verify packets/gold remain blank")
    ver.add_argument("--root", type=Path, default=REPO_ROOT)
    imp = sub.add_parser("import", help="Validate actual returned AF-028 files (fail-closed)")
    imp.add_argument("--root", type=Path, default=REPO_ROOT)
    imp.add_argument("--returned", type=Path, required=True)
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if args.command == "materialize":
        summary = materialize(root)
        print(canonical_dumps({
            "binding": summary["binding"],
            "schema": summary["schema"],
            "binding_sha256": summary["binding_sha256"],
            "human_annotations": 0,
            "import_status": "pending_AF-028",
        }))
        return 0
    if args.command == "verify-blank":
        built = verify_blank_state(root)
        print(canonical_dumps(built["verification"]))
        return 0 if built["verification"]["passed"] else 1
    binding = build_binding_manifest(root)
    result = validate_returned_reviews(Path(args.returned), binding)
    print(canonical_dumps(result))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReviewImportError as exc:
        print(f"review_import: {exc}", flush=True)
        raise SystemExit(1)
