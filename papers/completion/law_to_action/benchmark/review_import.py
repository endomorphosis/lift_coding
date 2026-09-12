#!/usr/bin/python3.12
"""Fail-closed independent-review importer for LA-028/LA-027.

A returned human review cannot complete unless independent labels, reviewer
identities, timestamps, and the full selected population are present.
Agent-generated provenance is refused. Missing reviews do not yield a scored
fidelity claim. Analysis of incomplete imports is refused.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

HERE = Path(__file__).resolve()


def find_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "papers" / "completion" / "law_to_action").is_dir():
            return candidate
    raise RuntimeError("repository root not found")


ROOT = find_root(HERE)
LIVE = ROOT / "papers" / "completion" / "law_to_action"
BENCHMARK = LIVE / "benchmark"
SCHEMA = "law-to-action-review-import/v1"
IMPORTER_VERSION = "la-028-review-import/v1"
REQUIRED_REVIEW_FIELDS = (
    "reviewer_id",
    "reviewed_at",
    "adjudication",
    "agreement",
    "disagreement",
    "final_adjudication",
)
AGENT_MARKERS = (
    "la005-packet-preparer-implementation-worker",
    "autonomous_annotation_packet_preparer",
    "implementation-daemon",
    "implementation_worker",
    "agent-supervisor",
    "generated_by_supervisor",
    "model-generated-human-review",
)
INDEPENDENT_LABEL_FIELDS = (
    "label",
    "expected_polarity",
    "polarity",
    "applicability_label",
)


class ReviewImportError(RuntimeError):
    """Returned review cannot be admitted."""


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode(
        "utf-8"
    )


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-" + uuid4().hex)
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def selected_population() -> dict[str, Any]:
    splits = load_json(BENCHMARK / "manifests" / "splits.json")
    families = []
    case_ids: list[str] = []
    for row in splits["assignments"]:
        families.append(
            {
                "population": row["population"],
                "lineage_family_id": row["lineage_family_id"],
                "source_id": row["source_id"],
                "split": row["split"],
                "planned_case_ids": row["planned_case_ids"],
            }
        )
        case_ids.extend(row["planned_case_ids"])
    if len(families) != 30 or len(case_ids) != 60:
        raise ReviewImportError("frozen population is incomplete in splits.json")
    return {
        "families": families,
        "case_ids": case_ids,
        "family_count": len(families),
        "case_count": len(case_ids),
        "splits_sha256": sha256_file(BENCHMARK / "manifests" / "splits.json"),
        "sources_sha256": sha256_file(BENCHMARK / "manifests" / "sources.json"),
    }


def contains_agent_marker(value: Any) -> bool:
    text = json.dumps(value, ensure_ascii=False).lower() if not isinstance(value, str) else value.lower()
    return any(marker.lower() in text for marker in AGENT_MARKERS)


def label_present(record: Mapping[str, Any]) -> bool:
    applicability = record.get("applicability")
    if isinstance(applicability, Mapping):
        label = applicability.get("label")
        if isinstance(label, str) and label.strip() and label != "unknown" and applicability.get("expert_certified") is True:
            return True
        if applicability.get("expert_certified") is True and label in {"allow", "deny", "unknown"}:
            return True
    for field in INDEPENDENT_LABEL_FIELDS:
        value = record.get(field)
        if isinstance(value, str) and value.strip() and value not in {"null", "none"}:
            if field in {"polarity", "expected_polarity"} and record.get("reviewer_id"):
                return True
    independent = record.get("independent_review")
    if isinstance(independent, Mapping):
        if independent.get("is_independent_security_review") is True and independent.get("reviewer_id"):
            return True
    return False


def reviewer_complete(record: Mapping[str, Any]) -> bool:
    reviewer = record.get("reviewer_id") or (record.get("independent_review") or {}).get("reviewer_id") if isinstance(record.get("independent_review"), Mapping) else record.get("reviewer_id")
    reviewed_at = record.get("reviewed_at")
    if isinstance(record.get("provenance"), Mapping):
        human = record["provenance"].get("independent_human_legal_review") or record["provenance"].get(
            "independent_human_intent_review"
        )
        if isinstance(human, Mapping):
            reviewer = reviewer or human.get("reviewer_id")
            reviewed_at = reviewed_at or human.get("reviewed_at")
            if human.get("status") in {"not_obtained", "pending", None}:
                return False
            if human.get("is_expert_legal_review") is False and human.get("generated_labels_are_not_expert_review") is True:
                return False
    if not isinstance(reviewer, str) or not reviewer.strip():
        return False
    if not isinstance(reviewed_at, str) or not reviewed_at.strip():
        return False
    return True


def packet_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, Mapping)]
    if not isinstance(payload, Mapping):
        raise ReviewImportError("review return must be a JSON object or array")
    for key in ("packets", "records", "reviews", "cases"):
        value = payload.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, Mapping)]
    if payload.get("case_id") or payload.get("packet_id"):
        return [dict(payload)]
    raise ReviewImportError("review return has no packets/records/reviews array")


def reasons_for(record: Mapping[str, Any], *, required_ids: set[str]) -> list[str]:
    reasons: list[str] = []
    identity = record.get("case_id") or record.get("packet_id")
    if identity not in required_ids:
        reasons.append("record_not_in_selected_population")
    if contains_agent_marker(record):
        reasons.append("agent_generated_human_provenance")
    if not reviewer_complete(record):
        reasons.append("missing_independent_reviewer_or_timestamp")
    if not label_present(record):
        reasons.append("missing_independent_label")
    for field in REQUIRED_REVIEW_FIELDS:
        if record.get(field) in (None, "", [], {}):
            if field in {"adjudication", "agreement", "disagreement", "final_adjudication"}:
                reasons.append(f"blank_{field}")
    provenance = record.get("provenance")
    if isinstance(provenance, Mapping):
        preparer = provenance.get("packet_preparer")
        if isinstance(preparer, Mapping) and preparer.get("is_expert_legal_review") is True:
            reasons.append("packet_preparer_claimed_as_expert_review")
        if contains_agent_marker(provenance):
            reasons.append("agent_generated_human_provenance")
    return sorted(set(reasons))


def refuse(*, code: str, message: str, details: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload = {
        "schema": SCHEMA,
        "importer_version": IMPORTER_VERSION,
        "task": "LA-028",
        "status": "refused",
        "admitted": False,
        "complete_review": False,
        "scored_fidelity_claim": False,
        "empirical_benchmark_result": False,
        "code": code,
        "message": message,
        "refused_at": utc_now(),
        "details": dict(details or {}),
    }
    return payload


def import_review(path: Path | None) -> dict[str, Any]:
    population = selected_population()
    required_ids = set(population["case_ids"])
    if path is None or not path.is_file():
        return refuse(
            code="missing_independent_review_return",
            message="No independent human review return is present. Missing reviewers or labels cannot yield a complete review or scored fidelity claim.",
            details={
                "return_path": None if path is None else str(path),
                "required_case_count": population["case_count"],
                "pending_in": ["LA-027"],
            },
        )
    try:
        payload = load_json(path)
    except Exception as exc:
        return refuse(
            code="unreadable_review_return",
            message=f"Review return could not be parsed: {type(exc).__name__}: {exc}",
            details={"return_path": str(path)},
        )
    if contains_agent_marker(payload):
        return refuse(
            code="agent_generated_human_provenance",
            message="Review return contains agent/supervisor provenance markers and cannot be imported as independent human review.",
            details={"return_path": str(path), "return_sha256": sha256_file(path)},
        )
    records = packet_records(payload)
    present_ids = []
    record_reasons: list[dict[str, Any]] = []
    for record in records:
        identity = record.get("case_id") or record.get("packet_id")
        if isinstance(identity, str):
            present_ids.append(identity)
        record_reasons.append({"id": identity, "reasons": reasons_for(record, required_ids=required_ids)})
    missing_ids = sorted(required_ids - set(present_ids))
    incomplete = bool(missing_ids) or len(set(present_ids)) != population["case_count"]
    blocked = [row for row in record_reasons if row["reasons"]]
    if incomplete:
        return refuse(
            code="incomplete_population",
            message="Review return does not cover every frozen selected case. Incomplete populations cannot be admitted.",
            details={
                "return_path": str(path),
                "return_sha256": sha256_file(path),
                "required_case_count": population["case_count"],
                "returned_case_count": len(set(present_ids)),
                "missing_case_count": len(missing_ids),
                "missing_case_ids_head": missing_ids[:12],
            },
        )
    if blocked:
        return refuse(
            code="missing_independent_labels_or_reviewers",
            message="Review return is missing independent labels, reviewer identity, timestamps, or adjudication. It is not a complete review.",
            details={
                "return_path": str(path),
                "return_sha256": sha256_file(path),
                "blocked_record_count": len(blocked),
                "blocked_head": blocked[:12],
            },
        )
    return {
        "schema": SCHEMA,
        "importer_version": IMPORTER_VERSION,
        "status": "admitted_pending_downstream",
        "admitted": True,
        "complete_review": True,
        "scored_fidelity_claim": False,
        "empirical_benchmark_result": False,
        "message": "Independent review fields are complete. Scoring remains a later task and is not authorized here.",
        "return_path": str(path),
        "return_sha256": sha256_file(path),
        "case_count": len(set(present_ids)),
    }


def analyze_import(result: Mapping[str, Any]) -> dict[str, Any]:
    if result.get("admitted") is True and result.get("complete_review") is True:
        return {
            "schema": "law-to-action-review-analysis/v1",
            "status": "analysis_blocked_until_later_scoring_task",
            "scored": False,
            "message": "Complete import is retained. LA-028 analysis refuses to score fidelity; LA-009 remains responsible for held-out scoring after LA-027.",
            "import": result,
        }
    return {
        "schema": "law-to-action-review-analysis/v1",
        "status": "refused",
        "scored": False,
        "code": "analysis_refuses_incomplete_or_missing_review",
        "message": "Analysis refuses missing independent labels, agent-generated provenance, and incomplete populations.",
        "import": result,
    }


def current_blank_packets() -> dict[str, Any]:
    manifest_path = BENCHMARK / "annotations" / "review_packet_manifest.json"
    payload = load_json(manifest_path)
    independent = payload.get("independent_review") if isinstance(payload.get("independent_review"), Mapping) else {}
    blank_fields = payload.get("blank_reviewer_fields") or []
    packets = payload.get("packets") if isinstance(payload.get("packets"), list) else []
    nonempty = []
    for packet in packets:
        if not isinstance(packet, Mapping):
            continue
        for field in blank_fields:
            value = packet.get(field)
            if value in (None, "", [], {}):
                continue
            nonempty.append({"packet_id": packet.get("packet_id"), "field": field})
            break
    return {
        "manifest": str(manifest_path.relative_to(ROOT)),
        "manifest_sha256": sha256_file(manifest_path),
        "independent_review_status": independent.get("status"),
        "blank_reviewer_fields": blank_fields,
        "packet_count": len(packets),
        "nonblank_review_fields": nonempty[:12],
        "original_blank_packets_preserved": independent.get("status") == "pending" and not nonempty,
    }


def run(*, returned: Path | None, out: Path, analyze: bool) -> dict[str, Any]:
    imported = import_review(returned)
    analysis = analyze_import(imported) if analyze or imported.get("admitted") is not True else analyze_import(imported)
    blank = current_blank_packets()
    result = {
        "schema": SCHEMA,
        "importer_version": IMPORTER_VERSION,
        "blank_packet_state": blank,
        "import": imported,
        "analysis": analysis,
        "final_admission": {
            "admitted": False,
            "reason": imported.get("code") or "review_complete_but_scoring_not_authorized_in_LA-028",
            "missing_independent_labels": imported.get("admitted") is not True,
            "scored": False,
        },
    }
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "review_import_refusal.json" if imported.get("admitted") is not True else out / "review_import.json", result)
    write_json(out / "review_analysis.json", analysis)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("import", "analyze", "refuse-missing"), default="refuse-missing", nargs="?")
    parser.add_argument("--returned", type=Path, default=None, help="Path to an independent review return JSON")
    parser.add_argument("--out", type=Path, default=LIVE / "results" / "development_qualification")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    analyze = args.command == "analyze"
    result = run(returned=args.returned, out=args.out, analyze=analyze or args.command == "refuse-missing")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
