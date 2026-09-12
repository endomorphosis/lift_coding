#!/usr/bin/env python3
"""AF-012 isolated trusted proof-head training and evaluation.

Construct admitted verifier-feedback records from the AF-004 train/selection
partitions and the AF-003 pinned compiler/checker identities. Attempt T3 from
each matched AF-011 T2 checkpoint with AdaptiveModalAutoencoder isolated
heads. Evaluate isolation, calibration, abstention, family coverage, route
value, and actual checker outcomes against T2.

Native Lean/Z3/CVC5 binaries are judged only on the sealed validation PATH.
Missing native feedback yields a documented unrun/limited-scope T3 outcome.
Isolation-contract probes are constructed controls: they may update auxiliary
heads but are never admitted as T3 training labels or native certification.
Predicted proof-head success is never treated as a checked proof.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from shutil import which
from typing import Any, Mapping, Sequence

SCHEMA_MANIFEST = "autoformalization-proof-feedback-manifest/v1"
SCHEMA_RESULT = "autoformalization-proof-head-result/v1"
SCHEMA_ISOLATION = "autoformalization-proof-head-isolation/v1"
TASK_ID = "AF-012"
SEEDS = (104729, 130363, 155921)
NATIVE_TOOLS = (
    "lean",
    "lake",
    "elan",
    "z3",
    "cvc5",
    "vampire",
    "eprover",
    "coqc",
    "isabelle",
)
PROTECTED_STATE_KEYS = (
    "decoded_embeddings",
    "family_logits",
    "feature_embedding_weights",
    "feature_family_logits",
    "legal_ir_view_logits",
    "legal_ir_view_embedding_weights",
    "semantic_slot_embedding_weights",
    "compiler_quality_embedding_weights",
    "compiler_quality_family_logits",
)
PROOF_STATE_KEYS = (
    "applied_proof_feedback_ids",
    "proof_auxiliary_head_logits",
    "proof_auxiliary_head_schema_version",
    "proof_feedback_version_fingerprint",
)

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parents[2]
REPO_ROOT = PAPER_ROOT.parents[2]
T2_STATE_DIR = PAPER_ROOT / "receipts" / "snapshots" / "AF-011" / "checkpoints" / "states"
TRAIN_PATH = PAPER_ROOT / "receipts" / "snapshots" / "AF-004" / "train.sources.jsonl"
SELECTION_PATH = PAPER_ROOT / "receipts" / "snapshots" / "AF-004" / "selection.sources.jsonl"

sys.path[:0] = [str(REPO_ROOT / "external" / "ipfs_datasets")]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if isinstance(value, (str, bool)) or value is None:
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, float):
        return float(value)
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return jsonable(to_dict())
    value_attr = getattr(value, "value", None)
    if value_attr is not None and value_attr is not value:
        return jsonable(value_attr)
    return str(value)


def write_json(path: Path, value: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    blob = json.dumps(jsonable(value), indent=2, ensure_ascii=True, sort_keys=True) + "\n"
    path.write_text(blob, encoding="utf-8")
    return sha256_bytes(blob.encode("utf-8"))


def write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(jsonable(row), ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        for row in rows
    ]
    text = "\n".join(lines) + ("\n" if lines else "")
    path.write_text(text, encoding="utf-8")
    return sha256_bytes(text.encode("utf-8"))


def probe_import(name: str) -> dict[str, Any]:
    try:
        module = importlib.import_module(name)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return {
        "ok": True,
        "file": getattr(module, "__file__", None),
        "version": getattr(module, "__version__", None),
    }


def probe_environment() -> dict[str, Any]:
    home = os.environ.get("HOME") or ""
    binaries = {name: which(name) for name in NATIVE_TOOLS}
    return {
        "interpreter": sys.executable,
        "version": sys.version,
        "path": os.environ.get("PATH"),
        "home": home,
        "home_is_validation_private": Path(home).name.startswith("ipfs-accelerate-validation-home-")
        if home
        else False,
        "imports": {
            name: probe_import(name)
            for name in ("numpy", "torch", "transformers", "faiss", "multiformats")
        },
        "binaries": binaries,
        "any_native_checker_usable": any(binaries.values()),
        "host_elan_or_local_bin_ignored": True,
    }


def load_source_ids(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            rows.append(
                {
                    "citation": record.get("citation"),
                    "document_sha256": record.get("document_sha256"),
                    "family": record.get("family"),
                    "record_id": record["record_id"],
                }
            )
    return rows


def state_fingerprint(payload: Mapping[str, Any], *, exclude: Sequence[str] = ()) -> str:
    clipped = {key: value for key, value in payload.items() if key not in set(exclude)}
    return sha256_bytes(canonical_json(clipped))


def protected_fields(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {key: payload.get(key) for key in PROTECTED_STATE_KEYS}


def result_row(**fields: Any) -> dict[str, Any]:
    payload = {
        "schema": SCHEMA_RESULT,
        "task_id": TASK_ID,
        "claim_admissible": False,
        "counts_as_native_checked_proof": False,
        "predicted_proof_success_used_as_certification": False,
        "fixture": False,
    }
    payload.update(fields)
    return payload


def compact_record(record: Any) -> dict[str, Any]:
    payload = jsonable(record.to_dict())
    keep = (
        "record_id",
        "obligation_id",
        "training_label",
        "trust_status",
        "partition",
        "deterministic_trusted",
        "eligible_for_training",
        "version_fingerprint",
        "legal_ir_view",
        "semantic_family",
        "route_availability",
        "route_statuses",
        "backend_outcomes",
        "kernel_reconstruction",
        "minimal_failing_contract",
        "repair_label",
    )
    return {key: payload.get(key) for key in keep}


def main() -> int:
    started = time.time()
    env = probe_environment()
    native_usable = bool(env["any_native_checker_usable"])

    from ipfs_datasets_py.logic.integration.reasoning.legal_ir_hammer_translation import (
        LEGAL_IR_HAMMER_RECONSTRUCTION_RECEIPT_SCHEMA_VERSION,
        LEGAL_IR_HAMMER_TRANSLATION_SCHEMA_VERSION,
    )
    from ipfs_datasets_py.logic.integration.reasoning.legal_ir_obligations import (
        LEGAL_IR_OBLIGATION_SCHEMA_VERSION,
    )
    from ipfs_datasets_py.logic.integration.reasoning.legal_ir_premises import (
        LEGAL_IR_PREMISE_LIBRARY_VERSION,
    )
    from ipfs_datasets_py.logic.integration.reasoning.legal_ir_proof_feedback import (
        KernelReconstructionFeedback,
        LegalIRProofFeedbackRecord,
        ProofFeedbackPartitionPolicy,
        ProofFeedbackVersions,
    )
    from ipfs_datasets_py.logic.integration.reasoning.legal_ir_proof_router import (
        LEGAL_IR_PROOF_ROUTER_SCHEMA_VERSION,
    )
    from ipfs_datasets_py.logic.integration.reasoning.legal_ir_view_contracts import (
        LEGAL_IR_VIEW_CONTRACT_REGISTRY_VERSION,
    )
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.modal_autoencoder import (
        AdaptiveModalAutoencoder,
        ModalAutoencoderTrainingState,
        PROOF_AUXILIARY_HEAD_NAMES,
        PROOF_AUXILIARY_HEAD_SCHEMA_VERSION,
        PROOF_AUXILIARY_PROTECTED_OBJECTIVES,
        PROOF_AUXILIARY_TRAINING_SCHEMA_VERSION,
    )

    splits = json.loads((PAPER_ROOT / "data" / "splits.json").read_text(encoding="utf-8"))
    experiment_plan = json.loads((PAPER_ROOT / "config" / "experiment_plan.json").read_text(encoding="utf-8"))
    environment_manifest = json.loads(
        (PAPER_ROOT / "config" / "environment_manifest.json").read_text(encoding="utf-8")
    )
    teacher = json.loads((PAPER_ROOT / "data" / "teacher_manifest.json").read_text(encoding="utf-8"))
    pct_cases = json.loads(
        (PAPER_ROOT / "data" / "policy_code_trace_cases.json").read_text(encoding="utf-8")
    )
    t2_manifest = json.loads(
        (PAPER_ROOT / "checkpoints" / "baselines" / "manifest.json").read_text(encoding="utf-8")
    )
    t2_results = [
        json.loads(line)
        for line in (PAPER_ROOT / "runs" / "training_baselines" / "results.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line
    ]

    train_ids = load_source_ids(TRAIN_PATH)
    selection_ids = load_source_ids(SELECTION_PATH)
    if len(train_ids) != splits["counts"]["train"]["natural_source_units"]:
        raise SystemExit("train source count does not match splits.json")
    if len(selection_ids) != splits["counts"]["selection"]["natural_source_units"]:
        raise SystemExit("selection source count does not match splits.json")

    pinned_versions = ProofFeedbackVersions(
        compiler_version=str(
            environment_manifest["logical_profile"]["compiler_version"]
        ),
        obligation_schema_version=LEGAL_IR_OBLIGATION_SCHEMA_VERSION,
        contract_registry_version=LEGAL_IR_VIEW_CONTRACT_REGISTRY_VERSION,
        premise_library_version=LEGAL_IR_PREMISE_LIBRARY_VERSION,
        proof_router_version=LEGAL_IR_PROOF_ROUTER_SCHEMA_VERSION,
        translation_schema_version=LEGAL_IR_HAMMER_TRANSLATION_SCHEMA_VERSION,
        reconstruction_schema_version=LEGAL_IR_HAMMER_RECONSTRUCTION_RECEIPT_SCHEMA_VERSION,
        solver_toolchain_version="sealed-path-unavailable",
        lean_toolchain_version="sealed-path-unavailable",
        theorem_registry_version="autoformalization-theorem-registry/v1",
        repair_taxonomy_version="legal-ir-repair-labels-v1",
    )
    train_policy = ProofFeedbackPartitionPolicy(holdout_fraction=0.0)
    holdout_policy = ProofFeedbackPartitionPolicy(holdout_fraction=1.0)
    t3_plan = next(item for item in experiment_plan["conditions"] if item["id"] == "T3")
    t2_plan = next(item for item in experiment_plan["conditions"] if item["id"] == "T2")
    matched_budget = {
        "common_envelope": experiment_plan["common_budget"],
        "t2_budget": t2_plan["budget"],
        "t3_budget": t3_plan["budget"],
        "learned_condition_seeds": list(SEEDS),
        "matched_primary_envelope": True,
        "t3_extra_checker_cost_consumed": False,
        "reason": "T3 uses the same three-seed common envelope as T2; extra checker cost was unused because sealed-PATH native checkers are absent.",
    }

    inventory: list[dict[str, Any]] = []
    admitted_records: list[Any] = []

    def reject_source(source: Mapping[str, Any], split: str) -> None:
        inventory.append(
            {
                "admitted_for_t3_training": False,
                "citation": source.get("citation"),
                "document_sha256": source.get("document_sha256"),
                "eligible_native_label": False,
                "family": source.get("family"),
                "native_feedback": "unavailable",
                "partition_role": split,
                "record_kind": "natural_source_candidate",
                "rejection_reasons": [
                    "native_checker_unavailable",
                    "no_trusted_verifier_label",
                    "teacher_proof_feedback_pending",
                ],
                "source_record_id": source["record_id"],
                "split": split,
                "training_label": "no_trusted_signal",
            }
        )

    for source in train_ids:
        reject_source(source, "train")
    for source in selection_ids:
        reject_source(source, "selection")

    inventory.append(
        {
            "admitted_for_t3_training": False,
            "n_units": splits["counts"]["final_test"]["natural_source_units"],
            "record_kind": "locked_split",
            "rejection_reasons": ["final_test_locked", "ids_not_inspected", "bodies_not_opened"],
            "split": "final_test",
        }
    )
    inventory.append(
        {
            "admitted_for_t3_training": False,
            "n_units": splits["counts"]["fixed_canary"]["natural_source_units"],
            "record_kind": "unused_split",
            "rejection_reasons": ["fixed_canary_not_used_for_t3_training_or_threshold_selection"],
            "split": "fixed_canary",
        }
    )

    for case in pct_cases.get("cases", []):
        inventory.append(
            {
                "admitted_for_t3_training": False,
                "case_id": case["case_id"],
                "constructed_control": True,
                "native_feedback": "unavailable"
                if case["case_id"] == "NATIVE-LEAN-Q1"
                else "not_native_kernel",
                "record_kind": "af015_constructed_bridge",
                "rejection_reasons": [
                    "constructed_control",
                    "not_from_permitted_natural_partition",
                    "not_native_checked_proof",
                ],
                "split": "constructed_control",
            }
        )

    isolation_trusted = LegalIRProofFeedbackRecord.create(
        obligation_id="af012-isolation-trusted",
        obligation_type="exception_scope",
        legal_ir_view="deontic.ir",
        semantic_family="conditional_normative",
        semantic_slots={"actor": "present", "condition": "single", "exception": "present"},
        selected_premise_families=("sample_local_assumption", "theorem_template"),
        route_availability={
            "deterministic_contract": True,
            "native_lean_reconstruction": False,
        },
        route_statuses={"deterministic_contract": "passed"},
        backend_outcomes={"lean": "skipped", "z3": "skipped"},
        deterministic_trusted=True,
        repair_label="exception_scope_projection",
        evidence_ids=("af012-isolation-evidence-trusted",),
        receipt_ids=("af012-isolation-receipt-trusted",),
        partition_key="af012-isolation-trusted",
        partition_policy=train_policy,
        versions=pinned_versions,
    )
    isolation_contract = LegalIRProofFeedbackRecord.create(
        obligation_id="af012-isolation-contract",
        obligation_type="exception_scope",
        legal_ir_view="deontic.ir",
        semantic_family="conditional_normative",
        semantic_slots={"actor": "present", "condition": "single", "exception": "absent"},
        selected_premise_families=("sample_local_assumption",),
        route_availability={"deterministic_contract": True, "native_lean_reconstruction": False},
        route_statuses={},
        backend_outcomes={},
        deterministic_trusted=False,
        minimal_failing_contract={
            "contract_id": "legal-ir-view/deontic-ir/v1",
            "failure_code": "missing_exception_scope",
            "failing_fields": ["formulas.exceptions"],
            "deterministic": True,
            "evidence_id": "af012-isolation-contract-evidence",
            "receipt_id": "af012-isolation-contract-receipt",
        },
        repair_label="exception_scope_projection",
        evidence_ids=("af012-isolation-evidence-contract",),
        receipt_ids=("af012-isolation-receipt-contract",),
        partition_key="af012-isolation-contract",
        partition_policy=train_policy,
        versions=pinned_versions,
    )
    isolation_records = [isolation_trusted, isolation_contract]

    untrusted = LegalIRProofFeedbackRecord.create(
        obligation_id="af012-filter-untrusted",
        obligation_type="exception_scope",
        legal_ir_view="deontic.ir",
        semantic_family="conditional_normative",
        route_availability={"deterministic_contract": False, "native_lean_reconstruction": False},
        route_statuses={},
        backend_outcomes={},
        deterministic_trusted=False,
        partition_key="af012-filter-untrusted",
        partition_policy=train_policy,
        versions=pinned_versions,
    )
    stale = LegalIRProofFeedbackRecord.create(
        obligation_id="af012-filter-stale",
        obligation_type="exception_scope",
        legal_ir_view="deontic.ir",
        semantic_family="conditional_normative",
        route_availability={"deterministic_contract": True},
        route_statuses={"deterministic_contract": "passed"},
        deterministic_trusted=True,
        partition_key="af012-filter-stale",
        partition_policy=train_policy,
        versions=ProofFeedbackVersions(
            compiler_version="compiler-stale",
            solver_toolchain_version="sealed-path-unavailable",
            lean_toolchain_version="sealed-path-unavailable",
            theorem_registry_version="autoformalization-theorem-registry/v1",
        ),
    )
    holdout = LegalIRProofFeedbackRecord.create(
        obligation_id="af012-filter-holdout",
        obligation_type="exception_scope",
        legal_ir_view="deontic.ir",
        semantic_family="conditional_normative",
        route_availability={"deterministic_contract": True},
        route_statuses={"deterministic_contract": "passed"},
        deterministic_trusted=True,
        partition_key="af012-filter-holdout",
        partition_policy=holdout_policy,
        versions=pinned_versions,
    )
    reconstruction_probe = LegalIRProofFeedbackRecord.create(
        obligation_id="af012-filter-reconstruction",
        obligation_type="exception_scope",
        legal_ir_view="deontic.ir",
        semantic_family="conditional_normative",
        deterministic_trusted=False,
        kernel_reconstruction=KernelReconstructionFeedback(
            status="unavailable",
            attempted=True,
            verified=False,
            checker="lean",
            receipt_id="af012-filter-reconstruction-receipt",
        ),
        partition_key="af012-filter-reconstruction",
        partition_policy=train_policy,
        versions=pinned_versions,
    )
    tampered = isolation_trusted.to_dict()
    tampered["obligation_type"] = "tampered_after_addressing"

    for record, kind, reasons in (
        (isolation_trusted, "isolation_contract_probe", ["constructed_control", "not_native_feedback", "isolation_probe_not_t3_label"]),
        (isolation_contract, "isolation_contract_probe", ["constructed_control", "not_native_feedback", "isolation_probe_not_t3_label"]),
        (untrusted, "filter_probe", ["untrusted", "no_trusted_signal"]),
        (stale, "filter_probe", ["version_mismatch"]),
        (holdout, "filter_probe", ["holdout_partition"]),
        (reconstruction_probe, "filter_probe", ["constructed_control", "native_reconstruction_not_verified", "not_admitted_t3_label"]),
    ):
        inventory.append(
            {
                "admitted_for_t3_training": False,
                "constructed_control": True,
                "record": compact_record(record),
                "record_kind": kind,
                "rejection_reasons": reasons,
                "split": "constructed_control",
            }
        )
    inventory.append(
        {
            "admitted_for_t3_training": False,
            "constructed_control": True,
            "record_kind": "filter_probe",
            "rejection_reasons": ["invalid_content_address", "tampered_payload"],
            "split": "constructed_control",
            "obligation_id": "af012-isolation-trusted",
        }
    )

    eligible_native_labels = 0
    t3_status = "unrun" if not native_usable else "insufficient_labels"
    t3_scope = "limited_scope_unrun_missing_native_feedback"
    t3_reason = (
        "Sealed PATH has no lean/z3/cvc5/other native checkers; teacher proof_feedback "
        f"records={teacher['proof_feedback']['records']}; no version-matched native "
        "kernel labels exist on the permitted train partition. T3 is not trained and "
        "is not certified from predicted proof-head success or constructed isolation probes."
    )

    architecture = AdaptiveModalAutoencoder(compute_device="python").proof_auxiliary_head_architecture()
    filter_model = AdaptiveModalAutoencoder(compute_device="python")
    filter_report = filter_model.train_proof_auxiliary_heads(
        [isolation_trusted, untrusted, stale, holdout, reconstruction_probe, tampered],
        expected_versions=pinned_versions,
        learning_rate=0.5,
    )
    duplicate_report = filter_model.apply_proof_feedback(
        [isolation_trusted],
        expected_versions=pinned_versions,
    )

    t2_runs = [item for item in t2_manifest["runs"] if item["arm_id"] == "T2"]
    isolation_by_seed: list[dict[str, Any]] = []
    t3_by_seed: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []

    results.append(
        result_row(
            record_id="AF-012:capability",
            record_kind="capability",
            arm_id="environment",
            execution_status="measured",
            result_kind="bounded_observation",
            constructed_control=True,
            metrics={"any_native_checker_usable": native_usable},
            notes="Sealed-PATH probe only; host ~/.elan and ~/.local/bin are out of scope.",
            environment=env,
        )
    )

    for seed in SEEDS:
        t2_run = next(item for item in t2_runs if item.get("seed") == seed)
        state_path = T2_STATE_DIR / f"T2-{seed}-final.json"
        wrapped = json.loads(state_path.read_text(encoding="utf-8"))
        t2_state = ModalAutoencoderTrainingState.from_dict(wrapped["state"])
        t2_payload = t2_state.to_dict()
        t2_protected = state_fingerprint(t2_payload, exclude=PROOF_STATE_KEYS)
        t2_identity = wrapped["identity_sha256"]

        t3_model = AdaptiveModalAutoencoder(state=t2_state.copy(), compute_device="python")
        t3_before = t3_model.state.to_dict()
        t3_report = t3_model.train_proof_auxiliary_heads(
            admitted_records,
            expected_versions=pinned_versions,
            learning_rate=0.10,
        )
        t3_after = t3_model.state.to_dict()
        t3_protected = state_fingerprint(t3_after, exclude=PROOF_STATE_KEYS)
        t3_eval = t3_model.evaluate_proof_auxiliary_heads(
            admitted_records,
            expected_versions=pinned_versions,
        )
        t3_seed = {
            "seed": seed,
            "t2_checkpoint_identity": t2_identity,
            "t2_checkpoint_path": str(state_path.relative_to(REPO_ROOT)),
            "t2_update_count": t2_run["update_count"],
            "t2_termination_reason": t2_run["termination_reason"],
            "t3_status": t3_report["status"],
            "t3_applied_count": t3_report["applied_count"],
            "t3_eligible_count": t3_report["eligible_count"],
            "t3_candidate_count": t3_report["candidate_count"],
            "protected_fingerprint_before": t2_protected,
            "protected_fingerprint_after": t3_protected,
            "protected_parameters_unchanged": t2_protected == t3_protected,
            "state_unchanged": t3_before == t3_after,
            "execution_status": "unavailable",
            "result_kind": "no_run",
            "claim_admissible": False,
            "native_checked_useful_proof_coverage": None,
            "calibration_error": None if t3_eval["observation_count"] == 0 else t3_eval["calibration_error"],
            "eligible_label_count": t3_eval["observation_count"],
            "reason": t3_reason,
        }
        t3_by_seed.append(t3_seed)

        iso_model = AdaptiveModalAutoencoder(
            state=ModalAutoencoderTrainingState.from_dict(t2_payload),
            compute_device="python",
        )
        iso_before = iso_model.state.to_dict()
        iso_report = iso_model.train_proof_auxiliary_heads(
            isolation_records,
            expected_versions=pinned_versions,
            learning_rate=0.5,
        )
        iso_after = iso_model.state.to_dict()
        iso_protected_before = state_fingerprint(iso_before, exclude=PROOF_STATE_KEYS)
        iso_protected_after = state_fingerprint(iso_after, exclude=PROOF_STATE_KEYS)
        field_equal = {
            key: iso_before.get(key) == iso_after.get(key) for key in PROTECTED_STATE_KEYS
        }
        iso_eval = iso_model.evaluate_proof_auxiliary_heads(
            isolation_records,
            expected_versions=pinned_versions,
            require_train_partition=False,
        )
        isolation_by_seed.append(
            {
                "seed": seed,
                "applied_count": iso_report["applied_count"],
                "head_update_counts": iso_report["head_update_counts"],
                "heads_changed": iso_before["proof_auxiliary_head_logits"]
                != iso_after["proof_auxiliary_head_logits"],
                "objective_isolation": iso_report["objective_isolation"],
                "protected_fields_unchanged": field_equal,
                "protected_fingerprint_after": iso_protected_after,
                "protected_fingerprint_before": iso_protected_before,
                "protected_parameters_unchanged": iso_protected_before == iso_protected_after,
                "status": iso_report["status"],
                "t2_checkpoint_identity": t2_identity,
                "calibration_error_isolation_probe_only": iso_eval["calibration_error"],
                "coverage_isolation_probe_only": iso_eval["coverage"],
                "abstention_rate_isolation_probe_only": iso_eval["abstention_rate"],
                "by_legal_ir_family": iso_eval.get("by_legal_ir_family"),
                "not_t3_certification": True,
            }
        )

        t2_train_agg = next(
            row
            for row in t2_results
            if row.get("arm_id") == "T2"
            and row.get("record_kind") == "aggregate"
            and row.get("seed") == seed
            and row.get("split") == "train"
        )
        results.append(
            result_row(
                record_id=f"T2:{seed}:baseline",
                record_kind="t2_baseline",
                arm_id="T2",
                seed=seed,
                split="train",
                execution_status="measured",
                result_kind="bounded_observation",
                dataset_id=t2_manifest["dataset_id"],
                config_id=t2_manifest["config_id"],
                checkpoint={
                    "initial": t2_run["initial_checkpoint_sha256"],
                    "final": t2_run["final_checkpoint_sha256"],
                },
                update_count=t2_run["update_count"],
                termination_reason=t2_run["termination_reason"],
                metrics={
                    "native_checked_useful_proof_coverage": None,
                    "source_fidelity": None,
                    "vector_cosine": (t2_train_agg.get("metrics") or {}).get("vector_cosine"),
                },
                notes="AF-011 T2 identities reused; T2 is the matched starting checkpoint, not a new T3 result.",
            )
        )
        results.append(
            result_row(
                record_id=f"T3:{seed}:attempt",
                record_kind="t3_attempt",
                arm_id="T3",
                seed=seed,
                split="train",
                execution_status="unavailable",
                result_kind="no_run",
                dataset_id=t2_manifest["dataset_id"],
                config_id=t2_manifest["config_id"],
                checkpoint={
                    "initial": t2_identity,
                    "final": t2_identity,
                    "matched_t2": True,
                },
                update_count=0,
                termination_reason="no_admitted_native_feedback",
                t3_scope=t3_scope,
                metrics={
                    "calibration_error": None,
                    "native_checked_useful_proof_coverage": None,
                    "route_value": None,
                    "source_fidelity": None,
                    "eligible_native_label_count": eligible_native_labels,
                    "applied_count": t3_report["applied_count"],
                },
                notes=t3_reason,
                detail=t3_seed,
            )
        )
        results.append(
            result_row(
                record_id=f"T3:{seed}:isolation_probe",
                record_kind="isolation",
                arm_id="T3-isolation-probe",
                seed=seed,
                split="constructed_control",
                execution_status="measured",
                result_kind="bounded_observation",
                constructed_control=True,
                fixture=False,
                claim_admissible=False,
                metrics={
                    "protected_parameters_unchanged": iso_protected_before == iso_protected_after,
                    "heads_changed": iso_before["proof_auxiliary_head_logits"]
                    != iso_after["proof_auxiliary_head_logits"],
                    "proof_loss_weight_in_primary_objective": iso_report["objective_isolation"][
                        "proof_loss_weight_in_primary_objective"
                    ],
                    "calibration_error": iso_eval["calibration_error"],
                },
                notes="Constructed isolation probes update auxiliary heads only; not T3 certification or native proof coverage.",
                detail=isolation_by_seed[-1],
            )
        )

    results.append(
        result_row(
            record_id="T3:calibration",
            record_kind="calibration",
            arm_id="T3",
            execution_status="unavailable",
            result_kind="no_run",
            split="train",
            metrics={
                "calibration_error": None,
                "abstention_rate": None,
                "coverage": None,
                "eligible_native_label_count": eligible_native_labels,
                "eligible_natural_train_sources": len(train_ids),
                "eligible_natural_selection_sources": len(selection_ids),
                "numerator_basis": "actual_eligible_native_or_version_matched_verifier_labels",
                "predicted_proof_success_used_as_certification": False,
            },
            notes="Calibration is undefined without eligible native/version-matched labels; isolation-probe calibration is retained separately and is not a T3 metric.",
        )
    )
    results.append(
        result_row(
            record_id="T3:routing",
            record_kind="routing",
            arm_id="T3",
            execution_status="unavailable",
            result_kind="no_run",
            split="train",
            metrics={
                "route_value": None,
                "actual_checker_outcomes": 0,
                "predicted_route_success": None,
                "predicted_proof_success_used_as_certification": False,
                "matched_route_budget": True,
            },
            matched_budget=matched_budget,
            notes="Route value uses matched T2/T3 budgets and actual checker outcomes. Predicted head probabilities are not certification.",
        )
    )
    results.append(
        result_row(
            record_id="T3:filter",
            record_kind="filter",
            arm_id="T3",
            execution_status="measured",
            result_kind="bounded_observation",
            constructed_control=True,
            metrics={
                "applied_count": filter_report["applied_count"],
                "duplicate_count": duplicate_report["duplicate_count"],
                "skipped_holdout_count": filter_report["skipped_holdout_count"],
                "skipped_invalid_count": filter_report["skipped_invalid_count"],
                "skipped_untrusted_count": filter_report["skipped_untrusted_count"],
                "skipped_version_mismatch_count": filter_report["skipped_version_mismatch_count"],
            },
            notes="Filter accounting uses constructed probes plus rejected natural candidates. Applied isolation-probe updates are not T3 labels.",
            detail=jsonable(filter_report),
            duplicate=jsonable(duplicate_report),
        )
    )
    results.append(
        result_row(
            record_id="T3:final_test:locked",
            record_kind="coverage",
            arm_id="T3",
            split="final_test",
            execution_status="unrun",
            result_kind="no_run",
            bodies_opened=False,
            ids_inspected=False,
            n_units=splits["counts"]["final_test"]["natural_source_units"],
            notes="Final-test identities and bodies were not opened.",
        )
    )
    results.append(
        result_row(
            record_id="T3:fixed_canary:unused",
            record_kind="coverage",
            arm_id="T3",
            split="fixed_canary",
            execution_status="unrun",
            result_kind="no_run",
            bodies_opened=False,
            n_units=splits["counts"]["fixed_canary"]["natural_source_units"],
            notes="Fixed canary was not used for T3 training or threshold selection.",
        )
    )

    isolation_ok = all(
        item["protected_parameters_unchanged"]
        and item["heads_changed"]
        and item["objective_isolation"]["proof_loss_weight_in_primary_objective"] == 0.0
        and item["objective_isolation"]["separate_parameters"]
        and all(item["protected_fields_unchanged"].values())
        for item in isolation_by_seed
    )
    t3_unrun_ok = all(
        item["t3_applied_count"] == 0 and item["execution_status"] == "unavailable"
        for item in t3_by_seed
    )

    results.append(
        result_row(
            record_id="AF-012:summary",
            record_kind="summary",
            arm_id="T3",
            execution_status="unavailable",
            result_kind="no_run",
            t3_scope=t3_scope,
            t3_status=t3_status,
            claim_admissible=False,
            metrics={
                "admitted_t3_records": len(admitted_records),
                "eligible_native_label_count": eligible_native_labels,
                "isolation_contract_held": isolation_ok,
                "t3_unrun_limited_scope": t3_unrun_ok,
                "calibration_error": None,
                "route_value": None,
                "native_checked_useful_proof_coverage": None,
            },
            comparison={
                "control": "T3 vs T2",
                "t2_executed": True,
                "t3_executed": False,
                "improvement_claimed": False,
                "reason": t3_reason,
            },
            notes=t3_reason,
        )
    )

    rejection_counts: dict[str, int] = {}
    for row in inventory:
        for reason in row.get("rejection_reasons") or []:
            rejection_counts[reason] = rejection_counts.get(reason, 0) + 1

    manifest = {
        "schema": SCHEMA_MANIFEST,
        "task_id": TASK_ID,
        "created_at": utc_now(),
        "admitted_for_t3_training": [],
        "admitted_count": 0,
        "eligible_native_label_count": eligible_native_labels,
        "t3_outcome": {
            "status": t3_status,
            "scope": t3_scope,
            "reason": t3_reason,
            "native_checker_usable": native_usable,
            "teacher_proof_feedback": teacher["proof_feedback"],
        },
        "pinned_versions": pinned_versions.to_dict(),
        "pinned_version_fingerprint": pinned_versions.fingerprint,
        "permitted_partitions": {
            "train": {"n_units": len(train_ids), "used_for": "candidate_inventory"},
            "selection": {"n_units": len(selection_ids), "used_for": "candidate_inventory_eval_split"},
            "fixed_canary": {
                "n_units": splits["counts"]["fixed_canary"]["natural_source_units"],
                "used_for": "unused",
            },
            "final_test": {
                "n_units": splits["counts"]["final_test"]["natural_source_units"],
                "used_for": "locked",
                "ids_inspected": False,
                "bodies_opened": False,
            },
        },
        "compiler_checker_pins": {
            "compiler_entry_point": environment_manifest["selected_entry_points"]["compiler"]["entry_point"],
            "compiler_version": environment_manifest["logical_profile"]["compiler_version"],
            "model_architecture_version": environment_manifest["selected_entry_points"]["model"][
                "architecture_version"
            ],
            "host_lean_status": "pinned_by_AF-003_but_not_on_sealed_PATH",
            "host_z3_status": "pinned_by_AF-003_but_not_on_sealed_PATH",
            "sealed_path_native_checker": "unavailable",
            "solver_authority": environment_manifest["selected_entry_points"]["solver"]["proof_authority"],
        },
        "filter_accounting": {
            "candidate_count": filter_report["candidate_count"],
            "applied_count": filter_report["applied_count"],
            "duplicate_count": duplicate_report["duplicate_count"],
            "skipped_holdout_count": filter_report["skipped_holdout_count"],
            "skipped_invalid_count": filter_report["skipped_invalid_count"],
            "skipped_untrusted_count": filter_report["skipped_untrusted_count"],
            "skipped_version_mismatch_count": filter_report["skipped_version_mismatch_count"],
            "natural_candidates_rejected": len(train_ids) + len(selection_ids),
            "rejection_reason_counts": rejection_counts,
        },
        "isolation_probes": [compact_record(record) for record in isolation_records],
        "inventory": inventory,
        "matched_budget": matched_budget,
        "frozen_inputs": {
            "experiment_plan_sha256": sha256_file(PAPER_ROOT / "config" / "experiment_plan.json"),
            "environment_manifest_sha256": sha256_file(PAPER_ROOT / "config" / "environment_manifest.json"),
            "metrics_sha256": sha256_file(PAPER_ROOT / "config" / "metrics.json"),
            "splits_sha256": sha256_file(PAPER_ROOT / "data" / "splits.json"),
            "teacher_manifest_sha256": sha256_file(PAPER_ROOT / "data" / "teacher_manifest.json"),
            "train_sources_sha256": sha256_file(TRAIN_PATH),
            "selection_sources_sha256": sha256_file(SELECTION_PATH),
            "t2_checkpoint_manifest_sha256": sha256_file(
                PAPER_ROOT / "checkpoints" / "baselines" / "manifest.json"
            ),
        },
        "capability_probe": env,
        "not_claimed": [
            "T3 training gain versus T2",
            "native checked useful-proof coverage",
            "predicted proof-head success as certification",
            "calibration on ineligible or constructed labels as a T3 metric",
            "final-test proof-head generalization",
        ],
    }

    isolation = {
        "schema": SCHEMA_ISOLATION,
        "task_id": TASK_ID,
        "created_at": utc_now(),
        "isolation_contract": {
            "proof_loss_weight_in_primary_objective": 0.0,
            "protected_objectives": list(PROOF_AUXILIARY_PROTECTED_OBJECTIVES),
            "separate_parameters": True,
            "anti_copy_protected": True,
            "primary_representation_protected": True,
            "heads": list(PROOF_AUXILIARY_HEAD_NAMES),
            "head_schema_version": PROOF_AUXILIARY_HEAD_SCHEMA_VERSION,
            "training_schema_version": PROOF_AUXILIARY_TRAINING_SCHEMA_VERSION,
            "architecture": architecture,
            "rule": "Proof-feedback updates may change only proof_auxiliary_head_logits and applied_proof_feedback_ids/version fingerprint. Compiler CE, embedding, structural, provenance, and anti-copy parameters stay frozen.",
        },
        "matched_t2_checkpoints": [
            {
                "seed": seed,
                "identity_sha256": next(item["t2_checkpoint_identity"] for item in t3_by_seed if item["seed"] == seed),
                "path": f"papers/completion/autoformalization/receipts/snapshots/AF-011/checkpoints/states/T2-{seed}-final.json",
            }
            for seed in SEEDS
        ],
        "t3_empirical": {
            "status": t3_status,
            "scope": t3_scope,
            "admitted_records": 0,
            "seeds": t3_by_seed,
            "reason": t3_reason,
        },
        "isolation_probes": isolation_by_seed,
        "filter_accounting": {
            "applied_count": filter_report["applied_count"],
            "duplicate_count": duplicate_report["duplicate_count"],
            "skipped_holdout_count": filter_report["skipped_holdout_count"],
            "skipped_invalid_count": filter_report["skipped_invalid_count"],
            "skipped_untrusted_count": filter_report["skipped_untrusted_count"],
            "skipped_version_mismatch_count": filter_report["skipped_version_mismatch_count"],
            "objective_isolation": filter_report["objective_isolation"],
        },
        "held": isolation_ok,
        "predicted_proof_success_used_as_certification": False,
        "calibration_and_routing": {
            "eligible_native_label_count": eligible_native_labels,
            "calibration_error": None,
            "route_value": None,
            "matched_route_budget": True,
            "actual_checker_outcomes": 0,
            "isolation_probe_metrics_are_not_t3_certification": True,
        },
    }

    current_manifest = PAPER_ROOT / "data" / "proof_feedback_manifest.json"
    current_results = PAPER_ROOT / "runs" / "proof_heads" / "results.jsonl"
    current_isolation = PAPER_ROOT / "evidence" / "proof_head_isolation.json"
    write_json(current_manifest, manifest)
    write_jsonl(current_results, results)
    write_json(current_isolation, isolation)
    write_json(HERE / "data" / "proof_feedback_manifest.json", manifest)
    write_jsonl(HERE / "runs" / "proof_heads" / "results.jsonl", results)
    write_json(HERE / "evidence" / "proof_head_isolation.json", isolation)
    write_json(
        HERE / "capability_probe.json",
        {
            "environment": env,
            "elapsed_seconds": round(time.time() - started, 3),
            "t3_scope": t3_scope,
            "isolation_held": isolation_ok,
        },
    )
    print(
        json.dumps(
            {
                "admitted_count": 0,
                "elapsed_seconds": round(time.time() - started, 3),
                "isolation_held": isolation_ok,
                "native_usable": native_usable,
                "t3_scope": t3_scope,
                "train_units": len(train_ids),
                "selection_units": len(selection_ids),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if isolation_ok and t3_unrun_ok and not native_usable else 1


if __name__ == "__main__":
    raise SystemExit(main())
