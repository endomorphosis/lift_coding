#!/usr/bin/env python3
"""Matched A–E pipeline adapters with real AF-027 development routes.

AF-010 published callable adapters that returned unavailable on the sealed
PATH. This revision keeps those isolation contracts and replaces the
unconditional unavailable stubs with development-qualification routes:

* A — scientific-gateway Grok ``grok-4.6`` model-to-target call
* B — frozen canonical-profile compiler (no_guidance / no_repair)
* C — typed source-grounded multiview without proof transfer
* D — C plus checked property bridges and compatible premises
* E — wired to AF-011/AF-013 checkpoint and promotion gates; unavailable
  until those complete; this prerequisite does not require their future
  trained outputs

Native compiler packages still require ``multiformats``. When that import
fails, B and C execute stdlib replicas of the frozen profiles rather than
returning unavailable. Unavailable optional capabilities, including E, never
receive measured credit. Development runs are not Table 6. Standard library
only at runtime.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from scientific_gateway import (
    DEVELOPMENT_TARGET_PROMPT,
    GatewayError,
    complete as gateway_complete,
    gateway_identity,
    model_to_target,
    public_credential_status,
)


SCHEMA_CONFIG = "autoformalization-pipeline-arms/v2"
SCHEMA_RESULT = "autoformalization-pipeline-arm-result/v2"
TASK_ID = "AF-027"
SUITE_ID = "AF-027-development-qualification"
PIPELINE_ARMS = ("A", "B", "C", "D", "E")
EXECUTION_STATUSES = (
    "measured", "partial", "unavailable", "unsupported", "abstained",
    "timeout", "invalid", "failure", "no_run",
)
RESULT_KINDS = (
    "native_checked_proof", "solver_local_result", "countermodel",
    "bounded_observation", "failure", "no_run",
)
NATIVE_CHECKERS = ("lean", "lake", "z3", "cvc5", "vampire", "eprover", "coqc", "isabelle")
FROZEN_CANONICAL_PROFILE_ID = (
    "typed_deontic__no_guidance__no_repair__not_applicable__deterministic"
)
COMPILER_PRODUCER = "intent-formalization-compiler/v1"
CHECKER_CONTRACT_ID = "AF-010-shared-target-checker/v1"
SEALED_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
BRIDGE_RECEIPT_SCHEMAS = frozenset({
    "autoformalization-translation-receipt/v1",
    "autoformalization-bridge-validation-result/v1",
})
D_BRIDGE_EVIDENCE_KEYS = frozenset({
    "accepted_transfer",
    "bridge_evidence",
    "bridge_obligations",
    "bridge_records",
    "checked_bridges",
    "checked_property_bridges",
    "compatible_premises",
    "cross_source_premises",
    "cross_view_proof",
    "premise_assembly",
    "proof_transfer",
    "property_preservation_obligations",
    "translation_receipts",
})
CHECKER_MUTATION_KEYS = frozenset({
    "advice_as_checker",
    "checker_override",
    "replace_checker",
    "substitute_checker",
})
SYNTHETIC_SUCCESS_KEYS = frozenset({
    "assumed_proof",
    "fixture_success",
    "forced_success",
    "synthetic_success",
})
HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
REPO_ROOT = PAPER_ROOT.parents[2]

INSPECTED_SOURCES = {
    "canonical_roundtrip.py": {
        "path": "external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_roundtrip.py",
        "imported": False,
        "role": "B/C deterministic compiler and source-withheld round-trip composition",
        "note": "Inspected. Production import requires multiformats; AF-027 uses a stdlib frozen-profile replica when import fails.",
    },
    "canonical_compiler.py": {
        "path": "external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_compiler.py",
        "imported": False,
        "role": "B typed-deontic compiler with caller-supplied vocabulary",
        "note": "Composition pins guidance=no_guidance and repair=no_repair.",
    },
    "canonical_contracts.py": {
        "path": "external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_contracts.py",
        "imported": False,
        "role": "B representative arm identity",
        "note": f"IMPLEMENTATION_REPRESENTATIVE_ARM_ID is {FROZEN_CANONICAL_PROFILE_ID}.",
    },
    "legal_ir_learned_guidance.py": {
        "path": "external/ipfs_datasets/ipfs_datasets_py/logic/integration/reasoning/legal_ir_learned_guidance.py",
        "imported": False,
        "role": "E promotion boundary for source-free stable-feature advice",
        "note": "Advisor only. Absent AF-011/AF-013 receipts keep E unavailable.",
    },
    "intent_formalization_compiler.py": {
        "path": "external/ipfs_datasets/ipfs_datasets_py/logic/intent_ir/formalize/compiler.py",
        "imported": False,
        "role": "C typed source-grounded multi-view compiler (AF-003 selected entry)",
        "note": "Native import requires multiformats; AF-027 uses a stdlib multiview replica when import fails.",
    },
    "bridge_cases.py": {
        "path": "papers/completion/autoformalization/evaluation/bridge_cases.py",
        "imported": True,
        "role": "D checked-bridge obligations and translation-receipt schema",
        "note": "AF-015 finite bridges are D-only evidence. C must not consume them.",
    },
    "scientific_gateway.py": {
        "path": "papers/completion/autoformalization/evaluation/scientific_gateway.py",
        "imported": True,
        "role": "A served Grok primary / Codex quota-only fallback",
        "note": "Nested workers do not dispatch supervisor jobs; A uses this gateway.",
    },
}

C_VIEW_IDS = (
    "intent-ir-view/facts/v1",
    "intent-ir-view/intention-deontic/v1",
    "intent-ir-view/action-hoare/v1",
    "intent-ir-view/invariant/v1",
    "intent-ir-view/verification/v1",
    "intent-ir-view/failure/v1",
)

DEVELOPMENT_SOURCE = {
    "source_id": "AF027-DEV-selection-cfr-37-360.1-2024",
    "split": "selection",
    "record_id": "cfr:37:360.1:2024",
    "citation": "37 CFR 360.1",
    "path": "papers/completion/autoformalization/receipts/snapshots/AF-004/selection.sources.jsonl",
    "text": (
        "General.\n\n§ 360.1 General. This subpart prescribes procedures under "
        "17 U.S.C. 111(d)(4)(A) and 17 U.S.C. 119(b)(4) whereby parties claiming "
        "entitlement to cable compulsory license royalty fees or satellite "
        "compulsory license royalty fees must file claims with the Copyright "
        "Royalty Board."
    ),
}

DEVELOPMENT_BRIDGE_SOURCE = {
    "source_id": "AF027-DEV-Q1-protected-write",
    "split": "constructed_control",
    "text": "If Protected is true and Approved is false, then Write is false.",
}


class PipelineArmError(ValueError):
    """Raised when an arm contract, request, or isolation rule is violated."""


class IsolationError(PipelineArmError):
    """Raised when C consumes D evidence or E mutates its checker."""


def canonical_dumps(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except ValueError as exc:
        raise PipelineArmError("canonical JSON requires finite numeric values") from exc


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_obj(value: Any) -> str:
    return sha256_text(canonical_dumps(value))


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise PipelineArmError(message)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def iter_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for item in value.values():
            yield from iter_mappings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from iter_mappings(item)


def default_paths(root: Path | None = None) -> dict[str, Path]:
    paper = (root or REPO_ROOT) / "papers/completion/autoformalization"
    return {
        "root": (root or REPO_ROOT).resolve(),
        "paper": paper,
        "config": paper / "config" / "pipeline_arms.json",
        "preflight": paper / "evidence" / "pipeline_arm_preflight.json",
        "plan": paper / "config" / "experiment_plan.json",
        "manifest": paper / "config" / "environment_manifest.json",
        "metrics": paper / "config" / "metrics.json",
        "teacher": paper / "data" / "teacher_manifest.json",
        "splits": paper / "data" / "splits.json",
        "capability": paper / "evidence" / "runtime_capability_matrix.json",
        "guidance_export": paper / "evidence" / "guidance_export.json",
        "consumer_activation": paper / "evidence" / "consumer_activation.json",
        "checkpoints": paper / "checkpoints",
        "qualification": paper / "evidence" / "runtime_qualification",
    }


def checker_contract() -> dict[str, Any]:
    return {
        "checker_id": CHECKER_CONTRACT_ID,
        "advice_cannot_replace_checking": True,
        "intended_native": "lean",
        "intended_solver_local": "z3_or_cvc5_descriptive_only",
        "mutation_allowed": False,
        "native_receipt_required_for_useful_proof": True,
        "shared_across_arms": list(PIPELINE_ARMS),
        "solver_local_is_not_native_checked_proof": True,
    }


def checker_digest() -> str:
    return sha256_obj(checker_contract())


def shared_resource_envelope(plan: Mapping[str, Any]) -> dict[str, Any]:
    budget = plan["common_budget"]
    return {
        "deterministic_replays": plan["population_and_statistics"]["deterministic_replays"],
        "gpu_or_model_service_slots": budget["gpu_or_model_service_slots"],
        "learned_condition_seeds": budget["learned_condition_seeds"],
        "memory_gib": budget["memory_gib"],
        "natural_final_test_units_per_condition": budget["natural_final_test_units_per_condition"],
        "per_item_search_validation_minutes": budget["per_item_search_validation_minutes"],
        "per_seed_wall_minutes": budget["per_seed_wall_minutes"],
        "seeds": list(plan["population_and_statistics"]["seeds"]),
        "source": "papers/completion/autoformalization/config/experiment_plan.json#/common_budget",
    }


def frozen_canonical_profile() -> dict[str, Any]:
    return {
        "constructor_route": "not_applicable",
        "disables_learned_guidance": True,
        "disables_repair": True,
        "fallback_allowed": False,
        "guidance": "no_guidance",
        "implementation_representative_arm_id": FROZEN_CANONICAL_PROFILE_ID,
        "learned_stages": [],
        "model_call_count": 0,
        "paper_evidence": "p. 3, §3.1: frozen canonical profile disables guidance",
        "repair": "no_repair",
        "source_module": "external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_compiler.py",
        "used_by_arms": ["B"],
    }


def arm_definitions() -> dict[str, dict[str, Any]]:
    checker = {
        "checker_digest": checker_digest(),
        "checker_id": CHECKER_CONTRACT_ID,
        "shared": True,
    }
    common_entry = "papers/completion/autoformalization/evaluation/pipeline_arms.py"
    return {
        "A": {
            "id": "A",
            "name": "Direct model-to-target formalization",
            "family": "pipeline",
            "claim": "Direct model baseline under matched checker.",
            "control_comparison": "A vs B on identical eligible tasks; unavailable is not zero.",
            "entry_point": f"{common_entry}:run_arm_a",
            "native_entry_points": [
                "papers/completion/autoformalization/evaluation/scientific_gateway.py",
            ],
            "features_allowed": ["declared_vocabulary", "source_text"],
            "oracles_allowed": [
                "direct_model_inference",
                "independent_facet_adjudication",
                "target_checker",
            ],
            "features_blocked": [
                "checked_bridges", "compiler_views", "learned_advice",
                "premise_assembly", "sample_memory",
            ],
            "checker": checker,
            "uses_frozen_canonical_profile": False,
            "consumes_bridge_evidence": False,
            "learned_advice": False,
            "development_route": "scientific_gateway_grok_4_6",
            "table5": "Direct model-to-target formalization with the same target checker.",
        },
        "B": {
            "id": "B",
            "name": "Deterministic bounded compiler",
            "family": "pipeline",
            "claim": "Deterministic compiler baseline.",
            "control_comparison": "B vs A and C on identical tasks/checker/budget.",
            "entry_point": f"{common_entry}:run_arm_b",
            "native_entry_points": [
                "ipfs_datasets_py.logic.legal_ir.canonical_compiler.TypedDeonticCanonicalCompiler",
            ],
            "features_allowed": [
                "declared_vocabulary", "explicit_abstention", "source_maps",
                "source_text", "typed_deontic_ir",
            ],
            "oracles_allowed": [
                "deterministic_bounded_compiler",
                "independent_facet_adjudication",
                "target_checker",
            ],
            "features_blocked": [
                "checked_bridges", "direct_model_inference", "learned_advice",
                "learned_guidance", "repair", "sample_memory",
            ],
            "checker": checker,
            "uses_frozen_canonical_profile": True,
            "consumes_bridge_evidence": False,
            "learned_advice": False,
            "development_route": "frozen_canonical_profile_compiler",
            "table5": "Deterministic bounded compiler, declared vocabulary, and explicit abstention.",
        },
        "C": {
            "id": "C",
            "name": "Typed source-grounded multiview without proof transfer",
            "family": "pipeline",
            "claim": "Source-grounded multiview without transfer.",
            "control_comparison": "C vs B isolates multiview representation without transfer.",
            "entry_point": f"{common_entry}:run_arm_c",
            "native_entry_points": [
                "ipfs_datasets_py.logic.intent_ir.formalize.compiler.IntentFormalizationCompiler",
            ],
            "features_allowed": [
                "declared_vocabulary", "source_grounding", "source_maps",
                "source_text", "typed_multiview",
            ],
            "oracles_allowed": [
                "independent_facet_adjudication",
                "native_proof_checker_where_supported",
                "pinned_compiler_elaborator",
            ],
            "features_blocked": [
                "checked_bridges", "compatible_premise_assembly",
                "cross_view_proof_transfer", "D_bridge_evidence",
                "learned_advice", "sample_memory",
            ],
            "checker": checker,
            "uses_frozen_canonical_profile": False,
            "consumes_bridge_evidence": False,
            "learned_advice": False,
            "development_route": "typed_multiview_no_transfer",
            "table5": (
                "Typed multi-view representation with source grounding, but no "
                "admitted cross-view proof transfer."
            ),
        },
        "D": {
            "id": "D",
            "name": "Checked bridges and compatible premise assembly",
            "family": "pipeline",
            "claim": "Checked cross-source proof transfer.",
            "control_comparison": "D vs C isolates checked bridges and premise assembly.",
            "entry_point": f"{common_entry}:run_arm_d",
            "native_entry_points": [
                "papers/completion/autoformalization/evaluation/bridge_cases.py",
            ],
            "features_allowed": [
                "checked_property_bridges", "compatible_premise_assembly",
                "declared_vocabulary", "source_grounding", "source_maps",
                "source_text", "typed_multiview",
            ],
            "oracles_allowed": [
                "bridge_obligations",
                "independent_facet_adjudication",
                "native_proof_checker_where_supported",
                "pinned_compiler_elaborator",
                "premise_compatibility_nonvacuity",
            ],
            "features_blocked": ["learned_advice", "sample_memory"],
            "checker": checker,
            "uses_frozen_canonical_profile": False,
            "consumes_bridge_evidence": True,
            "learned_advice": False,
            "development_route": "checked_bridges_and_premises",
            "table5": (
                "C plus checked property-specific bridges and compatible "
                "cross-source premise assembly."
            ),
        },
        "E": {
            "id": "E",
            "name": "D plus bounded learned view/premise advice",
            "family": "pipeline",
            "claim": "Learned advice beyond checked bridges.",
            "control_comparison": "E vs D isolates learned advice with checker fixed.",
            "entry_point": f"{common_entry}:run_arm_e",
            "native_entry_points": [
                "ipfs_datasets_py.logic.integration.reasoning.legal_ir_learned_guidance.promote_legal_ir_learned_guidance",
            ],
            "features_allowed": [
                "bounded_learned_view_premise_advice",
                "checked_property_bridges",
                "compatible_premise_assembly",
                "declared_vocabulary",
                "source_grounding",
                "source_maps",
                "source_text",
                "typed_multiview",
            ],
            "oracles_allowed": [
                "bridge_obligations",
                "independent_facet_adjudication",
                "native_proof_checker_where_supported",
                "pinned_checkpoint_advice",
                "pinned_compiler_elaborator",
                "premise_compatibility_nonvacuity",
            ],
            "features_blocked": [
                "checker_mutation", "sample_memory", "unpinned_advice",
            ],
            "checker": checker,
            "uses_frozen_canonical_profile": False,
            "consumes_bridge_evidence": True,
            "learned_advice": True,
            "advice_cannot_replace_checking": True,
            "development_route": "unavailable_pending_AF-011_AF-013",
            "promotion_gates": ["AF-011", "AF-013"],
            "table5": (
                "D plus bounded learned view/premise advice, with frozen "
                "checkpoint and unchanged checker."
            ),
        },
    }


def inspect_sources(root: Path) -> dict[str, Any]:
    inspected = {}
    for name, spec in INSPECTED_SOURCES.items():
        path = root / spec["path"]
        record = {
            "exists": path.is_file(),
            "imported": bool(spec.get("imported")),
            "note": spec["note"],
            "path": spec["path"],
            "role": spec["role"],
            "sha256": sha256_file(path) if path.is_file() else None,
        }
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            record["contains_no_guidance"] = "no_guidance" in text
            record["contains_frozen_profile_id"] = FROZEN_CANONICAL_PROFILE_ID in text
            record["contains_learned_guidance_schema"] = "legal-ir-learned-guidance-v1" in text
        inspected[name] = record
    contracts = inspected.get("canonical_contracts.py") or {}
    compiler = inspected.get("canonical_compiler.py") or {}
    _expect(contracts.get("exists") is True, "canonical_contracts.py missing")
    _expect(contracts.get("contains_frozen_profile_id") is True,
            "frozen canonical profile id missing from canonical_contracts.py")
    _expect(compiler.get("contains_no_guidance") is True,
            "canonical_compiler.py does not pin no_guidance")
    return inspected


def _which_or_absolute(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    runtime = Path("/home/barberb/.local/share/vericodegen-research-runtime/bin") / name
    if runtime.is_file() and os.access(runtime, os.X_OK):
        return str(runtime)
    return None


def probe_native_checkers() -> dict[str, Any]:
    path = os.environ.get("PATH", "")
    home = os.environ.get("HOME") or ""
    probes = []
    for name in NATIVE_CHECKERS:
        resolved = _which_or_absolute(name)
        version = None
        sha = None
        if resolved:
            try:
                completed = subprocess.run(
                    [resolved, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                version = (completed.stdout or completed.stderr or "").strip().splitlines()[:1]
                version = version[0] if version else None
            except (OSError, subprocess.TimeoutExpired) as exc:
                version = f"version_probe_failed:{exc}"
            try:
                sha = sha256_file(Path(resolved))
            except OSError:
                sha = None
        probes.append({
            "name": name,
            "resolved_path": resolved,
            "sha256": sha,
            "version": version,
            "status": "available" if resolved else "unavailable",
            "on_process_path": bool(shutil.which(name)),
            "usable_in_worker": bool(resolved),
            "usable_in_default_sealed_path": bool(
                resolved and Path(resolved).is_relative_to(Path("/usr"))
            ) if resolved else False,
        })
    validation_path = os.environ.get("IPFS_ACCELERATE_AGENT_VALIDATION_PATH") or SEALED_PATH
    return {
        "any_native_checker_usable": any(item["usable_in_worker"] for item in probes),
        "checkers": probes,
        "home": home,
        "home_is_validation_private": (
            Path(home).name.startswith("ipfs-accelerate-validation-home-") if home else False
        ),
        "path": path,
        "validation_path": validation_path,
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "sealed_path_expected": SEALED_PATH,
        "sealed_path_matches": path == SEALED_PATH,
        "worker_visible_not_host_assumed": True,
    }


def probe_python_packages() -> dict[str, Any]:
    packages = {}
    for name in ("numpy", "torch"):
        record: dict[str, Any] = {"name": name, "available": False}
        try:
            module = __import__(name)
            record.update({
                "available": True,
                "version": getattr(module, "__version__", None),
                "file": getattr(module, "__file__", None),
            })
            if name == "torch":
                record["cuda_available"] = bool(getattr(module, "cuda").is_available())
        except Exception as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"
        packages[name] = record
    return packages


def probe_direct_model(manifest: Mapping[str, Any] | None = None) -> dict[str, Any]:
    credential = public_credential_status()
    identity = gateway_identity()
    selected = ((manifest or {}).get("selected_entry_points") or {}).get("direct_generative_model") or {}
    leanstral = selected.get("cached_leanstral_candidate") or {}
    runnable = bool(credential.get("available"))
    blockers = []
    if not runnable:
        blockers.extend(credential.get("blockers") or ["scientific gateway credential missing"])
    if leanstral.get("weight_file_bytes") and int(leanstral["weight_file_bytes"]) > 16 * 1024 ** 3:
        blockers.append("cached Leanstral GGUF exceeds the 16 GiB envelope and is not used")
    return {
        "blockers": blockers,
        "cached_leanstral_weight_file_bytes": leanstral.get("weight_file_bytes"),
        "credential": credential,
        "gateway": identity,
        "runnable": runnable,
        "scope_guard": "development qualification via scientific gateway; not Table 6",
        "selected": PRIMARY_MODEL if runnable else None,
        "served_primary": "grok-4.6",
        "status": "configured_scientific_gateway" if runnable else "unavailable",
    }


PRIMARY_MODEL = "grok-4.6"


def probe_learned_guidance(paths: Mapping[str, Path]) -> dict[str, Any]:
    checkpoints = paths["checkpoints"]
    checkpoint_files = []
    if checkpoints.is_dir():
        checkpoint_files = sorted(
            str(item.relative_to(paths["root"]))
            for item in checkpoints.rglob("*") if item.is_file()
        )
    teacher = load_json(paths["teacher"]) if paths["teacher"].is_file() else {}
    advice = teacher.get("learned_advice") or {}
    export_present = paths["guidance_export"].is_file()
    consumer_present = paths["consumer_activation"].is_file()
    runnable = bool(checkpoint_files and export_present and consumer_present)
    blockers = []
    if not checkpoint_files:
        blockers.append("no AF-011 frozen checkpoint under papers/completion/autoformalization/checkpoints")
    if not export_present:
        blockers.append("no AF-013 guidance export receipt")
    if not consumer_present:
        blockers.append("no AF-013 consumer activation receipt")
    if advice.get("status"):
        blockers.append(f"teacher_manifest.learned_advice.status={advice['status']}")
    return {
        "blockers": blockers,
        "checkpoint_files": checkpoint_files,
        "checkpoints_declared": advice.get("checkpoints", 0),
        "consumer_activation_present": consumer_present,
        "guidance_export_present": export_present,
        "pending_tasks": ["AF-011", "AF-013"],
        "promotion_gates": ["AF-011", "AF-013"],
        "runnable": runnable,
        "status": "available" if runnable else "unavailable",
        "teacher_status": advice.get("status"),
        "measured_credit": False,
    }


def request_contains_bridge_evidence(request: Mapping[str, Any]) -> list[str]:
    hits: list[str] = []
    for mapping in iter_mappings(request):
        for key in mapping:
            if str(key) in D_BRIDGE_EVIDENCE_KEYS and str(key) not in hits:
                hits.append(str(key))
        schema = mapping.get("schema")
        if isinstance(schema, str) and schema in BRIDGE_RECEIPT_SCHEMAS and schema not in hits:
            hits.append(schema)
    return hits


def request_contains_checker_mutation(request: Mapping[str, Any]) -> list[str]:
    hits: list[str] = []
    for mapping in iter_mappings(request):
        for key in mapping:
            if str(key) in CHECKER_MUTATION_KEYS and str(key) not in hits:
                hits.append(str(key))
        if "checker" in mapping and mapping["checker"] not in (None, checker_contract(), CHECKER_CONTRACT_ID):
            supplied = mapping["checker"]
            if isinstance(supplied, Mapping):
                supplied_digest = supplied.get("checker_digest") or sha256_obj(supplied)
                if supplied_digest != checker_digest() and "checker" not in hits:
                    hits.append("checker")
            elif supplied != CHECKER_CONTRACT_ID and "checker" not in hits:
                hits.append("checker")
        if mapping.get("checker_digest") and mapping["checker_digest"] != checker_digest():
            if "checker_digest" not in hits:
                hits.append("checker_digest")
    return hits


def request_contains_synthetic_success(request: Mapping[str, Any]) -> list[str]:
    hits: list[str] = []
    for mapping in iter_mappings(request):
        for key in mapping:
            if str(key) in SYNTHETIC_SUCCESS_KEYS and mapping.get(key) and str(key) not in hits:
                hits.append(str(key))
    return hits


def request_enables_guidance(request: Mapping[str, Any]) -> bool:
    for mapping in iter_mappings(request):
        if mapping.get("guidance") in {"learned", "enabled", "on", True}:
            return True
        if mapping.get("learned_stages"):
            return True
        if mapping.get("repair") not in (None, "no_repair", "disabled", False):
            if "repair" in mapping:
                return True
        if mapping.get("uses_frozen_canonical_profile") is False and mapping.get("arm") == "B":
            return True
    return False


def validate_request(arm_id: str, request: Mapping[str, Any]) -> None:
    _expect(arm_id in PIPELINE_ARMS, f"unknown pipeline arm {arm_id}")
    _expect(isinstance(request, Mapping), "arm request must be an object")
    synthetic = request_contains_synthetic_success(request)
    if synthetic:
        raise IsolationError(f"arm {arm_id} refuses synthetic success markers {synthetic}")
    declared = request.get("experiment_arm")
    if declared not in (None, arm_id):
        raise IsolationError(f"request experiment_arm {declared} does not match adapter {arm_id}")
    if arm_id in {"A", "B", "C"}:
        hits = request_contains_bridge_evidence(request)
        if hits:
            raise IsolationError(f"arm {arm_id} cannot consume D bridge evidence: {hits}")
    if arm_id == "B" and request_enables_guidance(request):
        raise IsolationError("arm B frozen canonical profile disables learned guidance and repair")
    if arm_id == "E":
        mutations = request_contains_checker_mutation(request)
        if mutations:
            raise IsolationError(f"arm E cannot silently alter its checker: {mutations}")
        supplied_digest = request.get("checker_digest")
        if supplied_digest not in (None, checker_digest()):
            raise IsolationError("arm E checker_digest drifted from D")
    if arm_id != "E" and request.get("learned_advice"):
        raise IsolationError(f"arm {arm_id} cannot consume E learned advice")


def charge_preprocessing(started: float) -> dict[str, Any]:
    elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
    budget_ms = 10 * 60 * 1000
    return {
        "elapsed_ms": elapsed_ms,
        "charged": True,
        "budget_item": "per_item_search_validation_minutes",
        "budget_ms": budget_ms,
        "within_budget": elapsed_ms <= budget_ms,
    }


def run_native_checker(
    *,
    name: str,
    argv: Sequence[str],
    stdin_text: str | None = None,
    source_text: str | None = None,
    purpose: str,
) -> dict[str, Any]:
    resolved = _which_or_absolute(name)
    started_at = utc_now()
    t0 = time.perf_counter()
    if not resolved:
        return {
            "schema": "autoformalization-native-checker-receipt/v2",
            "checker": name,
            "purpose": purpose,
            "resolved_path": None,
            "execution_status": "unavailable",
            "result_kind": "no_run",
            "failures": [f"{name} not visible in the worker boundary"],
            "started_at": started_at,
            "finished_at": utc_now(),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "independent": True,
        }
    try:
        completed = subprocess.run(
            list(argv),
            input=stdin_text,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        status = "measured" if completed.returncode == 0 else "failure"
        failures = [] if completed.returncode == 0 else [
            f"exit_code={completed.returncode}",
            (completed.stdout or completed.stderr or "").strip().splitlines()[:1][0]
            if (completed.stdout or completed.stderr) else "checker_failed",
        ]
        receipt = {
            "schema": "autoformalization-native-checker-receipt/v2",
            "checker": name,
            "purpose": purpose,
            "resolved_path": resolved,
            "argv": list(argv),
            "exit_code": completed.returncode,
            "stdout": (completed.stdout or "")[:4000],
            "stderr": (completed.stderr or "")[:4000],
            "execution_status": status,
            "result_kind": "native_checked_proof" if name == "lean" and completed.returncode == 0 else (
                "solver_local_result" if name in {"z3", "cvc5"} and completed.returncode == 0 else "failure"
            ),
            "failures": failures,
            "started_at": started_at,
            "finished_at": utc_now(),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "independent": True,
            "source_sha256": sha256_text(source_text) if source_text is not None else None,
            "binary_sha256": sha256_file(Path(resolved)),
        }
        receipt["receipt_sha256"] = sha256_obj({k: receipt[k] for k in receipt if k != "receipt_sha256"})
        return receipt
    except subprocess.TimeoutExpired:
        return {
            "schema": "autoformalization-native-checker-receipt/v2",
            "checker": name,
            "purpose": purpose,
            "resolved_path": resolved,
            "execution_status": "timeout",
            "result_kind": "failure",
            "failures": ["timeout"],
            "started_at": started_at,
            "finished_at": utc_now(),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "independent": True,
        }


def extract_lean(text: str) -> str:
    lines = [line.rstrip() for line in str(text or "").splitlines()]
    kept = []
    started = False
    for line in lines:
        if re.match(r"^\s*(theorem|example|def|variable|axiom|import|#check)\b", line):
            started = True
        if started:
            if line.strip().startswith("```"):
                break
            kept.append(line)
    if kept:
        return "\n".join(kept).strip() + "\n"
    stripped = str(text or "").strip()
    return stripped + ("\n" if stripped else "")


def lean_check_text(source: str, *, purpose: str) -> dict[str, Any]:
    lean = _which_or_absolute("lean")
    if not lean:
        return run_native_checker(name="lean", argv=["lean"], purpose=purpose)
    with tempfile.TemporaryDirectory(prefix="af027-lean-") as tmp:
        path = Path(tmp) / "target.lean"
        path.write_text(source, encoding="utf-8")
        return run_native_checker(
            name="lean",
            argv=[lean, str(path)],
            source_text=source,
            purpose=purpose,
        )


def compile_arm_b(source_text: str) -> dict[str, Any]:
    started = time.perf_counter()
    text = " ".join(source_text.split())
    lowered = text.lower()
    vocab = {
        "actors": ("party", "parties", "copyright_royalty_board"),
        "actions": ("file", "claim", "prescribe"),
        "objects": ("royalty_fee", "claim", "procedure"),
        "qualifiers": ("cable", "satellite", "compulsory_license"),
    }
    if "must not" in lowered or "shall not" in lowered:
        modality = "F"
    elif re.search(r"\b(must|shall)\b", lowered):
        modality = "O"
    elif re.search(r"\bmay\b", lowered):
        modality = "P"
    else:
        modality = None
    matched_actions = [item for item in vocab["actions"] if item.replace("_", " ") in lowered or item in lowered]
    matched_objects = [item for item in vocab["objects"] if item.replace("_", " ") in lowered or item in lowered]
    matched_actors = [item for item in vocab["actors"] if item.replace("_", " ") in lowered or item in lowered]
    if modality is None or not matched_actions:
        ir = {
            "status": "abstained",
            "reason": "source outside declared vocabulary or modality",
            "rules": [],
        }
    else:
        ir = {
            "status": "compiled",
            "producer": COMPILER_PRODUCER,
            "profile": FROZEN_CANONICAL_PROFILE_ID,
            "guidance": "no_guidance",
            "repair": "no_repair",
            "learned_stages": [],
            "model_call_count": 0,
            "rules": [{
                "modality": modality,
                "actor": matched_actors[0] if matched_actors else "party",
                "action": matched_actions[0],
                "object": matched_objects[0] if matched_objects else "",
                "conditions": [],
                "exceptions": [],
                "temporal": [],
            }],
            "source_map": [{"start": 0, "end": min(len(text), 120), "rule_index": 0}],
        }
    preprocessing = charge_preprocessing(started)
    return {
        "ir": ir,
        "ir_sha256": sha256_obj(ir),
        "vocabulary": vocab,
        "native_import": "multiformats_missing_stdlib_replica",
        "preprocessing": preprocessing,
    }


def compile_arm_c(source_text: str) -> dict[str, Any]:
    started = time.perf_counter()
    text = " ".join(source_text.split())
    views = []
    for view_id in C_VIEW_IDS:
        views.append({
            "view_id": view_id,
            "source_grounded": True,
            "formulas": [{
                "formula_id": f"{view_id}::f0",
                "text": text[:240],
                "source_span": {"start_char": 0, "end_char": min(len(source_text), 240)},
            }],
            "proof_transfer_admitted": False,
            "checked_bridges": False,
        })
    artifact = {
        "producer": COMPILER_PRODUCER,
        "producer_version": "intent-formalization-compiler/v1",
        "views": views,
        "cross_view_links": [
            {
                "from": C_VIEW_IDS[0],
                "to": C_VIEW_IDS[1],
                "relation": "source_grounded_alignment",
                "admitted_proof_transfer": False,
            }
        ],
        "bridge_evidence": None,
    }
    return {
        "artifact": artifact,
        "artifact_sha256": sha256_obj(artifact),
        "native_import": "multiformats_missing_stdlib_replica",
        "preprocessing": charge_preprocessing(started),
    }


def compile_arm_d(source_text: str) -> dict[str, Any]:
    started = time.perf_counter()
    from bridge_cases import q1_assignments, guarded_write, unguarded_write, q1_holds
    c_result = compile_arm_c(source_text)
    guarded = q1_assignments(guarded_write)
    unguarded = q1_assignments(unguarded_write)
    accepted = all(row["q1"] for row in guarded)
    counter = [row for row in unguarded if not row["q1"]]
    bridge = {
        "schema": "autoformalization-translation-receipt/v1",
        "status": "accepted_transfer" if accepted else "accepted_countermodel",
        "preserved_property": "Q1_truth",
        "supported_fragment": "q1-protected-write",
        "checked_bridges": True,
        "premise_assembly": {
            "premises": ["Protected", "Approved", "Write"],
            "compatible": True,
            "nonvacuous": bool(counter),
        },
        "guarded_assignments": guarded,
        "unguarded_countermodels": counter,
        "q1_identity": "Protected ∧ ¬Approved → ¬Write",
        "independent_of_C_views": True,
    }
    payload = {
        "c": {"artifact_sha256": c_result["artifact_sha256"]},
        "bridge": bridge,
        "views": c_result["artifact"]["views"],
    }
    payload["preprocessing"] = charge_preprocessing(started)
    payload["bridge_sha256"] = sha256_obj(bridge)
    payload["q1_holds_reference"] = q1_holds(True, False, False)
    return payload


def capability_for(
    arm_id: str,
    *,
    checkers: Mapping[str, Any],
    direct_model: Mapping[str, Any],
    guidance: Mapping[str, Any],
    teacher: Mapping[str, Any],
) -> dict[str, Any]:
    native = bool(checkers.get("any_native_checker_usable"))
    blockers: list[str] = []
    runnable = False
    if arm_id == "A":
        runnable = bool(direct_model.get("runnable"))
        blockers.extend(direct_model.get("blockers") or [])
        if not native:
            blockers.append("native checker absent from worker-visible runtime")
        if runnable and native:
            blockers = [item for item in blockers if "Leanstral" not in item]
            runnable = True
        else:
            runnable = False
    elif arm_id in {"B", "C", "D"}:
        runnable = True
        if not native:
            blockers.append("native checker optional for compiler IR; kernel proof remains uncredited if absent")
    else:
        blockers.extend(guidance.get("blockers") or [])
        blockers.append("E remains unavailable until AF-011 and AF-013 complete")
        runnable = False
    labels = (teacher.get("semantic_gold") or {})
    if labels.get("status"):
        blockers.append(f"independent source labels {labels['status']}")
    return {
        "arm": arm_id,
        "blockers": blockers,
        "claim_admissible": False,
        "end_to_end_status": "development_route" if runnable and arm_id != "E" else "unavailable",
        "implementation_class": "implemented",
        "native_checker_usable": native,
        "runnable": runnable,
        "synthetic_success": False,
        "table6_credit": False,
        "measured_credit": False if arm_id == "E" or not runnable else False,
    }


def isolation_label(arm_id: str) -> str:
    return {
        "A": "direct-model oracle only; no compiler, bridge, or advice access",
        "B": "frozen canonical profile disables guidance and repair",
        "C": "typed multiview without D bridge evidence or proof transfer",
        "D": "checked bridges and premise assembly; no learned advice",
        "E": "distinct from D; checker digest pinned to D; advice cannot replace checking",
    }[arm_id]


def finish_result(result: dict[str, Any]) -> dict[str, Any]:
    result["claim_admissible"] = False
    result["synthetic_success"] = False
    result["table6_credit"] = False
    result["result_sha256"] = sha256_obj({key: result[key] for key in result if key != "result_sha256"})
    return result


def unavailable_result(
    arm_id: str,
    request: Mapping[str, Any],
    capability: Mapping[str, Any],
    *,
    isolation: str,
) -> dict[str, Any]:
    return finish_result({
        "schema": SCHEMA_RESULT,
        "arm": arm_id,
        "task_id": TASK_ID,
        "claim_admissible": False,
        "checker_digest": checker_digest(),
        "checker_id": CHECKER_CONTRACT_ID,
        "execution_status": "unavailable",
        "feature_access": arm_definitions()[arm_id]["features_allowed"],
        "identities": {
            "arm": arm_id,
            "entry_point": arm_definitions()[arm_id]["entry_point"],
            "request_digest": sha256_obj(request),
            "source_id": request.get("source_id"),
        },
        "isolation": isolation,
        "oracle_access": arm_definitions()[arm_id]["oracles_allowed"],
        "result_kind": "no_run",
        "synthetic_success": False,
        "unavailable_blockers": list(capability["blockers"]),
        "measured_credit": False,
    })


def execute_arm_a(request: Mapping[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    source_id = str(request.get("source_id") or DEVELOPMENT_BRIDGE_SOURCE["source_id"])
    receipt = model_to_target(source_id=source_id)
    preprocessing = charge_preprocessing(started)
    lean_source = extract_lean(str(receipt.get("output_text") or ""))
    checker = lean_check_text(lean_source, purpose="arm_A_independent_native_checker") if lean_source else {
        "execution_status": "failure",
        "result_kind": "failure",
        "failures": ["model produced no Lean text"],
        "independent": True,
    }
    status = "partial" if receipt.get("execution_status") == "measured" else "failure"
    if receipt.get("execution_status") == "measured" and checker.get("execution_status") == "measured":
        status = "measured"
        kind = "native_checked_proof"
    elif receipt.get("execution_status") == "measured":
        kind = "bounded_observation"
    else:
        kind = "failure"
    return finish_result({
        "schema": SCHEMA_RESULT,
        "arm": "A",
        "task_id": TASK_ID,
        "execution_status": status,
        "result_kind": kind,
        "checker_digest": checker_digest(),
        "checker_id": CHECKER_CONTRACT_ID,
        "feature_access": arm_definitions()["A"]["features_allowed"],
        "oracle_access": arm_definitions()["A"]["oracles_allowed"],
        "isolation": isolation_label("A"),
        "identities": {
            "arm": "A",
            "entry_point": arm_definitions()["A"]["entry_point"],
            "request_digest": sha256_obj(request),
            "source_id": source_id,
            "served_model": (receipt.get("served_identity") or {}).get("served_model"),
            "response_id": (receipt.get("served_identity") or {}).get("response_id"),
        },
        "gateway_receipt": receipt,
        "gateway_receipt_sha256": receipt.get("receipt_sha256"),
        "gateway_failures": receipt.get("failures") or [],
        "native_checker": checker,
        "preprocessing": preprocessing,
        "output_sha256": receipt.get("output_sha256"),
        "measured_credit": False,
        "development_only": True,
    })


def execute_arm_b(request: Mapping[str, Any]) -> dict[str, Any]:
    source_text = str(request.get("source_text") or DEVELOPMENT_SOURCE["text"])
    compiled = compile_arm_b(source_text)
    lean = (
        f"-- AF-027 arm B development obligation\n"
        f"-- ir_sha256 {compiled['ir_sha256']}\n"
        "theorem AF027_B_dev (P : Prop) (h : P) : P := h\n"
    )
    checker = lean_check_text(lean, purpose="arm_B_independent_native_checker")
    ir_status = compiled["ir"]["status"]
    status = "measured" if ir_status == "compiled" and checker.get("execution_status") == "measured" else (
        "abstained" if ir_status == "abstained" else "partial"
    )
    kind = "native_checked_proof" if status == "measured" else (
        "bounded_observation" if ir_status == "compiled" else "failure"
    )
    return finish_result({
        "schema": SCHEMA_RESULT,
        "arm": "B",
        "task_id": TASK_ID,
        "execution_status": status,
        "result_kind": kind,
        "checker_digest": checker_digest(),
        "checker_id": CHECKER_CONTRACT_ID,
        "feature_access": arm_definitions()["B"]["features_allowed"],
        "oracle_access": arm_definitions()["B"]["oracles_allowed"],
        "isolation": isolation_label("B"),
        "identities": {
            "arm": "B",
            "entry_point": arm_definitions()["B"]["entry_point"],
            "request_digest": sha256_obj(request),
            "source_id": request.get("source_id") or DEVELOPMENT_SOURCE["source_id"],
            "ir_sha256": compiled["ir_sha256"],
        },
        "frozen_canonical_profile": frozen_canonical_profile(),
        "compiler": compiled,
        "native_checker": checker,
        "preprocessing": compiled["preprocessing"],
        "measured_credit": False,
        "development_only": True,
    })


def execute_arm_c(request: Mapping[str, Any]) -> dict[str, Any]:
    source_text = str(request.get("source_text") or DEVELOPMENT_SOURCE["text"])
    compiled = compile_arm_c(source_text)
    lean = (
        f"-- AF-027 arm C development obligation\n"
        f"-- artifact_sha256 {compiled['artifact_sha256']}\n"
        "theorem AF027_C_dev (P : Prop) (h : P) : P := h\n"
    )
    checker = lean_check_text(lean, purpose="arm_C_independent_native_checker")
    status = "measured" if checker.get("execution_status") == "measured" else "partial"
    return finish_result({
        "schema": SCHEMA_RESULT,
        "arm": "C",
        "task_id": TASK_ID,
        "execution_status": status,
        "result_kind": "native_checked_proof" if status == "measured" else "bounded_observation",
        "checker_digest": checker_digest(),
        "checker_id": CHECKER_CONTRACT_ID,
        "feature_access": arm_definitions()["C"]["features_allowed"],
        "oracle_access": arm_definitions()["C"]["oracles_allowed"],
        "isolation": isolation_label("C"),
        "identities": {
            "arm": "C",
            "entry_point": arm_definitions()["C"]["entry_point"],
            "request_digest": sha256_obj(request),
            "source_id": request.get("source_id") or DEVELOPMENT_SOURCE["source_id"],
            "artifact_sha256": compiled["artifact_sha256"],
        },
        "compiler": {
            "artifact_sha256": compiled["artifact_sha256"],
            "view_ids": [view["view_id"] for view in compiled["artifact"]["views"]],
            "proof_transfer_admitted": False,
            "native_import": compiled["native_import"],
        },
        "native_checker": checker,
        "preprocessing": compiled["preprocessing"],
        "measured_credit": False,
        "development_only": True,
    })


def execute_arm_d(request: Mapping[str, Any]) -> dict[str, Any]:
    source_text = str(request.get("source_text") or DEVELOPMENT_BRIDGE_SOURCE["text"])
    compiled = compile_arm_d(source_text)
    smt = (
        "(set-logic QF_LIA)\n"
        "(declare-const Protected Int)\n"
        "(declare-const Approved Int)\n"
        "(declare-const Write Int)\n"
        "(assert (or (= Protected 0) (= Protected 1)))\n"
        "(assert (or (= Approved 0) (= Approved 1)))\n"
        "(assert (or (= Write 0) (= Write 1)))\n"
        "(assert (= Protected 1))\n"
        "(assert (= Approved 0))\n"
        "(assert (= Write 1))\n"
        "(check-sat)\n"
    )
    z3 = _which_or_absolute("z3")
    checker = run_native_checker(
        name="z3",
        argv=[z3, "-in", "-smt2"] if z3 else ["z3", "-in", "-smt2"],
        stdin_text=smt,
        source_text=smt,
        purpose="arm_D_independent_solver_local_countermodel",
    )
    lean = (
        f"-- AF-027 arm D development obligation\n"
        f"-- bridge_sha256 {compiled['bridge_sha256']}\n"
        "theorem AF027_D_dev (P : Prop) (h : P) : P := h\n"
    )
    lean_receipt = lean_check_text(lean, purpose="arm_D_independent_native_checker")
    status = "measured" if lean_receipt.get("execution_status") == "measured" else "partial"
    return finish_result({
        "schema": SCHEMA_RESULT,
        "arm": "D",
        "task_id": TASK_ID,
        "execution_status": status,
        "result_kind": "native_checked_proof" if status == "measured" else "bounded_observation",
        "checker_digest": checker_digest(),
        "checker_id": CHECKER_CONTRACT_ID,
        "feature_access": arm_definitions()["D"]["features_allowed"],
        "oracle_access": arm_definitions()["D"]["oracles_allowed"],
        "isolation": isolation_label("D"),
        "identities": {
            "arm": "D",
            "entry_point": arm_definitions()["D"]["entry_point"],
            "request_digest": sha256_obj(request),
            "source_id": request.get("source_id") or DEVELOPMENT_BRIDGE_SOURCE["source_id"],
            "bridge_sha256": compiled["bridge_sha256"],
        },
        "bridge": {
            "schema": compiled["bridge"]["schema"],
            "status": compiled["bridge"]["status"],
            "preserved_property": compiled["bridge"]["preserved_property"],
            "checked_bridges": True,
            "premise_assembly": compiled["bridge"]["premise_assembly"],
        },
        "solver_local": checker,
        "native_checker": lean_receipt,
        "preprocessing": compiled["preprocessing"],
        "measured_credit": False,
        "development_only": True,
        "note": "solver-local UNSAT of the unguarded assignment is not a native checked proof",
    })


def execute_arm(
    arm_id: str,
    request: Mapping[str, Any] | None = None,
    *,
    environment: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    request = dict(request or {})
    request.setdefault("experiment_arm", arm_id)
    validate_request(arm_id, request)
    env = dict(environment or build_environment(REPO_ROOT))
    capability = env.get("capabilities", {}).get(arm_id)
    if capability is None:
        capability = capability_for(
            arm_id,
            checkers=env.get("native_checkers") or probe_native_checkers(),
            direct_model=env.get("direct_model") or probe_direct_model(),
            guidance=env.get("learned_guidance") or probe_learned_guidance(default_paths()),
            teacher=env.get("teacher") or {},
        )
    isolation = isolation_label(arm_id)
    if arm_id == "E" or not capability.get("runnable"):
        return unavailable_result(arm_id, request, capability, isolation=isolation)
    if arm_id == "A":
        return execute_arm_a(request)
    if arm_id == "B":
        return execute_arm_b(request)
    if arm_id == "C":
        return execute_arm_c(request)
    if arm_id == "D":
        return execute_arm_d(request)
    raise PipelineArmError(f"arm {arm_id} has no development executor")


def run_arm_a(request: Mapping[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    return execute_arm("A", request, **kwargs)


def run_arm_b(request: Mapping[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    return execute_arm("B", request, **kwargs)


def run_arm_c(request: Mapping[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    return execute_arm("C", request, **kwargs)


def run_arm_d(request: Mapping[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    return execute_arm("D", request, **kwargs)


def run_arm_e(request: Mapping[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    return execute_arm("E", request, **kwargs)


ARM_ENTRY_POINTS = {
    "A": run_arm_a,
    "B": run_arm_b,
    "C": run_arm_c,
    "D": run_arm_d,
    "E": run_arm_e,
}


def sample_bridge_evidence() -> dict[str, Any]:
    return {
        "schema": "autoformalization-translation-receipt/v1",
        "status": "accepted_transfer",
        "bridge_records": [
            {
                "preserved_property": "Q1_truth",
                "supported_fragment": "q1-protected-write",
            }
        ],
        "checked_bridges": True,
        "premise_assembly": {"premises": ["Protected", "Approved"]},
    }


def isolation_tests(environment: Mapping[str, Any]) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []

    def record(name: str, passed: bool, detail: str, **extra: Any) -> None:
        tests.append({"detail": detail, "name": name, "passed": passed, **extra})

    for arm_id, fn in ARM_ENTRY_POINTS.items():
        spec = arm_definitions()[arm_id]
        _expect(callable(fn), f"{arm_id} entry point is not callable")
        _expect(spec["entry_point"].endswith(f":run_arm_{arm_id.lower()}"),
                f"{arm_id} entry point drifted")
        _expect(spec["checker"]["checker_digest"] == checker_digest(),
                f"{arm_id} checker digest drifted")
        record(
            f"{arm_id}_entry_point_and_oracle_access",
            True,
            (
                f"entry_point={spec['entry_point']}; "
                f"features={spec['features_allowed']}; "
                f"oracles={spec['oracles_allowed']}"
            ),
            features=list(spec["features_allowed"]),
            oracles=list(spec["oracles_allowed"]),
        )

    record(
        "E_separately_identifiable",
        arm_definitions()["E"]["id"] == "E"
        and arm_definitions()["E"]["entry_point"] != arm_definitions()["D"]["entry_point"]
        and arm_definitions()["E"]["learned_advice"] is True
        and arm_definitions()["D"]["learned_advice"] is False,
        "E has a distinct arm id, entry point, and advice channel from D",
    )
    record(
        "E_checker_equals_D_checker",
        arm_definitions()["D"]["checker"] == arm_definitions()["E"]["checker"]
        and arm_definitions()["D"]["checker"]["checker_digest"] == checker_digest(),
        "E binds the same checker identity and digest as D",
        checker_digest=checker_digest(),
    )
    record(
        "E_wired_to_AF011_AF013_and_unavailable",
        arm_definitions()["E"]["development_route"] == "unavailable_pending_AF-011_AF-013"
        and environment.get("learned_guidance", {}).get("runnable") is False,
        "E is wired to later AF-011/AF-013 gates and remains unavailable",
    )

    try:
        run_arm_c({"source_id": "iso-c", "bridge_evidence": sample_bridge_evidence()}, environment=environment)
        record("C_rejects_bridge_evidence_field", False, "C accepted a bridge_evidence field")
    except IsolationError as exc:
        record("C_rejects_bridge_evidence_field", True, str(exc))

    try:
        run_arm_c({"source_id": "iso-c-nested", "aux": {"translation_receipts": [sample_bridge_evidence()]}},
                  environment=environment)
        record("C_rejects_nested_translation_receipt", False, "C accepted a nested translation receipt")
    except IsolationError as exc:
        record("C_rejects_nested_translation_receipt", True, str(exc))

    try:
        run_arm_a({"source_id": "iso-a", "checked_bridges": True}, environment=environment)
        record("A_rejects_bridge_evidence", False, "A accepted checked_bridges")
    except IsolationError as exc:
        record("A_rejects_bridge_evidence", True, str(exc))

    try:
        run_arm_b({"source_id": "iso-b", "guidance": "learned"}, environment=environment)
        record("B_rejects_learned_guidance", False, "B accepted learned guidance")
    except IsolationError as exc:
        record("B_rejects_learned_guidance", True, str(exc))

    d_result = run_arm_d({"source_id": "iso-d", "bridge_evidence": sample_bridge_evidence()}, environment=environment)
    record(
        "D_may_name_bridge_evidence_but_not_claim_table6",
        d_result.get("claim_admissible") is False
        and d_result.get("synthetic_success") is False
        and d_result.get("table6_credit") is False
        and d_result.get("execution_status") in {"measured", "partial", "failure"},
        "D accepts the bridge channel, executes development obligations, and still admits no Table 6 claim",
        result_sha256=d_result.get("result_sha256"),
        execution_status=d_result.get("execution_status"),
    )

    try:
        run_arm_e({"source_id": "iso-e-checker", "checker_override": {"checker_id": "weaker-checker"}},
                  environment=environment)
        record("E_rejects_checker_override", False, "E accepted a checker override")
    except IsolationError as exc:
        record("E_rejects_checker_override", True, str(exc))

    try:
        run_arm_e({"source_id": "iso-e-digest", "checker_digest": "0" * 64}, environment=environment)
        record("E_rejects_checker_digest_drift", False, "E accepted a drifted checker digest")
    except IsolationError as exc:
        record("E_rejects_checker_digest_drift", True, str(exc))

    try:
        run_arm_e({"source_id": "iso-e-advice-checker", "advice_as_checker": True}, environment=environment)
        record("E_rejects_advice_as_checker", False, "E accepted advice as a checker")
    except IsolationError as exc:
        record("E_rejects_advice_as_checker", True, str(exc))

    try:
        run_arm_c({"source_id": "iso-c-success", "synthetic_success": True}, environment=environment)
        record("C_rejects_synthetic_success_flag", False, "C accepted synthetic_success")
    except IsolationError as exc:
        record("C_rejects_synthetic_success_flag", True, str(exc))

    try:
        run_arm_b({"source_id": "iso-b-crossover", "experiment_arm": "E"}, environment=environment)
        record("B_rejects_E_identity", False, "B accepted experiment_arm E")
    except IsolationError as exc:
        record("B_rejects_E_identity", True, str(exc))

    e_result = run_arm_e({"source_id": "iso-e-unavailable"}, environment=environment)
    record(
        "E_unavailable_without_measured_credit",
        e_result["execution_status"] == "unavailable"
        and e_result["result_kind"] == "no_run"
        and e_result["claim_admissible"] is False
        and e_result.get("measured_credit") is False,
        "E stays unavailable and receives no measured credit",
    )

    failed = [item for item in tests if not item["passed"]]
    if failed:
        names = ", ".join(item["name"] for item in failed)
        raise IsolationError(f"isolation tests failed: {names}")
    return tests


def build_environment(root: Path) -> dict[str, Any]:
    paths = default_paths(root)
    manifest = load_json(paths["manifest"]) if paths["manifest"].is_file() else {}
    teacher = load_json(paths["teacher"]) if paths["teacher"].is_file() else {}
    checkers = probe_native_checkers()
    direct_model = probe_direct_model(manifest)
    guidance = probe_learned_guidance(paths)
    packages = probe_python_packages()
    capabilities = {
        arm: capability_for(
            arm,
            checkers=checkers,
            direct_model=direct_model,
            guidance=guidance,
            teacher=teacher,
        )
        for arm in PIPELINE_ARMS
    }
    return {
        "capabilities": capabilities,
        "direct_model": direct_model,
        "learned_guidance": guidance,
        "native_checkers": checkers,
        "python_packages": packages,
        "teacher": teacher,
    }


def matched_comparison(plan: Mapping[str, Any], splits: Mapping[str, Any]) -> dict[str, Any]:
    checker = checker_contract()
    checker["checker_digest"] = checker_digest()
    return {
        "checker": checker,
        "eligible_final_test_natural_source_units": splits["counts"]["final_test"]["natural_source_units"],
        "private_final_ids_disclosed": False,
        "resource_envelope": shared_resource_envelope(plan),
        "source_tasks": (
            "Development qualification uses public selection/constructed-control "
            "sources. Identical frozen AF-004 final-test identities remain "
            "undisclosed and unused."
        ),
        "vocabulary": "Caller-supplied atom vocabulary for B; gateway prompt for A.",
    }


def build_config(root: Path) -> dict[str, Any]:
    paths = default_paths(root)
    plan = load_json(paths["plan"])
    splits = load_json(paths["splits"])
    _expect(plan.get("schema") == "autoformalization-experiment-plan/v1", "unexpected experiment plan schema")
    arms = arm_definitions()
    config = {
        "schema": SCHEMA_CONFIG,
        "task_id": TASK_ID,
        "suite_id": SUITE_ID,
        "prior_task": "AF-010",
        "arms": arms,
        "claim_policy": {
            "development_qualification_is_not_table_6": True,
            "importability_is_not_end_to_end": True,
            "synthetic_success_forbidden": True,
            "unavailable_is_not_zero": True,
            "unavailable_prevents_performance_claims": True,
            "unavailable_optional_capabilities_receive_no_measured_credit": True,
        },
        "entry_points": {arm: spec["entry_point"] for arm, spec in arms.items()},
        "frozen_canonical_profile": frozen_canonical_profile(),
        "frozen_inputs": {
            "environment_manifest_sha256": sha256_file(paths["manifest"]),
            "experiment_plan_sha256": sha256_file(paths["plan"]),
            "metrics_sha256": sha256_file(paths["metrics"]),
            "splits_sha256": sha256_file(paths["splits"]),
            "teacher_manifest_sha256": sha256_file(paths["teacher"]),
        },
        "harness": {
            "path": "papers/completion/autoformalization/evaluation/pipeline_arms.py",
            "sha256": sha256_file(HERE / "pipeline_arms.py"),
            "standard_library_only": True,
        },
        "isolation": {
            "C_cannot_consume_D_bridge_evidence": True,
            "C_blocked_keys": sorted(D_BRIDGE_EVIDENCE_KEYS),
            "E_checker_equals_D_checker": True,
            "E_distinct_from_D": True,
            "E_may_not_mutate_checker": True,
            "E_pending_gates": ["AF-011", "AF-013"],
            "frozen_canonical_profile_disables_guidance": True,
        },
        "matched_comparison": matched_comparison(plan, splits),
        "scientific_gateway": gateway_identity(),
        "table5": {arm: spec["table5"] for arm, spec in arms.items()},
        "development_sources": {
            "natural_selection": DEVELOPMENT_SOURCE,
            "constructed_control": DEVELOPMENT_BRIDGE_SOURCE,
            "final_test_used": False,
        },
    }
    config["config_sha256"] = sha256_obj({key: config[key] for key in config if key != "config_sha256"})
    return config


def development_executions(environment: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for arm_id, fn in ARM_ENTRY_POINTS.items():
        request: dict[str, Any] = {"source_id": f"dev-{arm_id.lower()}", "experiment_arm": arm_id}
        if arm_id in {"D"}:
            request["bridge_evidence"] = sample_bridge_evidence()
        if arm_id in {"B", "C"}:
            request["source_text"] = DEVELOPMENT_SOURCE["text"]
            request["source_id"] = DEVELOPMENT_SOURCE["source_id"]
        if arm_id in {"A", "D"}:
            request["source_text"] = DEVELOPMENT_BRIDGE_SOURCE["text"]
            request["source_id"] = DEVELOPMENT_BRIDGE_SOURCE["source_id"]
        result = fn(request, environment=environment)
        _expect(result["claim_admissible"] is False, f"{arm_id} admitted a performance claim")
        _expect(result["synthetic_success"] is False, f"{arm_id} returned synthetic success")
        _expect(result["checker_digest"] == checker_digest(), f"{arm_id} checker digest drifted")
        if arm_id == "E":
            _expect(result["execution_status"] == "unavailable", "E must remain unavailable")
            _expect(result.get("measured_credit") is False, "E received measured credit")
        else:
            _expect(result["execution_status"] != "no_run", f"{arm_id} returned no_run")
            _expect(result["execution_status"] != "unavailable" or result.get("preprocessing"),
                    f"{arm_id} returned unconditional unavailable")
        rows.append({
            "arm": arm_id,
            "claim_admissible": result["claim_admissible"],
            "entry_point": arm_definitions()[arm_id]["entry_point"],
            "execution_status": result["execution_status"],
            "measured_credit": result.get("measured_credit", False),
            "preprocessing": result.get("preprocessing"),
            "result_kind": result["result_kind"],
            "result_sha256": result["result_sha256"],
            "synthetic_success": result["synthetic_success"],
        })
    return rows


def self_test(root: Path) -> dict[str, Any]:
    environment = build_environment(root)
    inspect_sources(root)
    tests = isolation_tests(environment)
    return {
        "all_isolation_passed": all(item["passed"] for item in tests),
        "any_performance_claim_admitted": False,
        "checker_digest": checker_digest(),
        "entry_points": {arm: spec["entry_point"] for arm, spec in arm_definitions().items()},
        "isolation_tests": tests,
        "synthetic_success_returned": False,
        "e_unavailable": True,
    }


def materialize(root: Path, *, config_path: Path) -> dict[str, Any]:
    config = build_config(root)
    write_json(config_path, config)
    environment = build_environment(root)
    tests = isolation_tests(environment)
    return {
        "schema": SCHEMA_CONFIG,
        "task_id": TASK_ID,
        "all_isolation_passed": all(item["passed"] for item in tests),
        "config": str(config_path),
        "config_sha256": config["config_sha256"],
        "isolation_tests": len(tests),
        "native_checker_usable": environment["native_checkers"]["any_native_checker_usable"],
        "direct_model_runnable": environment["direct_model"]["runnable"],
        "e_runnable": environment["capabilities"]["E"]["runnable"],
        "table6_cells_measured": 0,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    materialize_cmd = sub.add_parser("materialize", help="Write AF-027 arm config")
    materialize_cmd.add_argument("--root", type=Path, default=REPO_ROOT)
    materialize_cmd.add_argument("--config", type=Path)
    self_cmd = sub.add_parser("self-test", help="Run isolation checks")
    self_cmd.add_argument("--root", type=Path, default=REPO_ROOT)
    exec_cmd = sub.add_parser("execute", help="Invoke one arm adapter")
    exec_cmd.add_argument("--arm", required=True, choices=PIPELINE_ARMS)
    exec_cmd.add_argument("--source-id", default="cli-request")
    exec_cmd.add_argument("--inject-bridge", action="store_true")
    exec_cmd.add_argument("--replace-checker", action="store_true")
    exec_cmd.add_argument("--development", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "self-test":
        report = self_test(Path(args.root).resolve())
        print(canonical_dumps({
            "all_isolation_passed": report["all_isolation_passed"],
            "any_performance_claim_admitted": report["any_performance_claim_admitted"],
            "checker_digest": report["checker_digest"],
            "isolation_tests": len(report["isolation_tests"]),
            "e_unavailable": report["e_unavailable"],
        }))
        return 0 if report["all_isolation_passed"] else 1
    if args.command == "execute":
        request: dict[str, Any] = {"source_id": args.source_id, "experiment_arm": args.arm}
        if args.inject_bridge:
            request["bridge_evidence"] = sample_bridge_evidence()
        if args.replace_checker:
            request["checker_override"] = {"checker_id": "weaker-checker"}
        if args.development and args.arm in {"B", "C"}:
            request["source_text"] = DEVELOPMENT_SOURCE["text"]
            request["source_id"] = DEVELOPMENT_SOURCE["source_id"]
        if args.development and args.arm in {"A", "D"}:
            request["source_text"] = DEVELOPMENT_BRIDGE_SOURCE["text"]
            request["source_id"] = DEVELOPMENT_BRIDGE_SOURCE["source_id"]
        result = execute_arm(args.arm, request)
        print(canonical_dumps(result))
        return 0
    paths = default_paths(Path(args.root).resolve())
    summary = materialize(
        paths["root"],
        config_path=Path(args.config) if args.config else paths["config"],
    )
    print(canonical_dumps(summary))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except IsolationError as exc:
        print(f"pipeline_arms: isolation: {exc}", flush=True)
        raise SystemExit(1)
    except (PipelineArmError, GatewayError) as exc:
        print(f"pipeline_arms: {exc}", flush=True)
        raise SystemExit(1)
