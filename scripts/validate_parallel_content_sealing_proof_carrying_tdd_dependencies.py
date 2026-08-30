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
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping


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
    "test/api/parallel_content_sealing/test_pctdd_g6_control_amendment.py",
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
    if seal.get("store_generation") != "pctdd-v1-g6":
        errors.append("dependency seal store generation differs")
    if seal.get("predecessor_generation") != "pctdd-v1-g5":
        errors.append("dependency seal predecessor generation differs")
    if seal.get("migration_inventory") != "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/g5_migration_inventory.json":
        errors.append("dependency seal migration inventory binding differs")
    migration_path = ROOT / str(seal.get("migration_inventory") or "")
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
        if candidate is None or not candidate.is_file() or _sha256_file(candidate) != expected:
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
            errors.append(f"PCTDD-004 nested migration commit unavailable: {commit}")
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

    artifact_hashes = _validate_artifacts(seal, errors)
    control_manifest_path = ROOT / CONTROL_MANIFEST_RELATIVE
    control_manifest = (
        _load_json(control_manifest_path) if control_manifest_path.is_file() else {}
    )
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
    sources = _validate_sources(seal, errors)
    baseline_path = (
        ROOT
        / "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/repository_baseline.json"
    )
    baseline = _load_json(baseline_path) if baseline_path.is_file() else {}
    if not isinstance(baseline, Mapping) or baseline.get("schema") != "pctdd/repository-baseline@2":
        errors.append("fresh g6 repository baseline schema differs")
    else:
        if baseline.get("all_governed_sources_clean_and_gitlink_exact") is not True:
            errors.append("fresh g6 baseline did not capture clean exact-gitlink sources")
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
            errors.append("fresh g6 baseline source records differ from the dependency seal")
        original = baseline.get("original_user_tree_evidence")
        if not isinstance(original, Mapping) or not original.get("root_status_sha256"):
            errors.append("fresh g6 baseline does not preserve original dirty-user-tree evidence")

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
            if database.get("store_generation") != "pctdd-v1-g6":
                errors.append("scheduler task-store generation is not g6")
            if database.get("quack_endpoint") != "quack:127.0.0.1:42778":
                errors.append("scheduler Quack endpoint is not the sealed g6 endpoint")
            if database.get("predecessor_store_generation") != "pctdd-v1-g5" or database.get("predecessor_is_read_only_history") is not True:
                errors.append("scheduler does not preserve g5 as explicit read-only history")
            provider = scheduler.get("provider") or {}
            if provider.get("implementation_fallback_authorized") is not False:
                errors.append("scheduler does not disable conflicting Codex implementation fallback")
            if provider.get("provider_id") != "grok_cli" or provider.get("model_id") != "grok-4.6":
                errors.append("scheduler does not bind the exact Grok-only implementation route")
            if provider.get("completion_authority") != "controller_owned_sealed_validation_and_database_cas":
                errors.append("scheduler does not bind controller-owned completion authority")
            if any(key.startswith("fallback_") for key in provider):
                errors.append("scheduler encodes an unauthorized implementation fallback")
            ducklake = scheduler.get("ducklake_projection_program") or scheduler.get("ducklake") or {}
            if ducklake.get("authority", ducklake.get("authoritative", False)) is not False:
                errors.append("scheduler incorrectly makes DuckLake authoritative")
            if "_g6/ducklake/" not in str(ducklake.get("catalog_path") or ""):
                errors.append("scheduler DuckLake catalog is not isolated under g6")

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
