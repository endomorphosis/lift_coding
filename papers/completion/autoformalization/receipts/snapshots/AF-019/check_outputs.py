#!/usr/bin/env python3
"""Validate AF-019 domain-transfer artifacts against acceptance criteria."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parents[2]
REPO_ROOT = PAPER_ROOT.parents[2]

SCHEMA = "autoformalization-domain-transfer-result/v1"
MATRIX_SCHEMA = "autoformalization-domain-scope-matrix/v1"
CLAIM_CLASSES = {
    "structural_compatibility",
    "learned_transfer",
    "semantic_proof_transfer",
    "multimodal_extraction",
    "summary",
}
EVALUATED_DOMAINS = {"legal", "security", "intent", "software", "trace"}
AF011_T0_T2 = "5975e52cd3db3f1ac7e8be248351d685782e102a56d69dd17ecb4b1ef1d23737"
AF029_T2 = {
    "00b940fcd4a96a67fdccde88310b5956e790e3a5d66055984d19cd1b3c61a8d8",
    "095147ede126c6a6f4f9f2817c208ce78e6662c3ce9d8ec6979a42aceac0ebf0",
    "cb766e9e811216a00f47ca8d96263c1d7dce4ec8c458f417ae36b11db8304c2b",
}
REQUIRED_MATRIX_FIELDS = (
    "profile",
    "population",
    "formal_target_provenance",
    "checkpoint",
    "baseline",
)
PERFORMANCE_KEYS = ("wer", "cer", "word_error_rate", "character_error_rate", "accuracy", "f1", "bleu")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> int:
    results_path = PAPER_ROOT / "runs" / "domain_transfer" / "results.jsonl"
    matrix_path = PAPER_ROOT / "evidence" / "domain_scope_matrix.json"
    results = load_jsonl(results_path)
    matrix = load_json(matrix_path)
    errors: list[str] = []

    if matrix.get("schema") != MATRIX_SCHEMA:
        errors.append(f"bad matrix schema {matrix.get('schema')}")
    if matrix.get("task_id") != "AF-019":
        errors.append("matrix task_id is not AF-019")
    if matrix.get("independent_source_semantic_labels", {}).get("available") is not False:
        errors.append("matrix must record independent labels unavailable")
    if matrix.get("independent_source_semantic_labels", {}).get("implied_by_prover_or_teacher"):
        errors.append("matrix implies source-semantic gold from prover/teacher")

    observations = [row for row in results if row.get("kind") == "observation"]
    summaries = [row for row in results if row.get("kind") == "summary"]
    if len(summaries) != 1:
        errors.append(f"expected one summary, got {len(summaries)}")
    if not observations:
        errors.append("no observation rows")

    by_class: dict[str, list] = defaultdict(list)
    by_domain_class: dict[tuple[str, str], list] = defaultdict(list)
    for row in observations:
        if row.get("schema") != SCHEMA:
            errors.append(f"bad result schema {row.get('record_id')}")
        claim = row.get("claim_class")
        if claim not in CLAIM_CLASSES:
            errors.append(f"unknown claim_class {claim} on {row.get('record_id')}")
        by_class[claim].append(row)
        by_domain_class[(row.get("domain"), claim)].append(row)
        facets = row.get("source_facets") or {}
        if facets.get("independent_gold_present"):
            errors.append(f"independent gold implied {row.get('record_id')}")
        if facets.get("all_facet_match") is True:
            errors.append(f"source facet match fabricated {row.get('record_id')}")
        if row.get("counts_as_source_semantic_transfer"):
            errors.append(f"source-semantic transfer claimed {row.get('record_id')}")
        if row.get("counts_as_native_checked_proof"):
            errors.append(f"native checked proof claimed {row.get('record_id')}")
        if row.get("eligible_for_natural_table"):
            errors.append(f"natural table admission {row.get('record_id')}")
        proof = row.get("proof") or {}
        for key in ("useful", "false_transfer", "checker_class", "receipt_sha256"):
            if key not in proof:
                errors.append(f"proof missing {key} on {row.get('record_id')}")
        identities = row.get("identities") or {}
        for key in ("experiment_arm", "model", "tool", "checker", "compiler"):
            if key not in identities:
                errors.append(f"identities missing {key} on {row.get('record_id')}")
        if row.get("claim_class") == "learned_transfer" and row.get("claim_class") == "semantic_proof_transfer":
            errors.append(f"mixed claim class {row.get('record_id')}")
        extra_struct = row.get("structural") or {}
        extra_learned = row.get("learned_transfer") or {}
        extra_proof = row.get("semantic_proof_transfer") or {}
        if row.get("claim_class") == "structural_compatibility":
            if extra_learned or extra_proof.get("accepted_transfer"):
                errors.append(f"structural row carries transfer scores {row.get('record_id')}")
            if extra_struct.get("not_statistical_transfer") is not True and row.get("record_id") != "structural:feature-transfer-is-architecture-migration":
                if extra_struct.get("cross_domain_operator") is True:
                    errors.append(f"structural row claims cross-domain operator {row.get('record_id')}")
        if row.get("claim_class") == "learned_transfer":
            if extra_struct.get("compatible") is True:
                errors.append(f"learned row uses structural compatibility as transfer {row.get('record_id')}")
            if extra_proof.get("accepted_transfer"):
                errors.append(f"learned row uses proof transfer as learned transfer {row.get('record_id')}")
            if extra_learned.get("source_semantic_gold"):
                errors.append(f"learned row claims source gold {row.get('record_id')}")
        if row.get("claim_class") == "semantic_proof_transfer":
            if extra_struct.get("compatible") is True:
                errors.append(f"proof row uses adapter compatibility as proof {row.get('record_id')}")
            if extra_proof.get("source_semantic_gold"):
                errors.append(f"proof row claims source gold {row.get('record_id')}")
        multimodal = row.get("multimodal") or {}
        if row.get("claim_class") == "multimodal_extraction":
            if multimodal.get("performance_claimed"):
                errors.append(f"OCR/ASR performance claimed {row.get('record_id')}")
            if multimodal.get("measured_extraction_route"):
                errors.append(f"unverified extraction route marked measured {row.get('record_id')}")
            for key in PERFORMANCE_KEYS:
                if multimodal.get(key) not in (None, False):
                    errors.append(f"OCR/ASR metric {key} present on {row.get('record_id')}")
            text = json.dumps(row)
            if any(token in text.lower() for token in (" wer=", '"wer": 0', '"accuracy": 0')):
                errors.append(f"OCR/ASR numeric performance in {row.get('record_id')}")

    for claim in ("structural_compatibility", "learned_transfer", "semantic_proof_transfer"):
        if not by_class.get(claim):
            errors.append(f"missing claim class {claim}")
    if not by_class.get("multimodal_extraction"):
        errors.append("missing multimodal extraction bound")

    domains = matrix.get("domains") or {}
    for domain in EVALUATED_DOMAINS:
        entry = domains.get(domain)
        if not isinstance(entry, dict) or not entry.get("evaluated"):
            errors.append(f"domain {domain} is not evaluated in the matrix")
            continue
        for field in REQUIRED_MATRIX_FIELDS:
            if field not in entry:
                errors.append(f"domain {domain} missing {field}")
        profile = entry.get("profile") or {}
        if not profile.get("supported"):
            errors.append(f"evaluated domain {domain} lacks supported profile")
        population = entry.get("population") or {}
        if not population.get("frozen"):
            errors.append(f"evaluated domain {domain} population is not frozen")
        target = entry.get("formal_target_provenance") or {}
        if not target:
            errors.append(f"evaluated domain {domain} missing formal target provenance")
        checkpoint = entry.get("checkpoint") or {}
        if not checkpoint.get("actual"):
            errors.append(f"evaluated domain {domain} missing actual checkpoint")
        baseline = entry.get("baseline") or {}
        if not baseline.get("actual"):
            errors.append(f"evaluated domain {domain} missing actual baseline")
        if entry.get("source_semantic_gold"):
            errors.append(f"domain {domain} implies source-semantic gold")
        labels = entry.get("independent_labels") or {}
        if labels.get("available"):
            errors.append(f"domain {domain} claims independent labels")
        classes = entry.get("claim_classes") or {}
        if domain in {"legal", "security", "intent", "software"}:
            for claim in ("structural_compatibility", "learned_transfer", "semantic_proof_transfer"):
                if claim not in classes:
                    errors.append(f"domain {domain} does not separately record {claim}")

    media = domains.get("media") or {}
    if media.get("evaluated"):
        errors.append("media must not be evaluated without an extraction route")
    extraction = media.get("extraction_route") or {}
    if extraction.get("measured") or extraction.get("ocr_performance_claimed") or extraction.get("asr_performance_claimed"):
        errors.append("media extraction/performance claimed without a measured route")

    learned = by_class.get("learned_transfer") or []
    t2_rows = [row for row in learned if row.get("experiment_arm") == "learned.AF011-T2-vs-T0"]
    if len(t2_rows) < 3:
        errors.append(f"expected AF-011 T2 learned rows for security/intent/software, got {len(t2_rows)}")
    for row in t2_rows:
        payload = row.get("learned_transfer") or {}
        if payload.get("shared_parameter_delta") != 0 or payload.get("t0_equals_t2") is not True:
            errors.append(f"AF-011 T2 null delta not recorded {row.get('record_id')}")
        if payload.get("calibrated_target_formalizer"):
            errors.append(f"calibrated formalizer claimed {row.get('record_id')}")
        if row.get("identities", {}).get("checkpoint") != AF011_T0_T2:
            errors.append(f"AF-011 checkpoint identity missing {row.get('record_id')}")
    af029_rows = [row for row in learned if row.get("experiment_arm") == "learned.AF029-T2-minilm-packed-cpu"]
    if len(af029_rows) < 3:
        errors.append("AF-029 T2 unavailability not recorded per target domain")
    for row in af029_rows:
        if row.get("execution_status") != "unavailable" or row.get("result_kind") != "no_run":
            errors.append(f"AF-029 application must be unavailable/no_run {row.get('record_id')}")
        payload = row.get("learned_transfer") or {}
        if payload.get("unavailable_is_not_zero") is not True:
            errors.append(f"AF-029 unavailable treated as zero {row.get('record_id')}")
        identities = set(row.get("identities", {}).get("af029_t2_identities") or [])
        if identities != AF029_T2:
            errors.append(f"AF-029 T2 identities not bound {row.get('record_id')}")

    proof_rows = by_class.get("semantic_proof_transfer") or []
    outcomes = {row.get("semantic_proof_transfer", {}).get("outcome") for row in proof_rows}
    for required in (
        "q1_holds_on_guarded_model",
        "q1_countermodel",
        "plan_is_not_occurrence",
        "unresolved_identity",
        "constraint_stated_not_implementation_proof",
    ):
        if required not in outcomes:
            errors.append(f"missing semantic proof outcome {required}")
    accepted = [row for row in proof_rows if (row.get("semantic_proof_transfer") or {}).get("accepted_transfer")]
    if not accepted:
        errors.append("no accepted constructed semantic proof transfer recorded")
    for row in accepted:
        if (row.get("semantic_proof_transfer") or {}).get("not_learned_transfer") is not True:
            errors.append(f"accepted proof not separated from learned transfer {row.get('record_id')}")
        if row.get("proof", {}).get("checker_class") == "native":
            errors.append(f"native checker class without kernel {row.get('record_id')}")

    structural = by_class.get("structural_compatibility") or []
    if not any((row.get("structural") or {}).get("compatible") for row in structural):
        errors.append("no adapter recorded as structurally compatible")
    if any((row.get("structural") or {}).get("cross_domain_operator") for row in structural):
        errors.append("feature-transfer module treated as cross-domain operator")

    summary = summaries[0] if summaries else {}
    if summary.get("source_semantic_gold") or summary.get("ocr_asr_performance_claimed"):
        errors.append("summary claims source gold or OCR/ASR performance")
    if matrix["independent_source_semantic_labels"].get("gold_rows_with_values") != 0:
        errors.append("independent gold values are present; AF-019 must not treat them as transfer gold")
    if summary.get("gold_rows_with_values") not in (0, None):
        errors.append("summary reports independent gold values")

    # Frozen input pins from AF-004/AF-011.
    frozen = matrix.get("frozen_inputs") or summary.get("frozen_inputs") or {}
    expected = {
        "corpus_manifest_sha256": "ca410804725f7e323551082243cea3ca5e381bcdc87b0726a0dd6f5dcfbb5ed6",
        "splits_sha256": "d4989a3ea15f7035a4e85621bc220b4567828537733c4de4947fd17637bc0b27",
        "environment_manifest_sha256": "06d1ff983d6879cfbe13e700267f4d2f2d21dbc2136c5d062276a4a7dfced1d5",
        "structural_evidence_scope_sha256": "6373506c21a276388ef3ebf582d48d01a7aa5cc114ca414c0ca07a23f4f8ceea",
    }
    for key, digest in expected.items():
        if frozen.get(key) != digest:
            errors.append(f"frozen pin mismatch {key}: {frozen.get(key)}")

    if errors:
        print("AF-019 check failed:")
        for item in errors:
            print(f"- {item}")
        return 1
    report = {
        "ok": True,
        "n_observations": len(observations),
        "claim_classes": {key: len(value) for key, value in sorted(by_class.items())},
        "evaluated_domains": sorted(EVALUATED_DOMAINS),
        "independent_labels": False,
        "ocr_asr_performance_claimed": False,
        "source_semantic_gold": False,
    }
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
