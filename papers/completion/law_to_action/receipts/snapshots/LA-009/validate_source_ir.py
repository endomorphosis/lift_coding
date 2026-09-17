#!/usr/bin/python3.12
"""Validate LA-009 source-to-IR outputs against the frozen cohort and case files."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

SNAPSHOT = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[6]
LIVE = ROOT / "papers" / "completion" / "law_to_action"
BENCHMARK = LIVE / "benchmark"

EXPECTED_CASES = 60
EXPECTED_FAMILIES = 30
EXPECTED_SPLITS_SHA256 = "f40b60ce73acbbbb7e9da39159b7dc5706f250cb5b85ac407c4b10140cb5c5a6"
EXPECTED_SOURCES_SHA256 = "55c69799805ce8466c7935f41c43a6656fbb2dce867496fb771ae07c4395feb6"
ORIGINAL_PROTOCOL_SHA256 = "ba03394cd66f51999d1b177a29558b6130429eb9fc3faebea5e57c780857940f"
WITHDRAWN = (
    "expert_legal_fidelity",
    "inter_annotator_agreement",
    "independent_human_validation",
    "legal_applicability_or_validity_in_the_world",
    "semantic_accuracy_from_implementation_agreement",
)
STATUSES = {"prediction", "failed", "unavailable", "unsupported"}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def canonical_json(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode(
        "utf-8"
    )


def digest(value) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def rate(numerator: int, denominator: int) -> dict:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "rate": None if denominator == 0 else numerator / denominator,
        "formula": f"{numerator}/{denominator}",
    }


def main() -> int:
    live_raw = LIVE / "results" / "source_ir" / "raw.jsonl"
    live_metrics = LIVE / "results" / "source_ir" / "metrics.json"
    live_review = LIVE / "results" / "source_ir" / "failure_review.md"
    snap_raw = SNAPSHOT / "outputs" / "results" / "source_ir" / "raw.jsonl"
    snap_metrics = SNAPSHOT / "outputs" / "results" / "source_ir" / "metrics.json"
    snap_review = SNAPSHOT / "outputs" / "results" / "source_ir" / "failure_review.md"
    for path in (live_raw, live_metrics, live_review, snap_raw, snap_metrics, snap_review):
        if not path.is_file():
            raise SystemExit(f"missing {path}")
    if live_raw.read_bytes() != snap_raw.read_bytes():
        raise SystemExit("raw.jsonl live/snapshot mismatch")
    if live_metrics.read_bytes() != snap_metrics.read_bytes():
        raise SystemExit("metrics.json live/snapshot mismatch")
    if live_review.read_bytes() != snap_review.read_bytes():
        raise SystemExit("failure_review.md live/snapshot mismatch")

    splits = load_json(BENCHMARK / "manifests" / "splits.json")
    if sha256_file(BENCHMARK / "manifests" / "splits.json") != EXPECTED_SPLITS_SHA256:
        raise SystemExit("splits.json hash changed after outcomes")
    if sha256_file(BENCHMARK / "manifests" / "sources.json") != EXPECTED_SOURCES_SHA256:
        raise SystemExit("sources.json hash changed after outcomes")
    amendment = load_json(BENCHMARK / "automated_evidence_amendment.json")
    if ((amendment.get("original_protocol") or {}).get("sha256")) != ORIGINAL_PROTOCOL_SHA256:
        raise SystemExit("LA-027 amendment no longer binds the original protocol hash")

    planned = [case_id for row in splits["assignments"] for case_id in row["planned_case_ids"]]
    if len(splits["assignments"]) != EXPECTED_FAMILIES or len(planned) != EXPECTED_CASES:
        raise SystemExit("frozen cohort counts drifted")

    rows = load_jsonl(live_raw)
    metrics = load_json(live_metrics)
    review = live_review.read_text(encoding="utf-8")
    got = [row["case_id"] for row in rows]
    if sorted(got) != sorted(planned):
        raise SystemExit("raw.jsonl case identities are not the frozen planned case IDs")
    if len(got) != len(set(got)):
        raise SystemExit("duplicate case identities in raw.jsonl")
    if any(row.get("status") not in STATUSES for row in rows):
        raise SystemExit("a frozen case lacks prediction/failed/unavailable/unsupported status")
    if any(row.get("frozen_selected_case") is not True for row in rows):
        raise SystemExit("a raw row is not marked as a frozen selected case")
    if any(row.get("synthetic_qualification_control") for row in rows):
        raise SystemExit("synthetic qualification controls leaked into the frozen raw file")
    if any(row.get("human_review_run_dependency") for row in rows):
        raise SystemExit("human review was recorded as a run dependency")
    if any(row.get("independent_human_gold") for row in rows):
        raise SystemExit("independent human gold was assigned")
    if any(row.get("unmeasured", {}).get("numeric_score_assigned") for row in rows):
        raise SystemExit("unmeasured expert claims received a numeric score")

    raw_sha256 = hashlib.sha256(b"".join(canonical_json(row) + b"\n" for row in rows)).hexdigest()
    if metrics.get("raw_sha256") != raw_sha256:
        raise SystemExit("metrics.json raw_sha256 is not reproducible from raw.jsonl")
    if metrics["frozen_population"]["original_protocol_sha256"] != ORIGINAL_PROTOCOL_SHA256:
        raise SystemExit("metrics lost the original protocol pin")
    if metrics["frozen_population"]["cohorts_changed_after_outcomes"] is not False:
        raise SystemExit("metrics claim a cohort change")
    if metrics["case_accounting"]["records"] != EXPECTED_CASES or metrics["case_accounting"]["missing"] != 0:
        raise SystemExit("case accounting is incomplete")
    if metrics["human_review_run_dependency"] is not False:
        raise SystemExit("metrics treat human review as a run dependency")

    span_linked = sum(1 for row in rows if (row.get("source_span_linkage") or {}).get("linked"))
    schema_valid = sum(1 for row in rows if (row.get("parse_schema_validity") or {}).get("valid"))
    contract_ok = sum(1 for row in rows if (row.get("machine_contract_outcome") or {}).get("satisfied"))
    recomputed_span = rate(span_linked, EXPECTED_CASES)
    recomputed_schema = rate(schema_valid, EXPECTED_CASES)
    recomputed_contract = rate(contract_ok, EXPECTED_CASES)
    for name, recomputed in (
        ("source_span_linkage_coverage", recomputed_span),
        ("parse_schema_validity", recomputed_schema),
        ("machine_contract_coverage", recomputed_contract),
    ):
        reported = metrics["metrics"][name]
        if reported["numerator"] != recomputed["numerator"] or reported["denominator"] != recomputed["denominator"]:
            raise SystemExit(f"metric {name} is not reproducible from case-level files")
        if reported["formula"] != recomputed["formula"]:
            raise SystemExit(f"metric {name} formula drifted")

    cve_rows = [row for row in rows if row["population"] == "cve"]
    if len(cve_rows) != 24:
        raise SystemExit("CVE denominator drifted")
    cve_unknown = sum(1 for row in cve_rows if (row.get("cve_behavior") or {}).get("polarity_expected") == "unknown")
    if cve_unknown != 24:
        raise SystemExit("CVE polarity was forced instead of remaining unknown")
    if metrics["metrics"]["cve_source_supported_behavior"]["polarity_accuracy_not_scored"] is not True:
        raise SystemExit("CVE polarity accuracy was scored")
    if metrics["metrics"]["cve_source_supported_behavior"]["polarity_supported_by_contract"] != 0:
        raise SystemExit("CVE polarity was treated as contract-supported")

    for name in WITHDRAWN:
        withdrawn = metrics["withdrawn_unmeasured"][name]
        if withdrawn.get("numeric_score_assigned") is not False or withdrawn.get("status") != "unmeasured":
            raise SystemExit(f"withdrawn metric {name} was assigned a numeric score")
        if name.replace("_", " ") in review.lower() and "unmeasured" not in review.lower():
            raise SystemExit("failure review does not keep withdrawn claims unmeasured")

    legal_consistency = metrics["metrics"]["compiler_checker_consistency"]["legal_parser_converter_nonempty_agreement"]
    if legal_consistency.get("implementation_agreement_is_not_semantic_accuracy") is not True:
        raise SystemExit("legal implementation consistency was labeled as semantic accuracy")
    if legal_consistency.get("shared_producer_dependence") is not True:
        raise SystemExit("legal parser/converter shared-producer dependence was not reported")
    skill_consistency = metrics["metrics"]["compiler_checker_consistency"]["skill_normalizer_independent_decoder_agreement"]
    if skill_consistency.get("shared_producer_dependence") is not False:
        raise SystemExit("skill independent decoder was marked as shared-producer")

    excluded = metrics["synthetic_qualification_controls"]["excluded_case_ids"]
    if metrics["synthetic_qualification_controls"]["included_in_frozen_denominator"] is not False:
        raise SystemExit("synthetic controls were included in the frozen denominator")
    if any(case_id in planned for case_id in excluded):
        raise SystemExit("a frozen planned case was classified as an excluded synthetic control")
    if "Implementation agreement is not semantic accuracy" not in review:
        raise SystemExit("failure review omits the implementation-agreement limitation")
    if "unmeasured" not in review.lower():
        raise SystemExit("failure review omits unmeasured expert claims")
    if str(EXPECTED_CASES) not in review:
        raise SystemExit("failure review omits the frozen case denominator")

    producers = {json.dumps((row.get("machine_expectation") or {}).get("producer"), sort_keys=True) for row in rows}
    if len(producers) != 1:
        raise SystemExit("machine expectation producer is not uniform")
    producer = (rows[0].get("machine_expectation") or {}).get("producer") or {}
    if producer.get("id") != "la-027-automated-reference-manifest":
        raise SystemExit("machine expectation producer is not the LA-027 compiler")
    if producer.get("distinct_from_evaluated_adapter") is not True:
        raise SystemExit("machine expectation producer is not distinct from evaluated adapters")

    for row in cve_rows:
        behavior = row.get("cve_behavior") or {}
        independent = behavior.get("independent_producer") or {}
        if independent.get("id") not in {None, "la-006-scoped-behavior-contract-compiler"} and independent.get("distinct_from_evaluated_adapter") is not True:
            raise SystemExit(f"CVE case {row['case_id']} lacks independent behavior provenance")

    print(
        json.dumps(
            {
                "task": "LA-009",
                "valid": True,
                "cases": len(rows),
                "raw_sha256": raw_sha256,
                "metrics_reproduced": True,
                "cohorts_unchanged": True,
                "withdrawn_unmeasured": list(WITHDRAWN),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
