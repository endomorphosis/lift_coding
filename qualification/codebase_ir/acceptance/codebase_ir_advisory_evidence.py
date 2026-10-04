"""Bounded stdlib audit of explicitly pinned advisory stages and attempt costs.

Structural equality and byte identities do not authenticate signatures, run
numerical work, or qualify a complete joined execution.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from codebase_ir_admission_evidence import (
    AdmissionEvidenceError,
    assert_admission,
    canonical,
    cid,
    exact,
    need,
    parse_document,
    raw_cid,
)
from codebase_ir_external_pins import _bounded_document

SCHEMA = "codebase-ir-advisory-retained-audit@1"
INPUT_SCHEMA = "codebase-ir-advisory-audit-input@1"
MAX_FILES = 256
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_MANIFEST_BYTES = 256 * 1024
MAX_OBSERVATION_SECONDS = 3600
ATTEMPTS = ("01", "02", "03", "04", "05", "06")
STAGED = {"02", "05", "06"}
TRAIN_PHASES = ("root_training", "initial_child_training", "successor_child_training")
TRAIN_DIRS = (
    "root-training-context",
    "initial-child-training-context",
    "successor-child-training-context",
)
ADVISORY_FIELDS = (
    "source_cid",
    "query",
    "domain_inputs",
    "domain_cid",
    "observations",
    "eligible_clause_ids",
    "residual_clause_ids",
    "clause_results",
    "selected_task_ids",
    "declared_task_requirement_ids",
    "candidate_task_meaning",
    "current_facts_count",
    "operation_catalog_cid",
)
COLD_FIELDS = (
    "source_cid",
    "query",
    "domain_inputs",
    "observations",
    "eligible_requirement_ids",
    "residual_requirement_ids",
    "finite_selected_task_ids",
    "operation_catalog_cid",
    "model_status",
)
CONTEXT_FALSE = {
    "admission_authority",
    "behavior_authority",
    "behavioral_satisfaction",
    "completion_authority",
    "convergence_proved",
    "execution_authority",
    "formal_decoder_available",
    "formalized",
    "mutation_authority",
    "promotion_performed",
    "proof_authority",
    "qualified",
    "runtime_behavior_verified",
    "source_semantics_verified",
}
NATIVE_FEATURE_FALSE = {
    "qualified",
    "admitted",
    "formalized",
    "promotion_performed",
    "proof_authority",
    "source_runtime_semantics_verified",
    "behavioral_satisfaction",
    "admission_authority",
    "completion_authority",
}
MEASUREMENT_FALSE = {
    "behavior_authority",
    "completion_authority",
    "convergence_proved",
    "decoder_384d_qualified",
    "execution_authority",
    "generalization_verified",
    "mutation_authority",
    "omission_authority",
    "production_admitted",
    "proof_authority",
    "public_terminal_bench_task_satisfied",
    "runtime_behavior_verified",
    "signed_evidence_admitted",
    "source_semantics_verified",
    "training_convergence_proved",
    "whole_program_semantics_verified",
    "worker_launched",
}
INCLUSIVE = {"private_native_execution_scope_inclusive", "native_typed_owner_lifetime_inclusive"}
INVENTORY = sorted(
    [
        "calc.py",
        "canary.py",
        "check_offset.py",
        "check_type.py",
        "consumer.py",
        "decoy.py",
        "known_variant.py",
        "support.py",
        "tune.py",
        "unsupported.py",
    ]
)


def integer(value: Any) -> bool:
    return type(value) is int and value >= 0


def seconds(value: Any) -> bool:
    return (
        type(value) in {int, float}
        and math.isfinite(value)
        and 0 <= value <= MAX_OBSERVATION_SECONDS
    )


def digest(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def false_fields(value: Any, fields: set[str]) -> None:
    need(
        type(value) is dict and fields <= set(value) and all(value[key] is False for key in fields),
        "missing or altered required false authority fields",
    )


def role_paths(attempt: str) -> dict[str, str]:
    """Closed selected public inputs for this six-attempt cohort; never discover files."""
    paths = {"host": "host-resource-admission.json"}
    if attempt == "04":
        return paths
    paths |= {
        "wrapper": "container-execution-final.json",
        "wrapper_initial": "container-execution.json",
        "outcome": "native/result.json" if attempt == "06" else "native/failure.json",
        "phases": "native/phase-costs.json",
    }
    if attempt == "01":
        return paths
    paths |= {
        "epochs": "native/training-attempts.json",
        "total": "native/total-cost.json",
        "native_resources": "native/private/resource-admission.json",
        "criteria": "native/criteria.json",
        "selections": "native/training-selections.json",
        "measurements": "native/training-measurements.json",
    }
    count = 2 if attempt == "03" else 3
    for number, directory in enumerate(TRAIN_DIRS[:count]):
        for name in (
            "context",
            "checkpoint",
            "lineage",
            "invocation",
            "record",
            "inference",
            "metrics",
        ):
            paths[f"train{number}_{name}"] = f"native/private/advisory/{directory}/{name}.json"
    if attempt in STAGED:
        paths |= {
            "before": "native/before-admission.json",
            "successor": "native/successor-admission.json",
            "cold": "native/cold-admission.json",
            "materialized": "native/materialized.json",
            "bridge": "native/candidate-bridge.json",
            "descriptor": "native/candidate-descriptor.json",
            "generated": "native/generated-candidate.json",
            "reviewed": "native/reviewed-candidate.json",
            "replacement": "native/private/candidate-artifacts/candidate.py",
            "handoff": "handoffs/candidate.json",
            "initial_comparison": "native/initial-advisory-comparison.json",
            "successor_comparison": "native/successor-advisory-comparison.json",
            "cold_comparison": "native/cold-comparison.json",
            "lifecycle": "native/native-lifecycle.json",
            "scope": "native/execution-scope.json",
            "cleanup": "native/owner-fixture-worktree-cleanup.json",
            "replay_resources": "native/fresh-current-resource-admission.json",
        }
        for label in (
            "initial-off",
            "root-frozen",
            "initial-child-frozen",
            "successor-off",
            "successor-frozen",
        ):
            paths["preview_" + label] = f"native/private/advisory/{label}-preview.json"
    if attempt in {"05", "06"}:
        paths["transcript"] = "native/fresh-process.json"
    if attempt == "06":
        paths |= {
            "replay": "native/fresh-process-replay.json",
            "response": "native/fresh-process-response.json",
        }
    return paths


class PinnedReader:
    def __init__(self):
        self.pins: dict[str, dict[str, Any]] = {}
        self.total = 0

    def read(self, path: Path, expected: dict[str, Any] | None = None, *, manifest=False) -> bytes:
        need(
            path.is_absolute()
            and path.resolve(strict=True) == path
            and not any(part.is_symlink() for part in (path, *path.parents)),
            "noncanonical or symlink input path",
        )
        key = str(path)
        if key not in self.pins:
            need(len(self.pins) < MAX_FILES, "input file count budget exceeded")
        limit = min(
            MAX_MANIFEST_BYTES if manifest else MAX_FILE_BYTES, MAX_TOTAL_BYTES - self.total
        )
        if key in self.pins:
            limit = self.pins[key]["bytes"]
        elif expected is not None:
            need(
                integer(expected["bytes"]) and expected["bytes"] <= limit,
                "input byte budget exceeded before read",
            )
            limit = expected["bytes"]
        need(limit >= 0, "input aggregate byte budget exceeded")
        raw = _bounded_document(path, limit)
        observed = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
        if expected is not None:
            need(
                observed == {key: expected[key] for key in observed},
                "selected input raw pin mismatch",
            )
        if key in self.pins:
            need(observed == self.pins[key], "selected input changed between reads")
        else:
            self.pins[key] = observed
            self.total += len(raw)
        return raw

    def recheck(self) -> bool:
        for path, pin in tuple(self.pins.items()):
            self.read(Path(path), pin)
        return True


def validate_manifest(spec: Any) -> None:
    need(
        type(spec) is dict
        and set(spec) == {"schema", "attempts"}
        and spec["schema"] == INPUT_SCHEMA,
        "closed advisory input schema required",
    )
    cases = spec["attempts"]
    need(
        type(cases) is list and [case["id"] for case in cases] == list(ATTEMPTS),
        "complete ordered six-attempt history required",
    )
    all_paths, declared_bytes = set(), 0
    for case in cases:
        need(
            type(case) is dict and set(case) == {"id", "root", "files"},
            "closed attempt root mapping required",
        )
        root = Path(case["root"])
        need(
            type(case["root"]) is str
            and root.is_absolute()
            and str(root) == case["root"]
            and root.resolve(strict=False) == root
            and not any(part.is_symlink() for part in (root, *root.parents)),
            "absolute canonical root mapping required",
        )
        files = case["files"]
        paths = role_paths(case["id"])
        need(
            type(files) is list and len(files) == len(paths),
            "complete selected role population required",
        )
        roles = []
        for pin in files:
            need(
                type(pin) is dict and set(pin) == {"role", "path", "sha256", "bytes"},
                "closed raw input pin required",
            )
            role, selected = pin["role"], pin["path"]
            need(
                type(role) is str
                and role in paths
                and selected == paths[role]
                and type(selected) is str
                and str(PurePosixPath(selected)) == selected
                and ".." not in PurePosixPath(selected).parts
                and not PurePosixPath(selected).is_absolute(),
                "foreign or noncanonical role selector",
            )
            need(
                digest(pin["sha256"]) and integer(pin["bytes"]) and pin["bytes"] <= MAX_FILE_BYTES,
                "exact bounded raw SHA256 pin required",
            )
            roles.append(role)
            path = str(root / selected)
            need(path not in all_paths, "cross-attempt root or selected-file alias")
            all_paths.add(path)
            declared_bytes += pin["bytes"]
        need(
            len(set(roles)) == len(roles) and set(roles) == set(paths),
            "duplicate or missing input roles",
        )
    need(
        len(all_paths) < MAX_FILES and declared_bytes <= MAX_TOTAL_BYTES - MAX_MANIFEST_BYTES,
        "declared aggregate input budget exceeded",
    )


def load_inputs(spec: dict[str, Any], reader: PinnedReader) -> dict[str, Any]:
    validate_manifest(spec)
    cases = {}
    for case in spec["attempts"]:
        root = Path(case["root"])
        need(
            root.resolve(strict=True) == root and root.is_dir(),
            "canonical retained attempt directory required",
        )
        records, pins = {}, {}
        for pin in case["files"]:
            raw = reader.read(root / pin["path"], pin)
            records[pin["role"]] = raw if pin["role"] == "replacement" else parse_document(raw)
            pins[pin["role"]] = {**pin, "absolute_path": str(root / pin["path"])}
        cases[case["id"]] = {"records": records, "pins": pins}
    return cases


def raw_pin(case: dict[str, Any], role: str, value: Any) -> None:
    """Selected native JSON artifacts use exact compact canonical native bytes."""
    raw = (
        value
        if type(value) is bytes
        else json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode()
    )
    pin = case["pins"][role]
    need(
        hashlib.sha256(raw).hexdigest() == pin["sha256"] and len(raw) == pin["bytes"],
        "correlated mutation crossed selected raw artifact anchor",
    )


def descriptor(case: dict[str, Any], value: Any, role: str) -> None:
    pin = case["pins"][role]
    original = (
        "/opt/ipfs-supervisor/finite-handoffs/candidate.json"
        if role == "handoff"
        else "/results/" + pin["path"]
    )
    need(
        value["path"] == original
        and value["sha256"] == pin["sha256"]
        and value["bytes"] == pin["bytes"],
        "artifact descriptor differs from exact selected role/raw pin",
    )


def projection(preview: dict[str, Any]) -> dict[str, Any]:
    match = preview["match"]
    return {
        key: match[key]
        for key in (
            "source_cid",
            "query",
            "domain_inputs",
            "domain_cid",
            "eligible_clause_ids",
            "residual_clause_ids",
            "clause_results",
        )
    } | {
        "observations": match["observation"]["observations"],
        "selected_task_ids": preview["selected_task_ids"],
        "declared_task_requirement_ids": preview["declared_task_requirement_ids"],
        "candidate_task_meaning": preview["candidate_plan"]["tasks"],
        "current_facts_count": preview["current_facts_count"],
        "operation_catalog_cid": preview["operation_catalog_cid"],
    }


def assert_comparison(records: dict[str, Any], *, successor: bool) -> dict[str, Any]:
    label = "successor" if successor else "initial"
    comparison = records[label + "_comparison"]
    labels = (
        ("successor-off", "successor-frozen")
        if successor
        else ("initial-off", "root-frozen", "initial-child-frozen")
    )
    views = [records["preview_" + name] for name in labels]
    expected = projection(views[0])
    need(
        comparison["schema"] == "finite-advisory-mode-comparison@1"
        and comparison["agreement"] is True
        and exact(comparison["compared_fields"], list(ADVISORY_FIELDS))
        and exact(comparison["projection"], expected)
        and all(exact(projection(view), expected) for view in views),
        "complete thirteen-field advisory mode invariant differs",
    )
    references = [
        {
            "label": name,
            "result_cid": view["result_cid"],
            "feature_context_cid": view["feature_context"]["context_cid"],
        }
        for name, view in zip(labels, views, strict=True)
    ]
    need(
        exact(references, comparison["preview_records"])
        and len({row["feature_context_cid"] for row in references}) == len(labels),
        "advisory modes or distinct context identities relabeled",
    )
    false_fields(
        comparison, {"features_choose_fixed_edit", "execution_authority", "completion_authority"}
    )
    for name, view in zip(labels, views, strict=True):
        binding = view["feature_context"]
        need(
            binding["context_cid"]
            == cid({key: value for key, value in binding.items() if key != "context_cid"}),
            "embedded advisory context content identity differs",
        )
        false_fields(binding["authority"], CONTEXT_FALSE)
        off = name.endswith("-off")
        need(
            binding["mode"] == ("model_off" if off else "frozen")
            and binding["model_enabled"] is (not off)
            and type(binding["actual_training_delta"]) is int
            and binding["actual_training_delta"] == 0,
            "advisory mode/model-enabled/delta contradicts no-fit selected mode",
        )
        if off:
            need(
                all(
                    binding[key] is None
                    for key in (
                        "version_id",
                        "parent_version_id",
                        "state_sha256",
                        "feature_space_sha256",
                        "contract_sha256",
                        "model_record_cid",
                        "candidate_checkpoint_raw_cid",
                        "selection_version_cid",
                    )
                )
                and exact(binding["selected_optimizer_steps"], [])
                and type(binding["selected_total_epochs"]) is int
                and binding["selected_total_epochs"] == 0
                and set(binding["artifacts"]) == {"invocation"},
                "model-off context carries selected numerical state",
            )
        false_fields(
            view,
            {
                "execution_authority",
                "completion_authority",
                "production_admitted",
                "proof_authority",
            },
        )
        need(
            type(view["training_steps_during_preview"]) is int
            and view["training_steps_during_preview"] == 0,
            "preview performed fitting",
        )
    return expected


def assert_selected_models(records: dict[str, Any], *, completed: bool) -> None:
    """Bind frozen selection to separately byte-pinned native training records."""
    for label, number in (("root-frozen", 0), ("initial-child-frozen", 1), ("successor-frozen", 2)):
        frozen, trained = (
            records["preview_" + label]["feature_context"],
            records[f"train{number}_context"],
        )
        varying = {"mode", "actual_training_delta", "context_cid", "artifacts"}
        need(
            set(frozen) == set(trained)
            and all(exact(frozen[key], trained[key]) for key in set(trained) - varying),
            "frozen preview selected state/feature/record/contract/source/optimizer differs from independent trained context",
        )
        need(
            set(frozen["artifacts"]) == set(trained["artifacts"]),
            "frozen model artifact role population differs",
        )
        for role, artifact in frozen["artifacts"].items():
            need(
                set(artifact)
                == {"schema", "role", "relative_path", "sha256", "size_bytes", "blob_cid"}
                and artifact["schema"] == "supervisor-codebase-feature-blob@1"
                and artifact["role"] == role
                and artifact["relative_path"] == role + ".json"
                and digest(artifact["sha256"])
                and integer(artifact["size_bytes"])
                and artifact["size_bytes"] <= MAX_FILE_BYTES
                and artifact["blob_cid"]
                == cid({key: value for key, value in artifact.items() if key != "blob_cid"}),
                "frozen artifact descriptor shape/digest/content identity differs",
            )
            if role in {"checkpoint", "record", "lineage"}:
                need(
                    exact(artifact, trained["artifacts"][role]),
                    "frozen artifact changed independently pinned checkpoint/record/lineage bytes",
                )
    if completed:
        outcome = records["outcome"]
        need(
            outcome["selected_initial_model_version_id"] == records["train1_context"]["version_id"]
            and outcome["selected_successor_model_version_id"]
            == records["train2_context"]["version_id"],
            "completed result selected model identity differs from independent initial/successor training records",
        )
        need(
            exact(outcome["training_measurements"], records["measurements"]["measurements"])
            and exact(outcome["continuations"], records["measurements"]["continuations"]),
            "completed result duplicated measurements/continuations differ from independent records",
        )
        need(
            exact(outcome["initial_advisory_comparison"], records["initial_comparison"])
            and exact(outcome["successor_advisory_comparison"], records["successor_comparison"])
            and exact(outcome["candidate_bridge"], records["bridge"]),
            "completed result duplicated advisory/bridge stages differ from independent records",
        )


def assert_training(case: dict[str, Any], attempt: str) -> tuple[int, int]:
    records = case["records"]
    ledger = records.get("epochs", records.get("outcome", {}).get("training_observation"))
    if ledger is None:
        need(attempt == "04", "missing returned training attempt ledger")
        return 0, 0
    need(
        ledger["schema"] == "finite-advisory-observed-training-attempts@1"
        and type(ledger["attempts"]) is list
        and integer(ledger["known_actual_attempted_epochs"])
        and integer(ledger["unknown_fitting_attempt_count"]),
        "exact observed epoch accounting required",
    )
    count = 0 if attempt == "01" else (2 if attempt == "03" else 3)
    rows = ledger["attempts"]
    need(
        len(rows) == count and [row["phase"] for row in rows] == list(TRAIN_PHASES[:count]),
        "returned fitting phase population differs",
    )
    epoch_counts(ledger)
    total, unknown = 0, 0
    prior = None
    if count:
        need(
            records["criteria"]["configuration"]
            == {"epochs": 16, "learning_rate": 0.01, "seed": 1729},
            "training configuration differs",
        )
        need(
            records["selections"]
            == [
                {"contracts": [], "path": path, "role": role}
                for path, role in (
                    ("calc.py", "train"),
                    ("known_variant.py", "train"),
                    ("tune.py", "tune"),
                    ("canary.py", "canary"),
                )
            ],
            "transductive training/evaluation cohort differs",
        )
        need(
            len(records["measurements"]["measurements"]) == count,
            "returned measurement population differs",
        )
    for number, row in enumerate(rows):
        need(
            row["status"] == "completed" and integer(row["requested_epochs"]),
            "selected retained checkpoint records establish returned fitting; unknown/relabelled phase refused",
        )
        binding = records[f"train{number}_context"]
        checkpoint = records[f"train{number}_checkpoint"]
        state, report = checkpoint["state"], checkpoint["report"]
        raw_pin(case, f"train{number}_checkpoint", checkpoint)
        raw_pin(case, f"train{number}_context", binding)
        need(
            binding["schema"] == "supervisor-codebase-feature-context@1"
            and binding["mode"] == "train"
            and binding["profile"] == "codebase_ir/source_bound_feature_v1"
            and binding["latent_width"] == 8
            and binding["parameter_dtype"] == "float64"
            and binding["model_enabled"] is True
            and binding["context_cid"]
            == cid({key: value for key, value in binding.items() if key != "context_cid"}),
            "native structural training context identity differs",
        )
        need(
            set(binding["authority"]) == CONTEXT_FALSE,
            "closed advisory authority population differs",
        )
        false_fields(binding["authority"], CONTEXT_FALSE)
        need(
            integer(row["actual_attempted_epochs"])
            and row["actual_attempted_epochs"]
            == report["attempted_epochs"]
            == binding["actual_training_delta"]
            == 16
            and row["requested_epochs"] == 16,
            "returned epochs differ from actual checkpoint report/context",
        )
        need(
            row["context_cid"] == binding["context_cid"]
            and row["version_id"] == binding["version_id"]
            and row["parent_version_id"]
            == binding["parent_version_id"]
            == (None if prior is None else prior["version_id"]),
            "ordered native child lineage differs",
        )
        need(
            binding["selected_total_epochs"] == state["completed_epochs"]
            and exact(
                binding["selected_optimizer_steps"], [item["step"] for item in state["adam"]]
            ),
            "selected optimizer state mistaken for attempted epoch count",
        )
        need(
            type(state["latent_width"]) is int
            and state["latent_width"] == 8
            and binding["state_sha256"] == hashlib.sha256(canonical(state)).hexdigest()
            and binding["feature_space_sha256"]
            == hashlib.sha256(canonical(checkpoint["feature_space"])).hexdigest()
            and exact(report["codebase_provenance"]["head"], binding["head"]),
            "checkpoint state/feature/source identity differs",
        )
        need(
            set(binding["artifacts"])
            == {"checkpoint", "lineage", "invocation", "record", "inference", "metrics"},
            "complete native model artifact roles required",
        )
        for name, artifact in binding["artifacts"].items():
            role = f"train{number}_{name}"
            raw_pin(case, role, records[role])
            need(
                role in case["pins"]
                and artifact["sha256"] == case["pins"][role]["sha256"]
                and artifact["size_bytes"] == case["pins"][role]["bytes"]
                and artifact["relative_path"] == name + ".json"
                and artifact["blob_cid"]
                == cid({key: value for key, value in artifact.items() if key != "blob_cid"}),
                "retained native model artifact binding differs",
            )
        record, inference = records[f"train{number}_record"], records[f"train{number}_inference"]
        false_fields(record["authority"], NATIVE_FEATURE_FALSE)
        false_fields(inference["authority"], NATIVE_FEATURE_FALSE)
        need(
            binding["model_record_cid"] == cid(record)
            and record["version_id"] == binding["version_id"]
            and exact(record["head"], binding["head"])
            and inference["version_id"] == binding["version_id"]
            and exact(inference["head"], binding["head"])
            and inference["training_executed"] is False,
            "native record/inference source/version authority differs",
        )
        lineage = records[f"train{number}_lineage"]
        need(
            len(lineage) == number + 1
            and exact(lineage[0]["checkpoint"], checkpoint)
            and [item["version"]["version_id"] for item in lineage]
            == [records[f"train{k}_context"]["version_id"] for k in range(number, -1, -1)]
            and all(
                exact(item["checkpoint"], records[f"train{k}_checkpoint"])
                for item, k in zip(lineage, range(number, -1, -1), strict=True)
            ),
            "complete ordered checkpoint ancestry differs",
        )
        if prior is not None:
            parent = records[f"train{number - 1}_checkpoint"]
            need(
                report["base_state_sha256"]
                == hashlib.sha256(canonical(parent["state"])).hexdigest()
                and exact(checkpoint["feature_space"], parent["feature_space"])
                and exact(checkpoint["contract"], parent["contract"])
                and exact(state["optimizer_config"], parent["state"]["optimizer_config"]),
                "child changed frozen basis or exact Adam parent state",
            )
            provenance, parent_provenance = (
                report["codebase_provenance"],
                parent["report"]["codebase_provenance"],
            )
            need(
                provenance["continuation"] == "exact_frozen_basis_adam_resume"
                and all(
                    exact(provenance[key], parent_provenance[key])
                    for key in ("selections", "tuning_targets", "canary_targets", "replay_targets")
                ),
                "child changed fixed split/evaluation ancestry",
            )
        measurement = records["measurements"]["measurements"][number]
        need(
            measurement["attempted_epochs"] == row["actual_attempted_epochs"]
            and measurement["version_id"] == binding["version_id"]
            and measurement["parent_version_id"] == binding["parent_version_id"]
            and measurement["context_cid"] == binding["context_cid"]
            and exact(measurement["optimizer_steps"], binding["selected_optimizer_steps"]),
            "measurement/returned checkpoint join differs",
        )
        false_fields(measurement, MEASUREMENT_FALSE)
        total += row["actual_attempted_epochs"]
        prior = binding
    need(
        total == ledger["known_actual_attempted_epochs"]
        and unknown == ledger["unknown_fitting_attempt_count"],
        "returned versus unknown epoch totals differ",
    )
    outcome = records.get("outcome", {})
    if "training_observation" in outcome:
        need(
            exact(outcome["training_observation"], ledger),
            "failure receipt disagrees with returned fitting ledger",
        )
    return total, unknown


def epoch_counts(ledger: dict[str, Any]) -> tuple[int, int]:
    rows = ledger["attempts"]
    need(type(rows) is list and len(rows) <= 8, "bounded fitting attempt population required")
    returned, unknown = 0, 0
    for row in rows:
        amount = row["actual_attempted_epochs"]
        if amount is None:
            need(
                row["status"] in {"running", "failed_unknown_actual_fitting"},
                "missing returned work must retain unknown fitting disposition",
            )
            unknown += 1
        else:
            need(
                integer(amount) and row["status"] == "completed",
                "completed exact returned epoch count required",
            )
            returned += amount
    need(
        type(ledger["known_actual_attempted_epochs"]) is int
        and type(ledger["unknown_fitting_attempt_count"]) is int
        and (returned, unknown)
        == (ledger["known_actual_attempted_epochs"], ledger["unknown_fitting_attempt_count"]),
        "known/unknown fitting ledger totals differ",
    )
    return returned, unknown


def assert_stages(case: dict[str, Any], attempt: str) -> dict[str, Any]:
    records = case["records"]
    assert_admission(records["before"], successor=False)
    assert_admission(records["successor"], successor=True)
    assert_admission(records["cold"], successor=True)
    tasks = {row["task_key"]: row["content_id"] for row in records["before"]["graph"]["tasks"]}
    need(
        all(
            exact(
                tasks,
                {row["task_key"]: row["content_id"] for row in records[name]["graph"]["tasks"]},
            )
            for name in ("successor", "cold")
        ),
        "original native task meanings/population changed across successor",
    )
    initial = assert_comparison(records, successor=False)
    successor = assert_comparison(records, successor=True)
    assert_selected_models(records, completed=attempt == "06")
    need(
        exact(initial, projection(records["before"]["evidence"]))
        and exact(successor, projection(records["successor"]["evidence"])),
        "advisory comparisons detached from signed model-off evidence",
    )
    bridge, generated, descriptor_value = (
        records[name] for name in ("bridge", "generated", "descriptor")
    )
    handoff = records["handoff"]
    raw_pin(case, "handoff", handoff)
    for role, field in (
        ("generated", "generated_result_pin"),
        ("reviewed", "reviewed_candidate_pin"),
        ("initial_comparison", "advisory_comparison_pin"),
        ("handoff", "public_candidate_pin"),
    ):
        descriptor(case, bridge[field], role)
    descriptor(case, bridge["replacement_artifact"], "replacement")
    need(
        bridge["schema"] == "finite-advisory-trusted-proposal-native-handoff@1"
        and bridge["finite_admission_cid"] == cid(records["before"])
        and bridge["semantic_context_cid"]
        == records["before"]["receipt"]["payload"]["semantic_context_cid"]
        and bridge["task_cid"] == tasks["FINITE-OFFSET"]
        and type(bridge["task_revision"]) is int
        and bridge["task_revision"] == 1,
        "bridge admission/task/ready revision differs",
    )
    need(
        exact(bridge["public_candidate_descriptor"], descriptor_value)
        and descriptor_value["task_id"] == "FINITE-OFFSET"
        and all(
            exact(descriptor_value[key], bridge[key])
            for key in (
                "task_cid",
                "task_revision",
                "finite_admission_cid",
                "semantic_context_cid",
                "before_sha256",
                "after_sha256",
            )
        ),
        "public handoff descriptor changed native task meaning",
    )
    need(
        bridge["advisory_context_cids"]
        == [row["feature_context_cid"] for row in records["initial_comparison"]["preview_records"]],
        "proposal bridge changed advisory context selection",
    )
    replacement = records["replacement"]
    need(
        replacement == b"def increment(n: int) -> int:\n    return n + 2\n"
        and bridge["replacement_raw_cid"] == raw_cid(replacement)
        and bridge["replacement_sha256"]
        == bridge["after_sha256"]
        == hashlib.sha256(replacement).hexdigest()
        and generated["replacement_cid"] == bridge["replacement_raw_cid"]
        and generated["result_cid"] == bridge["generated_result_cid"]
        and generated["reviewed_candidate_cid"] == bridge["reviewed_candidate_cid"]
        and generated["task_cid"] == tasks["FINITE-OFFSET"],
        "trusted proposal bytes/task identity differ",
    )
    false_fields(
        bridge,
        {
            "completion_authority",
            "execution_authority",
            "publication_authority",
            "features_choose_fixed_edit",
        },
    )
    false_fields(
        generated,
        {
            "execution_authority",
            "completion_authority",
            "mutation_authority",
            "publication_authority",
            "proof_authority",
            "production_activation",
            "owner_keys_inaccessible",
            "process_origin_attested",
        },
    )
    for key in (
        "canonical_source_unchanged",
        "native_task_rows_unchanged",
        "model_registry_unchanged",
    ):
        need(bridge[key] is True, "proposal altered owner state")
    child = generated["child_process"]
    need(
        type(child["returncode"]) is int
        and child["returncode"] == 0
        and generated["status"] == "candidate_generated"
        and generated["result_cid"]
        == cid({key: value for key, value in generated.items() if key != "result_cid"})
        and exact(generated["parent_admission"], records["before"])
        and exact(generated["reviewed_candidate"], records["reviewed"]),
        "trusted proposal parent/result did not bind actual retained originals",
    )
    false_fields(
        child, {"cancelled", "timed_out", "resource_exhausted", "output_truncated", "unavailable"}
    )
    lifecycle = records["lifecycle"]
    need(
        lifecycle["worker_launched"] is True
        and lifecycle["status"] == "incomplete"
        and sorted(lifecycle["inventory_paths"]) == INVENTORY,
        "completed worker stage/checkpoint inventory differs",
    )
    false_fields(
        lifecycle,
        {
            "production_activated",
            "task_omission_authority",
            "features_choose_fixed_edit",
            "formal_decoder_available",
            "cuda_qualified",
            "384d_qualified",
            "universal_python_semantics_proved",
        },
    )
    for control in ("start", "stop"):
        value = lifecycle[control]
        need(
            value["operation"] == control and value["status"] == "succeeded",
            "START/STOP stage did not succeed",
        )
    cleanup = lifecycle["stop"]["data"]["isolated_worker_cleanup"]
    need(
        type(cleanup["worker_uid"]) is int
        and cleanup["worker_uid"] == 1001
        and type(cleanup["returncode"]) is int
        and cleanup["returncode"] == 0
        and cleanup["single_worker"] is True
        and cleanup["completion_authority"] is False
        and lifecycle["stop"]["data"]["old_tree_fenced"] is True
        and lifecycle["stop"]["data"]["new_process_identity"] is None
        and type(lifecycle["remaining_processes"]) is int
        and lifecycle["remaining_processes"] == 0
        and lifecycle["bootstrap_errors"] == [],
        "retained STOP/UID cleanup differs",
    )
    task = lifecycle["task"]
    need(
        task["status"] == "completed" and type(task["revision"]) is int and task["revision"] == 4,
        "native residual stage not completed at expected revision",
    )
    completion = task["body"]["completion_receipt"]
    transition = completion["validation"]["accepted_source_transition"]
    database = transition["database_attempt_binding"]
    need(
        completion["operation"] == "database_complete"
        and completion["validation"]["outcome"] == "passed"
        and transition["database_task_cid"] == database["task_cid"] == tasks["FINITE-OFFSET"]
        and transition["task_alias"] == "FINITE-OFFSET",
        "worker completion/task population differs",
    )
    for key in ("attempt_id", "claim_id", "lease_id", "fence_epoch", "fencing_token"):
        need(exact(completion[key], database[key]), "retained claim/fence crossing differs")
    for key in ("fence_epoch", "fencing_token"):
        need(
            type(completion[key]) is int and completion[key] == 1,
            "exact positive native fence required",
        )
    need(
        transition["baseline_ref"] == lifecycle["original_commit"]
        and transition["integration_commit_proof"]["passed"] is True
        and transition["declared_output_invariant"]["passed"] is True,
        "publication baseline/output stage differs",
    )
    for name in ("before", "successor", "cold"):
        manifest = records[name]["declaration"]["payload"]["manifest"]["payload"]
        expected_source = (
            b"def increment(n: int) -> int:\n    return n + 1\n"
            if name == "before"
            else replacement
        )
        need(
            sorted(manifest["sources"]) == INVENTORY
            and manifest["sources"]["calc.py"]["sha256"]
            == hashlib.sha256(expected_source).hexdigest()
            and manifest["baseline_commit"]
            == (lifecycle["original_commit"] if name == "before" else transition["merge_commit"]),
            "signed source population/baseline differs from original or published worker stage",
        )
    owner_cleanup = records["cleanup"]
    expected_allocations = (
        [("settling", 4)] if attempt == "05" else [("preparing", 1), ("settling", 4)]
    )
    need(
        type(owner_cleanup) is list
        and len(owner_cleanup) == 1
        and [(row["state"], row["fence"]) for row in lifecycle["observed_worker_allocations"]]
        == expected_allocations
        and owner_cleanup[0]["scope"]
        == "explicit owner fixture cleanup after native STOP; not native completion recovery",
        "explicit owner cleanup relabeled or allocation population changed",
    )
    initial_allocation, final_allocation = (
        lifecycle["observed_worker_allocations"][0],
        owner_cleanup[0]["allocation"],
    )
    stable_allocation_fields = {
        "attempt",
        "branch",
        "canonical_task_cid",
        "created_at",
        "lane_id",
        "lease_id",
        "merge_target",
        "owner",
        "repo_root",
        "schema",
        "state_dir",
        "task_id",
    }
    need(
        all(
            exact(initial_allocation[key], final_allocation[key])
            for key in stable_allocation_fields
        )
        and exact(lifecycle["observed_worker_allocations"][-1], final_allocation)
        and final_allocation["state"] == "settling"
        and final_allocation["fence"] == 4
        and final_allocation["workspace_path"].startswith(
            "/opt/ipfs-supervisor/worktrees/workspace_"
        )
        and owner_cleanup[0]["native_lifecycle_record_after_stop"] is None,
        "owner cleanup detached from stable allocation identity/observed settling state",
    )
    scope = records["scope"]["payload"]
    need(
        scope["finite_admission_cid"] == bridge["finite_admission_cid"]
        and scope["semantic_context_cid"] == bridge["semantic_context_cid"]
        and scope["candidate"]["descriptor"] == descriptor_value
        and scope["task_population_preserved"] is True,
        "held worker scope detached from admission, handoff or population",
    )
    false_fields(
        scope,
        {
            "completion_authority",
            "production_activation",
            "proof_authority",
            "publication_authority",
            "task_omission_authority",
        },
    )
    cold_comparison = records["cold_comparison"]
    need(
        cold_comparison["agreement"] is True
        and cold_comparison["compared_fields"] == list(COLD_FIELDS),
        "complete cold finite field population differs",
    )
    after = records["successor"]["receipt"]["payload"]["semantic_context"]
    cold = records["cold"]["receipt"]["payload"]["semantic_context"]
    need(
        all(exact(after[key], cold[key]) for key in COLD_FIELDS),
        "cold/successor complete nine-field finite agreement differs",
    )
    for row in (initial, successor):
        need(row["domain_inputs"] == [-2, -1, 0, 1, 2], "finite declared domain changed")
    if attempt == "06":
        result = records["outcome"]
        need(
            all(
                exact(result[key], lifecycle[key])
                for key in (
                    "start",
                    "stop",
                    "task",
                    "task_observations",
                    "observed_worker_allocations",
                    "original_commit",
                )
            )
            and result["published_commit"] == transition["merge_commit"]
            and result["changed_paths"] == ["calc.py"]
            and result["published_commit_parents"]
            == [lifecycle["original_commit"], transition["implementation_commit"]]
            and exact(result["execution_scope_after_stop"], records["scope"]),
            "completed result differs from retained lifecycle/scope/publication stages",
        )
    return {
        "original_tasks": tasks,
        "bridge_task_revision": 1,
        "replacement_sha256": bridge["replacement_sha256"],
        "advisory_comparison_fields": len(ADVISORY_FIELDS),
        "worker_stage_completed": True,
        "native_checkpoint_status": "incomplete",
        "successor_cold_field_count": len(COLD_FIELDS),
        "original_commit": lifecycle["original_commit"],
        "published_commit": transition["merge_commit"],
        "attempt_disposition": "completed"
        if attempt == "06"
        else "failed_with_completed_worker_prefix",
    }


def phase_accounting(rows: Any) -> dict[str, Any]:
    need(type(rows) is list and 0 < len(rows) <= 64, "bounded phase ledger required")
    names, calls, inclusive = set(), [], []
    intervals = []
    for row in rows:
        need(
            type(row) is dict
            and type(row["phase"]) is str
            and row["phase"] not in names
            and row["status"] in {"completed", "failed"}
            and seconds(row["wall_seconds"]),
            "duplicate/malformed finite phase cost",
        )
        names.add(row["phase"])
        if row["phase"] in INCLUSIVE:
            need(
                row.get("cost_scope")
                == "inclusive context lifetime; nested phase costs are not additive",
                "inclusive lifetime mislabeled as disjoint cost",
            )
            inclusive.append({"phase": row["phase"], "seconds": row["wall_seconds"]})
        else:
            need(
                "cost_scope" not in row and type(row.get("started_at")) is str,
                "call cost interval missing or mislabeled",
            )
            start = datetime.fromisoformat(row["started_at"])
            need(start.tzinfo is not None, "phase interval timezone missing")
            intervals.append((start.timestamp(), start.timestamp() + row["wall_seconds"]))
            calls.append(
                {"phase": row["phase"], "seconds": row["wall_seconds"], "status": row["status"]}
            )
    intervals.sort()
    need(
        all(
            left[1] <= right[0] + 0.005
            for left, right in zip(intervals, intervals[1:], strict=False)
        ),
        "recorded call intervals overlap; cannot sum as disjoint calls",
    )
    return {
        "disjoint_recorded_call_seconds": sum(row["seconds"] for row in calls),
        "calls": calls,
        "inclusive_lifetimes_not_added": inclusive,
        "complete_invocation_wall_time_measured": False,
        "wrapper_setup_copy_image_and_scheduler_costs_measured": False,
    }


def assert_attempts(cases: dict[str, Any]) -> dict[str, Any]:
    need(list(cases) == list(ATTEMPTS), "complete retained six-attempt population required")
    facts, summaries, returned, unknown = {}, [], 0, 0
    for attempt, case in cases.items():
        records = case["records"]
        host = records["host"]
        need(
            host["schema_version"] == "legal-ir-global-resource-scheduler-v1"
            and host["leases"] == {}
            and host["waiters"] == {},
            "retained host accounting not drained",
        )
        if attempt == "04":
            need(
                type(host["metrics"]["acquisitions_total"]) is int
                and host["metrics"]["acquisitions_total"] == 0
                and type(host["metrics"]["timeouts_total"]) is int
                and host["metrics"]["timeouts_total"] == 1
                and host["proof_backoff"]["reason"] == "proof_memory_stall",
                "host-refused attempt lacks retained admission refusal",
            )
            need(seconds(host["metrics"]["wait_seconds_total"]), "finite host wait cost required")
            summaries.append(
                {
                    "id": attempt,
                    "disposition": "host_refused",
                    "returned_epochs": 0,
                    "unknown_epoch_attempts": 0,
                    "host_wait_seconds": host["metrics"]["wait_seconds_total"],
                    "native_seconds": None,
                    "wrapper_seconds": None,
                    "no_container_observation_scope": "explicit host-refused selected profile; no live process observation",
                }
            )
            continue
        wrapper, initial, outcome = (
            records[key] for key in ("wrapper", "wrapper_initial", "outcome")
        )
        need(
            wrapper["schema"] == "finite-worker-offline-container-execution@1"
            and wrapper["container_removed"] is True
            and wrapper["container_creation_attempted"] is True
            and wrapper["network"] == "none"
            and wrapper["privileged"] is False
            and all(exact(value, wrapper[key]) for key, value in initial.items()),
            "container accounting/removal or original wrapper projection differs",
        )
        need(
            type(wrapper["returncode"]) is int
            and wrapper["returncode"] == (0 if attempt == "06" else 1)
            and outcome["schema"] == "finite-repository-advisory-native-worker-qualification@1"
            and outcome["status"] == ("completed" if attempt == "06" else "failed"),
            "retained overall attempt disposition changed",
        )
        need(
            seconds(wrapper["elapsed_seconds"])
            and seconds(outcome["elapsed_seconds"])
            and seconds(wrapper["host_reservation"]["wait_seconds"])
            and wrapper["elapsed_seconds"] >= outcome["elapsed_seconds"],
            "native and wrapper timers are inconsistent or nonfinite",
        )
        n, u = assert_training(case, attempt)
        returned += n
        unknown += u
        phases = phase_accounting(records["phases"])
        row = {
            "id": attempt,
            "disposition": outcome["status"],
            "returned_epochs": n,
            "unknown_epoch_attempts": u,
            "native_seconds": outcome["elapsed_seconds"],
            "wrapper_seconds": wrapper["elapsed_seconds"],
            "host_wait_seconds": wrapper["host_reservation"]["wait_seconds"],
            "host_accounting_drained": True,
            "phase_costs": phases,
        }
        if attempt != "06":
            expected_failure = {
                "01": "FileExistsError",
                "02": "TimeoutExpired",
                "03": "LeaseTimeoutError",
                "05": "JSONDecodeError",
            }[attempt]
            need(
                outcome["error_type"] == expected_failure
                and outcome["worker_completion_claimed"] is False
                and outcome["production_activated"] is False,
                "retained failure classification or scope changed",
            )
            row["retained_failure_error_type"] = expected_failure
        cleanup_counts = wrapper["host_resources_after_cleanup"]
        need(
            all(
                type(cleanup_counts[key]) is int and cleanup_counts[key] == 0
                for key in (
                    "active_lease_count",
                    "active_child_lease_count",
                    "active_root_lease_count",
                    "waiting_request_count",
                )
            ),
            "wrapper retained accounting counters disagree with drained host ledger",
        )
        if "total" in records:
            need(
                records["total"]["phase_cost_scope"]
                == "Observed call durations; inclusive scope entries overlap nested phases.",
                "total cost claims disjoint phase aggregation",
            )
            need(
                seconds(records["total"]["elapsed_seconds"]),
                "finite later total checkpoint cost required",
            )
            row["later_total_checkpoint_seconds"] = records["total"]["elapsed_seconds"]
            native = records["native_resources"]
            need(
                native["leases"] == {} and native["waiters"] == {},
                "original native accounting not drained",
            )
        if attempt in STAGED:
            facts[attempt] = assert_stages(case, attempt)
            replay_resources = records["replay_resources"]
            row["archived_fresh_replay_leases"] = len(replay_resources["leases"])
            row["archived_fresh_replay_waiters"] = len(replay_resources["waiters"])
            need(
                (row["archived_fresh_replay_leases"], row["archived_fresh_replay_waiters"])
                == ((2, 1) if attempt == "02" else (0, 0)),
                "archived replay rows rewritten or wrongly described as drained",
            )
            row["container_removal_is_not_archived_ledger_drain"] = True
        if attempt == "02":
            need(
                outcome["error_type"] == "TimeoutExpired"
                and records["phases"][-1]["status"] == "failed",
                "timeout attempt upgraded to completed replay",
            )
        if attempt == "05":
            need(
                outcome["error_type"] == "JSONDecodeError"
                and records["transcript"]["returncode"] == 0
                and records["phases"][-1]["status"] == "completed",
                "successful child replay lost parent protocol failure distinction",
            )
            row["child_replay_returned_zero_parent_protocol_failed"] = True
            lines = records["transcript"]["stdout"].splitlines()
            need(1 < len(lines) <= 256, "failed parent protocol lost exact diagnostic prefix")
            child_replay = parse_document(lines[-1].encode())
            assert_replay(child_replay)
            row["retained_child_response_diagnostic_prefix_lines"] = len(lines) - 1
        if attempt == "06":
            need(
                exact(records["response"], records["replay"])
                and records["transcript"]["returncode"] == 0,
                "response-file replay differs from retained completed payload",
            )
            assert_replay(records["replay"])
            need(
                type(outcome["actual_attempted_training_epochs"]) is int
                and outcome["actual_attempted_training_epochs"] == n,
                "completed result changed returned fitting total",
            )
            false_fields(
                outcome,
                {
                    "production_activated",
                    "task_omission_authority",
                    "universal_python_semantics_proved",
                    "features_choose_fixed_edit",
                    "latent_ranking_available",
                    "formal_decoder_available",
                    "cuda_qualified",
                    "384d_qualified",
                    "metadata_hydration_performed",
                },
            )
            need(
                all(
                    type(outcome[key]) is int and outcome[key] == 0
                    for key in (
                        "provider_calls",
                        "planning_model_calls",
                        "training_steps_during_admission_and_worker",
                        "active_leases",
                        "waiting_requests",
                    )
                ),
                "completed producer reports undeclared fitting, provider work or leaked accounting",
            )
        if attempt in STAGED:
            row["lineage"] = [
                {
                    key: binding[key]
                    for key in (
                        "context_cid",
                        "version_id",
                        "parent_version_id",
                        "head",
                        "selected_total_epochs",
                        "selected_optimizer_steps",
                        "actual_training_delta",
                    )
                }
                for binding in (records[f"train{k}_context"] for k in range(3))
            ]
        summaries.append(row)
    return {
        "attempts": summaries,
        "returned_epochs": returned,
        "unknown_epoch_attempts": unknown,
        "failed_attempt_returned_epochs": sum(
            row["returned_epochs"] for row in summaries if row["disposition"] != "completed"
        ),
        "bound_stage_facts": facts,
        "separate_attempts_are_not_one_training_lineage": True,
        "cost_accounting": {
            "sum_selected_native_attempt_seconds": sum(
                row["native_seconds"] or 0 for row in summaries
            ),
            "sum_selected_wrapper_seconds": sum(row["wrapper_seconds"] or 0 for row in summaries),
            "host_waits_overlap_wrapper_seconds_and_are_not_added": True,
            "inclusive_lifetimes_are_not_added_to_call_or_native_totals": True,
            "complete_invocation_setup_cost_measured": False,
        },
    }


def assert_replay(replay: dict[str, Any]) -> None:
    need(
        replay["schema"] == "finite-advisory-worker-current-and-historical-replay@1"
        and replay["task_statuses"] == {"FINITE-TYPE": "completed", "FINITE-OFFSET": "completed"}
        and replay["current_successor_feature_verified"] is True
        and replay["historical_integrity_verified"] is True,
        "retained fresh replay lost completed original population or stage result",
    )
    false_fields(
        replay,
        {
            "current_freshness_claimed",
            "fitting_performed",
            "promotion_performed",
            "independent_cold_generation_used_for_feature_verification",
        },
    )
    need(
        type(replay["training_steps"]) is int
        and replay["training_steps"] == 0
        and exact(replay["registry_before_verification"], replay["registry_after_verification"]),
        "retained replay fitted or changed reopened registry",
    )


def repin(case: dict[str, Any], role: str) -> None:
    value = case["records"][role]
    raw = (
        value
        if type(value) is bytes
        else json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode()
    )
    case["pins"][role] |= {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def stage_case(case: dict[str, Any]) -> dict[str, Any]:
    """A small inert assertion view; never opens additional artifact paths."""
    return {
        "records": {
            key: value
            for key, value in case["records"].items()
            if not key.startswith("train") or key.endswith("_context")
        },
        "pins": {
            key: value
            for key, value in case["pins"].items()
            if not key.startswith("train") or key.endswith("_context")
        },
    }


FROZEN_CORRUPTIONS = {
    "state_sha256": "0" * 64,
    "feature_space_sha256": "0" * 64,
    "contract_sha256": "0" * 64,
    "selected_total_epochs": 999,
    "selected_optimizer_steps": [999] * 4,
    "actual_training_delta": 999,
    "mode": "train",
    "model_enabled": False,
    "model_record_cid": cid({"foreign": "model"}),
    "parent_version_id": "sha256:" + "0" * 64,
    "candidate_checkpoint_raw_cid": raw_cid(b"foreign checkpoint"),
    "checkpoint_descriptor": "0" * 64,
}


def rebind_preview(case: dict[str, Any], label: str) -> None:
    """Regenerate changed unsigned context/result/bridge references in inert copies."""
    records = case["records"]
    preview = records["preview_" + label]
    binding = preview["feature_context"]
    binding["context_cid"] = cid(
        {key: value for key, value in binding.items() if key != "context_cid"}
    )
    preview["result_cid"] = cid(
        {key: value for key, value in preview.items() if key != "result_cid"}
    )
    comparison_name = (
        "successor_comparison" if label.startswith("successor") else "initial_comparison"
    )
    comparison = records[comparison_name]
    for row in comparison["preview_records"]:
        if row["label"] == label:
            row |= {
                "result_cid": preview["result_cid"],
                "feature_context_cid": binding["context_cid"],
            }
    repin(case, "preview_" + label)
    repin(case, comparison_name)
    if comparison_name == "initial_comparison":
        bridge = records["bridge"]
        bridge["advisory_context_cids"] = [
            row["feature_context_cid"] for row in comparison["preview_records"]
        ]
        bridge["advisory_comparison_pin"] |= {
            key: case["pins"][comparison_name][key] for key in ("sha256", "bytes")
        }
        repin(case, "bridge")
    outcome = records["outcome"]
    outcome["initial_advisory_comparison"] = copy.deepcopy(records["initial_comparison"])
    outcome["successor_advisory_comparison"] = copy.deepcopy(records["successor_comparison"])
    outcome["candidate_bridge"] = copy.deepcopy(records["bridge"])
    repin(case, "outcome")


def mutate_stage(case: dict[str, Any], name: str) -> None:
    """Corrupt copies only, rebind unsigned descriptors; signatures are never issued."""
    records = case["records"]
    if name.startswith("outcome:"):
        field = name.split(":")[1]
        records["outcome"][field] = (
            [] if field in {"training_measurements", "continuations"} else "sha256:" + "0" * 64
        )
        repin(case, "outcome")
    elif name.startswith("frozen:"):
        _, label, field = name.split(":")
        binding = records["preview_" + label]["feature_context"]
        if field == "checkpoint_descriptor":
            artifact = binding["artifacts"]["checkpoint"]
            artifact["sha256"] = "0" * 64
            artifact["blob_cid"] = cid(
                {key: value for key, value in artifact.items() if key != "blob_cid"}
            )
        else:
            binding[field] = copy.deepcopy(FROZEN_CORRUPTIONS[field])
        rebind_preview(case, label)
    elif name.startswith("off:"):
        label = name.split(":")[1]
        records["preview_" + label]["feature_context"] |= {
            "mode": "train",
            "model_enabled": True,
            "actual_training_delta": 999,
        }
        rebind_preview(case, label)
    elif name in {"correlated_bridge_task", "correlated_bridge_revision"}:
        bridge, desc, handoff = (records[key] for key in ("bridge", "descriptor", "handoff"))
        key, value = (
            ("task_cid", records["before"]["graph"]["tasks"][1]["content_id"])
            if name.endswith("task")
            else ("task_revision", 2)
        )
        for row in (bridge, desc, handoff):
            row[key] = value
        handoff["candidate_cid"] = cid(
            {key: value for key, value in handoff.items() if key != "candidate_cid"}
        )
        repin(case, "handoff")
        desc["candidate_cid"] = handoff["candidate_cid"]
        desc["sha256"] = case["pins"]["handoff"]["sha256"]
        bridge["public_candidate_descriptor"] = copy.deepcopy(desc)
        bridge["public_candidate_pin"] |= {
            key: case["pins"]["handoff"][key] for key in ("sha256", "bytes")
        }
        generated = records["generated"]
        if key == "task_cid":
            generated[key] = value
        generated["result_cid"] = cid(
            {key: value for key, value in generated.items() if key != "result_cid"}
        )
        repin(case, "generated")
        bridge["generated_result_cid"] = generated["result_cid"]
        bridge["generated_result_pin"] |= {
            key: case["pins"]["generated"][key] for key in ("sha256", "bytes")
        }
        records["scope"]["payload"]["candidate"]["descriptor"] = copy.deepcopy(desc)
        records["outcome"]["execution_scope_after_stop"] = copy.deepcopy(records["scope"])
        records["outcome"]["candidate_bridge"] = copy.deepcopy(bridge)
        for role in ("descriptor", "bridge", "scope", "outcome"):
            repin(case, role)
    elif name == "correlated_lifecycle_stop":
        for row in (records["lifecycle"], records["outcome"]):
            row["stop"]["data"]["old_tree_fenced"] = False
        repin(case, "lifecycle")
        repin(case, "outcome")
    elif name == "correlated_boolean_fence":
        for row in (records["lifecycle"], records["outcome"]):
            completed = row["task"]["body"]["completion_receipt"]
            completed["fencing_token"] = True
            transition = completed["validation"]["accepted_source_transition"]
            transition["database_attempt_binding"]["fencing_token"] = True
            transition["transition_cid"] = (
                "sha256:"
                + hashlib.sha256(
                    canonical(
                        {key: value for key, value in transition.items() if key != "transition_cid"}
                    )
                ).hexdigest()
            )
        repin(case, "lifecycle")
        repin(case, "outcome")
    elif name == "correlated_advisory_meaning":
        comparison = records["initial_comparison"]
        comparison["projection"]["observations"][0]["output"] = 99
        for label in ("initial-off", "root-frozen", "initial-child-frozen"):
            records["preview_" + label]["match"]["observation"]["observations"][0]["output"] = 99
            records["preview_" + label]["result_cid"] = cid(
                {
                    key: value
                    for key, value in records["preview_" + label].items()
                    if key != "result_cid"
                }
            )
            repin(case, "preview_" + label)
        comparison["preview_records"] = [
            {
                "label": label,
                "result_cid": records["preview_" + label]["result_cid"],
                "feature_context_cid": records["preview_" + label]["feature_context"][
                    "context_cid"
                ],
            }
            for label in ("initial-off", "root-frozen", "initial-child-frozen")
        ]
        repin(case, "initial_comparison")
        records["bridge"]["advisory_comparison_pin"] |= {
            key: case["pins"]["initial_comparison"][key] for key in ("sha256", "bytes")
        }
        repin(case, "bridge")
        records["outcome"]["initial_advisory_comparison"] = copy.deepcopy(comparison)
        records["outcome"]["candidate_bridge"] = copy.deepcopy(records["bridge"])
        repin(case, "outcome")
    elif name == "missing_advisory_field":
        records["initial_comparison"]["compared_fields"].pop()
    elif name == "missing_cold_field":
        records["cold_comparison"]["compared_fields"].pop()
    elif name == "cold_false_agreement":
        records["cold_comparison"]["agreement"] = False
    elif name == "correlated_foreign_publication":
        transition = records["lifecycle"]["task"]["body"]["completion_receipt"]["validation"][
            "accepted_source_transition"
        ]
        transition["merge_commit"] = "e" * 40
        records["outcome"]["task"] = copy.deepcopy(records["lifecycle"]["task"])
        records["outcome"]["published_commit"] = "e" * 40
        repin(case, "lifecycle")
        repin(case, "outcome")
    elif name == "drop_original_native_task":
        records["before"]["graph"]["tasks"].pop()
    elif name == "grant_advisory_authority":
        records["initial_comparison"]["execution_authority"] = True
    elif name == "grant_held_scope_completion":
        records["scope"]["payload"]["completion_authority"] = True
    elif name == "claim_automatic_cleanup":
        records["cleanup"][0]["scope"] = "automatic completion recovery"
    else:
        raise ValueError("unrecognized authored control")


STAGE_CONTROLS = (
    (
        "correlated_bridge_task",
        "correlated_bridge_revision",
        "correlated_lifecycle_stop",
        "correlated_boolean_fence",
        "correlated_advisory_meaning",
        "missing_advisory_field",
        "missing_cold_field",
        "cold_false_agreement",
        "correlated_foreign_publication",
        "drop_original_native_task",
        "grant_advisory_authority",
        "grant_held_scope_completion",
        "claim_automatic_cleanup",
    )
    + tuple(
        "outcome:" + field
        for field in (
            "selected_initial_model_version_id",
            "selected_successor_model_version_id",
            "training_measurements",
            "continuations",
        )
    )
    + tuple(
        f"frozen:{label}:{field}"
        for label in ("root-frozen", "initial-child-frozen", "successor-frozen")
        for field in FROZEN_CORRUPTIONS
    )
    + ("off:initial-off", "off:successor-off")
)


def structural_controls(cases: dict[str, Any]) -> list[dict[str, Any]]:
    controls = []
    view = stage_case(cases["06"])
    for name in STAGE_CONTROLS:
        corrupted = copy.deepcopy(view)
        mutate_stage(corrupted, name)
        try:
            assert_stages(corrupted, "06")
        except (ValueError, KeyError, TypeError, AdmissionEvidenceError) as error:
            controls.append(
                {
                    "name": name,
                    "refused": True,
                    "error": str(error),
                    "scope": "inert structural copy; no signatures authenticated or rewritten",
                }
            )
        else:
            raise AdmissionEvidenceError("authored corruption was accepted: " + name)
    corrupted = copy.deepcopy(cases["06"])
    records = corrupted["records"]
    records["epochs"]["attempts"][0]["actual_attempted_epochs"] = 17
    records["epochs"]["known_actual_attempted_epochs"] = 49
    binding = records["train0_context"]
    binding["actual_training_delta"] = 17
    binding["context_cid"] = cid(
        {key: value for key, value in binding.items() if key != "context_cid"}
    )
    records["epochs"]["attempts"][0]["context_cid"] = binding["context_cid"]
    records["measurements"]["measurements"][0] |= {
        "attempted_epochs": 17,
        "context_cid": binding["context_cid"],
    }
    repin(corrupted, "train0_context")
    repin(corrupted, "epochs")
    repin(corrupted, "measurements")
    try:
        assert_training(corrupted, "06")
    except (ValueError, KeyError, TypeError, AdmissionEvidenceError) as error:
        controls.append(
            {
                "name": "correlated_returned_epochs",
                "refused": True,
                "error": str(error),
                "scope": "context CID, raw pins and ledger regenerated; actual selected checkpoint return remains independent",
            }
        )
    else:
        raise AdmissionEvidenceError("correlated returned epoch corruption was accepted")
    return controls


def run(manifest: Path, output: Path) -> dict[str, Any]:
    reader = PinnedReader()
    # Permission to write a fresh output is established before the catch which
    # emits refusal reports. A rejected output can never receive such a report.
    manifest, output = manifest.absolute(), output.absolute()
    need(
        not output.exists()
        and output.resolve(strict=False) == output
        and not any(part.is_symlink() for part in (output, *output.parents)),
        "fresh canonical output required",
    )
    raw = reader.read(manifest, manifest=True)
    spec = parse_document(raw)
    validate_manifest(spec)
    need(
        not any(output.is_relative_to(Path(case["root"])) for case in spec["attempts"])
        and not manifest.is_relative_to(output),
        "fresh output outside retained input roots required",
    )
    output.mkdir(parents=True, exist_ok=False)
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "refused",
        "manifest_sha256": None,
        "started_at": datetime.now(UTC).isoformat(),
        "native_execution_performed": False,
        "training_executed": False,
        "current_authority_claimed": False,
        "full_join_qualified": False,
        "signature_authentication_performed": False,
        "git_object_verification_performed": False,
        "frozen_auxiliary_artifact_bodies_verified": False,
        "owner_database_opened": False,
        "profile_keys_read": False,
        "input_files_unchanged": False,
        "bounds": {
            "files": MAX_FILES,
            "file_bytes": MAX_FILE_BYTES,
            "total_bytes": MAX_TOTAL_BYTES,
            "manifest_bytes": MAX_MANIFEST_BYTES,
            "observation_seconds": MAX_OBSERVATION_SECONDS,
        },
        "limitations": [
            "Selected retained structural records and byte identities only; no signature authentication, current owner verification, numerical replay or process-origin attestation.",
            "The other owner's complete archive qualification remains a separate claim; full_join_qualified is false for this audit.",
            "Wrapper timing excludes source copying, deployment setup, image inspection and scheduler setup; no complete invocation latency or speedup claim.",
            "Publication is a cross-record JSON/source-baseline join; this workflow does not verify Git object bodies.",
            "Frozen checkpoint/record/lineage descriptors must equal independently pinned training artifacts; frozen-only invocation/inference/metrics descriptors are checked structurally, and their separate bodies are not selected or verified.",
        ],
    }
    try:
        report["manifest_sha256"] = hashlib.sha256(raw).hexdigest()
        cases = load_inputs(spec, reader)
        report.update(assert_attempts(cases))
        controls = structural_controls(cases)
        report |= {
            "controls": controls,
            "controls_count": len(controls),
            "controls_refused": sum(row["refused"] for row in controls),
            "controls_scope": "authored inert dictionary mutations with regenerated selected unsigned pins/CIDs; no new execution or authentication",
        }
        report["input_files_unchanged"] = reader.recheck()
        report["status"] = "passed"
    except (
        ValueError,
        OSError,
        KeyError,
        TypeError,
        RecursionError,
        OverflowError,
        AdmissionEvidenceError,
    ) as error:
        report["error"] = type(error).__name__ + ": " + str(error)
    report["selected_input_pins"] = reader.pins
    report["read_file_count"] = len(reader.pins)
    report["read_bytes"] = reader.total
    report["finished_at"] = datetime.now(UTC).isoformat()
    (output / "advisory_evidence.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = run(args.manifest, args.output)
    except (
        ValueError,
        OSError,
        KeyError,
        TypeError,
        RecursionError,
        AdmissionEvidenceError,
    ) as error:
        print(
            json.dumps(
                {
                    "status": "refused",
                    "report": None,
                    "error": type(error).__name__ + ": " + str(error),
                    "native_execution_performed": False,
                    "full_join_qualified": False,
                },
                sort_keys=True,
            )
        )
        return 3
    print(
        json.dumps(
            {
                "status": report["status"],
                "report": str(args.output / "advisory_evidence.json"),
                "native_execution_performed": False,
                "full_join_qualified": False,
            },
            sort_keys=True,
        )
    )
    return 0 if report["status"] == "passed" else 3


if __name__ == "__main__":
    raise SystemExit(main())
