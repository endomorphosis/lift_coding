#!/usr/bin/python3.12
"""Development-split source adapters for the LA-027 automated evidence scope.

Selected native adapters process frozen development legal, CVE, and skill
sources into retained predictions or explicit failures. Inputs and runtime
versions are pinned. Outputs are predictions or machine-contract expectations,
never human/expert gold. Final-split labels are not inspected and no held-out
score is emitted. This is qualification infrastructure, not LA-009 scoring.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping
from uuid import uuid4

HERE = Path(__file__).resolve()


def find_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "papers" / "completion" / "law_to_action").is_dir() and (
            candidate / "external" / "ipfs_datasets"
        ).is_dir():
            return candidate
    raise RuntimeError("repository root not found")


ROOT = find_root(HERE)
LIVE = ROOT / "papers" / "completion" / "law_to_action"
BENCHMARK = LIVE / "benchmark"
PYTHON = "/usr/bin/python3.12"
VALIDATION_SITE_PACKAGES = Path("/opt/ipfs-validation-site-packages")
SCHEMA = "law-to-action-source-pipeline/v1"
PIPELINE_VERSION = "la-027-source-pipeline/v1"
EVIDENCE_SCOPE = "automated_source_contracts_and_policy_effects"
DEVELOPMENT_SPLIT = "development"
FORBIDDEN_SPLITS = frozenset({"calibration", "final"})
PINNED_INPUTS = (
    BENCHMARK / "manifests" / "sources.json",
    BENCHMARK / "manifests" / "splits.json",
    BENCHMARK / "corpus_counts.json",
    BENCHMARK / "annotations" / "legal.jsonl",
    BENCHMARK / "annotations" / "skills.jsonl",
    BENCHMARK / "cases" / "skill_adversarial.jsonl",
    BENCHMARK / "cases" / "cve_pairs.jsonl",
    BENCHMARK / "cve_reproduction" / "index.json",
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


class PipelineError(RuntimeError):
    """Source pipeline cannot proceed."""


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
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-" + uuid4().hex)
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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


def development_assignments(splits: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = [row for row in splits["assignments"] if row.get("split") == DEVELOPMENT_SPLIT]
    if len(rows) != 6:
        raise PipelineError(f"expected 6 development families, found {len(rows)}")
    populations = {row["population"] for row in rows}
    if populations != {"legal", "cve", "skill"}:
        raise PipelineError("development families must cover legal, CVE, and skill")
    held = {row["lineage_family_id"] for row in splits["assignments"] if row.get("split") != DEVELOPMENT_SPLIT}
    overlap = {row["lineage_family_id"] for row in rows} & held
    if overlap:
        raise PipelineError(f"development families overlap held-out lineages: {sorted(overlap)}")
    return rows


def refuse_final_split(requested: str) -> None:
    if requested in FORBIDDEN_SPLITS:
        raise PipelineError(
            f"refusing split {requested!r}: the automated-scope pipeline processes "
            "development sources only; final labels and scored examples remain blocked"
        )
    if requested != DEVELOPMENT_SPLIT:
        raise PipelineError(f"unsupported split {requested!r}")


def iter_development_records(path: Path, families: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            split = record.get("split")
            lineage = record.get("lineage_family_id")
            if lineage is None:
                source = record.get("source") if isinstance(record.get("source"), Mapping) else {}
                lineage = source.get("lineage_family_id")
            if split != DEVELOPMENT_SPLIT or lineage not in families:
                continue
            selected.append(record)
    return selected


def reconstruct_span_text(spans: Any) -> dict[str, Any]:
    if not isinstance(spans, list):
        return {"text": "", "span_count": 0, "quoted_sha256s": []}
    parts: list[str] = []
    hashes: list[str] = []
    for span in spans:
        if not isinstance(span, Mapping):
            continue
        quoted = span.get("quoted_text")
        if not isinstance(quoted, str) or not quoted:
            continue
        parts.append(quoted)
        hashes.append(str(span.get("quoted_sha256") or sha256_text(quoted)))
    text = "\n\n".join(parts)
    return {
        "text": text,
        "span_count": len(parts),
        "quoted_sha256s": hashes,
        "reconstructed_sha256": sha256_text(text) if text else None,
        "redistribution": "quoted_spans_only",
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


def legal_prediction(record: Mapping[str, Any], family: Mapping[str, Any]) -> dict[str, Any]:
    case_id = record["case_id"]
    reconstructed = reconstruct_span_text(record.get("source_spans"))
    text = reconstructed["text"]
    prediction: dict[str, Any] = {
        "schema": SCHEMA,
        "pipeline_version": PIPELINE_VERSION,
        "population": "legal",
        "case_id": case_id,
        "lineage_family_id": family["lineage_family_id"],
        "source_id": family["source_id"],
        "split": DEVELOPMENT_SPLIT,
        "adapter": {
            "id": "deterministic_deontic_parser",
            "symbol": "extract_normative_elements",
            "module": "ipfs_datasets_py.logic.deontic.utils.deontic_parser",
            "version": None,
        },
        "input": {
            "annotation_id": record.get("annotation_id"),
            "mutation_class": record.get("mutation_class"),
            "source_artifact_id": (record.get("source") or {}).get("artifact_id"),
            "document_sha256": (record.get("source") or {}).get("document_sha256"),
            "span_reconstruction": {key: reconstructed[key] for key in reconstructed if key != "text"},
            "text_sha256": sha256_text(text) if text else None,
            "independent_label_used": False,
        },
        "scored": False,
        "empirical_benchmark_result": False,
        "gold_inspected": False,
        "evidence_scope": EVIDENCE_SCOPE,
        "generated_labels_are": "predictions or explicitly identified machine-contract expectations, never human/expert gold",
        "independent_human_gold": False,
    }
    if not text:
        prediction["status"] = "failure"
        prediction["failure"] = {
            "code": "empty_quoted_source",
            "message": "development legal record has no quoted source spans to process",
        }
        return prediction
    try:
        from ipfs_datasets_py.logic.deontic.utils.deontic_parser import PARSER_SCHEMA_VERSION, extract_normative_elements

        prediction["adapter"]["version"] = PARSER_SCHEMA_VERSION
        elements = extract_normative_elements(text, document_type="statute")
        compact_elements = []
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
        converter_payload: dict[str, Any] | None = None
        converter_error: str | None = None
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
                "note": "LegalIRCompilerAPI is not the selected development adapter; the deterministic deontic parser ran.",
            }
        prediction["status"] = "prediction"
        prediction["prediction"] = {
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
        return prediction
    except Exception as exc:
        prediction["status"] = "failure"
        prediction["failure"] = {
            "code": "legal_adapter_error",
            "message": bounded_error(exc),
            "trace": traceback.format_exc(limit=8),
        }
        return prediction


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


def skill_prediction(record: Mapping[str, Any], family: Mapping[str, Any]) -> dict[str, Any]:
    case_id = record["case_id"]
    source = record.get("source") if isinstance(record.get("source"), Mapping) else {}
    markdown = skill_markdown(record)
    reconstructed = reconstruct_span_text(record.get("source_spans"))
    prediction: dict[str, Any] = {
        "schema": SCHEMA,
        "pipeline_version": PIPELINE_VERSION,
        "population": "skill",
        "case_id": case_id,
        "lineage_family_id": family["lineage_family_id"],
        "source_id": family["source_id"],
        "split": DEVELOPMENT_SPLIT,
        "adapter": {
            "id": "skillcenter-intent-normalizer",
            "symbol": "SkillCenterIntentNormalizer.normalize_with_diagnostics",
            "module": "ipfs_datasets_py.logic.intent_ir.normalize.skill",
            "version": None,
        },
        "input": {
            "annotation_id": record.get("annotation_id"),
            "skill_id": source.get("skill_id"),
            "bundle_sha256": source.get("bundle_sha256"),
            "content_sha256": source.get("content_sha256"),
            "span_reconstruction": {key: reconstructed[key] for key in reconstructed if key != "text"},
            "reconstructed_markdown_sha256": sha256_text(markdown) if markdown else None,
            "full_bundle_body": "retrieval_only_not_redistributed",
            "independent_label_used": False,
            "source_contains_markdown_commands": record.get("source_contains_markdown_commands"),
        },
        "scored": False,
        "empirical_benchmark_result": False,
        "gold_inspected": False,
        "evidence_scope": EVIDENCE_SCOPE,
        "generated_labels_are": "predictions or explicitly identified machine-contract expectations, never human/expert gold",
        "independent_human_gold": False,
    }
    if not markdown:
        prediction["status"] = "failure"
        prediction["failure"] = {
            "code": "empty_quoted_source",
            "message": "development skill record has no quoted Markdown spans to process",
        }
        return prediction
    try:
        from ipfs_datasets_py.logic.intent_ir.normalize.skill import (
            INTENT_NORMALIZER_VERSION,
            SkillCenterIntentNormalizer,
            SkillNormalizationPolicyError,
        )
        from ipfs_datasets_py.logic.intent_ir.source_adapters.skillcenter import SkillCenterSkillRecord

        prediction["adapter"]["version"] = INTENT_NORMALIZER_VERSION
        identity = record.get("identity") if isinstance(record.get("identity"), Mapping) else {}
        metadata_lines = [
            f"title: {source.get('title') or record.get('annotation_id')}",
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
            title=str(source.get("title") or "development-skill"),
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
            prediction["status"] = "failure"
            prediction["failure"] = {
                "code": "skill_policy_blocked",
                "message": bounded_error(exc),
                "policy": exc.decision.to_dict() if hasattr(exc, "decision") else None,
            }
            return prediction
        document = result.to_dict()["document"]
        prediction["status"] = "prediction"
        prediction["prediction"] = {
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
        return prediction
    except Exception as exc:
        prediction["status"] = "failure"
        prediction["failure"] = {
            "code": "skill_adapter_error",
            "message": bounded_error(exc),
            "trace": traceback.format_exc(limit=8),
        }
        return prediction


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


def load_reproduction(source_id: str) -> dict[str, Any] | None:
    index = load_json(BENCHMARK / "cve_reproduction" / "index.json")
    for relative in index.get("pair_records") or []:
        path = ROOT / relative if not Path(relative).is_absolute() else Path(relative)
        if not path.is_file():
            continue
        record = load_json(path)
        if record.get("source_id") == source_id:
            behavior = record.get("source_supported_behavior") if isinstance(record.get("source_supported_behavior"), Mapping) else {}
            return {
                "path": str(path.relative_to(ROOT)),
                "sha256": sha256_file(path),
                "cve_id": record.get("cve_id"),
                "untrusted_source_executed": record.get("untrusted_source_executed"),
                "isolated_reproduction": compact_mapping(
                    record.get("isolated_reproduction") or {},
                    keys=(
                        "status",
                        "kind",
                        "executed_untrusted_source",
                        "vulnerable_revision",
                        "fixed_revision",
                        "runnable_sandbox_reproduction",
                    ),
                ),
                "source_supported_behavior": compact_mapping(
                    behavior,
                    keys=("action", "cwe_id", "effects", "applicability", "authority", "kind", "transfer_to_export_json"),
                ),
            }
    return None


def cve_prediction(record: Mapping[str, Any], family: Mapping[str, Any]) -> dict[str, Any]:
    pair_id = record.get("pair_id") or family["lineage_family_id"] + ":pair"
    restriction = record.get("restriction_candidate") if isinstance(record.get("restriction_candidate"), Mapping) else {}
    reproduction = load_reproduction(family["source_id"])
    prediction: dict[str, Any] = {
        "schema": SCHEMA,
        "pipeline_version": PIPELINE_VERSION,
        "population": "cve",
        "case_id": pair_id,
        "planned_case_ids": family["planned_case_ids"],
        "lineage_family_id": family["lineage_family_id"],
        "source_id": family["source_id"],
        "split": DEVELOPMENT_SPLIT,
        "adapter": {
            "id": "cvefixes-security-ir-adapter",
            "symbol": "adapt_cvefixes_candidate",
            "module": "ipfs_datasets_py.logic.security_ir.cvefixes.adapter",
            "version": None,
        },
        "input": {
            "restriction_status": restriction.get("status"),
            "restriction_authoritative": restriction.get("authoritative"),
            "restriction_mapping_status": restriction.get("mapping_status"),
            "cve_ids": restriction.get("cve_ids"),
            "reproduction": reproduction,
            "independent_label_used": False,
            "independent_polarity": None,
        },
        "scored": False,
        "empirical_benchmark_result": False,
        "gold_inspected": False,
        "evidence_scope": EVIDENCE_SCOPE,
        "generated_labels_are": "predictions or explicitly identified machine-contract expectations, never human/expert gold",
        "independent_human_gold": False,
    }
    if restriction.get("authoritative") is True or restriction.get("grants_execution_authority") is True:
        prediction["status"] = "failure"
        prediction["failure"] = {
            "code": "refused_authoritative_packet_preparer_candidate",
            "message": "packet-preparer restriction candidates cannot grant execution authority",
        }
        return prediction
    try:
        from ipfs_datasets_py.logic.security_ir.cvefixes.adapter import (
            CVEFIXES_ADAPTER_VERSION,
            CandidateReview,
            CandidateReviewState,
            adapt_cvefixes_candidate,
        )
        from ipfs_datasets_py.logic.security_ir.cvefixes.schemas import PolicyCandidate, SourceRecord
        from ipfs_datasets_py.logic.security_ir.cvefixes.vocabulary import CVEFIXES_POLICY_ATTRIBUTES_KEY

        prediction["adapter"]["version"] = CVEFIXES_ADAPTER_VERSION
        config_cid = canonical_cid(
            {
                "adapter": CVEFIXES_ADAPTER_VERSION,
                "source_id": family["source_id"],
                "task": "LA-027",
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
            payload={"lineage_family_id": family["lineage_family_id"], "split": DEVELOPMENT_SPLIT},
        )
        attributes = cve_attributes(restriction)
        candidate = PolicyCandidate(
            effect="deny",
            scope={CVEFIXES_POLICY_ATTRIBUTES_KEY: attributes},
            source_cids=(source_record.record_id,),
            parent_cids=(source_record.record_id,),
            config_cid=config_cid,
            payload={"pair_id": pair_id, "authoritative": False},
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
        prediction["status"] = "prediction"
        prediction["prediction"] = {
            "kind": "cvefixes_security_ir_observed_candidate",
            "adapter_version": adapted.adapter_version,
            "candidate_cid": candidate.record_id,
            "source_record_id": source_record.record_id,
            "declaration_sha256": digest(adapted_dict.get("declaration")),
            "review_state": review.state.value,
            "grants_execution_authority": False,
            "proof_authoritative": False,
            "authority": "observed_candidate_not_independent_review",
            "independent_review": "not_used",
            "independent_human_gold": False,
        }
        return prediction
    except Exception as exc:
        prediction["status"] = "failure"
        prediction["failure"] = {
            "code": "cve_adapter_error",
            "message": bounded_error(exc),
            "trace": traceback.format_exc(limit=8),
        }
        return prediction


def expand_cve_cases(row: Mapping[str, Any], family: Mapping[str, Any]) -> list[dict[str, Any]]:
    records = []
    for index, case_id in enumerate(family["planned_case_ids"]):
        item = dict(row)
        item["case_id"] = case_id
        item["cve_side"] = "vulnerable" if index == 0 else "fixed"
        records.append(item)
    return records


def run_pipeline(*, split: str = DEVELOPMENT_SPLIT, out_dir: Path | None = None) -> dict[str, Any]:
    refuse_final_split(split)
    sources = load_json(BENCHMARK / "manifests" / "sources.json")
    splits = load_json(BENCHMARK / "manifests" / "splits.json")
    families = {row["lineage_family_id"]: row for row in development_assignments(splits)}
    pins = [pin_path(path) for path in PINNED_INPUTS]
    runtime = configure_runtime()
    freeze = {
        "schema": "law-to-action-source-pipeline-freeze/v1",
        "frozen_at": utc_now(),
        "split": DEVELOPMENT_SPLIT,
        "families": [
            {
                "population": row["population"],
                "lineage_family_id": row["lineage_family_id"],
                "source_id": row["source_id"],
                "planned_case_ids": row["planned_case_ids"],
            }
            for row in development_assignments(splits)
        ],
        "inputs": pins,
        "runtime": runtime,
        "scored": False,
        "inspect_final_labels": False,
    }
    legal_records = iter_development_records(BENCHMARK / "annotations" / "legal.jsonl", families)
    skill_originals = iter_development_records(BENCHMARK / "annotations" / "skills.jsonl", families)
    skill_adversarial = iter_development_records(BENCHMARK / "cases" / "skill_adversarial.jsonl", families)
    cve_pairs = iter_development_records(BENCHMARK / "cases" / "cve_pairs.jsonl", families)
    if len(legal_records) != 4:
        raise PipelineError(f"expected 4 development legal cases, found {len(legal_records)}")
    if len(skill_originals) != 2:
        raise PipelineError(f"expected 2 development original skill records, found {len(skill_originals)}")
    if len(cve_pairs) != 2:
        raise PipelineError(f"expected 2 development CVE pairs, found {len(cve_pairs)}")
    planned_skill_case1 = {row["planned_case_ids"][1] for row in development_assignments(splits) if row["population"] == "skill"}
    skill_mutations = [row for row in skill_adversarial if row.get("case_id") in planned_skill_case1]
    if len(skill_mutations) != 2:
        raise PipelineError(f"expected 2 reserved development skill mutations, found {len(skill_mutations)}")

    rows: list[dict[str, Any]] = []
    for record in legal_records:
        rows.append(legal_prediction(record, families[record["source"]["lineage_family_id"]]))
    originals_by_lineage = {}
    for record in skill_originals:
        lineage = record.get("lineage_family_id") or record["source"]["lineage_family_id"]
        originals_by_lineage[lineage] = record
        rows.append(skill_prediction(record, families[lineage]))
    for record in skill_mutations:
        lineage = record.get("lineage_family_id") or record["source"]["lineage_family_id"]
        mutation = dict(record)
        original = originals_by_lineage.get(lineage)
        if original and not mutation.get("source_spans"):
            mutation["source_spans"] = original.get("source_spans")
        rows.append(skill_prediction(mutation, families[lineage]))
    for pair in cve_pairs:
        family = families[pair["lineage_family_id"]]
        adapted = cve_prediction(pair, family)
        for case in expand_cve_cases(pair, family):
            item = dict(adapted)
            item["case_id"] = case["case_id"]
            item["cve_side"] = case["cve_side"]
            rows.append(item)

    expected_ids = [case_id for row in development_assignments(splits) for case_id in row["planned_case_ids"]]
    got_ids = [row["case_id"] for row in rows]
    if sorted(got_ids) != sorted(expected_ids):
        raise PipelineError(f"pipeline case population mismatch: expected {expected_ids}, got {got_ids}")
    if any(row.get("gold_inspected") or row.get("scored") for row in rows):
        raise PipelineError("pipeline attempted to inspect gold or score outcomes")

    predictions = [row for row in rows if row.get("status") == "prediction"]
    failures = [row for row in rows if row.get("status") == "failure"]
    by_population = {}
    for population in ("legal", "cve", "skill"):
        group = [row for row in rows if row["population"] == population]
        by_population[population] = {
            "cases": len(group),
            "predictions": sum(1 for row in group if row.get("status") == "prediction"),
            "failures": sum(1 for row in group if row.get("status") == "failure"),
        }
    summary = {
        "schema": SCHEMA,
        "pipeline_version": PIPELINE_VERSION,
        "task": "LA-027",
        "evidence_scope": EVIDENCE_SCOPE,
        "split": DEVELOPMENT_SPLIT,
        "frozen": freeze,
        "source_manifest_status": sources.get("status"),
        "evaluation_admission": sources.get("evaluation_admission"),
        "counts": {
            "cases": len(rows),
            "predictions": len(predictions),
            "failures": len(failures),
            "by_population": by_population,
        },
        "scored": False,
        "empirical_benchmark_result": False,
        "final_labels_inspected": False,
        "fixture_route": False,
        "production_claim": False,
        "independent_human_gold": False,
        "generated_labels_are": "predictions or explicitly identified machine-contract expectations, never human/expert gold",
        "held_out_result_inferred": False,
        "useful_work_success_inferred_from_fixtures": False,
    }
    destination = out_dir or (LIVE / "results" / "development_qualification")
    destination.mkdir(parents=True, exist_ok=True)
    write_json(destination / "source_pipeline_freeze.json", freeze)
    write_jsonl(destination / "source_predictions.jsonl", predictions)
    write_jsonl(destination / "source_failures.jsonl", failures)
    write_jsonl(destination / "source_records.jsonl", rows)
    write_json(destination / "source_pipeline_summary.json", summary)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("run", "freeze-check"), default="run", nargs="?")
    parser.add_argument("--split", default=DEVELOPMENT_SPLIT)
    parser.add_argument("--out", type=Path, default=LIVE / "results" / "development_qualification")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    refuse_final_split(args.split)
    if args.command == "freeze-check":
        splits = load_json(BENCHMARK / "manifests" / "splits.json")
        print(json.dumps({"split": DEVELOPMENT_SPLIT, "families": len(development_assignments(splits))}, sort_keys=True))
        return 0
    summary = run_pipeline(split=args.split, out_dir=args.out)
    print(json.dumps(summary, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
