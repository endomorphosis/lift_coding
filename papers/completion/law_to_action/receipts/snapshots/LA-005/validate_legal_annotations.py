#!/usr/bin/python3.12
"""Validate LA-005 legal annotation packets, guidelines, and review report.

This checker is structural provenance validation. It does not perform
independent human legal expert review and must not be reported as such.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
PAPER = ROOT / "papers/completion/law_to_action"
ANNOT = PAPER / "benchmark/annotations"
JSONL = ANNOT / "legal.jsonl"
GUIDELINES = ANNOT / "legal_guidelines.md"
REPORT = ANNOT / "legal_review_report.md"
SOURCES = PAPER / "benchmark/manifests/sources.json"
SPLITS = PAPER / "benchmark/manifests/splits.json"

SCHEMA = "law-to-action-legal-annotation/v1"
REQUIRED_MUTATIONS = {
    "omitted_legal_exception",
    "wrong_date_or_jurisdiction",
    "unsupported_construct",
    "no_applicable_record",
}
ATOM_FIELDS = (
    "modality",
    "actor",
    "action",
    "object",
    "conditions",
    "exceptions",
    "effective_interval",
    "jurisdiction",
    "authority",
    "definitions",
    "cross_references",
)
AMBIGUOUS_MUTATIONS = {
    "omitted_legal_exception",
    "wrong_date_or_jurisdiction",
    "unsupported_construct",
    "no_applicable_record",
}


def fail(message: str) -> None:
    raise SystemExit("LA-005 validation failed: " + message)


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


def field_status(atom) -> str:
    if isinstance(atom, dict):
        return str(atom.get("status") or "")
    return ""


def collect_statuses(atom) -> list[str]:
    if isinstance(atom, dict):
        return [field_status(atom)]
    if isinstance(atom, list):
        return [field_status(item) for item in atom if isinstance(item, dict)]
    return []


def require_text(path: Path, needles: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        fail(f"{path} is empty")
    missing = [needle for needle in needles if needle not in text]
    if missing:
        fail(f"{path} missing required language: {missing}")


def check_atom(case_id: str, name: str, atom) -> None:
    values = atom if isinstance(atom, list) else [atom]
    if not values:
        fail(f"{case_id} atom {name} is empty")
    for item in values:
        if not isinstance(item, dict):
            fail(f"{case_id} atom {name} has a non-object entry")
        if "value" not in item or "status" not in item or "span_ids" not in item:
            fail(f"{case_id} atom {name} missing value/status/span_ids")
        if item["status"] not in {"source_attested", "unknown", "unsupported"}:
            fail(f"{case_id} atom {name} has invalid status {item['status']!r}")
        if not isinstance(item["span_ids"], list):
            fail(f"{case_id} atom {name} span_ids must be a list")
        if item["status"] == "source_attested" and not item["span_ids"]:
            fail(f"{case_id} atom {name} is source_attested without spans")


def check_record(row: dict, planned: dict[str, dict], artifacts: dict[str, dict]) -> None:
    case_id = row.get("case_id")
    if case_id not in planned:
        fail(f"unexpected case_id {case_id!r}")
    if row.get("schema") != SCHEMA:
        fail(f"{case_id} has wrong schema")
    assignment = planned[case_id]
    if row.get("split") != assignment["split"]:
        fail(f"{case_id} split {row.get('split')!r} != reserved {assignment['split']!r}")
    held_out = assignment["split"] != "development"
    if row.get("held_out") is not held_out:
        fail(f"{case_id} held_out flag incorrect")
    source = row.get("source")
    if not isinstance(source, dict):
        fail(f"{case_id} missing source block")
    if source.get("source_id") != assignment["source_id"]:
        fail(f"{case_id} source_id mismatch")
    if source.get("lineage_family_id") != assignment["lineage_family_id"]:
        fail(f"{case_id} family mismatch")
    artifact = artifacts[source["artifact_id"]]
    if source.get("document_sha256") != artifact["sha256"]:
        fail(f"{case_id} document hash mismatch")
    spans = row.get("source_spans")
    if not isinstance(spans, list) or not spans:
        fail(f"{case_id} missing source spans")
    span_ids = set()
    for span in spans:
        if not isinstance(span, dict):
            fail(f"{case_id} span is not an object")
        for key in ("span_id", "role", "quoted_text", "normalized_char_start", "normalized_char_end", "quoted_sha256"):
            if key not in span:
                fail(f"{case_id} span missing {key}")
        quote = span["quoted_text"]
        if not isinstance(quote, str) or len(quote) < 20:
            fail(f"{case_id} span quote too short")
        if sha256_text(quote) != span["quoted_sha256"]:
            fail(f"{case_id} span {span['span_id']} quoted_sha256 mismatch")
        start, end = span["normalized_char_start"], span["normalized_char_end"]
        if type(start) is not int or type(end) is not int or end - start != len(quote) or start < 0:
            fail(f"{case_id} span {span['span_id']} offsets do not match quoted text")
        if span["span_id"] in span_ids:
            fail(f"{case_id} duplicate span_id {span['span_id']}")
        span_ids.add(span["span_id"])
    atoms = row.get("atoms")
    if not isinstance(atoms, dict):
        fail(f"{case_id} missing atoms")
    for name in ATOM_FIELDS:
        if name not in atoms:
            fail(f"{case_id} missing atom {name}")
        check_atom(case_id, name, atoms[name])
        used = []
        blob = atoms[name]
        entries = blob if isinstance(blob, list) else [blob]
        for item in entries:
            used.extend(item.get("span_ids") or [])
        unknown = set(used) - span_ids
        if unknown:
            fail(f"{case_id} atom {name} references missing spans {sorted(unknown)}")
    applicability = row.get("applicability")
    if not isinstance(applicability, dict):
        fail(f"{case_id} missing applicability")
    if applicability.get("label") != "unknown":
        fail(f"{case_id} applicability is {applicability.get('label')!r}; unknown is required without expert review")
    if applicability.get("forced_permission_or_denial") is not False:
        fail(f"{case_id} silently forced permission or denial")
    if applicability.get("expert_certified") is not False:
        fail(f"{case_id} claims expert-certified applicability")
    assumptions = applicability.get("assumptions")
    if not isinstance(assumptions, list) or not assumptions or not all(isinstance(item, str) and item.strip() for item in assumptions):
        fail(f"{case_id} missing applicability assumptions")
    if row.get("mutation_class") in AMBIGUOUS_MUTATIONS and applicability["label"] != "unknown":
        fail(f"{case_id} ambiguous/unsupported mutation forced a non-unknown label")
    provenance = row.get("provenance")
    if not isinstance(provenance, dict):
        fail(f"{case_id} missing provenance")
    preparer = provenance.get("packet_preparer")
    review = provenance.get("independent_human_legal_review")
    if not isinstance(preparer, dict) or not preparer.get("annotator_id"):
        fail(f"{case_id} missing annotator provenance")
    if preparer.get("is_expert_legal_review") is not False:
        fail(f"{case_id} packet preparer is represented as expert review")
    if not isinstance(review, dict):
        fail(f"{case_id} missing review provenance")
    if review.get("status") != "not_obtained":
        fail(f"{case_id} independent review status must be not_obtained")
    if review.get("reviewer_id") not in {None, ""}:
        fail(f"{case_id} invented independent reviewer identity")
    if review.get("is_expert_legal_review") is not False:
        fail(f"{case_id} missing review is marked as expert review")
    if review.get("generated_labels_are_not_expert_review") is not True:
        fail(f"{case_id} does not record that generated labels are not expert review")
    adjudication = row.get("adjudication")
    if not isinstance(adjudication, dict):
        fail(f"{case_id} missing adjudication")
    if adjudication.get("status") != "unresolved_missing_expert_review":
        fail(f"{case_id} adjudication is not visibly unresolved")
    if adjudication.get("agreement") != "not_applicable_no_independent_reviewer":
        fail(f"{case_id} agreement is not documented as inapplicable")
    if adjudication.get("disagreement_records") != []:
        fail(f"{case_id} disagreement records must be an explicit empty list while no reviewer exists")
    if adjudication.get("final_adjudication") is not None:
        fail(f"{case_id} final adjudication claimed without expert review")
    if adjudication.get("claims_narrowed") is not True or adjudication.get("visible_unresolved") is not True:
        fail(f"{case_id} missing-expert-review narrowing is not recorded")
    if adjudication.get("evaluation_admission") != "blocked_until_independent_human_legal_review":
        fail(f"{case_id} evaluation admission is not blocked")
    if row.get("gold_use") != "atom_and_span_fidelity_only_until_expert_review":
        fail(f"{case_id} gold_use overclaims expert labels")
    limitations = row.get("claim_limitations")
    if not isinstance(limitations, list) or not limitations:
        fail(f"{case_id} missing claim limitations")
    if held_out:
        if not spans or not assumptions or review.get("status") != "not_obtained":
            fail(f"held-out {case_id} missing spans, assumptions, or review provenance")


def main() -> int:
    if not JSONL.is_file() or not GUIDELINES.is_file() or not REPORT.is_file():
        fail("annotation deliverables are missing")
    sources = load_json(SOURCES)
    splits = load_json(SPLITS)
    artifacts = {row["artifact_id"]: row for row in sources["source_artifacts"]}
    planned: dict[str, dict] = {}
    for assignment in splits["assignments"]:
        if assignment["population"] != "legal":
            continue
        source = next(row for row in sources["source_records"] if row["source_id"] == assignment["source_id"])
        for case_id in assignment["planned_case_ids"]:
            planned[case_id] = {
                "source_id": assignment["source_id"],
                "lineage_family_id": assignment["lineage_family_id"],
                "split": assignment["split"],
                "artifact_id": source["artifact_id"],
            }
    if len(planned) != 12:
        fail(f"expected 12 reserved legal cases, found {len(planned)}")
    rows = load_jsonl(JSONL)
    if len(rows) != 12:
        fail(f"expected 12 annotation records, found {len(rows)}")
    seen = []
    mutations = set()
    held_out = 0
    for row in rows:
        case_id = row.get("case_id")
        if case_id in seen:
            fail(f"duplicate case_id {case_id}")
        seen.append(case_id)
        check_record(row, planned, artifacts)
        mutations.add(row.get("mutation_class"))
        if row.get("held_out"):
            held_out += 1
    missing_ids = sorted(set(planned) - set(seen))
    if missing_ids:
        fail(f"missing reserved case ids: {missing_ids}")
    if not REQUIRED_MUTATIONS <= mutations:
        fail(f"missing required mutation classes: {sorted(REQUIRED_MUTATIONS - mutations)}")
    if held_out != 8:
        fail(f"expected 8 held-out records, found {held_out}")
    require_text(
        GUIDELINES,
        [
            "unknown",
            "not expert review",
            "Independent human legal expert review was **not obtained**",
            "source spans",
            "Applicability assumptions",
            "omitted_legal_exception",
            "wrong_date_or_jurisdiction",
            "unsupported_construct",
            "no_applicable_record",
            "Never silently recode unknown as permission or denial",
            "evaluation admission remains blocked",
        ],
    )
    require_text(
        REPORT,
        [
            "Review status: unresolved",
            "Independent human legal expert review was not",
            "not expert review",
            "unknown",
            "Agreement, disagreement, and adjudication",
            "Observed agreements",
            "Observed disagreements",
            "unresolved_missing_expert_review",
            "blocked_until_independent_human_legal_review",
            "Independent expert reviews | 0",
            "Explicit unknown labels | 12",
            "Claims are narrowed",
        ],
    )
    report = REPORT.read_text(encoding="utf-8")
    if re.search(r"expert review (was|is) (completed|obtained|performed)", report, re.I):
        fail("review report claims expert review was obtained")
    if "Cohen" in report or "kappa" in report.lower() and "no Cohen" not in report:
        # Permit an explicit statement that kappa was not computed.
        if "no Cohen's kappa" not in report:
            fail("review report must not invent an agreement statistic")
    payload = {
        "status": "passed",
        "records": len(rows),
        "held_out": held_out,
        "mutations": sorted(mutations),
        "independent_human_legal_review": "not_obtained",
        "applicability_labels": "unknown",
        "adjudication": "unresolved_missing_expert_review",
        "evaluation_admission": "blocked",
        "limitation": "Structural packet checks passed; this is not independent scientific or legal expert review.",
    }
    json.dump(payload, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
