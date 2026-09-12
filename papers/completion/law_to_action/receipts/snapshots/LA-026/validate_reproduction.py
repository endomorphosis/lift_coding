#!/usr/bin/python3.12
"""Validate LA-026 source-bound CVE reproductions and reviewer packets.

Structural provenance validation only. This checker does not perform
independent human security review and does not execute untrusted source.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

def repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if (parent / "papers/completion/law_to_action/benchmark/cases/cve_pairs.jsonl").is_file():
            return parent
    raise SystemExit("LA-026 validation failed: cannot locate repository root")


ROOT = repo_root()
PAPER = ROOT / "papers/completion/law_to_action"
PAIRS = PAPER / "benchmark/cases/cve_pairs.jsonl"
CONTROLS = PAPER / "benchmark/cases/cve_controls.jsonl"
REVIEW = PAPER / "benchmark/annotations/cve_review.md"
MANIFEST = PAPER / "benchmark/annotations/review_packet_manifest.json"
REPRO = PAPER / "benchmark/cve_reproduction"
INDEX = REPRO / "index.json"
FAILURES = REPRO / "failures.jsonl"
SOURCES = PAPER / "benchmark/manifests/sources.json"
SPLITS = PAPER / "benchmark/manifests/splits.json"
PAIR_SCHEMA = "law-to-action-cve-pair/v1"
CONTROL_SCHEMA = "law-to-action-cve-control/v1"
MANIFEST_SCHEMA = "law-to-action-review-packet-manifest/v1"
RECOVERY_SCHEMA = "law-to-action-cve-upstream-recovery/v1"
FORBIDDEN_FIXTURE_CVES = {"CVE-2026-0042"}
REQUIRED_CONTROLS = {
    "misleading_cve_similarity",
    "fixed_negative_control",
    "broadened_effects",
    "unknown_scope",
    "wildcard_scope",
    "self_granted_authority",
    "unsupported_transfer",
}
SYNTHETIC_CONTROL_CLASSES = {
    "broadened_effects",
    "unknown_scope",
    "wildcard_scope",
    "self_granted_authority",
    "unsupported_transfer",
}
BLANK_FIELDS = (
    "polarity",
    "expected_polarity",
    "adjudication",
    "agreement",
    "disagreement",
    "reviewer_id",
    "reviewed_at",
    "reviewer_notes",
    "final_adjudication",
)


def fail(message: str) -> None:
    raise SystemExit("LA-026 validation failed: " + message)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_json(path: Path):
    if not path.is_file():
        fail(f"missing {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        fail(f"missing {path}")
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


def check_quote(span: dict, label: str) -> None:
    quote = span.get("quoted_text")
    if not isinstance(quote, str) or not quote.strip():
        fail(f"{label} empty quote")
    if span.get("quoted_sha256") != sha256_text(quote):
        fail(f"{label} quoted_sha256 mismatch")


def planned_cve() -> dict[str, dict]:
    sources = load_json(SOURCES)
    splits = load_json(SPLITS)
    artifact = next(row for row in sources["source_artifacts"] if row["artifact_id"] == "cve-first-shard")
    planned = {}
    for assignment in splits["assignments"]:
        if assignment["population"] != "cve":
            continue
        source = next(row for row in sources["source_records"] if row["source_id"] == assignment["source_id"])
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
            "artifact": artifact,
        }
    if len(planned) != 12:
        fail(f"expected 12 reserved CVE families, found {len(planned)}")
    return planned


def check_polarity(label: dict, case_id: str) -> None:
    if not isinstance(label, dict):
        fail(f"{case_id} missing polarity")
    if label.get("expected") != "unknown":
        fail(f"{case_id} independently reviewed polarity is {label.get('expected')!r}")
    if label.get("independently_reviewed") is not False:
        fail(f"{case_id} claims independently reviewed polarity")
    if label.get("expert_certified") is not False:
        fail(f"{case_id} claims expert-certified polarity")


def check_pair(row: dict, planned: dict, recovery: dict) -> None:
    if row.get("schema") != PAIR_SCHEMA:
        fail(f"{row.get('pair_id')} has wrong schema")
    source = row.get("source")
    if not isinstance(source, dict):
        fail("pair missing source")
    source_id = source.get("source_id")
    assignment = planned[source_id]
    artifact = assignment["artifact"]
    if row.get("split") != assignment["split"]:
        fail(f"{source_id} split mismatch")
    if row.get("lineage_family_id") != assignment["lineage_family_id"]:
        fail(f"{source_id} family mismatch")
    if row.get("empirical_sample") is not True or row.get("enters_empirical_sample_count") is not True:
        fail(f"{source_id} empirical pair is not counted as empirical")
    if row.get("fixture") is not False or row.get("fixture_cve") is not False:
        fail(f"{source_id} empirical pair marked fixture")
    if row.get("mocked_source_record") is not False:
        fail(f"{source_id} empirical pair marked mocked")
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
    if not source.get("fix_commit") or len(source["fix_commit"]) != 40:
        fail(f"{source_id} missing exact fix commit")
    upstream = row.get("upstream")
    if not isinstance(upstream, dict):
        fail(f"{source_id} missing upstream recovery")
    if upstream.get("fix_commit") != source["fix_commit"]:
        fail(f"{source_id} upstream fix commit drifted")
    if not upstream.get("commit_sha"):
        fail(f"{source_id} missing recovered commit SHA")
    if not upstream.get("vulnerable_revision"):
        fail(f"{source_id} missing recovered parent/vulnerable revision")
    if len(upstream["commit_sha"]) != 40 or len(upstream["vulnerable_revision"]) != 40:
        fail(f"{source_id} recovered revision hashes are not full SHAs")
    if not upstream.get("files"):
        fail(f"{source_id} missing recovered file hashes")
    for item in upstream["files"]:
        if not item.get("path"):
            fail(f"{source_id} recovered file missing path")
        if not item.get("git_blob_sha") and not item.get("fixed_sha256") and not item.get("vulnerable_sha256"):
            fail(f"{source_id} {item.get('path')} missing exact source hash")
    evidence = row.get("supported_behavior_evidence")
    if not isinstance(evidence, dict):
        fail(f"{source_id} missing supported behavior evidence")
    isolated = evidence.get("isolated_reproduction")
    behavior = evidence.get("source_supported_behavior")
    if not isinstance(isolated, dict) and not isinstance(behavior, dict):
        fail(f"{source_id} missing isolated reproduction and source-supported behavior")
    if evidence.get("runnable_sandbox_reproduction") != "not_run_untrusted_source_not_executed":
        fail(f"{source_id} claims a sandbox reproduction that was not run")
    if isolated and isolated.get("executed_untrusted_source") is not False:
        fail(f"{source_id} claims untrusted source execution")
    if isolated and isolated.get("native_sink_observed") is not False:
        fail(f"{source_id} claims a native sink observation")
    if not isinstance(evidence.get("recovery_failures"), list):
        fail(f"{source_id} missing recovery failure records")
    if recovery.get("failures") != evidence.get("recovery_failures"):
        fail(f"{source_id} pair failure records drifted from reproduction record")
    sides = row.get("sides")
    if set(sides) != {"vulnerable", "fixed"}:
        fail(f"{source_id} missing sides")
    vulnerable_id, fixed_id = assignment["planned_case_ids"]
    if sides["vulnerable"].get("case_id") != vulnerable_id:
        fail(f"{source_id} case-0 identity mismatch")
    if sides["fixed"].get("case_id") != fixed_id:
        fail(f"{source_id} case-1 identity mismatch")
    check_polarity(sides["vulnerable"]["polarity"], vulnerable_id)
    check_polarity(sides["fixed"]["polarity"], fixed_id)
    for role in ("vulnerable", "fixed"):
        if sides[role].get("executed") is not False:
            fail(f"{source_id} {role} claims execution")
        for span in sides[role].get("source_spans") or []:
            check_quote(span, f"{source_id} {role}")
    lineage = row.get("mutation_lineage")
    if not isinstance(lineage, dict):
        fail(f"{source_id} missing mutation lineage")
    for key in (
        "lineage_family_id",
        "source_id",
        "pair_id",
        "cve_id",
        "fix_commit",
        "vulnerable_revision",
        "fixed_revision",
        "source_record_sha256",
    ):
        if not lineage.get(key):
            fail(f"{source_id} mutation lineage missing {key}")
    if lineage.get("synthetic") is not False or lineage.get("empirical_sample") is not True:
        fail(f"{source_id} mutation lineage empirical/synthetic flags are wrong")
    review = row["provenance"]["independent_human_security_review"]
    if review.get("status") != "not_obtained":
        fail(f"{source_id} independent review is not pending")
    if review.get("pending_in") != ["LA-027", "LA-006"]:
        fail(f"{source_id} independent review pending-in tasks are wrong")
    if review.get("reviewer_id") not in {None, ""}:
        fail(f"{source_id} invented reviewer identity")
    if row["adjudication"].get("final_adjudication") is not None:
        fail(f"{source_id} final adjudication claimed without expert review")
    if row.get("restriction_candidate", {}).get("authoritative") is not False:
        fail(f"{source_id} restriction claims authority")
    if row.get("restriction_candidate", {}).get("grants_execution_authority") is not False:
        fail(f"{source_id} restriction grants execution authority")
    mapping = row.get("intent_code_effect_mapping")
    if mapping.get("code_effect", {}).get("status") != "unsupported_transfer":
        fail(f"{source_id} unsupported transfer was not recorded")


def check_recovery(recovery: dict, pair: dict) -> None:
    if recovery.get("schema") != RECOVERY_SCHEMA:
        fail(f"{recovery.get('cve_id')} recovery has wrong schema")
    if recovery.get("cve_id") != pair["source"]["cve_id"]:
        fail(f"{pair['pair_id']} recovery CVE mismatch")
    if recovery.get("untrusted_source_executed") is not False:
        fail(f"{recovery.get('cve_id')} claims execution")
    if recovery.get("independent_review_inferred") is not False:
        fail(f"{recovery.get('cve_id')} inferred independent review")
    iso = recovery.get("isolated_reproduction")
    behavior = recovery.get("source_supported_behavior")
    if not isinstance(iso, dict) or not isinstance(behavior, dict):
        fail(f"{recovery.get('cve_id')} missing reproduction or behavior evidence")
    if not recovery.get("commit_sha") or not recovery.get("vulnerable_revision"):
        fail(f"{recovery.get('cve_id')} missing exact source/revision hashes")
    if iso.get("files_listed", 0) < 1:
        fail(f"{recovery.get('cve_id')} listed no recovered files")
    if iso.get("vulnerable_files_recovered", 0) < 1 and iso.get("fixed_files_recovered", 0) < 1:
        fail(f"{recovery.get('cve_id')} recovered neither side and has no isolated source observation")
    if not isinstance(recovery.get("failures"), list):
        fail(f"{recovery.get('cve_id')} missing failure list")
    for item in recovery["files"]:
        if item.get("fixed", {}).get("executed") is not False:
            fail(f"{recovery.get('cve_id')} executed a recovered file")
        quote = (item.get("fixed") or {}).get("quote") or (item.get("vulnerable") or {}).get("quote")
        if quote:
            check_quote(quote, f"{recovery.get('cve_id')} recovered quote")
        for span in item.get("patch_quotes") or []:
            check_quote(span, f"{recovery.get('cve_id')} patch quote")


def check_control(row: dict, planned: dict) -> None:
    if row.get("schema") != CONTROL_SCHEMA:
        fail(f"{row.get('control_id')} has wrong schema")
    parent = row.get("parent_source_id")
    if parent not in planned:
        fail(f"{row.get('control_id')} parent is not a frozen CVE family")
    if row.get("lineage_family_id") != planned[parent]["lineage_family_id"]:
        fail(f"{row.get('control_id')} left its parent family")
    if row.get("empirical_sample") is not False or row.get("enters_empirical_sample_count") is not False:
        fail(f"{row.get('control_id')} entered empirical sample counts")
    control_class = row.get("control_class")
    if control_class not in REQUIRED_CONTROLS:
        fail(f"{row.get('control_id')} unknown control class")
    synthetic = control_class in SYNTHETIC_CONTROL_CLASSES
    if row.get("synthetic") is not synthetic:
        fail(f"{row.get('control_id')} synthetic flag incorrect")
    lineage = row.get("mutation_lineage")
    if not isinstance(lineage, dict):
        fail(f"{row.get('control_id')} missing mutation lineage")
    for key in (
        "lineage_family_id",
        "source_id",
        "parent_pair_id",
        "control_id",
        "control_class",
        "cve_id",
        "fix_commit",
        "source_record_sha256",
    ):
        if not lineage.get(key):
            fail(f"{row.get('control_id')} mutation lineage missing {key}")
    if lineage.get("empirical_sample") is not False:
        fail(f"{row.get('control_id')} lineage entered empirical counts")
    if lineage.get("synthetic") is not synthetic:
        fail(f"{row.get('control_id')} lineage synthetic flag incorrect")
    if row.get("expected_polarity") != "unknown":
        fail(f"{row.get('control_id')} forced a reviewed polarity")
    if row["provenance"]["independent_human_security_review"].get("pending_in") != ["LA-027", "LA-006"]:
        fail(f"{row.get('control_id')} independent review pending-in tasks are wrong")
    if row["adjudication"].get("final_adjudication") is not None:
        fail(f"{row.get('control_id')} claimed adjudication")


def check_manifest(manifest: dict, pairs: list[dict], controls: list[dict]) -> None:
    if manifest.get("schema") != MANIFEST_SCHEMA:
        fail("review packet manifest has wrong schema")
    review = manifest.get("independent_review")
    if not isinstance(review, dict):
        fail("manifest missing independent_review")
    if review.get("status") != "pending":
        fail("manifest independent review is not pending")
    if review.get("pending_in") != ["LA-027", "LA-006"]:
        fail("manifest must leave independent review pending in LA-027 and LA-006")
    if review.get("reviewer_id") is not None or review.get("reviewed_at") is not None:
        fail("manifest invented a reviewer")
    if review.get("is_independent_security_review") is not False:
        fail("manifest claims independent review")
    packets = manifest.get("packets")
    if not isinstance(packets, list):
        fail("manifest missing packets")
    expected_ids = []
    for pair in pairs:
        expected_ids.extend(
            [pair["sides"]["vulnerable"]["case_id"], pair["sides"]["fixed"]["case_id"]]
        )
    expected_ids.extend(row["control_id"] for row in controls)
    got_ids = [row.get("packet_id") for row in packets]
    if sorted(got_ids) != sorted(expected_ids):
        fail("manifest packets do not cover every reserved case and excluded control")
    if len(packets) != 24 + 84:
        fail(f"manifest expected 108 packets, found {len(packets)}")
    empirical = [row for row in packets if row.get("empirical_sample")]
    excluded = [row for row in packets if not row.get("empirical_sample")]
    if len(empirical) != 24 or len(excluded) != 84:
        fail("manifest empirical/excluded packet counts drifted")
    for packet in packets:
        for field in BLANK_FIELDS:
            if packet.get(field) is not None:
                fail(f"{packet.get('packet_id')} reviewer field {field} is not blank")
        if not isinstance(packet.get("source_evidence"), dict) or not packet["source_evidence"]:
            fail(f"{packet.get('packet_id')} missing source evidence")
        if not isinstance(packet.get("scope_assumptions"), dict) or not packet["scope_assumptions"]:
            fail(f"{packet.get('packet_id')} missing scope assumptions")
        if packet.get("empirical_sample") and packet.get("enters_empirical_sample_count") is not True:
            fail(f"{packet.get('packet_id')} empirical packet is not counted")
        if not packet.get("empirical_sample") and packet.get("enters_empirical_sample_count") is not False:
            fail(f"{packet.get('packet_id')} excluded packet entered empirical counts")
        if packet.get("synthetic") and packet.get("empirical_sample"):
            fail(f"{packet.get('packet_id')} synthetic control entered empirical sample counts")
    cohort = manifest.get("cohort")
    if cohort.get("empirical_pairs") != 12 or cohort.get("empirical_cases") != 24:
        fail("manifest cohort empirical counts drifted")
    if cohort.get("excluded_controls") != 84:
        fail("manifest cohort control count drifted")
    if cohort.get("synthetic_controls_in_empirical_sample_counts") != 0:
        fail("manifest admits synthetic controls into empirical counts")


def main() -> int:
    planned = planned_cve()
    pairs = load_jsonl(PAIRS)
    controls = load_jsonl(CONTROLS)
    if len(pairs) != 12:
        fail(f"expected 12 pair records, found {len(pairs)}")
    if len(controls) != 84:
        fail(f"expected 84 controls, found {len(controls)}")
    index = load_json(INDEX)
    if index.get("pairs") != 12 or index.get("cases") != 24 or index.get("controls") != 84:
        fail("reproduction index cohort drifted")
    if index.get("untrusted_source_executed") is not False:
        fail("index claims untrusted execution")
    if index.get("independent_review", {}).get("pending_in") != ["LA-027", "LA-006"]:
        fail("index independent review is not pending in LA-027 and LA-006")
    recoveries = {}
    seen_pairs = []
    seen_cases = []
    empirical_cves = []
    for pair in pairs:
        pair_id = pair.get("pair_id")
        if pair_id in seen_pairs:
            fail(f"duplicate pair_id {pair_id}")
        seen_pairs.append(pair_id)
        cve_id = pair["source"]["cve_id"]
        recovery_path = REPRO / "pairs" / f"{cve_id}.json"
        recovery = load_json(recovery_path)
        recoveries[pair_id] = recovery
        check_recovery(recovery, pair)
        check_pair(pair, planned, recovery)
        empirical_cves.append(cve_id)
        seen_cases.extend(
            [pair["sides"]["vulnerable"]["case_id"], pair["sides"]["fixed"]["case_id"]]
        )
    expected_cases = [case_id for item in planned.values() for case_id in item["planned_case_ids"]]
    if sorted(seen_cases) != sorted(expected_cases):
        fail("reserved CVE case identities are incomplete")
    if len(set(empirical_cves)) != 12:
        fail("empirical CVE identifiers are not 12 distinct real records")
    if any(item in FORBIDDEN_FIXTURE_CVES for item in empirical_cves):
        fail("fabricated fixture CVE entered empirical sample counts")
    classes_by_family: dict[str, set[str]] = {}
    synthetic_empirical = 0
    for row in controls:
        check_control(row, planned)
        classes_by_family.setdefault(row["parent_source_id"], set()).add(row["control_class"])
        if row.get("synthetic") and (
            row.get("empirical_sample") or row.get("enters_empirical_sample_count")
        ):
            synthetic_empirical += 1
    if synthetic_empirical:
        fail("synthetic control entered empirical sample counts")
    for source_id, classes in classes_by_family.items():
        if classes != REQUIRED_CONTROLS:
            fail(f"{source_id} missing control classes {sorted(REQUIRED_CONTROLS - classes)}")
    failures = load_jsonl(FAILURES)
    recorded_failed_attempts = 0
    for recovery in recoveries.values():
        recorded_failed_attempts += len(recovery.get("failures") or [])
    if recorded_failed_attempts and not failures:
        fail("recovery failures exist but failures.jsonl is empty")
    for row in failures:
        if row.get("ok") is True:
            fail("failures.jsonl contains a successful attempt")
        if not row.get("cve_id") or not (row.get("error") or row.get("status") or row.get("attempt")):
            fail("failure record is missing identity or error")
    manifest = load_json(MANIFEST)
    check_manifest(manifest, pairs, controls)
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
            "pending in LA-027 and LA-006",
            "blank",
            "Isolated",
        ],
    )
    report = REVIEW.read_text(encoding="utf-8")
    if re.search(r"expert review (was|is) (completed|obtained|performed)", report, re.I):
        fail("review report claims expert review was obtained")
    pair_text = PAIRS.read_text(encoding="utf-8")
    if "CVE-2026-0042" in pair_text:
        fail("fixture CVE identifier present in empirical pairs")
    payload = {
        "status": "passed",
        "pairs": len(pairs),
        "empirical_cases": 24,
        "controls": len(controls),
        "synthetic_controls": sum(1 for row in controls if row.get("synthetic")),
        "synthetic_controls_in_empirical_sample_counts": 0,
        "fixture_cves_in_empirical_counts": 0,
        "mocked_source_records_in_empirical_counts": 0,
        "recovery_failure_records": len(failures),
        "independent_human_security_review": "pending_LA-027_and_LA-006",
        "reviewer_polarity_fields": "blank",
        "reviewer_adjudication_fields": "blank",
        "expected_polarity_packet_state": "unknown",
        "adjudication": "unresolved_missing_expert_review",
        "evaluation_admission": "blocked",
        "untrusted_source_executed": False,
        "limitation": "Structural packet checks passed; this is not independent scientific or security expert review.",
    }
    json.dump(payload, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
