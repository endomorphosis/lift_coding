#!/usr/bin/env python3
"""Matched A–E pipeline adapters and fail-closed preflight for AF-010.

This harness implements explicit, separately identifiable adapters for the
paper's Table 5 conditions under one shared source-task, vocabulary, checker,
and resource envelope:

* A — direct model-to-target formalization
* B — deterministic bounded compiler (frozen canonical profile; no guidance)
* C — typed source-grounded multiview without admitted proof transfer
* D — C plus checked property bridges and compatible premise assembly
* E — D plus pinned bounded learned advice; checker identical to D

It does not execute the AF-016 source-to-proof benchmark, invent Table 6
cells, or treat importability as end-to-end success. Native modules are
inspected and optionally imported as capability probes. Direct-model and
stable-guidance paths are wired only when a real service or promotion
receipt is present. Unavailable routes return ``unavailable`` / ``no_run``
with ``claim_admissible=false``; they never return synthetic success.

C cannot consume D bridge evidence. E is a distinct arm and cannot replace
or mutate the shared checker. Standard library only at runtime.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_CONFIG = "autoformalization-pipeline-arms/v1"
SCHEMA_PREFLIGHT = "autoformalization-pipeline-arm-preflight/v1"
SCHEMA_RESULT = "autoformalization-pipeline-arm-result/v1"
TASK_ID = "AF-010"
SUITE_ID = "AF-010-matched-pipeline-arms"
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
DIRECT_MODEL_ENV_VARS = (
    "OPENAI_API_KEY", "OPENAI_BASE_URL", "ANTHROPIC_API_KEY",
    "LEANSTRAL_ENDPOINT", "LEANSTRAL_API_KEY", "HF_TOKEN",
    "AUTOFORMALIZATION_DIRECT_MODEL_ENDPOINT",
)
HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
REPO_ROOT = PAPER_ROOT.parents[2]
DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"

INSPECTED_SOURCES = {
    "canonical_roundtrip.py": {
        "path": "external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_roundtrip.py",
        "imported": False,
        "role": "B/C deterministic compiler and source-withheld round-trip composition",
        "note": (
            "Frozen production composition disables learned stages, fallback, and "
            "model calls. Inspected, not executed as Table 6 evidence."
        ),
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
        "note": (
            "Advisor only. Promotion requires a source-free export, canonical "
            "contracts, and paired canary evidence. Absent receipts keep E unavailable."
        ),
    },
    "intent_formalization_compiler.py": {
        "path": "external/ipfs_datasets/ipfs_datasets_py/logic/intent_ir/formalize/compiler.py",
        "imported": False,
        "role": "C typed source-grounded multi-view compiler (AF-003 selected entry)",
        "note": "Syntactic lowering to named views; does not invoke a model or prover.",
    },
    "bridge_cases.py": {
        "path": "papers/completion/autoformalization/evaluation/bridge_cases.py",
        "imported": False,
        "role": "D checked-bridge obligations and translation-receipt schema",
        "note": "AF-015 finite bridges are D-only evidence. C must not consume them.",
    },
}

IMPORT_PROBES = (
    "ipfs_datasets_py.logic.legal_ir.canonical_roundtrip",
    "ipfs_datasets_py.logic.legal_ir.canonical_compiler",
    "ipfs_datasets_py.logic.integration.reasoning.legal_ir_learned_guidance",
)


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


def matched_comparison(plan: Mapping[str, Any], splits: Mapping[str, Any]) -> dict[str, Any]:
    checker = checker_contract()
    checker["checker_digest"] = checker_digest()
    return {
        "checker": checker,
        "eligible_final_test_natural_source_units": splits["counts"]["final_test"]["natural_source_units"],
        "private_final_ids_disclosed": False,
        "resource_envelope": shared_resource_envelope(plan),
        "source_tasks": (
            "Identical frozen AF-004 final-test source identities for every A–E "
            "comparison. Individual IDs remain undisclosed in this preflight."
        ),
        "vocabulary": (
            "Caller-supplied atom vocabulary. Dataset compiler/view targets are "
            "not generated (teacher_manifest.compiler_and_view_targets)."
        ),
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
                "environment_manifest.selected_entry_points.direct_generative_model",
            ],
            "features_allowed": [
                "declared_vocabulary",
                "source_text",
            ],
            "oracles_allowed": [
                "direct_model_inference",
                "independent_facet_adjudication",
                "target_checker",
            ],
            "features_blocked": [
                "checked_bridges",
                "compiler_views",
                "learned_advice",
                "premise_assembly",
                "sample_memory",
            ],
            "checker": checker,
            "uses_frozen_canonical_profile": False,
            "consumes_bridge_evidence": False,
            "learned_advice": False,
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
                "ipfs_datasets_py.logic.legal_ir.canonical_roundtrip.CanonicalSemanticRoundTrip",
            ],
            "features_allowed": [
                "declared_vocabulary",
                "explicit_abstention",
                "source_maps",
                "source_text",
                "typed_deontic_ir",
            ],
            "oracles_allowed": [
                "deterministic_bounded_compiler",
                "independent_facet_adjudication",
                "target_checker",
            ],
            "features_blocked": [
                "checked_bridges",
                "direct_model_inference",
                "learned_advice",
                "learned_guidance",
                "repair",
                "sample_memory",
            ],
            "checker": checker,
            "uses_frozen_canonical_profile": True,
            "consumes_bridge_evidence": False,
            "learned_advice": False,
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
                "declared_vocabulary",
                "source_grounding",
                "source_maps",
                "source_text",
                "typed_multiview",
            ],
            "oracles_allowed": [
                "independent_facet_adjudication",
                "native_proof_checker_where_supported",
                "pinned_compiler_elaborator",
            ],
            "features_blocked": [
                "checked_bridges",
                "compatible_premise_assembly",
                "cross_view_proof_transfer",
                "D_bridge_evidence",
                "learned_advice",
                "sample_memory",
            ],
            "checker": checker,
            "uses_frozen_canonical_profile": False,
            "consumes_bridge_evidence": False,
            "learned_advice": False,
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
                "ipfs_datasets_py.logic.intent_ir.formalize.compiler.IntentFormalizationCompiler",
            ],
            "features_allowed": [
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
                "pinned_compiler_elaborator",
                "premise_compatibility_nonvacuity",
            ],
            "features_blocked": [
                "learned_advice",
                "sample_memory",
            ],
            "checker": checker,
            "uses_frozen_canonical_profile": False,
            "consumes_bridge_evidence": True,
            "learned_advice": False,
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
                "checker_mutation",
                "sample_memory",
                "unpinned_advice",
            ],
            "checker": checker,
            "uses_frozen_canonical_profile": False,
            "consumes_bridge_evidence": True,
            "learned_advice": True,
            "advice_cannot_replace_checking": True,
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
            "imported": False,
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


def probe_native_checkers() -> dict[str, Any]:
    path = os.environ.get("PATH", "")
    home = os.environ.get("HOME") or ""
    probes = []
    for name in NATIVE_CHECKERS:
        resolved = shutil.which(name)
        probes.append({
            "name": name,
            "resolved_path": resolved,
            "status": "available" if resolved else "unavailable",
            "usable_in_sealed_validation": bool(resolved),
        })
    return {
        "any_native_checker_usable": any(item["usable_in_sealed_validation"] for item in probes),
        "checkers": probes,
        "home": home,
        "home_is_validation_private": (
            Path(home).name.startswith("ipfs-accelerate-validation-home-") if home else False
        ),
        "path": path,
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "sealed_path_expected": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin",
        "sealed_path_matches": path == "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin",
    }


def probe_direct_model(manifest: Mapping[str, Any]) -> dict[str, Any]:
    selected = manifest["selected_entry_points"]["direct_generative_model"]
    present_env = [name for name in DIRECT_MODEL_ENV_VARS if os.environ.get(name)]
    candidate = selected.get("cached_leanstral_candidate") or {}
    blockers = [
        str(selected.get("status") or "unselected"),
        str(candidate.get("blocker") or "no cached compatible weights"),
        "no served direct-model runtime on the sealed validation PATH",
    ]
    if present_env:
        blockers.append(
            "environment variable names are present but are not a qualified served model"
        )
    return {
        "blockers": blockers,
        "cached_leanstral_weight_file_bytes": candidate.get("weight_file_bytes"),
        "env_service_variable_names_present": present_env,
        "runnable": False,
        "scope_guard": selected.get("scope_guard"),
        "selected": selected.get("selected"),
        "status": "unavailable",
    }


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
        "runnable": runnable,
        "status": "available" if runnable else "unavailable",
        "teacher_status": advice.get("status"),
    }


def probe_import(module: str, root: Path) -> dict[str, Any]:
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "PYTHONPATH": str(root / "external" / "ipfs_datasets"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "IPFS_AUTO_INSTALL": "false",
        "IPFS_DATASETS_AUTO_INSTALL": "false",
        "CUDA_VISIBLE_DEVICES": "",
    }
    try:
        completed = subprocess.run(
            [sys.executable, "-c", f"import {module}"],
            capture_output=True,
            text=True,
            timeout=20,
            env=env,
            cwd=str(root),
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "error": str(exc),
            "imported": False,
            "module": module,
            "status": "import_failed",
        }
    stderr = (completed.stderr or "").strip().splitlines()
    error = stderr[-1] if stderr else ""
    return {
        "error": error or None,
        "exit_code": completed.returncode,
        "imported": completed.returncode == 0,
        "module": module,
        "status": "imported" if completed.returncode == 0 else "import_failed",
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
        raise IsolationError(
            f"arm {arm_id} refuses synthetic success markers {synthetic}"
        )
    declared = request.get("experiment_arm")
    if declared not in (None, arm_id):
        raise IsolationError(f"request experiment_arm {declared} does not match adapter {arm_id}")
    if arm_id in {"A", "B", "C"}:
        hits = request_contains_bridge_evidence(request)
        if hits:
            raise IsolationError(
                f"arm {arm_id} cannot consume D bridge evidence: {hits}"
            )
    if arm_id == "B" and request_enables_guidance(request):
        raise IsolationError(
            "arm B frozen canonical profile disables learned guidance and repair"
        )
    if arm_id == "E":
        mutations = request_contains_checker_mutation(request)
        if mutations:
            raise IsolationError(
                f"arm E cannot silently alter its checker: {mutations}"
            )
        supplied_digest = request.get("checker_digest")
        if supplied_digest not in (None, checker_digest()):
            raise IsolationError("arm E checker_digest drifted from D")
    if arm_id != "E" and request.get("learned_advice"):
        raise IsolationError(f"arm {arm_id} cannot consume E learned advice")


def capability_for(
    arm_id: str,
    *,
    checkers: Mapping[str, Any],
    direct_model: Mapping[str, Any],
    guidance: Mapping[str, Any],
    teacher: Mapping[str, Any],
) -> dict[str, Any]:
    native = bool(checkers.get("any_native_checker_usable"))
    compiler_targets = teacher.get("compiler_and_view_targets") or {}
    labels = teacher.get("semantic_gold") or {}
    blockers: list[str] = []
    runnable = False
    if not native:
        blockers.append("native checker absent from sealed validation PATH")
    if compiler_targets.get("targets_produced", 0) == 0:
        blockers.append("compiler/view dataset targets are not generated")
    if labels.get("status"):
        blockers.append(f"independent source labels {labels['status']}")
    if arm_id == "A":
        blockers.extend(direct_model["blockers"])
        runnable = False
    elif arm_id == "B":
        blockers.append("AF-016 paper-task execution is not this preflight")
        runnable = False
    elif arm_id == "C":
        blockers.append("typed multiview paper-task execution is not this preflight")
        runnable = False
    elif arm_id == "D":
        blockers.append("checked-bridge paper-task execution is not this preflight")
        blockers.append("AF-015 finite bridges are not Table 6 measurements")
        runnable = False
    else:
        blockers.extend(guidance["blockers"])
        blockers.append("learned-advice paper-task execution is not this preflight")
        runnable = False
    return {
        "arm": arm_id,
        "blockers": blockers,
        "claim_admissible": False,
        "end_to_end_status": "unavailable",
        "implementation_class": "implemented",
        "native_checker_usable": native,
        "runnable": runnable,
        "synthetic_success": False,
    }


def unavailable_result(
    arm_id: str,
    request: Mapping[str, Any],
    capability: Mapping[str, Any],
    *,
    isolation: str,
) -> dict[str, Any]:
    result = {
        "schema": SCHEMA_RESULT,
        "arm": arm_id,
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
        "task_id": TASK_ID,
        "unavailable_blockers": list(capability["blockers"]),
    }
    result["result_sha256"] = sha256_obj({key: result[key] for key in result if key != "result_sha256"})
    return result


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
            direct_model=env.get("direct_model") or probe_direct_model(
                load_json(default_paths()["manifest"])
            ),
            guidance=env.get("learned_guidance") or probe_learned_guidance(default_paths()),
            teacher=env.get("teacher") or {},
        )
    isolation = {
        "A": "direct-model oracle only; no compiler, bridge, or advice access",
        "B": "frozen canonical profile disables guidance and repair",
        "C": "typed multiview without D bridge evidence or proof transfer",
        "D": "checked bridges and premise assembly; no learned advice",
        "E": "distinct from D; checker digest pinned to D; advice cannot replace checking",
    }[arm_id]
    if not capability.get("runnable"):
        return unavailable_result(arm_id, request, capability, isolation=isolation)
    raise PipelineArmError(
        f"arm {arm_id} is marked runnable but AF-010 must not emit measured Table 6 rows"
    )


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

    d_checker = arm_definitions()["D"]["checker"]
    e_checker = arm_definitions()["E"]["checker"]
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
        d_checker == e_checker and d_checker["checker_digest"] == checker_digest(),
        "E binds the same checker identity and digest as D",
        checker_digest=checker_digest(),
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
        "D_may_name_bridge_evidence_but_not_claim_success",
        d_result["execution_status"] == "unavailable"
        and d_result["result_kind"] == "no_run"
        and d_result["claim_admissible"] is False
        and d_result["synthetic_success"] is False,
        "D accepts the bridge channel but remains unavailable without a native receipt",
        result_sha256=d_result["result_sha256"],
    )

    try:
        run_arm_e({
            "source_id": "iso-e-checker",
            "checker_override": {"checker_id": "weaker-checker"},
        }, environment=environment)
        record("E_rejects_checker_override", False, "E accepted a checker override")
    except IsolationError as exc:
        record("E_rejects_checker_override", True, str(exc))

    try:
        run_arm_e({
            "source_id": "iso-e-digest",
            "checker_digest": "0" * 64,
        }, environment=environment)
        record("E_rejects_checker_digest_drift", False, "E accepted a drifted checker digest")
    except IsolationError as exc:
        record("E_rejects_checker_digest_drift", True, str(exc))

    try:
        run_arm_e({
            "source_id": "iso-e-advice-checker",
            "advice_as_checker": True,
        }, environment=environment)
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

    failed = [item for item in tests if not item["passed"]]
    if failed:
        names = ", ".join(item["name"] for item in failed)
        raise IsolationError(f"isolation tests failed: {names}")
    return tests


def synthetic_executions(environment: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for arm_id, fn in ARM_ENTRY_POINTS.items():
        request: dict[str, Any] = {"source_id": f"preflight-{arm_id.lower()}", "experiment_arm": arm_id}
        if arm_id in {"D", "E"}:
            request["bridge_evidence"] = sample_bridge_evidence()
        result = fn(request, environment=environment)
        _expect(result["execution_status"] == "unavailable", f"{arm_id} returned {result['execution_status']}")
        _expect(result["result_kind"] == "no_run", f"{arm_id} returned {result['result_kind']}")
        _expect(result["claim_admissible"] is False, f"{arm_id} admitted a performance claim")
        _expect(result["synthetic_success"] is False, f"{arm_id} returned synthetic success")
        _expect(result["checker_digest"] == checker_digest(), f"{arm_id} checker digest drifted")
        rows.append({
            "arm": arm_id,
            "claim_admissible": result["claim_admissible"],
            "entry_point": arm_definitions()[arm_id]["entry_point"],
            "execution_status": result["execution_status"],
            "result_kind": result["result_kind"],
            "result_sha256": result["result_sha256"],
            "synthetic_success": result["synthetic_success"],
        })
    return rows


def build_config(root: Path) -> dict[str, Any]:
    paths = default_paths(root)
    plan = load_json(paths["plan"])
    splits = load_json(paths["splits"])
    _expect(plan.get("schema") == "autoformalization-experiment-plan/v1", "unexpected experiment plan schema")
    arms = arm_definitions()
    _expect(tuple(arms) == PIPELINE_ARMS, "arm definition order drifted")
    config = {
        "schema": SCHEMA_CONFIG,
        "task_id": TASK_ID,
        "suite_id": SUITE_ID,
        "arms": arms,
        "claim_policy": {
            "importability_is_not_end_to_end": True,
            "preflight_is_not_table_6": True,
            "synthetic_success_forbidden": True,
            "unavailable_is_not_zero": True,
            "unavailable_prevents_performance_claims": True,
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
            "frozen_canonical_profile_disables_guidance": True,
        },
        "matched_comparison": matched_comparison(plan, splits),
        "table5": {
            "A": arms["A"]["table5"],
            "B": arms["B"]["table5"],
            "C": arms["C"]["table5"],
            "D": arms["D"]["table5"],
            "E": arms["E"]["table5"],
        },
    }
    config["config_sha256"] = sha256_obj({key: config[key] for key in config if key != "config_sha256"})
    return config


def build_environment(root: Path) -> dict[str, Any]:
    paths = default_paths(root)
    manifest = load_json(paths["manifest"])
    teacher = load_json(paths["teacher"])
    checkers = probe_native_checkers()
    direct_model = probe_direct_model(manifest)
    guidance = probe_learned_guidance(paths)
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
        "teacher": teacher,
    }


def build_preflight(root: Path, config: Mapping[str, Any]) -> dict[str, Any]:
    paths = default_paths(root)
    environment = build_environment(root)
    inspected = inspect_sources(root)
    imports = [probe_import(module, root) for module in IMPORT_PROBES]
    tests = isolation_tests(environment)
    executions = synthetic_executions(environment)
    admitted = [row["arm"] for row in executions if row["claim_admissible"]]
    _expect(not admitted, f"performance claims admitted for {admitted}")
    preflight = {
        "schema": SCHEMA_PREFLIGHT,
        "task_id": TASK_ID,
        "suite_id": SUITE_ID,
        "observed_at": utc_now(),
        "all_isolation_passed": all(item["passed"] for item in tests),
        "any_performance_claim_admitted": False,
        "arms": {
            arm: {
                "blockers": environment["capabilities"][arm]["blockers"],
                "claim_admissible": False,
                "consumes_bridge_evidence": arm_definitions()[arm]["consumes_bridge_evidence"],
                "end_to_end_status": "unavailable",
                "entry_point": arm_definitions()[arm]["entry_point"],
                "execution_status": "unavailable",
                "features_allowed": arm_definitions()[arm]["features_allowed"],
                "implementation_class": "implemented",
                "learned_advice": arm_definitions()[arm]["learned_advice"],
                "oracles_allowed": arm_definitions()[arm]["oracles_allowed"],
                "result_kind": "no_run",
                "runnable": False,
                "synthetic_success": False,
            }
            for arm in PIPELINE_ARMS
        },
        "claim_policy": config["claim_policy"],
        "config_sha256": config["config_sha256"],
        "direct_model": environment["direct_model"],
        "environment": {
            "home": environment["native_checkers"]["home"],
            "home_is_validation_private": environment["native_checkers"]["home_is_validation_private"],
            "path": environment["native_checkers"]["path"],
            "python_executable": environment["native_checkers"]["python_executable"],
            "python_version": environment["native_checkers"]["python_version"],
            "sealed_path_matches": environment["native_checkers"]["sealed_path_matches"],
        },
        "frozen_canonical_profile": frozen_canonical_profile(),
        "import_probes": imports,
        "importability_is_not_end_to_end": True,
        "inspected_sources": inspected,
        "isolation_tests": tests,
        "learned_guidance": environment["learned_guidance"],
        "native_checkers": environment["native_checkers"],
        "performance_claims_admitted": [],
        "synthetic_executions": executions,
        "table6_cells_measured": 0,
        "warnings": [
            "This preflight publishes adapter capability. It is not AF-016.",
            "Unavailable implementations are not zero-score successes.",
            "Native checker presence on a provider host is ignored unless it is on PATH.",
        ],
    }
    preflight["preflight_sha256"] = sha256_obj(
        {key: preflight[key] for key in preflight if key != "preflight_sha256"}
    )
    _expect(preflight["all_isolation_passed"], "isolation tests did not all pass")
    _expect(paths["plan"].is_file(), "experiment plan missing")
    return preflight


def materialize(root: Path, *, config_path: Path, preflight_path: Path) -> dict[str, Any]:
    config = build_config(root)
    write_json(config_path, config)
    preflight = build_preflight(root, config)
    write_json(preflight_path, preflight)
    return {
        "schema": SCHEMA_PREFLIGHT,
        "task_id": TASK_ID,
        "all_isolation_passed": preflight["all_isolation_passed"],
        "any_performance_claim_admitted": preflight["any_performance_claim_admitted"],
        "arms": {
            arm: {
                "claim_admissible": body["claim_admissible"],
                "entry_point": body["entry_point"],
                "execution_status": body["execution_status"],
                "oracles_allowed": body["oracles_allowed"],
            }
            for arm, body in preflight["arms"].items()
        },
        "config": str(config_path),
        "config_sha256": config["config_sha256"],
        "isolation_tests": len(preflight["isolation_tests"]),
        "native_checker_usable": preflight["native_checkers"]["any_native_checker_usable"],
        "preflight": str(preflight_path),
        "preflight_sha256": preflight["preflight_sha256"],
        "synthetic_success_returned": False,
        "table6_cells_measured": 0,
    }


def self_test(root: Path) -> dict[str, Any]:
    environment = build_environment(root)
    inspect_sources(root)
    tests = isolation_tests(environment)
    executions = synthetic_executions(environment)
    return {
        "all_isolation_passed": all(item["passed"] for item in tests),
        "any_performance_claim_admitted": any(row["claim_admissible"] for row in executions),
        "checker_digest": checker_digest(),
        "entry_points": {arm: spec["entry_point"] for arm, spec in arm_definitions().items()},
        "executions": executions,
        "isolation_tests": tests,
        "synthetic_success_returned": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    materialize_cmd = sub.add_parser("materialize", help="Write arm config and sealed preflight")
    materialize_cmd.add_argument("--root", type=Path, default=REPO_ROOT)
    materialize_cmd.add_argument("--config", type=Path)
    materialize_cmd.add_argument("--preflight", type=Path)
    self_cmd = sub.add_parser("self-test", help="Run isolation and unavailable-execution checks")
    self_cmd.add_argument("--root", type=Path, default=REPO_ROOT)
    exec_cmd = sub.add_parser("execute", help="Invoke one arm adapter (fail-closed)")
    exec_cmd.add_argument("--arm", required=True, choices=PIPELINE_ARMS)
    exec_cmd.add_argument("--source-id", default="cli-request")
    exec_cmd.add_argument("--inject-bridge", action="store_true")
    exec_cmd.add_argument("--replace-checker", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "self-test":
        report = self_test(Path(args.root).resolve())
        print(canonical_dumps(report))
        return 0 if report["all_isolation_passed"] and not report["any_performance_claim_admitted"] else 1
    if args.command == "execute":
        request: dict[str, Any] = {"source_id": args.source_id, "experiment_arm": args.arm}
        if args.inject_bridge:
            request["bridge_evidence"] = sample_bridge_evidence()
        if args.replace_checker:
            request["checker_override"] = {"checker_id": "weaker-checker"}
        result = execute_arm(args.arm, request)
        print(canonical_dumps(result))
        return 0
    paths = default_paths(Path(args.root).resolve())
    summary = materialize(
        paths["root"],
        config_path=Path(args.config) if args.config else paths["config"],
        preflight_path=Path(args.preflight) if args.preflight else paths["preflight"],
    )
    print(canonical_dumps(summary))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except IsolationError as exc:
        print(f"pipeline_arms: isolation: {exc}", flush=True)
        raise SystemExit(1)
    except PipelineArmError as exc:
        print(f"pipeline_arms: {exc}", flush=True)
        raise SystemExit(1)
