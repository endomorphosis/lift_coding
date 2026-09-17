#!/usr/bin/python3.12
"""Validate LA-006 automated-scope CVE pair evidence.

Structural provenance validation only. This checker does not perform
independent human security review, does not execute untrusted source, and must
not be reported as empirical evaluation or universal security.
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
MACHINE = PAPER / "benchmark/annotations/automated_reference_manifest.json"
REPRO_DIR = PAPER / "benchmark/cve_reproduction/pairs"
LA026_PAIRS = PAPER / "receipts/snapshots/LA-026/outputs/benchmark/cases/cve_pairs.jsonl"
LA026_CONTROLS = PAPER / "receipts/snapshots/LA-026/outputs/benchmark/cases/cve_controls.jsonl"
SNAP = Path(__file__).resolve().parent
CONTRACTS = SNAP / "polarity_contracts.jsonl"
HIST = SNAP / "original_failed_blocked_attempt_20260911"
PAIR_SCHEMA = "law-to-action-cve-pair/v1"
CONTROL_SCHEMA = "law-to-action-cve-control/v1"
PRODUCER_ID = "la-006-scoped-behavior-contract-compiler"
PRODUCER_KIND = "machine_contract_expectation_compiler"
EVALUATED_ADAPTER = "ipfs_datasets_py.logic.security_ir.cvefixes.adapter"
REQUIRED_CONTROLS = {
    "misleading_cve_similarity",
    "fixed_negative_control",
    "broadened_effects",
    "unknown_scope",
    "wildcard_scope",
    "self_granted_authority",
    "unsupported_transfer",
}
REJECTED_CONTROLS = {"wildcard_scope", "self_granted_authority", "broadened_effects"}
UNKNOWN_CONTROLS = {
    "unknown_scope",
    "unsupported_transfer",
    "misleading_cve_similarity",
    "fixed_negative_control",
}
FORBIDDEN_FIXTURE_CVES = {"CVE-2026-0042"}
ORIGINAL_CRITERIA = [
    "Each pair has runnable sandbox reproduction or precisely defined supported behavior evidence and independently reviewed expected polarity.",
    "No fabricated fixture CVE or mocked source record enters empirical sample counts.",
    "Wildcards, self-granted authority and unsupported transfer remain rejected/unknown with reasons.",
]
LA026_PAIRS_SHA256 = "2ccf55f725559f8a61ccee62e49cdd2a350f6171b7d400148bd62389a55a4117"
LA026_CONTROLS_SHA256 = "9c4ef24da2b52c5f7965f60327f3c1f56159090d6221fd3791827415b780966c"
ORIGINAL_PAIRS_SHA256 = "95ea434792dd8223b7f22ea1232c58d2920c5aaf4fd68b9a255379bd0280f25c"
ORIGINAL_CONTROLS_SHA256 = "2151581aa3b8d61f8abf46dfd7f915225dd56bc2aee140c6719ea1927fb623ab"


def fail(message: str) -> None:
    raise SystemExit("LA-006 validation failed: " + message)


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


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


def check_producer(producer: dict, label: str) -> None:
    if not isinstance(producer, dict):
        fail(f"{label} missing producer")
    if producer.get("id") != PRODUCER_ID:
        fail(f"{label} producer id is not {PRODUCER_ID}")
    if producer.get("kind") != PRODUCER_KIND:
        fail(f"{label} producer kind is not {PRODUCER_KIND}")
    if producer.get("distinct_from_evaluated_adapter") is not True:
        fail(f"{label} producer is not distinct from the evaluated adapter")
    if producer.get("evaluated_adapter") != EVALUATED_ADAPTER:
        fail(f"{label} evaluated adapter identity missing")
    if producer.get("not_cvefixes_adapter_output") is not True:
        fail(f"{label} producer is represented as adapter output")
    if producer.get("not_human_gold") is not True or producer.get("not_independent_review") is not True:
        fail(f"{label} producer claims human gold")


def check_contract(contract: dict, label: str) -> None:
    if not isinstance(contract, dict):
        fail(f"{label} missing behavior contract")
    if contract.get("kind") != "scoped_machine_checkable_behavior_contract":
        fail(f"{label} contract kind is not machine-checkable")
    if contract.get("expectation_kind") != "machine_contract":
        fail(f"{label} contract is not a machine contract")
    if not contract.get("checked_property"):
        fail(f"{label} contract missing checked_property")
    observation = contract.get("observation")
    if not isinstance(observation, dict) or not observation:
        fail(f"{label} missing actual observation")
    check_producer(contract.get("producer") or {}, label)
    if contract.get("polarity_supported_by_contract") is not False:
        fail(f"{label} claims a polarity the observation does not support")
    denom = contract.get("unsupported_metric_denominator")
    if not isinstance(denom, dict) or denom.get("excluded") is not True:
        fail(f"{label} unknown polarity was not excluded from the unsupported denominator")
    if not isinstance(denom.get("reason"), str) or len(denom["reason"].strip()) < 20:
        fail(f"{label} missing denominator exclusion reason")


def check_history() -> None:
    if not HIST.is_dir():
        fail("original failed/blocked history directory is missing")
    receipt = HIST / "original_receipt.json"
    criteria = HIST / "original_criteria.json"
    if not receipt.is_file() or not criteria.is_file():
        fail("original failed history receipt or criteria missing")
    original = load_json(receipt)
    if original.get("task_id") != "LA-006":
        fail("original receipt is not LA-006")
    recorded = [c.get("criterion") for c in original.get("criteria") or []]
    if recorded != ORIGINAL_CRITERIA:
        fail("original criteria were not retained")
    meta = load_json(criteria)
    if meta.get("failure_kind") != "blocked_missing_independent_human_security_review":
        fail("original failure kind was not retained")
    if meta.get("original_criteria") != ORIGINAL_CRITERIA:
        fail("original_criteria.json does not retain the original criteria")
    for name, expected in (
        ("outputs/benchmark/cases/cve_pairs.jsonl", ORIGINAL_PAIRS_SHA256),
        ("outputs/benchmark/cases/cve_controls.jsonl", ORIGINAL_CONTROLS_SHA256),
        ("outputs/benchmark/annotations/cve_review.md", None),
        ("build_cve_pairs.py", None),
        ("validate_cve_pairs.py", None),
    ):
        path = HIST / name
        if not path.is_file():
            fail(f"original failed history missing {name}")
        if expected is not None and sha256_file(path) != expected:
            fail(f"original failed history {name} hash drift")


def check_pair_identity(row: dict, planned: dict, original: dict, reproduction: dict) -> None:
    source = row.get("source") or {}
    source_id = source.get("source_id")
    assignment = planned.get(source_id)
    if assignment is None:
        fail(f"unexpected source_id {source_id!r}")
    if row.get("schema") != PAIR_SCHEMA:
        fail(f"{source_id} schema drift")
    if row.get("pair_id") != assignment["lineage_family_id"] + ":pair":
        fail(f"{source_id} pair_id drift")
    if row.get("planned_case_ids") != assignment["planned_case_ids"]:
        fail(f"{source_id} planned_case_ids drift")
    if row.get("lineage_family_id") != assignment["lineage_family_id"]:
        fail(f"{source_id} family drift")
    if row.get("split") != assignment["split"]:
        fail(f"{source_id} split drift")
    if row.get("held_out") is not (assignment["split"] != "development"):
        fail(f"{source_id} held_out drift")
    if source.get("cve_id") != assignment["cve_id"]:
        fail(f"{source_id} CVE identity drift")
    if source.get("file_row_number") != assignment["file_row_number"]:
        fail(f"{source_id} file_row_number drift")
    if source.get("fix_commit") != assignment["fix_commit"]:
        fail(f"{source_id} fix_commit drift")
    if source.get("repository") != assignment["repository"]:
        fail(f"{source_id} repository drift")
    if source.get("source_record_sha256") != assignment["source_record_sha256"]:
        fail(f"{source_id} source_record_sha256 drift")
    if source.get("shard_sha256") != assignment["shard_sha256"]:
        fail(f"{source_id} shard hash drift")
    if source.get("revision") != assignment["revision"]:
        fail(f"{source_id} revision drift")
    orig_source = original["source"]
    for key in (
        "cve_id",
        "file_row_number",
        "fix_commit",
        "repository",
        "source_record_sha256",
        "shard_sha256",
        "revision",
        "source_id",
    ):
        if source.get(key) != orig_source.get(key):
            fail(f"{source_id} LA-026 source binding {key} changed")
    orig_iso = original["supported_behavior_evidence"]["isolated_reproduction"]
    iso = row["supported_behavior_evidence"]["isolated_reproduction"]
    for key in (
        "status",
        "vulnerable_revision",
        "fixed_revision",
        "vulnerable_tree_sha256",
        "fixed_tree_sha256",
        "vulnerable_files_recovered",
        "fixed_files_recovered",
        "executed_untrusted_source",
        "native_sink_observed",
        "runnable_sandbox_reproduction",
        "effect_observed",
    ):
        if iso.get(key) != orig_iso.get(key):
            fail(f"{source_id} LA-026 behavior evidence {key} changed")
    if iso.get("vulnerable_revision") != reproduction.get("vulnerable_revision"):
        fail(f"{source_id} reproduction vulnerable revision mismatch")
    if iso.get("fixed_revision") != reproduction.get("fix_commit"):
        fail(f"{source_id} reproduction fixed revision mismatch")
    if row.get("supported_behavior_evidence", {}).get("recovery_failures") not in ([], None):
        if not isinstance(row["supported_behavior_evidence"]["recovery_failures"], list):
            fail(f"{source_id} recovery_failures missing")
    if row.get("empirical_sample") is not True or row.get("enters_empirical_sample_count") is not True:
        fail(f"{source_id} empirical pair dropped from sample counts")
    if row.get("fixture") is not False or row.get("fixture_cve") is not False:
        fail(f"{source_id} empirical pair marked fixture")
    if row.get("mocked_source_record") is not False:
        fail(f"{source_id} mocked source entered empirical counts")
    if source.get("cve_id") in FORBIDDEN_FIXTURE_CVES:
        fail(f"{source_id} fabricated fixture CVE entered empirical counts")
    if row.get("universal_security_claimed") is not False:
        fail(f"{source_id} claims universal security")
    restriction = row.get("restriction_candidate") or {}
    if restriction.get("grants_execution_authority") is not False:
        fail(f"{source_id} grants execution authority")
    if restriction.get("wildcard") is True:
        fail(f"{source_id} admitted a wildcard restriction")
    mapping = row.get("intent_code_effect_mapping") or {}
    if mapping.get("correlation") != "unknown":
        fail(f"{source_id} forced an intent/code-effect correlation")
    if (mapping.get("code_effect") or {}).get("status") != "unsupported_transfer":
        fail(f"{source_id} unsupported transfer received a supported mapping")
    sides = row.get("sides") or {}
    vuln_id, fix_id = assignment["planned_case_ids"]
    if sides.get("vulnerable", {}).get("case_id") != vuln_id:
        fail(f"{source_id} case-0 identity drift")
    if sides.get("fixed", {}).get("case_id") != fix_id:
        fail(f"{source_id} case-1 identity drift")
    if sides["vulnerable"].get("upstream_revision") != original["sides"]["vulnerable"]["upstream_revision"]:
        fail(f"{source_id} vulnerable revision binding changed")
    if sides["fixed"].get("upstream_revision") != original["sides"]["fixed"]["upstream_revision"]:
        fail(f"{source_id} fixed revision binding changed")
    review = (row.get("provenance") or {}).get("independent_human_security_review") or {}
    if review.get("status") != "not_obtained":
        fail(f"{row['pair_id']} independent review status drifted")
    if review.get("reviewer_id") not in {None, ""}:
        fail(f"{row['pair_id']} fabricated reviewer identity")
    if review.get("is_independent_security_review") is not False:
        fail(f"{row['pair_id']} claims independent review")
    adjudication = row.get("adjudication") or {}
    if adjudication.get("final_adjudication") is not None:
        fail(f"{row['pair_id']} fabricated final adjudication")
    if adjudication.get("status") != "unresolved_missing_expert_review":
        fail(f"{row['pair_id']} original blocked adjudication not retained")


def check_pair_polarity(row: dict, machine_cases: dict, catalog: dict) -> None:
    for role in ("vulnerable", "fixed"):
        side = row["sides"][role]
        label = side["case_id"]
        polarity = side.get("polarity") or {}
        if polarity.get("expected") != "unknown":
            fail(f"{label} expected polarity is {polarity.get('expected')!r}")
        if polarity.get("independently_reviewed") is not False:
            fail(f"{label} claims independently reviewed polarity")
        if polarity.get("expert_certified") is not False:
            fail(f"{label} claims expert-certified polarity")
        dataset = "vulnerable_positive" if role == "vulnerable" else "fixed_negative"
        if polarity.get("dataset_derived") != dataset:
            fail(f"{label} dataset-derived role drift")
        result = catalog.get(label)
        if not isinstance(result, dict) or result.get("subject_kind") != "pair_side":
            fail(f"{label} missing bound polarity contract")
        if result.get("expected") != "unknown":
            fail(f"{label} catalog polarity is {result.get('expected')!r}")
        if result.get("empirical_success_credit") is not False:
            fail(f"{label} granted empirical success credit")
        if result.get("independent_human_gold") is not False:
            fail(f"{label} claims independent human gold")
        if result.get("universal_security_claimed") is not False:
            fail(f"{label} claims universal security")
        contract = result.get("behavior_contract") or {}
        check_contract(contract, label)
        observation = contract["observation"]
        if observation.get("source_difference_observed") is not True:
            fail(f"{label} missing source-difference observation")
        if observation.get("executed_untrusted_source") is not False:
            fail(f"{label} claims untrusted execution")
        if observation.get("native_sink_observed") is not False:
            fail(f"{label} claims native sink observation")
        machine = machine_cases.get(label)
        if not isinstance(machine, dict):
            fail(f"{label} missing LA-027 machine case")
        if machine.get("policy_polarity") != "unknown":
            fail(f"{label} LA-027 policy polarity is not unknown")
        if contract.get("la027_policy_polarity") != "unknown":
            fail(f"{label} bound LA-027 polarity is not unknown")
        if side.get("executed") is not False:
            fail(f"{label} claims execution")


def check_control(row: dict, planned: dict, original: dict, parent: dict, catalog: dict) -> None:
    if row.get("schema") != CONTROL_SCHEMA:
        fail(f"{row.get('control_id')} schema drift")
    parent_id = row.get("parent_source_id")
    if parent_id not in planned:
        fail(f"{row.get('control_id')} parent is not a frozen CVE family")
    if row.get("lineage_family_id") != planned[parent_id]["lineage_family_id"]:
        fail(f"{row['control_id']} left its parent family")
    if row.get("split") != planned[parent_id]["split"]:
        fail(f"{row['control_id']} split independently from its parent")
    if row.get("control_id") != original.get("control_id"):
        fail("control identity drift")
    if row.get("empirical_sample") is not False or row.get("enters_empirical_sample_count") is not False:
        fail(f"{row['control_id']} entered empirical sample counts")
    cls = row.get("control_class")
    if cls not in REQUIRED_CONTROLS:
        fail(f"{row['control_id']} unknown control class {cls!r}")
    expected_status = "rejected" if cls in REJECTED_CONTROLS else "unknown"
    if row.get("expected_status") != expected_status:
        fail(f"{row['control_id']} expected_status {row.get('expected_status')!r}")
    if row.get("expected_polarity") != "unknown":
        fail(f"{row['control_id']} forced expected polarity")
    result = catalog.get(row["control_id"])
    if not isinstance(result, dict) or result.get("subject_kind") != "control":
        fail(f"{row['control_id']} missing bound polarity contract")
    polarity = result
    if polarity.get("expected") != "unknown":
        fail(f"{row['control_id']} polarity.expected is not unknown")
    if polarity.get("expected_status") != expected_status:
        fail(f"{row['control_id']} polarity.expected_status mismatch")
    if polarity.get("empirical_success_credit") is not False:
        fail(f"{row['control_id']} polarity granted empirical success")
    if polarity.get("independent_human_gold") is not False:
        fail(f"{row['control_id']} claims human gold")
    check_contract(polarity.get("behavior_contract") or {}, row["control_id"])
    contract = polarity["behavior_contract"]
    if contract.get("status_supported_by_contract") is not True:
        fail(f"{row['control_id']} status is not bound to an observation")
    if cls == "wildcard_scope":
        if not (contract["observation"] or {}).get("contains_wildcard"):
            fail(f"{row['control_id']} wildcard observation missing")
    if cls == "self_granted_authority":
        if (contract["observation"] or {}).get("grants_execution_authority") is not True:
            fail(f"{row['control_id']} self-grant observation missing")
        if row.get("rejected_payload", {}).get("grants_execution_authority") is not True:
            fail(f"{row['control_id']} self-granted payload missing")
    if cls == "unsupported_transfer":
        if (parent.get("intent_code_effect_mapping") or {}).get("code_effect", {}).get("status") != "unsupported_transfer":
            fail(f"{row['control_id']} parent transfer was credited as supported")
    if cls == "misleading_cve_similarity":
        distractor = row.get("distractor") or {}
        if distractor.get("cve_id") in FORBIDDEN_FIXTURE_CVES:
            fail(f"{row['control_id']} fabricated fixture used as distractor")
        if distractor.get("cve_id") == parent["source"]["cve_id"]:
            fail(f"{row['control_id']} reused an empirical CVE as a distractor")
        if distractor.get("cve_id") != original.get("distractor", {}).get("cve_id"):
            fail(f"{row['control_id']} distractor identity drift")
    if cls == "fixed_negative_control":
        if row.get("fixed_case_id") != original.get("fixed_case_id"):
            fail(f"{row['control_id']} fixed-side identity drift")
    if row.get("universal_security_claimed") is not False:
        fail(f"{row['control_id']} claims universal security")
    if row.get("fixture_cve") is not False or row.get("mocked_source_record") is not False:
        fail(f"{row['control_id']} fixture or mocked source")
    review = (row.get("provenance") or {}).get("independent_human_security_review") or {}
    if review.get("reviewer_id") not in {None, ""}:
        fail(f"{row['control_id']} fabricated reviewer")
    adjudication = row.get("adjudication") or {}
    if adjudication.get("status") != "unresolved_missing_expert_review":
        fail(f"{row['control_id']} original blocked adjudication not retained")


def main() -> int:
    for path in (PAIRS, CONTROLS, REVIEW, SOURCES, SPLITS, MACHINE, LA026_PAIRS, LA026_CONTROLS, CONTRACTS):
        if not path.is_file():
            fail(f"missing {path}")
    if sha256_file(PAIRS) != LA026_PAIRS_SHA256 or sha256_file(LA026_PAIRS) != LA026_PAIRS_SHA256:
        fail("live pair envelopes are not the frozen LA-026 bytes")
    if sha256_file(CONTROLS) != LA026_CONTROLS_SHA256 or sha256_file(LA026_CONTROLS) != LA026_CONTROLS_SHA256:
        fail("live control envelopes are not the frozen LA-026 bytes")
    snap_pairs = SNAP / "outputs/benchmark/cases/cve_pairs.jsonl"
    snap_controls = SNAP / "outputs/benchmark/cases/cve_controls.jsonl"
    if sha256_file(snap_pairs) != LA026_PAIRS_SHA256 or sha256_file(snap_controls) != LA026_CONTROLS_SHA256:
        fail("snapshot pair/control copies drifted from the frozen envelopes")
    check_history()
    sources = load_json(SOURCES)
    splits = load_json(SPLITS)
    artifact = next(row for row in sources["source_artifacts"] if row["artifact_id"] == "cve-first-shard")
    planned: dict[str, dict] = {}
    for assignment in splits["assignments"]:
        if assignment["population"] != "cve":
            continue
        source = next(row for row in sources["source_records"] if row["source_id"] == assignment["source_id"])
        planned[assignment["source_id"]] = {
            "cve_id": source["source_locator"]["cve_id"],
            "file_row_number": source["source_locator"]["file_row_number"],
            "fix_commit": source["source_locator"]["fix_commit"],
            "lineage_family_id": assignment["lineage_family_id"],
            "planned_case_ids": assignment["planned_case_ids"],
            "repository": source["source_locator"]["repository"],
            "revision": artifact["revision"],
            "shard_sha256": artifact["sha256"],
            "source_id": assignment["source_id"],
            "source_record_sha256": source["source_record_sha256"],
            "split": assignment["split"],
        }
    if len(planned) != 12:
        fail(f"expected 12 reserved CVE families, found {len(planned)}")
    machine_cases = {
        row["case_id"]: row
        for row in load_json(MACHINE)["cases"]
        if row.get("population") == "cve"
    }
    if len(machine_cases) != 24:
        fail(f"expected 24 LA-027 CVE machine cases, found {len(machine_cases)}")
    reproductions = {}
    for path in sorted(REPRO_DIR.glob("CVE-*.json")):
        record = load_json(path)
        reproductions[record["cve_id"]] = record
    if len(reproductions) != 12:
        fail(f"expected 12 LA-026 reproduction files, found {len(reproductions)}")
    original_pairs = {row["source_id"]: row for row in load_jsonl(LA026_PAIRS)}
    original_controls = {row["control_id"]: row for row in load_jsonl(LA026_CONTROLS)}
    if len(original_pairs) != 12 or len(original_controls) != 84:
        fail("LA-026 evidence counts are not the frozen 12/84")
    catalog_rows = load_jsonl(CONTRACTS)
    if len(catalog_rows) != 108:
        fail(f"expected 108 polarity contracts, found {len(catalog_rows)}")
    catalog = {}
    for row in catalog_rows:
        subject = row.get("subject_id")
        if not subject or subject in catalog:
            fail(f"duplicate or missing polarity subject {subject!r}")
        catalog[subject] = row
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
        source_id = row["source"]["source_id"]
        check_pair_identity(row, planned, original_pairs[source_id], reproductions[row["source"]["cve_id"]])
        check_pair_polarity(row, machine_cases, catalog)
        empirical_cves.append(row["source"]["cve_id"])
        seen_cases.extend([row["sides"]["vulnerable"]["case_id"], row["sides"]["fixed"]["case_id"]])
    expected_cases = [case_id for item in planned.values() for case_id in item["planned_case_ids"]]
    if sorted(seen_cases) != sorted(expected_cases):
        fail("reserved CVE case identities are incomplete")
    if sorted(seen_cases) != sorted(machine_cases):
        fail("LA-027 CVE case identities do not match frozen pairs")
    if len(set(empirical_cves)) != 12:
        fail("empirical CVE identifiers are not 12 distinct real records")
    if any(item in FORBIDDEN_FIXTURE_CVES for item in empirical_cves):
        fail("fabricated fixture CVE entered empirical sample counts")
    parents = {row["source_id"]: row for row in pairs}
    controls = load_jsonl(CONTROLS)
    if len(controls) != 12 * len(REQUIRED_CONTROLS):
        fail(f"expected {12 * len(REQUIRED_CONTROLS)} controls, found {len(controls)}")
    classes_by_family: dict[str, set[str]] = {}
    for row in controls:
        original = original_controls.get(row.get("control_id"))
        if original is None:
            fail(f"control identity {row.get('control_id')!r} is not in the frozen LA-026 set")
        check_control(row, planned, original, parents[row["parent_source_id"]], catalog)
        classes_by_family.setdefault(row["parent_source_id"], set()).add(row["control_class"])
    for source_id, classes in classes_by_family.items():
        if classes != REQUIRED_CONTROLS:
            fail(f"{source_id} missing control classes {sorted(REQUIRED_CONTROLS - classes)}")
    bound_subjects = set(catalog)
    expected_subjects = set(seen_cases) | {row["control_id"] for row in controls}
    if bound_subjects != expected_subjects:
        fail("polarity catalog does not cover every pair side and control")
    require_text(
        REVIEW,
        [
            "automated-scope complete",
            "human gold uncollected",
            "Original LA-006 failed/blocked attempt",
            "blocked_missing_independent_human_security_review",
            "independently reviewed expected polarity",
            "original_failed_blocked_attempt_20260911",
            "Expected polarity remains `unknown`",
            "No independent-human",
            "universal-security",
            "Fabricated fixture CVE identifiers in empirical counts | 0",
            "Mocked source records in empirical counts | 0",
            "Fabricated reviewers | 0",
            "Empirical success credits for unsupported transfer | 0",
            "Empirical success credits for self-granted authority | 0",
            "Polarity results with expected ≠ unknown | 0",
            "wildcard_scope",
            "self_granted_authority",
            "unsupported_transfer",
            "A fix for one restriction is not universal security",
            "untrusted",
            "not executed",
            "No Cohen's kappa",
            "machine-checkable behavior contract",
            "LA-026",
        ],
    )
    report = REVIEW.read_text(encoding="utf-8")
    if re.search(r"expert review (was|is) (completed|obtained|performed)", report, re.I):
        fail("review report claims expert review was obtained")
    if re.search(r"independent human (security )?review (was|is) (completed|obtained)", report, re.I):
        fail("review report claims independent human review was obtained")
    pair_text = PAIRS.read_text(encoding="utf-8")
    if "CVE-2026-0042" in pair_text:
        fail("fixture CVE identifier present in empirical pairs")
    payload = {
        "status": "passed",
        "pairs": len(pairs),
        "empirical_cases": 24,
        "controls": len(controls),
        "control_classes": sorted(REQUIRED_CONTROLS),
        "fixture_cves_in_empirical_counts": 0,
        "mocked_source_records_in_empirical_counts": 0,
        "fabricated_reviewers": 0,
        "empirical_success_credits": 0,
        "independent_human_security_review": "not_obtained",
        "expected_polarity": "unknown",
        "polarity_results_bound": 24 + 84,
        "adjudication": "automated_scope_complete_human_gold_uncollected",
        "evaluation_admission": "automated_scope_source_supported_evidence_complete_polarity_unknown",
        "original_failed_history_retained": True,
        "limitation": "Structural packet checks passed; this is not independent scientific or security expert review.",
    }
    json.dump(payload, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
