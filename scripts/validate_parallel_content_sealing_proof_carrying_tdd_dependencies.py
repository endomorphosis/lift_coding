#!/usr/bin/env python3
"""Verify the PCTDD dependency/source seal against the current checkout.

The validator is deliberately read-only: it never installs extensions,
keys, or packages.  Optional theorem provers are discovered through the
ipfs_datasets_py lazy installer (managed bin + already-installed PATH) without
downloading.  Missing optional proof capabilities may be sealed as typed
unavailable records; a record marked required or production-admitted fails
closed when it cannot be reproduced exactly.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import platform
import re
import subprocess
import sys
from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SEAL_PATH = ROOT / "config/parallel_content_sealing_proof_carrying_tdd_dependencies.seal.json"
SCHEDULER_PATH = ROOT / "config/agent_supervisor_parallel_content_sealing_proof_carrying_tdd_scheduler.json"
NAMESPACE = "parallel-content-sealing-proof-carrying-tdd-v1"
PLAN_REVISION = "PCTDD-PLAN-V1.1"
CONTROL_MANIFEST_RELATIVE = (
    "config/parallel_content_sealing_proof_carrying_tdd_control_manifest.json"
)
DEPENDENCY_SEAL_RELATIVE = (
    "config/parallel_content_sealing_proof_carrying_tdd_dependencies.seal.json"
)
G5_MIGRATION_RELATIVE = (
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/g5_migration_inventory.json"
)
G6_SOURCE_MIGRATION_RELATIVE = (
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/g6_source_migration_inventory.json"
)
G7_PROVIDER_ROUTE_MIGRATION_RELATIVE = (
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/"
    "g7_provider_route_migration_inventory.json"
)
G8_TO_G9_DESCENDANT_SOURCE_MIGRATION_RELATIVE = (
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/"
    "g8_to_g9_descendant_source_inventory.json"
)
G8_RESOLVED_GUARDRAIL_ARCHIVE_RELATIVE = (
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/"
    "g8_resolved_guardrail_archive.json"
)
OPERATOR_CONTROL_RECEIPT_RELATIVE = (
    "artifacts/parallel_content_sealing_proof_carrying_tdd/receipts/PCTDD-000.json"
)
G8_PROVIDER_ROUTE_MODULE_RELATIVE = "scripts/pctdd_g8_provider_route_successor.py"
G9_DESCENDANT_SOURCE_MODULE_RELATIVE = "scripts/pctdd_g9_descendant_source_successor.py"
G7_CONTROL_SOURCE_ANCHOR_HEAD = "85aa9bad12e04e97537c4dcbad2eb89941eaa431"
G7_CONTROL_SOURCE_ANCHOR_TREE = "5907232e5768dab9d8483c37720165e6b40193ff"
G7_RUNTIME_ROOT = (
    "data/agent_supervisor/parallel_content_sealing_proof_carrying_tdd_v1_g7"
)
G8_RUNTIME_ROOT = (
    "data/agent_supervisor/parallel_content_sealing_proof_carrying_tdd_v1_g8"
)
G9_RUNTIME_ROOT = (
    "data/agent_supervisor/parallel_content_sealing_proof_carrying_tdd_v1_g9"
)
G9_CONTROL_SOURCE_ANCHOR_HEAD = "3be981e55320fba49c4b8395086cea65c8ac571e"
G9_CONTROL_SOURCE_ANCHOR_TREE = "74e3f2aa0f738b442fbc275a78039223fb11ec34"
EXPECTED_PROVIDER_ROUTE = {
    "primary_provider_id": "grok_cli",
    "primary_model_id": "grok-4.6",
    "fallback_provider_id": "codex",
    "fallback_model_id": "gpt-5.6-terra",
    "fallback_trigger": "primary_quota_exhausted",
    "fallback_reasoning_effort": "medium",
    "implementation_fallback_authorized": True,
}
EXPECTED_SOURCE_MIGRATION_CONTROL_PATHS = {
    "artifacts/parallel_content_sealing_proof_carrying_tdd/receipts/PCTDD-000.json",
    "config/agent_supervisor_parallel_content_sealing_proof_carrying_tdd_scheduler.json",
    "config/parallel_content_sealing_proof_carrying_tdd_control_manifest.json",
    "config/parallel_content_sealing_proof_carrying_tdd_dependencies.seal.json",
    "docs/architecture/PARALLEL_CONTENT_SEALING_PROOF_CARRYING_TDD_PLAN.md",
    G6_SOURCE_MIGRATION_RELATIVE,
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/repository_baseline.json",
    "external/ipfs_accelerate",
    "scripts/generate_parallel_content_sealing_proof_carrying_tdd_controls.py",
    "scripts/materialize_parallel_content_sealing_proof_carrying_tdd_program.py",
    "scripts/ops/agent_supervisor/parallel_content_sealing_proof_carrying_tdd.py",
    "scripts/pctdd_g7_source_binding_successor.py",
    "scripts/validate_parallel_content_sealing_proof_carrying_tdd_board.py",
    "scripts/validate_parallel_content_sealing_proof_carrying_tdd_dependencies.py",
    "test/api/parallel_content_sealing/test_pctdd_g6_control_amendment.py",
    "test/api/parallel_content_sealing/test_pctdd_g7_source_binding_successor.py",
    "test/api/parallel_content_sealing/test_pctdd_quack_lifecycle_wrapper.py",
}
EXPECTED_PROVIDER_ROUTE_MIGRATION_CONTROL_PATHS = {
    OPERATOR_CONTROL_RECEIPT_RELATIVE,
    "config/agent_supervisor_parallel_content_sealing_proof_carrying_tdd_scheduler.json",
    "config/parallel_content_sealing_proof_carrying_tdd_control_manifest.json",
    "config/parallel_content_sealing_proof_carrying_tdd_dependencies.seal.json",
    "docs/architecture/PARALLEL_CONTENT_SEALING_PROOF_CARRYING_TDD_PLAN.md",
    G7_PROVIDER_ROUTE_MIGRATION_RELATIVE,
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/repository_baseline.json",
    "external/ipfs_accelerate",
    "scripts/generate_parallel_content_sealing_proof_carrying_tdd_controls.py",
    "scripts/materialize_parallel_content_sealing_proof_carrying_tdd_program.py",
    G8_PROVIDER_ROUTE_MODULE_RELATIVE,
    "scripts/validate_parallel_content_sealing_proof_carrying_tdd_board.py",
    "scripts/validate_parallel_content_sealing_proof_carrying_tdd_dependencies.py",
    "test/api/parallel_content_sealing/test_pctdd_g6_control_amendment.py",
    "test/api/parallel_content_sealing/test_pctdd_g8_provider_route_successor.py",
}

REQUIRED_HASHED_ARTIFACTS = {
    "docs/architecture/PARALLEL_CONTENT_SEALING_PROOF_CARRYING_TDD_PLAN.md",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd.objectives.md",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd.todo.md",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/repository_baseline.json",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/authority_matrix.json",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/overlap_gap_matrix.json",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/hash_identity_inventory.json",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/hashing_critical_path.json",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/pytest_identity_inventory.json",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/fixture_adapter_inventory.json",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/proof_claim_matrix.json",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/zkp_backend_inventory.json",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/storage_recovery_inventory.json",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/benchmark_preregistration.json",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/g5_migration_inventory.json",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/g6_source_migration_inventory.json",
    G7_PROVIDER_ROUTE_MIGRATION_RELATIVE,
    G8_RESOLVED_GUARDRAIL_ARCHIVE_RELATIVE,
    G8_TO_G9_DESCENDANT_SOURCE_MIGRATION_RELATIVE,
    "config/agent_supervisor_parallel_content_sealing_proof_carrying_tdd_scheduler.json",
    "config/parallel_content_sealing_proof_carrying_tdd_benchmark.json",
    "config/parallel_content_sealing_proof_carrying_tdd_validation_profiles.json",
    "config/parallel_content_sealing_proof_carrying_tdd_control_manifest.json",
    "artifacts/parallel_content_sealing_proof_carrying_tdd/receipts/PCTDD-000.json",
    "scripts/generate_parallel_content_sealing_proof_carrying_tdd_controls.py",
    "scripts/run_parallel_content_sealing_proof_carrying_tdd_validation.py",
    "scripts/validate_parallel_content_sealing_proof_carrying_tdd_dependencies.py",
    "scripts/validate_parallel_content_sealing_proof_carrying_tdd_board.py",
    "scripts/materialize_parallel_content_sealing_proof_carrying_tdd_program.py",
    "scripts/ops/agent_supervisor/parallel_content_sealing_proof_carrying_tdd.py",
    "scripts/pctdd_g7_source_binding_successor.py",
    G8_PROVIDER_ROUTE_MODULE_RELATIVE,
    G9_DESCENDANT_SOURCE_MODULE_RELATIVE,
    "test/api/parallel_content_sealing/test_pctdd_g6_control_amendment.py",
    "test/api/parallel_content_sealing/test_pctdd_g7_source_binding_successor.py",
    "test/api/parallel_content_sealing/test_pctdd_g8_provider_route_successor.py",
    "test/api/parallel_content_sealing/test_pctdd_g9_descendant_source_successor.py",
    "test/api/parallel_content_sealing/test_pctdd_g9_orphan_recovery_regressions.py",
    "test/api/parallel_content_sealing/test_pctdd_quack_lifecycle_wrapper.py",
}

SOURCE_PATHS = {
    "ipfs_accelerate_py": "external/ipfs_accelerate",
    "ipfs_datasets_py": "external/ipfs_datasets",
    "ipfs_kit_py": "external/ipfs_kit",
}
FROZEN_G5_RESCUE_BRANCH_PREFIX_COUNTS = {
    "refs/heads/rescue/pctdd-001-3c1c70df54d4-": 7,
    "refs/heads/rescue/pctdd-002-28ace0eab61e-": 7,
    "refs/heads/rescue/pctdd-003-783b342df728-": 8,
    "refs/heads/rescue/pctdd-004-1f308616e139-": 7,
}


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def _normalize_sha256(value: Any) -> str:
    text = str(value or "").strip().lower()
    if re.fullmatch(r"[0-9a-f]{64}", text):
        return "sha256:" + text
    if re.fullmatch(r"sha256:[0-9a-f]{64}", text):
        return text
    return ""


def _git(*args: str, cwd: Path = ROOT) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def _version(distribution: str) -> str:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return ""


def _walk_dicts(value: Any) -> Iterator[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_dicts(child)


def _deep_value(value: Any, names: Iterable[str]) -> Any:
    wanted = {name.lower() for name in names}
    for record in _walk_dicts(value):
        for key, child in record.items():
            if str(key).lower() in wanted:
                return child
    return None


def _named_record(value: Any, names: Iterable[str]) -> Mapping[str, Any] | None:
    wanted = {name.lower().replace("-", "_") for name in names}
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            if normalized in wanted and isinstance(child, Mapping):
                return child
        for record in _walk_dicts(value):
            label = str(
                record.get("name") or record.get("id") or record.get("capability")
                or record.get("tool") or record.get("extension_name") or ""
            ).lower().replace("-", "_")
            if label in wanted:
                return record
    return None


def _artifact_records(seal: Mapping[str, Any]) -> list[tuple[str, str]]:
    sections: list[Any] = []
    for name in ("artifacts", "control_artifacts", "sealed_artifacts", "files", "artifact_hashes"):
        if name in seal:
            sections.append(seal[name])
    records: list[tuple[str, str]] = []
    for section in sections:
        if isinstance(section, Mapping):
            for key, value in section.items():
                if isinstance(value, str):
                    records.append((str(key), value))
                elif isinstance(value, Mapping):
                    records.append((
                        str(value.get("path") or value.get("relative_path") or key),
                        str(value.get("sha256") or value.get("byte_sha256") or value.get("digest") or ""),
                    ))
        elif isinstance(section, list):
            for value in section:
                if not isinstance(value, Mapping):
                    continue
                records.append((
                    str(value.get("path") or value.get("relative_path") or ""),
                    str(value.get("sha256") or value.get("byte_sha256") or value.get("digest") or ""),
                ))
    return records


def _source_records(seal: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    result: list[Mapping[str, Any]] = []
    for name in ("sources", "repositories", "source_bindings", "authorities"):
        section = seal.get(name)
        if isinstance(section, list):
            result.extend(item for item in section if isinstance(item, Mapping))
        elif isinstance(section, Mapping):
            for key, value in section.items():
                if isinstance(value, Mapping):
                    merged = dict(value)
                    merged.setdefault("name", str(key))
                    result.append(merged)
    source = seal.get("source_binding")
    if isinstance(source, Mapping):
        nested = source.get("repositories") or source.get("sources")
        if isinstance(nested, Mapping):
            for key, value in nested.items():
                if isinstance(value, Mapping):
                    merged = dict(value)
                    merged.setdefault("name", str(key))
                    result.append(merged)
        elif isinstance(nested, list):
            result.extend(item for item in nested if isinstance(item, Mapping))
    return result


def _record_bool(record: Mapping[str, Any], *names: str) -> bool | None:
    for name in names:
        if name not in record:
            continue
        value = record[name]
        if isinstance(value, bool):
            return value
        if str(value).strip().lower() in {"true", "yes", "1", "available", "loaded"}:
            return True
        if str(value).strip().lower() in {"false", "no", "0", "unavailable", "missing"}:
            return False
    return None


def _safe_path(relative: str) -> Path | None:
    if not relative or Path(relative).is_absolute():
        return None
    resolved = (ROOT / relative).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        return None
    return resolved


def _sealed_extension_directory(
    name: str,
    record: Mapping[str, Any] | None,
    errors: list[str],
) -> str:
    """Verify and return the exact preinstalled extension directory binding."""

    if record is None or _record_bool(record, "available", "loaded") is not True:
        return ""
    raw_directory = str(record.get("extension_directory") or "").strip()
    raw_install_path = str(record.get("install_path") or "").strip()
    expected_sha256 = _normalize_sha256(record.get("install_sha256") or "")
    if not raw_directory or not raw_install_path or not expected_sha256:
        errors.append(
            f"{name} available capability omits sealed extension directory, path, or SHA-256"
        )
        return ""
    directory = Path(raw_directory)
    install_path = Path(raw_install_path)
    if not directory.is_absolute() or not install_path.is_absolute():
        errors.append(f"{name} sealed extension paths must be absolute")
        return ""
    try:
        resolved_directory = directory.resolve(strict=True)
        resolved_install_path = install_path.resolve(strict=True)
        resolved_install_path.relative_to(resolved_directory)
    except (OSError, ValueError) as exc:
        errors.append(f"{name} sealed extension path is unavailable or escapes its directory: {exc}")
        return ""
    if not resolved_directory.is_dir() or not resolved_install_path.is_file():
        errors.append(f"{name} sealed extension binding is not a directory/file pair")
        return ""
    if resolved_install_path.name != f"{name}.duckdb_extension":
        errors.append(f"{name} sealed extension filename is not canonical")
        return ""
    actual_sha256 = _sha256_file(resolved_install_path)
    if actual_sha256 != expected_sha256:
        errors.append(
            f"{name} extension bytes differ: sealed={expected_sha256}, actual={actual_sha256}"
        )
        return ""
    return str(resolved_directory)


def _extension_state(name: str, *, extension_directory: str = "") -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": name,
        "available": False,
        "loaded": False,
        "version": "",
        "error": "",
    }
    try:
        import duckdb  # imported only during explicit validation

        config = {
            "autoinstall_known_extensions": "false",
            "autoload_known_extensions": "false",
        }
        if extension_directory:
            config["extension_directory"] = extension_directory
        connection = duckdb.connect(":memory:", config=config)
        try:
            connection.execute(f"LOAD {name}")
            result["loaded"] = True
            row = connection.execute(
                "SELECT extension_version, installed, loaded, install_mode, installed_from, "
                "install_path "
                "FROM duckdb_extensions() WHERE extension_name = ?",
                [name],
            ).fetchone()
            if row:
                result.update({
                    "version": str(row[0] or ""),
                    "available": bool(row[1]),
                    "loaded": bool(row[2]),
                    "install_mode": str(row[3] or ""),
                    "installed_from": str(row[4] or ""),
                    "install_path": str(row[5] or ""),
                })
                install_path = Path(str(row[5] or ""))
                if install_path.is_file():
                    result["install_sha256"] = _sha256_file(install_path)
            else:
                result["available"] = result["loaded"]
        finally:
            connection.close()
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def _command_state(name: str, argv: tuple[str, ...]) -> dict[str, Any]:
    generator_path = ROOT / "scripts/generate_parallel_content_sealing_proof_carrying_tdd_controls.py"
    spec = importlib.util.spec_from_file_location(
        "pctdd_controls_theorem_provers",
        generator_path,
    )
    if spec is None or spec.loader is None:
        return {
            "name": name,
            "command": argv[0],
            "available": False,
            "executable": "",
            "version": "",
            "error": "PCTDD control generator is unavailable",
        }
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    probed = module.probe_managed_theorem_prover(name, argv, install=False)
    return {
        "name": name,
        "command": argv[0],
        "available": bool(probed.get("available")),
        "executable": str(probed.get("install_path") or ""),
        "install_path": str(probed.get("install_path") or ""),
        "version": str(probed.get("version") or ""),
        "error": str(probed.get("error") or ""),
        "loaded": True,
    }


def _verify_capability_record(
    name: str,
    record: Mapping[str, Any] | None,
    actual: Mapping[str, Any],
    errors: list[str],
    warnings: list[str],
) -> None:
    if record is None:
        errors.append(f"dependency seal omits capability record {name}")
        return
    observed = _record_bool(record, "available", "load_ok", "loaded", "operational")
    actual_available = bool(actual.get("available") and actual.get("loaded", True))
    required = _record_bool(record, "required", "required_for_launch", "mandatory") is True
    if observed is None:
        errors.append(f"{name} capability record omits explicit availability")
    elif observed != actual_available:
        provisioning = str(
            record.get("provisioning") or record.get("installer_authority") or ""
        ).lower()
        optional_lazy_promotion = (
            not required
            and not observed
            and actual_available
            and "ipfs_datasets" in provisioning
        )
        if optional_lazy_promotion:
            warnings.append(
                f"{name} was sealed unavailable and is now provided by the "
                "ipfs_datasets_py lazy installer"
            )
        else:
            errors.append(
                f"{name} availability differs: sealed={observed}, "
                f"actual={actual_available}"
            )
    sealed_version = str(record.get("version") or record.get("extension_version") or "").strip()
    actual_version = str(actual.get("version") or "").strip()
    if observed and not sealed_version:
        errors.append(f"{name} available capability omits exact version")
    elif sealed_version and actual_version and sealed_version not in actual_version and actual_version not in sealed_version:
        errors.append(f"{name} version differs: sealed={sealed_version!r}, actual={actual_version!r}")
    for field in ("install_path", "install_sha256"):
        sealed_value = str(record.get(field) or "").strip()
        actual_value = str(actual.get(field) or "").strip()
        if observed and sealed_value != actual_value:
            errors.append(
                f"{name} {field} differs: sealed={sealed_value!r}, actual={actual_value!r}"
            )
    if required and not actual.get("available"):
        errors.append(f"required capability {name} is unavailable: {actual.get('error', '')}")
    elif not actual.get("available"):
        warnings.append(f"typed optional capability unavailable: {name}: {actual.get('error', '')}")


def _gitlink(relative: str) -> str:
    row = _git("ls-tree", "HEAD", "--", relative).split()
    if len(row) < 3 or row[0] != "160000":
        return ""
    return row[2]


def _validate_artifacts(seal: Mapping[str, Any], errors: list[str]) -> dict[str, str]:
    records = _artifact_records(seal)
    if not records:
        errors.append("dependency seal contains no artifact hash records")
        return {}
    expected_by_path: dict[str, str] = {}
    for relative, claimed in records:
        if relative in expected_by_path:
            errors.append(f"duplicate sealed artifact path: {relative}")
            continue
        digest = _normalize_sha256(claimed)
        if not digest:
            errors.append(f"invalid SHA-256 for sealed artifact {relative}")
            continue
        path = _safe_path(relative)
        if path is None:
            errors.append(f"sealed artifact escapes repository: {relative}")
            continue
        expected_by_path[relative] = digest
        if not path.is_file():
            errors.append(f"sealed artifact missing: {relative}")
            continue
        actual = _sha256_file(path)
        if actual != digest:
            errors.append(f"sealed artifact hash differs for {relative}: {actual} != {digest}")
        if path.suffix == ".json":
            try:
                _load_json(path)
            except Exception as exc:
                errors.append(f"sealed JSON artifact rejected for {relative}: {type(exc).__name__}: {exc}")
    missing = sorted(REQUIRED_HASHED_ARTIFACTS - set(expected_by_path))
    if missing:
        errors.append("dependency seal omits protected artifact hashes: " + ", ".join(missing))
    return expected_by_path


def _validate_sources(seal: Mapping[str, Any], errors: list[str]) -> dict[str, Any]:
    records = _source_records(seal)
    by_path: dict[str, Mapping[str, Any]] = {}
    for record in records:
        relative = str(record.get("path") or record.get("relative_path") or record.get("root") or "").rstrip("/")
        if relative:
            if relative in by_path:
                errors.append(f"duplicate source binding for {relative}")
            by_path[relative] = record
    result: dict[str, Any] = {}
    for name, relative in SOURCE_PATHS.items():
        record = by_path.get(relative)
        if record is None:
            errors.append(f"source seal omits {name} at {relative}")
            continue
        path = ROOT / relative
        if not path.is_dir():
            errors.append(f"source repository missing: {relative}")
            continue
        actual_head = _git("rev-parse", "HEAD", cwd=path)
        actual_tree = _git("rev-parse", "HEAD^{tree}", cwd=path)
        actual_gitlink = _gitlink(relative)
        sealed_head = str(record.get("head") or record.get("commit") or record.get("revision") or "")
        sealed_tree = str(record.get("tree") or record.get("tree_oid") or "")
        sealed_gitlink = str(record.get("gitlink") or record.get("gitlink_oid") or sealed_head)
        if not sealed_head or sealed_head != actual_head:
            errors.append(f"{name} HEAD differs: sealed={sealed_head!r}, actual={actual_head!r}")
        if not sealed_tree or sealed_tree != actual_tree:
            errors.append(f"{name} tree differs: sealed={sealed_tree!r}, actual={actual_tree!r}")
        if not actual_gitlink or sealed_gitlink != actual_gitlink or actual_gitlink != actual_head:
            errors.append(
                f"{name} gitlink/head binding differs: sealed={sealed_gitlink!r}, "
                f"gitlink={actual_gitlink!r}, head={actual_head!r}"
            )
        dirty = _git("status", "--porcelain=v1", "--untracked-files=all", cwd=path)
        if dirty:
            errors.append(f"governed source repository is dirty: {relative}")
        if record.get("dirty") is not False:
            errors.append(f"{name} seal does not assert an actually clean source")
        if record.get("gitlink_matches_nested_head") is not True:
            errors.append(f"{name} seal does not assert exact gitlink/head equality")
        status_digest = "sha256:" + hashlib.sha256(dirty.encode("utf-8")).hexdigest()
        if record.get("status_sha256") != status_digest:
            errors.append(f"{name} sealed status digest differs")
        origin = str(record.get("origin") or record.get("origin_url") or "")
        if origin:
            actual_origin = _git("remote", "get-url", "origin", cwd=path)
            if actual_origin.rstrip("/") != origin.rstrip("/"):
                errors.append(f"{name} origin differs")
        result[name] = {
            "path": relative,
            "head": actual_head,
            "tree": actual_tree,
            "gitlink": actual_gitlink,
            "dirty": bool(dirty),
        }
    return result


def _validate_proof_admission(seal: Mapping[str, Any], errors: list[str]) -> None:
    bad_classes = {"simulated", "simulation", "mock", "structural", "integrity_only", "research_only"}
    for record in _walk_dicts(seal):
        classification = str(
            record.get("classification") or record.get("proof_class")
            or record.get("evidence_class") or record.get("backend_type") or ""
        ).strip().lower()
        admitted = _record_bool(
            record, "production_admitted", "admitted_for_production", "production",
            "authoritative", "accepted_as_real_proof",
        )
        if classification in bad_classes and admitted is True:
            errors.append(f"non-production proof class promoted as production: {classification}")
        if admitted is True and classification in {"zk", "zero_knowledge", "real_proving", "direct_execution"}:
            key_policy = str(
                record.get("key_policy") or record.get("key_policy_cid")
                or record.get("verification_key_policy") or ""
            )
            if not key_policy:
                errors.append(f"production proof admission lacks verifier-selected key policy: {classification}")


def _validate_g6_source_migration(
    inventory: Any,
    *,
    errors: list[str],
) -> Mapping[str, Any]:
    if not isinstance(inventory, Mapping):
        errors.append("g6 source-migration inventory is absent")
        return {}
    if (
        inventory.get("schema") != "pctdd/g6-source-binding-migration-inventory@1"
        or inventory.get("historical_plan_revision") != PLAN_REVISION
        or inventory.get("historical_task_definitions_preserved") is not True
        or inventory.get(
            "historical_completions_revalidated_for_integrity_not_reissued"
        )
        is not True
    ):
        errors.append("g6 source-migration inventory claim boundary differs")
    try:
        accepted_inventory = json.loads(
            _git(
                "show",
                f"{G7_CONTROL_SOURCE_ANCHOR_HEAD}:{G6_SOURCE_MIGRATION_RELATIVE}",
            ),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (RuntimeError, json.JSONDecodeError, ValueError) as exc:
        errors.append(
            "accepted historical g6 source-migration inventory is unavailable: "
            f"{type(exc).__name__}: {exc}"
        )
    else:
        if inventory != accepted_inventory:
            errors.append(
                "g6 source-migration inventory differs from accepted g7 history"
            )
    policy = inventory.get("source_binding_successor_materialization")
    if not isinstance(policy, Mapping):
        errors.append("g6 source-migration policy is absent")
        return {}
    expected_policy_keys = {
        "schema",
        "migration_revision",
        "prior_store_generation",
        "target_store_generation",
        "prior_runtime_root",
        "target_runtime_root",
        "target_quack_endpoint",
        "receipt_marker",
        "control_source_anchor_head",
        "control_source_anchor_tree",
        "operator_control_paths",
        "governed_gitlinks",
        "prior_control_store",
        "prior_bootstrap_receipt",
        "prior_stopped_status",
        "prior_owner_identity",
        "accepted_plan_root_cid",
        "prior_plan_revision",
        "prior_control_projection",
        "coordination_stores",
        "target_control_projection",
        "copy_policy",
    }
    if set(policy) != expected_policy_keys:
        errors.append("g6 source-migration policy is not a closed record")
    expected_identity = {
        "schema": "pctdd/source-binding-successor-materialization@1",
        "migration_revision": "PCTDD-SOURCE-G7",
        "prior_store_generation": "pctdd-v1-g6",
        "target_store_generation": "pctdd-v1-g7",
        "prior_runtime_root": "data/agent_supervisor/parallel_content_sealing_proof_carrying_tdd_v1_g6",
        "target_runtime_root": "data/agent_supervisor/parallel_content_sealing_proof_carrying_tdd_v1_g7",
        "target_quack_endpoint": "quack:127.0.0.1:27278",
        "receipt_marker": "source-migration-receipt.json",
        "control_source_anchor_head": "c8917d039e3f4598a7d29643c621e341318197da",
        "control_source_anchor_tree": "c3e061b62caa3ad0c35c7e167242694a8fec171c",
        "accepted_plan_root_cid": "baguqeeraaiqrxovjj4y3ecx6jtvzqfrrrqwuag7hl2c35i2z3eapax2nzaya",
        "prior_plan_revision": 1,
    }
    for name, expected in expected_identity.items():
        if policy.get(name) != expected:
            errors.append(f"g6 source-migration {name} differs")
    operator_paths = policy.get("operator_control_paths") or []
    if (
        set(operator_paths) != EXPECTED_SOURCE_MIGRATION_CONTROL_PATHS
        or len(operator_paths) != len(EXPECTED_SOURCE_MIGRATION_CONTROL_PATHS)
    ):
        errors.append("g6 source-migration operator path allowlist differs")
    historical_gitlinks = policy.get("governed_gitlinks")
    if (
        not isinstance(historical_gitlinks, Mapping)
        or set(historical_gitlinks) != set(SOURCE_PATHS.values())
        or any(
            re.fullmatch(r"[0-9a-f]{40}", str(value or "")) is None
            for value in historical_gitlinks.values()
        )
    ):
        errors.append("g6 source-migration governed gitlink history differs")
    coordination = policy.get("coordination_stores")
    if not isinstance(coordination, list) or [
        item.get("lane") for item in coordination if isinstance(item, Mapping)
    ] != [0, 1, 2, 3]:
        errors.append("g6 source migration must bind four ordered lane stores")
        coordination = []
    for lane, record in enumerate(coordination):
        observation = record.get("execution_observation")
        if not isinstance(observation, Mapping):
            errors.append(f"g6 lane {lane} execution observation is absent")
    settlements = {
        record.get("settlement", {}).get("task_alias")
        for record in coordination
        if isinstance(record.get("settlement"), Mapping)
    }
    if settlements != {"PCTDD-001", "PCTDD-029"}:
        errors.append("g6 source migration settlement set differs")
    if policy.get("target_control_projection") != {
        "statuses": {"completed": 14, "retrying": 3, "todo": 37},
        "task_revisions": {"PCTDD-001": 17, "PCTDD-029": 7},
        "ready_frontier": [
            "PCTDD-001",
            "PCTDD-018",
            "PCTDD-029",
            "PCTDD-031",
            "PCTDD-033",
        ],
    }:
        errors.append("g7 target control projection differs")
    # G6 is immutable predecessor history at g8.  Its accepted inventory bytes
    # above are the authority; dependency validation must not reopen a stopped
    # runtime database and accidentally turn historical state into live input.
    copy_policy = policy.get("copy_policy") or {}
    if copy_policy != {
        "copied": ["authoritative_control_store", "coordination_history"],
        "not_copied": [
            "execution_observation_stores",
            "read_replica",
            "ducklake_catalog_and_data",
            "logs",
            "worktrees",
            "merge_queue",
            "quack_owner_runtime",
            "credentials",
            "runtime_registry",
        ],
        "publication": "private_stage_hash_verify_then_no_overwrite_links_and_marker_last",
        "g6_remains_read_only_history": True,
    }:
        errors.append("g7 copy policy would promote a non-authoritative sidecar")
    return policy


def _validate_g7_provider_route_migration(
    inventory: Any,
    *,
    errors: list[str],
) -> Mapping[str, Any]:
    """Validate the sealed g7->g8 delta without opening runtime stores."""

    expected_inventory_keys = {
        "schema",
        "program_id",
        "historical_plan_revision",
        "historical_completed_task_definitions_preserved",
        "historical_completions_revalidated_for_integrity_not_reissued",
        "source_provider_route_successor_materialization",
    }
    if not isinstance(inventory, Mapping):
        errors.append("g7 provider-route migration inventory is absent")
        return {}
    if set(inventory) != expected_inventory_keys:
        errors.append("g7 provider-route migration inventory is not closed")
    if (
        inventory.get("schema")
        != "pctdd/g7-provider-route-migration-inventory@1"
        or inventory.get("program_id") != NAMESPACE
        or inventory.get("historical_plan_revision") != PLAN_REVISION
        or inventory.get("historical_completed_task_definitions_preserved")
        is not True
        or inventory.get(
            "historical_completions_revalidated_for_integrity_not_reissued"
        )
        is not True
    ):
        errors.append("g7 provider-route migration claim boundary differs")
    policy = inventory.get("source_provider_route_successor_materialization")
    if not isinstance(policy, Mapping):
        errors.append("g7 provider-route successor policy is absent")
        return {}
    expected_policy_keys = {
        "schema",
        "migration_revision",
        "prior_store_generation",
        "target_store_generation",
        "prior_runtime_root",
        "target_runtime_root",
        "target_quack_endpoint",
        "receipt_marker",
        "control_source_anchor_head",
        "control_source_anchor_tree",
        "operator_control_paths",
        "governed_gitlinks",
        "provider_route",
        "provider_route_binding_cid",
        "prior_control_store",
        "prior_generation_receipt",
        "prior_stopped_status",
        "prior_owner_identity",
        "coordination_stores",
        "prior_control_projection",
        "accepted_plan_root_cid",
        "prior_plan_revision",
        "settlements",
        "provider_role_revisions",
        "target_control_projection",
        "copy_policy",
    }
    if set(policy) != expected_policy_keys:
        errors.append("g7 provider-route successor policy is not closed")
    expected_identity = {
        "schema": "pctdd/source-provider-route-successor-materialization@1",
        "migration_revision": "PCTDD-SOURCE-PROVIDER-G8",
        "prior_store_generation": "pctdd-v1-g7",
        "target_store_generation": "pctdd-v1-g8",
        "prior_runtime_root": G7_RUNTIME_ROOT,
        "target_runtime_root": G8_RUNTIME_ROOT,
        "target_quack_endpoint": "quack:127.0.0.1:27278",
        "receipt_marker": "source-provider-route-migration-receipt.json",
        "control_source_anchor_head": G7_CONTROL_SOURCE_ANCHOR_HEAD,
        "control_source_anchor_tree": G7_CONTROL_SOURCE_ANCHOR_TREE,
    }
    for name, expected in expected_identity.items():
        if policy.get(name) != expected:
            errors.append(f"g7 provider-route migration {name} differs")
    provider = policy.get("provider_route")
    if provider != EXPECTED_PROVIDER_ROUTE:
        errors.append("g8 provider route is not the exact reviewed Grok-to-Codex route")
    operator_paths = policy.get("operator_control_paths") or []
    if (
        set(operator_paths) != EXPECTED_PROVIDER_ROUTE_MIGRATION_CONTROL_PATHS
        or len(operator_paths)
        != len(EXPECTED_PROVIDER_ROUTE_MIGRATION_CONTROL_PATHS)
    ):
        errors.append("g8 provider-route operator path allowlist differs")
    historical_gitlinks = policy.get("governed_gitlinks")
    if (
        not isinstance(historical_gitlinks, Mapping)
        or set(historical_gitlinks) != set(SOURCE_PATHS.values())
        or any(
            not re.fullmatch(r"[0-9a-f]{40}", str(value))
            for value in historical_gitlinks.values()
        )
    ):
        errors.append("g8 provider-route governed gitlinks differ")
    prior_projection = policy.get("prior_control_projection") or {}
    if (
        not isinstance(prior_projection, Mapping)
        or prior_projection.get("statuses")
        != {"blocked": 2, "completed": 14, "retrying": 1, "todo": 37}
        or prior_projection.get("event_watermark") != 192
    ):
        errors.append("stopped g7 control projection differs")
    target_projection = policy.get("target_control_projection") or {}
    if (
        not isinstance(target_projection, Mapping)
        or target_projection.get("statuses")
        != {"completed": 14, "retrying": 1, "todo": 39}
    ):
        errors.append("g8 target control projection differs")
    copy_policy = policy.get("copy_policy") or {}
    if copy_policy != {
        "copied": ["authoritative_control_store", "coordination_history"],
        "not_copied": [
            "execution_observation",
            "provider_attempt_store",
            "ducklake",
            "read_replica",
            "logs",
            "owner_runtime",
            "worktrees",
            "merge_state",
        ],
        "publication": (
            "private_stage_hash_verify_then_no_overwrite_links_and_marker_last"
        ),
        "g7_remains_read_only_history": True,
    }:
        errors.append("g8 copy policy would promote a runtime sidecar")

    module_path = ROOT / G8_PROVIDER_ROUTE_MODULE_RELATIVE
    spec = importlib.util.spec_from_file_location(
        "pctdd_g8_provider_route_successor_dependency_validation", module_path
    )
    if spec is None or spec.loader is None:
        errors.append("cannot load protected g8 provider-route successor module")
    else:
        for entry in (
            str(ROOT / "external/ipfs_accelerate"),
            str(ROOT / "scripts"),
        ):
            if entry not in sys.path:
                sys.path.insert(0, entry)
        try:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            validated_policy, route_binding = module._policy(
                {"source_provider_route_successor_materialization": policy}
            )
        except Exception as exc:
            errors.append(
                "canonical g8 provider-route policy validation failed: "
                f"{type(exc).__name__}: {exc}"
            )
        else:
            if validated_policy != dict(policy) or not route_binding:
                errors.append("canonical g8 provider-route binding differs")
    return policy


def _validate_g8_to_g9_descendant_source(
    inventory: Any,
    archive: Any,
    *,
    errors: list[str],
    warnings: list[str],
) -> Mapping[str, Any]:
    """Validate tracked g9 controls without opening the stopped g8 stores."""

    expected_inventory_keys = {
        "schema",
        "program_id",
        "capture_status",
        "migration_admitted",
        "stopped_predecessor_capture",
        "resolved_guardrail_archive",
        "historical_completed_task_definitions_preserved",
        "historical_completions_revalidated_for_integrity_not_reissued",
        "final_capture_command",
        "operator_note",
    }
    if not isinstance(inventory, Mapping) or set(inventory) != expected_inventory_keys:
        errors.append("g8-to-g9 descendant-source inventory is not closed")
        return {}
    status = inventory.get("capture_status")
    capture = inventory.get("stopped_predecessor_capture")
    if (
        inventory.get("schema") != "pctdd/g8-to-g9-descendant-source-inventory@1"
        or inventory.get("program_id") != NAMESPACE
        or inventory.get("resolved_guardrail_archive")
        != G8_RESOLVED_GUARDRAIL_ARCHIVE_RELATIVE
        or inventory.get("historical_completed_task_definitions_preserved") is not True
        or inventory.get(
            "historical_completions_revalidated_for_integrity_not_reissued"
        )
        is not True
        or inventory.get("final_capture_command")
        != "python scripts/generate_parallel_content_sealing_proof_carrying_tdd_controls.py --capture-g9-inputs"
    ):
        errors.append("g8-to-g9 descendant-source inventory claim boundary differs")
    if status == "pending_stopped_g8_capture":
        if capture is not None or inventory.get("migration_admitted") is not False:
            errors.append("pending g9 inventory contains fabricated migration evidence")
        else:
            warnings.append(
                "g9 stopped-g8 capture is pending; dependency controls validate but migration remains fail-closed"
            )
    elif status == "sealed_stopped_g8_capture":
        if not isinstance(capture, Mapping) or inventory.get("migration_admitted") is not True:
            errors.append("sealed g9 inventory lacks its stopped-g8 capture")
    else:
        errors.append("g9 descendant-source capture status is not closed")
    if (
        not isinstance(archive, Mapping)
        or archive.get("schema") != "pctdd/resolved-generated-guardrail-archive@1"
        or archive.get("canonical_active_task_ids")
        != [f"PCTDD-{index:03d}" for index in range(54)]
        or archive.get("source_board_task_ids")
        != ["PCTDD-054", "PCTDD-055", "PCTDD-056"]
        or archive.get("all_resolved") is not True
        or archive.get("g8_runtime_evidence_preserved") is not True
    ):
        errors.append("resolved generated-guardrail archive claim boundary differs")
    else:
        records = archive.get("guardrails")
        if (
            not isinstance(records, list)
            or [item.get("task_id") for item in records if isinstance(item, Mapping)]
            != ["PCTDD-054", "PCTDD-055", "PCTDD-056"]
            or any(
                not isinstance(item, Mapping)
                or item.get("status") != "completed"
                or item.get("schedulable") is not False
                or not re.fullmatch(r"[0-9a-f]{64}", str(item.get("markdown_block_sha256") or ""))
                or not re.fullmatch(r"[0-9a-f]{64}", str(item.get("discovery_sha256") or ""))
                for item in records or ()
            )
        ):
            errors.append("resolved generated-guardrail archive population differs")
    return dict(inventory)


def validate() -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if not SEAL_PATH.is_file():
        raise FileNotFoundError(SEAL_PATH.relative_to(ROOT).as_posix())
    seal = _load_json(SEAL_PATH)
    if not isinstance(seal, dict):
        raise ValueError("dependency seal must be a JSON object")
    if str(seal.get("status") or "").lower() != "sealed":
        errors.append("dependency seal status must be sealed")
    namespace = seal.get("board_namespace") or seal.get("namespace") or _deep_value(seal, ("board_namespace",))
    if namespace != NAMESPACE:
        errors.append("dependency seal board namespace differs")
    revision = seal.get("plan_revision") or _deep_value(seal, ("plan_revision",))
    if revision != PLAN_REVISION:
        errors.append("dependency seal plan revision differs")
    if seal.get("amends_plan_revision") != "PCTDD-PLAN-V1":
        errors.append("dependency seal predecessor plan revision differs")
    if seal.get("store_generation") != "pctdd-v1-g9":
        errors.append("dependency seal store generation differs")
    if seal.get("predecessor_generation") != "pctdd-v1-g8":
        errors.append("dependency seal predecessor generation differs")
    if seal.get("historical_generations") != [
        "pctdd-v1-g5",
        "pctdd-v1-g6",
        "pctdd-v1-g7",
        "pctdd-v1-g8",
    ]:
        errors.append("dependency seal historical generation chain differs")
    if seal.get("migration_inventory") != G8_TO_G9_DESCENDANT_SOURCE_MIGRATION_RELATIVE:
        errors.append("dependency seal migration inventory binding differs")
    if (
        seal.get("historical_g7_provider_route_migration_inventory")
        != G7_PROVIDER_ROUTE_MIGRATION_RELATIVE
    ):
        errors.append("dependency seal historical g7 provider-route binding differs")
    if seal.get("resolved_guardrail_archive") != G8_RESOLVED_GUARDRAIL_ARCHIVE_RELATIVE:
        errors.append("dependency seal resolved guardrail archive binding differs")
    if (
        seal.get("historical_g6_source_migration_inventory")
        != G6_SOURCE_MIGRATION_RELATIVE
    ):
        errors.append(
            "dependency seal historical g6 source-migration binding differs"
        )
    if seal.get("historical_g5_migration_inventory") != G5_MIGRATION_RELATIVE:
        errors.append("dependency seal historical g5 migration binding differs")
    source_migration_path = ROOT / str(
        seal.get("historical_g6_source_migration_inventory") or ""
    )
    source_migration = (
        _load_json(source_migration_path) if source_migration_path.is_file() else {}
    )
    provider_route_migration_path = ROOT / str(
        seal.get("historical_g7_provider_route_migration_inventory") or ""
    )
    provider_route_migration = (
        _load_json(provider_route_migration_path)
        if provider_route_migration_path.is_file()
        else {}
    )
    descendant_source_migration_path = ROOT / str(seal.get("migration_inventory") or "")
    descendant_source_migration = (
        _load_json(descendant_source_migration_path)
        if descendant_source_migration_path.is_file()
        else {}
    )
    guardrail_archive_path = ROOT / str(seal.get("resolved_guardrail_archive") or "")
    guardrail_archive = (
        _load_json(guardrail_archive_path) if guardrail_archive_path.is_file() else {}
    )
    migration_path = ROOT / str(seal.get("historical_g5_migration_inventory") or "")
    migration = _load_json(migration_path) if migration_path.is_file() else {}
    predecessor = migration.get("predecessor") if isinstance(migration, Mapping) else {}
    if not isinstance(predecessor, Mapping):
        errors.append("g5 migration predecessor record is absent")
        predecessor = {}
    for label, path_field, hash_field in (
        ("g5 database", "frozen_database_path", "frozen_database_sha256"),
        ("g5 bootstrap receipt", "bootstrap_receipt_path", "bootstrap_receipt_sha256"),
    ):
        candidate = _safe_path(str(predecessor.get(path_field) or ""))
        expected = _normalize_sha256(predecessor.get(hash_field))
        if candidate is None or not candidate.is_file():
            warnings.append(
                f"{label} is historical ignored runtime data unavailable in this isolated source worktree"
            )
        elif _sha256_file(candidate) != expected:
            errors.append(f"{label} does not match its preserved migration hash")
    candidates = migration.get("w1_rescue_candidates") if isinstance(migration, Mapping) else {}
    if not isinstance(candidates, Mapping):
        errors.append("g5 migration rescue candidates are absent")
        candidates = {}
    for task_id, outer in {
        "PCTDD-001": "e623dd43dbc8f8feb503dd8dea2a6afb4bbd26c0",
        "PCTDD-002": "25b2a4e0fd1ab354a0db5317ec8ea49ce0319a61",
        "PCTDD-003": "37ccf1a42d7bbf0a6cad0a20a7671ddc0cbffac6",
        "PCTDD-004": "2b37146f4f2f354ced02ca5327d0a7d21344f044",
    }.items():
        record = candidates.get(task_id)
        if not isinstance(record, Mapping) or record.get("outer_commit") != outer:
            errors.append(f"{task_id} migration candidate binding differs")
            continue
        if subprocess.run(
            ["git", "cat-file", "-e", f"{outer}^{{commit}}"],
            cwd=ROOT,
            capture_output=True,
            check=False,
        ).returncode != 0:
            errors.append(f"{task_id} migration commit is unavailable")
    pctdd_004 = candidates.get("PCTDD-004") if isinstance(candidates, Mapping) else {}
    component = (
        (pctdd_004.get("component_commits") or {}).get("external/ipfs_accelerate")
        if isinstance(pctdd_004, Mapping)
        else {}
    ) or {}
    if (
        component.get("commit") != "48edb688ac31bc3d05fdd5c8efd7e50ab14b755e"
        or component.get("prior_gitlink") != "cfbd381ee6196e818ecd59a438386a60b5d71bd7"
    ):
        errors.append("PCTDD-004 component-safe migration binding differs")
    nested = ROOT / "external/ipfs_accelerate"
    for commit in (
        "48edb688ac31bc3d05fdd5c8efd7e50ab14b755e",
        "cfbd381ee6196e818ecd59a438386a60b5d71bd7",
    ):
        if subprocess.run(
            ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
            cwd=nested,
            capture_output=True,
            check=False,
        ).returncode != 0:
            warnings.append(
                f"PCTDD-004 historical nested migration object unavailable in this isolated clone: {commit}"
            )
    outer_gitlink = _git(
        "ls-tree",
        "2b37146f4f2f354ced02ca5327d0a7d21344f044",
        "external/ipfs_accelerate",
    ).split()
    outer_parent_gitlink = _git(
        "ls-tree",
        "2b37146f4f2f354ced02ca5327d0a7d21344f044^",
        "external/ipfs_accelerate",
    ).split()
    if len(outer_gitlink) < 3 or outer_gitlink[2] != component.get("commit"):
        errors.append("PCTDD-004 outer rescue commit does not bind the component commit")
    if len(outer_parent_gitlink) < 3 or outer_parent_gitlink[2] != component.get("prior_gitlink"):
        errors.append("PCTDD-004 outer parent does not bind the prior component gitlink")
    rescue_refs = [
        ref
        for ref in _git(
            "for-each-ref", "--format=%(refname)", "refs/heads/rescue"
        ).splitlines()
        if ref.startswith("refs/heads/rescue/pctdd-")
    ]
    frozen_rescue_count = sum(FROZEN_G5_RESCUE_BRANCH_PREFIX_COUNTS.values())
    if frozen_rescue_count != int(
        predecessor.get("preserved_failed_validation_rescue_branch_count") or -1
    ):
        errors.append("g5 PCTDD frozen rescue-branch count binding differs")
    for prefix, expected_count in FROZEN_G5_RESCUE_BRANCH_PREFIX_COUNTS.items():
        actual_count = sum(ref.startswith(prefix) for ref in rescue_refs)
        if actual_count != expected_count:
            errors.append(
                "g5 PCTDD failed-validation rescue branch population differs "
                f"for {prefix}: expected {expected_count}, observed {actual_count}"
            )

    sealed_source_migration_policy = _validate_g6_source_migration(
        source_migration, errors=errors
    )
    sealed_provider_route_migration_policy = (
        _validate_g7_provider_route_migration(
            provider_route_migration,
            errors=errors,
        )
    )
    sealed_descendant_source_inventory = _validate_g8_to_g9_descendant_source(
        descendant_source_migration,
        guardrail_archive,
        errors=errors,
        warnings=warnings,
    )
    artifact_hashes = _validate_artifacts(seal, errors)
    control_manifest_path = ROOT / CONTROL_MANIFEST_RELATIVE
    control_manifest = (
        _load_json(control_manifest_path) if control_manifest_path.is_file() else {}
    )
    if (
        not isinstance(control_manifest, Mapping)
        or control_manifest.get("schema") != "pctdd/operator-control-manifest@1"
        or control_manifest.get("program_id") != NAMESPACE
        or control_manifest.get("plan_revision") != PLAN_REVISION
        or control_manifest.get("task_id") != "PCTDD-000"
        or control_manifest.get("historical_completion_reissued") is not False
        or control_manifest.get("historical_plan_and_task_definitions_preserved")
        is not True
        or control_manifest.get("source_binding_migration_revision")
        != "PCTDD-SOURCE-G7"
        or control_manifest.get("source_binding_migration_inventory")
        != G6_SOURCE_MIGRATION_RELATIVE
        or control_manifest.get("source_binding_migration_module")
        != "scripts/pctdd_g7_source_binding_successor.py"
        or control_manifest.get("source_provider_route_migration_revision")
        != "PCTDD-SOURCE-PROVIDER-G8"
        or control_manifest.get("source_provider_route_migration_inventory")
        != G7_PROVIDER_ROUTE_MIGRATION_RELATIVE
        or control_manifest.get("source_provider_route_migration_module")
        != G8_PROVIDER_ROUTE_MODULE_RELATIVE
        or control_manifest.get("descendant_source_migration_revision")
        != "PCTDD-DESCENDANT-SOURCE-G9"
        or control_manifest.get("descendant_source_migration_inventory")
        != G8_TO_G9_DESCENDANT_SOURCE_MIGRATION_RELATIVE
        or control_manifest.get("descendant_source_migration_module")
        != G9_DESCENDANT_SOURCE_MODULE_RELATIVE
        or control_manifest.get("resolved_guardrail_archive")
        != G8_RESOLVED_GUARDRAIL_ARCHIVE_RELATIVE
        or control_manifest.get("ordinary_worker_may_modify") is not False
        or control_manifest.get("manifest_is_completion_receipt") is not False
    ):
        errors.append("PCTDD-000 g9 control manifest claim boundary differs")
    manifest_hashes = (
        control_manifest.get("protected_control_hashes_before_manifest_and_seal")
        if isinstance(control_manifest, Mapping)
        else None
    )
    expected_manifest_paths = REQUIRED_HASHED_ARTIFACTS - {
        CONTROL_MANIFEST_RELATIVE,
        DEPENDENCY_SEAL_RELATIVE,
    }
    if not isinstance(manifest_hashes, Mapping) or set(manifest_hashes) != expected_manifest_paths:
        errors.append("PCTDD-000 control manifest protected path population differs")
    else:
        for relative, claimed in sorted(manifest_hashes.items()):
            path = ROOT / relative
            if not path.is_file() or claimed != _sha256_file(path):
                errors.append(f"PCTDD-000 control manifest hash differs: {relative}")
    operator_receipt_path = ROOT / OPERATOR_CONTROL_RECEIPT_RELATIVE
    operator_receipt = (
        _load_json(operator_receipt_path)
        if operator_receipt_path.is_file()
        else {}
    )
    expected_receipt_keys = {
        "schema",
        "task_id",
        "board_namespace",
        "plan_revision",
        "amends_plan_revision",
        "store_generation",
        "predecessor_generation",
        "migration_revision",
        "migration_inventory",
        "historical_source_migration_revision",
        "historical_g6_source_migration_inventory",
        "historical_provider_route_migration_revision",
        "historical_g7_provider_route_migration_inventory",
        "historical_g5_migration_inventory",
        "resolved_guardrail_archive",
        "status",
        "markdown_non_authoritative",
        "historical_completion_reissued",
        "historical_plan_and_task_definitions_preserved",
        "completion_authority",
        "dependency_seal",
        "claim",
    }
    if (
        not isinstance(operator_receipt, Mapping)
        or set(operator_receipt) != expected_receipt_keys
        or operator_receipt.get("schema") != "pctdd/operator-control-receipt@1"
        or operator_receipt.get("task_id") != "PCTDD-000"
        or operator_receipt.get("board_namespace") != NAMESPACE
        or operator_receipt.get("plan_revision") != PLAN_REVISION
        or operator_receipt.get("amends_plan_revision") != "PCTDD-PLAN-V1"
        or operator_receipt.get("store_generation") != "pctdd-v1-g9"
        or operator_receipt.get("predecessor_generation") != "pctdd-v1-g8"
        or operator_receipt.get("migration_revision")
        != "PCTDD-DESCENDANT-SOURCE-G9"
        or operator_receipt.get("migration_inventory")
        != G8_TO_G9_DESCENDANT_SOURCE_MIGRATION_RELATIVE
        or operator_receipt.get("historical_source_migration_revision")
        != "PCTDD-SOURCE-G7"
        or operator_receipt.get("historical_g6_source_migration_inventory")
        != G6_SOURCE_MIGRATION_RELATIVE
        or operator_receipt.get("historical_provider_route_migration_revision")
        != "PCTDD-SOURCE-PROVIDER-G8"
        or operator_receipt.get("historical_g7_provider_route_migration_inventory")
        != G7_PROVIDER_ROUTE_MIGRATION_RELATIVE
        or operator_receipt.get("historical_g5_migration_inventory")
        != G5_MIGRATION_RELATIVE
        or operator_receipt.get("resolved_guardrail_archive")
        != G8_RESOLVED_GUARDRAIL_ARCHIVE_RELATIVE
        or operator_receipt.get("status")
        != "sealed_pending_runtime_descendant_source_migration"
        or operator_receipt.get("markdown_non_authoritative") is not True
        or operator_receipt.get("historical_completion_reissued") is not False
        or operator_receipt.get(
            "historical_plan_and_task_definitions_preserved"
        )
        is not True
        or operator_receipt.get("dependency_seal") != DEPENDENCY_SEAL_RELATIVE
    ):
        errors.append("PCTDD-000 g9 operator control receipt differs")
    sources = _validate_sources(seal, errors)
    baseline_path = (
        ROOT
        / "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/repository_baseline.json"
    )
    baseline = _load_json(baseline_path) if baseline_path.is_file() else {}
    if not isinstance(baseline, Mapping) or baseline.get("schema") != "pctdd/repository-baseline@3":
        errors.append("g9 descendant-source successor repository baseline schema differs")
    else:
        if (
            baseline.get("control_generation_input_head")
            != G9_CONTROL_SOURCE_ANCHOR_HEAD
            or baseline.get("control_generation_input_tree")
            != G9_CONTROL_SOURCE_ANCHOR_TREE
        ):
            errors.append("g9 baseline source anchor differs")
        if baseline.get("all_governed_sources_clean_and_gitlink_exact") is not True:
            errors.append("g9 baseline did not capture clean exact-gitlink sources")
        baseline_sources = {
            str(item.get("path") or ""): item
            for item in baseline.get("sources", ())
            if isinstance(item, Mapping)
        }
        seal_sources = {
            str(item.get("path") or ""): item
            for item in _source_records(seal)
            if isinstance(item, Mapping)
        }
        if baseline_sources != seal_sources:
            errors.append("g9 baseline source records differ from the dependency seal")
        original = baseline.get("original_user_tree_evidence")
        if not isinstance(original, Mapping) or not original.get("root_status_sha256"):
            errors.append("g9 baseline does not preserve original dirty-user-tree evidence")

    python_record = _named_record(seal, ("python", "python_runtime"))
    if python_record is None:
        python_record = seal.get("toolchain") if isinstance(seal.get("toolchain"), Mapping) else None
    if python_record is None:
        errors.append("dependency seal omits Python toolchain record")
    else:
        sealed_executable = str(python_record.get("executable") or python_record.get("python_executable") or "")
        sealed_version = str(python_record.get("version") or python_record.get("python_version") or "")
        actual_executable = str(Path(sys.executable).resolve())
        if not sealed_executable or str(Path(sealed_executable).resolve()) != actual_executable:
            errors.append(f"Python executable differs: sealed={sealed_executable!r}, actual={actual_executable!r}")
        if sealed_version != platform.python_version():
            errors.append(f"Python version differs: sealed={sealed_version!r}, actual={platform.python_version()!r}")
        executable_hash = _normalize_sha256(
            python_record.get("sha256") or python_record.get("python_sha256") or ""
        )
        if executable_hash and Path(sys.executable).is_file() and _sha256_file(Path(sys.executable)) != executable_hash:
            errors.append("Python executable hash differs")

    actual_packages = {
        "pytest": _version("pytest"),
        "pytest_xdist": _version("pytest-xdist"),
        "duckdb": _version("duckdb"),
    }
    package_keys = {
        "pytest": ("pytest_version",),
        "pytest_xdist": ("pytest_xdist_version", "xdist_version"),
        "duckdb": ("duckdb_version",),
    }
    for name, keys in package_keys.items():
        sealed = str(_deep_value(seal, keys) or "")
        if not sealed:
            errors.append(f"dependency seal omits {name} version")
        elif sealed != actual_packages[name]:
            errors.append(f"{name} version differs: sealed={sealed!r}, actual={actual_packages[name]!r}")

    quack_record = _named_record(seal, ("quack", "quack_extension"))
    ducklake_record = _named_record(seal, ("ducklake", "ducklake_extension"))
    quack_extension_directory = _sealed_extension_directory("quack", quack_record, errors)
    ducklake_extension_directory = _sealed_extension_directory("ducklake", ducklake_record, errors)
    quack_actual = _extension_state(
        "quack", extension_directory=quack_extension_directory
    )
    ducklake_actual = _extension_state(
        "ducklake", extension_directory=ducklake_extension_directory
    )
    _verify_capability_record("quack", quack_record, quack_actual, errors, warnings)
    _verify_capability_record("ducklake", ducklake_record, ducklake_actual, errors, warnings)
    if not (quack_actual.get("available") and quack_actual.get("loaded")):
        errors.append("Quack must be locally installed and loadable for the authoritative state owner")
    if not (ducklake_actual.get("available") and ducklake_actual.get("loaded")):
        errors.append("DuckLake must be locally installed and loadable for the sealed analytics projection")

    quack_probe: dict[str, Any] = {}
    try:
        accelerator = ROOT / "external/ipfs_accelerate"
        if str(accelerator) not in sys.path:
            sys.path.insert(0, str(accelerator))
        from ipfs_accelerate_py.agent_supervisor.task_sources.quack_capabilities import (  # noqa: E402
            probe_quack_capabilities,
        )

        def sealed_quack_connection(duckdb_module: Any) -> Any:
            config = {
                "autoinstall_known_extensions": "false",
                "autoload_known_extensions": "false",
            }
            if quack_extension_directory:
                config["extension_directory"] = quack_extension_directory
            return duckdb_module.connect(database=":memory:", config=config)

        report = probe_quack_capabilities(
            allow_network_install=False,
            allow_local_load=True,
            use_cache=False,
            connection_factory=sealed_quack_connection,
        )
        quack_probe = report.to_dict() if hasattr(report, "to_dict") else {
            "status": str(getattr(report, "status", ""))
        }
        status_value = getattr(getattr(report, "status", None), "value", str(getattr(report, "status", "")))
        if str(status_value).lower() != "compatible":
            errors.append(f"Quack supervisor capability status is not compatible: {status_value}")
        if bool(getattr(report, "network_install_attempted", False)):
            errors.append("Quack capability probe attempted a network install")
    except Exception as exc:
        errors.append(f"Quack supervisor capability probe failed: {type(exc).__name__}: {exc}")

    prover_commands = {
        "lean": ("lean", "--version"),
        "cvc5": ("cvc5", "--version"),
        "coq": ("coqc", "--version"),
    }
    prover_states: dict[str, Any] = {}
    for name, argv in prover_commands.items():
        actual = _command_state(name, argv)
        prover_states[name] = actual
        aliases = (name, "rocq") if name == "coq" else (name,)
        record = _named_record(seal, aliases)
        _verify_capability_record(name, record, actual, errors, warnings)
        if record is not None:
            provisioning = str(
                record.get("provisioning") or record.get("installer_authority")
                or record.get("installation_authority") or ""
            ).lower()
            if "ipfs_datasets" not in provisioning:
                errors.append(f"{name} must bind ipfs_datasets_py as theorem-prover provisioning authority")

    _validate_proof_admission(seal, errors)

    if not SCHEDULER_PATH.is_file():
        errors.append("scheduler config is missing")
    else:
        scheduler = _load_json(SCHEDULER_PATH)
        if not isinstance(scheduler, Mapping):
            errors.append("scheduler config must be a JSON object")
        else:
            database = scheduler.get("database_program") or scheduler.get("task_store") or {}
            if database.get("authority_mode") != "quack" or database.get("task_source_kind") != "duckdb":
                errors.append("scheduler does not bind DuckDB + Quack authority")
            if database.get("failover_policy", "fail_closed") != "fail_closed":
                errors.append("scheduler task-store failover is not fail_closed")
            if database.get("store_generation") != "pctdd-v1-g9":
                errors.append("scheduler task-store generation is not g9")
            if database.get("quack_endpoint") != "quack:127.0.0.1:27278":
                errors.append("scheduler Quack endpoint is not the sealed g9 endpoint")
            if (
                database.get("predecessor_store_generation") != "pctdd-v1-g8"
                or database.get("predecessor_is_read_only_history") is not True
                or database.get("historical_store_generations")
                != ["pctdd-v1-g5", "pctdd-v1-g6", "pctdd-v1-g7", "pctdd-v1-g8"]
            ):
                errors.append("scheduler does not preserve g8 and prior history")
            for field in (
                "store_id",
                "event_store_path",
                "runtime_registry_path",
                "worktree_root",
            ):
                if G9_RUNTIME_ROOT not in str(database.get(field) or ""):
                    errors.append(f"scheduler {field} is not isolated under g9")
            owner = database.get("owner_management") or {}
            if (
                owner.get("mode") != "managed_local"
                or owner.get("max_restart_attempts") != 8
                or owner.get("health_check_interval_seconds") != 5.0
                or owner.get("initial_backoff_seconds") != 1.0
                or owner.get("max_backoff_seconds") != 10.0
            ):
                errors.append("scheduler g9 Quack restart policy differs")
            if G9_RUNTIME_ROOT not in str(owner.get("owner_state_dir") or ""):
                errors.append("scheduler Quack owner state is not isolated under g9")
            if scheduler.get("source_binding_successor_materialization") != sealed_source_migration_policy:
                errors.append("scheduler historical source-migration policy differs")
            if (
                scheduler.get("source_provider_route_successor_materialization")
                != sealed_provider_route_migration_policy
            ):
                errors.append(
                    "scheduler provider-route migration policy differs from the sealed inventory"
                )
            descendant_policy = scheduler.get("descendant_source_successor_materialization")
            if not isinstance(descendant_policy, Mapping):
                errors.append("scheduler g9 descendant-source policy is absent")
            else:
                if (
                    descendant_policy.get("capture_status")
                    != sealed_descendant_source_inventory.get("capture_status")
                    or descendant_policy.get("stopped_predecessor_capture")
                    != sealed_descendant_source_inventory.get("stopped_predecessor_capture")
                    or descendant_policy.get("control_source_anchor_head")
                    != G9_CONTROL_SOURCE_ANCHOR_HEAD
                    or descendant_policy.get("control_source_anchor_tree")
                    != G9_CONTROL_SOURCE_ANCHOR_TREE
                ):
                    errors.append("scheduler g9 descendant-source capture/source binding differs")
                module_path = ROOT / G9_DESCENDANT_SOURCE_MODULE_RELATIVE
                spec = importlib.util.spec_from_file_location(
                    "pctdd_g9_descendant_source_dependency_validation", module_path
                )
                if spec is None or spec.loader is None:
                    errors.append("cannot load protected g9 descendant-source successor module")
                else:
                    for entry in (str(ROOT / "external/ipfs_accelerate"), str(ROOT / "scripts")):
                        if entry not in sys.path:
                            sys.path.insert(0, entry)
                    try:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        pending = module.validate_pending_policy(scheduler)
                    except Exception as exc:
                        errors.append(
                            "canonical g9 descendant-source policy validation failed: "
                            f"{type(exc).__name__}: {exc}"
                        )
                    else:
                        if pending.get("valid") is not True:
                            errors.append("canonical g9 descendant-source policy differs")
            if any(scheduler.get(flag) is not False for flag in (
                "dependency_guardrail_enabled",
                "reconciliation_guardrail_enabled",
                "retry_budget_guardrail_enabled",
            )):
                errors.append("scheduler generated-board guardrails are not all disabled")
            operational = scheduler.get("operational_control_plane") or {}
            if (
                operational.get("markdown_is_bootstrap_only") is not True
                or operational.get("generated_guardrail_reporting")
                != "state_and_events_only_for_this_sealed_board"
            ):
                errors.append("scheduler generated guardrails are not state/event-only")
            provider = scheduler.get("provider") or {}
            if provider.get("implementation_fallback_authorized") is not True:
                errors.append("scheduler does not explicitly authorize the quota-only Codex implementation fallback")
            if any(
                provider.get(field) != value
                for field, value in EXPECTED_PROVIDER_ROUTE.items()
            ):
                errors.append("scheduler does not bind the exact reviewed Grok-to-Codex quota/medium route")
            if "provider_id" in provider or "model_id" in provider:
                errors.append("scheduler mixes the ordered provider route with legacy provider/model fields")
            if provider.get("completion_authority") != "controller_owned_sealed_validation_and_database_cas":
                errors.append("scheduler does not bind controller-owned completion authority")
            ducklake = scheduler.get("ducklake_projection_program") or scheduler.get("ducklake") or {}
            if ducklake.get("authority", ducklake.get("authoritative", False)) is not False:
                errors.append("scheduler incorrectly makes DuckLake authoritative")
            if "_g9/ducklake/" not in str(ducklake.get("catalog_path") or ""):
                errors.append("scheduler DuckLake catalog is not isolated under g9")
            if "_g9/ducklake/" not in str(ducklake.get("data_path") or ""):
                errors.append("scheduler DuckLake data is not isolated under g9")

    status = "passed" if not errors else "failed"
    return {
        "schema": "pctdd/dependency-validation@1",
        "status": status,
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "board_namespace": NAMESPACE,
        "plan_revision": PLAN_REVISION,
        "sealed_artifact_count": len(artifact_hashes),
        "sources": sources,
        "environment": {
            "python_executable": str(Path(sys.executable).resolve()),
            "python_version": platform.python_version(),
            **actual_packages,
            "quack": quack_actual,
            "ducklake": ducklake_actual,
            "quack_supervisor_probe": quack_probe,
            "theorem_provers": prover_states,
        },
        "source_head": _git("rev-parse", "HEAD"),
        "source_tree": _git("rev-parse", "HEAD^{tree}"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-all", action="store_true", help="validate all sealed dependencies")
    parser.parse_args()
    try:
        result = validate()
    except Exception as exc:  # preserve machine-readable failure diagnostics
        result = {
            "schema": "pctdd/dependency-validation@1",
            "status": "failed",
            "valid": False,
            "errors": [f"{type(exc).__name__}: {exc}"],
            "warnings": [],
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("valid") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
