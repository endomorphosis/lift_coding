#!/usr/bin/python3.12
"""Qualify development source adapters and the selected runtime boundary.

Freezes source pins, selected solver/crypto/transport/runtime profiles, arm
budgets, machine-expectation provenance and automated-admission requirements
before any evaluated prediction. Runs the development source pipeline and one
end-to-end A4 development command through SAT, UCAN, ENFORCE, durable
consumption, and the independent effect-observing bounded export handler.

The automated evidence scope does not require outside reviewers. Optional
review import remains strict for authentic human returns and is not the
automated gate. This is qualification, not production scoring. Fixture-only
LA-008 harness routes are labeled and are not represented as production.
Final labels are not inspected. Failed automated admission exits non-zero.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

HERE = Path(__file__).resolve()


def find_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "papers" / "completion" / "law_to_action").is_dir() and (
            candidate / "external" / "ipfs_accelerate"
        ).is_dir():
            return candidate
    raise RuntimeError("repository root not found")


ROOT = find_root(HERE)
LIVE = ROOT / "papers" / "completion" / "law_to_action"
BENCHMARK = LIVE / "benchmark"
PYTHON = "/usr/bin/python3.12"
VALIDATION_SITE_PACKAGES = Path("/opt/ipfs-validation-site-packages")
QUALIFY_VERSION = "la-028-qualify-final-runtime/v1"
QUALIFY_AUTOMATED_VERSION = "la-027-qualify-automated-scope/v1"
EVIDENCE_SCOPE = "automated_source_contracts_and_policy_effects"
SELECTED_ARM = "A4"
SELECTED_ARM_NAME = "full_enforcement"
CLOSED_LOOP_ARM = "closed_loop_A4"
FIXTURE_HARNESS = "papers/completion/law_to_action/benchmark/run.py"

for path in (
    VALIDATION_SITE_PACKAGES,
    ROOT / "external" / "ipfs_accelerate",
    ROOT / "external" / "ipfs_datasets",
    ROOT / "external" / "ipfs_kit",
    BENCHMARK,
):
    text = str(path)
    if path.is_dir() and text not in sys.path:
        sys.path.insert(0, text)


class QualifyError(RuntimeError):
    """Development qualification cannot proceed."""


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


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise QualifyError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def pin(path: Path) -> dict[str, Any]:
    return {
        "path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
        "sha256": sha256_file(path) if path.is_file() else None,
        "present": path.is_file(),
        "size_bytes": path.stat().st_size if path.is_file() else None,
    }


def which(name: str) -> str | None:
    return shutil.which(name)


def probe_routes() -> dict[str, Any]:
    sympy_meta: dict[str, Any]
    try:
        import sympy

        sympy_meta = {
            "available": True,
            "version": getattr(sympy, "__version__", None),
            "origin": getattr(sympy, "__file__", None),
        }
    except Exception as exc:
        sympy_meta = {"available": False, "error": f"{type(exc).__name__}: {exc}"}
    crypto_meta: dict[str, Any]
    try:
        import cryptography
        from ipfs_kit_py.mcp_server.mcplusplus import ucan as ucan_mod

        crypto_meta = {
            "available": True,
            "cryptography_version": cryptography.__version__,
            "HAVE_CRYPTO_ED25519": bool(ucan_mod.HAVE_CRYPTO_ED25519),
            "origin": getattr(cryptography, "__file__", None),
        }
    except Exception as exc:
        crypto_meta = {"available": False, "error": f"{type(exc).__name__}: {exc}", "HAVE_CRYPTO_ED25519": False}
    duckdb_meta: dict[str, Any]
    try:
        import duckdb

        duckdb_meta = {
            "available": True,
            "version": getattr(duckdb, "__version__", None),
            "origin": getattr(duckdb, "__file__", None),
        }
    except Exception as exc:
        duckdb_meta = {"available": False, "error": f"{type(exc).__name__}: {exc}"}
    solver_executables = {name: which(name) for name in ("z3", "cvc5", "vampire", "eprover", "lean", "coqc", "isabelle")}
    native_solvers_available = any(solver_executables.values())
    return {
        "observed_at": utc_now(),
        "python": PYTHON,
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "python_sha256": sha256_file(Path(sys.executable)) if Path(sys.executable).is_file() else None,
        "path": os.environ.get("PATH"),
        "home": os.environ.get("HOME"),
        "home_is_validation_prefix": str(os.environ.get("HOME", "")).startswith("ipfs-accelerate-validation-home-"),
        "sympy": sympy_meta,
        "crypto": crypto_meta,
        "duckdb": duckdb_meta,
        "solver_executables": solver_executables,
        "native_smt_atp_kernel_available": native_solvers_available,
        "selected_solver_route": {
            "id": "qf_bool_sympy_sat",
            "authority_kind": "satisfiability",
            "cannot_authorize_theorem_allow": True,
            "available": bool(sympy_meta.get("available")),
            "production_theorem_route": False,
        },
        "selected_crypto_route": {
            "id": "real_ed25519_ucan_verifier",
            "available": bool(crypto_meta.get("HAVE_CRYPTO_ED25519")),
            "fixture_verifier_is_production": False,
        },
        "selected_handler_route": {
            "id": "bounded_export_handler",
            "symbol": "BoundedExportHandler.execute",
            "observer": "EffectObserver.observe",
            "path": "papers/completion/law_to_action/benchmark/handlers/effects.py",
            "arbitrary_generated_source_execution": False,
            "fixture_harness": FIXTURE_HARNESS,
            "fixture_harness_is_production": False,
        },
        "selected_enforcement_route": {
            "id": "supervisor_pre_invocation_enforce",
            "symbol": "SupervisorPreInvocationEnforcement.authorize_and_delegate",
            "mode": "enforce",
            "off_mode_is_production": False,
        },
        "selected_durable_store": {
            "id": "duckdb-file-typed-quack-owner",
            "available": bool(duckdb_meta.get("available")),
            "in_memory_store_is_production": False,
        },
        "transport": {
            "development_mode": "local-process",
            "actual_network": False,
            "in_process_not_libp2p": True,
            "ipfs_daemon": False,
        },
        "model_provider": {
            "scientific_model_pinned": False,
            "paid_provider_budget": 0,
            "closed_loop_status": "declared_unrun_pending_LA-016",
        },
        "source_pins": {
            "effects.py": pin(BENCHMARK / "handlers" / "effects.py"),
            "baselines.py": pin(BENCHMARK / "baselines.py"),
            "durable_consumption.py": pin(BENCHMARK / "durable_consumption.py"),
            "source_pipeline.py": pin(BENCHMARK / "source_pipeline.py"),
            "review_import.py": pin(BENCHMARK / "review_import.py"),
            "admissibility_enforcement.py": pin(
                ROOT / "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/admissibility_enforcement.py"
            ),
            "authorization.py": pin(ROOT / "external/ipfs_kit/ipfs_kit_py/mcp_server/authorization.py"),
            "provers.json": pin(BENCHMARK / "manifests" / "provers.json"),
            "route_inventory.json": pin(BENCHMARK / "route_inventory.json"),
            "arms.json": pin(BENCHMARK / "arms.json"),
        },
    }


def frozen_budgets() -> dict[str, Any]:
    protocol = load_json(BENCHMARK / "protocol.json")
    resource_plan = load_json(BENCHMARK / "resource_plan.json")
    arms = load_json(BENCHMARK / "arms.json")
    return {
        "schema": "law-to-action-frozen-arm-budgets/v1",
        "frozen_at": utc_now(),
        "frozen_before_evaluated_predictions": True,
        "protocol_revision": protocol.get("schema"),
        "selected_arm": SELECTED_ARM,
        "selected_arm_name": SELECTED_ARM_NAME,
        "selected_arm_model_calls": 0,
        "closed_loop_arm": {
            "id": CLOSED_LOOP_ARM,
            "selected": False,
            "status": "unrun",
            "requires_model_calls": True,
            "maximum_model_calls_per_attempt": arms["shared_controls"]["model_budgets"][
                "closed_loop_maximum_model_calls_per_attempt"
            ],
            "paid_provider_budget": 0,
        },
        "fixed_action": {
            "attempts_if_scored": resource_plan["fixed_action_budget"]["attempts"],
            "development_scheduled_attempts": protocol["fixed_action_plan"]["scheduled_attempts"]["development"],
            "this_qualification_attempts": 2,
            "seeds": protocol["fixed_action_plan"]["seeds"],
            "wall_timeout_seconds": resource_plan["fixed_action_budget"]["per_attempt_resource_group"][
                "wall_timeout_seconds"
            ],
            "network": "disabled",
            "scored": False,
        },
        "shared_controls_fingerprint_rule": arms.get("fingerprint_rule"),
        "admitted_split": "development",
        "calibration_and_final_excluded": True,
        "empirical_benchmark_result": False,
    }


def frozen_inputs() -> dict[str, Any]:
    splits = load_json(BENCHMARK / "manifests" / "splits.json")
    development = [row for row in splits["assignments"] if row.get("split") == "development"]
    return {
        "schema": "law-to-action-frozen-final-inputs/v1",
        "frozen_at": utc_now(),
        "frozen_before_evaluated_predictions": True,
        "split": "development",
        "inspect_final_labels": False,
        "score_final_examples": False,
        "families": [
            {
                "population": row["population"],
                "lineage_family_id": row["lineage_family_id"],
                "source_id": row["source_id"],
                "planned_case_ids": row["planned_case_ids"],
            }
            for row in development
        ],
        "pins": {
            "sources.json": pin(BENCHMARK / "manifests" / "sources.json"),
            "splits.json": pin(BENCHMARK / "manifests" / "splits.json"),
            "corpus_counts.json": pin(BENCHMARK / "corpus_counts.json"),
            "legal.jsonl": pin(BENCHMARK / "annotations" / "legal.jsonl"),
            "skills.jsonl": pin(BENCHMARK / "annotations" / "skills.jsonl"),
            "cve_pairs.jsonl": pin(BENCHMARK / "cases" / "cve_pairs.jsonl"),
            "protocol.json": pin(BENCHMARK / "protocol.json"),
            "resource_plan.json": pin(BENCHMARK / "resource_plan.json"),
            "arms.json": pin(BENCHMARK / "arms.json"),
        },
    }


def admission_requirements(*, evidence_scope: str | None = None) -> dict[str, Any]:
    if evidence_scope == EVIDENCE_SCOPE:
        return {
            "evidence_scope": EVIDENCE_SCOPE,
            "independent_labels": "not required for automated scope; human fields remain uncollected",
            "reviewer_identity_and_timestamp": "absent unless an authentic optional return exists; agent-generated provenance is refused",
            "complete_population": "exactly 6 legal, 12 CVE, and 12 skill families / 60 cases; shortfall refuses",
            "machine_expectations": "pre-prediction machine-contract provenance required; evaluated-compiler self-labels refuse",
            "selected_solver_route": "qf_bool_sympy_sat must remain available for A4 SAT obligations; native theorem kernels remain unavailable",
            "selected_crypto_route": "real Ed25519 UCAN verifier required for A3/A4; fixture verifiers are not production",
            "selected_handler_route": "BoundedExportHandler plus independent EffectObserver; LA-008 fixture harness is not production",
            "durable_consumption": "file-backed DuckDB store required for A4; InMemoryCapabilityConsumptionStore is not production",
            "model_route": "closed-loop arms require a pinned scientific model; none is pinned",
            "final_split": "final examples remain unscored; development qualification is not a held-out result",
            "fixture_only_routes_are_not_production": True,
            "failed_admission_exit_status": "nonzero",
        }
    return {
        "independent_labels": "required; missing labels refuse final admission and analysis",
        "reviewer_identity_and_timestamp": "required; agent-generated provenance is refused",
        "complete_population": "exactly 6 legal, 12 CVE, and 12 skill families / 60 cases; shortfall refuses",
        "selected_solver_route": "qf_bool_sympy_sat must remain available for A4 SAT obligations; native theorem kernels remain unavailable",
        "selected_crypto_route": "real Ed25519 UCAN verifier required for A3/A4; fixture verifiers are not production",
        "selected_handler_route": "BoundedExportHandler plus independent EffectObserver; LA-008 fixture harness is not production",
        "durable_consumption": "file-backed DuckDB store required for A4; InMemoryCapabilityConsumptionStore is not production",
        "model_route": "closed-loop arms require a pinned scientific model; none is pinned",
        "final_split": "final examples remain unscored until LA-027 independent labels exist",
        "fixture_only_routes_are_not_production": True,
    }


def build_runtime_manifest(
    probe: Mapping[str, Any],
    budgets: Mapping[str, Any],
    inputs: Mapping[str, Any],
    *,
    evidence_scope: str | None = None,
    task: str = "LA-028",
    qualify_version: str | None = None,
) -> dict[str, Any]:
    selected_solver_ok = bool(probe["selected_solver_route"]["available"])
    selected_crypto_ok = bool(probe["selected_crypto_route"]["available"])
    selected_store_ok = bool(probe["selected_durable_store"]["available"])
    unavailable = []
    if not selected_solver_ok:
        unavailable.append("qf_bool_sympy_sat")
    if not selected_crypto_ok:
        unavailable.append("real_ed25519_ucan_verifier")
    if not selected_store_ok:
        unavailable.append("duckdb-file-typed-quack-owner")
    if probe["native_smt_atp_kernel_available"]:
        kernel_status = "present_but_not_selected_for_theorem_allow"
    else:
        kernel_status = "unavailable"
    return {
        "schema": "law-to-action-runtime-manifest/v1",
        "task": task,
        "evidence_scope": evidence_scope,
        "qualify_version": qualify_version or QUALIFY_VERSION,
        "frozen_at": utc_now(),
        "frozen_before_evaluated_predictions": True,
        "empirical_benchmark_result": False,
        "production_claim": False,
        "selected_arm": {
            "id": SELECTED_ARM,
            "name": SELECTED_ARM_NAME,
            "model_calls": 0,
            "requires_model_provider": False,
            "requires_sat": True,
            "requires_ucan": True,
            "requires_enforce": True,
            "requires_durable_consumption": True,
            "requires_effect_observer": True,
        },
        "fixture_routes": {
            "la008_trusted_fixture_harness": {
                "path": FIXTURE_HARNESS,
                "production": False,
                "role": "measurement-integrity smoke only",
            },
            "injected_ucan_fixture_verifiers": {"production": False},
            "in_memory_capability_store": {"production": False},
            "supervisor_off_audit_shadow": {"production": False},
        },
        "inputs": inputs,
        "budgets": budgets,
        "routes": {
            "solver": probe["selected_solver_route"],
            "crypto": probe["selected_crypto_route"],
            "handler": probe["selected_handler_route"],
            "enforcement": probe["selected_enforcement_route"],
            "durable_store": probe["selected_durable_store"],
            "transport": probe["transport"],
            "model": probe["model_provider"],
            "native_kernel_status": kernel_status,
        },
        "source_pins": probe["source_pins"],
        "admission_requirements": admission_requirements(evidence_scope=evidence_scope),
        "unavailable_runtime_routes": unavailable,
        "authoritative_environment": {
            "python": PYTHON,
            "path": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin",
            "observed_path": probe.get("path"),
            "home_prefix": "ipfs-accelerate-validation-home-",
            "home_is_validation_prefix": probe.get("home_is_validation_prefix"),
        },
    }


def model_provider_ledger(manifest: Mapping[str, Any]) -> dict[str, Any]:
    requires = bool(manifest["selected_arm"]["requires_model_provider"])
    env_keys = [key for key in os.environ if "API_KEY" in key or key.endswith("_TOKEN")]
    calls: list[dict[str, Any]] = []
    if requires:
        calls.append(
            {
                "attempted": True,
                "provider": None,
                "status": "unavailable_unpinned_scientific_model",
                "http_performed": False,
                "reason": "Selected arm requires model calls but no scientific model/provider revision is pinned and paid budget is 0.",
            }
        )
    return {
        "schema": "law-to-action-model-provider-ledger/v1",
        "chosen_arm": manifest["selected_arm"]["id"],
        "requires_model_calls": requires,
        "actual_calls": calls,
        "call_count": len(calls),
        "closed_loop_arm_selected": False,
        "scientific_model_pinned": False,
        "credential_names_present": sorted(env_keys),
        "fixture_model_stubs_used": False,
        "note": "A4 fixed-action development qualification does not call a model. Closed-loop arms remain unrun.",
    }


def load_source_pipeline():
    return load_module("la028_source_pipeline", BENCHMARK / "source_pipeline.py")


def load_review_import():
    return load_module("la028_review_import", BENCHMARK / "review_import.py")


def load_automated_evidence():
    return load_module("la027_automated_evidence", BENCHMARK / "automated_evidence.py")


def load_baselines():
    return load_module("la028_baselines", BENCHMARK / "baselines.py")


def source_derived_candidate(prediction: Mapping[str, Any], *, oracle_role: str, baselines: Any) -> dict[str, Any]:
    case_id = str(prediction["case_id"])
    instruction = {
        "operation": "export_json",
        "path": f"exports/dev-{sha256_text(case_id)[:16]}.json",
        "payload": {
            "candidate_id": case_id,
            "population": prediction["population"],
            "split": "development",
            "task": "LA-027-automated-scope-qualification",
            "source_prediction_sha256": digest(prediction.get("prediction") or prediction.get("failure") or {}),
            "adapter": (prediction.get("adapter") or {}).get("id"),
            "oracle_role": oracle_role,
            "fixture_candidate": False,
        },
    }
    encoded = canonical_json(instruction["payload"])
    candidate = {
        "candidate_id": case_id,
        "lineage_family_id": prediction["lineage_family_id"],
        "source_id": prediction["source_id"],
        "population": prediction["population"],
        "split": "development",
        "oracle_role": oracle_role,
        "actor": baselines.ACTOR,
        "audience": baselines.AUDIENCE,
        "root": "policy:root-v1",
        "arguments": instruction,
        "declared_effects": [
            {
                "effect_kind": "filesystem.export_json",
                "target": instruction["path"],
                "payload_sha256": hashlib.sha256(encoded).hexdigest(),
                "payload_bytes": len(encoded),
            }
        ],
        "handler_version": "bounded-export-handler/v2",
        "observer_version": "independent-filesystem-journal-observer/v2",
        "clock": baselines.CLOCK,
        "initial_sandbox_state": "empty",
        "derived_from_source_adapter": True,
        "la014_preselected_fixture": False,
    }
    candidate["candidate_digest"] = digest(
        {
            "candidate_id": candidate["candidate_id"],
            "actor": candidate["actor"],
            "audience": candidate["audience"],
            "arguments": candidate["arguments"],
            "declared_effects": candidate["declared_effects"],
        }
    )
    return candidate


def run_e2e(predictions: list[Mapping[str, Any]], manifest: Mapping[str, Any]) -> dict[str, Any]:
    unavailable = list(manifest.get("unavailable_runtime_routes") or [])
    if unavailable:
        return {
            "schema": "law-to-action-development-e2e/v1",
            "status": "refused_unavailable_runtime_route",
            "unavailable_runtime_routes": unavailable,
            "handler_boundary_reached": False,
            "empirical_benchmark_result": False,
            "fixture_route": False,
            "production_claim": False,
        }
    if not predictions:
        return {
            "schema": "law-to-action-development-e2e/v1",
            "status": "refused_no_source_predictions",
            "handler_boundary_reached": False,
            "empirical_benchmark_result": False,
        }
    baselines = load_baselines()
    config = baselines.load_arms()
    a4 = next(arm for arm in config["arms"] if arm["id"] == "A4")
    a0 = next(arm for arm in config["arms"] if arm["id"] == "A0")
    seed = predictions[0]
    allow_candidate = source_derived_candidate(seed, oracle_role="allowed", baselines=baselines)
    deny_candidate = source_derived_candidate(seed, oracle_role="forbidden", baselines=baselines)
    durable = baselines.load_durable()
    work = Path(tempfile.mkdtemp(prefix="la028-e2e-"))
    database = work / "control.duckdb"
    store = durable.DuckDBCapabilityConsumptionStore(database, owner_id="owner:la-028")
    attempts: list[dict[str, Any]] = []
    try:
        store.attach()
        allow_result = baselines.run_a4(a4, allow_candidate, config, store)
        deny_result = baselines.run_a4(a4, deny_candidate, config, store)
        unguarded = baselines.run_unguarded(a0, allow_candidate, config)
        attempts = [allow_result.to_record(), deny_result.to_record(), unguarded.to_record()]
        for row in attempts:
            row["development_qualification"] = True
            row["fixture_route"] = False
            row["production_claim"] = False
            row["empirical_benchmark_result"] = False
            row["derived_from_source_adapter"] = True
        handler_reached = all("observed_effect_count" in row for row in attempts)
        sat_ran = bool((allow_result.mechanism or {}).get("obligation"))
        ucan_ran = bool((allow_result.mechanism or {}).get("ucan"))
        enforce_ran = (allow_result.mechanism or {}).get("enforce_mode") == "enforce"
        status = "qualified_development_boundary"
        if allow_result.failure or deny_result.failure:
            status = "executed_with_failures"
        return {
            "schema": "law-to-action-development-e2e/v1",
            "status": status,
            "selected_arm": SELECTED_ARM,
            "handler_boundary_reached": handler_reached,
            "proof_route_executed": sat_ran,
            "capability_route_executed": ucan_ran,
            "enforce_route_executed": enforce_ran,
            "durable_store_kind": getattr(store, "store_kind", None),
            "in_memory_store": False,
            "arbitrary_generated_source_execution": False,
            "fixture_harness_used": False,
            "la008_run_py_represented_as_production": False,
            "source_case_id": seed["case_id"],
            "source_adapter": (seed.get("adapter") or {}).get("id"),
            "attempts": attempts,
            "allow_decision": allow_result.decision,
            "deny_decision": deny_result.decision,
            "unguarded_effects": unguarded.observed_effect_count,
            "empirical_benchmark_result": False,
            "production_claim": False,
            "model_calls": 0,
        }
    except Exception as exc:
        return {
            "schema": "law-to-action-development-e2e/v1",
            "status": "execution_failure",
            "error": f"{type(exc).__name__}: {exc}",
            "trace": traceback.format_exc(limit=12),
            "handler_boundary_reached": False,
            "empirical_benchmark_result": False,
            "attempts": attempts,
        }
    finally:
        try:
            store.close()
        except Exception:
            pass
        shutil.rmtree(work, ignore_errors=True)


def automated_frozen_inputs() -> dict[str, Any]:
    splits = load_json(BENCHMARK / "manifests" / "splits.json")
    families = [
        {
            "population": row["population"],
            "lineage_family_id": row["lineage_family_id"],
            "source_id": row["source_id"],
            "split": row["split"],
            "planned_case_ids": row["planned_case_ids"],
        }
        for row in splits["assignments"]
    ]
    evidence = load_automated_evidence()
    return {
        "schema": "law-to-action-frozen-final-inputs/v1",
        "frozen_at": utc_now(),
        "frozen_before_evaluated_predictions": True,
        "evidence_scope": EVIDENCE_SCOPE,
        "executed_split": "development",
        "full_population_bound": True,
        "inspect_final_labels": False,
        "score_final_examples": False,
        "held_out_result_inferred": False,
        "families": families,
        "case_count": sum(len(row["planned_case_ids"]) for row in families),
        "family_count": len(families),
        "original_protocol_sha256": evidence.ORIGINAL_PROTOCOL_SHA256,
        "pins": {
            "sources.json": pin(BENCHMARK / "manifests" / "sources.json"),
            "splits.json": pin(BENCHMARK / "manifests" / "splits.json"),
            "corpus_counts.json": pin(BENCHMARK / "corpus_counts.json"),
            "protocol.json": pin(BENCHMARK / "protocol.json"),
            "automated_evidence_amendment.json": pin(BENCHMARK / "automated_evidence_amendment.json"),
            "automated_reference_manifest.json": pin(BENCHMARK / "annotations" / "automated_reference_manifest.json"),
            "automated_evidence.py": pin(BENCHMARK / "automated_evidence.py"),
            "legal.jsonl": pin(BENCHMARK / "annotations" / "legal.jsonl"),
            "skills.jsonl": pin(BENCHMARK / "annotations" / "skills.jsonl"),
            "cve_pairs.jsonl": pin(BENCHMARK / "cases" / "cve_pairs.jsonl"),
            "resource_plan.json": pin(BENCHMARK / "resource_plan.json"),
            "arms.json": pin(BENCHMARK / "arms.json"),
        },
    }


def qualify_automated(out: Path) -> dict[str, Any]:
    evidence = load_automated_evidence()
    out.mkdir(parents=True, exist_ok=True)
    manifest_payload = evidence.write_reference_manifest()
    write_json(out / "automated_reference_manifest.json", manifest_payload)
    probe = probe_routes()
    probe["source_pins"]["automated_evidence.py"] = pin(BENCHMARK / "automated_evidence.py")
    probe["source_pins"]["automated_evidence_amendment.json"] = pin(BENCHMARK / "automated_evidence_amendment.json")
    write_json(out / "runtime_probe.json", probe)
    inputs = automated_frozen_inputs()
    budgets = frozen_budgets()
    budgets["evidence_scope"] = EVIDENCE_SCOPE
    budgets["admitted_split"] = "development"
    budgets["calibration_and_final_excluded"] = True
    write_json(out / "frozen_inputs.json", inputs)
    write_json(out / "frozen_budgets.json", budgets)
    manifest = build_runtime_manifest(
        probe,
        budgets,
        inputs,
        evidence_scope=EVIDENCE_SCOPE,
        task="LA-027",
        qualify_version=QUALIFY_AUTOMATED_VERSION,
    )
    write_json(out / "runtime_manifest.json", manifest)
    freeze_digest = digest(
        {
            "inputs": inputs["pins"],
            "budgets": budgets["selected_arm"],
            "arm": SELECTED_ARM,
            "amendment": inputs["pins"]["automated_evidence_amendment.json"],
            "expectations": manifest_payload.get("manifest_digest"),
            "original_protocol": evidence.ORIGINAL_PROTOCOL_SHA256,
        }
    )
    write_json(
        out / "freeze_digest.json",
        {
            "digest": freeze_digest,
            "frozen_before_evaluated_predictions": True,
            "evidence_scope": EVIDENCE_SCOPE,
        },
    )

    pipeline_mod = load_source_pipeline()
    pipeline = pipeline_mod.run_pipeline(split="development", out_dir=out)
    after_inputs = automated_frozen_inputs()
    after = digest(
        {
            "inputs": after_inputs["pins"],
            "budgets": frozen_budgets()["selected_arm"],
            "arm": SELECTED_ARM,
            "amendment": after_inputs["pins"]["automated_evidence_amendment.json"],
            "expectations": evidence.load_reference_manifest().get("manifest_digest"),
            "original_protocol": evidence.ORIGINAL_PROTOCOL_SHA256,
        }
    )
    if after != freeze_digest:
        raise QualifyError("inputs, amendment, expectations or arm budgets changed after freeze")

    review_mod = load_review_import()
    review = review_mod.run(returned=None, out=out, analyze=True)
    if review.get("import", review).get("admitted") is True:
        raise QualifyError("optional review importer must not admit a missing human return")

    records_path = out / "source_records.jsonl"
    predictions: list[dict[str, Any]] = []
    if records_path.is_file():
        with records_path.open(encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                if row.get("status") == "prediction":
                    predictions.append(row)
    e2e = run_e2e(predictions, manifest)
    write_json(out / "e2e_handler_trace.json", e2e)
    ledger = model_provider_ledger(manifest)
    write_json(out / "model_provider_ledger.json", ledger)

    envelope = evidence.build_valid_envelope(
        qualification={
            "development_only": True,
            "held_out_scored": False,
            "handler_boundary_reached": e2e.get("handler_boundary_reached") is True,
            "proof_route_executed": e2e.get("proof_route_executed") is True,
            "capability_route_executed": e2e.get("capability_route_executed") is True,
        },
        effect_observation={
            "observer": "EffectObserver.observe",
            "independent": True,
            "self_reported": False,
            "success_claimed": False,
            "qualification_only": True,
            "handler_boundary_reached": e2e.get("handler_boundary_reached") is True,
        },
    )
    write_json(out / "automated_envelope.json", envelope)
    admission = evidence.admit(envelope)
    write_json(out / "automated_admission.json", admission)
    write_json(out / "final_admission.json", admission)
    controls = evidence.run_controls(out)
    analysis = evidence.automated_analysis(
        admission,
        {
            "e2e": {
                "status": e2e.get("status"),
                "handler_boundary_reached": e2e.get("handler_boundary_reached"),
                "proof_route_executed": e2e.get("proof_route_executed"),
                "capability_route_executed": e2e.get("capability_route_executed"),
            },
            "pipeline": pipeline.get("counts"),
        },
        envelope=envelope,
    )
    write_json(out / "final_analysis.json", analysis)
    if admission.get("admitted") is not True or admission.get("scored") is True:
        write_json(out / "qualification_summary.json", {"status": "refused", "admission": admission, "e2e": e2e})
        raise QualifyError(f"automated admission refused: {admission.get('reasons')}")
    if e2e.get("handler_boundary_reached") is not True:
        raise QualifyError("independent effect observer did not reach the handler boundary")
    if e2e.get("empirical_benchmark_result") is True or e2e.get("production_claim") is True:
        raise QualifyError("qualification claimed a held-out or production result")
    if controls.get("all_refused") is not True:
        raise QualifyError("focused admission controls did not all refuse")
    summary = {
        "schema": "law-to-action-automated-scope-qualification/v1",
        "task": "LA-027",
        "qualify_version": QUALIFY_AUTOMATED_VERSION,
        "evidence_scope": EVIDENCE_SCOPE,
        "completed_at": utc_now(),
        "selected_arm": SELECTED_ARM,
        "frozen_before_evaluated_predictions": True,
        "pipeline": {
            "cases": (pipeline.get("counts") or {}).get("cases"),
            "predictions": (pipeline.get("counts") or {}).get("predictions"),
            "failures": (pipeline.get("counts") or {}).get("failures"),
            "by_population": (pipeline.get("counts") or {}).get("by_population"),
        },
        "optional_review_import": {
            "admitted": review.get("import", review).get("admitted"),
            "code": review.get("import", review).get("code") or (review.get("import") or {}).get("code"),
            "used_as_automated_gate": False,
        },
        "e2e": {
            "status": e2e.get("status"),
            "handler_boundary_reached": e2e.get("handler_boundary_reached"),
            "proof_route_executed": e2e.get("proof_route_executed"),
            "capability_route_executed": e2e.get("capability_route_executed"),
            "enforce_route_executed": e2e.get("enforce_route_executed"),
            "allow_decision": e2e.get("allow_decision"),
            "deny_decision": e2e.get("deny_decision"),
            "fixture_harness_used": e2e.get("fixture_harness_used"),
            "la008_run_py_represented_as_production": e2e.get("la008_run_py_represented_as_production"),
        },
        "model_provider_ledger": {"call_count": ledger["call_count"], "requires_model_calls": ledger["requires_model_calls"]},
        "automated_admission": {
            "admitted": admission.get("admitted"),
            "scored": admission.get("scored"),
            "exit_status": admission.get("exit_status"),
            "human_fields": admission.get("human_fields"),
        },
        "controls": {"all_refused": controls.get("all_refused"), "count": len(controls.get("controls") or [])},
        "analysis": analysis,
        "empirical_benchmark_result": False,
        "production_claim": False,
        "held_out_result_inferred": False,
        "useful_work_success_inferred_from_fixtures": False,
        "fixture_only_routes_represented_as_production": False,
        "final_labels_inspected": False,
        "independent_human_gold": False,
    }
    write_json(out / "qualification_summary.json", summary)
    return summary


def final_admission(
    *,
    manifest: Mapping[str, Any],
    pipeline: Mapping[str, Any],
    review: Mapping[str, Any],
    e2e: Mapping[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []
    if review.get("import", review).get("admitted") is not True:
        reasons.append("missing_independent_labels")
    if manifest.get("unavailable_runtime_routes"):
        reasons.append("unavailable_runtime_routes")
    counts = (pipeline.get("counts") or {})
    if counts.get("cases") != 12:
        reasons.append("incomplete_development_population")
    if pipeline.get("final_labels_inspected"):
        reasons.append("final_labels_inspected")
    if e2e.get("handler_boundary_reached") is not True:
        reasons.append("handler_boundary_not_reached")
    admitted = not reasons
    return {
        "schema": "law-to-action-final-admission/v1",
        "admitted": False if reasons else admitted,
        "scored": False,
        "final_examples_scored": False,
        "reasons": reasons
        or ["development_qualification_only_final_scoring_blocked_until_LA-027"],
        "missing_independent_labels": True,
        "unavailable_runtime_routes": list(manifest.get("unavailable_runtime_routes") or []),
        "incomplete_populations": "incomplete_development_population" in reasons,
        "production_claim": False,
        "message": "Final admission and analysis refuse missing independent labels, unavailable runtime routes, and incomplete populations. Development qualification is not a scored final run.",
    }


def refuse_analysis(admission: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": "law-to-action-final-analysis/v1",
        "status": "refused",
        "scored": False,
        "code": "analysis_refuses_unadmitted_final_run",
        "message": "Analysis refuses to score final examples without independent labels, complete populations, and available runtime routes.",
        "admission": admission,
    }


def qualify(out: Path) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    probe = probe_routes()
    write_json(out / "runtime_probe.json", probe)
    inputs = frozen_inputs()
    budgets = frozen_budgets()
    write_json(out / "frozen_inputs.json", inputs)
    write_json(out / "frozen_budgets.json", budgets)
    manifest = build_runtime_manifest(probe, budgets, inputs)
    write_json(out / "runtime_manifest.json", manifest)
    write_json(BENCHMARK / "runtime_manifest.json", manifest)
    freeze_digest = digest({"inputs": inputs["pins"], "budgets": budgets["selected_arm"], "arm": SELECTED_ARM})
    write_json(out / "freeze_digest.json", {"digest": freeze_digest, "frozen_before_evaluated_predictions": True})

    pipeline_mod = load_source_pipeline()
    pipeline = pipeline_mod.run_pipeline(split="development", out_dir=out)
    after = digest({"inputs": frozen_inputs()["pins"], "budgets": frozen_budgets()["selected_arm"], "arm": SELECTED_ARM})
    if after != freeze_digest:
        raise QualifyError("inputs or arm budgets changed after freeze")

    review_mod = load_review_import()
    review = review_mod.run(returned=None, out=out, analyze=True)

    records_path = out / "source_records.jsonl"
    predictions: list[dict[str, Any]] = []
    if records_path.is_file():
        with records_path.open(encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                if row.get("status") == "prediction":
                    predictions.append(row)
    e2e = run_e2e(predictions, manifest)
    write_json(out / "e2e_handler_trace.json", e2e)
    ledger = model_provider_ledger(manifest)
    write_json(out / "model_provider_ledger.json", ledger)
    admission = final_admission(manifest=manifest, pipeline=pipeline, review=review, e2e=e2e)
    write_json(out / "final_admission.json", admission)
    analysis = refuse_analysis(admission)
    write_json(out / "final_analysis.json", analysis)
    summary = {
        "schema": "law-to-action-development-qualification/v1",
        "task": "LA-028",
        "qualify_version": QUALIFY_VERSION,
        "completed_at": utc_now(),
        "selected_arm": SELECTED_ARM,
        "frozen_before_evaluated_predictions": True,
        "pipeline": {
            "cases": (pipeline.get("counts") or {}).get("cases"),
            "predictions": (pipeline.get("counts") or {}).get("predictions"),
            "failures": (pipeline.get("counts") or {}).get("failures"),
            "by_population": (pipeline.get("counts") or {}).get("by_population"),
        },
        "review_import": {
            "admitted": review.get("import", review).get("admitted"),
            "code": review.get("import", review).get("code") or (review.get("import") or {}).get("code"),
        },
        "e2e": {
            "status": e2e.get("status"),
            "handler_boundary_reached": e2e.get("handler_boundary_reached"),
            "proof_route_executed": e2e.get("proof_route_executed"),
            "capability_route_executed": e2e.get("capability_route_executed"),
            "enforce_route_executed": e2e.get("enforce_route_executed"),
            "allow_decision": e2e.get("allow_decision"),
            "deny_decision": e2e.get("deny_decision"),
        },
        "model_provider_ledger": {"call_count": ledger["call_count"], "requires_model_calls": ledger["requires_model_calls"]},
        "final_admission": admission,
        "analysis": analysis,
        "empirical_benchmark_result": False,
        "production_claim": False,
        "fixture_only_routes_represented_as_production": False,
        "final_labels_inspected": False,
    }
    write_json(out / "qualification_summary.json", summary)
    return summary


def admit_final(out: Path) -> tuple[dict[str, Any], int]:
    automated_path = out / "automated_admission.json"
    admission_path = out / "final_admission.json"
    if automated_path.is_file():
        admission, _envelope = load_automated_evidence().load_saved_admission(out)
        if admission.get("admitted") is True and admission.get("scored") is not True:
            result = {
                "schema": "law-to-action-final-admission-gate/v1",
                "admitted": True,
                "scored": False,
                "held_out_scored": False,
                "evidence_scope": EVIDENCE_SCOPE,
                "message": "Automated-scope admission succeeded without reviewer identities or human labels. This is not a scored held-out run.",
                "admission": admission,
            }
            print(json.dumps(result, indent=2, sort_keys=True))
            return result, 0
        result = {
            "schema": "law-to-action-final-admission-gate/v1",
            "admitted": False,
            "scored": False,
            "evidence_scope": EVIDENCE_SCOPE,
            "message": "Automated-scope admission refused. A failed admission is not an executed study.",
            "admission": admission,
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        status = admission.get("exit_status")
        return result, int(status) if isinstance(status, int) else 2
    if admission_path.is_file():
        admission = load_json(admission_path)
    else:
        admission = {
            "admitted": False,
            "reasons": ["qualification_not_run"],
            "scored": False,
        }
    result = {
        "schema": "law-to-action-final-admission-gate/v1",
        "admitted": False,
        "scored": False,
        "message": "Final scoring is refused without automated-scope admission. Independent labels are not synthesized.",
        "admission": admission,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if admission.get("admitted") is True and admission.get("scored") is True:
        raise QualifyError("this qualifier must not score a held-out run")
    return result, 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("qualify", "qualify-automated", "admit-final", "analyze"),
        default="qualify-automated",
        nargs="?",
    )
    parser.add_argument("--out", type=Path, default=LIVE / "results" / "automated_scope_qualification")
    parser.add_argument("--arm", default=SELECTED_ARM)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.arm not in {SELECTED_ARM, "A4"}:
        if args.arm in {"closed_loop", CLOSED_LOOP_ARM, "A4-closed-loop"}:
            ledger = model_provider_ledger(
                {
                    "selected_arm": {
                        "id": CLOSED_LOOP_ARM,
                        "requires_model_provider": True,
                    }
                }
            )
            write_json(args.out / "model_provider_ledger.json", ledger)
            print(json.dumps({"status": "refused_unpinned_model_arm", "ledger": ledger}, indent=2, sort_keys=True))
            return 0
        raise QualifyError(f"unsupported arm {args.arm}; development qualification selects A4")
    if args.command in {"admit-final", "analyze"}:
        if args.command == "analyze" and (args.out / "automated_admission.json").is_file():
            evidence = load_automated_evidence()
            admission, envelope = evidence.load_saved_admission(args.out)
            analysis = evidence.automated_analysis(
                admission,
                load_json(args.out / "qualification_summary.json") if (args.out / "qualification_summary.json").is_file() else None,
                envelope=envelope,
            )
            write_json(args.out / "final_analysis.json", analysis)
            print(json.dumps(analysis, indent=2, sort_keys=True))
            status = analysis.get("exit_status")
            return int(status) if isinstance(status, int) else 2
        _result, status = admit_final(args.out)
        return status
    if args.command == "qualify":
        summary = qualify(args.out)
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0
    summary = qualify_automated(args.out)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary.get("automated_admission", {}).get("admitted") is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
