#!/usr/bin/env python3
"""AF-028 structural-evidence scope auditor.

Sealed-PATH, standard library only. Reads public AF-005/AF-027 preparation
files and completed receipts. Does not open sealed final packets, source
bodies, private reviewer forms, or pending gold. Does not invent labels.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_POLICY = "af-automated-structural-evidence-scope/v1"
SCHEMA_AUDIT = "af-structural-scope-audit/v1"
SCHEMA_FEEDBACK = "af-optional-author-feedback-status/v1"
TASK_ID = "AF-028"
POPULATION_UNITS = 1913
REVIEW_SLOTS = 100
REVIEW_GROUPS = 20
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
AF005_OUTPUT_PINS = {
    "papers/completion/autoformalization/data/annotation_guidelines.md":
        "papers/completion/autoformalization/receipts/snapshots/AF-005/qualified-outputs/data/annotation_guidelines.md",
    "papers/completion/autoformalization/data/annotation_packets.jsonl":
        "papers/completion/autoformalization/receipts/snapshots/AF-005/qualified-outputs/data/annotation_packets.jsonl",
    "papers/completion/autoformalization/data/gold_facets.jsonl":
        "papers/completion/autoformalization/receipts/snapshots/AF-005/qualified-outputs/data/gold_facets.jsonl",
    "papers/completion/autoformalization/evidence/annotation_provenance.json":
        "papers/completion/autoformalization/receipts/snapshots/AF-005/qualified-outputs/evidence/annotation_provenance.json",
}
AF027_OUTPUT_PINS = {
    "papers/completion/autoformalization/data/review_binding_manifest.json":
        "papers/completion/autoformalization/receipts/snapshots/AF-027/data/review_binding_manifest.json",
    "papers/completion/autoformalization/data/review_packet_schema.json":
        "papers/completion/autoformalization/receipts/snapshots/AF-027/data/review_packet_schema.json",
    "papers/completion/autoformalization/evaluation/review_import.py":
        "papers/completion/autoformalization/receipts/snapshots/AF-027/evaluation/review_import.py",
    "papers/completion/autoformalization/evidence/human_review_handoff.md":
        "papers/completion/autoformalization/receipts/snapshots/AF-027/evidence/human_review_handoff.md",
}
REQUIRED_PHRASES = {
    "policy": [
        "unmeasured_not_collected",
        "original-source semantic gold",
        "optional non-independent author feedback",
        "absence_is_acceptable",
        "AF013 checkpoint/canary/consumer/rollback gates",
    ],
    "report": [
        "not collected / unmeasured",
        "original-source semantic gold",
        "optional non-independent author feedback",
        "1913",
        "Arm E",
        "AF-013",
        "blank",
        "does not fail",
    ],
    "tex": [
        "not original-source semantic gold",
        "faithfully captures the original natural-language source",
        "No independent human semantic-fidelity",
        "1913-unit no-run denominator",
        "optional author comments",
        "non-independent",
        "AF-013",
    ],
    "protocol": [
        "AF-028/v1",
        "not collected and remain unmeasured",
        "Optional author feedback is not required",
        "1913-unit final-test no-run denominator",
        "AF-002/v1",
    ],
    "feedback": [
        "optional non-independent author feedback",
        "absence_is_acceptable",
        "not_collected_unmeasured",
    ],
}
FORBIDDEN_PHRASES = (
    "independent human agreement was measured",
    "annotator reliability is high",
    "checker pass is source gold",
    "semantic fidelity of",
    "kappa=",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")
    return sha256_file(path)


def repo_root_from(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "scripts" / "paper_supervisors.py").is_file():
            return candidate
    raise SystemExit("cannot locate repository root")


def paper_paths(root: Path) -> dict[str, Path]:
    paper = root / "papers" / "completion" / "autoformalization"
    return {
        "root": root,
        "paper": paper,
        "policy": paper / "config" / "structural_evidence_scope.json",
        "audit": paper / "evidence" / "structural_scope_audit.json",
        "feedback": paper / "evidence" / "author_feedback_status.json",
        "report": paper / "evidence" / "structural_scope_report.md",
        "tex": paper / "manuscript" / "empirical_scope.tex",
        "protocol": paper / "protocol.md",
        "gold": paper / "data" / "gold_facets.jsonl",
        "packets": paper / "data" / "annotation_packets.jsonl",
        "guidelines": paper / "data" / "annotation_guidelines.md",
        "provenance": paper / "evidence" / "annotation_provenance.json",
        "binding": paper / "data" / "review_binding_manifest.json",
        "schema": paper / "data" / "review_packet_schema.json",
        "importer": paper / "evaluation" / "review_import.py",
        "handoff": paper / "evidence" / "human_review_handoff.md",
        "receipts": paper / "receipts",
        "af005": paper / "receipts" / "AF-005.json",
        "af027": paper / "receipts" / "AF-027.json",
        "unrun": paper / "receipts" / "snapshots" / "AF-007" / "evidence" / "unrun_tables.json",
        "reference_results": paper / "evaluation" / "reference_results.json",
        "reference_prov": paper / "evidence" / "reference_provenance.json",
        "translation": paper / "evidence" / "translation_receipts.jsonl",
        "native_af018": paper / "evidence" / "native_checker_receipts.jsonl",
        "native_af027": paper / "evidence" / "runtime_qualification" / "native_checker_receipts.jsonl",
        "training_manifest": paper / "runs" / "training_baselines" / "manifest.json",
        "proof_isolation": paper / "evidence" / "proof_head_isolation.json",
        "teacher": paper / "data" / "teacher_manifest.json",
        "splits": paper / "data" / "splits.json",
        "corpus": paper / "data" / "corpus_manifest.json",
        "pipeline_arms": paper / "config" / "pipeline_arms.json",
        "minimal_pairs": paper / "data" / "minimal_pairs.jsonl",
        "retrieval": paper / "data" / "retrieval_judgments.jsonl",
        "af002_protocol": paper / "receipts" / "snapshots" / "AF-002" / "protocol.md",
    }


def count_jsonl(path: Path) -> int:
    if not path.is_file():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def inspect_gold(path: Path) -> dict[str, Any]:
    filled = 0
    pending = 0
    rows = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows += 1
        rec = json.loads(line)
        if rec.get("gold_records_with_values"):
            filled += 1
        status = rec.get("label_status")
        if status in {"pending_independent_review", "unmeasured"} or rec.get("semantic_claim_status") == "unmeasured":
            pending += 1
        facets = rec.get("facets") or {}
        for facet in facets.values():
            if facet.get("values"):
                filled += 1
        if rec.get("annotators"):
            filled += 1
    return {"rows": rows, "values_present_rows": filled, "pending_or_unmeasured_rows": pending}


def inspect_packets(path: Path) -> dict[str, Any]:
    rows = 0
    labeled = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows += 1
        rec = json.loads(line)
        if rec.get("labels") or rec.get("annotator_ids") or rec.get("model_outputs"):
            labeled += 1
    return {"rows": rows, "labeled_rows": labeled}


def pin_outputs(root: Path, receipt_path: Path, mapping: dict[str, str]) -> list[dict[str, Any]]:
    receipt = load_json(receipt_path)
    artifacts = receipt["artifacts"]
    outputs = receipt["outputs"]
    rows = []
    for current, snapshot in mapping.items():
        if outputs.get(current) != snapshot:
            raise SystemExit(f"receipt output mapping drifted: {current}")
        expected = artifacts[snapshot]
        actual = sha256_file(root / current)
        snapshot_hash = sha256_file(root / snapshot)
        rows.append({
            "path": current,
            "snapshot": snapshot,
            "expected_sha256": expected,
            "current_sha256": actual,
            "snapshot_sha256": snapshot_hash,
            "unchanged": actual == expected == snapshot_hash,
        })
        if actual != expected or snapshot_hash != expected:
            raise SystemExit(f"custody changed: {current}")
    return rows


def receipt_hashes(paper: Path) -> dict[str, str]:
    out = {}
    for path in sorted((paper / "receipts").glob("AF-*.json")):
        if path.name == "AF-028.json":
            continue
        out[str(path.relative_to(paper.parents[2]))] = sha256_file(path)
    return out


def classify_native_receipts(path: Path) -> dict[str, Any]:
    kinds: dict[str, int] = {}
    gold_admitted = 0
    rows = []
    if not path.is_file():
        return {"path": str(path), "records": 0, "kinds": kinds, "source_gold_admitted": 0, "sample": rows}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        kind = rec.get("result_kind") or rec.get("execution_status") or "unknown"
        kinds[kind] = kinds.get(kind, 0) + 1
        if rec.get("admitted_as_source_gold") or rec.get("semantic_gold") is True:
            gold_admitted += 1
        if len(rows) < 8:
            rows.append({
                "receipt_id": rec.get("receipt_id") or rec.get("purpose") or rec.get("attempt_id"),
                "checker": rec.get("checker") or rec.get("checker_name"),
                "execution_status": rec.get("execution_status"),
                "result_kind": rec.get("result_kind"),
                "counts_as_native_checked_proof": rec.get("counts_as_native_checked_proof"),
            })
    return {
        "path": str(path),
        "records": sum(kinds.values()),
        "kinds": kinds,
        "source_gold_admitted": gold_admitted,
        "sample": rows,
    }


def reference_check_count(path: Path) -> int:
    data = load_json(path)
    checks = data.get("checks") if isinstance(data, dict) else data
    return len(checks) if isinstance(checks, list) else 0


def required_bindings(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": item.get("source"),
        "goal": item.get("goal"),
        "premises": item.get("premises"),
        "checker": item.get("checker"),
        "seed": item.get("seed"),
        "denominator": item.get("denominator"),
        "cost": item.get("cost"),
        "status": item.get("status"),
        "admitted_as_source_gold": False,
    }


def build_quantities(p: dict[str, Path], hashes: dict[str, str]) -> list[dict[str, Any]]:
    unrun = load_json(p["unrun"])
    teacher = load_json(p["teacher"])
    training = load_json(p["training_manifest"])
    isolation = load_json(p["proof_isolation"])
    arms = load_json(p["pipeline_arms"])
    provenance = load_json(p["provenance"])
    gold = inspect_gold(p["gold"])
    quantities = [
        {
            "id": "Q-final-test-unrun",
            "class": "unrun_failed_unavailable",
            "description": "A-E and T0-T5 final-test tables remain no-run on the natural held-out population.",
            "status": "unrun",
            "denominator": unrun["eligible_basis"]["count"],
            "numerator": 0,
            "source": "papers/completion/autoformalization/data/splits.json",
            "goal": None,
            "premises": None,
            "checker": None,
            "seed": None,
            "cost": "unmeasured_no_final_execution",
            "bindings": {
                "splits_sha256": hashes["splits"],
                "corpus_sha256": hashes["corpus"],
                "unrun_tables_sha256": hashes["unrun"],
                "eligible_field": unrun["eligible_basis"]["field"],
            },
            "admitted_as_source_gold": False,
        },
        {
            "id": "Q-human-fidelity",
            "class": "unmeasured_human_semantic_fidelity",
            "description": "Independent human source-facet labels, agreement and adjudication were not collected.",
            "status": "unmeasured_not_collected",
            "denominator": REVIEW_SLOTS,
            "numerator": None,
            "source": "public AF-005/AF-027 blank packets; private store not opened",
            "goal": None,
            "premises": None,
            "checker": None,
            "seed": None,
            "cost": "human_review_seconds_unmeasured",
            "bindings": {
                "annotators": provenance["agreement_disagreement_adjudication"]["independent_human_annotators"],
                "agreements": provenance["agreement_disagreement_adjudication"]["agreements"],
                "disagreements": provenance["agreement_disagreement_adjudication"]["disagreements"],
                "adjudications": provenance["agreement_disagreement_adjudication"]["adjudications"],
                "gold_rows": gold["rows"],
                "gold_values_present_rows": gold["values_present_rows"],
                "gold_sha256": hashes["gold"],
                "packets_sha256": hashes["packets"],
            },
            "admitted_as_source_gold": False,
        },
        {
            "id": "Q-constructed-af006",
            "class": "constructed_conformance",
            "description": "Twelve newly executed finite reconstruction checks; not recovered historical Table 4.",
            "status": "measured_constructed",
            "denominator": reference_check_count(p["reference_results"]),
            "numerator": reference_check_count(p["reference_results"]),
            "source": "papers/completion/autoformalization/data/minimal_pairs.jsonl",
            "goal": "predefined finite witnesses in Table 4 transcription",
            "premises": "finite Kripke/Boolean/request-audit/identity examples only",
            "checker": "papers/completion/autoformalization/evaluation/reference_semantics.py",
            "seed": None,
            "cost": "recorded_in_AF-006_receipt",
            "bindings": {
                "results_sha256": hashes["reference_results"],
                "provenance_sha256": hashes["reference_prov"],
                "minimal_pairs_sha256": hashes["minimal_pairs"],
            },
            "admitted_as_source_gold": False,
        },
        {
            "id": "Q-constructed-af015",
            "class": "constructed_conformance",
            "description": "Property-specific Boolean/trace translation receipts; solver-local, not native Lean coverage.",
            "status": "measured_constructed_solver_local_or_unavailable",
            "denominator": count_jsonl(p["translation"]),
            "numerator": count_jsonl(p["translation"]),
            "source": "papers/completion/autoformalization/data/policy_code_trace_cases.json",
            "goal": "named Q1/Q2/TDFOL fragment cases",
            "premises": "case-local bridge assumptions",
            "checker": "stdlib_finite_enumeration; native lean unavailable on sealed PATH",
            "seed": None,
            "cost": "recorded_in_AF-015_receipt",
            "bindings": {"translation_sha256": hashes["translation"]},
            "admitted_as_source_gold": False,
        },
        {
            "id": "Q-native-af027",
            "class": "exact_goal_native_checker_acceptance",
            "description": "Independent Lean identity success, Lean explicit failure, and Z3 unsat sentinel on development artifacts.",
            "status": "measured_development_exact_goal",
            "denominator": 3,
            "numerator": 3,
            "source": "AF027-DEV constructed guarded-write artifacts",
            "goal": "ok.lean identity; fail.lean False:=trivial; sentinel.smt2",
            "premises": "development qualification files only",
            "checker": "Lean 4.33.1 digest 79fb1d26...; Z3 4.15.4 digest bbea82f9...",
            "seed": None,
            "cost": "elapsed_ms on AF-027 receipts",
            "bindings": {
                "native_receipts_sha256": hashes["native_af027"],
                "claim_admissible": False,
                "table6_credit": False,
            },
            "admitted_as_source_gold": False,
        },
        {
            "id": "Q-native-af018-sealed",
            "class": "unrun_failed_unavailable",
            "description": "Sealed-PATH native checker probes for assistance goals remain unavailable.",
            "status": "unavailable",
            "denominator": count_jsonl(p["native_af018"]),
            "numerator": 0,
            "source": "AF-018 assistance encodings",
            "goal": "named hammer/leanstral goals where present",
            "premises": None,
            "checker": "absent from sealed PATH",
            "seed": None,
            "cost": "probe elapsed retained; no kernel time",
            "bindings": {"native_receipts_sha256": hashes["native_af018"]},
            "admitted_as_source_gold": False,
        },
        {
            "id": "Q-teacher-af011",
            "class": "teacher_agreement",
            "description": "Mock embedding encode/decode and family CE on train/selection windows. Teacher dataset targets were not generated.",
            "status": "measured_teacher_diagnostic",
            "denominator": 69 + 15,
            "numerator": 69 + 15,
            "source": "AF-004 train/selection CFR windows",
            "goal": "encode_decode_family_ce_without_decompiler_structural_targets",
            "premises": None,
            "checker": None,
            "seed": [104729, 130363, 155921],
            "cost": "AF-011 run wall/cpu in receipt",
            "bindings": {
                "embedding_model": "mock:stable-sha256",
                "teacher_targets_produced": teacher["compiler_and_view_targets"]["targets_produced"],
                "claim_admissible": False,
                "training_manifest_sha256": hashes["training_manifest"],
                "teacher_sha256": hashes["teacher"],
            },
            "admitted_as_source_gold": False,
        },
        {
            "id": "Q-learned-af011-t2",
            "class": "learned_updates",
            "description": "T0-T2 limited-scope sealed-PATH execution; T2 python backend, update_count 0, not packed_cpu.",
            "status": "measured_limited_scope",
            "denominator": "69 train + 15 selection; 3 T0 replays; 3 T1/T2 seeds",
            "numerator": None,
            "source": "AF-004 train/selection only",
            "goal": None,
            "premises": None,
            "checker": None,
            "seed": training["arms"]["T2"]["seeds"],
            "cost": "AF-011 receipt",
            "bindings": {
                "t2_executed": training["arms"]["T2"]["executed"],
                "t2_backend": training["arms"]["T2"].get("executed_backend"),
                "claim_admissible": False,
            },
            "admitted_as_source_gold": False,
        },
        {
            "id": "Q-learned-af012-t3",
            "class": "learned_updates",
            "description": "T3 has no admitted native feedback; isolation probes are constructed controls.",
            "status": "unavailable",
            "denominator": isolation["calibration_and_routing"]["eligible_native_label_count"],
            "numerator": 0,
            "source": "matched AF-011 T2 checkpoints",
            "goal": None,
            "premises": None,
            "checker": "none admitted on sealed PATH",
            "seed": [104729, 130363, 155921],
            "cost": "AF-012 receipt",
            "bindings": {
                "eligible_native_label_count": isolation["calibration_and_routing"]["eligible_native_label_count"],
                "isolation_probe_not_certification": isolation["calibration_and_routing"]["isolation_probe_metrics_are_not_t3_certification"],
                "proof_isolation_sha256": hashes["proof_isolation"],
            },
            "admitted_as_source_gold": False,
        },
        {
            "id": "Q-structural-reconstruction",
            "class": "automated_structural_correctness",
            "description": "Forward/cycle/final reconstruction remain distinct accounting fields; final-test values unrun.",
            "status": "accounted_unrun_on_final_test",
            "denominator": POPULATION_UNITS,
            "numerator": None,
            "source": "final-test lock",
            "goal": None,
            "premises": None,
            "checker": None,
            "seed": None,
            "cost": None,
            "bindings": {"unrun_tables_sha256": hashes["unrun"]},
            "admitted_as_source_gold": False,
        },
        {
            "id": "Q-arm-e-gate",
            "class": "training_activation_gates",
            "description": "Arm E remains unavailable until AF-013 names exact checkpoint/advice identities.",
            "status": "unavailable",
            "denominator": None,
            "numerator": 0,
            "source": None,
            "goal": None,
            "premises": None,
            "checker": arms["arms"]["E"]["checker"]["checker_digest"],
            "seed": None,
            "cost": None,
            "bindings": {
                "promotion_gates": arms["arms"]["E"]["promotion_gates"],
                "development_route": arms["arms"]["E"]["development_route"],
                "pipeline_arms_sha256": hashes["pipeline_arms"],
            },
            "admitted_as_source_gold": False,
        },
        {
            "id": "Q-retrieval-constructed",
            "class": "constructed_conformance",
            "description": "AF-017 retrieval labels are constructed protocol judgments, not independent human adjudication.",
            "status": "measured_constructed",
            "denominator": count_jsonl(p["retrieval"]),
            "numerator": count_jsonl(p["retrieval"]),
            "source": "constructed citation/controlling-source protocol",
            "goal": "relevance",
            "premises": None,
            "checker": None,
            "seed": None,
            "cost": "AF-017 receipt",
            "bindings": {
                "retrieval_sha256": hashes["retrieval"],
                "human_adjudication": False,
            },
            "admitted_as_source_gold": False,
        },
    ]
    for item in quantities:
        item["required_bindings"] = required_bindings(item)
        if item["admitted_as_source_gold"]:
            raise SystemExit(f"gold admission leak: {item['id']}")
    return quantities


def private_store_status() -> dict[str, Any]:
    visible = PRIVATE_STORE.is_dir()
    return {
        "path_recorded": str(PRIVATE_STORE),
        "visible_to_this_process": visible,
        "opened": False,
        "source_bodies_read": False,
        "private_packets_read": False,
        "pending_gold_read": False,
        "commitments": PRIVATE_COMMITMENTS,
        "note": "Existence may be probed; this auditor does not open private files.",
    }


def build_audit(p: dict[str, Path], *, recorded_at: str) -> dict[str, Any]:
    hashes = {
        "policy": sha256_file(p["policy"]),
        "feedback": sha256_file(p["feedback"]),
        "report": sha256_file(p["report"]),
        "tex": sha256_file(p["tex"]),
        "protocol": sha256_file(p["protocol"]),
        "gold": sha256_file(p["gold"]),
        "packets": sha256_file(p["packets"]),
        "guidelines": sha256_file(p["guidelines"]),
        "provenance": sha256_file(p["provenance"]),
        "binding": sha256_file(p["binding"]),
        "schema": sha256_file(p["schema"]),
        "importer": sha256_file(p["importer"]),
        "handoff": sha256_file(p["handoff"]),
        "unrun": sha256_file(p["unrun"]),
        "reference_results": sha256_file(p["reference_results"]),
        "reference_prov": sha256_file(p["reference_prov"]),
        "translation": sha256_file(p["translation"]),
        "native_af018": sha256_file(p["native_af018"]),
        "native_af027": sha256_file(p["native_af027"]),
        "training_manifest": sha256_file(p["training_manifest"]),
        "proof_isolation": sha256_file(p["proof_isolation"]),
        "teacher": sha256_file(p["teacher"]),
        "splits": sha256_file(p["splits"]),
        "corpus": sha256_file(p["corpus"]),
        "pipeline_arms": sha256_file(p["pipeline_arms"]),
        "minimal_pairs": sha256_file(p["minimal_pairs"]),
        "retrieval": sha256_file(p["retrieval"]),
        "af002_protocol_snapshot": sha256_file(p["af002_protocol"]),
        "af005_receipt": sha256_file(p["af005"]),
        "af027_receipt": sha256_file(p["af027"]),
    }
    af005_pins = pin_outputs(p["root"], p["af005"], AF005_OUTPUT_PINS)
    af027_pins = pin_outputs(p["root"], p["af027"], AF027_OUTPUT_PINS)
    gold = inspect_gold(p["gold"])
    packets = inspect_packets(p["packets"])
    if gold["values_present_rows"] != 0 or packets["labeled_rows"] != 0:
        raise SystemExit("public gold or packets are no longer blank")
    if gold["rows"] != REVIEW_SLOTS:
        raise SystemExit(f"expected {REVIEW_SLOTS} gold templates, found {gold['rows']}")
    protocol_text = p["protocol"].read_text(encoding="utf-8")
    historical = p["af002_protocol"].read_text(encoding="utf-8")
    if "# AF-002: frozen research protocol" not in protocol_text:
        raise SystemExit("amended protocol dropped the historical AF-002 freeze")
    if "Protocol version:** `AF-002/v1`" not in protocol_text.replace(" ", ""):
        # keep a looser check that the version string remains
        if "AF-002/v1" not in protocol_text:
            raise SystemExit("historical protocol version missing")
    quantities = build_quantities(p, hashes)
    audit = {
        "schema": SCHEMA_AUDIT,
        "task_id": TASK_ID,
        "policy_id": "AF-028/structural-evidence-scope/v1",
        "policy_schema": SCHEMA_POLICY,
        "recorded_at": recorded_at,
        "authority": "User selected manuscript preparation without outside reviewers on 2026-09-12.",
        "private_store": private_store_status(),
        "source_scoring_rule": (
            "A checker proves the submitted formal statement within its profile. "
            "Whether that statement faithfully captures the source remains unmeasured "
            "without separate valid evidence. No proof/checker pass or automatic label "
            "is original-source semantic gold."
        ),
        "human_review": {
            "independent_review_collected": False,
            "agreement_status": "unmeasured_not_collected",
            "adjudication_status": "not_performed",
            "human_fidelity_status": "unmeasured_not_collected",
            "prepared_blank_packets": REVIEW_SLOTS,
            "groups": REVIEW_GROUPS,
            "population_units": POPULATION_UNITS,
            "public_gold": gold,
            "public_packets": packets,
        },
        "optional_author_feedback": {
            "collected": False,
            "absence_is_acceptable": True,
            "may_be_used_as_gold": False,
            "label": "optional non-independent author feedback",
            "status_path": "papers/completion/autoformalization/evidence/author_feedback_status.json",
            "status_sha256": hashes["feedback"],
        },
        "custody_unchanged": {
            "af005_public_outputs": af005_pins,
            "af027_public_outputs": af027_pins,
            "prior_receipts": receipt_hashes(p["paper"]),
            "historical_af002_protocol_sha256": hashes["af002_protocol_snapshot"],
            "current_protocol_is_amendment": True,
            "historical_protocol_body_retained": "AF-002/v1" in protocol_text and historical.split("\n", 1)[0] in protocol_text,
        },
        "native_checker_inventory": {
            "af027_development": classify_native_receipts(p["native_af027"]),
            "af018_sealed_path": classify_native_receipts(p["native_af018"]),
        },
        "quantities": quantities,
        "evidence_class_summary": {
            "automated_structural_correctness": ["Q-structural-reconstruction"],
            "exact_goal_native_checker_acceptance": ["Q-native-af027"],
            "teacher_agreement": ["Q-teacher-af011"],
            "learned_updates": ["Q-learned-af011-t2", "Q-learned-af012-t3"],
            "constructed_conformance": ["Q-constructed-af006", "Q-constructed-af015", "Q-retrieval-constructed"],
            "unmeasured_human_semantic_fidelity": ["Q-human-fidelity"],
            "unrun_failed_unavailable": ["Q-final-test-unrun", "Q-native-af018-sealed"],
            "training_activation_gates": ["Q-arm-e-gate"],
        },
        "excluded_from_manuscript_scope": [
            "independent human agreement, adjudication, or semantic-fidelity scores",
            "prover or teacher success as original-source meaning",
            "Table 6/11/13 confirmatory performance from development or constructed rows",
            "Arm E activation without AF-013 named checkpoint/advice receipts",
        ],
        "manuscript_wording_path": "papers/completion/autoformalization/manuscript/empirical_scope.tex",
        "analysis_wording_path": "papers/completion/autoformalization/evidence/structural_scope_report.md",
        "deliverable_sha256": {
            "papers/completion/autoformalization/config/structural_evidence_scope.json": hashes["policy"],
            "papers/completion/autoformalization/evidence/author_feedback_status.json": hashes["feedback"],
            "papers/completion/autoformalization/evidence/structural_scope_report.md": hashes["report"],
            "papers/completion/autoformalization/manuscript/empirical_scope.tex": hashes["tex"],
            "papers/completion/autoformalization/protocol.md": hashes["protocol"],
        },
        "limitations": [
            "This audit binds public evidence classes; it is not independent scientific replication.",
            "Private gold and source bodies were not read and therefore cannot be asserted filled or empty beyond public commitments.",
            "AF-029 training execution is out of this task and remains gated by its own criteria.",
        ],
    }
    if any(q["admitted_as_source_gold"] for q in quantities):
        raise SystemExit("a quantity admitted checker/teacher evidence as source gold")
    return audit


def _folded(text: str) -> str:
    return " ".join(text.lower().split())


def phrase_check(label: str, text: str, required: list[str]) -> list[str]:
    missing = []
    folded = _folded(text)
    for needle in required:
        if _folded(needle) not in folded:
            missing.append(f"{label}: missing {needle!r}")
    for bad in FORBIDDEN_PHRASES:
        if _folded(bad) in folded:
            missing.append(f"{label}: forbidden phrase {bad!r}")
    return missing


def check_files(p: dict[str, Path]) -> dict[str, Any]:
    problems: list[str] = []
    policy = load_json(p["policy"])
    audit = load_json(p["audit"])
    feedback = load_json(p["feedback"])
    if policy.get("schema") != SCHEMA_POLICY:
        problems.append("policy schema mismatch")
    if audit.get("schema") != SCHEMA_AUDIT or audit.get("task_id") != TASK_ID:
        problems.append("audit schema/task mismatch")
    if feedback.get("schema") != SCHEMA_FEEDBACK:
        problems.append("feedback schema mismatch")
    if policy.get("independent_human_semantic_labels_available") is not False:
        problems.append("policy must declare independent labels unavailable")
    if policy["optional_author_feedback"]["may_be_used_as_gold"] is not False:
        problems.append("author feedback must not be gold")
    if policy["optional_author_feedback"]["absence_is_acceptable"] is not True:
        problems.append("author-feedback absence must be acceptable")
    if feedback["optional_author_feedback"]["collected"] is not False:
        recs = feedback["optional_author_feedback"].get("records") or []
        for rec in recs:
            if not rec.get("author_provenance"):
                problems.append("author feedback record lacks provenance")
            if rec.get("independent") is True:
                problems.append("author feedback must not be labeled independent")
            if rec.get("used_as_gold") is True:
                problems.append("author feedback used as gold")
    if feedback["independent_human_review"]["collected"] is not False:
        problems.append("independent review marked collected")
    if feedback["independent_human_review"]["kappa_or_majority_imputed"] is not False:
        problems.append("kappa imputed without data")
    if audit["human_review"]["independent_review_collected"] is not False:
        problems.append("audit marks independent review collected")
    if audit["private_store"]["opened"] or audit["private_store"]["source_bodies_read"]:
        problems.append("audit opened private store")
    if any(q.get("admitted_as_source_gold") for q in audit["quantities"]):
        problems.append("audit admits source gold")
    gold = inspect_gold(p["gold"])
    packets = inspect_packets(p["packets"])
    if gold["values_present_rows"] or packets["labeled_rows"]:
        problems.append("public gold/packets are no longer blank")
    pin_outputs(p["root"], p["af005"], AF005_OUTPUT_PINS)
    pin_outputs(p["root"], p["af027"], AF027_OUTPUT_PINS)
    problems.extend(phrase_check("policy", p["policy"].read_text(encoding="utf-8"), REQUIRED_PHRASES["policy"]))
    problems.extend(phrase_check("report", p["report"].read_text(encoding="utf-8"), REQUIRED_PHRASES["report"]))
    problems.extend(phrase_check("tex", p["tex"].read_text(encoding="utf-8"), REQUIRED_PHRASES["tex"]))
    problems.extend(phrase_check("protocol", p["protocol"].read_text(encoding="utf-8"), REQUIRED_PHRASES["protocol"]))
    problems.extend(phrase_check("feedback", p["feedback"].read_text(encoding="utf-8"), REQUIRED_PHRASES["feedback"]))
    for rel, expected in audit["deliverable_sha256"].items():
        actual = sha256_file(p["root"] / rel)
        if actual != expected:
            problems.append(f"deliverable hash drift: {rel}")
    if "do not fail" not in p["report"].read_text(encoding="utf-8").lower() and "does not fail" not in p["report"].read_text(encoding="utf-8").lower():
        problems.append("report: missing absence-does-not-fail wording")
    if problems:
        raise SystemExit("AF-028 check failed:\n- " + "\n- ".join(problems))
    return {
        "passed": True,
        "task_id": TASK_ID,
        "quantities": len(audit["quantities"]),
        "independent_review_collected": False,
        "author_feedback_collected": feedback["optional_author_feedback"]["collected"],
        "private_store_opened": False,
        "public_gold_blank": True,
        "prior_af005_af027_outputs_unchanged": True,
        "source_gold_admitted": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--recorded-at", default="2026-09-12T15:24:00+00:00")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("write", help="Write structural_scope_audit.json from public evidence")
    sub.add_parser("check", help="Verify AF-028 deliverables and unchanged custody")
    args = parser.parse_args(argv)
    start = Path(__file__).resolve()
    root = Path(args.root).resolve() if args.root else repo_root_from(start)
    paths = paper_paths(root)
    if args.command == "write":
        audit = build_audit(paths, recorded_at=args.recorded_at)
        sha = write_json(paths["audit"], audit)
        # Re-bind the audit file hash after write; deliverable map excludes the
        # audit itself to avoid a circular digest.
        summary = {
            "wrote": str(paths["audit"].relative_to(root)),
            "sha256": sha,
            "quantities": len(audit["quantities"]),
            "independent_review_collected": False,
            "private_store_opened": False,
        }
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0
    summary = check_files(paths)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        raise SystemExit(1)
