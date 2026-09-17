#!/usr/bin/python3.12
"""Typed automated evidence admission for LA-027.

Admits source-contract and policy-effect evidence without reviewer identities
or human labels. This is not independent human gold and does not score
held-out examples. Failed admission returns a non-success result and a
non-zero process exit status.
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
PYTHON = "/usr/bin/python3.12"

SCHEMA = "law-to-action-automated-evidence-admission/v1"
MANIFEST_SCHEMA = "law-to-action-automated-reference-manifest/v1"
ADMISSION_VERSION = "la-027-automated-evidence/v1"
EVIDENCE_SCOPE = "automated_source_contracts_and_policy_effects"
ORIGINAL_PROTOCOL_SHA256 = "ba03394cd66f51999d1b177a29558b6130429eb9fc3faebea5e57c780857940f"
ORIGINAL_PROTOCOL_PATH = "papers/completion/law_to_action/benchmark/protocol.json"
AMENDMENT_PATH = BENCHMARK / "automated_evidence_amendment.json"
MANIFEST_PATH = BENCHMARK / "annotations" / "automated_reference_manifest.json"
FAILED_EXIT = 2

EXPECTED_FAMILIES = 30
EXPECTED_CASES = 60
EXPECTED_SPLIT_FAMILIES = {"development": 6, "calibration": 6, "final": 18}
EXPECTED_POPULATION_FAMILIES = {"legal": 6, "cve": 12, "skill": 12}
EXPECTED_POPULATION_CASES = {"legal": 12, "cve": 24, "skill": 24}

PERMITTED_CLAIMS = (
    "source provenance/span linkage and coverage",
    "parse/schema/structural contract conformance",
    "source-supported narrowly defined CVE behavior",
    "actual solver/checker outcome for encoded obligations",
    "observed protected effects and useful work relative to frozen modeled policy",
    "measured runtime/resource/provider usage with complete failures",
)
WITHDRAWN_CLAIMS = (
    "expert legal source-to-rule semantic fidelity",
    "legal applicability or validity in the world",
    "independent human legal/security/intent validation",
    "inter-annotator agreement or adjudicated gold accuracy",
    "semantic correctness inferred from implementation agreement",
)
CHECKED_PROPERTY = {
    "legal": "source_span_linkage_and_schema_conformance",
    "cve": "source_supported_behavior_contract",
    "skill": "source_span_and_intent_ir_schema_conformance",
}
HUMAN_IDENTITY_FIELDS = (
    "reviewer_id",
    "reviewed_at",
    "reviewer_credentials",
    "agreement",
    "disagreement",
    "adjudication",
    "final_adjudication",
    "independent_human_gold",
    "expert_certified",
)
GOLD_TEXT_MARKERS = (
    "independent human gold",
    "independently reviewed gold",
    "expert legal gold",
    "labeled as human gold",
    "is human gold",
)
GOLD_DISCLAIMERS = (
    "never human/expert gold",
    "never human gold",
    "not human gold",
    "not independent human gold",
    "not expert gold",
)
PRODUCER = {
    "id": "la-027-automated-reference-manifest",
    "kind": "machine_contract_expectation_compiler",
    "version": ADMISSION_VERSION,
    "not_human_gold": True,
    "not_independent_review": True,
    "not_expert_legal_review": True,
    "generated_labels_are": "explicitly identified machine-contract expectations, never human/expert gold",
}
UNCOLLECTED_HUMAN_FIELDS = {
    "reviewer_id": "absent",
    "reviewed_at": "uncollected",
    "agreement": "uncollected",
    "disagreement": "uncollected",
    "adjudication": "uncollected",
    "final_adjudication": "uncollected",
    "independent_human_gold": False,
    "optional_author_review": {
        "required": False,
        "independent": False,
        "collected": False,
        "may_substitute_for_empirical_evidence": False,
        "label": "non-independent",
    },
}


class AdmissionError(RuntimeError):
    """Automated admission cannot proceed."""


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


def pin(path: Path) -> dict[str, Any]:
    relative = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
    return {
        "path": relative,
        "sha256": sha256_file(path) if path.is_file() else None,
        "present": path.is_file(),
        "size_bytes": path.stat().st_size if path.is_file() else None,
    }


def load_amendment() -> dict[str, Any]:
    if not AMENDMENT_PATH.is_file():
        raise AdmissionError("automated_evidence_amendment.json is missing")
    payload = load_json(AMENDMENT_PATH)
    if payload.get("schema") != "law-automated-evidence-scope-amendment/v1":
        raise AdmissionError("amendment schema mismatch")
    original = payload.get("original_protocol") or {}
    if original.get("sha256") != ORIGINAL_PROTOCOL_SHA256:
        raise AdmissionError("amendment does not bind the unchanged original protocol hash")
    if payload.get("original_population_budgets_unchanged") is not True:
        raise AdmissionError("amendment must leave source population and budgets unchanged")
    return payload


def population_inventory(splits: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload = splits if splits is not None else load_json(BENCHMARK / "manifests" / "splits.json")
    families: list[dict[str, Any]] = []
    case_ids: list[str] = []
    split_counts = {name: 0 for name in EXPECTED_SPLIT_FAMILIES}
    population_families = {name: 0 for name in EXPECTED_POPULATION_FAMILIES}
    population_cases = {name: 0 for name in EXPECTED_POPULATION_CASES}
    for row in payload.get("assignments") or []:
        planned = list(row.get("planned_case_ids") or [])
        family = {
            "population": row.get("population"),
            "lineage_family_id": row.get("lineage_family_id"),
            "source_id": row.get("source_id"),
            "split": row.get("split"),
            "planned_case_ids": planned,
        }
        families.append(family)
        case_ids.extend(planned)
        if family["split"] in split_counts:
            split_counts[str(family["split"])] += 1
        if family["population"] in population_families:
            population_families[str(family["population"])] += 1
            population_cases[str(family["population"])] += len(planned)
    missing = []
    unknown = []
    for family in families:
        if not family["lineage_family_id"] or not family["source_id"] or len(family["planned_case_ids"]) != 2:
            missing.append(family["lineage_family_id"])
    return {
        "family_count": len(families),
        "case_count": len(case_ids),
        "unique_case_count": len(set(case_ids)),
        "families": families,
        "case_ids": case_ids,
        "split_family_counts": split_counts,
        "population_family_counts": population_families,
        "population_case_counts": population_cases,
        "missing_case_ids": missing,
        "unknown_expectation_policy": "retain unknown and full source/case accounting",
        "unknown_policy_polarity_case_ids": list(case_ids),
        "complete": (
            len(families) == EXPECTED_FAMILIES
            and len(case_ids) == EXPECTED_CASES
            and len(set(case_ids)) == EXPECTED_CASES
            and split_counts == EXPECTED_SPLIT_FAMILIES
            and population_families == EXPECTED_POPULATION_FAMILIES
            and population_cases == EXPECTED_POPULATION_CASES
            and not missing
        ),
    }


def profile_pins() -> dict[str, Any]:
    paths = {
        "qualify_final_runtime.py": BENCHMARK / "qualify_final_runtime.py",
        "source_pipeline.py": BENCHMARK / "source_pipeline.py",
        "automated_evidence.py": BENCHMARK / "automated_evidence.py",
        "effects.py": BENCHMARK / "handlers" / "effects.py",
        "baselines.py": BENCHMARK / "baselines.py",
        "provers.json": BENCHMARK / "manifests" / "provers.json",
        "arms.json": BENCHMARK / "arms.json",
    }
    pins = {name: pin(path) for name, path in paths.items()}
    return {
        "pins": pins,
        "digest": digest({name: row["sha256"] for name, row in pins.items()}),
        "selected_solver_route": "qf_bool_sympy_sat",
        "selected_crypto_route": "real_ed25519_ucan_verifier",
        "selected_handler_route": "bounded_export_handler",
        "selected_observer_route": "independent-filesystem-journal-observer/v2",
        "selected_enforcement_route": "supervisor_pre_invocation_enforce",
        "selected_durable_store": "duckdb-file-typed-quack-owner",
    }


def budget_pins() -> dict[str, Any]:
    resource_plan = pin(BENCHMARK / "resource_plan.json")
    arms = pin(BENCHMARK / "arms.json")
    protocol = pin(BENCHMARK / "protocol.json")
    return {
        "resource_plan": resource_plan,
        "arms": arms,
        "protocol": protocol,
        "digest": digest(
            {
                "resource_plan": resource_plan["sha256"],
                "arms": arms["sha256"],
                "selected_arm": "A4",
                "paid_provider_budget": 0,
            }
        ),
        "selected_arm": "A4",
        "selected_arm_model_calls": 0,
        "paid_provider_budget": 0,
        "frozen_before_evaluated_predictions": True,
    }


def source_pins() -> dict[str, Any]:
    return {
        "sources.json": pin(BENCHMARK / "manifests" / "sources.json"),
        "splits.json": pin(BENCHMARK / "manifests" / "splits.json"),
        "corpus_counts.json": pin(BENCHMARK / "corpus_counts.json"),
        "protocol.json": pin(BENCHMARK / "protocol.json"),
        "amendment": pin(AMENDMENT_PATH),
        "original_protocol_sha256": ORIGINAL_PROTOCOL_SHA256,
    }


def case_expectation(family: Mapping[str, Any], case_id: str) -> dict[str, Any]:
    population = str(family["population"])
    return {
        "case_id": case_id,
        "lineage_family_id": family["lineage_family_id"],
        "source_id": family["source_id"],
        "population": population,
        "split": family["split"],
        "expectation_kind": "machine_contract",
        "checked_property": CHECKED_PROPERTY[population],
        "policy_polarity": "unknown",
        "structural_expectation": "source_span_and_schema_conformance",
        "authority": "explicitly_identified_machine_contract_expectation",
        "independent_human_gold": False,
        "human_fields": "uncollected",
        "producer": dict(PRODUCER),
        "frozen_before_evaluated_predictions": True,
        "held_out_result_inferred": False,
        "useful_work_success_inferred": False,
    }


def build_reference_manifest() -> dict[str, Any]:
    inventory = population_inventory()
    cases = [
        case_expectation(family, case_id)
        for family in inventory["families"]
        for case_id in family["planned_case_ids"]
    ]
    unsupported = [
        {
            "metric": "expert_legal_fidelity",
            "denominator_restricted": True,
            "reason": "withdrawn_without_independent_data",
        },
        {
            "metric": "inter_annotator_agreement",
            "denominator_restricted": True,
            "reason": "withdrawn_without_independent_data",
        },
        {
            "metric": "independent_human_validation",
            "denominator_restricted": True,
            "reason": "withdrawn_without_independent_data",
        },
        {
            "metric": "legal_applicability_or_validity_in_the_world",
            "denominator_restricted": True,
            "reason": "withdrawn_without_independent_data",
        },
    ]
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "task": "LA-027",
        "evidence_scope": EVIDENCE_SCOPE,
        "admission_version": ADMISSION_VERSION,
        "frozen_before_evaluated_predictions": True,
        "generated_labels_are": PRODUCER["generated_labels_are"],
        "producer": dict(PRODUCER),
        "human_fields": dict(UNCOLLECTED_HUMAN_FIELDS),
        "original_protocol": {"path": ORIGINAL_PROTOCOL_PATH, "sha256": ORIGINAL_PROTOCOL_SHA256},
        "source_pins": source_pins(),
        "inventory": {
            "family_count": inventory["family_count"],
            "case_count": inventory["case_count"],
            "split_family_counts": inventory["split_family_counts"],
            "population_family_counts": inventory["population_family_counts"],
            "population_case_counts": inventory["population_case_counts"],
            "missing_case_ids": inventory["missing_case_ids"],
            "unknown_policy_polarity_count": len(inventory["unknown_policy_polarity_case_ids"]),
            "complete": inventory["complete"],
        },
        "cases": cases,
        "unsupported_metric_denominators": unsupported,
        "permitted_claims": list(PERMITTED_CLAIMS),
        "withdrawn_without_independent_data": list(WITHDRAWN_CLAIMS),
        "fixtures_are_qualification_only": True,
        "held_out_result_inferred": False,
        "useful_work_success_inferred_from_fixtures": False,
        "blank_review_packets_preserved": True,
        "original_receipts_unchanged": ["LA-005", "LA-007", "LA-026", "LA-028"],
    }
    manifest["manifest_digest"] = digest(
        {
            "cases": [row["case_id"] for row in cases],
            "producer": PRODUCER,
            "inventory": manifest["inventory"],
            "original_protocol": ORIGINAL_PROTOCOL_SHA256,
        }
    )
    return manifest


def write_reference_manifest(path: Path | None = None) -> dict[str, Any]:
    manifest = build_reference_manifest()
    destination = path or MANIFEST_PATH
    write_json(destination, manifest)
    return manifest


def load_reference_manifest() -> dict[str, Any]:
    if not MANIFEST_PATH.is_file():
        raise AdmissionError("automated_reference_manifest.json is missing")
    payload = load_json(MANIFEST_PATH)
    if payload.get("schema") != MANIFEST_SCHEMA:
        raise AdmissionError("reference manifest schema mismatch")
    if payload.get("evidence_scope") != EVIDENCE_SCOPE:
        raise AdmissionError("reference manifest evidence_scope mismatch")
    if payload.get("generated_labels_are") != PRODUCER["generated_labels_are"]:
        raise AdmissionError("reference manifest must declare machine-contract expectations")
    if payload.get("producer", {}).get("not_human_gold") is not True:
        raise AdmissionError("reference manifest producer must not be human gold")
    return payload


def walk_strings(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, str):
        found.append(value)
    elif isinstance(value, Mapping):
        for item in value.values():
            found.extend(walk_strings(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(walk_strings(item))
    return found


def populated_human_fields(value: Any, *, path: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            location = f"{path}.{key}" if path else str(key)
            if key in HUMAN_IDENTITY_FIELDS:
                if item in (None, "", [], {}, "absent", "uncollected", False):
                    continue
                if key == "expert_certified" and item is not True:
                    continue
                hits.append(location)
            hits.extend(populated_human_fields(item, path=location))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            hits.extend(populated_human_fields(item, path=f"{path}[{index}]"))
    return hits


def expectation_records(envelope: Mapping[str, Any]) -> list[dict[str, Any]]:
    expectations = envelope.get("machine_expectations") or {}
    if isinstance(expectations, Mapping) and isinstance(expectations.get("cases"), list):
        return [row for row in expectations["cases"] if isinstance(row, Mapping)]
    if isinstance(envelope.get("cases"), list):
        return [row for row in envelope["cases"] if isinstance(row, Mapping)]
    return []


def refuse(reasons: list[str], *, envelope: Mapping[str, Any] | None = None) -> dict[str, Any]:
    unique = sorted(set(reasons))
    return {
        "schema": SCHEMA,
        "admission_version": ADMISSION_VERSION,
        "task": "LA-027",
        "evidence_scope": EVIDENCE_SCOPE,
        "admitted": False,
        "scored": False,
        "held_out_scored": False,
        "final_examples_scored": False,
        "empirical_benchmark_result": False,
        "useful_work_success_inferred_from_fixtures": False,
        "production_claim": False,
        "human_fields": dict(UNCOLLECTED_HUMAN_FIELDS),
        "reasons": unique,
        "exit_status": FAILED_EXIT,
        "message": "Automated admission refused. A failed admission is not an executed study.",
        "envelope_digest": digest(envelope) if envelope is not None else None,
        "admitted_at": utc_now(),
    }


def admit(envelope: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(envelope, Mapping):
        return refuse(["missing_runtime_binding", "missing_source_binding", "incomplete_case_accounting"])
    reasons: list[str] = []
    live_sources = source_pins()
    live_profile = profile_pins()
    live_budget = budget_pins()
    live_inventory = population_inventory()
    live_amendment = load_json(AMENDMENT_PATH) if AMENDMENT_PATH.is_file() else {}
    live_manifest = load_json(MANIFEST_PATH) if MANIFEST_PATH.is_file() else {}

    if envelope.get("evidence_scope") != EVIDENCE_SCOPE:
        reasons.append("missing_runtime_binding")
    original = envelope.get("original_protocol") or {}
    if original.get("sha256") != ORIGINAL_PROTOCOL_SHA256 or original.get("path") != ORIGINAL_PROTOCOL_PATH:
        reasons.append("missing_source_binding")
    source_binding = envelope.get("source_manifest") or envelope.get("sources") or {}
    splits_binding = envelope.get("splits") or {}
    if source_binding.get("sha256") != live_sources["sources.json"]["sha256"]:
        reasons.append("missing_source_binding")
    if splits_binding.get("sha256") != live_sources["splits.json"]["sha256"]:
        reasons.append("missing_source_binding")
    amendment = envelope.get("amendment") or {}
    if amendment.get("sha256") != live_sources["amendment"]["sha256"]:
        reasons.append("missing_source_binding")
    if live_amendment.get("original_population_budgets_unchanged") is not True:
        reasons.append("missing_source_binding")

    inventory = envelope.get("case_inventory") or envelope.get("inventory") or {}
    bound_ids = list(inventory.get("case_ids") or [])
    if (
        inventory.get("family_count") != EXPECTED_FAMILIES
        or inventory.get("case_count") != EXPECTED_CASES
        or len(bound_ids) != EXPECTED_CASES
        or len(set(bound_ids)) != EXPECTED_CASES
        or sorted(bound_ids) != sorted(live_inventory["case_ids"])
        or inventory.get("missing_case_ids") not in ([], None)
        or inventory.get("complete") is not True
        or inventory.get("split_family_counts") != EXPECTED_SPLIT_FAMILIES
        or inventory.get("population_family_counts") != EXPECTED_POPULATION_FAMILIES
        or inventory.get("population_case_counts") != EXPECTED_POPULATION_CASES
    ):
        reasons.append("incomplete_case_accounting")

    runtime = envelope.get("runtime") or {}
    required_routes = (
        "selected_solver_route",
        "selected_crypto_route",
        "selected_handler_route",
        "selected_observer_route",
    )
    if any(not runtime.get(name) for name in required_routes):
        reasons.append("missing_runtime_binding")
    if runtime.get("profile_digest") != live_profile["digest"]:
        reasons.append("stale_profile" if runtime.get("profile_digest") else "missing_runtime_binding")

    budgets = envelope.get("budgets") or {}
    if budgets.get("digest") != live_budget["digest"]:
        reasons.append("stale_budget" if budgets.get("digest") else "missing_runtime_binding")
    if budgets.get("frozen_before_evaluated_predictions") is not True:
        reasons.append("stale_budget")

    expectations = envelope.get("machine_expectations") or {}
    records = expectation_records(envelope)
    producer = expectations.get("producer") or (records[0].get("producer") if records else None) or {}
    if (
        not records
        or len(records) != EXPECTED_CASES
        or sorted(str(row.get("case_id")) for row in records) != sorted(live_inventory["case_ids"])
        or producer.get("kind") != PRODUCER["kind"]
        or producer.get("not_human_gold") is not True
        or expectations.get("frozen_before_evaluated_predictions") is not True
        or expectations.get("generated_labels_are") != PRODUCER["generated_labels_are"]
        or any(row.get("policy_polarity") not in {"unknown", None} and row.get("independent_human_gold") for row in records)
        or any(row.get("producer", {}).get("kind") not in {PRODUCER["kind"], None} for row in records)
        or expectations.get("producer_is_evaluated_compiler") is True
        or envelope.get("expectation_frozen_after_predictions") is True
    ):
        reasons.append("invalid_expectation_provenance")
    if live_manifest and expectations.get("manifest_digest") not in {live_manifest.get("manifest_digest"), digest(live_manifest.get("cases"))}:
        if expectations.get("manifest_digest") and expectations.get("manifest_digest") != live_manifest.get("manifest_digest"):
            reasons.append("invalid_expectation_provenance")

    effects = envelope.get("effect_observation") or {}
    observer = str(effects.get("observer") or "")
    independent = effects.get("independent") is True
    self_reported = effects.get("self_reported") is True or str(effects.get("source") or "").lower() in {
        "self",
        "handler",
        "candidate",
        "producer",
    }
    success_claimed = effects.get("success") is True or effects.get("success_claimed") is True
    if success_claimed and (self_reported or not independent or "EffectObserver" not in observer):
        reasons.append("self_reported_success")
    if envelope.get("useful_work_success") is True or envelope.get("useful_work_success_inferred_from_fixtures") is True:
        reasons.append("self_reported_success")
    if envelope.get("fixture") is True and envelope.get("held_out_result") is True:
        reasons.append("self_reported_success")

    generated = str(envelope.get("generated_labels_are") or expectations.get("generated_labels_are") or "").lower()
    gold_hits = populated_human_fields(envelope)
    text_hits = []
    for text in walk_strings(envelope):
        lower = text.lower()
        if any(disclaimer in lower for disclaimer in GOLD_DISCLAIMERS):
            continue
        if any(marker in lower for marker in GOLD_TEXT_MARKERS):
            text_hits.append(text)
    generated_claims_gold = "human gold" in generated and not any(disclaimer in generated for disclaimer in GOLD_DISCLAIMERS)
    if (
        gold_hits
        or text_hits
        or generated_claims_gold
        or envelope.get("independent_human_gold") is True
        or any(row.get("independent_human_gold") is True for row in records)
    ):
        reasons.append("automated_output_labeled_human_gold")

    review = envelope.get("review") or {}
    if review.get("admitted") is True:
        reasons.append("automated_output_labeled_human_gold")

    if envelope.get("scored") is True or envelope.get("held_out_scored") is True or envelope.get("final_examples_scored") is True:
        reasons.append("incomplete_case_accounting")
        reasons.append("invalid_expectation_provenance")

    permitted = list(envelope.get("permitted_claims") or [])
    withdrawn = list(envelope.get("withdrawn_without_independent_data") or envelope.get("withdrawn_claims") or [])
    if permitted != list(PERMITTED_CLAIMS) or withdrawn != list(WITHDRAWN_CLAIMS):
        reasons.append("invalid_expectation_provenance")

    if envelope.get("human_fields") and populated_human_fields(envelope.get("human_fields") or {}):
        reasons.append("automated_output_labeled_human_gold")

    if reasons:
        return refuse(reasons, envelope=envelope)

    return {
        "schema": SCHEMA,
        "admission_version": ADMISSION_VERSION,
        "task": "LA-027",
        "evidence_scope": EVIDENCE_SCOPE,
        "admitted": True,
        "scored": False,
        "held_out_scored": False,
        "final_examples_scored": False,
        "empirical_benchmark_result": False,
        "useful_work_success_inferred_from_fixtures": False,
        "production_claim": False,
        "development_qualification_is_not_held_out": True,
        "fixtures_are_qualification_only": True,
        "human_fields": dict(UNCOLLECTED_HUMAN_FIELDS),
        "reasons": [],
        "exit_status": 0,
        "bindings": {
            "original_protocol": {"path": ORIGINAL_PROTOCOL_PATH, "sha256": ORIGINAL_PROTOCOL_SHA256},
            "amendment": live_sources["amendment"],
            "source_manifest": live_sources["sources.json"],
            "splits": live_sources["splits.json"],
            "case_count": EXPECTED_CASES,
            "family_count": EXPECTED_FAMILIES,
            "machine_expectations_digest": expectations.get("manifest_digest") or live_manifest.get("manifest_digest"),
            "profile_digest": live_profile["digest"],
            "budget_digest": live_budget["digest"],
            "observer": runtime.get("selected_observer_route"),
            "solver": runtime.get("selected_solver_route"),
        },
        "permitted_claims": list(PERMITTED_CLAIMS),
        "withdrawn_without_independent_data": list(WITHDRAWN_CLAIMS),
        "message": (
            "Automated source-contract and policy-effect admission succeeded without reviewer "
            "identities or human labels. This is not a scored held-out study and not human gold."
        ),
        "envelope_digest": digest(envelope),
        "admitted_at": utc_now(),
    }


def build_valid_envelope(
    *,
    qualification: Mapping[str, Any] | None = None,
    effect_observation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    inventory = population_inventory()
    manifest = load_reference_manifest() if MANIFEST_PATH.is_file() else build_reference_manifest()
    profile = profile_pins()
    budgets = budget_pins()
    sources = source_pins()
    observation = dict(effect_observation or {})
    observation.setdefault("observer", "EffectObserver.observe")
    observation.setdefault("independent", True)
    observation.setdefault("self_reported", False)
    observation.setdefault("success_claimed", False)
    observation.setdefault("qualification_only", True)
    envelope = {
        "schema": SCHEMA,
        "evidence_scope": EVIDENCE_SCOPE,
        "admission_version": ADMISSION_VERSION,
        "original_protocol": {"path": ORIGINAL_PROTOCOL_PATH, "sha256": ORIGINAL_PROTOCOL_SHA256},
        "amendment": sources["amendment"],
        "source_manifest": sources["sources.json"],
        "splits": sources["splits.json"],
        "case_inventory": {
            "family_count": inventory["family_count"],
            "case_count": inventory["case_count"],
            "case_ids": list(inventory["case_ids"]),
            "split_family_counts": inventory["split_family_counts"],
            "population_family_counts": inventory["population_family_counts"],
            "population_case_counts": inventory["population_case_counts"],
            "missing_case_ids": [],
            "unknown_policy_polarity_count": inventory["case_count"],
            "complete": True,
        },
        "machine_expectations": {
            "manifest_path": str(MANIFEST_PATH.relative_to(ROOT)),
            "manifest_digest": manifest.get("manifest_digest"),
            "producer": dict(PRODUCER),
            "generated_labels_are": PRODUCER["generated_labels_are"],
            "frozen_before_evaluated_predictions": True,
            "producer_is_evaluated_compiler": False,
            "cases": list(manifest.get("cases") or []),
        },
        "runtime": {
            "selected_solver_route": profile["selected_solver_route"],
            "selected_crypto_route": profile["selected_crypto_route"],
            "selected_handler_route": profile["selected_handler_route"],
            "selected_observer_route": profile["selected_observer_route"],
            "selected_enforcement_route": profile["selected_enforcement_route"],
            "selected_durable_store": profile["selected_durable_store"],
            "profile_digest": profile["digest"],
        },
        "budgets": {
            "digest": budgets["digest"],
            "selected_arm": "A4",
            "selected_arm_model_calls": 0,
            "paid_provider_budget": 0,
            "frozen_before_evaluated_predictions": True,
        },
        "effect_observation": observation,
        "permitted_claims": list(PERMITTED_CLAIMS),
        "withdrawn_without_independent_data": list(WITHDRAWN_CLAIMS),
        "human_fields": dict(UNCOLLECTED_HUMAN_FIELDS),
        "generated_labels_are": PRODUCER["generated_labels_are"],
        "scored": False,
        "held_out_scored": False,
        "final_examples_scored": False,
        "fixture": False,
        "qualification": dict(qualification or {"development_only": True, "held_out_scored": False}),
    }
    return envelope


def control_envelope(name: str) -> dict[str, Any]:
    envelope = build_valid_envelope()
    if name == "missing_runtime_binding":
        envelope["runtime"] = {}
    elif name == "missing_source_binding":
        envelope["source_manifest"] = {"sha256": "0" * 64}
        envelope["splits"] = {}
    elif name == "incomplete_case_accounting":
        envelope["case_inventory"]["case_ids"] = envelope["case_inventory"]["case_ids"][:-1]
        envelope["case_inventory"]["case_count"] = EXPECTED_CASES - 1
        envelope["case_inventory"]["complete"] = True
        envelope["case_inventory"]["missing_case_ids"] = []
    elif name == "invalid_expectation_provenance":
        envelope["machine_expectations"]["producer"] = {
            "id": "evaluated-compiler",
            "kind": "evaluated_compiler_self_label",
            "not_human_gold": True,
        }
        envelope["machine_expectations"]["frozen_before_evaluated_predictions"] = False
        envelope["machine_expectations"]["producer_is_evaluated_compiler"] = True
    elif name == "self_reported_success":
        envelope["effect_observation"] = {
            "observer": "handler.execute",
            "independent": False,
            "self_reported": True,
            "source": "handler",
            "success": True,
            "success_claimed": True,
        }
        envelope["useful_work_success"] = True
    elif name == "stale_profile":
        envelope["runtime"]["profile_digest"] = "1" * 64
    elif name == "stale_budget":
        envelope["budgets"]["digest"] = "2" * 64
        envelope["budgets"]["frozen_before_evaluated_predictions"] = True
    elif name == "automated_output_labeled_human_gold":
        envelope["generated_labels_are"] = "independent human gold"
        envelope["independent_human_gold"] = True
        envelope["review"] = {"admitted": True, "reviewer_id": "agent-fabricated"}
        envelope["machine_expectations"]["cases"][0]["independent_human_gold"] = True
    else:
        raise AdmissionError(f"unknown control {name}")
    return envelope


CONTROL_NAMES = (
    "missing_runtime_binding",
    "missing_source_binding",
    "incomplete_case_accounting",
    "invalid_expectation_provenance",
    "self_reported_success",
    "stale_profile",
    "stale_budget",
    "automated_output_labeled_human_gold",
)
EXPECTED_CONTROL_REASONS = {
    "missing_runtime_binding": "missing_runtime_binding",
    "missing_source_binding": "missing_source_binding",
    "incomplete_case_accounting": "incomplete_case_accounting",
    "invalid_expectation_provenance": "invalid_expectation_provenance",
    "self_reported_success": "self_reported_success",
    "stale_profile": "stale_profile",
    "stale_budget": "stale_budget",
    "automated_output_labeled_human_gold": "automated_output_labeled_human_gold",
}


def run_controls(out: Path | None = None) -> dict[str, Any]:
    results = []
    destination = out
    if destination is not None:
        (destination / "controls").mkdir(parents=True, exist_ok=True)
    for name in CONTROL_NAMES:
        envelope = control_envelope(name)
        admission = admit(envelope)
        expected = EXPECTED_CONTROL_REASONS[name]
        ok = (
            admission.get("admitted") is False
            and admission.get("exit_status") == FAILED_EXIT
            and expected in (admission.get("reasons") or [])
            and admission.get("scored") is False
        )
        row = {
            "control": name,
            "expected_reason": expected,
            "admitted": admission.get("admitted"),
            "scored": admission.get("scored"),
            "exit_status": admission.get("exit_status"),
            "reasons": admission.get("reasons"),
            "passed": ok,
        }
        results.append(row)
        if destination is not None:
            write_json(
                destination / "controls" / f"{name}.json",
                {"control": name, "mutation": name, "admission": admission, "check": row},
            )
    summary = {
        "schema": "law-to-action-automated-admission-controls/v1",
        "controls": results,
        "all_refused": all(row["passed"] for row in results),
        "normal_admission": admit(build_valid_envelope()),
    }
    if destination is not None:
        write_json(destination / "admission_controls.json", summary)
    return summary


def automated_analysis(admission: Mapping[str, Any], qualification: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if admission.get("admitted") is not True:
        return {
            "schema": "law-to-action-automated-analysis/v1",
            "status": "refused",
            "scored": False,
            "held_out_scored": False,
            "code": "analysis_refuses_unadmitted_automated_scope",
            "message": "Analysis refuses to score or interpret an unadmitted automated envelope.",
            "admission": admission,
            "exit_status": FAILED_EXIT,
        }
    return {
        "schema": "law-to-action-automated-analysis/v1",
        "status": "qualification_recorded_not_scored",
        "scored": False,
        "held_out_scored": False,
        "final_examples_scored": False,
        "empirical_benchmark_result": False,
        "useful_work_success_inferred_from_fixtures": False,
        "permitted_claims": list(PERMITTED_CLAIMS),
        "withdrawn_without_independent_data": list(WITHDRAWN_CLAIMS),
        "qualification": qualification or {},
        "message": (
            "Automated-scope analysis records source-contract coverage and independent "
            "effect-observer qualification. It does not score held-out examples or claim "
            "expert legal fidelity, legal validity, or human agreement."
        ),
        "admission": {
            "admitted": True,
            "scored": False,
            "evidence_scope": EVIDENCE_SCOPE,
        },
        "exit_status": 0,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("build-manifest", "admit", "admit-live", "control", "controls", "analyze"),
        nargs="?",
        default="admit-live",
    )
    parser.add_argument("--envelope", type=Path)
    parser.add_argument("--control", choices=CONTROL_NAMES)
    parser.add_argument("--out", type=Path, default=LIVE / "results" / "automated_scope_qualification")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "build-manifest":
        manifest = write_reference_manifest()
        print(json.dumps({"path": str(MANIFEST_PATH.relative_to(ROOT)), "digest": manifest["manifest_digest"]}, indent=2, sort_keys=True))
        return 0
    if args.command == "controls":
        summary = run_controls(args.out)
        print(json.dumps(summary, indent=2, sort_keys=True, default=str))
        return 0 if summary.get("all_refused") and summary["normal_admission"].get("admitted") is True else FAILED_EXIT
    if args.command == "control":
        name = args.control or CONTROL_NAMES[0]
        admission = admit(control_envelope(name))
        print(json.dumps(admission, indent=2, sort_keys=True))
        return int(admission.get("exit_status") or FAILED_EXIT)
    if args.command == "admit":
        if args.envelope is None or not args.envelope.is_file():
            admission = refuse(["missing_runtime_binding", "missing_source_binding"])
        else:
            admission = admit(load_json(args.envelope))
        print(json.dumps(admission, indent=2, sort_keys=True))
        status = admission.get("exit_status")
        return int(status) if isinstance(status, int) else FAILED_EXIT
    if args.command == "analyze":
        if args.envelope is not None and args.envelope.is_file():
            admission = admit(load_json(args.envelope))
        else:
            admission = admit(build_valid_envelope())
        analysis = automated_analysis(admission)
        print(json.dumps(analysis, indent=2, sort_keys=True))
        status = analysis.get("exit_status")
        return int(status) if isinstance(status, int) else FAILED_EXIT
    envelope = build_valid_envelope()
    admission = admit(envelope)
    args.out.mkdir(parents=True, exist_ok=True)
    write_json(args.out / "automated_envelope.json", envelope)
    write_json(args.out / "automated_admission.json", admission)
    print(json.dumps(admission, indent=2, sort_keys=True))
    status = admission.get("exit_status")
    return int(status) if isinstance(status, int) else FAILED_EXIT


if __name__ == "__main__":
    raise SystemExit(main())
