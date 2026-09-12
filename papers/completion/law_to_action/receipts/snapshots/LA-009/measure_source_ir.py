#!/usr/bin/python3.12
"""LA-009 source-to-IR contract, coverage, and scoped behavior measurements.

Runs pinned adapters on the unchanged frozen 60-case cohort. Metrics are
machine-contract coverage and observations, never expert legal fidelity,
human agreement, or semantic accuracy inferred from implementation agreement.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import traceback
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping
from uuid import uuid4

SNAPSHOT = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[6]
LIVE = ROOT / "papers" / "completion" / "law_to_action"
BENCHMARK = LIVE / "benchmark"
PYTHON = "/usr/bin/python3.12"
VALIDATION_SITE_PACKAGES = Path("/opt/ipfs-validation-site-packages")

SCHEMA = "law-to-action-source-ir-measurement/v1"
METRICS_SCHEMA = "law-to-action-source-ir-metrics/v1"
PIPELINE_VERSION = "la-009-source-ir/v1"
TASK = "LA-009"
EVIDENCE_SCOPE = "automated_source_contracts_and_policy_effects"
ORIGINAL_PROTOCOL_SHA256 = "ba03394cd66f51999d1b177a29558b6130429eb9fc3faebea5e57c780857940f"
EXPECTED_SPLITS_SHA256 = "f40b60ce73acbbbb7e9da39159b7dc5706f250cb5b85ac407c4b10140cb5c5a6"
EXPECTED_SOURCES_SHA256 = "55c69799805ce8466c7935f41c43a6656fbb2dce867496fb771ae07c4395feb6"
EXPECTED_FAMILIES = 30
EXPECTED_CASES = 60
EXPECTED_SPLIT_FAMILIES = {"development": 6, "calibration": 6, "final": 18}
EXPECTED_POPULATION_FAMILIES = {"legal": 6, "cve": 12, "skill": 12}
EXPECTED_POPULATION_CASES = {"legal": 12, "cve": 24, "skill": 24}
CHECKED_PROPERTY = {
    "legal": "source_span_linkage_and_schema_conformance",
    "cve": "source_supported_behavior_contract",
    "skill": "source_span_and_intent_ir_schema_conformance",
}
LEGAL_SCHEMA_KEYS = (
    "deontic_operator",
    "norm_type",
    "action",
    "exceptions",
    "conditions",
    "subject",
)
GENERATED_LABELS = (
    "predictions or explicitly identified machine-contract expectations, never human/expert gold"
)
WITHDRAWN = (
    "expert_legal_fidelity",
    "inter_annotator_agreement",
    "independent_human_validation",
    "legal_applicability_or_validity_in_the_world",
    "semantic_accuracy_from_implementation_agreement",
)

for path in (
    VALIDATION_SITE_PACKAGES,
    ROOT / "external" / "ipfs_accelerate",
    ROOT / "external" / "ipfs_datasets",
    ROOT / "external" / "ipfs_kit",
):
    text = str(path)
    if path.is_dir() and text not in sys.path:
        sys.path.insert(0, text)


class MeasurementError(RuntimeError):
    """Measurement cannot proceed without changing frozen cohorts."""


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode(
        "utf-8"
    )


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-" + uuid4().hex)
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-" + uuid4().hex)
    temporary.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    os.replace(temporary, path)


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-" + uuid4().hex)
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(canonical_json(row).decode("utf-8") + "\n")
    os.replace(temporary, path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def bounded_error(exc: BaseException, limit: int = 800) -> str:
    text = f"{type(exc).__name__}: {exc}"
    return text if len(text) <= limit else text[: limit - 3] + "..."


def pin_path(path: Path) -> dict[str, Any]:
    relative = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
    return {
        "path": relative,
        "sha256": sha256_file(path) if path.is_file() else None,
        "size_bytes": path.stat().st_size if path.is_file() else None,
        "present": path.is_file(),
    }


def rate(numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "rate": None if denominator == 0 else numerator / denominator,
        "formula": f"{numerator}/{denominator}",
    }


def configure_runtime() -> dict[str, Any]:
    versions: dict[str, Any] = {
        "pipeline_version": PIPELINE_VERSION,
        "python": PYTHON,
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "path": os.environ.get("PATH"),
        "home": os.environ.get("HOME"),
        "home_is_validation_prefix": str(os.environ.get("HOME", "")).startswith("ipfs-accelerate-validation-home-"),
        "validation_site_packages": str(VALIDATION_SITE_PACKAGES) if VALIDATION_SITE_PACKAGES.is_dir() else None,
        "python_executable_sha256": sha256_file(Path(sys.executable)) if Path(sys.executable).is_file() else None,
    }
    for name in ("cryptography", "multiformats", "sympy", "duckdb"):
        try:
            module = __import__(name)
            versions[name] = {
                "available": True,
                "version": getattr(module, "__version__", None),
                "origin": getattr(module, "__file__", None),
            }
        except Exception as exc:
            versions[name] = {"available": False, "error": bounded_error(exc)}
    return versions


def reconstruct_span_text(spans: Any) -> dict[str, Any]:
    if not isinstance(spans, list):
        return {
            "text": "",
            "span_count": 0,
            "quoted_sha256s": [],
            "hash_matches": 0,
            "hash_mismatches": 0,
            "empty_quoted": 0,
            "reconstructed_sha256": None,
            "redistribution": "quoted_spans_only",
        }
    parts: list[str] = []
    hashes: list[str] = []
    matches = 0
    mismatches = 0
    empty = 0
    for span in spans:
        if not isinstance(span, Mapping):
            continue
        quoted = span.get("quoted_text")
        if not isinstance(quoted, str) or not quoted:
            empty += 1
            continue
        actual = sha256_text(quoted)
        declared = span.get("quoted_sha256")
        if declared == actual:
            matches += 1
        else:
            mismatches += 1
        parts.append(quoted)
        hashes.append(str(declared or actual))
    text = "\n\n".join(parts)
    return {
        "text": text,
        "span_count": len(parts),
        "quoted_sha256s": hashes,
        "hash_matches": matches,
        "hash_mismatches": mismatches,
        "empty_quoted": empty,
        "reconstructed_sha256": sha256_text(text) if text else None,
        "redistribution": "quoted_spans_only",
    }


def span_linkage_record(spans: Any, reconstructed: Mapping[str, Any]) -> dict[str, Any]:
    present = reconstructed["span_count"] > 0
    hashes_ok = reconstructed["hash_mismatches"] == 0 and reconstructed["span_count"] > 0
    return {
        "checker": {
            "id": "la-009-quoted-span-hash-checker",
            "kind": "independent_source_span_checker",
            "distinct_from_evaluated_adapter": True,
            "not_human_gold": True,
        },
        "span_count": reconstructed["span_count"],
        "hash_matches": reconstructed["hash_matches"],
        "hash_mismatches": reconstructed["hash_mismatches"],
        "empty_quoted": reconstructed["empty_quoted"],
        "reconstructed_sha256": reconstructed["reconstructed_sha256"],
        "linked": present and hashes_ok,
        "coverage": "quoted_spans_present" if present else "no_quoted_spans",
        "input_span_count": len(spans) if isinstance(spans, list) else 0,
    }


def overlay_text(value: Any) -> str:
    if isinstance(value, str) and value.strip():
        return value
    if isinstance(value, Mapping):
        quoted = value.get("quoted_text")
        if isinstance(quoted, str) and quoted.strip():
            return quoted
    return ""


def skill_markdown(record: Mapping[str, Any]) -> str:
    overlay = overlay_text(record.get("mutation_overlay"))
    spans = record.get("source_spans") if isinstance(record.get("source_spans"), list) else []
    blocks: list[str] = []
    for span in spans:
        if not isinstance(span, Mapping):
            continue
        quoted = span.get("quoted_text")
        if not isinstance(quoted, str) or not quoted:
            continue
        role = str(span.get("role") or "section")
        heading = role.replace("_", " ").strip().title()
        blocks.append(f"## {heading}\n\n{quoted}")
    body = "\n\n".join(blocks)
    if overlay:
        return body + ("\n\n" if body else "") + overlay
    return body


def canonical_cid(payload: Any, *, domain: str) -> str:
    from ipfs_datasets_py.logic.ir_core.identity import canonical_identity
    from ipfs_datasets_py.logic.security_ir.cvefixes.schemas import CVEFIXES_SCHEMA_VERSION

    return canonical_identity(payload, domain=domain, schema_version=CVEFIXES_SCHEMA_VERSION).cid


def cve_attributes(restriction: Mapping[str, Any]) -> dict[str, Any]:
    language = restriction.get("language")
    if isinstance(language, Mapping):
        language_term = language.get("canonical") or language.get("name")
    else:
        language_term = language
    return {
        "action": restriction.get("action"),
        "cve_ids": list(restriction.get("cve_ids") or []),
        "cwe_ids": list(restriction.get("cwe_ids") or []),
        "effects": list(restriction.get("effects") or []),
        "language": language_term,
        "mitigations": list(restriction.get("mitigations") or []),
        "preconditions": list(restriction.get("preconditions") or []),
        "schema_version": "security.cvefixes/v1",
        "scope": restriction.get("scope"),
    }


def compact_mapping(value: Any, *, keys: tuple[str, ...] | None = None, limit: int = 24) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {"type": type(value).__name__}
    selected = dict(value) if keys is None else {key: value.get(key) for key in keys if key in value}
    if len(selected) > limit:
        keep = list(selected.items())[:limit]
        selected = dict(keep)
        selected["truncated"] = True
    return selected


def unmeasured_block() -> dict[str, Any]:
    return {
        "expert_legal_fidelity": "unmeasured",
        "human_agreement": "unmeasured",
        "semantic_accuracy": "unmeasured",
        "numeric_score_assigned": False,
        "reason": "withdrawn_without_independent_data",
    }


def base_row(family: Mapping[str, Any], case_id: str, *, mutation_class: str | None) -> dict[str, Any]:
    population = family["population"]
    return {
        "schema": SCHEMA,
        "task": TASK,
        "pipeline_version": PIPELINE_VERSION,
        "evidence_scope": EVIDENCE_SCOPE,
        "case_id": case_id,
        "lineage_family_id": family["lineage_family_id"],
        "source_id": family["source_id"],
        "population": population,
        "split": family["split"],
        "planned_case_ids": list(family["planned_case_ids"]),
        "mutation_class": mutation_class,
        "empirical_source_case": True,
        "frozen_selected_case": True,
        "synthetic_qualification_control": False,
        "human_review_run_dependency": False,
        "independent_human_gold": False,
        "generated_labels_are": GENERATED_LABELS,
        "implementation_agreement_is_not_semantic_accuracy": True,
        "unmeasured": unmeasured_block(),
        "machine_expectation": {
            "checked_property": CHECKED_PROPERTY[population],
            "expectation_kind": "machine_contract",
            "authority": "explicitly_identified_machine_contract_expectation",
            "producer": {
                "id": "la-027-automated-reference-manifest",
                "kind": "machine_contract_expectation_compiler",
                "version": "la-027-automated-evidence/v1",
                "not_human_gold": True,
                "not_independent_review": True,
                "not_expert_legal_review": True,
                "distinct_from_evaluated_adapter": True,
                "generated_labels_are": "explicitly identified machine-contract expectations, never human/expert gold",
            },
            "frozen_before_evaluated_predictions": True,
            "independent_human_gold": False,
            "policy_polarity": "unknown",
        },
    }


def legal_schema_check(elements: Any) -> dict[str, Any]:
    if not isinstance(elements, list):
        return {"valid": False, "reason": "elements_not_a_list", "element_count": 0, "required_keys_present": 0}
    missing = 0
    present = 0
    for element in elements:
        if not isinstance(element, Mapping):
            missing += 1
            continue
        if all(key in element for key in LEGAL_SCHEMA_KEYS):
            present += 1
        else:
            missing += 1
    return {
        "valid": missing == 0,
        "reason": "ok" if missing == 0 else "missing_required_fields",
        "element_count": len(elements),
        "required_keys_present": present,
        "required_keys_missing": missing,
        "empty_parse_is_schema_valid": len(elements) == 0,
        "checker": {
            "id": "la-009-legal-element-schema-checker",
            "kind": "independent_structural_schema_checker",
            "distinct_from_evaluated_adapter": True,
            "checked_keys": list(LEGAL_SCHEMA_KEYS),
        },
    }


def measure_legal(record: Mapping[str, Any], family: Mapping[str, Any]) -> dict[str, Any]:
    case_id = record["case_id"]
    reconstructed = reconstruct_span_text(record.get("source_spans"))
    text = reconstructed["text"]
    row = base_row(family, case_id, mutation_class=record.get("mutation_class"))
    row["adapter"] = {
        "id": "deterministic_deontic_parser",
        "symbol": "extract_normative_elements",
        "module": "ipfs_datasets_py.logic.deontic.utils.deontic_parser",
        "version": None,
    }
    row["source_span_linkage"] = span_linkage_record(record.get("source_spans"), reconstructed)
    row["input"] = {
        "annotation_id": record.get("annotation_id"),
        "source_artifact_id": (record.get("source") or {}).get("artifact_id"),
        "document_sha256": (record.get("source") or {}).get("document_sha256"),
        "span_reconstruction": {key: reconstructed[key] for key in reconstructed if key != "text"},
        "text_sha256": sha256_text(text) if text else None,
        "independent_label_used": False,
        "packet_preparer_atoms_used_as_gold": False,
    }
    if not text:
        row["status"] = "unavailable"
        row["failure"] = {"code": "empty_quoted_source", "message": "legal record has no quoted source spans"}
        row["parse_schema_validity"] = {"valid": False, "reason": "no_source_text"}
        row["supported_unsupported_fields"] = {"supported": [], "unsupported": ["quoted_source_text"]}
        row["compiler_checker"] = {"ran": False, "reason": "no_source_text"}
        row["machine_contract_outcome"] = {
            "checked_property": CHECKED_PROPERTY["legal"],
            "satisfied": False,
            "reason": "source_unavailable",
            "implementation_agreement_is_not_semantic_accuracy": True,
        }
        return row
    try:
        from ipfs_datasets_py.logic.deontic.utils.deontic_parser import PARSER_SCHEMA_VERSION, extract_normative_elements

        row["adapter"]["version"] = PARSER_SCHEMA_VERSION
        elements = extract_normative_elements(text, document_type="statute")
        compact_elements = []
        supported: list[str] = []
        unsupported: list[str] = []
        for element in elements:
            compact_elements.append(
                {
                    "deontic_operator": element.get("deontic_operator"),
                    "norm_type": element.get("norm_type"),
                    "action": element.get("action"),
                    "action_verb": element.get("action_verb"),
                    "subject": element.get("subject"),
                    "exceptions": element.get("exceptions"),
                    "conditions": element.get("conditions"),
                    "promotable_to_theorem": element.get("promotable_to_theorem"),
                    "element_sha256": digest(
                        {
                            "deontic_operator": element.get("deontic_operator"),
                            "action": element.get("action"),
                            "support_text": element.get("support_text"),
                            "source_id": element.get("source_id"),
                        }
                    ),
                }
            )
            if element.get("deontic_operator"):
                supported.append("deontic_operator")
            if element.get("exceptions"):
                supported.append("exceptions")
            else:
                unsupported.append("exceptions_empty_in_parse")
            if element.get("promotable_to_theorem") is False:
                unsupported.append("promotable_to_theorem")
        schema = legal_schema_check(elements)
        converter_payload = None
        converter_error = None
        try:
            from ipfs_datasets_py.logic.deontic.converter import DeonticConverter

            converter = DeonticConverter(
                use_cache=False,
                use_ml=False,
                enable_monitoring=False,
                jurisdiction="us",
                document_type="statute",
            )
            converted = converter.convert(text)
            output = getattr(converted, "output", None)
            converter_payload = {
                "status": str(getattr(converted, "status", None)),
                "operator": str(getattr(getattr(output, "operator", None), "value", getattr(output, "operator", None))),
                "proposition": getattr(output, "proposition", None),
                "confidence": getattr(output, "confidence", None),
                "source_text_sha256": sha256_text(getattr(output, "source_text", "") or ""),
            }
        except Exception as exc:
            converter_error = bounded_error(exc)
        compiler_status: dict[str, Any]
        try:
            from ipfs_datasets_py.logic.integration.reasoning.legal_ir_compiler_api import compile_legal_ir

            compiled = compile_legal_ir(text)
            compiler_status = {
                "available": True,
                "status": getattr(compiled, "status", None),
                "exit_code": getattr(compiled, "exit_code", None),
            }
        except Exception as exc:
            compiler_status = {
                "available": False,
                "error": bounded_error(exc),
                "selected": False,
                "note": "LegalIRCompilerAPI is not the selected adapter; the deterministic deontic parser ran.",
            }
        nonempty = len(elements) > 0
        converter_nonempty = bool(
            converter_payload
            and converter_payload.get("proposition")
            and converter_payload.get("proposition") != "UnparsedNonNormativeOrAmbiguousText"
        )
        row["status"] = "prediction"
        row["prediction"] = {
            "kind": "legal_deontic_elements",
            "element_count": len(elements),
            "elements": compact_elements,
            "elements_sha256": digest(compact_elements),
            "converter": converter_payload,
            "converter_error": converter_error,
            "legal_ir_compiler": compiler_status,
            "authority": "non_authoritative_adapter_output",
            "independent_review": "not_used",
            "independent_human_gold": False,
        }
        row["parse_schema_validity"] = schema
        row["supported_unsupported_fields"] = {
            "supported": sorted(set(supported)),
            "unsupported": sorted(set(unsupported)),
            "source_unsupported_constructs": list(record.get("unsupported_constructs") or []),
        }
        row["compiler_checker"] = {
            "parser": {"ran": True, "nonempty_elements": nonempty, "producer": "deterministic_deontic_parser"},
            "converter": {
                "ran": converter_payload is not None,
                "nonempty_proposition": converter_nonempty,
                "producer": "DeonticConverter",
                "error": converter_error,
            },
            "legal_ir_compiler": compiler_status,
            "implementation_consistency": {
                "both_ran": converter_payload is not None,
                "agree_on_nonempty": nonempty == converter_nonempty if converter_payload is not None else None,
                "shared_producer_dependence": True,
                "shared_producer_reason": "parser and converter are the same deontic package; agreement is not semantic accuracy",
                "implementation_agreement_is_not_semantic_accuracy": True,
            },
            "independent_span_checker_agrees_with_source_hashes": row["source_span_linkage"]["linked"],
        }
        row["machine_contract_outcome"] = {
            "checked_property": CHECKED_PROPERTY["legal"],
            "satisfied": bool(row["source_span_linkage"]["linked"] and schema["valid"]),
            "reason": "span_linkage_and_schema_conformance",
            "implementation_agreement_is_not_semantic_accuracy": True,
            "reference_producer": "la-027-automated-reference-manifest",
        }
        return row
    except Exception as exc:
        row["status"] = "failed"
        row["failure"] = {
            "code": "legal_adapter_error",
            "message": bounded_error(exc),
            "trace": traceback.format_exc(limit=8),
        }
        row["parse_schema_validity"] = {"valid": False, "reason": "adapter_error"}
        row["supported_unsupported_fields"] = {"supported": [], "unsupported": ["adapter_output"]}
        row["compiler_checker"] = {"ran": False, "reason": "adapter_error"}
        row["machine_contract_outcome"] = {
            "checked_property": CHECKED_PROPERTY["legal"],
            "satisfied": False,
            "reason": "adapter_failed",
            "implementation_agreement_is_not_semantic_accuracy": True,
        }
        return row


def measure_skill(record: Mapping[str, Any], family: Mapping[str, Any]) -> dict[str, Any]:
    case_id = record["case_id"]
    source = record.get("source") if isinstance(record.get("source"), Mapping) else {}
    markdown = skill_markdown(record)
    reconstructed = reconstruct_span_text(record.get("source_spans"))
    row = base_row(family, case_id, mutation_class=record.get("mutation_class"))
    row["adapter"] = {
        "id": "skillcenter-intent-normalizer",
        "symbol": "SkillCenterIntentNormalizer.normalize_with_diagnostics",
        "module": "ipfs_datasets_py.logic.intent_ir.normalize.skill",
        "version": None,
    }
    row["source_span_linkage"] = span_linkage_record(record.get("source_spans"), reconstructed)
    row["input"] = {
        "annotation_id": record.get("annotation_id"),
        "skill_id": source.get("skill_id"),
        "bundle_sha256": source.get("bundle_sha256"),
        "content_sha256": source.get("content_sha256"),
        "span_reconstruction": {key: reconstructed[key] for key in reconstructed if key != "text"},
        "reconstructed_markdown_sha256": sha256_text(markdown) if markdown else None,
        "full_bundle_body": "retrieval_only_not_redistributed",
        "independent_label_used": False,
        "packet_preparer_intent_nodes_used_as_gold": False,
        "source_contains_markdown_commands": record.get("source_contains_markdown_commands"),
        "synthetic_mutation": bool(record.get("synthetic")),
    }
    if not markdown:
        row["status"] = "unavailable"
        row["failure"] = {"code": "empty_quoted_source", "message": "skill record has no quoted Markdown spans"}
        row["parse_schema_validity"] = {"valid": False, "reason": "no_source_text"}
        row["supported_unsupported_fields"] = {"supported": [], "unsupported": ["quoted_source_text"]}
        row["compiler_checker"] = {"ran": False, "reason": "no_source_text"}
        row["machine_contract_outcome"] = {
            "checked_property": CHECKED_PROPERTY["skill"],
            "satisfied": False,
            "reason": "source_unavailable",
            "implementation_agreement_is_not_semantic_accuracy": True,
        }
        return row
    try:
        from ipfs_datasets_py.logic.intent_ir.normalize.skill import (
            INTENT_NORMALIZER_VERSION,
            SkillCenterIntentNormalizer,
            SkillNormalizationPolicyError,
        )
        from ipfs_datasets_py.logic.intent_ir.source_adapters.skillcenter import SkillCenterSkillRecord

        row["adapter"]["version"] = INTENT_NORMALIZER_VERSION
        identity = record.get("identity") if isinstance(record.get("identity"), Mapping) else {}
        metadata_lines = [
            f"title: {source.get('title') or record.get('annotation_id') or case_id}",
            f"license: {source.get('license_expression') or 'MIT'}",
            f"license_spdx: {source.get('license_expression') or 'MIT'}",
            f"license_risk: {source.get('license_risk') or 'allow'}",
        ]
        skill_record = SkillCenterSkillRecord(
            skill_id=str(source.get("skill_id") or identity.get("skill_id") or case_id),
            domain=str(source.get("domain") or "security"),
            profile=str(source.get("profile") or "security"),
            source_type=str(source.get("source_type") or "github"),
            source_url=str(source.get("source_url") or source.get("source_uri") or "https://example.invalid/skill"),
            title=str(source.get("title") or "frozen-skill"),
            overall_score=4.0 if source.get("overall_score") is None else source.get("overall_score"),
            skill_kind=str(source.get("skill_kind") or "github"),
            language=str(source.get("language") or "en"),
            source_id=str(source.get("source_id") or family["source_id"]),
            primary_source_id=str(source.get("primary_source_id") or source.get("skill_id") or case_id),
            metadata_yaml="\n".join(metadata_lines) + "\n",
            skill_md=markdown,
            library_md="",
            dataset_id=str(source.get("dataset_id") or "Tommysha/skillcenter-bundles"),
            dataset_revision=str(source.get("dataset_revision") or "f9dd4fec3c86d85ebf116c7408ac5ce602c418a1"),
            repository_file=str(source.get("repository_file") or "clawskills-bundle-lite-security-v20260227.sqlite"),
            bundle_sha256=str(source.get("bundle_sha256") or "8b763be5896b12510c38b92459325d9568770d99cf38aa53ab17485b456d82a4"),
        )
        try:
            result = SkillCenterIntentNormalizer().normalize_with_diagnostics(skill_record)
        except SkillNormalizationPolicyError as exc:
            policy = exc.decision.to_dict() if hasattr(exc, "decision") else None
            row["status"] = "unsupported"
            row["failure"] = {
                "code": "skill_policy_blocked",
                "message": bounded_error(exc),
                "policy": policy,
            }
            row["parse_schema_validity"] = {"valid": False, "reason": "policy_blocked_before_ir"}
            row["supported_unsupported_fields"] = {
                "supported": ["source_span_linkage"] if row["source_span_linkage"]["linked"] else [],
                "unsupported": ["intent_ir_document_policy_excluded"],
            }
            row["compiler_checker"] = {
                "ran": False,
                "reason": "policy_blocked",
                "untrusted_markdown_executed": False,
            }
            row["prediction"] = {
                "kind": "skill_intent_ir_policy_excluded",
                "untrusted_markdown_executed": False,
                "authority": "non_authoritative_adapter_output",
                "independent_human_gold": False,
            }
            row["machine_contract_outcome"] = {
                "checked_property": CHECKED_PROPERTY["skill"],
                "satisfied": bool(row["source_span_linkage"]["linked"]),
                "reason": "span_linkage_recorded_ir_unsupported_by_source_policy",
                "implementation_agreement_is_not_semantic_accuracy": True,
                "reference_producer": "la-027-automated-reference-manifest",
            }
            return row
        document = result.to_dict()["document"]
        decoder_status: dict[str, Any]
        try:
            from ipfs_datasets_py.logic.intent_ir.decoder import decode_intent_ir
            from ipfs_datasets_py.logic.intent_ir.schema import validate_intent_ir

            decoded = decode_intent_ir(document)
            validated = validate_intent_ir(decoded)
            decoder_status = {
                "valid": True,
                "schema_version": validated.schema_version,
                "document_id": validated.document_id,
                "checker": {
                    "id": "intent-ir-decoder-and-schema",
                    "modules": [
                        "ipfs_datasets_py.logic.intent_ir.decoder",
                        "ipfs_datasets_py.logic.intent_ir.schema",
                    ],
                    "distinct_from_evaluated_adapter": True,
                    "evaluated_adapter": "ipfs_datasets_py.logic.intent_ir.normalize.skill",
                },
            }
        except Exception as exc:
            decoder_status = {
                "valid": False,
                "error": bounded_error(exc),
                "checker": {
                    "id": "intent-ir-decoder-and-schema",
                    "distinct_from_evaluated_adapter": True,
                },
            }
        typed_status: dict[str, Any]
        try:
            from ipfs_datasets_py.logic.intent_ir.formalize.typed_compiler import IntentFormalizationCompiler

            compiler = IntentFormalizationCompiler()
            receipt = compiler.route_view("skill", source_kind="declaration", fail_on_unsupported=False)
            typed_status = {
                "available": True,
                "interface": compiler.interface,
                "version": compiler.version,
                "route_id": getattr(receipt, "route_id", None) or str(getattr(receipt, "route", None)),
                "producer": "intent-ir-typed-compiler",
                "distinct_from_evaluated_adapter": True,
            }
        except Exception as exc:
            typed_status = {"available": False, "error": bounded_error(exc), "selected": False}
        row["status"] = "prediction"
        row["prediction"] = {
            "kind": "skill_intent_ir",
            "document_id": document.get("document_id"),
            "schema_version": document.get("schema_version"),
            "statement_count": len(document.get("statements") or []),
            "action_count": len(document.get("actions") or []),
            "control_edge_count": len(document.get("control_edges") or []),
            "diagnostic_count": len(result.diagnostics),
            "document_sha256": digest(document),
            "normalizer_version": result.normalizer_version,
            "authority": "non_authoritative_adapter_output",
            "independent_review": "not_used",
            "independent_human_gold": False,
            "untrusted_markdown_executed": False,
        }
        row["parse_schema_validity"] = decoder_status
        row["supported_unsupported_fields"] = {
            "supported": [name for name, count in (
                ("statements", len(document.get("statements") or [])),
                ("actions", len(document.get("actions") or [])),
                ("control_edges", len(document.get("control_edges") or [])),
            ) if count],
            "unsupported": [name for name, count in (
                ("actions", len(document.get("actions") or [])),
                ("control_edges", len(document.get("control_edges") or [])),
            ) if not count],
        }
        row["compiler_checker"] = {
            "normalizer": {"ran": True, "producer": "skillcenter-intent-normalizer"},
            "independent_schema_checker": decoder_status,
            "typed_compiler": typed_status,
            "implementation_consistency": {
                "normalizer_and_independent_decoder_agree": decoder_status.get("valid") is True,
                "shared_producer_dependence": False,
                "implementation_agreement_is_not_semantic_accuracy": True,
                "note": "decoder/schema validate the produced document; they do not score intent fidelity against packet-preparer nodes",
            },
            "untrusted_markdown_executed": False,
        }
        row["machine_contract_outcome"] = {
            "checked_property": CHECKED_PROPERTY["skill"],
            "satisfied": bool(row["source_span_linkage"]["linked"] and decoder_status.get("valid")),
            "reason": "span_linkage_and_intent_ir_schema_conformance",
            "implementation_agreement_is_not_semantic_accuracy": True,
            "reference_producer": "la-027-automated-reference-manifest",
        }
        return row
    except Exception as exc:
        row["status"] = "failed"
        row["failure"] = {
            "code": "skill_adapter_error",
            "message": bounded_error(exc),
            "trace": traceback.format_exc(limit=8),
        }
        row["parse_schema_validity"] = {"valid": False, "reason": "adapter_error"}
        row["supported_unsupported_fields"] = {"supported": [], "unsupported": ["adapter_output"]}
        row["compiler_checker"] = {"ran": False, "reason": "adapter_error"}
        row["machine_contract_outcome"] = {
            "checked_property": CHECKED_PROPERTY["skill"],
            "satisfied": False,
            "reason": "adapter_failed",
            "implementation_agreement_is_not_semantic_accuracy": True,
        }
        return row


def measure_cve(pair: Mapping[str, Any], family: Mapping[str, Any], case_id: str, side: str, polarity: Mapping[str, Any] | None) -> dict[str, Any]:
    restriction = pair.get("restriction_candidate") if isinstance(pair.get("restriction_candidate"), Mapping) else {}
    side_payload = ((pair.get("sides") or {}).get(side) if isinstance(pair.get("sides"), Mapping) else {}) or {}
    reconstructed = reconstruct_span_text(side_payload.get("source_spans"))
    row = base_row(family, case_id, mutation_class=(pair.get("mutation_classes") or {}).get(side))
    row["cve_side"] = side
    row["adapter"] = {
        "id": "cvefixes-security-ir-adapter",
        "symbol": "adapt_cvefixes_candidate",
        "module": "ipfs_datasets_py.logic.security_ir.cvefixes.adapter",
        "version": None,
    }
    row["source_span_linkage"] = span_linkage_record(side_payload.get("source_spans"), reconstructed)
    contract = (polarity or {}).get("behavior_contract") if isinstance(polarity, Mapping) else None
    observation = (contract or {}).get("observation") if isinstance(contract, Mapping) else None
    evidence = pair.get("supported_behavior_evidence") if isinstance(pair.get("supported_behavior_evidence"), Mapping) else {}
    isolated = evidence.get("isolated_reproduction") if isinstance(evidence.get("isolated_reproduction"), Mapping) else {}
    behavior = evidence.get("source_supported_behavior") if isinstance(evidence.get("source_supported_behavior"), Mapping) else {}
    row["cve_behavior"] = {
        "independent_producer": compact_mapping((contract or {}).get("producer") or {}, keys=(
            "id", "kind", "version", "distinct_from_evaluated_adapter", "evaluated_adapter",
            "not_cvefixes_adapter_output", "not_human_gold", "generated_labels_are",
        )),
        "checked_property": (contract or {}).get("checked_property") or "source_difference_at_pinned_revisions",
        "la027_checked_property": CHECKED_PROPERTY["cve"],
        "observation": compact_mapping(observation or isolated, keys=(
            "status", "kind", "source_difference_observed", "executed_untrusted_source",
            "vulnerable_revision", "fixed_revision", "runnable_sandbox_reproduction",
            "observer", "effect_observed",
        )),
        "polarity_expected": (polarity or {}).get("expected", "unknown"),
        "polarity_supported_by_contract": (contract or {}).get("polarity_supported_by_contract"),
        "empirical_success_credit": (polarity or {}).get("empirical_success_credit"),
        "transfer_to_export_json": behavior.get("transfer_to_export_json") or isolated.get("la008_export_json_transfer"),
        "untrusted_source_executed": bool(isolated.get("executed_untrusted_source") or pair.get("untrusted_source_executed")),
        "independent_human_gold": False,
    }
    source_difference = bool(
        (observation or {}).get("source_difference_observed")
        or isolated.get("status") == "source_difference_observed_at_pinned_revisions"
        or (observation or {}).get("status") == "source_difference_observed_at_pinned_revisions"
    )
    polarity_unknown = (polarity or {}).get("expected", "unknown") == "unknown"
    behavior_contract_satisfied = bool(source_difference and polarity_unknown)
    row["input"] = {
        "restriction_status": restriction.get("status"),
        "restriction_authoritative": restriction.get("authoritative"),
        "restriction_mapping_status": restriction.get("mapping_status"),
        "cve_ids": restriction.get("cve_ids"),
        "pair_id": pair.get("pair_id"),
        "independent_label_used": False,
        "independent_polarity": (polarity or {}).get("expected", "unknown"),
        "span_reconstruction": {key: reconstructed[key] for key in reconstructed if key != "text"},
    }
    if restriction.get("authoritative") is True or restriction.get("grants_execution_authority") is True:
        row["status"] = "failed"
        row["failure"] = {
            "code": "refused_authoritative_packet_preparer_candidate",
            "message": "packet-preparer restriction candidates cannot grant execution authority",
        }
        row["parse_schema_validity"] = {"valid": False, "reason": "refused_authoritative_candidate"}
        row["supported_unsupported_fields"] = {"supported": [], "unsupported": ["execution_authority"]}
        row["compiler_checker"] = {"ran": False, "reason": "refused_authoritative_candidate"}
        row["machine_contract_outcome"] = {
            "checked_property": CHECKED_PROPERTY["cve"],
            "satisfied": False,
            "reason": "authoritative_candidate_refused",
            "implementation_agreement_is_not_semantic_accuracy": True,
        }
        return row
    try:
        from ipfs_datasets_py.logic.security_ir.cvefixes.adapter import (
            CVEFIXES_ADAPTER_VERSION,
            CandidateReview,
            CandidateReviewState,
            adapt_cvefixes_candidate,
        )
        from ipfs_datasets_py.logic.security_ir.cvefixes.schemas import PolicyCandidate, SourceRecord
        from ipfs_datasets_py.logic.security_ir.cvefixes.vocabulary import CVEFIXES_POLICY_ATTRIBUTES_KEY

        row["adapter"]["version"] = CVEFIXES_ADAPTER_VERSION
        config_cid = canonical_cid(
            {
                "adapter": CVEFIXES_ADAPTER_VERSION,
                "source_id": family["source_id"],
                "task": TASK,
                "case_id": case_id,
            },
            domain="cvefixes-security-ir/config",
        )
        source_record = SourceRecord(
            source_uri="https://huggingface.co/datasets/hitoshura25/cvefixes/resolve/d4f5c4ea65329d9ccbb8a3b3149e5d06eda5edb2/data/train-00000-of-00003.parquet",
            source_revision="d4f5c4ea65329d9ccbb8a3b3149e5d06eda5edb2",
            row_key=family["source_id"],
            source_cids=(config_cid,),
            parent_cids=(config_cid,),
            config_cid=config_cid,
            payload={"lineage_family_id": family["lineage_family_id"], "split": family["split"], "case_id": case_id},
        )
        attributes = cve_attributes(restriction)
        candidate = PolicyCandidate(
            effect="deny",
            scope={CVEFIXES_POLICY_ATTRIBUTES_KEY: attributes},
            source_cids=(source_record.record_id,),
            parent_cids=(source_record.record_id,),
            config_cid=config_cid,
            payload={"pair_id": pair.get("pair_id"), "authoritative": False, "case_id": case_id},
        )
        review = CandidateReview(
            state=CandidateReviewState.OBSERVED_CANDIDATE,
            review_id="",
            reviewer_id="",
            attributes={
                "independent_review": "not_used",
                "packet_preparer": True,
                "independent_human_gold": False,
                "evidence_scope": EVIDENCE_SCOPE,
            },
        )
        adapted = adapt_cvefixes_candidate(candidate, sources=[source_record], review=review)
        adapted_dict = adapted.to_dict()
        declaration = adapted_dict.get("declaration") if isinstance(adapted_dict, Mapping) else None
        schema_valid = isinstance(adapted_dict, Mapping) and bool(adapted.adapter_version)
        formalization_status: dict[str, Any]
        try:
            from ipfs_datasets_py.logic.security_ir.formalization_adapter import (
                SECURITY_IR_FORMALIZATION_ADAPTER_VERSION,
            )

            formalization_status = {
                "available": True,
                "version": SECURITY_IR_FORMALIZATION_ADAPTER_VERSION,
                "applied": False,
                "reason": "declaration_is_observed_candidate_not_authoritative_security_ir",
            }
        except Exception as exc:
            formalization_status = {"available": False, "error": bounded_error(exc)}
        row["status"] = "prediction"
        row["prediction"] = {
            "kind": "cvefixes_security_ir_observed_candidate",
            "adapter_version": adapted.adapter_version,
            "candidate_cid": candidate.record_id,
            "source_record_id": source_record.record_id,
            "declaration_sha256": digest(declaration),
            "review_state": review.state.value,
            "grants_execution_authority": False,
            "proof_authoritative": False,
            "authority": "observed_candidate_not_independent_review",
            "independent_review": "not_used",
            "independent_human_gold": False,
        }
        row["parse_schema_validity"] = {
            "valid": schema_valid,
            "reason": "ok" if schema_valid else "missing_adapter_declaration",
            "checker": {
                "id": "la-009-cvefixes-adapter-schema-checker",
                "distinct_from_independent_behavior_contract": True,
            },
        }
        row["supported_unsupported_fields"] = {
            "supported": ["source_difference_observation"] if source_difference else [],
            "unsupported": [
                name
                for name, flag in (
                    ("evaluation_polarity", True),
                    ("export_json_transfer", row["cve_behavior"]["transfer_to_export_json"] in {None, "unsupported"}),
                    ("native_sink_execution", not row["cve_behavior"]["untrusted_source_executed"]),
                )
                if flag
            ],
        }
        row["compiler_checker"] = {
            "adapter": {"ran": True, "producer": "cvefixes-security-ir-adapter"},
            "independent_behavior_contract": {
                "producer": ((contract or {}).get("producer") or {}).get("id") or "la-006-scoped-behavior-contract-compiler",
                "distinct_from_evaluated_adapter": True,
                "source_difference_observed": source_difference,
                "polarity_unknown": (polarity or {}).get("expected", "unknown") == "unknown",
            },
            "formalization_adapter": formalization_status,
            "implementation_consistency": {
                "shared_producer_dependence": False,
                "paired_independent_observation": True,
                "implementation_agreement_is_not_semantic_accuracy": True,
                "note": "adapter schema validity and LA-026/LA-006 source-difference observation are distinct properties",
            },
        }
        row["machine_contract_outcome"] = {
            "checked_property": CHECKED_PROPERTY["cve"],
            "satisfied": behavior_contract_satisfied,
            "reason": "source_supported_behavior_observation_with_unknown_polarity",
            "implementation_agreement_is_not_semantic_accuracy": True,
            "reference_producer": ((contract or {}).get("producer") or {}).get("id") or "la-006-scoped-behavior-contract-compiler",
            "polarity_not_scored": True,
            "adapter_schema_valid": schema_valid,
        }
        return row
    except Exception as exc:
        row["status"] = "failed"
        row["failure"] = {
            "code": "cve_adapter_error",
            "message": bounded_error(exc),
            "trace": traceback.format_exc(limit=8),
        }
        row["parse_schema_validity"] = {"valid": False, "reason": "adapter_error"}
        row["supported_unsupported_fields"] = {
            "supported": ["source_difference_observation"] if source_difference else [],
            "unsupported": ["adapter_output", "evaluation_polarity"],
        }
        row["compiler_checker"] = {
            "ran": False,
            "reason": "adapter_error",
            "independent_behavior_contract": {
                "producer": ((contract or {}).get("producer") or {}).get("id") or "la-006-scoped-behavior-contract-compiler",
                "distinct_from_evaluated_adapter": True,
                "source_difference_observed": source_difference,
                "polarity_unknown": polarity_unknown,
            },
        }
        row["machine_contract_outcome"] = {
            "checked_property": CHECKED_PROPERTY["cve"],
            "satisfied": behavior_contract_satisfied,
            "reason": "independent_behavior_observation_retained_after_adapter_failure",
            "implementation_agreement_is_not_semantic_accuracy": True,
            "reference_producer": ((contract or {}).get("producer") or {}).get("id") or "la-006-scoped-behavior-contract-compiler",
            "polarity_not_scored": True,
            "adapter_schema_valid": False,
        }
        return row


def inventory_splits(splits: Mapping[str, Any]) -> dict[str, Any]:
    families = []
    case_ids = []
    split_counts = {name: 0 for name in EXPECTED_SPLIT_FAMILIES}
    population_families = {name: 0 for name in EXPECTED_POPULATION_FAMILIES}
    population_cases = {name: 0 for name in EXPECTED_POPULATION_CASES}
    for row in splits.get("assignments") or []:
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
    complete = (
        len(families) == EXPECTED_FAMILIES
        and len(case_ids) == EXPECTED_CASES
        and len(set(case_ids)) == EXPECTED_CASES
        and split_counts == EXPECTED_SPLIT_FAMILIES
        and population_families == EXPECTED_POPULATION_FAMILIES
        and population_cases == EXPECTED_POPULATION_CASES
        and all(len(family["planned_case_ids"]) == 2 for family in families)
    )
    if not complete:
        raise MeasurementError("frozen split inventory does not match the original 30-family/60-case cohort")
    return {
        "families": families,
        "case_ids": case_ids,
        "split_family_counts": split_counts,
        "population_family_counts": population_families,
        "population_case_counts": population_cases,
        "complete": True,
    }


def index_by_case(rows: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        case_id = row.get("case_id")
        if isinstance(case_id, str) and case_id:
            indexed[case_id] = dict(row)
    return indexed


def derive_metrics(rows: list[Mapping[str, Any]], *, inventory: Mapping[str, Any], pins: Mapping[str, Any], runtime: Mapping[str, Any], excluded_controls: list[str], raw_sha256: str) -> dict[str, Any]:
    if len(rows) != EXPECTED_CASES:
        raise MeasurementError(f"expected {EXPECTED_CASES} case records, found {len(rows)}")
    got = [row["case_id"] for row in rows]
    if sorted(got) != sorted(inventory["case_ids"]):
        raise MeasurementError("case identities drifted from the frozen split reservation")
    status_counts = Counter(row.get("status") for row in rows)
    by_population: dict[str, dict[str, Any]] = {}
    by_split: dict[str, dict[str, Any]] = {}
    for key, field in (("legal", "population"), ("cve", "population"), ("skill", "population"), ("development", "split"), ("calibration", "split"), ("final", "split")):
        group = [row for row in rows if row.get(field) == key]
        target = by_population if field == "population" else by_split
        target[key] = {
            "cases": len(group),
            "prediction": sum(1 for row in group if row.get("status") == "prediction"),
            "failed": sum(1 for row in group if row.get("status") == "failed"),
            "unavailable": sum(1 for row in group if row.get("status") == "unavailable"),
            "unsupported": sum(1 for row in group if row.get("status") == "unsupported"),
            "span_linked": sum(1 for row in group if (row.get("source_span_linkage") or {}).get("linked")),
            "schema_valid": sum(1 for row in group if (row.get("parse_schema_validity") or {}).get("valid")),
            "machine_contract_satisfied": sum(1 for row in group if (row.get("machine_contract_outcome") or {}).get("satisfied")),
        }
    span_linked = sum(1 for row in rows if (row.get("source_span_linkage") or {}).get("linked"))
    schema_valid = sum(1 for row in rows if (row.get("parse_schema_validity") or {}).get("valid"))
    contract_ok = sum(1 for row in rows if (row.get("machine_contract_outcome") or {}).get("satisfied"))
    legal_shared = [
        row
        for row in rows
        if row.get("population") == "legal"
        and ((row.get("compiler_checker") or {}).get("implementation_consistency") or {}).get("both_ran")
    ]
    legal_agree = sum(
        1
        for row in legal_shared
        if ((row.get("compiler_checker") or {}).get("implementation_consistency") or {}).get("agree_on_nonempty")
    )
    skill_independent = [
        row
        for row in rows
        if row.get("population") == "skill" and row.get("status") == "prediction"
    ]
    skill_agree = sum(
        1
        for row in skill_independent
        if ((row.get("compiler_checker") or {}).get("implementation_consistency") or {}).get("normalizer_and_independent_decoder_agree")
    )
    cve_rows = [row for row in rows if row.get("population") == "cve"]
    cve_diff = sum(1 for row in cve_rows if ((row.get("cve_behavior") or {}).get("observation") or {}).get("source_difference_observed") or ((row.get("cve_behavior") or {}).get("observation") or {}).get("status") == "source_difference_observed_at_pinned_revisions")
    cve_unknown = sum(1 for row in cve_rows if (row.get("cve_behavior") or {}).get("polarity_expected") == "unknown")
    cve_supported_polarity = sum(1 for row in cve_rows if (row.get("cve_behavior") or {}).get("polarity_supported_by_contract") is True)
    cve_executed = sum(1 for row in cve_rows if (row.get("cve_behavior") or {}).get("untrusted_source_executed"))
    cve_transfer = sum(1 for row in cve_rows if (row.get("cve_behavior") or {}).get("transfer_to_export_json") in {None, "unsupported"})
    withdrawn = {
        name: {
            "numeric_score_assigned": False,
            "status": "unmeasured",
            "denominator_restricted": True,
            "reason": "withdrawn_without_independent_data",
        }
        for name in WITHDRAWN
    }
    return {
        "schema": METRICS_SCHEMA,
        "task": TASK,
        "pipeline_version": PIPELINE_VERSION,
        "evidence_scope": EVIDENCE_SCOPE,
        "derived_from": "papers/completion/law_to_action/results/source_ir/raw.jsonl",
        "raw_sha256": raw_sha256,
        "generated_at": utc_now(),
        "runtime": runtime,
        "pins": pins,
        "frozen_population": {
            "families": EXPECTED_FAMILIES,
            "cases": EXPECTED_CASES,
            "split_family_counts": inventory["split_family_counts"],
            "population_family_counts": inventory["population_family_counts"],
            "population_case_counts": inventory["population_case_counts"],
            "splits_sha256": pins["splits.json"]["sha256"],
            "sources_sha256": pins["sources.json"]["sha256"],
            "original_protocol_sha256": ORIGINAL_PROTOCOL_SHA256,
            "cohorts_changed_after_outcomes": False,
            "complete": True,
        },
        "case_accounting": {
            "denominator": EXPECTED_CASES,
            "records": len(rows),
            "prediction": status_counts.get("prediction", 0),
            "failed": status_counts.get("failed", 0),
            "unavailable": status_counts.get("unavailable", 0),
            "unsupported": status_counts.get("unsupported", 0),
            "missing": 0,
            "every_frozen_case_recorded": True,
        },
        "by_population": by_population,
        "by_split": by_split,
        "metrics": {
            "source_span_linkage_coverage": {
                **rate(span_linked, EXPECTED_CASES),
                "property": "quoted_span_hash_linkage",
                "independent_checker": "la-009-quoted-span-hash-checker",
            },
            "parse_schema_validity": {
                **rate(schema_valid, EXPECTED_CASES),
                "property": "adapter_or_independent_schema_conformance",
                "note": "schema validity is not semantic accuracy",
            },
            "machine_contract_coverage": {
                **rate(contract_ok, EXPECTED_CASES),
                "property": "exact_scoped_machine_expectation",
                "reference_producers": [
                    "la-027-automated-reference-manifest",
                    "la-006-scoped-behavior-contract-compiler",
                ],
            },
            "compiler_checker_consistency": {
                "legal_parser_converter_both_ran": rate(len(legal_shared), by_population["legal"]["cases"]),
                "legal_parser_converter_nonempty_agreement": {
                    **rate(legal_agree, len(legal_shared) or 0),
                    "shared_producer_dependence": True,
                    "implementation_agreement_is_not_semantic_accuracy": True,
                    "note": "same deontic package; not expert legal fidelity",
                },
                "skill_normalizer_independent_decoder_agreement": {
                    **rate(skill_agree, len(skill_independent) or 0),
                    "shared_producer_dependence": False,
                    "independent_checker": "intent-ir-decoder-and-schema",
                    "implementation_agreement_is_not_semantic_accuracy": True,
                },
                "cve_adapter_paired_with_independent_behavior_observation": {
                    **rate(cve_diff, len(cve_rows)),
                    "shared_producer_dependence": False,
                    "independent_producer": "la-006-scoped-behavior-contract-compiler",
                },
            },
            "cve_source_supported_behavior": {
                "denominator": len(cve_rows),
                "source_difference_observed": cve_diff,
                "source_difference_observed_rate": rate(cve_diff, len(cve_rows)),
                "polarity_unknown": cve_unknown,
                "polarity_supported_by_contract": cve_supported_polarity,
                "untrusted_source_executed": cve_executed,
                "transfer_unsupported": cve_transfer,
                "polarity_accuracy_not_scored": True,
                "independent_producer": "la-006-scoped-behavior-contract-compiler",
                "note": "source-difference observation is not vulnerable/fixed detection accuracy",
            },
        },
        "withdrawn_unmeasured": withdrawn,
        "synthetic_qualification_controls": {
            "included_in_frozen_denominator": False,
            "excluded_case_ids": excluded_controls,
            "count": len(excluded_controls),
            "reason": "extra skill_claims_authorization and command_execution_bait rows are synthetic qualification controls, not frozen selected cases",
        },
        "human_review_run_dependency": False,
        "independent_human_gold": False,
        "implementation_agreement_is_not_semantic_accuracy": True,
        "generated_labels_are": GENERATED_LABELS,
        "empirical_benchmark_result": True,
        "held_out_expert_fidelity_inferred": False,
        "useful_work_success_inferred_from_fixtures": False,
    }


def render_failure_review(rows: list[Mapping[str, Any]], metrics: Mapping[str, Any], excluded_controls: list[str]) -> str:
    failures = [row for row in rows if row.get("status") in {"failed", "unavailable", "unsupported"}]
    lines = [
        "# LA-009 source-to-IR failure and scope review",
        "",
        "This review accounts for every frozen selected case. It does not assign",
        "expert legal fidelity, human agreement, or semantic accuracy scores.",
        "",
        "## Frozen cohort",
        "",
        f"- Families: {EXPECTED_FAMILIES}; cases: {EXPECTED_CASES}.",
        f"- Splits SHA-256: `{metrics['frozen_population']['splits_sha256']}`.",
        f"- Sources SHA-256: `{metrics['frozen_population']['sources_sha256']}`.",
        f"- Original protocol SHA-256: `{ORIGINAL_PROTOCOL_SHA256}`.",
        "- Cohorts were not changed after outcomes.",
        "",
        "## Case accounting",
        "",
        f"- Records: {metrics['case_accounting']['records']}/{metrics['case_accounting']['denominator']}.",
        f"- Predictions: {metrics['case_accounting']['prediction']}.",
        f"- Failed: {metrics['case_accounting']['failed']}.",
        f"- Unavailable: {metrics['case_accounting']['unavailable']}.",
        f"- Unsupported: {metrics['case_accounting']['unsupported']}.",
        f"- Missing: {metrics['case_accounting']['missing']}.",
        "",
        "## Machine-contract metrics",
        "",
        f"- Source-span linkage: {metrics['metrics']['source_span_linkage_coverage']['formula']}.",
        f"- Parse/schema validity: {metrics['metrics']['parse_schema_validity']['formula']}.",
        f"- Scoped machine-contract coverage: {metrics['metrics']['machine_contract_coverage']['formula']}.",
        "- Implementation agreement is not semantic accuracy.",
        "",
        "## CVE source-supported behavior",
        "",
        f"- Source-difference observations: {metrics['metrics']['cve_source_supported_behavior']['source_difference_observed']}/{metrics['metrics']['cve_source_supported_behavior']['denominator']}.",
        f"- Polarity unknown: {metrics['metrics']['cve_source_supported_behavior']['polarity_unknown']}.",
        f"- Polarity supported by contract: {metrics['metrics']['cve_source_supported_behavior']['polarity_supported_by_contract']}.",
        f"- Untrusted source executed: {metrics['metrics']['cve_source_supported_behavior']['untrusted_source_executed']}.",
        f"- Transfer to export_json unsupported: {metrics['metrics']['cve_source_supported_behavior']['transfer_unsupported']}.",
        "- Independent producer: `la-006-scoped-behavior-contract-compiler` (distinct from the CVEfixes adapter).",
        "",
        "## Failed, unavailable, and unsupported records",
        "",
    ]
    if not failures:
        lines.append("No frozen selected case failed, was unavailable, or was unsupported.")
        lines.append("")
    else:
        lines.append("| case_id | population | split | status | code |")
        lines.append("| --- | --- | --- | --- | --- |")
        for row in failures:
            code = ((row.get("failure") or {}).get("code")) or ((row.get("machine_contract_outcome") or {}).get("reason")) or "unspecified"
            lines.append(
                f"| `{row['case_id']}` | {row['population']} | {row['split']} | {row['status']} | `{code}` |"
            )
        lines.append("")
        for row in failures:
            message = ((row.get("failure") or {}).get("message")) or ""
            lines.extend(
                [
                    f"### `{row['case_id']}`",
                    "",
                    f"- Status: `{row['status']}`.",
                    f"- Population/split: {row['population']}/{row['split']}.",
                    f"- Mutation: `{row.get('mutation_class')}`.",
                    f"- Message: {message or 'n/a'}.",
                    "",
                ]
            )
    lines.extend(
        [
            "## Shared-producer dependence",
            "",
            "- Legal parser vs DeonticConverter agreement is same-package implementation consistency, not expert legal fidelity.",
            "- Skill decoder/schema checks are independent of the SkillCenter normalizer.",
            "- CVE behavior observations come from LA-006/LA-026 contracts, not from the CVEfixes adapter under evaluation.",
            "- Packet-preparer atoms and intent nodes were not used as independent gold.",
            "",
            "## Synthetic qualification controls excluded from the frozen denominator",
            "",
            f"- Count: {len(excluded_controls)}.",
            "- These `skill_claims_authorization` and `command_execution_bait` rows are not planned case identities.",
            "- LA-008 fixture smokes are also outside this empirical cohort.",
            "",
        ]
    )
    if excluded_controls:
        for case_id in excluded_controls:
            lines.append(f"- `{case_id}`")
        lines.append("")
    lines.extend(
        [
            "## Withdrawn unmeasured claims",
            "",
            "- Expert legal applicability/exception fidelity: unmeasured; no numeric score.",
            "- Inter-annotator agreement and independent human validation: unmeasured; no numeric score.",
            "- Legal applicability or validity in the world: unmeasured; no numeric score.",
            "- Semantic accuracy inferred from implementation agreement: not assigned.",
            "- Human/author review was not a run dependency.",
            "",
        ]
    )
    return "\n".join(lines)


def copy_outputs(raw_rows: list[Mapping[str, Any]], metrics: Mapping[str, Any], review: str) -> None:
    live = LIVE / "results" / "source_ir"
    snap = SNAPSHOT / "outputs" / "results" / "source_ir"
    for directory in (live, snap):
        write_jsonl(directory / "raw.jsonl", raw_rows)
        write_json(directory / "metrics.json", metrics)
        write_text(directory / "failure_review.md", review)


def run() -> dict[str, Any]:
    sources = pin_path(BENCHMARK / "manifests" / "sources.json")
    splits_pin = pin_path(BENCHMARK / "manifests" / "splits.json")
    if splits_pin["sha256"] != EXPECTED_SPLITS_SHA256:
        raise MeasurementError("splits.json hash drifted from the frozen LA-027 cohort pin")
    if sources["sha256"] != EXPECTED_SOURCES_SHA256:
        raise MeasurementError("sources.json hash drifted from the frozen LA-027 cohort pin")
    splits = load_json(BENCHMARK / "manifests" / "splits.json")
    inventory = inventory_splits(splits)
    families = {row["lineage_family_id"]: row for row in inventory["families"]}
    reference = load_json(BENCHMARK / "annotations" / "automated_reference_manifest.json")
    if len(reference.get("cases") or []) != EXPECTED_CASES:
        raise MeasurementError("automated reference manifest does not cover 60 frozen cases")
    legal = index_by_case(load_jsonl(BENCHMARK / "annotations" / "legal.jsonl"))
    skills = index_by_case(load_jsonl(BENCHMARK / "annotations" / "skills.jsonl"))
    adversarial = load_jsonl(BENCHMARK / "cases" / "skill_adversarial.jsonl")
    reserved_mutations = {row["case_id"]: row for row in adversarial if row.get("case_id") in set(inventory["case_ids"])}
    excluded_controls = sorted(
        {
            str(row.get("case_id"))
            for row in adversarial
            if row.get("case_id") and row.get("case_id") not in set(inventory["case_ids"])
        }
    )
    cve_pairs = {row["lineage_family_id"]: row for row in load_jsonl(BENCHMARK / "cases" / "cve_pairs.jsonl")}
    polarity_rows = load_jsonl(ROOT / "papers/completion/law_to_action/receipts/snapshots/LA-006/polarity_contracts.jsonl")
    polarity = {row["subject_id"]: row for row in polarity_rows if row.get("subject_kind") == "pair_side"}
    pins = {
        "sources.json": sources,
        "splits.json": splits_pin,
        "corpus_counts.json": pin_path(BENCHMARK / "corpus_counts.json"),
        "protocol.json": pin_path(BENCHMARK / "protocol.json"),
        "automated_evidence_amendment.json": pin_path(BENCHMARK / "automated_evidence_amendment.json"),
        "automated_reference_manifest.json": pin_path(BENCHMARK / "annotations" / "automated_reference_manifest.json"),
        "legal.jsonl": pin_path(BENCHMARK / "annotations" / "legal.jsonl"),
        "skills.jsonl": pin_path(BENCHMARK / "annotations" / "skills.jsonl"),
        "skill_adversarial.jsonl": pin_path(BENCHMARK / "cases" / "skill_adversarial.jsonl"),
        "cve_pairs.jsonl": pin_path(BENCHMARK / "cases" / "cve_pairs.jsonl"),
        "polarity_contracts.jsonl": pin_path(ROOT / "papers/completion/law_to_action/receipts/snapshots/LA-006/polarity_contracts.jsonl"),
        "cve_reproduction_index.json": pin_path(BENCHMARK / "cve_reproduction" / "index.json"),
    }
    amendment = load_json(BENCHMARK / "automated_evidence_amendment.json")
    bound_protocol = ((amendment.get("original_protocol") or {}).get("sha256"))
    if bound_protocol != ORIGINAL_PROTOCOL_SHA256:
        raise MeasurementError("LA-027 amendment no longer binds the original protocol hash")
    pins["original_protocol_sha256_bound_by_amendment"] = {
        "path": "papers/completion/law_to_action/benchmark/automated_evidence_amendment.json",
        "sha256": ORIGINAL_PROTOCOL_SHA256,
        "current_protocol_sha256": pins["protocol.json"]["sha256"],
        "current_protocol_matches_original_bound_hash": pins["protocol.json"]["sha256"] == ORIGINAL_PROTOCOL_SHA256,
    }
    runtime = configure_runtime()
    originals_by_lineage = {}
    for record in skills.values():
        lineage = record.get("lineage_family_id") or (record.get("source") or {}).get("lineage_family_id")
        if lineage:
            originals_by_lineage[lineage] = record
    rows: list[dict[str, Any]] = []
    for family in inventory["families"]:
        population = family["population"]
        case0, case1 = family["planned_case_ids"]
        if population == "legal":
            for case_id in (case0, case1):
                if case_id not in legal:
                    raise MeasurementError(f"missing frozen legal record {case_id}")
                rows.append(measure_legal(legal[case_id], family))
        elif population == "skill":
            original = skills.get(case0)
            if original is None:
                raise MeasurementError(f"missing frozen skill original {case0}")
            rows.append(measure_skill(original, family))
            mutation = reserved_mutations.get(case1)
            if mutation is None:
                raise MeasurementError(f"missing frozen reserved skill mutation {case1}")
            if not mutation.get("source_spans") and original.get("source_spans"):
                mutation = dict(mutation)
                mutation["source_spans"] = original.get("source_spans")
            rows.append(measure_skill(mutation, family))
        elif population == "cve":
            pair = cve_pairs.get(family["lineage_family_id"])
            if pair is None:
                raise MeasurementError(f"missing frozen CVE pair {family['lineage_family_id']}")
            for case_id, side in ((case0, "vulnerable"), (case1, "fixed")):
                rows.append(measure_cve(pair, family, case_id, side, polarity.get(case_id)))
        else:
            raise MeasurementError(f"unknown population {population}")
    order = {case_id: index for index, case_id in enumerate(inventory["case_ids"])}
    rows.sort(key=lambda row: order[row["case_id"]])
    raw_sha256 = hashlib.sha256(b"".join(canonical_json(row) + b"\n" for row in rows)).hexdigest()
    metrics = derive_metrics(
        rows,
        inventory=inventory,
        pins=pins,
        runtime=runtime,
        excluded_controls=excluded_controls,
        raw_sha256=raw_sha256,
    )
    review = render_failure_review(rows, metrics, excluded_controls)
    copy_outputs(rows, metrics, review)
    summary = {
        "task": TASK,
        "cases": len(rows),
        "raw_sha256": raw_sha256,
        "metrics_sha256": digest(metrics),
        "case_accounting": metrics["case_accounting"],
        "withdrawn_unmeasured": list(WITHDRAWN),
        "cohorts_changed_after_outcomes": False,
    }
    print(json.dumps(summary, sort_keys=True, indent=2))
    return summary


def main() -> int:
    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
