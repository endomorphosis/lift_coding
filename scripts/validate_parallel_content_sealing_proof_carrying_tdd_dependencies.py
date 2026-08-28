#!/usr/bin/env python3
"""Verify the PCTDD dependency/source seal against the current checkout.

The validator is deliberately read-only: it never installs extensions,
provers, keys, or packages.  Missing optional proof capabilities may be sealed
as typed unavailable records; a record marked required or production-admitted
fails closed when it cannot be reproduced exactly.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
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
PLAN_REVISION = "PCTDD-PLAN-V1"

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
    "config/agent_supervisor_parallel_content_sealing_proof_carrying_tdd_scheduler.json",
    "config/parallel_content_sealing_proof_carrying_tdd_benchmark.json",
    "scripts/validate_parallel_content_sealing_proof_carrying_tdd_dependencies.py",
    "scripts/validate_parallel_content_sealing_proof_carrying_tdd_board.py",
    "scripts/materialize_parallel_content_sealing_proof_carrying_tdd_program.py",
    "scripts/ops/agent_supervisor/parallel_content_sealing_proof_carrying_tdd.py",
}

SOURCE_PATHS = {
    "ipfs_accelerate_py": "external/ipfs_accelerate",
    "ipfs_datasets_py": "external/ipfs_datasets",
    "ipfs_kit_py": "external/ipfs_kit",
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


def _extension_state(name: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": name,
        "available": False,
        "loaded": False,
        "version": "",
        "error": "",
    }
    try:
        import duckdb  # imported only during explicit validation

        connection = duckdb.connect(":memory:")
        try:
            connection.execute(f"LOAD {name}")
            result["loaded"] = True
            row = connection.execute(
                "SELECT extension_version, installed, loaded, install_mode, installed_from "
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
                })
            else:
                result["available"] = result["loaded"]
        finally:
            connection.close()
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def _command_state(name: str, argv: tuple[str, ...]) -> dict[str, Any]:
    executable = shutil.which(argv[0])
    result: dict[str, Any] = {
        "name": name,
        "command": argv[0],
        "available": executable is not None,
        "executable": str(Path(executable).resolve()) if executable else "",
        "version": "",
        "error": "",
    }
    if executable is None:
        return result
    command_environment = dict(os.environ)
    command_environment["ELAN_NO_UPDATE_CHECK"] = "1"
    # ``lean`` is commonly an elan shim.  Do not let an explicit dependency
    # check turn into an implicit toolchain download: first establish that an
    # installed toolchain already exists locally.
    if name == "lean" and ("/.elan/" in str(Path(executable).resolve()) or Path(executable).name == "elan"):
        elan = shutil.which("elan")
        if elan is None:
            result["available"] = False
            result["error"] = "elan shim present but elan executable is unavailable"
            return result
        listed = subprocess.run(
            [elan, "toolchain", "list"], text=True, capture_output=True,
            check=False, timeout=10, env=command_environment,
        )
        installed = [line.strip() for line in listed.stdout.splitlines() if line.strip()]
        if listed.returncode != 0 or not installed or installed == ["no installed toolchains"]:
            result["available"] = False
            result["error"] = "elan has no locally installed Lean toolchain"
            return result
    try:
        completed = subprocess.run(
            [executable, *argv[1:]], text=True, capture_output=True,
            check=False, timeout=20, env=command_environment,
        )
        text = (completed.stdout or completed.stderr).strip()
        result["version"] = text.splitlines()[0] if text else ""
        if completed.returncode != 0:
            result["available"] = False
            result["error"] = f"exit {completed.returncode}: {text[:300]}"
    except Exception as exc:
        result["available"] = False
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


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
    if observed is None:
        errors.append(f"{name} capability record omits explicit availability")
    elif observed != bool(actual.get("available") and actual.get("loaded", True)):
        errors.append(
            f"{name} availability differs: sealed={observed}, "
            f"actual={bool(actual.get('available') and actual.get('loaded', True))}"
        )
    sealed_version = str(record.get("version") or record.get("extension_version") or "").strip()
    actual_version = str(actual.get("version") or "").strip()
    if observed and not sealed_version:
        errors.append(f"{name} available capability omits exact version")
    elif sealed_version and actual_version and sealed_version not in actual_version and actual_version not in sealed_version:
        errors.append(f"{name} version differs: sealed={sealed_version!r}, actual={actual_version!r}")
    required = _record_bool(record, "required", "required_for_launch", "mandatory") is True
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

    artifact_hashes = _validate_artifacts(seal, errors)
    sources = _validate_sources(seal, errors)

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

    quack_actual = _extension_state("quack")
    ducklake_actual = _extension_state("ducklake")
    _verify_capability_record("quack", _named_record(seal, ("quack", "quack_extension")), quack_actual, errors, warnings)
    _verify_capability_record("ducklake", _named_record(seal, ("ducklake", "ducklake_extension")), ducklake_actual, errors, warnings)
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

        report = probe_quack_capabilities(
            allow_network_install=False, allow_local_load=True, use_cache=False
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
            ducklake = scheduler.get("ducklake_projection_program") or scheduler.get("ducklake") or {}
            if ducklake.get("authority", ducklake.get("authoritative", False)) is not False:
                errors.append("scheduler incorrectly makes DuckLake authoritative")

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
