#!/usr/bin/python3.12
"""Validate LA-006 CVE pairs, controls, and review report.

This checker is structural provenance validation. It does not perform
independent human security review, does not execute untrusted source, and must
not be reported as empirical evaluation.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
PAPER = ROOT / "papers/completion/law_to_action"
PAIRS = PAPER / "benchmark/cases/cve_pairs.jsonl"
CONTROLS = PAPER / "benchmark/cases/cve_controls.jsonl"
REVIEW = PAPER / "benchmark/annotations/cve_review.md"
SOURCES = PAPER / "benchmark/manifests/sources.json"
SPLITS = PAPER / "benchmark/manifests/splits.json"
EVIDENCE = Path(__file__).resolve().parent / "row_evidence.json"
PAIR_SCHEMA = "law-to-action-cve-pair/v1"
CONTROL_SCHEMA = "law-to-action-cve-control/v1"
REQUIRED_CONTROLS = {
    "misleading_cve_similarity",
    "fixed_negative_control",
    "broadened_effects",
    "unknown_scope",
    "wildcard_scope",
    "self_granted_authority",
    "unsupported_transfer",
}
REJECTED_CONTROLS = {
    "wildcard_scope",
    "self_granted_authority",
    "broadened_effects",
}
UNKNOWN_CONTROLS = {
    "unknown_scope",
    "unsupported_transfer",
    "misleading_cve_similarity",
    "fixed_negative_control",
}
FORBIDDEN_FIXTURE_CVES = {"CVE-2026-0042"}


def fail(message: str) -> None:
    raise SystemExit("LA-006 validation failed: " + message)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            fail(f"{path} line {index}: {exc}")
        if not isinstance(row, dict):
            fail(f"{path} line {index} is not an object")
        rows.append(row)
    return rows


def require_text(path: Path, needles: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        fail(f"{path} is empty")
    missing = [needle for needle in needles if needle not in text]
    if missing:
        fail(f"{path} missing required language: {missing}")


def check_polarity(label: dict, case_id: str) -> None:
    if not isinstance(label, dict):
        fail(f"{case_id} missing polarity")
    if label.get("expected") != "unknown":
        fail(f"{case_id} independently reviewed polarity is {label.get('expected')!r}")
    if label.get("independently_reviewed") is not False:
        fail(f"{case_id} claims independently reviewed polarity")
    if label.get("expert_certified") is not False:
        fail(f"{case_id} claims expert-certified polarity")
    if label.get("dataset_derived") not in {"vulnerable_positive", "fixed_negative"}:
        fail(f"{case_id} missing dataset-derived role")


def check_review_fields(row: dict, label: str) -> None:
    provenance = row.get("provenance")
    if not isinstance(provenance, dict):
        fail(f"{label} missing provenance")
    preparer = provenance.get("packet_preparer")
    review = provenance.get("independent_human_security_review")
    if not isinstance(preparer, dict) or not preparer.get("annotator_id"):
        fail(f"{label} missing annotator provenance")
    if preparer.get("is_independent_security_review") is not False:
        fail(f"{label} packet preparer is represented as independent review")
    if not isinstance(review, dict) or review.get("status") != "not_obtained":
        fail(f"{label} independent review status must be not_obtained")
    if review.get("reviewer_id") not in {None, ""}:
        fail(f"{label} invented independent reviewer identity")
    if review.get("generated_labels_are_not_expert_review") is not True:
        fail(f"{label} does not record that generated labels are not expert review")
    adjudication = row.get("adjudication")
    if not isinstance(adjudication, dict):
        fail(f"{label} missing adjudication")
    if adjudication.get("status") != "unresolved_missing_expert_review":
        fail(f"{label} adjudication is not visibly unresolved")
    if adjudication.get("final_adjudication") is not None:
        fail(f"{label} final adjudication claimed without expert review")
    if adjudication.get("evaluation_admission") != "blocked_until_independent_human_security_review":
        fail(f"{label} evaluation admission is not blocked")
    if row.get("universal_security_claimed") is not False:
        fail(f"{label} claims universal security")
    if row.get("fixture_cve") is not False or row.get("mocked_source_record") is not False:
        fail(f"{label} marks a fixture or mocked source record")


def check_quote(span: dict, label: str) -> None:
    quote = span.get("quoted_text")
    if not isinstance(quote, str) or not quote.strip():
        fail(f"{label} empty quote")
    if span.get("quoted_sha256") != sha256_text(quote):
        fail(f"{label} quoted_sha256 mismatch")


def check_pair(row: dict, planned: dict, evidence_by_source: dict, artifact: dict) -> None:
    if row.get("schema") != PAIR_SCHEMA:
        fail(f"{row.get('pair_id')} has wrong schema")
    source = row.get("source")
    if not isinstance(source, dict):
        fail("pair missing source")
    source_id = source.get("source_id")
    if source_id not in planned:
        fail(f"unexpected source_id {source_id!r}")
    assignment = planned[source_id]
    if row.get("split") != assignment["split"]:
        fail(f"{source_id} split mismatch")
    if row.get("lineage_family_id") != assignment["lineage_family_id"]:
        fail(f"{source_id} family mismatch")
    if row.get("held_out") is not (assignment["split"] != "development"):
        fail(f"{source_id} held_out flag incorrect")
    if row.get("empirical_sample") is not True or row.get("enters_empirical_sample_count") is not True:
        fail(f"{source_id} empirical pair is not counted as empirical")
    if row.get("fixture") is not False:
        fail(f"{source_id} empirical pair is marked fixture")
    if source.get("cve_id") in FORBIDDEN_FIXTURE_CVES:
        fail(f"{source_id} fabricated fixture CVE entered empirical counts")
    if source.get("cve_id") != assignment["cve_id"]:
        fail(f"{source_id} CVE identifier mismatch")
    if source.get("file_row_number") != assignment["file_row_number"]:
        fail(f"{source_id} file_row_number mismatch")
    if source.get("fix_commit") != assignment["fix_commit"]:
        fail(f"{source_id} fix commit mismatch")
    if source.get("repository") != assignment["repository"]:
        fail(f"{source_id} repository mismatch")
    if source.get("source_record_sha256") != assignment["source_record_sha256"]:
        fail(f"{source_id} source_record_sha256 mismatch")
    if source.get("shard_sha256") != artifact["sha256"]:
        fail(f"{source_id} shard hash mismatch")
    if source.get("revision") != artifact["revision"]:
        fail(f"{source_id} revision mismatch")
    evidence_row = evidence_by_source[source_id]["row"]
    if source.get("source_record_sha256") != evidence_row["source_record_sha256"]:
        fail(f"{source_id} evidence hash mismatch")
    sides = row.get("sides")
    if not isinstance(sides, dict) or set(sides) != {"vulnerable", "fixed"}:
        fail(f"{source_id} missing vulnerable/fixed sides")
    vulnerable_id, fixed_id = assignment["planned_case_ids"]
    if sides["vulnerable"].get("case_id") != vulnerable_id:
        fail(f"{source_id} case-0 identity mismatch")
    if sides["fixed"].get("case_id") != fixed_id:
        fail(f"{source_id} case-1 identity mismatch")
    check_polarity(sides["vulnerable"]["polarity"], vulnerable_id)
    check_polarity(sides["fixed"]["polarity"], fixed_id)
    if sides["vulnerable"]["polarity"]["dataset_derived"] != "vulnerable_positive":
        fail(f"{source_id} vulnerable role is not polarity-locked")
    if sides["fixed"]["polarity"]["dataset_derived"] != "fixed_negative":
        fail(f"{source_id} fixed role is not polarity-locked")
    if sides["vulnerable"]["polarity"]["dataset_derived"] == "fixed_negative":
        fail(f"{source_id} attached a fixed label to a vulnerable example")
    for role in ("vulnerable", "fixed"):
        side = sides[role]
        if side.get("executed") is not False:
            fail(f"{source_id} {role} claims execution")
        if side.get("body_present") is not evidence_row[role]["present"]:
            fail(f"{source_id} {role} body presence mismatch")
        if side.get("body_sha256") != evidence_row[role]["sha256"]:
            fail(f"{source_id} {role} body hash mismatch")
        spans = side.get("source_spans")
        if not isinstance(spans, list):
            fail(f"{source_id} {role} missing source spans")
        for span in spans:
            check_quote(span, f"{source_id} {role}")
        quote = evidence_row[role]["quote"]
        if quote:
            quoted = [span for span in spans if span.get("role") == f"{role}_code_span"]
            if not quoted or quoted[0]["quoted_sha256"] != quote["quoted_sha256"]:
                fail(f"{source_id} {role} unique quote mismatch")
    restriction = row.get("restriction_candidate")
    if not isinstance(restriction, dict):
        fail(f"{source_id} missing restriction candidate")
    if restriction.get("authoritative") is not False:
        fail(f"{source_id} restriction claims authority")
    if restriction.get("grants_execution_authority") is not False:
        fail(f"{source_id} restriction grants execution authority")
    if restriction.get("wildcard") is True:
        fail(f"{source_id} admitted a wildcard restriction into the pair")
    mapping = row.get("intent_code_effect_mapping")
    if not isinstance(mapping, dict) or mapping.get("correlation") != "unknown":
        fail(f"{source_id} missing unknown intent/code-effect mapping")
    if mapping.get("code_effect", {}).get("status") != "unsupported_transfer":
        fail(f"{source_id} unsupported transfer was not recorded")
    evidence = row.get("supported_behavior_evidence")
    if not isinstance(evidence, dict):
        fail(f"{source_id} missing supported behavior evidence")
    if evidence.get("runnable_sandbox_reproduction") != "not_run_untrusted_source_not_executed":
        fail(f"{source_id} claims a sandbox reproduction that was not run")
    check_review_fields(row, source_id)


def check_control(row: dict, planned: dict, evidence: dict) -> None:
    if row.get("schema") != CONTROL_SCHEMA:
        fail(f"{row.get('control_id')} has wrong schema")
    parent = row.get("parent_source_id")
    if parent not in planned:
        fail(f"{row.get('control_id')} parent is not a frozen CVE family")
    if row.get("lineage_family_id") != planned[parent]["lineage_family_id"]:
        fail(f"{row.get('control_id')} left its parent family")
    if row.get("split") != planned[parent]["split"]:
        fail(f"{row.get('control_id')} split independently from its parent")
    if row.get("empirical_sample") is not False or row.get("enters_empirical_sample_count") is not False:
        fail(f"{row.get('control_id')} entered empirical sample counts")
    control_class = row.get("control_class")
    if control_class not in REQUIRED_CONTROLS:
        fail(f"{row.get('control_id')} unknown control class {control_class!r}")
    if control_class in REJECTED_CONTROLS and row.get("expected_status") != "rejected":
        fail(f"{row.get('control_id')} must remain rejected")
    if control_class in UNKNOWN_CONTROLS and row.get("expected_status") != "unknown":
        fail(f"{row.get('control_id')} must remain unknown")
    if row.get("expected_polarity") != "unknown":
        fail(f"{row.get('control_id')} forced a reviewed polarity")
    reason = row.get("reason")
    if not isinstance(reason, str) or len(reason.strip()) < 20:
        fail(f"{row.get('control_id')} missing rejection/unknown reason")
    if control_class == "misleading_cve_similarity":
        distractor = row.get("distractor")
        if not isinstance(distractor, dict):
            fail(f"{row.get('control_id')} missing real distractor")
        expected = evidence["distractors"][parent]["row"]
        if distractor.get("cve_id") != expected["cve_id"]:
            fail(f"{row.get('control_id')} distractor CVE mismatch")
        if distractor.get("cve_id") in {planned[key]["cve_id"] for key in planned}:
            fail(f"{row.get('control_id')} reused an empirical CVE as a distractor identity")
        if distractor.get("cve_id") in FORBIDDEN_FIXTURE_CVES:
            fail(f"{row.get('control_id')} fabricated fixture CVE used as distractor")
        if distractor.get("source_record_sha256") != expected["source_record_sha256"]:
            fail(f"{row.get('control_id')} distractor is not the extracted real row")
        if row.get("fixture") is not False:
            fail(f"{row.get('control_id')} real distractor marked as fixture")
    if control_class == "wildcard_scope":
        payload = row.get("rejected_payload") or {}
        if "*" not in json.dumps(payload) and "any" not in json.dumps(payload).lower():
            fail(f"{row.get('control_id')} wildcard payload missing")
    if control_class == "self_granted_authority":
        payload = row.get("rejected_payload") or {}
        if payload.get("grants_execution_authority") is not True:
            fail(f"{row.get('control_id')} self-granted authority payload missing")
    check_review_fields(row, row.get("control_id"))


def main() -> int:
    for path in (PAIRS, CONTROLS, REVIEW, EVIDENCE):
        if not path.is_file():
            fail(f"missing {path}")
    sources = load_json(SOURCES)
    splits = load_json(SPLITS)
    evidence = load_json(EVIDENCE)
    artifact = next(row for row in sources["source_artifacts"] if row["artifact_id"] == "cve-first-shard")
    planned: dict[str, dict] = {}
    for assignment in splits["assignments"]:
        if assignment["population"] != "cve":
            continue
        source = next(
            row for row in sources["source_records"] if row["source_id"] == assignment["source_id"]
        )
        planned[assignment["source_id"]] = {
            "source_id": assignment["source_id"],
            "lineage_family_id": assignment["lineage_family_id"],
            "split": assignment["split"],
            "planned_case_ids": assignment["planned_case_ids"],
            "cve_id": source["source_locator"]["cve_id"],
            "file_row_number": source["source_locator"]["file_row_number"],
            "fix_commit": source["source_locator"]["fix_commit"],
            "repository": source["source_locator"]["repository"],
            "source_record_sha256": source["source_record_sha256"],
        }
    if len(planned) != 12:
        fail(f"expected 12 reserved CVE families, found {len(planned)}")
    evidence_by_source = {item["source_id"]: item for item in evidence["selected_rows"]}
    if set(evidence_by_source) != set(planned):
        fail("evidence selected rows do not match frozen CVE families")
    pairs = load_jsonl(PAIRS)
    if len(pairs) != 12:
        fail(f"expected 12 pair records, found {len(pairs)}")
    seen_pairs = []
    seen_cases = []
    empirical_cves = []
    for row in pairs:
        pair_id = row.get("pair_id")
        if pair_id in seen_pairs:
            fail(f"duplicate pair_id {pair_id}")
        seen_pairs.append(pair_id)
        check_pair(row, planned, evidence_by_source, artifact)
        empirical_cves.append(row["source"]["cve_id"])
        seen_cases.extend(
            [row["sides"]["vulnerable"]["case_id"], row["sides"]["fixed"]["case_id"]]
        )
    expected_cases = [case_id for item in planned.values() for case_id in item["planned_case_ids"]]
    if sorted(seen_cases) != sorted(expected_cases):
        fail("reserved CVE case identities are incomplete")
    if len(set(empirical_cves)) != 12:
        fail("empirical CVE identifiers are not 12 distinct real records")
    if any(item in FORBIDDEN_FIXTURE_CVES for item in empirical_cves):
        fail("fabricated fixture CVE entered empirical sample counts")
    controls = load_jsonl(CONTROLS)
    if len(controls) != 12 * len(REQUIRED_CONTROLS):
        fail(f"expected {12 * len(REQUIRED_CONTROLS)} controls, found {len(controls)}")
    classes_by_family: dict[str, set[str]] = {}
    for row in controls:
        check_control(row, planned, evidence)
        classes_by_family.setdefault(row["parent_source_id"], set()).add(row["control_class"])
        if row.get("enters_empirical_sample_count") is not False:
            fail("a control entered empirical sample counts")
    for source_id, classes in classes_by_family.items():
        if classes != REQUIRED_CONTROLS:
            fail(f"{source_id} missing control classes {sorted(REQUIRED_CONTROLS - classes)}")
    require_text(
        REVIEW,
        [
            "Review status: unresolved",
            "Independent human security review was not",
            "not expert review",
            "unknown",
            "Evaluation admission is blocked",
            "Fabricated fixture CVE identifiers in empirical counts | 0",
            "Mocked source records in empirical counts | 0",
            "Independent expert reviews | 0",
            "wildcard",
            "self-granted",
            "unsupported transfer",
            "A fix for one restriction is not universal security",
            "untrusted",
            "not executed",
            "No Cohen's kappa",
            "unresolved_missing_expert_review",
        ],
    )
    report = REVIEW.read_text(encoding="utf-8")
    if re.search(r"expert review (was|is) (completed|obtained|performed)", report, re.I):
        fail("review report claims expert review was obtained")
    if "CVE-2026-0042" in PAIRS.read_text(encoding="utf-8"):
        fail("fixture CVE identifier present in empirical pairs")
    payload = {
        "status": "passed",
        "pairs": len(pairs),
        "empirical_cases": 24,
        "controls": len(controls),
        "control_classes": sorted(REQUIRED_CONTROLS),
        "fixture_cves_in_empirical_counts": 0,
        "mocked_source_records_in_empirical_counts": 0,
        "independent_human_security_review": "not_obtained",
        "expected_polarity": "unknown",
        "adjudication": "unresolved_missing_expert_review",
        "evaluation_admission": "blocked",
        "limitation": "Structural packet checks passed; this is not independent scientific or security expert review.",
    }
    json.dump(payload, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
